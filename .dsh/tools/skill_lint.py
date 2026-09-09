#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_lint.py — .dsh/skills/ 下 skill 全套规约硬校验器（零第三方依赖，仅 stdlib）。

用法：
  python .dsh/tools/skill_lint.py                 # 扫描 .dsh/skills/ 全部 skill
  python .dsh/tools/skill_lint.py --path <dir>    # 只校验单个 skill 目录
  python .dsh/tools/skill_lint.py --verbose       # 连 WARN 也逐条列出（默认只列 ERROR + 汇总 WARN 数）

退出码：0 = 无 ERROR（WARN 允许）；1 = 存在 ERROR（禁止交付）。

ERROR  = 违反硬性规约，必须修复（与 DSH 加载器/仓库规约冲突或会导致 skill 静默失效）。
WARN   = 规约建议项 / 潜在风险，不阻断交付但应知晓。

规约依据：.dsh/skills/SKILL_AUTHORING.md（目录命名、并 frontmatter、引用完整性、必含章节）
          + .dsh/skills/<skill>/SKILL.md 自引用。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与辅助
# ---------------------------------------------------------------------------

SKILL_DIR_NAME_RE = r"^[a-z0-9-]+$"  # 目录名：仅小写字母/数字/连字符
FRONTMATTER_KNOWN_KEYS = {           # 白名单；其余字段按 WARN 提示（防 DSH 未来加新合法字段误杀）
    "name",
    "description",
    "whenToUse",
    "user-invocable",
    "disable-model-invocation",
    # 存量 skill 实证使用中的团队自定义字段（收编进白名单避免每次体检噪声）
    "allowed-tools",
    "author",
    "version",
    "origin",
}
DESC_LEN_WARN = 500    # description 超此长度 → WARN（superpower 建议 ≤500）
DESC_LEN_ERROR = 1000  # 超此长度 → ERROR（贴近 DSH 前端对 frontmatter 总长的现实约束）


# ---------------------------------------------------------------------------
# frontmatter 解析（零依赖简易 YAML 子集）
# ---------------------------------------------------------------------------

class FmError(Exception):
    """frontmatter 无法解析时抛出。"""


def parse_frontmatter(raw: str):
    """解析 SKILL.md 头部的 YAML frontmatter。

    要求：首行必须是 '---'，之后到下一个独立 '---' 行为 frontmatter 文本。
    解析：逐行按 'key: value' 处理；后续以空白开头的行并入上一个 value
    （continuation）。返回 (dict[str, str], body)。无 frontmatter 返回 (None, raw)。
    解析失败抛 FmError。

    与 DSH 加载器对齐：DSH 用 YAML 解析 frontmatter，mapping 中出现裸 scalar 行
    （如全角冒号 'key：value' 会整体被当成裸字符串）会导致解析失败、skill 被忽略。
    """
    lines = raw.splitlines()
    if not lines or not lines[0].strip() == "---":
        return None, raw
    fm_lines: list[str] = []
    body_start = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            body_start = idx + 1
            break
        fm_lines.append(lines[idx])
    if body_start is None:
        raise FmError("未找到 frontmatter 结束标记 '---'")
    fields: dict[str, str] = {}
    cur_key = None
    for ln in fm_lines:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if ln[:1] in (" ", "\t", "-", "*"):
            if ln.lstrip().startswith(("-", "*")) and cur_key is not None:
                # YAML 列表项并入上一个 value（dsl: description 多行列表等）
                fields[cur_key] = fields.get(cur_key, "") + " " + ln.strip()
            elif cur_key is not None:
                fields[cur_key] = fields.get(cur_key, "") + " " + ln.strip()
            continue
        m = __import__("re").match(r"^([^:\n]+):\s*(.*)$", ln)
        if not m:
            raise FmError(
                f"无法解析的 frontmatter 行: {ln!r}（应为 'key: value' 形式；"
                "注意中文全角冒号 '：' 会让该行变成裸文本，导致 YAML 解析失败、DSH 不加载）"
            )
        key, val = m.group(1).strip(), m.group(2).strip()
        if key in fields and cur_key == key:
            fields[key] = fields[key] + " " + val
        else:
            fields[key] = val
        cur_key = key
    body = "\n".join(lines[body_start:]).strip()
    return fields, body


# ---------------------------------------------------------------------------
# 路径引用提取与校验
# ---------------------------------------------------------------------------

import re as _re

# 形如 references/xxx.md、references/{a,b}.md、templates/xxx 、templates/{a,b}.txt
_REF_TOKEN = _re.compile(r"(?:^|[^\w./-])(references|templates)/([A-Za-z0-9_.\-{},\s]+)")


def _expand_braces(seg: str):
    """展开花括号枚举：{a,b} -> [a, b]；无花括号时原样返回。"""
    seg = seg.strip().rstrip(".,;:()")
    if "{" not in seg:
        return [seg] if seg else []
    parts = []
    m = _re.search(r"\{([^}]*)\}", seg)
    if not m:
        return [seg] if seg else []
    for item in m.group(1).split(","):
        if item.strip():
            parts.append(seg[: m.start()] + item.strip() + seg[m.end():])
    return parts


def check_path_refs(skill_dir: Path, body: str) -> list[str]:
    """校验 SKILL.md 正文对 references/、templates/ 的相对引用是否存在。

    返回 ERROR 消息列表（空 = 通过）。形如 references/{a,b}.md 的引用会展开逐个校验。
    注意：仅校验 references/ 与 templates/ 这两个语义明确的"skill 自身子目录"前缀；
    正文里提到的外部资源（.dsh/env_config/*.json、hooks/AGENT.md、兄弟 skill 文件等）
    不属于本 skill 目录，不在此列，避免误报。
    """
    errors: list[str] = []
    for kind, seg in _REF_TOKEN.findall(body):
        for name in _expand_braces(seg):
            target = skill_dir / kind / name
            if not target.exists():
                errors.append(f"正文引用缺失: {kind}/{name} 实际不存在")
    return errors


# ---------------------------------------------------------------------------
# 关键章节检查（WARN 级——SKILL_AUTHORING.md 4.1 推荐项，不强杀存量）
# ---------------------------------------------------------------------------

_SECTION_PATTERNS = {
    "触发词/触发条件": r"触发(词|条件)?",
    "使用说明/阶段路由/流程主体": r"(何时使用|阶段路由|核心流程|使用说明|使用方式|工作流|操作流程|概览|流程|Usage)",
}


def check_sections(body: str) -> list[str]:
    """按 SKILL_AUTHORING.md 4.1 校验推荐章节；缺失返回 WARN 消息列表。"""
    miss = [label for label, pat in _SECTION_PATTERNS.items()
            if not _re.search(pat, body, _re.IGNORECASE)]
    return [f"建议补充章节/关键词: {label}（SKILL_AUTHORING.md 4.1 推荐项）" for label in miss]


# ---------------------------------------------------------------------------
# 单个 skill 校验
# ---------------------------------------------------------------------------

def lint_skill(skill_dir: Path, verbose: bool) -> tuple[int, int, list[str]]:
    """校验单个 skill 目录。返回 (error_count, warn_count, 输出行列表)。"""
    errors: list[str] = []
    warns: list[str] = []
    name = skill_dir.name

    # 1. 目录名
    if not _re.match(SKILL_DIR_NAME_RE, name):
        errors.append(f"目录名不合法 {name!r}（仅允许小写字母/数字/连字符）")

    # 2. SKILL.md 存在
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        errors.append("缺少 SKILL.md（加载器只识别 <skill>/SKILL.md）")
        return len(errors), len(warns), _emit(errors, warns, name, verbose)

    raw = skill_file.read_text(encoding="utf-8", errors="replace")
    try:
        fm, body = parse_frontmatter(raw)
    except FmError as e:
        errors.append(f"frontmatter 解析失败: {e}")
        return len(errors), len(warns), _emit(errors, warns, name, verbose)

    # 3. frontmatter 存在
    if fm is None:
        errors.append("缺少 YAML frontmatter（首行必须为 ---；DSH 加载器将直接忽略本 skill）")

    if fm is not None:
        # 4. name / description 必填
        for key in ("name", "description"):
            val = fm.get(key, "")
            if not val or not val.strip():
                errors.append(f"frontmatter 缺少必填字段: {key}")
        # 5. name 合法性
        fname = fm.get("name", "")
        if fname and not _re.match(SKILL_DIR_NAME_RE, fname):
            errors.append(f"frontmatter name 不合法 {fname!r}（仅允许小写字母/数字/连字符）")
        # 6. name 与目录名不一致（存量 gdb-tools/gdb-attach 即为该形态，DSH 仍可加载 → WARN）
        if fname and fname != name:
            warns.append(f"frontmatter name={fname!r} 与目录名 {name!r} 不一致（DSH 以 name 注册，请确认有意为之）")
        # 7. description 长度
        dlen = len(fm.get("description", ""))
        if dlen > DESC_LEN_ERROR:
            errors.append(f"description 过长（{dlen} 字符 > {DESC_LEN_ERROR}），可能导致前端/加载器截断")
        elif dlen > DESC_LEN_WARN:
            warns.append(f"description 偏长（{dlen} 字符 > {DESC_LEN_WARN} 建议上限）")
        # 8. 未知字段
        unknown = sorted(set(fm) - FRONTMATTER_KNOWN_KEYS)
        if unknown:
            warns.append(f"frontmatter 含未知字段: {', '.join(unknown)}（若为 DSH 新合法字段请更新白名单）")

    # 9. 正文引用完整性（ERROR）+ 建议章节（WARN）
    if body:
        errors += check_path_refs(skill_dir, body)
        warns += check_sections(body)

    return len(errors), len(warns), _emit(errors, warns, name, verbose)


def _emit(errors: list[str], warns: list[str], name: str, verbose: bool) -> list[str]:
    lines: list[str] = []
    for msg in errors:
        lines.append(f"[ERROR] {name}: {msg}")
    if verbose or errors:
        for msg in warns:
            lines.append(f"[WARN ] {name}: {msg}")
    elif warns:
        lines.append(f"[WARN ] {name}: ({len(warns)} 条，--verbose 查看)")
    if not errors and not warns:
        lines.append(f"[OK   ] {name}")
    return lines


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=".dsh/skills/ 全套规约硬校验器（exit 1 = 有 ERROR）")
    ap.add_argument("--path", type=str, default=None,
                    help="只校验指定 skill 目录；缺省扫描 .dsh/skills/ 全部")
    ap.add_argument("--verbose", action="store_true", help="连 WARN 逐条输出")
    args = ap.parse_args()

    skills_root = Path(__file__).resolve().parent.parent / "skills"
    if args.path:
        targets = [Path(args.path).resolve()]
        if not targets[0].is_dir():
            print(f"FATAL: {args.path} 不是目录", file=sys.stderr)
            return 2
    else:
        if not skills_root.is_dir():
            print(f"FATAL: 未找到 skills 根目录 {skills_root}", file=sys.stderr)
            return 2
        targets = sorted(p for p in skills_root.iterdir() if p.is_dir())

    all_lines: list[str] = []
    n_ok = n_err = n_warn = 0
    for t in targets:
        e, w, lines = lint_skill(t, args.verbose)
        n_err += e
        n_warn += w
        n_ok += 1 if (e == 0 and w == 0) else 0
        all_lines += lines

    print("\n".join(all_lines))
    print("-" * 60)
    print(f"checked {len(targets)} skill(s): {n_ok} OK, {n_err} ERROR, {n_warn} WARN")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())