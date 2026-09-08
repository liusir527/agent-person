#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""path_guard.py — 运行时产物路径静态检查器

强制执行 hooks/AGENT.md「运行时产物纪律」：
  状态机/脚本内的落点常量（DEFAULT_STATE_DIR / OUTPUT_DIR / out_dir / STATE_DIR 等）
  默认值必须指向 runtime/ 子目录，禁止仓库根平铺（analysis-state/ / bug-fix-state/ /
  feature-state/ / tmp/ 等）。

用法：
  # 1) 检查单个 Python 文件
  python .dsh/tools/path_guard.py check <path-to-py>

  # 2) 扫描整个 .dsh/skills/ 目录
  python .dsh/tools/path_guard.py scan

  # 3) 校验指定落点路径是否合规（供脚本运行时自检）
  python .dsh/tools/path_guard.py validate-path <abs-or-rel-path>

退出码：
  0  全部通过
  2  发现违规
  1  其他错误

设计取舍：
  - 静态检查（grep + 正则），不解析 AST；足够覆盖 99% 误写。
  - 不修改源文件，只报告违规行号与建议替换。
  - 不强制修改 build_passed / pr_reviewed / jira_closed 等 JIRA 流程相关常量（不属于
    落点常量，跳过）。

与 nf-hooks 的关系：
  - nf-hooks 是文件工具的路径放行门控（基于 dirs.json 白名单），与本检查器正交。
  - 本检查器是 skill / 脚本源代码的合规门控，两层一起构成「运行时产物纪律」的硬约束。
"""
import argparse
import re
import sys
from pathlib import Path

# 仓库根（与 state_machine.py 同源锚定法）
WORKSPACE = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = WORKSPACE / ".dsh" / "skills"

# 违规模式（落点常量定义 + 平铺路径前缀）
FORBIDDEN_DIR_NAMES = (
    "analysis-state",
    "bug-fix-state",
    "feature-state",
    "tmp",
)
# 合规模式（runtime/ 子目录）
ALLOWED_PREFIX = "runtime"

# 落点常量名（与 state_machine.py 惯例对齐）
PATH_CONST_NAMES = (
    "DEFAULT_STATE_DIR",
    "OUTPUT_DIR",
    "STATE_DIR",
    "OUT_DIR",
    "LOG_DIR",
    "TEMP_DIR",
    "RUNTIME_DIR",
    "out_dir",   # 小写变体，文档/小项目可能用
)

# 匹配 `NAME = Path("...")` 或 `NAME = WORKSPACE / "..."` 等模式
CONST_RE = re.compile(
    rf'^\s*({"|".join(PATH_CONST_NAMES)})\s*=\s*(.+)',
    re.MULTILINE,
)

# 字符串字面量匹配（含单引号/双引号/Path 表达式）
STR_LIT_RE = re.compile(r"""(['"])([^'"\n]+?)\1""")
PATH_EXPR_RE = re.compile(r'WORKSPACE\s*/\s*[\'"]?([^/\'"\n]+)[\'"]?')


def _extract_path_literals(expr: str) -> list[str]:
    """从 `WORKSPACE / "x" / "y"` 或 `Path("x/y")` 等表达式提取所有字符串片段。"""
    fragments = []
    # Path("...") 形式
    for m in STR_LIT_RE.finditer(expr):
        fragments.append(m.group(2))
    # WORKSPACE / "..." 形式
    for m in PATH_EXPR_RE.finditer(expr):
        fragments.append(m.group(1))
    return fragments


def _is_violation(fragments: list[str]) -> tuple[bool, str]:
    """判断 fragments 列表是否含违规路径前缀。

    违规判定：fragment 中第一个非 'runtime' 的目录段在 `fallback_dirs` 里。
    """
    if not fragments:
        return False, ""
    first = fragments[0]
    if first == ALLOWED_PREFIX:
        return False, ""
    if first in FORBIDDEN_DIR_NAMES:
        return True, f"常量默认落点 '{first}' 违反运行时产物纪律（应在 runtime/ 子目录下）"
    # 其他情况：目录名不在禁用清单，视为合规
    return False, ""


def check_python_file(py_path: Path) -> list[dict]:
    """扫描单个 .py 文件，返回违规清单（每条含 file / line / const / expr / reason）。"""
    violations = []
    try:
        content = py_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    for m in CONST_RE.finditer(content):
        const_name = m.group(1)
        expr = m.group(2).strip()
        # 仅看本行（避免跨行误判）
        line_text = m.group(0).strip()
        line_no = content[: m.start()].count("\n") + 1
        fragments = _extract_path_literals(line_text)
        is_bad, reason = _is_violation(fragments)
        if is_bad:
            violations.append({
                "file": str(py_path),
                "line": line_no,
                "const": const_name,
                "expr": line_text,
                "reason": reason,
            })
    return violations


def cmd_check(args) -> int:
    p = Path(args.path).resolve()
    if not p.is_file():
        print(f"路径不存在或不是文件：{p}", file=sys.stderr)
        return 1
    violations = check_python_file(p)
    if not violations:
        print(f"OK: {p}")
        return 0
    print(f"[违规] {p}：发现 {len(violations)} 处违规")
    for v in violations:
        print(f"  L{v['line']} {v['const']} = {v['expr']}")
        print(f"        → {v['reason']}")
        print(f"        → 建议替换为：WORKSPACE / 'runtime' / '<new-class>' / '<SESS>'")
    return 2


def cmd_scan(args) -> int:
    """扫描 .dsh/skills/ 下所有 state_machine.py 与 skill 根目录的 *.py。"""
    if not SKILLS_DIR.is_dir():
        print(f"skills 目录不存在：{SKILLS_DIR}", file=sys.stderr)
        return 1
    all_violations: list[dict] = []
    files_scanned = 0
    for py in sorted(SKILLS_DIR.rglob("*.py")):
        # 跳过 __pycache__/（Python 字节码缓存，不入库；详见 SKILL_AUTHORING.md §9.5）
        if "__pycache__" in py.parts:
            continue
        files_scanned += 1
        all_violations.extend(check_python_file(py))
    print(f"扫描完成：{files_scanned} 个 .py 文件，发现 {len(all_violations)} 处违规")
    for v in all_violations:
        print(f"  {v['file']}:L{v['line']} {v['const']} = {v['expr']}")
        print(f"        → {v['reason']}")
    if all_violations:
        return 2
    return 0


def cmd_validate_path(args) -> int:
    """校验给定路径是否合规（供 skill 运行时自检）。"""
    p = Path(args.path).resolve()
    try:
        rel = p.relative_to(WORKSPACE.resolve())
    except ValueError:
        print(f"路径在 workspace 外，无需校验：{p}")
        return 0
    parts = rel.parts
    if not parts:
        return 2
    first = parts[0]
    if first == ALLOWED_PREFIX:
        print(f"OK: {p}（runtime/ 下合规）")
        return 0
    if first in FORBIDDEN_DIR_NAMES:
        print(f"[违规] {p}：首段目录 '{first}' 违反运行时产物纪律", file=sys.stderr)
        return 2
    print(f"OK: {p}（首段目录 '{first}' 不在禁用集合）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行时产物路径静态检查器")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("check", help="检查单个 Python 文件")
    p.add_argument("path", help=".py 文件路径")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("scan", help="扫描 .dsh/skills/ 下所有 .py")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("validate-path", help="校验给定路径是否落在合规目录")
    p.add_argument("path", help="要校验的绝对或相对路径")
    p.set_defaults(func=cmd_validate_path)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (KeyError, ValueError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())