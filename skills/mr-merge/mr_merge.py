#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mr_merge.py - MR 合并 / 批量 cherry-pick 工具

输入 commit 列表 + 目标分支，从目标分支 HEAD 派生 XX-MR 分支，
按 author-date 从早到晚排序后逐个 cherry-pick；
通过文件变更集相交预测冲突，预测会冲突的 commit 汇总到「需人工介入」列表。
人工介入完成后调用 check 子命令逐一校验每个 commit 是否完整到达 MR 分支。

设计要点（详细见 ../SKILL.md）：
- 纯本地 git 操作，不涉及 SSH / 远端
- 状态文件 mr_state.json 每完成一个 commit 原子写一次
- 冲突预测：commit 改的文件集 ∩ 目标分支 base 之后改的文件集
- git_cmd() 沿用 deploy_build 的 Windows UTF-8 包装方案
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# =====================================================================
# Windows GBK 兜底
# =====================================================================
# Windows 默认 GBK 编码，print 含中文/Unicode 符号（→/✗ 等）会抛
# UnicodeEncodeError。先尝试 reconfigure 到 UTF-8（Python 3.7+）；
# 失败则保持现状，依赖 print 行无 Unicode 符号兜底——cmd_start / cmd_resume
# 的所有 print 行已把 →/✗ 替换为 ->/[X]。注释/docstring 中的 → 字符不在
# print 路径，不影响 GBK 兜底。reconfigure 在 stdout 被重定向到文件时
# 偶发失败，故 try/except 兜底。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    # Python < 3.7 或 stdout 不可 reconfigure（被管道重定向等），
    # 依赖 print 行已无 Unicode 符号来兜底。
    pass


# =====================================================================
# 路径常量（项目根锚定，禁止相对化）
# =====================================================================

PROJECT_ROOT = Path("REDACTED_WORKSPACE_PATH")
MR_STATE_DIR = PROJECT_ROOT / "mr-state"
SKILL_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SKILL_DIR / "templates"
REPORT_TEMPLATE = TEMPLATE_DIR / "report.md"


# =====================================================================
# Git 操作（沿用 deploy_build 的 git_cmd 模式）
# =====================================================================

def git_cmd(args, cwd=None, quiet=False):
    """执行 git 命令，失败时打印错误并返回空字符串。

    Windows 下 subprocess 默认按 GBK 解码 git 的 UTF-8 输出，遇到中文文件名
    （如"搜索结果"）会抛 UnicodeDecodeError，因此显式指定 UTF-8 并容忍非法字节。
    quiet=True 时失败不打印错误（用于探测类命令）。
    """
    cwd = cwd or str(PROJECT_ROOT)
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        if not quiet:
            print(f"[ERROR] git {' '.join(args)}: {result.stderr.strip()}")
        return ""
    return result.stdout.strip()


def git_cmd_rc(args, cwd=None):
    """同 git_cmd 但返回 (stdout, returncode)，不静默失败。

    用于需要判断成功/失败但不靠 stdout 文本猜测的场景（见 do_cherry_pick）。
    """
    cwd = cwd or str(PROJECT_ROOT)
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return result.stdout.strip(), result.returncode


# =====================================================================
# 状态文件读写
# =====================================================================

def state_path(mr_name):
    return MR_STATE_DIR / mr_name / "mr_state.json"


def report_path(mr_name):
    return MR_STATE_DIR / mr_name / "report.md"


def load_state(mr_name):
    p = state_path(mr_name)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state, mr_name):
    """原子写状态文件：先写 .tmp 再 rename，避免半完成状态。"""
    p = state_path(mr_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def init_state(mr_name, base_branch, commits_meta):
    """初始化一个新的状态文件。"""
    return {
        "mr_name": mr_name,
        "base_branch": base_branch,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "commits": [
            {
                "id": m["id"],
                "title": m["title"],
                "author_date": m["author_date"],
                "files_changed": m["files_changed"],
                "predicted_conflict": False,
                "conflict_reason": "",
                "status": "pending",
                "cherry_pick_log": "",
            }
            for m in commits_meta
        ],
    }


# =====================================================================
# 核心：commit 元数据查询
# =====================================================================

def resolve_commit_ids(commits_arg, repo):
    """校验每个 commit 存在，取完整 hash（去重保序）。

    支持两种传入方式（混用也行）：
    - 多个独立参数（argparse nargs='+' 风格）：`--commits a b c`
    - 单个逗号分隔字符串：`--commits a,b,c`（SKILL.md 示例风格）
    内部先把每个 token 按逗号 split 展平，再去重。
    """
    seen = set()
    out = []
    flat = []
    for token in commits_arg:
        flat.extend(p.strip() for p in token.split(",") if p.strip())
    for c in flat:
        if c in seen:
            continue
        seen.add(c)
        full = git_cmd(["rev-parse", "--verify", f"{c}^{{commit}}"], cwd=repo, quiet=True)
        if not full:
            # 可能是缩写 hash
            full = git_cmd(["rev-parse", c], cwd=repo, quiet=True)
        if not full:
            print(f"[ERROR] commit '{c}' 不存在或无法解析。")
            sys.exit(1)
        out.append(full)
    return out


def get_commit_meta(commit, repo):
    """返回 {id, title, author_date, files_changed}。"""
    title = git_cmd(["log", "-1", "--format=%s", commit], cwd=repo)
    author_date = git_cmd(["log", "-1", "--format=%aI", commit], cwd=repo)
    files_out = git_cmd(["show", "--name-only", "--format=", commit], cwd=repo)
    files = [f.strip() for f in files_out.splitlines() if f.strip()]
    return {
        "id": commit,
        "title": title,
        "author_date": author_date,
        "files_changed": files,
    }


def sort_commits_by_date(commits_meta):
    """按 author_date 升序。author_date 缺失的排到最后。"""
    def key(m):
        try:
            return datetime.fromisoformat(m["author_date"])
        except Exception:
            return datetime.max
    return sorted(commits_meta, key=key)


# =====================================================================
# 冲突预测
# =====================================================================

def get_files_modified_since(base, head, repo):
    """取 base..head 之间改的文件集。"""
    out = git_cmd(["diff", "--name-only", base, head], cwd=repo)
    return set(f.strip() for f in out.splitlines() if f.strip())


def predict_conflicts(commits_meta, base_branch, head, repo):
    """对每个 commit 判断是否与目标分支改动文件重叠。

    返回 [(commit_meta, conflict_reason)] 列表（仅含预测冲突的）。
    """
    target_files = get_files_modified_since(base_branch, head, repo)
    print(f"[INFO] 目标分支 {base_branch}..{head} 改动了 {len(target_files)} 个文件。")
    conflicts = []
    for m in commits_meta:
        overlap = target_files & set(m["files_changed"])
        if overlap:
            reason = (
                f"commit 改动文件 {sorted(m['files_changed'])} "
                f"与目标分支改动文件 {sorted(overlap)} 重叠"
            )
            conflicts.append((m, reason))
    return conflicts


# =====================================================================
# 工作区检查
# =====================================================================

def assert_clean_working_tree(repo):
    """启动前检查工作区：忽略 untracked 文件（仅看 staged/unstaged 改动）。

    NPP 这类工程目录常带 .codegraph/、.claude/ 等本地工具/构建产物，
    算成"脏"会迫使脚本无法直接运行。--untracked-files=no 让 git status
    不输出 `??` 行，但保留 `M/A/D/R` 等真实改动。
    """
    out = git_cmd(["status", "--porcelain", "--untracked-files=no"], cwd=repo)
    if out.strip():
        print("[ERROR] 当前工作区有未提交改动（staged/unstaged），请先 stash 或 commit：")
        print(out)
        sys.exit(1)


def assert_branch_exists(branch, repo):
    if not git_cmd(["rev-parse", "--verify", branch], cwd=repo, quiet=True):
        print(f"[ERROR] 目标分支 '{branch}' 不存在。")
        sys.exit(1)


def assert_mr_branch_not_exists(mr_name, repo):
    """MR 分支名直接用 mr_name，不加后缀。"""
    if git_cmd(["rev-parse", "--verify", mr_name], cwd=repo, quiet=True):
        print(f"[ERROR] MR 分支 '{mr_name}' 已存在，请先删除或换名。")
        print(f"       提示: git branch -D {mr_name}")
        sys.exit(1)


# =====================================================================
# 分支操作 + cherry-pick
# =====================================================================

def create_mr_branch(mr_name, base_branch, repo):
    """git checkout -b <mr_name> <base>"""
    out = git_cmd(["checkout", "-b", mr_name, base_branch], cwd=repo)
    if not out and git_cmd(["rev-parse", "--verify", mr_name], cwd=repo, quiet=True):
        # 切了但 stdout 可能是空（checkout 不输出）
        return
    if not git_cmd(["rev-parse", "--verify", mr_name], cwd=repo, quiet=True):
        print(f"[ERROR] 创建 MR 分支 '{mr_name}' 失败。")
        sys.exit(1)


def do_cherry_pick(commit, repo):
    """git cherry-pick -x <commit>。返回 (success, log)

    判定逻辑（按优先级）：
    1. 如果 CHERRY_PICK_HEAD 文件存在 → 在 cherry-pick 中（冲突或半完成）→ 失败
    2. 否则用 git rev-parse --verify 查 HEAD 是否已包含新 commit → 成功
    3. 否则 fallback 看 git returncode（空 cherry-pick / 异常）
    """
    out, rc = git_cmd_rc(["cherry-pick", "-x", commit], cwd=repo)

    # 1. 检查 CHERRY_PICK_HEAD：存在 = 在 cherry-pick 中 = 冲突或未完成
    cherry_head_path = git_cmd(["rev-parse", "--git-path", "CHERRY_PICK_HEAD"], cwd=repo)
    if cherry_head_path:
        p = Path(repo) / cherry_head_path if not Path(cherry_head_path).is_absolute() else Path(cherry_head_path)
        if p.exists():
            git_cmd(["cherry-pick", "--abort"], cwd=repo, quiet=True)
            return False, f"cherry-pick 冲突或未完成（CHERRY_PICK_HEAD 存在）: {out}"

    # 2. CHERRY_PICK_HEAD 不存在：要么成功，要么空 cherry-pick
    #    通过比较 HEAD 哈希前后判断是否真的产生了 commit
    head_after = git_cmd(["rev-parse", "HEAD"], cwd=repo)
    # 用 reflog / show 简化为：检查 out 中是否含 commit 标记，或用 reflog 比对
    # 简化策略：看 out 是否包含 "[<branch> <hash>]" 格式（git 默认成功输出）
    if rc == 0 and ("]" in out or "file changed" in out or "files changed" in out):
        return True, out or "cherry-pick OK"

    # 3. 没有 CHERRY_PICK_HEAD、rc 也没报告成功 → 视为失败（空 cherry-pick 等）
    return False, f"cherry-pick 失败 (rc={rc}, out={out or '(empty)'})"


def verify_commit_present(commit, repo):
    """check 阶段：commit 是否到达 MR 分支（用 cherry-pick -x 自动写入的 (cherry picked from commit X) 标记）

    注意：默认 grep 是 basic regex，未闭合的 ) 会静默失败，必须用 -E。
    同时大小写也要忽略，因为 -x 写入的格式是固定的，hash 前缀可能跨大小写。
    """
    out = git_cmd(
        ["log", "--extended-regexp", "-i",
         f"--grep=cherry picked from commit {commit[:7]}",
         "--format=%H"],
        cwd=repo,
    )
    return bool(out.strip())


# =====================================================================
# 子命令实现
# =====================================================================

def cmd_analyze(args, repo):
    """只预测，不改分支。"""
    assert_clean_working_tree(repo)
    assert_branch_exists(args.base, repo)

    print(f"[INFO] 解析 {len(args.commits)} 个 commit...")
    ids = resolve_commit_ids(args.commits, repo)
    print(f"[INFO] 解析后 {len(ids)} 个唯一 commit。")

    print(f"[INFO] 取每个 commit 的元数据...")
    metas = [get_commit_meta(c, repo) for c in ids]
    metas = sort_commits_by_date(metas)

    target_head = git_cmd(["rev-parse", "--verify", args.base], cwd=repo) or "HEAD"
    print(f"[INFO] 目标分支 {args.base} HEAD: {target_head[:12]}")

    # 取与源 commits 的 merge-base 作为对比起点
    mb_args = ["merge-base", target_head] + ids
    mb = git_cmd(mb_args, cwd=repo)
    if not mb:
        print(f"[ERROR] 无法计算 {args.base} 与源 commits 的 merge-base。")
        print(f"        可能原因：commit 不存在、目标分支 ref 拼错、或仓库状态异常。")
        sys.exit(1)
    diff_from = mb
    print(f"[INFO] 目标分支相对 merge-base 起点: {diff_from[:12]}")

    conflicts = predict_conflicts(metas, diff_from, target_head, repo)
    conflict_ids = {m["id"] for m, _ in conflicts}
    safe = [m for m in metas if m["id"] not in conflict_ids]

    print()
    print("=" * 60)
    print(f"冲突预测结果（共 {len(metas)} 个 commit）")
    print("=" * 60)

    if safe:
        print(f"\n[OK] 预测可自动 cherry-pick ({len(safe)}):")
        for m in safe:
            print(f"  - {m['id'][:7]}  {m['title']}  ({m['author_date']})")

    if conflicts:
        print(f"\n[WARN] 预测需人工介入 ({len(conflicts)}):")
        for m, reason in conflicts:
            print(f"  - {m['id'][:7]}  {m['title']}")
            print(f"      原因: {reason}")

    print()


def cmd_start(args, repo):
    """派生 MR 分支 + 跑自动 cherry-pick。"""
    assert_clean_working_tree(repo)
    assert_branch_exists(args.base, repo)
    assert_mr_branch_not_exists(args.mr_name, repo)

    if not re.match(r"^[A-Za-z0-9._-]+$", args.mr_name):
        print(f"[ERROR] MR 名称 '{args.mr_name}' 含非法字符，仅允许 [A-Za-z0-9._-]")
        sys.exit(1)

    print(f"[INFO] 解析 {len(args.commits)} 个 commit...")
    ids = resolve_commit_ids(args.commits, repo)
    metas = [get_commit_meta(c, repo) for c in ids]
    metas = sort_commits_by_date(metas)
    print(f"[INFO] 按 author-date 升序排序后：")
    for m in metas:
        print(f"  {m['author_date']}  {m['id'][:7]}  {m['title']}")

    target_head = git_cmd(["rev-parse", "--verify", args.base], cwd=repo) or "HEAD"
    print(f"[INFO] 目标分支 {args.base} HEAD: {target_head[:12]}")

    mb_args = ["merge-base", target_head] + ids
    mb = git_cmd(mb_args, cwd=repo)
    if not mb:
        print(f"[ERROR] 无法计算 {args.base} 与源 commits 的 merge-base。")
        print(f"        可能原因：commit 不存在、目标分支 ref 拼错、或仓库状态异常。")
        sys.exit(1)
    diff_from = mb
    print(f"[INFO] 目标分支相对 merge-base 起点: {diff_from[:12]}")

    print(f"[INFO] 预测冲突...")
    conflicts = predict_conflicts(metas, diff_from, target_head, repo)
    conflict_ids = {m["id"] for m, _ in conflicts}

    state = init_state(args.mr_name, args.base, metas)
    for m, reason in conflicts:
        for c in state["commits"]:
            if c["id"] == m["id"]:
                c["predicted_conflict"] = True
                c["conflict_reason"] = reason
                c["status"] = "manual_required"
                break

    save_state(state, args.mr_name)
    print(f"[INFO] 状态已写入 {state_path(args.mr_name)}")

    print(f"[INFO] 派生 MR 分支: git checkout -b {args.mr_name} {args.base}")
    create_mr_branch(args.mr_name, args.base, repo)

    safe = [m for m in metas if m["id"] not in conflict_ids]
    print(f"[INFO] 开始串行 cherry-pick {len(safe)} 个预测安全的 commit...")

    for m in safe:
        print(f"  -> cherry-pick {m['id'][:7]}  {m['title']}")
        ok, log = do_cherry_pick(m["id"], repo)
        for c in state["commits"]:
            if c["id"] == m["id"]:
                c["cherry_pick_log"] = log
                if ok:
                    c["status"] = "cherry_picked"
                    c["pick_method"] = "auto"
                else:
                    c["status"] = "manual_required"
                    c["conflict_reason"] = f"自动 cherry-pick 失败: {log}"
                break
        save_state(state, args.mr_name)
        if not ok:
            print(f"  [X] 失败，把后续未合的 commit 也归入「需人工」")
            # 剩余未处理的全部标 manual_required
            failed = False
            for c in state["commits"]:
                if c["id"] == m["id"]:
                    failed = True
                    continue
                if failed and c["status"] == "pending":
                    c["status"] = "manual_required"
                    c["conflict_reason"] = "因前序 commit cherry-pick 失败，跳过自动阶段"
            save_state(state, args.mr_name)
            break

    print()
    cmd_status(args, repo)


def cmd_resume(args, repo):
    """跳过已成功项继续。"""
    state = load_state(args.mr_name)
    if not state:
        print(f"[ERROR] 找不到状态文件 {state_path(args.mr_name)}")
        sys.exit(1)

    # 切到 MR 分支
    current = git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    if current != args.mr_name:
        # 拒绝在不干净的树上切
        if git_cmd(["status", "--porcelain"], cwd=repo).strip():
            print(f"[ERROR] 当前分支 '{current}' 有未提交改动，不能切到 '{args.mr_name}'。")
            sys.exit(1)
        git_cmd(["checkout", args.mr_name], cwd=repo)

    pending = [c for c in state["commits"] if c["status"] in ("pending", "manual_required")
               and not c["predicted_conflict"]]
    print(f"[INFO] 还有 {len(pending)} 个未处理的 commit 尝试 cherry-pick...")

    for c in pending:
        print(f"  -> cherry-pick {c['id'][:7]}  {c['title']}")
        ok, log = do_cherry_pick(c["id"], repo)
        c["cherry_pick_log"] = log
        if ok:
            c["status"] = "cherry_picked"
            c["pick_method"] = "auto"
        else:
            c["status"] = "manual_required"
            c["conflict_reason"] = f"自动 cherry-pick 失败: {log}"
        save_state(state, args.mr_name)
        if not ok:
            print(f"  [X] 失败，停止后续自动阶段。")
            break

    cmd_status(args, repo)


def cmd_check(args, repo):
    """人工介入完成后，逐一校验每个 commit 是否到达 MR 分支。"""
    state = load_state(args.mr_name)
    if not state:
        print(f"[ERROR] 找不到状态文件 {state_path(args.mr_name)}")
        sys.exit(1)

    current = git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    if current != args.mr_name:
        print(f"[INFO] 当前在 '{current}'，切换到 '{args.mr_name}' 进行 check。")
        if git_cmd(["status", "--porcelain"], cwd=repo).strip():
            print(f"[ERROR] 当前分支 '{current}' 有未提交改动，不能切到 '{args.mr_name}'。")
            sys.exit(1)
        git_cmd(["checkout", args.mr_name], cwd=repo)

    print(f"[INFO] check 阶段: 校验 {len(state['commits'])} 个 commit...")
    all_ok = True
    for c in state["commits"]:
        present = verify_commit_present(c["id"], repo)
        c["verified_at"] = datetime.now().isoformat(timespec="seconds")
        if present:
            # 记录合入方式：manual_required 的 commit 校验通过 = 人工合入，
            # 保证 report 的「自动 cherry-pick 成功」口径不被人工合入项污染
            if c["status"] == "manual_required":
                c["pick_method"] = "manual"
            else:
                c.setdefault("pick_method", "auto")
            c["status"] = "verified"
            print(f"  [OK]   {c['id'][:7]}  {c['title']}")
        else:
            all_ok = False
            print(f"  [FAIL] {c['id'][:7]}  {c['title']}  -- 未到达 MR 分支")
        save_state(state, args.mr_name)

    print()
    if all_ok:
        print(f"[OK] 全部 {len(state['commits'])} 个 commit 均已到达 MR 分支 '{args.mr_name}'。")
    else:
        print(f"[WARN] 有 commit 未到达，请检查后重新 --resume 或人工介入。")


def cmd_status(args, repo):
    state = load_state(args.mr_name)
    if not state:
        print(f"[ERROR] 找不到状态文件 {state_path(args.mr_name)}")
        sys.exit(1)

    n_total = len(state["commits"])
    n_picked = sum(1 for c in state["commits"] if c["status"] == "cherry_picked")
    n_manual = sum(1 for c in state["commits"] if c["status"] == "manual_required")
    n_verified = sum(1 for c in state["commits"] if c["status"] == "verified")
    n_pending = sum(1 for c in state["commits"] if c["status"] == "pending")

    print("=" * 60)
    print(f"MR 状态: {args.mr_name}  (基线: {state['base_branch']})")
    print("=" * 60)
    print(f"  总数: {n_total}")
    print(f"  [OK]  自动 cherry-pick 成功: {n_picked}")
    print(f"  [OK]  check 阶段已校验: {n_verified}")
    print(f"  [WARN] 需人工介入: {n_manual}")
    print(f"  [TODO] 未处理: {n_pending}")
    print()

    if n_manual:
        print("需人工介入列表：")
        for c in state["commits"]:
            if c["status"] == "manual_required":
                print(f"  - {c['id'][:7]}  {c['title']}")
                if c["conflict_reason"]:
                    print(f"      原因: {c['conflict_reason']}")
        print()
        print(f"切到 MR 分支手动处理: git checkout {args.mr_name}")
        print(f"处理完运行 check: python3 mr_merge.py check --mr-name {args.mr_name}")


def cmd_report(args, repo):
    state = load_state(args.mr_name)
    if not state:
        print(f"[ERROR] 找不到状态文件 {state_path(args.mr_name)}")
        sys.exit(1)

    template = REPORT_TEMPLATE.read_text(encoding="utf-8") if REPORT_TEMPLATE.exists() else _default_template()

    n_total = len(state["commits"])
    # 自动 cherry-pick 成功：仅统计 pick_method=auto 的（人工合入的不算）
    n_picked = [c for c in state["commits"]
                if c["status"] in ("cherry_picked", "verified") and c.get("pick_method") != "manual"]
    # 需人工介入：含尚未解决的 + 已人工合入的（check 后 marked manual）
    n_manual = [c for c in state["commits"]
                if c["status"] == "manual_required"
                or (c["status"] == "verified" and c.get("pick_method") == "manual")]
    n_verified = [c for c in state["commits"] if c["status"] == "verified"]
    n_manual_resolved = [c for c in n_manual if c["status"] == "verified"]

    def fmt_table(rows, headers):
        out = "| " + " | ".join(headers) + " |\n"
        out += "|" + "|".join(["---"] * len(headers)) + "|\n"
        for r in rows:
            out += "| " + " | ".join(str(x) for x in r) + " |\n"
        return out

    picked_rows = [[c["id"][:7], c["title"], c["author_date"], len(c["files_changed"])]
                   for c in n_picked]
    manual_rows = [[c["id"][:7], c["title"], c["conflict_reason"],
                    "已人工合入" if c["status"] == "verified" else "未处理"]
                   for c in n_manual]
    verified_rows = [[c["id"][:7], "verified" if c in n_verified else "pending", "[OK]" if c in n_verified else "[FAIL]"]
                     for c in state["commits"]]

    md = template.format(
        MR_NAME=args.mr_name,
        BASE_BRANCH=state["base_branch"],
        CREATED_AT=state["created_at"],
        UPDATED_AT=state["updated_at"],
        N_TOTAL=n_total,
        N_PICKED=len(n_picked),
        N_MANUAL=len(n_manual),
        N_VERIFIED=len(n_verified),
        N_MANUAL_RESOLVED=len(n_manual_resolved),
        PICKED_TABLE=fmt_table(picked_rows, ["commit", "标题", "author-date", "改动文件数"]) if picked_rows else "_(无)_",
        MANUAL_TABLE=fmt_table(manual_rows, ["commit", "标题", "冲突原因", "处理状态"]) if manual_rows else "_(无)_",
        VERIFIED_TABLE=fmt_table(verified_rows, ["commit", "状态", "MR 分支上是否到达"]) if verified_rows else "_(无)_",
    )

    out = report_path(args.mr_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"[OK] 报告已写入: {out}")


def _default_template():
    return """# MR 合并报告 - {MR_NAME}

## 基本信息
- 目标分支: {BASE_BRANCH}
- 派生时间: {CREATED_AT}
- 最后更新: {UPDATED_AT}
- commit 总数: {N_TOTAL}
- 自动 cherry-pick 成功: {N_PICKED}
- 需人工介入: {N_MANUAL}
- 人工介入已合入: {N_MANUAL_RESOLVED}
- check 阶段已校验: {N_VERIFIED}

## 自动 cherry-pick 成功 / 已校验
{PICKED_TABLE}

## 需人工介入
{MANUAL_TABLE}

## 最终校验
{VERIFIED_TABLE}
"""


# =====================================================================
# CLI 入口
# =====================================================================

def build_parser():
    p = argparse.ArgumentParser(
        prog="mr_merge",
        description="MR 合并 / 批量 cherry-pick 工具（详见 ../SKILL.md）",
    )
    p.add_argument("--repo", default=str(PROJECT_ROOT), help="git 仓库根，默认项目根")
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("analyze", help="只预测冲突，不改分支")
    pa.add_argument("--commits", required=True, nargs="+", help="commit 列表，空格分隔")
    pa.add_argument("--base", default="master", help="目标分支")
    pa.set_defaults(func=cmd_analyze)

    ps = sub.add_parser("start", help="派生 MR 分支 + 跑自动 cherry-pick")
    ps.add_argument("--commits", required=True, nargs="+", help="commit 列表")
    ps.add_argument("--base", default="master", help="目标分支")
    ps.add_argument("--mr-name", required=True, help="MR 标识（同时是分支名和状态目录名）")
    ps.set_defaults(func=cmd_start)

    pr = sub.add_parser("resume", help="跳过已成功项继续")
    pr.add_argument("--mr-name", required=True, help="MR 标识")
    pr.set_defaults(func=cmd_resume)

    pc = sub.add_parser("check", help="人工介入后校验每个 commit 是否完整到达")
    pc.add_argument("--mr-name", required=True, help="MR 标识")
    pc.set_defaults(func=cmd_check)

    pst = sub.add_parser("status", help="打印 MR 当前状态")
    pst.add_argument("--mr-name", required=True, help="MR 标识")
    pst.set_defaults(func=cmd_status)

    prep = sub.add_parser("report", help="输出 markdown 报告到工作区")
    prep.add_argument("--mr-name", required=True, help="MR 标识")
    prep.set_defaults(func=cmd_report)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    repo = args.repo

    # 校验 repo 是 git 仓库
    if not git_cmd(["rev-parse", "--git-dir"], cwd=repo, quiet=True):
        print(f"[ERROR] '{repo}' 不是 git 仓库或无法访问。")
        sys.exit(1)

    # --commits 已经在子 parser 上声明（nargs="+），subcommand 不需要则没有此属性
    if not hasattr(args, "commits"):
        args.commits = []

    args.func(args, repo)


if __name__ == "__main__":
    main()
