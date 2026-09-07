#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NF BUG 修复状态机引擎

脚本驱动的确定性状态机，落地 .dsh/hooks/AGENT.md 中「BUG 修复流程铁律」的规则：
主状态机 分析→审查结论→出修改方案→编码→上机验证→更新BUG单→结束，
每个主状态内含微观状态机；硬校验门禁 + state.json 三键断点。

主状态（含微观状态）：
  分析      取证→假设→验证→结论             退出产物 问题分析结论.md
  审查结论  审查→复现→判定→轮次记账          退出产物 审查结果-rN.md
  出修改方案 方案草拟→影响评估→方案评审→用户确认 退出产物 修改方案.md
  编码      修改→代码审查→编译通过→修复审查问题 退出产物 编译产物（deploy_build 验证，非脚本跟踪）
  上机验证  自测记录→基础测试→转人工验证→人工验证通过 退出产物 自测记录.md
  更新BUG单 生成PR描述→提交PR→人工review PR→关闭工单→沉淀经验 退出产物 PR描述.md+结论文档
  结束      无

用法（仿 writable_dirs.py / deploy_build.py 惯例）：
  python state_machine.py init --bug-id NEWNF-51805 --title "..." --module "安全策略"
  python state_machine.py state --bug-id NEWNF-51805 [--json]
  python state_machine.py progress --bug-id NEWNF-51805   # 可视化进度总览
  python state_machine.py micro --bug-id NEWNF-51805 --to 假设
  python state_machine.py advance --bug-id NEWNF-51805 --to 审查结论
  python state_machine.py review --bug-id NEWNF-51805 --result PASS --round 1 --issues "..."
  python state_machine.py record --bug-id NEWNF-51805 --phase analysis --minutes 30
  python state_machine.py jira --bug-id NEWNF-51805 --flag fetched --value true
  python state_machine.py confirm --bug-id NEWNF-51805 --flag plan_confirmed --by <确认人> [--note]
  python state_machine.py gate --bug-id NEWNF-51805 --flag build_passed --value true --evidence <编译日志>
  python state_machine.py gate-check --bug-id NEWNF-51805
  python state_machine.py resolve --bug-id NEWNF-51805
  python state_machine.py close --bug-id NEWNF-51805 --conclusion 结论文档.md
  python state_machine.py reset --bug-id NEWNF-51805

约定：
  - exit 0 成功；exit 2 门禁拒绝（stderr 提示缺什么）；exit 1 其他错误。
  - 所有路径以 Path(__file__) 锚定工作区根（仓库根），不依赖 cwd。
  - 原子写（临时文件 + os.replace），避免中断损坏 JSON。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows 控制台默认 GBK 无法输出 ✓/✗/中文；强制 UTF-8，兼容 Git Bash 显示
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Windows/Git Bash 中文 argv 转码修复：命令行传入的中文（如结论文档路径）在 GBK
# locale 下会被错误解码，尝试按 UTF-8 原始字节重解，仅当成功且非 ASCII 时替换。
def _fix_utf8_argv() -> None:
    if sys.platform != "win32":
        return
    fixed = []
    for i, a in enumerate(sys.argv):
        try:
            raw = os.fsencode(a)
        except (UnicodeEncodeError, OSError):
            fixed.append(a)
            continue
        if not any(b >= 0x80 for b in raw):
            fixed.append(a)
            continue
        try:
            fixed.append(raw.decode("utf-8"))
        except UnicodeDecodeError:
            fixed.append(a)
    sys.argv = fixed


_fix_utf8_argv()

# 工作区根 = 本文件上级四级（skills/bug-fix-workflow/ -> skills/ -> .dsh/ -> 仓库根）
WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
SKILL_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SKILL_DIR / "templates"
DEFAULT_STATE_DIR = WORKSPACE / "bug-fix-state"

# 本地时区偏移（+08:00，中国大陆）；ISO8601 落盘用
LOCAL_TZ = timezone(timedelta(hours=8))

# 主状态 → 微观状态（有序）
MICRO_STATES = {
    "分析": ["取证", "假设", "验证", "结论"],
    "审查结论": ["审查", "复现", "判定", "轮次记账"],
    "出修改方案": ["方案草拟", "影响评估", "方案评审", "用户确认"],
    "编码": ["修改", "代码审查", "编译通过", "修复审查问题"],
    "上机验证": ["自测记录", "基础测试", "转人工验证", "人工验证通过"],
    "更新BUG单": ["生成PR描述", "提交PR", "人工review PR", "关闭工单", "沉淀经验"],
    "结束": [],
}
MAIN_STATES = list(MICRO_STATES.keys())
FIRST_MICRO = {s: m[0] for s, m in MICRO_STATES.items() if m}

# 审查轮次上限
MAX_REVIEW_ROUNDS = 3

# 退出产物映射（artifacts 键 → 文件名）
ARTIFACT_FILES = {
    "分析": ("analysis", "问题分析结论.md"),
    "审查结论": ("review", "审查结果-r{round}.md"),
    "出修改方案": ("plan", "修改方案.md"),
    "上机验证": ("selftest", "自测记录.md"),
    "更新BUG单": ("pr_desc", "PR描述.md"),
}

# 审查 FAIL 回退的起始微观状态
REVIEW_FAIL_BACK_TO = "取证"


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def fatal(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def gate_reject(msg: str) -> int:
    print(f"[gate] 拒绝：{msg}", file=sys.stderr)
    return 2


def ensure_not_takeover(state: dict) -> int | None:
    """人工接管后禁止自动推进。返回 None=可继续；否则返回 gate_reject 结果。"""
    if state.get("human_takeover"):
        return gate_reject(
            "已转人工接管（审查 3 轮 FAIL），禁止自动推进。请人工复核后人工处理。"
        )
    return None


def state_path(bug_id: str, state_dir: Path | None = None) -> Path:
    base = state_dir or DEFAULT_STATE_DIR
    return base / bug_id / "state.json"


def bug_dir(bug_id: str, state_dir: Path | None = None) -> Path:
    base = state_dir or DEFAULT_STATE_DIR
    return base / bug_id


def load_state(bug_id: str, state_dir: Path | None = None) -> dict | None:
    p = state_path(bug_id, state_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_state(state: dict, state_dir: Path | None = None) -> None:
    """原子写 state.json，并同步刷新 progress.md 人类可读进度卡片。"""
    p = state_path(state["bug_id"], state_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    try:
        write_progress_md(state, state_dir)
    except (OSError, ValueError):
        pass  # 进度卡片刷新失败不影响状态机主流程


def append_timeline(state: dict, event: str, main_state: str, micro_state: str, note: str = "") -> None:
    state["timeline"].append({
        "at": now_iso(),
        "event": event,
        "main_state": main_state,
        "micro_state": micro_state,
        "note": note,
    })


def progress_banner(state: dict) -> str:
    """一行紧凑进度横幅：如 【进度 3/7 · 出修改方案 · 用户确认】。

    每次状态变更命令输出末尾追加，让长程任务的运行日志每步都自带「当前位置」。
    """
    ms = state["main_state"]
    total = len(MAIN_STATES)
    idx = MAIN_STATES.index(ms) + 1 if ms in MAIN_STATES else total
    mis = state.get("micro_state") or ""
    return f"【进度 {idx}/{total} · {ms}" + (f" · {mis}" if mis else "") + "】"


def render_progress(state: dict) -> str:
    """可视化进度总览：主状态流水线 + 当前主状态内微观状态进度。

    ✓=已完成  ▶=当前  ○=未开始；当前主状态行展开其微观状态进度。
    """
    ms = state["main_state"]
    mis = state.get("micro_state") or ""
    idx = MAIN_STATES.index(ms) if ms in MAIN_STATES else len(MAIN_STATES)
    lines = [f"进度总览  {state['bug_id']}  {state['title'] or ''}".rstrip()]
    for i, s in enumerate(MAIN_STATES):
        mark = "✓" if i < idx else ("▶" if i == idx else "○")
        label = f"  {mark} [{i + 1}/{len(MAIN_STATES)}] {s}"
        micros = MICRO_STATES.get(s, [])
        if i == idx and micros:
            cur = mis if mis in micros else micros[0]
            ci = micros.index(cur)
            steps = []
            for j, m in enumerate(micros):
                if j < ci:
                    steps.append(f"✓{m}")
                elif j == ci:
                    steps.append(f"▶{m}")
                else:
                    steps.append(m)
            label += f"（{' → '.join(steps)}）"
        lines.append(label)
    extra = f"  审查轮次 {state.get('review_round', 0)}/{MAX_REVIEW_ROUNDS}"
    if state.get("human_takeover"):
        extra += "  ⚠已转人工接管"
    elif state.get("escalated"):
        extra += "  ⚠已升级"
    lines.append(extra)
    return "\n".join(lines)


def write_progress_md(state: dict, state_dir: Path | None = None) -> None:
    """刷新 <bug-dir>/progress.md 人类可读进度卡片。

    由 save_state 每次落盘自动调用，保证长程任务中用户随时打开该文件即可看到
    当前走到哪个阶段；progress 命令按需重建（覆盖旧状态文件未生成的场景）。
    """
    d = bug_dir(state["bug_id"], state_dir)
    d.mkdir(parents=True, exist_ok=True)
    ms = state["main_state"]
    mis = state.get("micro_state") or ""
    total = len(MAIN_STATES)
    idx = MAIN_STATES.index(ms) + 1 if ms in MAIN_STATES else total
    gates_done = [k for k, v in state.get("gates", {}).items() if v]
    gates_pending = [k for k, v in state.get("gates", {}).items() if not v]
    lines = [
        f"# 进度 {state['bug_id']}",
        "",
        f"- 标题：{state.get('title') or '-'}",
        f"- 模块：{state.get('module') or '-'}",
        f"- 当前：主状态「{ms}」({idx}/{total}) / 微观「{mis or '-'}」",
        f"- 审查轮次：{state.get('review_round', 0)}/{MAX_REVIEW_ROUNDS}"
        + ("（⚠ 已转人工接管）" if state.get("human_takeover") else ""),
        f"- 更新时间：{state.get('updated_at', '')}",
        "",
        "## 进度总览",
        "",
    ]
    for i, s in enumerate(MAIN_STATES):
        if i < idx - 1:
            mark = "[x]"
        elif i == idx - 1:
            mark = "[>]"
        else:
            mark = "[ ]"
        line = f"- `{mark}` {s}"
        micros = MICRO_STATES.get(s, [])
        if i == idx - 1 and micros:
            cur = mis if mis in micros else micros[0]
            ci = micros.index(cur)
            steps = []
            for j, m in enumerate(micros):
                if j < ci:
                    steps.append(f"x{m}")
                elif j == ci:
                    steps.append(f">{m}")
                else:
                    steps.append(m)
            line += f"（{' → '.join(steps)}）"
        lines.append(line)
    lines += [
        "",
        "## 门禁",
        f"- 已通过：{('、'.join(gates_done)) if gates_done else '无'}",
        f"- 未通过：{('、'.join(gates_pending)) if gates_pending else '无'}",
        "",
        "## 最近事件（最新 8 条）",
        "",
    ]
    for ev in state.get("timeline", [])[-8:]:
        note = ev.get("note") or ""
        lines.append(
            f"- `{ev.get('at', '')}` **{ev.get('event', '')}** "
            f"{ev.get('main_state', '')}/{ev.get('micro_state', '')} {note}".rstrip()
        )
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, d / "progress.md")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def artifact_path(state: dict, key: str, state_dir: Path | None = None) -> Path | None:
    """artifacts 键 → 磁盘路径。空名返回 None；绝对路径原样返回；相对路径相对 bug 目录解析。"""
    name = state.get("artifacts", {}).get(key, "")
    if not name:
        return None
    p = Path(name)
    if p.is_absolute():
        return p
    return bug_dir(state["bug_id"], state_dir) / name


def find_file_in_bugdir(bugid: str, state_dir: Path | None, name: str) -> Path:
    return bug_dir(bugid, state_dir) / name


def check_file_exists(path: Path | None) -> bool:
    if path is None:
        return False
    return path.exists() and path.is_file() and path.stat().st_size > 0


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
def register_in_writable_dirs(bug_dir: Path) -> None:
    """把新 BUG 状态目录登记进 restricted 门禁的可读写清单（dirs.json）。

    幂等：已登记的目录直接放行，不覆盖已有 note。
    若 bug_dir 在 workspace 外（--dir 自定义到外部路径），跳过登记并提示。
    """
    tool = WORKSPACE / ".dsh" / "tools" / "writable_dirs.py"
    try:
        rel = bug_dir.resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        print(f"  [登记跳过] 状态目录在 workspace 外，无需登记：{bug_dir}")
        return
    r = subprocess.run(
        [sys.executable, str(tool), "add", rel.as_posix(), "BUG状态目录"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    msg = (r.stdout or r.stderr or "").strip()
    if r.returncode == 0:
        print(f"  [门禁登记] {msg}")
    else:
        print(f"  [门禁登记警告] {msg}")


def cmd_init(args) -> int:
    bug_id = args.bug_id.strip()
    if not bug_id:
        return fatal("--bug-id 必填")
    if not re.match(r"^[A-Za-z0-9_.\-]+$", bug_id):
        return fatal(f"--bug-id 含非法字符：{bug_id}（仅允许字母数字_.-）")
    # L3: 防路径穿越（. / .. 会解析到 workspace 根）
    if bug_id in (".", "..") or bug_id.endswith("/..") or bug_id.endswith("/."):
        return fatal(f"--bug-id 非法路径：{bug_id}")

    base = args.dir if args.dir else DEFAULT_STATE_DIR
    bug = bug_dir(bug_id, base)
    if bug.exists():
        return fatal(f"目标目录已存在，禁止覆盖：{bug}")
    if not TEMPLATES_DIR.is_dir():
        return fatal(f"模板目录不存在：{TEMPLATES_DIR}")

    bug.mkdir(parents=True)
    register_in_writable_dirs(bug)
    # templates/ 全部为产出物模板（问题分析结论/审查结果/修改方案/自测记录/PR描述/结论文档），
    # 一律不预复制——agent 按 templates/ 结构在 bug 目录创建产物，作为 advance/review/close 门禁依据。
    # 预复制成骨架会让产物门禁（按文件名查磁盘）恒过，违背硬校验设计。

    state = {
        "schema_version": 1,
        "bug_id": bug_id,
        "jira_key": args.jira_key or bug_id,
        "title": args.title or "",
        "module": args.module or "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "main_state": "分析",
        "micro_state": "取证",
        "review_round": 0,
        "escalated": False,
        "human_takeover": False,
        "artifacts": {
            "analysis": ARTIFACT_FILES["分析"][1],
            "review": "",
            "reviews": [],
            "plan": "",
            "selftest": "",
            "pr_desc": "",
            "conclusion": "",
        },
        "gates": {
            "analysis_reviewed": False,
            "plan_confirmed": False,
            "worktree_ready": False,       # 编译机隔离 worktree 已派生并登记（仅 worktree-set 置位）
            "code_reviewed": False,
            "build_passed": False,
            "selftest_done": False,
            "basic_test_done": False,
            "manual_verify_handed": False,
            "manual_verify_passed": False,
            "pr_reviewed": False,
            "jira_closed": False,
        },
        "timeline": [],
        "review_rounds": [],
        "worklog": {
            "sync_mode": "local",
            "local": {
                "analysis": {"minutes": 0, "note": ""},
                "review": {"minutes": 0, "note": ""},
                "plan": {"minutes": 0, "note": ""},
                "coding": {"minutes": 0, "note": ""},
                "device_verify": {"minutes": 0, "note": ""},
                "jira": {"minutes": 0, "note": ""},
            },
            "total_minutes": 0,
            "jira_worklog_synced": False,
        },
        "jira": {
            "fetched": False,
            "analysis_comment_added": False,
            "conclusion_comment_added": False,
            "transition_done": False,
            "last_error": "",
        },
        "git": {
            "branch": "",
            "commit_sha": "",
            "commit_format": f"fix: {bug_id} 【{args.module}】描述",
            "pr_url": "",
        },
    }
    append_timeline(state, "init", "分析", "取证", "创建状态机")
    save_state(state, base)
    print(f"已初始化：{bug}")
    print(f"  产物模板不预复制：按 .dsh/skills/bug-fix-workflow/templates/ 结构创建产物文件（门禁按文件名校验）")
    print(f"  主状态：分析 / 微观状态：取证")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# state / gate-check / resolve
# ---------------------------------------------------------------------------
def cmd_state(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    try:
        write_progress_md(state, args.dir)  # 刷新进度卡片（含旧状态首次补齐）
    except (OSError, ValueError):
        pass
    print(render_progress(state))
    print(f"BUG: {state['bug_id']}  {state['title']}")
    print(f"  主状态：{state['main_state']}  微观状态：{state['micro_state']}")
    print(f"  审查轮次：{state['review_round']}/{MAX_REVIEW_ROUNDS}" +
          ("  [已升级人工接管]" if state.get("human_takeover") else "") +
          ("  [已升级]" if state.get("escalated") else ""))
    print("  产物：")
    for k, v in state["artifacts"].items():
        if v:
            print(f"    {k}: {v}")
    print("  门禁：")
    for k, v in state["gates"].items():
        print(f"    {k}: {'✓' if v else '✗'}")
    if state.get("worktree"):
        wt = state["worktree"]
        print(f"  worktree：{wt.get('name')} @ {wt.get('remote_dir')} (base={wt.get('base_branch') or '-'})")
    else:
        print("  worktree：未派生（进入【编码】前须 deploy_build --worktree fix-<BUG单号>）")
    print(f"  工时累计：{state['worklog']['total_minutes']} 分钟 (sync={state['worklog']['sync_mode']})")
    return 0


def cmd_gate_check(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    ms = state["main_state"]
    print(render_progress(state))
    print(f"当前主状态：{ms}  微观状态：{state['micro_state']}")
    # 缺产物检查：只检查「已越过的主状态」的退出产物（常量名查磁盘，与 gate_prereq 口径一致 C1）。
    # 当前主状态及其后状态的产物正在产出中，不报缺失。
    bugid = state["bug_id"]
    missing_art = []
    for cur, (_, name) in ARTIFACT_FILES.items():
        if cur == "审查结论":
            continue  # 审查产物由 review 命令落盘，按最新轮次文件（不在此列）
        if MAIN_STATES.index(cur) >= MAIN_STATES.index(ms):
            continue  # 当前及之后状态的产物未到产出时点
        p = find_file_in_bugdir(bugid, args.dir, name)
        if not check_file_exists(p):
            missing_art.append(name)
    # 结论文档（close 时 --conclusion 传路径）
    concl = artifact_path(state, "conclusion", args.dir)
    if concl is not None and not check_file_exists(concl):
        missing_art.append("结论文档")
    if missing_art:
        print("  缺失产物：" + ", ".join(missing_art))
    else:
        print("  关键产物：齐")
    print("  门禁状态：")
    for k, v in state["gates"].items():
        print(f"    {k}: {'✓' if v else '✗'}")
    # 下一步建议
    print("  下一步建议：")
    next_main = next_main_state(ms)
    prereq = gate_prereq(next_main, state, args.dir)
    if prereq:
        print(f"    可推进到「{next_main}」，门禁需满足：" + ("、" .join(prereq)))
    else:
        print(f"    「{next_main}」门禁已满足，可 advance")
    return 0


def cmd_resolve(args) -> int:
    """断点恢复指引：当前节点 + 推荐动作。"""
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    ms, mis = state["main_state"], state["micro_state"]
    print(render_progress(state))
    print(f"=== 断点恢复：{state['bug_id']} ===")
    print(f"主状态「{ms}」/ 微观状态「{mis}」/ 审查轮次 {state['review_round']}")
    if state.get("human_takeover"):
        print("⚠ 已转人工接管：停止自动推进，按上一条 review FAIL 的 issues 补充分析后由人工复核。")
        return 0
    if state.get("escalated"):
        print("⚠ 已升级（审查 3 轮失败）：请人工接管。")
        return 0
    if ms == "分析":
        print(f"下一步：完成「{mis}」后推进微观状态；产出问题分析结论.md 后 advance 到 审查结论。")
    elif ms == "审查结论":
        print(f"下一步：当前第 {state['review_round']} 轮已完成；若为 FAIL 且轮次<3 已回 分析，补取证后再审查；若为 PASS 已推进 出修改方案。")
    elif ms == "出修改方案":
        print("下一步：确认修改方案.md 后询问用户确认（置 gates.plan_confirmed），再 advance 到 编码。")
        wt = state.get("worktree")
        if wt:
            print(f"  worktree 已登记：{wt.get('name')}（{wt.get('remote_dir')}）")
        else:
            print("  ⚠ worktree 尚未派生：进入 编码 前须先在编译机执行 deploy_build --worktree fix-<BUG单号>（派生成功自动登记）")
    elif ms == "编码":
        print("下一步：完成代码审查（code_reviewed）+ 编译通过（build_passed）后 advance 到 上机验证。")
    elif ms == "上机验证":
        print("下一步：完成自测记录.md + 人工验证通过（manual_verify_passed）后 advance 到 更新BUG单。")
    elif ms == "更新BUG单":
        print("下一步：生成PR描述.md + 提交PR + 人工review（pr_reviewed）+ 关闭工单（jira_closed）+ 沉淀经验（memory-gen 生成经验文档并更新索引、memory-push 推送 git，然后 micro --to 沉淀经验）后 close。")
    else:
        print("已结束。")
    return 0


# ---------------------------------------------------------------------------
# micro / advance
# ---------------------------------------------------------------------------
def cmd_micro(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    guard = ensure_not_takeover(state)
    if guard is not None:
        return guard
    ms = state["main_state"]
    valid = MICRO_STATES[ms]
    if not valid:
        return fatal(f"主状态「{ms}」无微观状态")
    to = args.to
    if to not in valid:
        return fatal(f"「{to}」不属于主状态「{ms}」的微观状态列表：{'→'.join(valid)}")
    idx_cur = valid.index(state["micro_state"])
    idx_to = valid.index(to)
    if idx_to < idx_cur and not args.force:
        return gate_reject(f"不允许回退微观状态（当前「{state['micro_state']}」→「{to}」），如需回退加 --force")
    if idx_to == idx_cur and not args.force:
        return gate_reject(f"已处于「{to}」，无需推进")
    old = state["micro_state"]
    state["micro_state"] = to
    append_timeline(state, "micro", ms, to, f"{old} → {to}")
    save_state(state, args.dir)
    print(f"微观状态推进：{old} → {to}（主状态「{ms}」）")
    print(progress_banner(state))
    return 0


def next_main_state(ms: str) -> str:
    try:
        i = MAIN_STATES.index(ms)
    except ValueError:
        return "结束"
    return MAIN_STATES[i + 1] if i + 1 < len(MAIN_STATES) else "结束"


def gate_prereq(next_main: str, state: dict, state_dir: Path | None) -> list[str]:
    """advance 到 next_main 的门禁。返回缺失项列表（空 = 已满足）。

    产物存在性一律按已知产物文件名查磁盘（不依赖 artifacts 映射值——该值在
    advance 后才登记，门禁求值阶段可能是空串）。
    """
    missing = []
    bugid = state["bug_id"]
    if next_main == "审查结论":
        p = find_file_in_bugdir(bugid, state_dir, ARTIFACT_FILES["分析"][1])
        if not check_file_exists(p):
            missing.append("问题分析结论.md 不存在或为空")
    elif next_main == "出修改方案":
        if not state["gates"].get("analysis_reviewed"):
            missing.append("gates.analysis_reviewed 未置位（审查未 PASS）")
    elif next_main == "编码":
        p = find_file_in_bugdir(bugid, state_dir, ARTIFACT_FILES["出修改方案"][1])
        if not check_file_exists(p):
            missing.append("修改方案.md 不存在")
        if not state["gates"].get("plan_confirmed"):
            missing.append("gates.plan_confirmed 未置位（用户未确认方案）")
        if not state["gates"].get("worktree_ready"):
            missing.append("gates.worktree_ready 未置位（编译机 worktree 未派生/登记，先执行 deploy_build --worktree fix-<BUG单号>）")
    elif next_main == "上机验证":
        if not state["gates"].get("code_reviewed"):
            missing.append("gates.code_reviewed 未置位（代码未审查）")
        if not state["gates"].get("build_passed"):
            missing.append("gates.build_passed 未置位（编译未通过）")
    elif next_main == "更新BUG单":
        p = find_file_in_bugdir(bugid, state_dir, ARTIFACT_FILES["上机验证"][1])
        if not check_file_exists(p):
            missing.append("自测记录.md 不存在")
        if not state["gates"].get("manual_verify_passed"):
            missing.append("gates.manual_verify_passed 未置位（人工验证未通过）")
    elif next_main == "结束":
        if not state["gates"].get("pr_reviewed"):
            missing.append("gates.pr_reviewed 未置位（PR 未经人工 review）")
        if not state["gates"].get("jira_closed"):
            missing.append("gates.jira_closed 未置位（工单未关闭）")
        if state["micro_state"] != "沉淀经验":
            missing.append("微观状态未推进到「沉淀经验」（bugfix-flow 结束前必须完成经验沉淀：memory-gen 生成经验文档 + 更新索引，memory-push 推送 git，然后 micro --to 沉淀经验）")
        p = artifact_path(state, "conclusion", state_dir)
        if not check_file_exists(p):
            missing.append("结论文档不存在")
    return missing


def cmd_advance(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    guard = ensure_not_takeover(state)
    if guard is not None:
        return guard
    cur = state["main_state"]
    to = args.to
    if to not in MAIN_STATES:
        return fatal(f"非法主状态：{to}（可选：{'、'.join(MAIN_STATES)}）")
    if to == cur:
        return gate_reject(f"已处于「{to}」")
    if MAIN_STATES.index(to) != MAIN_STATES.index(cur) + 1:
        return gate_reject(f"不允许跳转：{cur} → {to}（只能推进到下一主状态）")

    missing = gate_prereq(to, state, args.dir)
    if missing:
        return gate_reject(f"推进到「{to}」门禁不满足：{('、'.join(missing))}")

    # 落退出产物路径（审查结论的产物由 review 命令写，此处只登记文件名占位）
    art_key, art_name = ARTIFACT_FILES.get(cur, (None, None))
    if art_key and cur != "审查结论":
        state["artifacts"][art_key] = art_name

    old = cur
    state["main_state"] = to
    state["micro_state"] = FIRST_MICRO.get(to, "")
    append_timeline(state, "advance", to, state["micro_state"], f"{old} → {to}")
    save_state(state, args.dir)
    print(f"主状态推进：{old} → {to}（微观状态：{state['micro_state']}）")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# review（对抗审查轮次）
# ---------------------------------------------------------------------------
PASS_MARK = re.compile(r"复现成功[:：]?\s*(PASS|成功)")


def cmd_review(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    guard = ensure_not_takeover(state)
    if guard is not None:
        return guard
    # M1: 仅「审查结论」或「分析」（FAIL 回退态）受理 review，防 PASS 后被误用回滚
    if state["main_state"] not in ("审查结论", "分析"):
        return gate_reject(
            f"当前主状态「{state['main_state']}」不允许执行 review（仅「审查结论」/「分析」可审查）"
        )

    result = args.result.upper()
    if result not in ("PASS", "FAIL"):
        return fatal(f"--result 仅支持 PASS|FAIL，收到：{result}")
    if args.round < 1 or args.round > MAX_REVIEW_ROUNDS:
        return fatal(f"--round 范围 1..{MAX_REVIEW_ROUNDS}，收到：{args.round}")
    expected = state["review_round"] + 1
    if args.round != expected:
        return gate_reject(f"--round {args.round} 与 state.json 轮次（{state['review_round']}）不一致，应为 {expected}")

    # 审查对象产物必须存在
    ap = artifact_path(state, "analysis", args.dir)
    if not check_file_exists(ap):
        return gate_reject("问题分析结论.md 不存在或为空，无法审查")

    # PASS 时硬校验产物含复现成功标记（防自报 PASS 无产物）
    art_name = ARTIFACT_FILES["审查结论"][1].format(round=args.round)
    artifact_file = find_file_in_bugdir(state["bug_id"], args.dir, art_name)
    if result == "PASS":
        if not check_file_exists(artifact_file):
            return gate_reject(f"审查产物 {art_name} 不存在；PASS 必须由审查 agent 落盘该文件")
        content = artifact_file.read_text(encoding="utf-8", errors="replace")
        if not PASS_MARK.search(content):
            return gate_reject(f"审查产物 {art_name} 不含「复现成功：PASS/成功」标记，禁止 PASS")

    # 记录轮次
    entry = {
        "round": args.round,
        "result": result,
        "reproduced": result == "PASS",
        "issues": args.issues or "",
        "artifact": art_name,
    }
    state["review_rounds"].append(entry)
    state["artifacts"]["review"] = art_name
    state["artifacts"].setdefault("reviews", [])
    if art_name not in state["artifacts"]["reviews"]:
        state["artifacts"]["reviews"].append(art_name)
    state["review_round"] = args.round

    if result == "FAIL":
        if args.round < MAX_REVIEW_ROUNDS:
            # 回分析，重新取证
            state["main_state"] = "分析"
            state["micro_state"] = REVIEW_FAIL_BACK_TO
            append_timeline(state, "review_fail", "分析", REVIEW_FAIL_BACK_TO,
                            f"第{args.round}轮 FAIL：{args.issues}")
            print(f"第{args.round}轮审查 FAIL → 主状态回「分析」（微观：{REVIEW_FAIL_BACK_TO}）")
            print(f"  补充方向：{args.issues or '（见 审查结果-r%d.md）' % args.round}")
        else:
            state["escalated"] = True
            state["human_takeover"] = True
            append_timeline(state, "escalate", state["main_state"], state["micro_state"],
                            f"第{args.round}轮 FAIL，转人工接管")
            print(f"第{args.round}轮审查 FAIL（已达上限）→ 转人工接管，停止自动推进")
    else:
        state["gates"]["analysis_reviewed"] = True
        state["main_state"] = "出修改方案"
        state["micro_state"] = FIRST_MICRO["出修改方案"]
        append_timeline(state, "review_pass", "出修改方案", FIRST_MICRO["出修改方案"],
                        f"第{args.round}轮 PASS，复现成功")
        print(f"第{args.round}轮审查 PASS → gates.analysis_reviewed 置位，推进到「出修改方案」")

    save_state(state, args.dir)
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# record / jira
# ---------------------------------------------------------------------------
PHASES = ("analysis", "review", "plan", "coding", "device_verify", "jira")


def cmd_record(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    phase = args.phase
    if phase not in PHASES:
        return fatal(f"--phase 仅支持 {'/'.join(PHASES)}，收到：{phase}")
    if args.minutes < 0:
        return fatal("--minutes 必须 >= 0")

    wl = state["worklog"]["local"][phase]
    wl["minutes"] += args.minutes
    if args.note:
        wl["note"] = (wl["note"] + "；" if wl["note"] else "") + args.note
    state["worklog"]["total_minutes"] = sum(
        state["worklog"]["local"][p]["minutes"] for p in PHASES)
    append_timeline(state, "worklog", state["main_state"], state["micro_state"],
                    f"{phase} +{args.minutes} 分钟")
    save_state(state, args.dir)
    print(f"工时累计：{phase} 累计 {state['worklog']['local'][phase]['minutes']} 分钟，总计 {state['worklog']['total_minutes']} 分钟")
    print(progress_banner(state))
    return 0


JIRA_FLAGS = ("fetched", "analysis_comment_added", "conclusion_comment_added", "transition_done")


def cmd_jira(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    flag = args.flag
    if flag not in JIRA_FLAGS:
        return fatal(f"--flag 仅支持 {'/'.join(JIRA_FLAGS)}，收到：{flag}")
    value = args.value
    if value is None:
        # 未给 --value 则取反
        state["jira"][flag] = not state["jira"][flag]
    else:
        v = value.lower()
        if v not in ("true", "false"):
            return fatal("--value 仅支持 true|false")
        state["jira"][flag] = v == "true"
    append_timeline(state, "jira_flag", state["main_state"], state["micro_state"],
                    f"{flag}={state['jira'][flag]}")
    save_state(state, args.dir)
    print(f"JIRA 标志 {flag} = {state['jira'][flag]}")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# gate（设置/清除门禁）
# ---------------------------------------------------------------------------
# 人工确认型门禁：只能由 confirm 命令置位（要求 --by 确认人，留审计痕迹），
# 禁止用 gate 命令手拍 true 绕过"用户确认/人工验收/人工review/人工关单"。
HUMAN_CONFIRM_GATES = {"plan_confirmed", "manual_verify_passed", "pr_reviewed", "jira_closed"}
# 证据型门禁：置位须带 --evidence <存在非空文件>（编译日志/审查记录/自测报告路径），
# 防止仅凭口头声称置位。code_reviewed 可用审查产物，build_passed 可用编译日志。
EVIDENCE_GATES = {"code_reviewed", "build_passed"}


def cmd_gate(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    flag = args.flag
    if flag not in state["gates"]:
        return fatal(f"--flag 仅支持 {'/'.join(state['gates'])}，收到：{flag}")
    # worktree_ready 是工具链硬门禁：只能由 worktree-set（deploy_build 派生成功后自动调用）置位，
    # 禁止用 gate 命令手拍 true 绕过"编译机派生隔离 worktree"这一前置动作。
    if flag == "worktree_ready":
        return gate_reject(
            "worktree_ready 禁止用 gate 命令设置；请先在编译机执行 "
            "deploy_build --worktree fix-<BUG单号> 派生隔离 worktree（派生成功自动登记置位）"
        )
    if flag in HUMAN_CONFIRM_GATES:
        return gate_reject(
            f"{flag} 属于人工确认门禁，禁止用 gate 命令设置；"
            "请由确认人执行 confirm 命令（--by <确认人> [--note]）"
        )
    if flag == "analysis_reviewed":
        return gate_reject(
            "analysis_reviewed 只能由对抗审查 PASS（review --result PASS）自动置位；"
            "禁止用 gate 命令绕过对抗审查"
        )
    value = args.value
    if str(value).lower() in ("true", "1") and flag in EVIDENCE_GATES:
        if not args.evidence:
            return gate_reject(
                f"{flag} 是证据型门禁，置位必须携带证据：--evidence <存在且非空的文件路径>"
                "（code_reviewed 用审查记录，build_passed 用编译日志）"
            )
        ev = Path(args.evidence)
        if not ev.is_file() or ev.stat().st_size == 0:
            return gate_reject(f"证据文件不存在或为空：{args.evidence}")
    if value is None:
        state["gates"][flag] = not state["gates"][flag]
    else:
        v = str(value).lower()
        if v not in ("true", "false", "1", "0"):
            return fatal("--value 仅支持 true|false")
        state["gates"][flag] = v in ("true", "1")
    note = f"{flag}={state['gates'][flag]}"
    if flag in EVIDENCE_GATES and state["gates"][flag]:
        note += f"（evidence: {args.evidence}）"
    append_timeline(state, "gate", state["main_state"], state["micro_state"], note)
    save_state(state, args.dir)
    print(f"门禁 {flag} = {state['gates'][flag]}")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# worktree-set（编译机 worktree 派生成功后由 deploy_build 自动调用）
# ---------------------------------------------------------------------------
def cmd_worktree_set(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    if not args.name or not args.remote_dir:
        return fatal("--name 与 --remote-dir 必填")
    state["worktree"] = {
        "name": args.name,
        "remote_dir": args.remote_dir,
        "base_branch": args.base_branch or "",
        "at": now_iso(),
    }
    state["gates"]["worktree_ready"] = True
    append_timeline(state, "worktree_set", state["main_state"], state["micro_state"],
                    f"登记 worktree {args.name}@{args.remote_dir} → gates.worktree_ready 置位")
    save_state(state, args.dir)
    print(f"worktree 已登记：{args.name}（{args.remote_dir}），gates.worktree_ready = True")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# confirm（人工确认门禁专用：plan_confirmed/manual_verify_passed/pr_reviewed/jira_closed）
# ---------------------------------------------------------------------------
def cmd_confirm(args) -> int:
    """人工确认门禁置位。--by 必填（确认人标识，写入 timeline 留审计痕迹）；
    支持 --note 补充说明。禁止 agent 自行置位（见 cmd_gate 拦截）。"""
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    if args.flag not in HUMAN_CONFIRM_GATES:
        return fatal(f"--flag 仅支持 {'/'.join(sorted(HUMAN_CONFIRM_GATES))}，收到：{args.flag}")
    if not args.by:
        return fatal("--by 必填：确认人标识（如姓名/账号），用于审计留痕")
    state["gates"][args.flag] = True
    note = f"人工确认 {args.flag} by {args.by}"
    if args.note:
        note += f"：{args.note}"
    append_timeline(state, "confirm", state["main_state"], state["micro_state"], note)
    save_state(state, args.dir)
    print(f"✅ 人工确认门禁 {args.flag} = True（by {args.by}）")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------
def cmd_close(args) -> int:
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    guard = ensure_not_takeover(state)
    if guard is not None:
        return guard
    # H4: 只有处于「更新BUG单」（工单关闭阶段）才允许 close，防从任意状态直接闭环
    if state["main_state"] != "更新BUG单":
        return gate_reject(
            f"当前主状态「{state['main_state']}」，仅「更新BUG单」可 close（须先完成 PR/人工 review/关闭工单）"
        )
    if args.conclusion:
        cp = Path(args.conclusion)
        if not cp.is_absolute():
            cp = bug_dir(state["bug_id"], args.dir) / cp
        if not check_file_exists(cp):
            return gate_reject(f"结论文档不存在或为空：{cp}")
        # H3: 结论文档可能位于 npp 仓库根（bug-fix-state 之外），存完整路径而非文件名
        state["artifacts"]["conclusion"] = str(cp)
    missing = gate_prereq("结束", state, args.dir)
    if missing:
        return gate_reject(f"关闭门禁不满足：{('、'.join(missing))}")

    state["main_state"] = "结束"
    state["micro_state"] = ""
    append_timeline(state, "close", "结束", "", "状态机闭环")
    save_state(state, args.dir)
    print(f"已关闭：{state['bug_id']}，状态机闭环（主状态=结束）")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# reset（人工接管后复位续跑）
# ---------------------------------------------------------------------------
def cmd_reset(args) -> int:
    """人工接管（审查 3 轮 FAIL）经人工复核后，复位 human_takeover/escalated，回到「分析·取证」。"""
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    if not state.get("human_takeover"):
        return gate_reject("当前未处于人工接管状态，无需 reset")
    state["human_takeover"] = False
    state["escalated"] = False
    state["main_state"] = "分析"
    state["micro_state"] = REVIEW_FAIL_BACK_TO
    append_timeline(state, "reset", "分析", REVIEW_FAIL_BACK_TO, "人工复核后复位，重新分析")
    save_state(state, args.dir)
    print(f"已复位人工接管：{state['bug_id']} → 主状态「分析」/微观状态「{REVIEW_FAIL_BACK_TO}」，可重新分析")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# progress（进度总览快速刷新）
# ---------------------------------------------------------------------------
def cmd_progress(args) -> int:
    """输出可视化进度总览（主状态流水线 + 当前微观状态），供长程任务中快速定位「走到哪」。
    同时刷新 <bug-dir>/progress.md 进度卡片（旧状态文件首次查看时补齐）。"""
    state = load_state(args.bug_id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.bug_id, args.dir)}（先 init）")
    try:
        write_progress_md(state, args.dir)
    except (OSError, ValueError):
        pass
    print(render_progress(state))
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NF BUG 修复状态机引擎")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化 BUG 单状态机")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--module", default="")
    p.add_argument("--jira-key", default=None)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("state", help="查看状态快照")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--dir", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("progress", help="输出可视化进度总览（主状态流水线 + 当前微观状态）")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_progress)

    p = sub.add_parser("micro", help="推进微观状态")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--dir", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--note", default="")
    p.set_defaults(func=cmd_micro)

    p = sub.add_parser("advance", help="推进主状态")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("review", help="登记对抗审查轮次")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--result", required=True, choices=["PASS", "FAIL"])
    p.add_argument("--round", required=True, type=int)
    p.add_argument("--issues", default="", nargs="?", const="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("record", help="累计工时")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--phase", required=True)
    p.add_argument("--minutes", required=True, type=int)
    p.add_argument("--note", default="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("jira", help="置 JIRA 同步标志")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--flag", required=True)
    p.add_argument("--value", default=None)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_jira)

    p = sub.add_parser("gate", help="设置/清除门禁标志（人工确认/证据型门禁受限）")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--flag", required=True)
    p.add_argument("--value", default=None)
    p.add_argument("--evidence", default=None,
                   help="证据文件路径（code_reviewed/build_passed 置位 true 时必填，校验存在非空）")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("confirm", help="人工确认门禁置位（plan_confirmed/manual_verify_passed/pr_reviewed/jira_closed）")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--flag", required=True)
    p.add_argument("--by", required=True, help="确认人标识（姓名/账号），审计留痕必填")
    p.add_argument("--note", default="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_confirm)

    p = sub.add_parser("worktree-set", help="登记编译机 worktree 派生（deploy_build 成功派生后自动调用）")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--remote-dir", required=True)
    p.add_argument("--base-branch", default="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_worktree_set)

    p = sub.add_parser("gate-check", help="检查门禁")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_gate_check)

    p = sub.add_parser("resolve", help="断点恢复指引")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("close", help="关闭状态机")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--conclusion", default=None)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("reset", help="复位人工接管（人工复核后续跑）")
    p.add_argument("--bug-id", required=True)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_reset)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    # H1: --dir 统一转 Path（cmd 内均为 Path | None）
    if getattr(args, "dir", None):
        args.dir = Path(args.dir)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as e:
        return fatal(f"错误：{e}")


if __name__ == "__main__":
    sys.exit(main())
