#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analysis-only-workflow 状态机引擎（无 bug 单的简化分析闭环）

主状态：分析→审查结论→出修改方案→编码→结束（5 个，比 bug-fix-workflow 少 2 个）
微观状态沿用 bug-fix-workflow 命名约定，便于 LLM 习惯。
硬保留门禁：analysis_reviewed / plan_confirmed / code_reviewed（evidence 必填）
可选门禁：build_passed
主动关闭门禁：worktree_ready / selftest_done / basic_test_done / manual_verify_* / pr_reviewed / jira_closed

脚本锚定自身路径解析 workspace，跨子目录运行可。
退出码：0 成功；2 门禁拒绝；1 其他错误。
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Windows 控制台 UTF-8 强转
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _fix_utf8_argv() -> None:
    if sys.platform != "win32":
        return
    fixed = []
    for a in sys.argv:
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

# workspace 根 = 本文件上级四级（.dsh/skills/analysis-only-workflow/ -> .dsh/ -> 仓库根）
WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
SKILL_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SKILL_DIR / "templates"
# 状态目录锚定到 runtime/analysis/<SLUG>/，与 vpp-api-sync / ssh-tools / gdb-attach 等
# skill 的 runtime/<SESS>/ 约定一致；避免污染 workspace 根。
# 前置依赖：.dsh/rules/dirs.json 已包含 "runtime" 可写登记（restricted 模式门控）。
DEFAULT_STATE_DIR = WORKSPACE / "runtime" / "analysis"

LOCAL_TZ = timezone(timedelta(hours=8))

# 主状态 → 微观状态
MICRO_STATES = {
    "分析": ["取证", "假设", "验证", "结论"],
    "审查结论": ["审查", "复现", "判定", "轮次记账"],
    "出修改方案": ["方案草拟", "影响评估", "方案评审", "用户确认"],
    "编码": ["修改", "代码审查", "编译通过", "修复审查问题"],
    "结束": [],
}
MAIN_STATES = list(MICRO_STATES.keys())
FIRST_MICRO = {s: m[0] for s, m in MICRO_STATES.items() if m}

MAX_REVIEW_ROUNDS = 3

ARTIFACT_FILES = {
    "分析": ("analysis", "问题分析结论.md"),
    "审查结论": ("review", "审查结果-r{round}.md"),
    "出修改方案": ("plan", "修改方案.md"),
    "编码": ("code_review", "代码审查记录.md"),
}

REVIEW_FAIL_BACK_TO = "取证"


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def fatal(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def gate_reject(msg: str) -> int:
    print(f"[gate] 拒绝：{msg}", file=sys.stderr)
    return 2


def ensure_not_takeover(state: dict):
    if state.get("human_takeover"):
        return gate_reject("已转人工接管（审查 3 轮 FAIL），禁止自动推进。请人工复核后人工处理。")
    return None


def state_path(slug: str, state_dir: Path | None = None) -> Path:
    base = state_dir or DEFAULT_STATE_DIR
    return base / slug / "state.json"


def session_dir(slug: str, state_dir: Path | None = None) -> Path:
    base = state_dir or DEFAULT_STATE_DIR
    return base / slug


def load_state(slug: str, state_dir: Path | None = None):
    p = state_path(slug, state_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        # 损坏态：state.json 存在但解析失败。直接退出并打印完整恢复路径。
        # 注意：必须删除整个 session 目录（state.json + progress.md + 残留产物），
        # 仅删 state.json 后 cmd_init 仍会因目录非空拒绝覆盖（sess.exists() 检查）。
        print(f"[损坏] state.json 解析失败：{p}：{e}", file=sys.stderr)
        print(f"  恢复方式 A：rm -rf {p.parent}  （删除整个 session 目录后重新 init）", file=sys.stderr)
        print(f"  恢复方式 B：--dir <新路径> init  （指向新 session 目录）", file=sys.stderr)
        sys.exit(1)  # 损坏态是数据错误，非门禁拒绝；用 exit 1 与 gate_reject (exit 2) 区分
    except OSError as e:
        print(f"[IO 错误] 读 state.json 失败：{p}：{e}", file=sys.stderr)
        return None


def save_state(state: dict, state_dir: Path | None = None) -> None:
    p = state_path(state["slug"], state_dir)
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
        pass


def append_timeline(state: dict, event: str, main_state: str, micro_state: str, note: str = "") -> None:
    state["timeline"].append({
        "at": now_iso(),
        "event": event,
        "main_state": main_state,
        "micro_state": micro_state,
        "note": note,
    })


def progress_banner(state: dict) -> str:
    ms = state["main_state"]
    total = len(MAIN_STATES)
    idx = MAIN_STATES.index(ms) + 1 if ms in MAIN_STATES else total
    mis = state.get("micro_state") or ""
    return f"【进度 {idx}/{total} · {ms}" + (f" · {mis}" if mis else "") + "】"


def render_progress(state: dict) -> str:
    ms = state["main_state"]
    mis = state.get("micro_state") or ""
    idx = MAIN_STATES.index(ms) if ms in MAIN_STATES else len(MAIN_STATES)
    lines = [f"进度总览  {state['slug']}  {state['title'] or ''}".rstrip()]
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
    d = session_dir(state["slug"], state_dir)
    d.mkdir(parents=True, exist_ok=True)
    ms = state["main_state"]
    mis = state.get("micro_state") or ""
    total = len(MAIN_STATES)
    idx = MAIN_STATES.index(ms) + 1 if ms in MAIN_STATES else total
    gates_done = [k for k, v in state.get("gates", {}).items() if v]
    gates_pending = [k for k, v in state.get("gates", {}).items() if not v]
    lines = [
        f"# 进度 {state['slug']}",
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


def artifact_path(state: dict, key: str, state_dir: Path | None = None):
    name = state.get("artifacts", {}).get(key, "")
    if not name:
        return None
    p = Path(name)
    if p.is_absolute():
        return p
    return session_dir(state["slug"], state_dir) / name


def find_file_in_session(slug: str, state_dir: Path | None, name: str) -> Path:
    return session_dir(slug, state_dir) / name


def check_file_exists(path) -> bool:
    if path is None:
        return False
    return path.exists() and path.is_file() and path.stat().st_size > 0


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
def register_in_writable_dirs(session_dir_path: Path) -> None:
    """把新 session 状态目录登记进 restricted 门禁的可读写清单（dirs.json）。

    幂等：已登记的目录直接放行。同时兜底登记 runtime/ 根目录，
    防止 nf-hooks 因 runtime/ 未登记而拦截后续文件写入。

    降级策略：若 .dsh/tools/writable_dirs.py 不存在（本环境未部署门控工具），
    静默跳过并打 info 提示，由用户通过静态 dirs.json 配置兜底。
    """
    tool = WORKSPACE / ".dsh" / "tools" / "writable_dirs.py"
    if not tool.is_file():
        print(f"  [登记跳过] 未找到 {tool.name}（门控工具未部署），请确认 .dsh/rules/dirs.json 已包含 runtime 目录")
        return
    try:
        rel = session_dir_path.resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        print(f"  [登记跳过] 状态目录在 workspace 外，无需登记：{session_dir_path}")
        return
    # 1) 登记 session 目录自身
    r = subprocess_run_safe([sys.executable, str(tool), "add", rel.as_posix(), "分析闭环状态目录"])
    msg = (r.get("stdout") or r.get("stderr") or "").strip()
    if r["returncode"] == 0:
        print(f"  [门禁登记] {msg}")
    else:
        print(f"  [门禁登记警告] {msg}")
    # 2) 兜底登记 runtime/ 根（已在则幂等跳过）
    try:
        runtime_rel = (WORKSPACE / "runtime").resolve().relative_to(WORKSPACE.resolve()).as_posix()
        r2 = subprocess_run_safe([sys.executable, str(tool), "add", runtime_rel, "运行时目录（skill 临时产物）"])
        msg2 = (r2.get("stdout") or r2.get("stderr") or "").strip()
        if r2["returncode"] == 0 and msg2:
            print(f"  [门禁登记] {msg2}")
        # 重复登记正常静默
    except ValueError:
        pass  # workspace 外场景已在上面跳过


def subprocess_run_safe(cmd, **kwargs):
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}, **kwargs)
    return {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def cmd_init(args) -> int:
    slug = args.id.strip()
    if not slug:
        return fatal("--id 必填")
    if not re.match(r"^[A-Za-z0-9_.\-]+$", slug):
        return fatal(f"--id 含非法字符：{slug}（仅允许字母数字_.-）")
    if slug in (".", "..") or slug.endswith("/..") or slug.endswith("/."):
        return fatal(f"--id 非法路径：{slug}")

    base = args.dir if args.dir else DEFAULT_STATE_DIR
    sess = session_dir(slug, base)
    if sess.exists():
        return fatal(f"目标目录已存在，禁止覆盖：{sess}")
    if not TEMPLATES_DIR.is_dir():
        return fatal(f"模板目录不存在：{TEMPLATES_DIR}")

    sess.mkdir(parents=True)
    register_in_writable_dirs(sess)

    state = {
        "schema_version": 1,
        "slug": slug,
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
            "code_review": "",
            "conclusion": "",
        },
        "gates": {
            "analysis_reviewed": False,
            "plan_confirmed": False,
            "code_reviewed": False,
            "build_passed": False,  # 可选
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
                "conclusion": {"minutes": 0, "note": ""},
            },
            "total_minutes": 0,
        },
    }
    append_timeline(state, "init", "分析", "取证", "创建状态机")
    save_state(state, base)
    print(f"已初始化：{sess}")
    print(f"  产物模板不预复制：按 templates/ 结构创建产物文件（门禁按文件名校验）")
    print(f"  主状态：分析 / 微观状态：取证")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# state / gate-check / resolve / progress
# ---------------------------------------------------------------------------
def cmd_state(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    try:
        write_progress_md(state, args.dir)
    except (OSError, ValueError):
        pass
    print(render_progress(state))
    print(f"SLUG: {state['slug']}  {state['title']}")
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
    print(f"  工时累计：{state['worklog']['total_minutes']} 分钟")
    return 0


def cmd_gate_check(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    ms = state["main_state"]
    print(render_progress(state))
    print(f"当前主状态：{ms}  微观状态：{state['micro_state']}")
    missing_art = []
    for cur, (_, name) in ARTIFACT_FILES.items():
        if cur == "审查结论":
            continue
        if MAIN_STATES.index(cur) >= MAIN_STATES.index(ms):
            continue
        p = find_file_in_session(state["slug"], args.dir, name)
        if not check_file_exists(p):
            missing_art.append(name)
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
    next_main = next_main_state(ms)
    if next_main == "结束":
        print("  下一步建议：完成所有门禁后推进到「结束」并 close")
    else:
        prereq = gate_prereq(next_main, state, args.dir)
        if prereq:
            print(f"  可推进到「{next_main}」，门禁需满足：" + "、".join(prereq))
        else:
            print(f"  「{next_main}」门禁已满足，可 advance")
    return 0


def cmd_resolve(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    ms, mis = state["main_state"], state["micro_state"]
    print(render_progress(state))
    print(f"=== 断点恢复：{state['slug']} ===")
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
        print("下一步：确认修改方案.md 后由用户执行 confirm --flag plan_confirmed，再 advance 到 编码。")
    elif ms == "编码":
        print("下一步：完成代码审查（code_reviewed，可选 build_passed）后 advance 到 结束 + close。")
    else:
        print("已结束。")
    return 0


def cmd_progress(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    try:
        write_progress_md(state, args.dir)
    except (OSError, ValueError):
        pass
    print(render_progress(state))
    return 0


# ---------------------------------------------------------------------------
# micro / advance
# ---------------------------------------------------------------------------
def cmd_micro(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
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


def gate_prereq(next_main: str, state: dict, state_dir: Path | None) -> list:
    missing = []
    slug = state["slug"]
    if next_main == "审查结论":
        p = find_file_in_session(slug, state_dir, ARTIFACT_FILES["分析"][1])
        if not check_file_exists(p):
            missing.append("问题分析结论.md 不存在或为空")
    elif next_main == "出修改方案":
        if not state["gates"].get("analysis_reviewed"):
            missing.append("gates.analysis_reviewed 未置位（审查未 PASS）")
    elif next_main == "编码":
        p = find_file_in_session(slug, state_dir, ARTIFACT_FILES["出修改方案"][1])
        if not check_file_exists(p):
            missing.append("修改方案.md 不存在")
        if not state["gates"].get("plan_confirmed"):
            missing.append("gates.plan_confirmed 未置位（用户未确认方案）")
    elif next_main == "结束":
        # code_reviewed 必须 + 可选 build_passed（如已置位则要求 evidence，但 build_passed 本身可选）
        p = find_file_in_session(slug, state_dir, ARTIFACT_FILES["编码"][1])
        if not check_file_exists(p):
            missing.append("代码审查记录.md 不存在")
        if not state["gates"].get("code_reviewed"):
            missing.append("gates.code_reviewed 未置位（代码审查未通过）")
        if not state["gates"].get("analysis_reviewed"):
            missing.append("gates.analysis_reviewed 未置位")
        if not state["gates"].get("plan_confirmed"):
            missing.append("gates.plan_confirmed 未置位")
    return missing


def cmd_advance(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
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
        return gate_reject(f"推进到「{to}」门禁不满足：{'、'.join(missing)}")
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
# review
# ---------------------------------------------------------------------------
PASS_MARK = re.compile(r"复现成功[:：]?\s*(PASS|成功)")


def cmd_review(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    guard = ensure_not_takeover(state)
    if guard is not None:
        return guard
    if state["main_state"] not in ("审查结论", "分析"):
        return gate_reject(f"当前主状态「{state['main_state']}」不允许执行 review（仅「审查结论」/「分析」可审查）")
    result = args.result.upper()
    if result not in ("PASS", "FAIL"):
        return fatal(f"--result 仅支持 PASS|FAIL，收到：{result}")
    if args.round < 1 or args.round > MAX_REVIEW_ROUNDS:
        return fatal(f"--round 范围 1..{MAX_REVIEW_ROUNDS}，收到：{args.round}")
    expected = state["review_round"] + 1
    if args.round != expected:
        return gate_reject(f"--round {args.round} 与 state.json 轮次（{state['review_round']}）不一致，应为 {expected}")
    ap = artifact_path(state, "analysis", args.dir)
    if not check_file_exists(ap):
        return gate_reject("问题分析结论.md 不存在或为空，无法审查")
    art_name = ARTIFACT_FILES["审查结论"][1].format(round=args.round)
    artifact_file = find_file_in_session(state["slug"], args.dir, art_name)
    if result == "PASS":
        if not check_file_exists(artifact_file):
            return gate_reject(f"审查产物 {art_name} 不存在；PASS 必须由审查 agent 落盘该文件")
        content = artifact_file.read_text(encoding="utf-8", errors="replace")
        if not PASS_MARK.search(content):
            return gate_reject(f"审查产物 {art_name} 不含「复现成功：PASS/成功」标记，禁止 PASS")
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
            state["main_state"] = "分析"
            state["micro_state"] = REVIEW_FAIL_BACK_TO
            append_timeline(state, "review_fail", "分析", REVIEW_FAIL_BACK_TO, f"第{args.round}轮 FAIL：{args.issues}")
            print(f"第{args.round}轮审查 FAIL → 主状态回「分析」（微观：{REVIEW_FAIL_BACK_TO}）")
            print(f"  补充方向：{args.issues or f'（见 {art_name}）'}")
        else:
            state["escalated"] = True
            state["human_takeover"] = True
            append_timeline(state, "escalate", state["main_state"], state["micro_state"], f"第{args.round}轮 FAIL，转人工接管")
            print(f"第{args.round}轮审查 FAIL（已达上限）→ 转人工接管，停止自动推进")
    else:
        state["gates"]["analysis_reviewed"] = True
        state["main_state"] = "出修改方案"
        state["micro_state"] = FIRST_MICRO["出修改方案"]
        append_timeline(state, "review_pass", "出修改方案", FIRST_MICRO["出修改方案"], f"第{args.round}轮 PASS，复现成功")
        print(f"第{args.round}轮审查 PASS → gates.analysis_reviewed 置位，推进到「出修改方案」")
    save_state(state, args.dir)
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# record
# ---------------------------------------------------------------------------
PHASES = ("analysis", "review", "plan", "coding", "conclusion")


def cmd_record(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
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
    append_timeline(state, "worklog", state["main_state"], state["micro_state"], f"{phase} +{args.minutes} 分钟")
    save_state(state, args.dir)
    print(f"工时累计：{phase} 累计 {state['worklog']['local'][phase]['minutes']} 分钟，总计 {state['worklog']['total_minutes']} 分钟")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# gate / confirm
# ---------------------------------------------------------------------------
HUMAN_CONFIRM_GATES = {"plan_confirmed"}  # 仅 plan_confirmed 需要用户确认；close 由 confirm jira_closed 不需要
EVIDENCE_GATES = {"code_reviewed", "build_passed"}


def cmd_gate(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    flag = args.flag
    if flag not in state["gates"]:
        return fatal(f"--flag 仅支持 {'/'.join(state['gates'])}，收到：{flag}")
    if flag in HUMAN_CONFIRM_GATES:
        return gate_reject(f"{flag} 属于人工确认门禁，禁止用 gate 命令设置；请由确认人执行 confirm 命令（--by <确认人> [--note]）")
    if flag == "analysis_reviewed":
        return gate_reject("analysis_reviewed 只能由对抗审查 PASS（review --result PASS）自动置位；禁止用 gate 命令绕过对抗审查")
    value = args.value
    if str(value).lower() in ("true", "1") and flag in EVIDENCE_GATES:
        if not args.evidence:
            return gate_reject(f"{flag} 是证据型门禁，置位必须携带证据：--evidence <存在且非空的文件路径>")
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


def cmd_confirm(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    if args.flag not in HUMAN_CONFIRM_GATES:
        return fatal(f"--flag 仅支持 {'/'.join(sorted(HUMAN_CONFIRM_GATES))}，收到：{args.flag}")
    if not args.by:
        return fatal("--by 必填：确认人标识（姓名/账号），用于审计留痕")
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
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    guard = ensure_not_takeover(state)
    if guard is not None:
        return guard
    if state["main_state"] != "编码":
        return gate_reject(f"当前主状态「{state['main_state']}」，仅「编码」完成后可 close（须先 advance 到 编码 + code_reviewed 置位）")
    if args.conclusion:
        cp = Path(args.conclusion)
        if not cp.is_absolute():
            cp = session_dir(state["slug"], args.dir) / cp
        if not check_file_exists(cp):
            return gate_reject(f"结论文档不存在或为空：{cp}")
        state["artifacts"]["conclusion"] = str(cp)
    missing = gate_prereq("结束", state, args.dir)
    if missing:
        return gate_reject(f"关闭门禁不满足：{'、'.join(missing)}")
    state["main_state"] = "结束"
    state["micro_state"] = ""
    append_timeline(state, "close", "结束", "", "状态机闭环")
    save_state(state, args.dir)
    print(f"已关闭：{state['slug']}，状态机闭环（主状态=结束）")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------
def cmd_reset(args) -> int:
    state = load_state(args.id, args.dir)
    if state is None:
        return fatal(f"状态文件不存在：{state_path(args.id, args.dir)}（先 init）")
    if not state.get("human_takeover"):
        return gate_reject("当前未处于人工接管状态，无需 reset")
    state["human_takeover"] = False
    state["escalated"] = False
    state["main_state"] = "分析"
    state["micro_state"] = REVIEW_FAIL_BACK_TO
    append_timeline(state, "reset", "分析", REVIEW_FAIL_BACK_TO, "人工复核后复位，重新分析")
    save_state(state, args.dir)
    print(f"已复位人工接管：{state['slug']} → 主状态「分析」/微观状态「{REVIEW_FAIL_BACK_TO}」，可重新分析")
    print(progress_banner(state))
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="analysis-only-workflow 状态机引擎（无 bug 单的简化分析闭环）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化 session 状态机")
    p.add_argument("--id", required=True, dest="id", help="session slug（仅字母数字_.-）")
    p.add_argument("--title", default="")
    p.add_argument("--module", default="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("state", help="查看状态快照")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--dir", default=None)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("progress", help="输出可视化进度总览")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_progress)

    p = sub.add_parser("micro", help="推进微观状态")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--to", required=True)
    p.add_argument("--dir", default=None)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_micro)

    p = sub.add_parser("advance", help="推进主状态")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--to", required=True)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("review", help="登记对抗审查轮次")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--result", required=True, choices=["PASS", "FAIL"])
    p.add_argument("--round", required=True, type=int)
    p.add_argument("--issues", default="", nargs="?", const="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("record", help="累计工时")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--phase", required=True)
    p.add_argument("--minutes", required=True, type=int)
    p.add_argument("--note", default="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("gate", help="设置/清除门禁（人工确认门禁受限）")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--flag", required=True)
    p.add_argument("--value", default=None)
    p.add_argument("--evidence", default=None)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("confirm", help="人工确认门禁置位（plan_confirmed）")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--flag", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--note", default="")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_confirm)

    p = sub.add_parser("gate-check", help="检查门禁")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_gate_check)

    p = sub.add_parser("resolve", help="断点恢复指引")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("close", help="关闭状态机")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--conclusion", default=None)
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("reset", help="复位人工接管")
    p.add_argument("--id", required=True, dest="id")
    p.add_argument("--dir", default=None)
    p.set_defaults(func=cmd_reset)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "dir", None):
        args.dir = Path(args.dir)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as e:
        return fatal(f"错误：{e}")


if __name__ == "__main__":
    sys.exit(main())