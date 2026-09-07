#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_build.py — 增量同步本地改动到远端编译服务器并执行编译/安装

设计原则（相对旧版的重构要点）:
  1. 配置驱动：Config dataclass 统一封装，消除全局变量；支持 DEPLOY_ 环境变量 + --config + --save-config 分级保存
  2. MSYS 路径修复：模块加载时修正 sys.argv（Git Bash/MSYS2 会自动转换 Linux 路径）
  3. CMake 反向依赖图扫描：下载 cmake_target_scan.py 到编译服务器执行，结果驱动精确安装
  4. 安装精确化：按扫描结果按目标分组推送，避免全量覆盖
  5. 连接预检：操作前 ping 编译服务器+目标设备（--test-connection 单独命令）
  6. 配置分离：deploy_config.json（编译服务器）+ device_config.json（目标设备），支持子集保存

用法见同目录 SKILL.md 及各子命令 --help
"""

import argparse
import json
import os
import posixpath
import re
import subprocess
import sys
import time
import paramiko
import signal
from pathlib import Path

# === 终端命令审计埋点（monitor） ===
# 发往编译服务器的命令写入 runtime/terminal-monitor/ops.jsonl，
# 供 nf-terminal-monitor 插件在 DSH Web GUI 实时展示。import 失败不影响主流程。
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "tools"))
    from terminal_audit import record as audit_record
except Exception:
    audit_record = None

# =====================================================================
# I/O 初始化 + MSYS argv 修复（必须在 argparse 之前执行）
# =====================================================================

def _setup_io():
    """强制 UTF-8，兼容 Windows GBK 终端。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _ensure_msys_path():
    """修正 Git Bash/MSYS2 对以 / 开头的 Linux 路径 argv 的自动转换。

    MSYS2 会把 /home/xxx 转成 C:/Program Files/Git/home/xxx。
    此函数在 sys.argv 层面还原，确保 argparse 拿到的就是原始 Linux 路径。
    """
    for i, a in enumerate(sys.argv):
        try:
            raw = os.fsencode(a)
        except (UnicodeEncodeError, OSError):
            continue
        m = re.match(rb"^C:/Program Files/Git(/.*)", raw)
        if not m:
            m = re.match(rb"^C:/Git(/.*)", raw)
        if m:
            sys.argv[i] = m.group(1).decode("utf-8", errors="replace")


_setup_io()
_ensure_msys_path()


# =====================================================================
# 默认配置 & 常量
# =====================================================================

DEFAULT_CONFIG = {
    # ⚠️ 仅编译机地址/端口允许默认值；其余一律不默认，由用户提供或运行时询问补齐。
    "remote_host": "10.66.240.3",
    "remote_port": 50222,
    "remote_user": None,  # 必填：编译服务器用户名（无默认，运行前询问）
    "remote_pass": None,  # 编译服务器密码：支持环境变量 DEPLOY_BUILD_REMOTE_PASS 或 deploy_config.json 明文存储
    "remote_npp_dir": None,  # 必填：远端 NPP 代码仓库基地址（无默认，运行前询问）
    "device_host": None,  # 必填：目标设备地址（无默认，运行前询问）
    "device_port": None,  # 必填：目标设备 SSH 端口（无默认，运行前询问）
    "device_user": None,  # 必填：目标设备用户名（无默认，运行前询问）
    "device_pass": None,  # 设备密码：支持环境变量 DEPLOY_BUILD_DEVICE_PASS 或 device_config.json 明文存储
    # device_plugin_dir / device_vpp_bin_dir / device_lib_dir 已删除：
    # install 通过 edisk 相对路径映射（nsfocus/→/opt/nsfocus、root/→/root），从不消费这三个字段。
    "nsbuild_build_dir": None,  # 派生 ${remote_npp_dir}/nf/.nsbuild/build
    "nsbuild_install_dir": None,  # 派生 ${remote_npp_dir}/nf/.nsbuild/install/edisk
    "base_branch": None,  # 无默认：优先读本地 npp 分支（resolve_local_base），读不到则询问用户
    "restart_service": None,  # 无默认：设备重启服务名（运行前询问）
}

# DEPLOY_BUILD_<KEY> 环境变量映射
ENV_PREFIX = "DEPLOY_BUILD_"
ENV_KEYS = {
    "remote_host": "REMOTE_HOST",
    "remote_port": "REMOTE_PORT",
    "remote_user": "REMOTE_USER",
    "remote_pass": "REMOTE_PASS",
    "remote_npp_dir": "REMOTE_NPP_DIR",
    "device_host": "DEVICE_HOST",
    "device_port": "DEVICE_PORT",
    "device_user": "DEVICE_USER",
    "device_pass": "DEVICE_PASS",
    "base_branch": "BASE_BRANCH",
    "restart_service": "RESTART_SERVICE",
}

# 需要做 MSYS 路径还原的字段（Linux 远端/设备路径，不应被转换）
MSYS_PATH_FIELDS = [
    "remote_npp_dir",
    "nsbuild_build_dir",
    "nsbuild_install_dir",
]

# 同步时排除的文件/目录（路径段精确匹配）
EXCLUDE_PATTERNS = [
    ".git", ".gitignore", ".dsh", ".cursor", ".vscode", ".gitnexus",
    "node_modules", "build", "build-root", "build-data", "doxygen",
    "docs", "test", "unused", "release", "deploy_build.py",
    ".deploy_sync_manifest.json", "deploy_logs",
]

MSYS_PREFIX_RE = re.compile(r"^C:/Program Files/Git(/.*)")


# =====================================================================
# 路径工具
# =====================================================================

def fix_msys_path(path):
    """还原被 Git Bash MSYS2 自动转换的 Linux 路径。"""
    if not path:
        return path
    m = MSYS_PREFIX_RE.match(path)
    if m:
        return m.group(1)
    m2 = re.match(r"^C:/Git(/.*)", path)
    if m2:
        return m2.group(1)
    return path


def shq(s):
    """单引号包裹 shell 字符串, 转义内部单引号, 防止密码含特殊字符破坏命令。"""
    return "'" + str(s).replace("'", "'\\''") + "'"


def fix_msys_dict(d, fields):
    """原地修正字典中被 MSYS 转换的路径字段。"""
    for f in fields:
        if f in d and d[f]:
            d[f] = fix_msys_path(d[f])


def is_excluded(filepath):
    """检查文件路径是否应被排除。"""
    parts = filepath.split("/")
    for pat in EXCLUDE_PATTERNS:
        if pat in parts:
            return True
        if filepath == pat:
            return True
    return False


# =====================================================================
# 全局路径（基于当前工作目录而非脚本目录）
# =====================================================================

# ⚠️ LOCAL_NPP_DIR = 本地 NPP 代码仓库根目录（filesync 源），默认取 cwd；
# 与 env_config 配置目录（固定 AGENT_ASSETS_DIR）相互独立，互不依赖。
LOCAL_NPP_DIR = os.getcwd()
# env_config 创建基准目录固定为 AGENT_ASSETS_DIR，不再随 cwd（NPP 代码目录）漂移。
# 约定：全部运行时中间产物（config / sync 清单 / 日志）统一落到
#   E:\agent_assets\.dsh\env_config\<skill>\    （AGENT_ASSETS_DIR 环境变量可覆盖）
# 改动原因：原实现基于 LOCAL_NPP_DIR=os.getcwd() 叠加 .dsh/env_config，
# 在 NPP 仓库或 worktree 目录下运行会把配置写到代码仓库里，污染仓库。
AGENT_ASSETS_DIR = os.environ.get("AGENT_ASSETS_DIR") or r"E:\agent_assets"
ENV_CONFIG_DIR = os.path.join(AGENT_ASSETS_DIR, ".dsh", "env_config", "deploy_build")
DEPLOY_DIR = ENV_CONFIG_DIR  # 兼容历史引用
CONFIG_FILE = os.path.join(ENV_CONFIG_DIR, "deploy_config.json")
DEVICE_CONFIG_FILE = os.path.join(ENV_CONFIG_DIR, "device_config.json")
SYNC_MANIFEST = os.path.join(ENV_CONFIG_DIR, "sync_manifest.json")
LOG_DIR = os.path.join(ENV_CONFIG_DIR, "logs")
SCAN_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cmake_target_scan.py")


# =====================================================================
# Config dataclass — 消除全局变量
# =====================================================================

class Config:
    """编译服务器 + 目标设备配置的统一封装。"""

    def __init__(self):
        self.remote_host = DEFAULT_CONFIG["remote_host"]
        self.remote_port = DEFAULT_CONFIG["remote_port"]
        self.remote_user = DEFAULT_CONFIG["remote_user"]
        self.remote_pass = DEFAULT_CONFIG["remote_pass"]
        self.remote_npp_dir = DEFAULT_CONFIG["remote_npp_dir"]
        self.device_host = DEFAULT_CONFIG["device_host"]
        self.device_port = DEFAULT_CONFIG["device_port"]
        self.device_user = DEFAULT_CONFIG["device_user"]
        self.device_pass = DEFAULT_CONFIG["device_pass"]
        self.base_branch = DEFAULT_CONFIG["base_branch"]
        self.restart_service = DEFAULT_CONFIG["restart_service"]
        self.devices = []  # [{desc, host, port, user}, ...] 多设备列表
        self.nsbuild_build_dir = None
        self.nsbuild_install_dir = None

    # ---------- 派生路径 ----------
    @property
    def nsbuild_base(self):
        # remote_npp_dir 缺失时（from_raw 阶段尚未补齐）返回 None，派生路径留待补齐后重算
        if not self.remote_npp_dir:
            return None
        return posixpath.join(self.remote_npp_dir, "nf", ".nsbuild")

    def ensure_nsbuild_paths(self):
        if not self.nsbuild_base:
            return
        if not self.nsbuild_build_dir:
            self.nsbuild_build_dir = posixpath.join(self.nsbuild_base, "build")
        if not self.nsbuild_install_dir:
            self.nsbuild_install_dir = posixpath.join(self.nsbuild_base, "install", "edisk")

    def use_worktree(self, name):
        """切换到 worktree 目录（NPP_BASE 的兄弟目录），并重置 nsbuild 派生路径。

        设计: 在编译机 npp 目录 `git worktree add ../{name}`，产物/扫描/编译
        均在 worktree 目录内进行，与原 npp 仓库隔离。
        """
        parent = posixpath.dirname(self.remote_npp_dir)
        self.remote_npp_dir = posixpath.join(parent, name)
        self.nsbuild_build_dir = None
        self.nsbuild_install_dir = None
        self.ensure_nsbuild_paths()

    @property
    def device_list(self):
        """目标设备列表 [{desc, host, port, user}]，兼容旧单设备配置。"""
        if self.devices:
            return self.devices
        if self.device_host:
            return [{
                "desc": "NF-1",
                "host": self.device_host,
                "port": self.device_port,
                "user": self.device_user,
            }]
        return []

    @property
    def scan_script_remote(self):
        # remote_npp_dir 缺失时（零配置 dry-run / 补齐前）返回 None，避免 TypeError
        if not self.remote_npp_dir:
            return None
        return posixpath.join(self.remote_npp_dir, "nf", "cmake_target_scan.py")

    @property
    def nf_dir(self):
        if not self.remote_npp_dir:
            return None
        return posixpath.join(self.remote_npp_dir, "nf")

    @property
    def build_root(self):
        if not self.remote_npp_dir:
            return None
        return f"{self.remote_npp_dir}/build-root/install-x86_64/vpp"

    # ---------- 加载 ----------
    @classmethod
    def load(cls, args=None):
        """三级加载：默认值 → 配置文件 → 环境变量 → 命令行参数（后者覆盖前者）。"""
        raw = dict(DEFAULT_CONFIG)

        # 1) 配置文件（deploy_config + device_config + --config 指定文件）
        config_paths = [CONFIG_FILE, DEVICE_CONFIG_FILE]
        if args and args.config:
            config_paths.append(args.config)
        for path in config_paths:
            if path and os.path.isfile(path):
                try:
                    with open(path, "r") as f:
                        saved = json.load(f)
                    fix_msys_dict(saved, MSYS_PATH_FIELDS)
                    raw.update(saved)
                except (json.JSONDecodeError, IOError):
                    pass

        # 2) 环境变量
        for key, env_name in ENV_KEYS.items():
            val = os.environ.get(ENV_PREFIX + env_name)
            if val:
                raw[key] = val

        # 3) 命令行参数
        if args:
            cli_map = {
                "remote_host": args.remote_host,
                "remote_port": args.remote_port,
                "remote_user": args.remote_user,
                "remote_npp_dir": args.remote_dir,
                "device_host": args.device_host,
                "device_port": args.device_port,
                "device_user": args.device_user,
                "base_branch": args.base,
            }
            for k, v in cli_map.items():
                # 空串视为未提供（如 --remote-user ""），不覆盖配置值，留给 prompt_missing 询问
                if v is not None and v != "":
                    raw[k] = v

        return cls.from_raw(raw)

    @classmethod
    def from_raw(cls, raw):
        fix_msys_dict(raw, MSYS_PATH_FIELDS)
        # 仅编译机地址/端口有默认；其余字段缺省保留 None，由 prompt_missing() 运行前补齐。
        raw.setdefault("remote_host", DEFAULT_CONFIG["remote_host"])
        raw.setdefault("remote_port", DEFAULT_CONFIG["remote_port"])
        cfg = cls()
        cfg.remote_host = raw["remote_host"]
        cfg.remote_port = int(raw["remote_port"])
        cfg.remote_user = raw.get("remote_user")
        cfg.remote_pass = raw.get("remote_pass")
        cfg.remote_npp_dir = raw.get("remote_npp_dir")
        cfg.device_host = raw.get("device_host")
        cfg.device_port = raw.get("device_port")
        cfg.device_user = raw.get("device_user")
        cfg.device_pass = raw.get("device_pass")
        cfg.base_branch = raw.get("base_branch")
        cfg.restart_service = raw.get("restart_service")
        # 多设备解析: device_config.json 顶层 devices 数组; 兼容旧单设备字段
        # 设备字段缺失时保留 None，由 prompt_missing() 运行前补齐（int(None) 会在补齐前崩溃）。
        cfg.devices = raw.get("devices") or []
        if not cfg.devices and raw.get("device_host"):
            cfg.devices = [{
                "desc": "NF-1",
                "host": raw["device_host"],
                "port": int(raw["device_port"]) if raw.get("device_port") else None,
                "user": raw["device_user"],
            }]
        # 默认设备(兼容单设备操作): 取第一台
        if cfg.devices:
            cfg.device_host = cfg.devices[0].get("host")
            cfg.device_port = cfg.devices[0].get("port")
            cfg.device_user = cfg.devices[0].get("user")
            # 设备密码支持从 device_config.json 的 devices[].pass 明文读取
            if not cfg.device_pass:
                cfg.device_pass = cfg.devices[0].get("pass") or cfg.devices[0].get("device_pass")
        # nsbuild_* 为派生路径: 仅当与当前 remote_npp_dir 派生一致才采纳, 否则置 None 重算
        # (防旧配置残留 worktree 专属路径污染非 worktree 运行)
        # remote_npp_dir 缺失时（尚未补齐）跳过派生校验，留待 prompt_missing 后重算
        cfg.nsbuild_build_dir = raw.get("nsbuild_build_dir")
        cfg.nsbuild_install_dir = raw.get("nsbuild_install_dir")
        if cfg.nsbuild_base:
            expected_build = posixpath.join(cfg.nsbuild_base, "build")
            expected_install = posixpath.join(cfg.nsbuild_base, "install", "edisk")
            if cfg.nsbuild_build_dir != expected_build:
                cfg.nsbuild_build_dir = None
            if cfg.nsbuild_install_dir != expected_install:
                cfg.nsbuild_install_dir = None
        cfg.ensure_nsbuild_paths()
        return cfg

    # ---------- 保存 ----------

    def to_deploy_dict(self):
        # nsbuild_* 目录是纯派生值(由 remote_npp_dir 推导), 不持久化,
        # 避免 worktree 会话后把 worktree 专属路径写入配置污染下次非 worktree 运行
        return {
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "remote_user": self.remote_user,
            "remote_pass": self.remote_pass,
            "remote_npp_dir": self.remote_npp_dir,
            "base_branch": self.base_branch,
            "restart_service": self.restart_service,
        }

    def to_device_dict(self):
        devs = []
        for d in (self.devices or []):
            dev = {"desc": d.get("desc"), "host": d.get("host"), "port": d.get("port"), "user": d.get("user")}
            if d.get("pass"):
                dev["pass"] = d.get("pass")
            elif d.get("device_pass"):
                dev["pass"] = d.get("device_pass")
            elif self.device_pass:
                dev["pass"] = self.device_pass
            devs.append(dev)
        return {"devices": devs}

    def save(self, kind):
        """保存配置。kind: all / deploy / device"""
        os.makedirs(DEPLOY_DIR, exist_ok=True)

        if kind == "deploy":
            self._write_file(CONFIG_FILE, self.to_deploy_dict())
            print(f"[CONFIG] 配置已保存到 {CONFIG_FILE}")
            return

        if kind == "device":
            self._write_file(DEVICE_CONFIG_FILE, self.to_device_dict())
            print(f"[CONFIG] 配置已保存到 {DEVICE_CONFIG_FILE}")
            return

        # kind == "all"
        self._write_file(CONFIG_FILE, self.to_deploy_dict())
        self._write_file(DEVICE_CONFIG_FILE, self.to_device_dict())
        print(f"[CONFIG] 配置已保存: {CONFIG_FILE} + {DEVICE_CONFIG_FILE}")

    @staticmethod
    def _write_file(path, data):
        fix_msys_dict(data, MSYS_PATH_FIELDS)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def prompt_missing(cfg, need_device=False):
    """运行前交互补齐缺失的连接参数。

    规则：仅编译机地址/端口允许默认；其余字段缺失时逐个向用户询问，
    绝不带默认值继续跑。returns cfg（原地补齐）。
    """
    # 基础必填：编译机用户名 + NPP_BASE。restart_service 仅 install 路径消费，
    # 由 need_device 分支询问；纯编译/同步/状态等操作不询问服务名。
    prompts = [
        ("remote_user", "编译服务器用户名"),
        ("remote_npp_dir", "远端 NPP 代码仓库基地址"),
    ]
    if need_device:
        prompts = [
            ("remote_user", "编译服务器用户名"),
            ("remote_npp_dir", "远端 NPP 代码仓库基地址"),
            ("device_host", "目标设备地址"),
            ("device_port", "目标设备 SSH 端口"),
            ("device_user", "目标设备用户名"),
            ("restart_service", "设备重启服务名"),
        ]

    def _ask(label):
        try:
            return input(f"请输入{label}: ").strip()
        except EOFError:
            # 非交互（agent 经 Bash 调用、stdin 非 TTY）时不能裸崩：
            # 打印缺失字段清单后退出，由调用方补全参数或改用配置文件。
            print(f"[ERROR] 缺少必要参数：{label}（非交互环境无法询问）", file=sys.stderr)
            sys.exit(2)

    for attr, label in prompts:
        cur = getattr(cfg, attr)
        if cur:
            continue
        val = _ask(label)
        if not val:
            # 空输入视为未提供，循环重询（防用户回车得到空串继续跑）
            print(f"[WARN] {label} 不能为空，请重新输入。")
            while not val:
                val = _ask(label)
        setattr(cfg, attr, val)
        if attr == "device_port":
            try:
                cfg.device_port = int(val)
            except ValueError:
                print(f"[ERROR] 设备端口必须是数字: {val}")
                sys.exit(2)
    # base_branch 特殊：本地分支优先（resolve_local_base），读不到则询问
    if not cfg.base_branch:
        local = resolve_local_base()
        if local:
            cfg.base_branch = local
            print(f"[CONFIG] 基线分支(本地读取): {local}")
        else:
            cfg.base_branch = _ask("基线分支（worktree 派生基准）")
            while not cfg.base_branch:
                cfg.base_branch = _ask("基线分支（worktree 派生基准）")
    # 补齐 remote_npp_dir 后必须重算 nsbuild 派生路径（from_raw 阶段可能被跳过）
    cfg.ensure_nsbuild_paths()
    return cfg


# =====================================================================
# Logger — 同时输出到终端和日志文件
# =====================================================================

class Logger:
    def __init__(self, log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.terminal = sys.stdout
        self.terminal_err = sys.stderr
        self.log = open(log_path, "w", encoding="utf-8")

    def write(self, message):
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="replace")
        self.log.write(message)
        self.log.flush()
        try:
            self.terminal.write(message)
        except UnicodeEncodeError:
            enc = self.terminal.encoding or "utf-8"
            self.terminal.write(
                message.encode(enc, errors="replace").decode(enc, errors="replace")
            )

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        try:
            self.log.close()
        except Exception:
            pass


# =====================================================================
# Git 操作
# =====================================================================

def git_cmd(args, cwd=None, quiet=False):
    """执行 git 命令，失败时打印错误并返回空字符串。

    Windows 下 subprocess 默认按 GBK 解码 git 的 UTF-8 输出，遇到中文文件名
    （如"搜索结果"）会抛 UnicodeDecodeError，因此显式指定 UTF-8 并容忍非法字节。
    quiet=True 时失败不打印错误（用于探测类命令）。
    """
    cwd = cwd or LOCAL_NPP_DIR
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        if not quiet:
            print(f"[ERROR] git {' '.join(args)}: {result.stderr}")
        return ""
    return result.stdout.strip()


def resolve_local_base():
    """从用户指定的本地工作目录解析默认基线。

    优先取当前分支的上游(upstream)，否则取与 origin/master 或 master 的
    merge-base —— 即本分支相对主干的共同祖先。返回 commit 哈希字符串；
    本地不是 git 仓库或无法解析时返回 None。
    """
    branch = git_cmd(["rev-parse", "--abbrev-ref", "HEAD"])
    if not branch or branch == "HEAD":
        return None
    refs = []
    # 先探测上游是否配置，避免无上游分支时 git 报错
    up = git_cmd(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], quiet=True)
    if up:
        refs.append("@{upstream}")
    refs.extend(["origin/master", "master"])
    for ref in refs:
        mb = git_cmd(["merge-base", branch, ref])
        if mb:
            return mb
    return None


def get_changed_files(cfg, base_branch=None):
    """获取相对基线的改动文件列表。返回 (files, deletes, untracked_list)。"""
    base = base_branch or cfg.base_branch
    verify = git_cmd(["rev-parse", "--verify", base], quiet=True)
    if not verify:
        print(f"[ERROR] 基线 '{base}' 无效或不存在, 请用 --base 指定正确的分支/commit。")
        sys.exit(1)

    output = git_cmd(["diff", "--name-status", base, "HEAD"])
    files, deletes = [], []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) < 2:
            continue
        status = parts[0].strip()[0]
        fp = parts[1].strip()
        if is_excluded(fp):
            continue
        (deletes if status == "D" else files).append(fp)

    # 未提交的已跟踪改动
    uncommitted = git_cmd(["diff", "--name-only", "HEAD"])
    for f in uncommitted.splitlines():
        f = f.strip()
        if f and not is_excluded(f) and f not in files:
            files.append(f)

    # 未跟踪文件
    untracked = git_cmd(["ls-files", "--others", "--exclude-standard"])
    untracked_list = []
    for f in untracked.splitlines():
        f = f.strip()
        if f and not is_excluded(f):
            files.append(f)
            untracked_list.append(f)

    # 上次同步过的未跟踪文件若本地已删除
    prev = load_manifest()
    for f in prev.get("untracked_files", []):
        if not os.path.exists(os.path.join(LOCAL_NPP_DIR, f)) and f not in untracked_list and f not in deletes:
            deletes.append(f)

    return files, deletes, untracked_list


def load_manifest():
    if os.path.exists(SYNC_MANIFEST):
        try:
            with open(SYNC_MANIFEST, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_manifest(untracked_files):
    os.makedirs(os.path.dirname(SYNC_MANIFEST), exist_ok=True)
    with open(SYNC_MANIFEST, "w") as f:
        json.dump({"untracked_files": untracked_files}, f, indent=2)


# =====================================================================
# SSH 操作
# =====================================================================

_INTERRUPT_REQUESTED = False
# 终端命令审计上下文：main() 建立连接后写入（host/port/user），ssh_exec 读取
_AUDIT_CTX = {}


def _set_interrupt():
    global _INTERRUPT_REQUESTED
    _INTERRUPT_REQUESTED = True
    print("\n[INTERRUPT] Ctrl+C detected, requesting termination...")


def _check_interrupt():
    if _INTERRUPT_REQUESTED:
        raise KeyboardInterrupt("Operation interrupted by user")


def ssh_connect(cfg):
    """连接到编译服务器。"""
    global _AUDIT_CTX
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(cfg.remote_host, port=cfg.remote_port, username=cfg.remote_user,
                password=cfg.remote_pass, timeout=15)
    transport = ssh.get_transport()
    if transport:
        transport.set_keepalive(5)
    # 终端命令审计上下文：本次连接的三元组，供 ssh_exec 埋点
    _AUDIT_CTX = {"host": cfg.remote_host, "port": cfg.remote_port,
                  "user": cfg.remote_user}
    return ssh


def ssh_exec(ssh, cmd, timeout=300, audit_ctx=None):
    """执行远端命令，实时输出，支持 Ctrl+C 终止。返回 (exit_code, stdout, stderr)。

    读取用 channel.recv()（非阻塞，返回当前可用数据）而非 stream.read()（阻塞，
    会等满 nbytes 或 EOF——命令退出后剩余数据不足 4096 字节时会永久阻塞，导致
    编译成功但脚本卡死不退出）。退出判定兼顾 exit_status 与 EOF。
    audit_ctx: {host, port, user}，供终端命令审计埋点；缺省时回退模块级 _AUDIT_CTX。
    """
    global _INTERRUPT_REQUESTED
    _INTERRUPT_REQUESTED = False
    print(f"[REMOTE] {cmd}")
    audit_meta = audit_ctx or _AUDIT_CTX or {}

    transport = ssh.get_transport()
    if transport:
        transport.set_keepalive(5)

    _audit_start = time.monotonic()
    def _audit_done(exit_code, timed_out=False, error=None):
        if audit_record is not None and audit_meta.get("host"):
            audit_record(host=audit_meta["host"], port=audit_meta.get("port"),
                         user=audit_meta.get("user"), cmd=cmd, mode="deploy",
                         result={"exit": exit_code, "dur": time.monotonic() - _audit_start,
                                 "timed_out": timed_out, "error": error})

    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=timeout)
    channel = stdout.channel
    out_lines, err_lines = [], []
    start = time.time()

    def _drain(stream, is_stdout=True):
        """非阻塞排空 channel 当前可用数据到行缓冲。"""
        try:
            while stream.channel.recv_ready():
                data = stream.channel.recv(4096)
                if not data:
                    break
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                (out_lines if is_stdout else err_lines).append(data)
                target = sys.stdout if is_stdout else sys.stderr
                try:
                    target.write(data if is_stdout else f"[STDERR] {data}")
                    target.flush()
                except UnicodeEncodeError:
                    pass
        except Exception:
            pass

    while True:
        _check_interrupt()
        elapsed = time.time() - start
        if timeout and elapsed > timeout:
            print(f"[TIMEOUT] Command timed out after {timeout}s")
            # 尝试向远端进程发 SIGTERM，避免僵尸进程残留
            try:
                channel.send_signal("TERM")  # 远端进程终止信号
            except Exception:
                pass
            # 等待远端进程响应终止信号
            try:
                channel.recv_exit_status()
            except Exception:
                pass
            channel.close()
            _audit_done(-1, timed_out=True, error=f"timed out after {timeout}s")
            return -1, "".join(out_lines), "".join(err_lines)

        _drain(stdout, True)
        _drain(stderr, False)

        # 退出条件：收到 exit_status 或 channel EOF（两者任一即可，避免
        # exit_status 迟迟不到而脚本空转）
        if channel.exit_status_ready() or channel.eof_received:
            # 退出后再排空一次，确保余下数据不丢
            _drain(stdout, True)
            _drain(stderr, False)
            break
        time.sleep(0.05)

    try:
        channel.recv_exit_status()
        exit_code = channel.exit_status
    except Exception:
        exit_code = -1

    _audit_done(exit_code, timed_out=False, error=None)
    return exit_code, "".join(out_lines), "".join(err_lines)


def sftp_put(ssh, local_path, remote_path):
    """通过 SFTP 上传文件，自动创建远端目录。"""
    sftp = ssh.open_sftp()
    try:
        remote_dir = posixpath.dirname(remote_path)
        _ensure_remote_dir(sftp, remote_dir)
        sftp.put(local_path, remote_path)
    finally:
        sftp.close()


def sftp_read(ssh, remote_path):
    """通过 SFTP 读取远端文件内容。"""
    sftp = ssh.open_sftp()
    try:
        with sftp.file(remote_path, "r") as f:
            return f.read()
    finally:
        sftp.close()


def _ensure_remote_dir(sftp, remote_dir):
    """递归创建远端目录（已存在的跳过）。绝对路径首段为空串, 跳过避免 stat('')/mkdir('') ENOENT。"""
    parts = remote_dir.split("/")
    for i in range(1, len(parts) + 1):
        cur = "/".join(parts[:i])
        if not cur:
            continue
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)


# =====================================================================
# 文件同步
# =====================================================================

def sync_files(ssh, cfg, files, deletes):
    """同步改动文件到远端编译服务器。"""
    sftp = None
    try:
        sftp = ssh.open_sftp()
        deleted_dirs = []

        for f in deletes:
            rp = posixpath.join(cfg.remote_npp_dir, f)
            try:
                sftp.remove(rp)
                print(f"  [DEL] {f}")
                deleted_dirs.append(posixpath.dirname(rp))
            except IOError:
                print(f"  [DEL-SKIP] {f} (not found on remote)")

        for f in files:
            lp = os.path.join(LOCAL_NPP_DIR, f)
            rp = posixpath.join(cfg.remote_npp_dir, f)
            if not os.path.isfile(lp):
                print(f"  [SKIP] {f} (local file not found)")
                continue
            rd = posixpath.dirname(rp)
            try:
                sftp.stat(rd)
            except IOError:
                parts = rd.split("/")
                npp_parts = cfg.remote_npp_dir.split("/")
                for i in range(len(npp_parts), len(parts) + 1):
                    try:
                        sftp.stat("/".join(parts[:i]))
                    except IOError:
                        sftp.mkdir("/".join(parts[:i]))
                        print(f"  [MKDIR] {'/'.join(parts[:i])}")
            sftp.put(lp, rp)
            print(f"  [SYNC] {f}")

        # 清理空目录
        for d in deleted_dirs:
            try:
                sftp.remove(os.path.join(d, "__sentinel__"))
            except Exception:
                try:
                    sftp.rmdir(d)
                    print(f"  [RMDIR] {d}")
                except IOError:
                    pass
    finally:
        if sftp:
            sftp.close()

    print(f"\n[SUMMARY] synced {len(files)} files, deleted {len(deletes)} files")


# =====================================================================
# worktree 派生(设计步骤 2-4: 切分支 → git worktree add → 进入 worktree)
# =====================================================================

# state_machine.py 的相对定位（本脚本目录/deploy-build → skills/ → bug-fix-workflow/）
STATE_MACHINE_REL = Path(__file__).resolve().parent.parent / "bug-fix-workflow" / "state_machine.py"


def register_worktree_to_state(worktree_name: str, wt_path: str, base_branch: str) -> None:
    """worktree 派生成功后，向 BUG 状态机登记（gates.worktree_ready 置位）。

    规则：worktree 名形如 fix-NEWNF-XXXXX 时，自动把派生结果登记到
    bug-fix-state/NEWNF-XXXXX/state.json；登记成功即置位 worktree_ready，
    使「advance → 编码」门禁可过。非 BUG 格式名称（bd_<任务名> 等）跳过登记。
    """
    m = re.match(r"^fix-(NEWNF-\d+)$", worktree_name)
    if not m:
        print(f"[WT-REGISTER] worktree 名 {worktree_name} 非 fix-NEWNF-XXXXX 格式，跳过状态机登记")
        return
    bug_id = m.group(1)
    sm = STATE_MACHINE_REL
    if not sm.is_file():
        print(f"[WT-REGISTER] state_machine.py 不存在：{sm}，跳过登记")
        return
    cmd = [
        sys.executable, str(sm),
        "worktree-set",
        "--bug-id", bug_id,
        "--name", worktree_name,
        "--remote-dir", wt_path,
        "--base-branch", base_branch or "",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        if r.returncode == 0:
            print(f"[WT-REGISTER] 已登记到 {bug_id} 状态机（gates.worktree_ready=True）")
        else:
            print(f"[WT-REGISTER] 登记失败（可能状态机未 init）：{(r.stderr or '').strip()}")
    except Exception as e:  # 登记失败不影响 worktree 派生主流程
        print(f"[WT-REGISTER] 登记异常（忽略）：{e}")


def prepare_worktree(ssh, cfg, worktree_name, base_branch):
    """在编译机上基于 NPP_BASE 派生 worktree 工作区。

    流程:
      1. npp 仓库切到基线分支(如 master)
      2. 若 worktree 不存在: git worktree add -b <name> ../<name> <base>
      3. 若已存在: 直接复用
    返回 worktree 绝对路径。
    """
    base_dir = cfg.remote_npp_dir
    parent = posixpath.dirname(base_dir)
    wt_path = posixpath.join(parent, worktree_name)
    print(f"[WORKTREE] 基仓库: {base_dir}")
    print(f"[WORKTREE] 目标工作区: {wt_path}")

    # 1) 基仓库切到基线分支(确保派生基于最新基线)
    code, out, err = ssh_exec(
        ssh, f"cd {base_dir} && git checkout {base_branch} 2>&1", timeout=60)
    if code != 0:
        print(f"[WORKTREE-WARN] checkout {base_branch} 失败, 将继续尝试 worktree 派生: {out}")

    # 2) 检查 worktree 是否已存在
    code, out, _ = ssh_exec(
        ssh,
        f"cd {base_dir} && git worktree list --porcelain | grep '^worktree ' | grep -Fq '{wt_path}' "
        f"&& echo WT_EXISTS || echo WT_ABSENT",
        timeout=30)
    if "WT_EXISTS" in out:
        print(f"[WORKTREE] 已存在, 直接复用: {wt_path}")
        # 复用同样登记（幂等）：确保 worktree_ready 置位，门禁可过
        register_worktree_to_state(worktree_name, wt_path, base_branch)
        return wt_path

    # 3) 派生: 同名分支已存在则直接 add, 否则基于基线新建同名分支
    code, out, _ = ssh_exec(
        ssh,
        f"cd {base_dir} && git show-ref --verify --quiet refs/heads/{worktree_name} "
        f"&& echo BR_EXISTS || echo BR_ABSENT",
        timeout=30)
    if "BR_EXISTS" in out:
        add_cmd = f"git worktree add ../{worktree_name} {worktree_name}"
    else:
        add_cmd = f"git worktree add -b {worktree_name} ../{worktree_name} {base_branch}"
    code, out, err = ssh_exec(ssh, f"cd {base_dir} && {add_cmd}", timeout=120)
    if code != 0:
        raise RuntimeError(f"[WORKTREE] 派生失败: {out} {err}")
    print(f"[WORKTREE] 已派生: {wt_path}")
    # 派生成功 → 自动登记到 BUG 状态机（置位 worktree_ready，门禁可过）
    register_worktree_to_state(worktree_name, wt_path, base_branch)
    return wt_path


# =====================================================================
# CMake 反向依赖图扫描
# =====================================================================

def _upload_scan_script(ssh, cfg):
    """将 cmake_target_scan.py 上传到编译服务器。"""
    if not os.path.isfile(SCAN_SCRIPT):
        raise FileNotFoundError(f"扫描脚本不存在: {SCAN_SCRIPT}")
    sftp_put(ssh, SCAN_SCRIPT, cfg.scan_script_remote)
    print(f"[SCAN] 已上传 cmake_target_scan.py → {cfg.scan_script_remote}")


def run_cmake_scan(ssh, cfg, files):
    """在编译服务器执行 cmake_target_scan.py，返回解析后的 JSON dict。

    流程:
      1. 上传扫描脚本
      2. 远端执行 python3 cmake_target_scan.py --build-dir ... --install-dir ... --changed-files ...
      3. 解析 stdout 中的 JSON 输出
    """
    cfg.ensure_nsbuild_paths()
    _upload_scan_script(ssh, cfg)

    file_args = " ".join(f"'{f}'" for f in files)
    cmd = (
        f"python3 {cfg.scan_script_remote} "
        f"--build-dir '{cfg.nsbuild_build_dir}' "
        f"--install-dir '{cfg.nsbuild_install_dir}' "
        f"--changed-files {file_args}"
    )

    print(f"[SCAN] 执行 CMake 反向依赖图扫描...")
    exit_code, out, err = ssh_exec(ssh, cmd, timeout=300)
    if exit_code != 0:
        print(f"[SCAN-ERROR] cmake_target_scan 失败 (exit={exit_code})")
        return None

    out_clean = out.strip()
    # stdout 应为纯 JSON（stderr 走独立通道）
    result = _parse_json(out_clean)
    if result is None:
        print(f"[SCAN-ERROR] 无法解析扫描输出 JSON")
        print(f"[SCAN-DEBUG] stdout 前 500 字符: {out_clean[:500]}")
        return None

    summary = result.get("summary", {})
    print(f"[SCAN] 受影响目标 {summary.get('affected_count', '?')} 个, 安装产物 {summary.get('artifact_count', '?')} 个")
    return result


def _parse_json(text):
    """鲁棒地解析 JSON，处理可能的污染。"""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试截取最外层 {} 块
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


# =====================================================================
# 安装脚本生成 & 执行
# =====================================================================

def edisk_rel_to_device(rel):
    """edisk 相对路径 → 设备绝对路径。

    edisk 镜像设备根文件系统(设计步骤8):
      nsfocus/ 前缀 → /opt/nsfocus/
      root/    前缀 → /root/
    无法映射时返回 None。
    """
    rel = rel.lstrip("/")
    if rel.startswith("nsfocus/"):
        return posixpath.join("/opt/nsfocus", rel[len("nsfocus/"):])
    if rel.startswith("root/"):
        return posixpath.join("/root", rel[len("root/"):])
    return None


def list_edisk_files(ssh, cfg):
    """列出 edisk 下所有文件(相对路径列表)。"""
    code, out, err = ssh_exec(
        ssh, f"cd {cfg.nsbuild_install_dir} && find . -type f 2>/dev/null", timeout=60)
    rels = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line == ".":
            continue
        rel = line[2:] if line.startswith("./") else line.lstrip("/")
        if rel:
            rels.append(rel)
    return rels


def find_edisk_file(ssh, cfg, filename):
    """在 edisk 中按文件名递归查找, 返回第一个匹配的相对路径。"""
    code, out, err = ssh_exec(
        ssh,
        f"cd {cfg.nsbuild_install_dir} && find . -name {shq(filename)} -type f 2>/dev/null | head -1",
        timeout=30)
    line = out.strip()
    if not line:
        return None
    return line[2:] if line.startswith("./") else line.lstrip("/")


def collect_install_entries(ssh, cfg, scan_result=None, files=None, install_full=False):
    """组装 [(edisk_rel, device_abs)] 安装条目。

    优先级: 全量 > 指定文件 > CMake 扫描精确结果。
    未命中 nsfocus/root 前缀的 rel 跳过并告警。
    """
    entries = []

    def _add(rel):
        abs_path = edisk_rel_to_device(rel)
        if abs_path:
            entries.append((rel, abs_path))
        else:
            print(f"[INSTALL] 跳过未映射路径(非 nsfocus/root 前缀): {rel}")

    if install_full:
        for rel in list_edisk_files(ssh, cfg):
            _add(rel)
    elif files:
        for fn in files:
            rel = find_edisk_file(ssh, cfg, fn)
            if rel:
                _add(rel)
            else:
                print(f"[INSTALL-WARN] edisk 中未找到: {fn}")
    else:
        for a in (scan_result or {}).get("artifacts", []):
            _add(a.get("rel", "").lstrip("/"))

    # 去重保序
    seen, dedup = set(), []
    for rel, abs_path in entries:
        key = (rel, abs_path)
        if key not in seen:
            seen.add(key)
            dedup.append(key)
    return dedup


def select_devices(cfg, device_desc=None):
    """按 --device 过滤设备列表; 未指定返回全部。"""
    devs = cfg.device_list
    if not devs:
        print("[INSTALL] 无目标设备配置")
        return []
    if device_desc:
        matched = [d for d in devs
                   if d.get("desc") == device_desc or d.get("host") == device_desc]
        if not matched:
            avail = ", ".join(d.get("desc", d.get("host", "?")) for d in devs)
            print(f"[WARN] 未找到设备 '{device_desc}', 可用: {avail}")
        return matched
    return devs


def generate_install_script(cfg, entries, devices, restart=True):
    """生成 install.sh: 推送 edisk 产物到多台设备并重启服务。

    entries: [(edisk_rel, device_abs), ...]
    devices: [{desc, host, port, user}, ...]
    密码不写入脚本: 优先取 DEPLOY_BUILD_DEVICE_PASS, 否则运行时交互输入。
    注意: SSH 命令用 bash 数组展开 ("${SSHPASS[@]}"), 避免变量间接层
    导致 $DEVICE_PASS 变成字面量(单趟展开不二次求值)。
    """
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    service = cfg.restart_service

    lines = f"""#!/bin/bash
# install.sh - 由 deploy_build.py 自动生成于 {ts}
# 推送 edisk 产物到 NF 设备并重启服务
EDISK_DIR="{cfg.nsbuild_install_dir}"

DEVICE_PASS="${{DEPLOY_BUILD_DEVICE_PASS:-}}"
if [ -z "$DEVICE_PASS" ]; then
    read -t 10 -sp "设备密码: " DEVICE_PASS
    echo
fi
if [ -z "$DEVICE_PASS" ]; then
    echo "[ERROR] 设备密码不能为空" >&2
    exit 1
fi
SSHPASS=(sshpass -p "$DEVICE_PASS")
SSH_OPTS=(-o StrictHostKeyChecking=no -o LogLevel=ERROR)
set -e
"""

    # 推送产物
    lines += f"\necho '[INSTALL] 推送 {len(entries)} 个产物到 {len(devices)} 台设备...'\n"
    for rel, abs_path in entries:
        target_dir = posixpath.dirname(abs_path)
        for dev in devices:
            dev_port = dev.get("port")
            dev_user = dev.get("user")
            dev_host = dev.get("host")
            if not dev_port or not dev_user or not dev_host:
                print(f"[INSTALL-WARN] 设备配置不完整(缺 port/user/host)，跳过: {dev}")
                continue
            lines += (
                f'"${{SSHPASS[@]}}" ssh "${{SSH_OPTS[@]}}" -p {dev_port} '
                f"{dev_user}@{dev_host} 'mkdir -p {target_dir}'\n"
            )
            lines += (
                f'"${{SSHPASS[@]}}" scp "${{SSH_OPTS[@]}}" -P {dev_port} '
                f"$EDISK_DIR/{rel} {dev_user}@{dev_host}:{abs_path}\n"
            )

    # 重启服务
    if restart:
        lines += f"\necho '[INSTALL] 重启服务 {service}...'\n"
        for dev in devices:
            dev_port = dev.get("port")
            dev_user = dev.get("user")
            dev_host = dev.get("host")
            if not dev_port or not dev_user or not dev_host:
                print(f"[INSTALL-WARN] 设备配置不完整，跳过重启: {dev}")
                continue
            lines += (
                f'"${{SSHPASS[@]}}" ssh "${{SSH_OPTS[@]}}" -p {dev_port} '
                f"{dev_user}@{dev_host} "
                f"'systemctl daemon-reload && systemctl restart {service}'\n"
            )
    else:
        lines += "\necho '[INSTALL] 跳过重启服务 (--no-restart)'\n"

    lines += "\necho '[INSTALL] 完成!'\n"
    return lines


def remote_install(ssh, cfg, entries=None, devices=None, restart=True, note=""):
    """在编译服务器上执行 install.sh, 推送 edisk 产物到目标设备。"""
    if not entries:
        print("[INSTALL] 无可推送产物, 跳过安装。")
        return 0
    if not devices:
        print("[INSTALL] 无目标设备, 跳过安装。")
        return 0
    # 密码必须存在: ssh_exec 无法交互输入, 缺失则 fail fast(先于写脚本, 避免无谓副作用)
    if not cfg.device_pass:
        print("[INSTALL-ERROR] 未提供设备密码, 请设置环境变量 DEPLOY_BUILD_DEVICE_PASS 后重试。")
        return 1

    print(f"[INSTALL] {note or f'推送 {len(entries)} 个产物到 {len(devices)} 台设备'}...")

    content = generate_install_script(cfg, entries, devices, restart=restart)
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    remote_install_path = posixpath.join(cfg.nf_dir, "install.sh")

    sftp = ssh.open_sftp()
    try:
        with sftp.file(remote_install_path, "w") as f:
            f.write(content)
    finally:
        sftp.close()

    run_cmd = f"cd {cfg.nf_dir} && DEPLOY_BUILD_DEVICE_PASS={shq(cfg.device_pass)} bash install.sh"
    exit_code, out, err = ssh_exec(ssh, run_cmd, timeout=300)
    if exit_code == 0:
        print("[INSTALL] Install succeeded!")
    else:
        print(f"[INSTALL] Install failed (exit_code={exit_code})")
    return exit_code


# =====================================================================
# 编译
# =====================================================================

def remote_build(ssh, cfg, mode="d"):
    """在编译服务器执行 nsbuild-git 编译。

    mode: d(debug) / b(release) / i(打包) / di(debug+打包) / bi(release+打包) / c(清理)
    """
    if mode == "c":
        print("[BUILD] Cleaning (nsbuild-git -c)...")
        exit_code, out, err = ssh_exec(
            ssh, f"cd {cfg.nf_dir} && nsbuild-git -c", timeout=540)
        if exit_code == 0:
            print("[BUILD] Clean succeeded!")
        else:
            print(f"[BUILD] Clean failed (exit_code={exit_code})")
        return exit_code

    print(f"[BUILD] Starting build (nsbuild-git -{mode})...")
    # 用 grep 过滤 nsbuild 输出，只保留 error/fatal 及其上下文，压缩 token 消耗。
    # 远端默认 shell 可能是 dash/sh，不支持 bash 的 PIPESTATUS：
    # 先将完整输出落盘到远端临时文件，退出码立刻保存，再 grep 文件过滤显示，
    # 避免 grep 无匹配返回 1 造成误判，也避免管道退出码丢失。
    exit_code, out, err = ssh_exec(
        ssh,
        f"cd {cfg.nf_dir} && {{ nsbuild-git -{mode}; }} > /tmp/nsbuild_build.log 2>&1; "
        f"__code=$?; grep -i -E 'error|fatal' -A 10 -B 10 /tmp/nsbuild_build.log; "
        f"echo __PIPE_NSBUILD_EXIT__=$__code",
        # 540s 预留 ≥60s 余量给 Bash 工具层超时清理，避免竞态导致 exit 120
        timeout=540,
    )
    # 从输出中提取 nsbuild 真实退出码
    m = re.search(r"__PIPE_NSBUILD_EXIT__=(\d+)", out)
    nsbuild_code = int(m.group(1)) if m else exit_code
    if nsbuild_code == 0:
        print("[BUILD] Build succeeded!")
    else:
        print(f"[BUILD] Build failed (exit_code={nsbuild_code})")
    return nsbuild_code


# =====================================================================
# 连接预检
# =====================================================================

def test_connections(cfg, device_desc=None):
    """ping 编译服务器 + 目标设备(可按 --device 过滤)，返回 (ok, error_list)。"""
    errors = []

    # 1) 编译服务器
    try:
        ssh = ssh_connect(cfg)
        print(f"[CONN-OK] 编译服务器 {cfg.remote_user}@{cfg.remote_host}:{cfg.remote_port}")
        ssh.close()
    except Exception as e:
        errors.append(f"编译服务器 {cfg.remote_user}@{cfg.remote_host}:{cfg.remote_port} 连接失败: {e}")

    # 2) 目标设备（通过编译服务器中转探测）
    if not cfg.device_pass:
        print("[CONN-WARN] 未设置 DEPLOY_BUILD_DEVICE_PASS, 跳过设备探测。")
        return (len(errors) == 0, errors)

    if not errors:
        for dev in select_devices(cfg, device_desc):
            dev_host = dev.get("host")
            dev_port = dev.get("port")
            dev_user = dev.get("user")
            desc = dev.get("desc", dev_host)
            try:
                ssh = ssh_connect(cfg)
                try:
                    probe = (
                        f"sshpass -p {shq(cfg.device_pass)} ssh "
                        f"-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o LogLevel=ERROR "
                        f"-p {dev_port} {dev_user}@{dev_host} 'hostname && echo DEVICE_OK'"
                    )
                    code, out, err = ssh_exec(ssh, probe, timeout=30)
                    if "DEVICE_OK" in out:
                        print(f"[CONN-OK] 目标设备 {desc} ({dev_user}@{dev_host}:{dev_port})")
                    else:
                        errors.append(
                            f"目标设备 {desc} ({dev_user}@{dev_host}:{dev_port}) "
                            f"中转探测失败 (exit={code})"
                        )
                finally:
                    ssh.close()
            except Exception as e:
                errors.append(f"目标设备 {desc} 探测异常: {e}")

    return (len(errors) == 0, errors)


# =====================================================================
# 主流程
# =====================================================================

def build_parser():
    p = argparse.ArgumentParser(
        description="增量同步本地改动到远端编译服务器并执行编译/安装",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    conn = p.add_argument_group("连接参数", "覆盖远端服务器/目标设备的连接配置")
    conn.add_argument("--project-dir", help="项目配置目录(含 .dsh/env_config), 默认 AGENT_ASSETS_DIR (环境变量可覆盖, 缺省 REDACTED_WORKSPACE_PATH)")
    conn.add_argument("--remote-host", help=f"编译服务器地址 (默认: {DEFAULT_CONFIG['remote_host']})")
    conn.add_argument("--remote-port", type=int, help=f"编译服务器SSH端口 (默认: {DEFAULT_CONFIG['remote_port']})")
    conn.add_argument("--remote-user", help="编译服务器用户名 (必填, 无默认)")
    conn.add_argument("--remote-dir", help="远端NPP代码仓库基地址 (必填, 无默认)")
    conn.add_argument("--device-host", help="目标设备地址 (安装时必填, 无默认)")
    conn.add_argument("--device-port", type=int, help="目标设备SSH端口 (安装时必填, 无默认)")
    conn.add_argument("--device-user", help="目标设备用户名 (安装时必填, 无默认)")
    conn.add_argument("--local-dir", help="本地NPP代码目录 (默认: 当前工作目录)")
    conn.add_argument("--config", help="指定额外配置文件路径 (优先级最高)")
    conn.add_argument("--save-config", nargs="?", const="all", default=None,
                      help="保存配置: all/deploy/device")

    op = p.add_argument_group("操作参数")
    op.add_argument("--base", help="基线分支 (无默认: 优先读本地 npp 分支, 读不到则询问用户)")
    op.add_argument("--worktree", help="编译机 worktree 工作区名(如 fix-NEWNF-12345), 从 NPP_BASE 派生到兄弟目录")
    op.add_argument("--mode", default=None, help="nsbuild-git 编译模式: d/b/i/di/bi/c (默认 d; 带 --install 时默认 di)")
    op.add_argument("--device", help="目标设备描述(NF-1 等), 默认推送全部设备")
    op.add_argument("--restart-service", help="设备重启服务名 (必填, 无默认)")
    op.add_argument("--build", action="store_true", help="同步+编译")
    op.add_argument("--build-only", action="store_true", help="只编译（不同步）")
    op.add_argument("--install", action="store_true", help="推送（基于 CMake 扫描 → edisk; 配合 --build 使用, 单独使用等于 --install-only）")
    op.add_argument("--install-only", action="store_true", help="只推送（基于 CMake 扫描或 --files）")
    op.add_argument("--install-full", action="store_true", help="edisk 全量推送（不依赖扫描）")
    op.add_argument("--files", nargs="*", default=None, help="手动指定推送文件列表")
    op.add_argument("--no-restart", action="store_true", help="安装后不重启服务")
    op.add_argument("--clean", action="store_true", help="执行 nsbuild-git -c 清理")
    op.add_argument("--sync-only", action="store_true", help="只同步文件")
    op.add_argument("--diff-only", action="store_true", help="只看差异")
    op.add_argument("--status", action="store_true", help="远端状态")
    op.add_argument("--scan-only", action="store_true", help="只执行 CMake 扫描（不编译/推送）")
    op.add_argument("--test-connection", action="store_true", help="仅测试连接，不执行其他操作")
    op.add_argument("--dry-run", action="store_true", help="打印将执行的操作，不实际执行")
    return p


def main():
    global LOCAL_NPP_DIR, ENV_CONFIG_DIR, DEPLOY_DIR, CONFIG_FILE, DEVICE_CONFIG_FILE, SYNC_MANIFEST, LOG_DIR

    parser = build_parser()
    args = parser.parse_args()

    # --project-dir 指定配置存放目录（.dsh/env_config），未指定时使用默认路径
    # （AGENT_ASSETS_DIR/.dsh/...，见模块顶部常量定义）
    # 必须在 Config.load 之前处理，确保配置文件路径正确
    if args.project_dir:
        ENV_CONFIG_DIR = os.path.join(os.path.abspath(args.project_dir), ".dsh", "env_config", "deploy_build")
        DEPLOY_DIR = ENV_CONFIG_DIR  # 兼容历史引用
        CONFIG_FILE = os.path.join(ENV_CONFIG_DIR, "deploy_config.json")
        DEVICE_CONFIG_FILE = os.path.join(ENV_CONFIG_DIR, "device_config.json")
        SYNC_MANIFEST = os.path.join(ENV_CONFIG_DIR, "sync_manifest.json")
        LOG_DIR = os.path.join(ENV_CONFIG_DIR, "logs")

    if args.local_dir:
        LOCAL_NPP_DIR = os.path.abspath(args.local_dir)

    cfg = Config.load(args)

    if args.restart_service:
        cfg.restart_service = args.restart_service

    # 保存配置（独立命令）—— 不触发交互补齐，由用户在 CLI/配置中提供
    if args.save_config:
        cfg.save(args.save_config)
        return

    # ── 运行前补齐缺失参数（交互询问）──
    # 仅编译机地址/端口有默认；其余缺失字段逐个询问，绝不带默认值继续。
    # dry-run 仅预览计划，不触发补齐（零配置也能预览）。
    if not args.dry_run:
        need_device = bool(args.install or args.install_only or args.install_full
                           or args.device or args.test_connection)
        prompt_missing(cfg, need_device=need_device)

    # ── 编译模式统一计算与校验(所有路径共用, 不连 SSH 即拦截非法值) ──
    if args.clean:
        BUILD_MODE = "c"
    elif args.mode:
        BUILD_MODE = args.mode
    elif args.install or args.install_only or args.install_full:
        BUILD_MODE = "di"
    else:
        BUILD_MODE = "d"
    if BUILD_MODE not in {"d", "b", "i", "di", "bi", "c"}:
        print(f"[ERROR] 无效编译模式 '{BUILD_MODE}', 可选: d/b/i/di/bi/c")
        sys.exit(2)

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, "deploy.log")
    logger = Logger(log_path)
    sys.stdout = logger
    sys.stderr = logger
    print(f"[LOG] 日志文件: {log_path}")
    print(f"[CONFIG] 编译服务器: {cfg.remote_user}@{cfg.remote_host}:{cfg.remote_port}")
    print(f"[CONFIG] 远端目录: {cfg.remote_npp_dir}")
    print(f"[CONFIG] 目标设备: {cfg.device_user}@{cfg.device_host}:{cfg.device_port}")
    print(f"[CONFIG] 基线分支: {cfg.base_branch}")
    print(f"[CONFIG] 扫描脚本: {cfg.scan_script_remote}")

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda s, f: _set_interrupt())

    ssh = None
    try:
        # ── 独立命令：测试连接 ──
        if args.test_connection:
            ok, errs = test_connections(cfg, args.device)
            if ok:
                print("[CONN] 连接测试全部通过 ✓")
            else:
                for e in errs:
                    print(f"[CONN-FAIL] {e}")
                sys.exit(1)
            return

        # ── 独立命令：远端状态 ──
        if args.status:
            ssh = ssh_connect(cfg)
            ssh_exec(ssh, f"cd {cfg.remote_npp_dir} && git branch --show-current && git log --oneline -5")
            ssh.close()
            ssh = None
            return

        # 基线解析：显式 --base 优先；否则从用户指定的本地工作目录解析
        # （当前分支与主干/上游的 merge-base），避免硬编码发布分支导致
        # 重构分支被误判为大量改动。
        if args.base:
            base = args.base
        else:
            base = resolve_local_base() or cfg.base_branch
            print(f"[CONFIG] 基线(本地解析): {base}")

        # ── dry-run 提前退出：不执行 git diff，不连接 SSH ──
        if args.dry_run:
            do_sync = not (args.install_only or args.install_full)
            do_build = args.build or args.build_only
            do_install = args.install or args.install_only or args.install_full
            install_fallback = args.install_full or args.files
            print(f"\n[DRY-RUN] 以下操作将执行（跳过实际操作）：")
            if args.worktree:
                print(f"  [DRY-RUN] worktree 派生: {args.worktree} (基于 {base})")
            if do_sync:
                print(f"  [DRY-RUN] 同步：待检测改动文件")
            if do_build:
                print(f"  [DRY-RUN] 远端编译: nsbuild-git -{BUILD_MODE}")
            if do_install:
                mode = "edisk 全量推送" if install_fallback else "基于 CMake 扫描的精确安装"
                restart = " + 重启服务" if not args.no_restart else ""
                print(f"  [DRY-RUN] 安装: {mode}{restart}")
            return

        # 获取改动文件（除 status/test-connection/dry-run 外的所有操作都需要）
        print(f"[INFO] Base: {base}, Local: {LOCAL_NPP_DIR}, Remote: {cfg.remote_npp_dir}")
        files, deletes, untracked_list = get_changed_files(cfg, base)

        if not files and not deletes and not (args.build_only or args.install_only or args.install_full):
            print("[INFO] 无改动文件，退出。")
            return

        print(f"\n[CHANGES] {len(files)} modified/new, {len(deletes)} deleted")
        for f in files:
            print(f"  + {f}")
        for f in deletes:
            print(f"  - {f}")

        # ── diff-only ──
        if args.diff_only:
            diff = git_cmd(["diff", "--stat", base, "HEAD"])
            print(f"\n[DIFF STAT]\n{diff}")
            return

        # ── scan-only（需 ssh） ──
        if args.scan_only:
            ssh = ssh_connect(cfg)
            result = run_cmake_scan(ssh, cfg, files)
            if result:
                print("\n[SCAN-RESULT]")
                print(json.dumps(result.get("summary", {}), ensure_ascii=False, indent=2))
                print(f"  受影响目标: {result.get('affected_targets', [])}")
                for a in result.get("artifacts", []):
                    print(f"    {a.get('target')} → {a.get('rel')} ({a.get('type')})")
            ssh.close()
            ssh = None
            return

        # ── 确定操作模式 ──
        do_sync = not (args.install_only or args.install_full)
        do_build = args.build or args.build_only
        do_install = args.install or args.install_only or args.install_full

        if args.install_full and args.files:
            print("[WARN] --install-full 与 --files 同时传入：--install-full 将覆盖 --files，全量推送。")

        ssh = ssh_connect(cfg)

        # ── worktree 派生(设计步骤 2-4: 切分支 → git worktree add → 进入 worktree) ──
        # 派生基线 = diff 基线(本地 merge-base), 保证"同步什么、在什么基线上同步"一致
        if args.worktree:
            prepare_worktree(ssh, cfg, args.worktree, base)
            cfg.use_worktree(args.worktree)
            print(f"[CONFIG] 远端工作目录(worktree): {cfg.remote_npp_dir}")

        if do_sync:
            if args.files:
                # --files 作为同步白名单：仅同步清单内且本地存在的文件，跳过删除
                sync_list = [f for f in args.files
                             if os.path.isfile(os.path.join(LOCAL_NPP_DIR, f))]
                print(f"[INFO] --files 白名单: {len(sync_list)} 个文件（仅同步清单，不执行删除）")
                sync_files(ssh, cfg, sync_list, [])
            else:
                sync_files(ssh, cfg, files, deletes)
            save_manifest(untracked_list)

            if args.sync_only:
                print("\n[DONE] 文件已同步。")
                ssh.close()
                ssh = None
                return

        if do_build:
            code = remote_build(ssh, cfg, mode=BUILD_MODE)
            if code != 0:
                print(f"\n[BUILD FAILED] exit_code={code}")
                try:
                    ssh.close()
                except Exception:
                    pass
                ssh = None
                sys.exit(code)
            if args.build_only:
                print("\n[DONE] 编译完成。")
                ssh.close()
                ssh = None
                return

        if do_install:
            restart = not args.no_restart
            devices = select_devices(cfg, args.device)
            if args.install_full or args.files:
                entries = collect_install_entries(
                    ssh, cfg, files=args.files, install_full=args.install_full)
            else:
                if not files:
                    print("[INSTALL-ERROR] 无改动文件: scan 型精确安装需要改动, 请改用 --files <文件> 指定或 --install-full 全量推送。")
                    ssh.close()
                    ssh = None
                    sys.exit(1)
                result = run_cmake_scan(ssh, cfg, files)
                if result is None:
                    print("[INSTALL-ERROR] CMake 扫描失败, 中止安装。请修复扫描问题或改用 --install-full。")
                    ssh.close()
                    ssh = None
                    sys.exit(1)
                entries = collect_install_entries(ssh, cfg, scan_result=result)
            rc = remote_install(ssh, cfg, entries=entries, devices=devices, restart=restart)
            if rc != 0:
                # 安装失败必须非零退出, 防止整条流水线谎报成功
                ssh.close()
                ssh = None
                sys.exit(rc)

        ssh.close()
        ssh = None
        print("\n[DONE] 完成。")

    except KeyboardInterrupt:
        print("\n[INTERRUPT] 用户中断，清理...")
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        sys.exit(130)
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        signal.signal(signal.SIGINT, original_sigint)
        # 恢复 stdout/stderr 到原始终端。若只恢复 stdout 而遗漏 stderr，
        # 解释器退出时会对已 close 的 logger 写 stderr 抛异常，进程以非零
        # 退出码(120)退出——编译成功但脚本被判定失败。
        sys.stdout = logger.terminal
        sys.stderr = getattr(logger, "terminal_err", sys.__stderr__)
        logger.close()
        print(f"\n[LOG] 日志已保存到: {log_path}")


if __name__ == "__main__":
    main()