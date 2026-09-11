#!/usr/bin/env python3
"""
hive_spawn.py - 蜂巢派生工具（Hive Brain M4）

派生 agent 通过配置继承蜂巢全量能力：
- spawn：校验派生配置 → 展开基座模板 → 生成 agent 文件骨架
- sync ：蜂巢变更后重展开所有派生 agent 的基座段（保留特异操作段）

设计约束（v0.3）：
- N5 唯一事实源：spawn/sync 只读 .dsh-memory/hive.yaml + 基座模板，杜绝能力清单两处漂移
- N6 定位标记：基座段用 <!-- HIVE-BASE-START/END --> 包裹，sync 只替换标记内（不靠标题文本）
- R3 递归顺序：嵌套继承（A→B→C）sync 沿继承链自顶向下（基座→A→B→C）
- R4 角色裁剪：skills 按角色裁剪，不机械全量

用法:
    python hive_spawn.py spawn <name> [--inherits hive/base] [--scene develop|debug]
    python hive_spawn.py sync
    python hive_spawn.py list
"""

import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent   # .dsh/tools/ -> 主仓根
HIVE_YAML = REPO_ROOT / '.dsh-memory' / 'hive.yaml'
BASE_MD = REPO_ROOT / '.dsh' / 'agents' / 'hive' / 'base.md'
AGENTS_DIR = REPO_ROOT / '.dsh' / 'agents'

BASE_START = '<!-- HIVE-BASE-START -->'
BASE_END = '<!-- HIVE-BASE-END -->'

# 场景目录与 hive.yaml skills 清单（用于 spawn 时校验 scene 值）
SCENE_NAMES = {'develop', 'debug'}
KNOWN_AGENTS = {'design-reviewer', 'analysis-reviewer', 'code-reviewer'}


def read_base() -> str:
    """读取基座模板全文（唯一输入之一）"""
    if not BASE_MD.exists():
        raise SystemExit(f"[错误] 基座模板不存在: {BASE_MD}")
    return read_norm(BASE_MD)


def read_norm(path: Path) -> str:
    """读取文件并统一换行为 LF + 剥离 BOM（兼容 Windows CRLF / UTF-8 BOM）"""
    return path.read_text(encoding='utf-8').replace('\r\n', '\n').lstrip('\ufeff')


def write_preserve(path: Path, content: str, original: str = None):
    """写回文件，保留原文件的换行风格与 BOM（避免 CRLF/BOM 文件被整体改写）"""
    if original is not None and '\r\n' in original:
        content = content.replace('\n', '\r\n')
    if original is not None and original.startswith('\ufeff'):
        content = '\ufeff' + content
    path.write_text(content, encoding='utf-8')


def resolve_inherits_chain(inherits: str, seen: set = None) -> list:
    """解析继承链，返回 [基座, A, B, ...]；检测循环继承与缺失"""
    seen = seen or set()
    if inherits in seen:
        raise SystemExit(f"[错误] 循环继承: {inherits}（链: {list(seen)}）")
    seen = seen | {inherits}

    chain = []
    if inherits == 'hive/base':
        return [BASE_MD]
    # 派生 agent 文件：.dsh/agents/<name>/<name>.md
    f = AGENTS_DIR / inherits / f"{inherits}.md"
    if not f.exists():
        raise SystemExit(f"[错误] 缺失基座/父 agent: {inherits}")
    content = read_norm(f)
    parent = extract_frontmatter(content).get('inherits', 'hive/base')
    chain = resolve_inherits_chain(parent, seen)
    chain.append(f)
    return chain


def extract_frontmatter(content: str) -> dict:
    """提取 frontmatter meta"""
    m = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not m:
        return {}
    try:
        import yaml
        return yaml.safe_load(m.group(1)) or {}
    except Exception:
        return {}


def _strip_marker_literals(text: str) -> str:
    """剥离正文中对定位标记的字面量引用（避免展开后嵌套标记）"""
    lines = []
    for line in text.splitlines():
        if '<!-- HIVE-BASE-START -->' in line and line.strip().startswith('<!--'):
            continue
        if '<!-- HIVE-BASE-END -->' in line and line.strip().startswith('<!--'):
            continue
        lines.append(line)
    return '\n'.join(lines)


def build_base_section() -> str:
    """构建基座段（含定位标记）"""
    body = read_base()
    # 去掉 base.md 自身的 frontmatter（frontmatter 不展开进派生文件）
    m = re.match(r'^---\n.*?\n---\n', body, re.DOTALL)
    if m:
        body = body[m.end():]
    body = _strip_marker_literals(body)
    return f"{BASE_START}\n{body}\n{BASE_END}"


def expand_chain(chain: list) -> str:
    """沿继承链展开：基座 + 各级父 agent 的基座段（自顶向下，R3）"""
    sections = []
    for f in chain:
        content = read_norm(f)
        # 取该文件基座段（若自身是基座模板则全文）
        m = re.search(rf'{re.escape(BASE_START)}(.*?){re.escape(BASE_END)}', content, re.DOTALL)
        if m:
            sections.append(_strip_marker_literals(m.group(1).strip()))
        else:
            # 无基座段的文件（父 agent 只有特异操作）跳过
            continue
    joined = "\n\n".join(sections)
    return f"{BASE_START}\n{joined}\n{BASE_END}"


def spawn(name: str, inherits: str, scene: str):
    """生成派生 agent 骨架"""
    target = AGENTS_DIR / name / f"{name}.md"
    if target.exists():
        raise SystemExit(f"[错误] 已存在 agent: {name}")

    if scene not in SCENE_NAMES and scene != '':
        print(f"[警告] 场景 '{scene}' 不在已知场景 {sorted(SCENE_NAMES)} 中，将创建新场景目录")
    if inherits != 'hive/base' and inherits not in KNOWN_AGENTS and not (AGENTS_DIR / inherits).exists():
        raise SystemExit(f"[错误] 未知继承源: {inherits}（用 hive/base 或已有 agent 名）")

    # 解析继承链（校验循环/缺失）
    chain = resolve_inherits_chain(inherits)
    base_section = expand_chain(chain) if len(chain) > 1 else build_base_section()

    content = f"""---
name: {name}
inherits: {inherits}
scene: {scene or 'null'}
---

{base_section}

# 我的特异操作

（此段为自身独有指令/偏好，允许自进化；通用价值必须回流 knowledge/ 共享区）
"""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    print(f"[spawn] 已生成 {target}（继承 {inherits}，场景 {scene or 'null'}）")


def sync():
    """同步所有派生 agent 的基座段（保留特异操作段）"""
    base_section = build_base_section()
    synced = 0
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir() or agent_dir.name == 'hive':
            continue
        f = agent_dir / f"{agent_dir.name}.md"
        if not f.exists():
            continue
        raw = f.read_text(encoding='utf-8')
        content = read_norm(f)
        meta = extract_frontmatter(content)
        if 'inherits' not in meta:
            continue  # 无继承声明，跳过

        # 确定新基座段：
        # - 直接继承 hive/base：用最新基座全文（build_base_section，含最新变更）
        # - 嵌套继承：沿继承链自顶向下展开（R3）
        try:
            if meta['inherits'] == 'hive/base':
                new_section = base_section
            else:
                chain = resolve_inherits_chain(meta['inherits'])
                new_section = expand_chain(chain)
        except SystemExit as e:
            print(f"[sync] 跳过 {agent_dir.name}: {e}")
            continue

        # 替换基座段（N6：只替换标记之间）
        pattern = re.compile(rf'{re.escape(BASE_START)}.*?{re.escape(BASE_END)}', re.DOTALL)
        if pattern.search(content):
            new_content = pattern.sub(new_section, content)
        else:
            # 无基座段：在 "# 我的特异操作" 前插入
            marker = '# 我的特异操作'
            if marker in content:
                new_content = content.replace(marker, f"{new_section}\n\n{marker}", 1)
            else:
                new_content = content + f"\n\n{new_section}\n"
        if new_content != content:
            write_preserve(f, new_content, raw)
            synced += 1
            print(f"[sync] {agent_dir.name} 基座段已更新")
    print(f"[sync] 完成，更新 {synced} 个派生 agent")


def list_agents():
    """列出所有 agent 与继承关系"""
    print("== 蜂巢 agent 一览 ==")
    print(f"[基座] hive/base ({BASE_MD.relative_to(REPO_ROOT)})")
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name == 'hive':
            continue
        f = agent_dir / f"{agent_dir.name}.md"
        if not f.exists():
            continue
        meta = extract_frontmatter(read_norm(f))
        inherits = meta.get('inherits', '(无，非派生)')
        scene = meta.get('scene', 'null')
        print(f"[agent] {agent_dir.name} | inherits={inherits} | scene={scene}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'spawn':
        if len(sys.argv) < 3:
            print("[错误] spawn 需要指定 agent 名")
            sys.exit(1)
        name = sys.argv[2]
        inherits = 'hive/base'
        scene = ''
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == '--inherits' and i + 1 < len(sys.argv):
                inherits = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--scene' and i + 1 < len(sys.argv):
                scene = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        spawn(name, inherits, scene)
    elif cmd == 'sync':
        sync()
    elif cmd == 'list':
        list_agents()
    else:
        print(f"[错误] 未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)
