#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sync_api_json.py — VPP *.api 改动后，将编译机生成的 *.api.json 下载暂存到本地 runtime/<SESS>/。

设计（对应同目录 SKILL.md）：
  1. 自动识别本地 npp worktree 中改动的 *.api 文件
     （相对基线 diff + 未提交改动 + 未跟踪文件；插件/核心路径分别映射）
  2. 映射到编译机 worktree 的
     build-root/install-<ARCH>/vpp/share/vpp/api/plugins/<模块>.api.json （插件）
     或 build-root/install-<ARCH>/vpp/share/vpp/api/<模块>.api.json （核心）
  3. SFTP 下载到 <项目根>/runtime/<SESS>/<模块>.api.json
  4. SESS = 环境变量 DSH_SESSION_ID（当前会话唯一标识，隔离多会话冲突），--sess 可覆盖

用法（本机 Windows 用 python；python3 是 WindowsApps 商店占位符，不可用）：
  python sync_api_json.py --remote-worktree-name <worktree名>   # 自动识别改动
  python sync_api_json.py --api-file src/plugins/pbr/pbr.api --remote-worktree-name <worktree名>
  python sync_api_json.py --remote-worktree-name <worktree名> --dry-run   # 只打印计划
密码：env_config/deploy_build/deploy_config.json 的 remote_pass（不入库），或环境变量
DEPLOY_BUILD_REMOTE_PASS / SSH_PASSWORD（不通过 CLI 传递）。
默认连接参数（liuxing5/packet-nf/x86_64）为本项目专用；其他环境请用 --remote-* 覆盖。
"""

import argparse
import os
import posixpath
import subprocess
import sys
from pathlib import Path

import paramiko

# 项目根 = 本文件所在目录的上三级（skills/vpp-api-sync/ -> skills/ -> .dsh/ -> 仓库根）
# （目录迁移后 .dsh 为真实目录，realpath 直接得到仓库根；推导逻辑不变）
SKILL_DIR = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))


def _resolve_workspace_root():
    """解析 env_config 落盘基目录。

    优先级：
      1. 环境变量 AGENT_ASSETS_DIR（显式指定，最优先；指向不存在目录会打印 warning 并回退）
      2. `git rev-parse --show-toplevel`（在 cwd 或其父目录探测到的 git 根）
      3. `os.getcwd()` 兜底（脚本被复制到非 git 目录调试时），会打印 warning 提示用户设置 AGENT_ASSETS_DIR

    该函数与 deploy-build / certificate-apply / mr-merge 三个脚本的解析逻辑一致。
    """
    env_root = os.environ.get("AGENT_ASSETS_DIR")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if p.is_dir():
            return p
        print(
            f"[WARN] AGENT_ASSETS_DIR={env_root!r} 指向的目录不存在，回退到探测",
            file=sys.stderr,
        )
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            root = result.stdout.strip()
            if root:
                return Path(root)
    except (FileNotFoundError, OSError):
        pass
    cwd = Path(os.getcwd()).resolve()
    print(
        f"[WARN] 未探测到 git 根（cwd={cwd}），env_config/ 将落到 cwd 下；"
        f"如需锚定到具体仓库，请设置环境变量 AGENT_ASSETS_DIR",
        file=sys.stderr,
    )
    return cwd


# env_config 创建基准目录：固定为 AGENT_ASSETS_DIR，缺省通过 git 探测定位当前仓库根，
# 与 deploy-build / certificate-apply 约定一致（AGENT_ASSETS_DIR 环境变量可覆盖）。
AGENT_ASSETS_DIR = _resolve_workspace_root()
ENV_CONFIG_DIR = os.path.join(str(AGENT_ASSETS_DIR), ".dsh", "env_config", "deploy_build")

DEFAULT_LOCAL_DIR = r"F:\software\NF605\npp\606\npp.worktrees\release-V6.0R06F02_M02B00"
DEFAULT_REMOTE_BASE = "/home/liuxing5/newnf-605-master/packet-nf"
DEFAULT_REMOTE_HOST = "10.66.240.3"
DEFAULT_REMOTE_PORT = 50222
DEFAULT_REMOTE_USER = "liuxing5"
DEFAULT_BASE_BRANCH = "release/V6.0R06F02_M02B00"


def _setup_utf8():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _load_remote_pass_from_env_config():
    """从 <AGENT_ASSETS_DIR>/.dsh/env_config/deploy_build/deploy_config.json 读取 remote_pass（该目录不入库）。

    作为环境变量之外的密码来源（deploy-build 约定：密码明文存 env_config）。
    """
    try:
        import json
        cfg_file = os.path.join(
            ENV_CONFIG_DIR, "deploy_config.json")
        with open(cfg_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("remote_pass") or None
    except Exception:
        return None


def git_cmd(local_dir, args):
    """在本地 worktree 执行 git 命令，返回 stdout。"""
    try:
        r = subprocess.run(["git"] + args, cwd=local_dir,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        return (r.stdout or "").strip()
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[WARN] git 命令失败 {args}: {e}")
        return ""


def resolve_base(local_dir, branch, explicit_base):
    """解析对比基线：隔离出本次改动（而非整个分支差异）。

    优先级：
      1) --base 显式指定（须可解析且不是 HEAD 本身）
      2) 当前分支 upstream / origin/<branch> / origin/master / master 的 merge-base
         —— 避免分支名与 HEAD 同名（如 worktree 直接 checkout 在 release 分支上、
         修复提交叠在其上）导致 diff 为空
      3) 兜底 HEAD~1
    """
    head = git_cmd(local_dir, ["rev-parse", "HEAD"])
    if explicit_base:
        v = git_cmd(local_dir, ["rev-parse", "--verify", explicit_base])
        if v and v != head:
            return explicit_base
    up = git_cmd(local_dir, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    refs = ([up] if up else []) + [f"origin/{branch}", "origin/master", "master"]
    for ref in refs:
        if not ref:
            continue
        mb = git_cmd(local_dir, ["merge-base", ref, "HEAD"])
        if mb:
            return mb
    return "HEAD~1"


def detect_changed_api(local_dir, base):
    """返回改动的 *.api 相对路径列表（基线 diff + 未提交 + 未跟踪）。"""
    changed = set()
    # --no-renames：避免 rename 输出 R100\t旧\t新 三列导致解析取错路径
    out = git_cmd(local_dir, ["diff", "--name-status", "--no-renames", base, "HEAD"])
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip().endswith(".api"):
            changed.add(parts[1].strip())
    for line in git_cmd(local_dir, ["diff", "--name-only", "HEAD"]).splitlines():
        p = line.strip()
        if p and p.endswith(".api"):
            changed.add(p)
    for line in git_cmd(local_dir, ["ls-files", "--others", "--exclude-standard"]).splitlines():
        p = line.strip()
        if p and p.endswith(".api"):
            changed.add(p)
    return sorted(changed)


def api_json_basename(api_rel):
    """src/plugins/pbr/pbr.api -> pbr.api.json"""
    base = os.path.basename(api_rel)
    if base.endswith(".api"):
        return base[: -len(".api")] + ".api.json"
    return base + ".json"


def remote_api_json_rel(api_rel):
    """把本地 *.api 相对路径映射为编译机 api.json 相对路径（相对 vpp/share/vpp/api/）。

    插件（src/plugins/ 下）-> plugins/<模块>.api.json
    核心（如 src/vnet/*.api）-> <模块>.api.json（根目录）
    """
    jname = api_json_basename(api_rel)
    if api_rel.replace("\\", "/").startswith("src/plugins/"):
        subdir = "plugins"
    else:
        subdir = "."
    return posixpath.join(subdir, jname).lstrip("./")


def resolve_sess(explicit):
    if explicit:
        return explicit
    return os.environ.get("DSH_SESSION_ID") or "default"


def main():
    _setup_utf8()
    ap = argparse.ArgumentParser(description="VPP *.api.json 下载暂存")
    ap.add_argument("--api-file", action="append", default=None,
                    help="显式指定改动的 .api 相对路径（可多次）；缺省自动识别")
    ap.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR, help="本地 npp worktree 目录")
    ap.add_argument("--base", default=DEFAULT_BASE_BRANCH, help="对比基线分支")
    ap.add_argument("--remote-host", default=DEFAULT_REMOTE_HOST)
    ap.add_argument("--remote-port", type=int, default=DEFAULT_REMOTE_PORT)
    ap.add_argument("--remote-user", default=DEFAULT_REMOTE_USER)
    ap.add_argument("--remote-base", default=DEFAULT_REMOTE_BASE, help="编译机 packet-nf 目录")
    ap.add_argument("--remote-worktree-name", default=None,
                    help="编译机 worktree 名（须与 deploy-build --worktree 一致，如 fix-NEWNF-54398）")
    ap.add_argument("--arch", default="x86_64", help="install-<ARCH> 架构")
    ap.add_argument("--out-root", default=os.path.join(PROJECT_ROOT, "runtime"),
                    help="暂存根目录（默认 <项目根>/runtime）")
    ap.add_argument("--sess", default=None, help="会话核心名；缺省=DSH_SESSION_ID")
    ap.add_argument("--expect-field", default=None,
                    help="新增字段名；下载后对暂存 api.json 做子串自检，未命中则非零退出")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不下载")
    args = ap.parse_args()

    # 1) 识别改动 *.api
    branch = git_cmd(args.local_dir, ["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    if args.api_file:
        api_files = [f for f in args.api_file if f.endswith(".api")]
        if not api_files:
            print("[ERROR] --api-file 均不是 *.api 文件")
            sys.exit(2)
    else:
        base = resolve_base(args.local_dir, branch, args.base)
        print(f"[INFO] 本地分支 = {branch}")
        print(f"[INFO] 对比基线 = {base}")
        api_files = detect_changed_api(args.local_dir, base)
        if not api_files:
            print("[INFO] 本地未检测到 *.api 改动。可用 --api-file 显式指定。")
            return

    # 2) SESS 与暂存目录
    sess = resolve_sess(args.sess)
    out_dir = os.path.join(args.out_root, sess)
    print(f"[INFO] 会话核心 SESS = {sess}")
    print(f"[INFO] 暂存目录 = {out_dir}")

    # 3) 编译机 worktree 名：本地分支名不一定是远端 worktree 名（本地常 checkout 在
    #    release 分支、修复提交叠其上）。分支以 release/master/main 开头且未显式指定 → 硬失败。
    if args.remote_worktree_name:
        wt = args.remote_worktree_name
    elif branch and (branch.startswith("release/") or branch in ("master", "main")):
        print("[ERROR] 本地分支不是修复分支，无法推断编译机 worktree 名；"
              "请显式 --remote-worktree-name <deploy-build 的 --worktree 名>（如 fix-NEWNF-54398）")
        sys.exit(2)
    else:
        wt = branch or "fix-UNKNOWN"
    api_root = posixpath.join(args.remote_base, wt, "build-root",
                              f"install-{args.arch}", "vpp", "share", "vpp", "api")
    print(f"[INFO] 编译机 api 目录 = {api_root}")

    targets = [(api_rel, api_json_basename(api_rel),
                posixpath.join(api_root, remote_api_json_rel(api_rel)))
               for api_rel in api_files]
    for api_rel, jname, rp in targets:
        print(f"  [CHANGE] {api_rel} -> {jname}")

    if args.dry_run:
        for api_rel, jname, rp in targets:
            print(f"  [DRY] {jname} <- {rp}")
        print(f"  [DRY] 将下载到 {out_dir}")
        return

    # 4) 密码：env_config 配置文件（不入库）→ 环境变量覆盖；不通过 CLI 传递
    password = os.environ.get("DEPLOY_BUILD_REMOTE_PASS") or os.environ.get("SSH_PASSWORD")
    if not password:
        password = _load_remote_pass_from_env_config()
    if not password:
        print("[ERROR] 未提供编译机密码：deploy_config.json#remote_pass（env_config 不入库）或"
              "环境变量 DEPLOY_BUILD_REMOTE_PASS / SSH_PASSWORD")
        sys.exit(2)

    # 5) SFTP 下载
    ssh = paramiko.SSHClient()
    # 与 deploy-build 一致使用 AutoAddPolicy（自动信任主机密钥）；
    # 敏感环境建议改为固定指纹 known_hosts 校验。
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.remote_host, port=args.remote_port, username=args.remote_user,
                password=password, timeout=15)
    os.makedirs(out_dir, exist_ok=True)
    staged = []
    try:
        sftp = ssh.open_sftp()
        try:
            for api_rel, jname, rp in targets:
                try:
                    st = sftp.stat(rp)
                except IOError:
                    print(f"  [MISS] 编译机不存在: {rp}")
                    continue
                lp = os.path.join(out_dir, jname)
                sftp.get(rp, lp)
                print(f"  [OK] {jname} <- {rp}")
                print(f"       size={st.st_size}B  remote_mtime={st.st_mtime}")
                staged.append((jname, lp, rp))
        finally:
            sftp.close()
    finally:
        ssh.close()

    if not staged:
        print(f"[ERROR] 0 个 api.json 下载成功（远端文件缺失或路径错误）。"
              "请确认编译已通过、--remote-worktree-name 正确。")
        sys.exit(1)

    # 6) 内容自检（--expect-field）：新字段命中任一暂存 api.json 即过
    #    （跨多模块改动时字段只属于对应模块，不能要求每个文件都含）
    if args.expect_field:
        hits = []
        for jname, lp, rp in staged:
            with open(lp, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if args.expect_field in content:
                hits.append(jname)
        if not hits:
            print(f"[ERROR] 暂存 api.json 均未包含新字段 {args.expect_field}，"
                  "api.json 可能仍是旧版（编译未通过/未重新生成）")
            sys.exit(1)
        for jname in hits:
            print(f"  [EXPECT] {jname} 包含 {args.expect_field} ✓")

    print(f"\n[SUMMARY] 暂存 {len(staged)} 个 api.json 到 {out_dir}")
    for jname, lp, rp in staged:
        print(f"  {lp}")
    print("\n[NOTE] 以上文件即移交 vpp-agent 开发人员的输入物"
          "（vpp-agent 根: F:/software/NF605/system-management/npp-agent）")


if __name__ == "__main__":
    main()
