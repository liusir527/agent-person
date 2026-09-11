#!/usr/bin/env python3
"""
link_check.py - 知识提交门禁（Hive Brain M5）

提交前校验（memory-push 前置门禁）：
1. frontmatter 必填字段齐全（weight/decay_rate/weight_updated_at/knowledge_type/scene 等）
2. 索引一致性（knowledge/ 各分区 索引.md 与内容一致）
3. 相对链接可达（.md 内 [x](x) 相对链接目标存在）
4. 启发式语义检查（IP/账号/密码/绝对路径/临时会话号正则命中 → FAIL）
5. scene 值存在于 init/scenes/*.yaml 定义（N9）

N2（扫描范围）：只检查【本次变更文件】（git diff --cached --name-only 或显式参数），
存量文件豁免（白名单）——否则存量经验中的设备 IP/编译机绝对路径会让门禁永远 FAIL。

用法:
    python link_check.py              # 扫描 git 暂存区变更文件
    python link_check.py <path>...    # 显式指定要检查的文件
    python link_check.py --all        # 全量检查（含存量，默认仅提示不 FAIL）
输出: PASS / FAIL
"""

import re
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent   # .dsh/tools/ -> 主仓根
KNOWLEDGE_DIR = REPO_ROOT / '.dsh-memory' / 'knowledge'
INIT_SCENES_DIR = REPO_ROOT / 'init' / 'scenes'
EXPERIENCES_DIR = KNOWLEDGE_DIR / 'experiences'

# 必填 frontmatter 字段（按知识类型）
REQUIRED_FIELDS = ['id', 'summary', 'tier', 'category', 'severity', 'created_at',
                   'updated_at', 'weight', 'weight_updated_at', 'knowledge_type']
REQUIRED_FIELDS_SCENE = REQUIRED_FIELDS + ['problem_id', 'scene']

# 启发式语义检查正则（命中即疑似环境残留）
SENSITIVE_PATTERNS = [
    (r'\b(\d{1,3}\.){3}\d{1,3}\b', 'IP 地址'),
    # 绝对路径：排除 URL（scheme:// 会被 [A-Za-z]:[\\/] 误匹配 s://）
    (r'(?<![:/\w])[A-Za-z]:[\\/][^\s"\'|<>]{3,}', '绝对路径'),
    (r'(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*\S+', '凭据'),
    (r'user(name)?\s*[:=]\s*[^\s"\'|<>]+', '账号'),
    (r'(session|会话)[-_ ]?(\d{6,}|[a-f0-9]{8,})', '会话号'),
    (r'(/opt|/home|/root|C:[\\/]Users[\\/])\S+', '系统路径'),
]

# 索引字段：索引表列名（用于校验索引格式）
INDEX_COLUMNS = ['日期', '文件', '内容概要', 'hit_count', 'last_hit_at', 'reuse_success']


def git_changed_files(repo: Path = None) -> list[Path]:
    """获取 git 暂存区变更文件清单（repo 指定 git 仓库，默认主仓）"""
    repo = repo or REPO_ROOT
    try:
        out = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACMR'],
            cwd=str(repo), capture_output=True, text=True, encoding='utf-8', timeout=30)
        paths = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        paths = []
    return paths


def is_knowledge_file(p: Path) -> bool:
    """判断是否知识文件（.dsh-memory/knowledge/ 下 .md）"""
    try:
        p.relative_to(KNOWLEDGE_DIR)
        return p.suffix == '.md'
    except ValueError:
        return False


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 frontmatter，返回 (meta, body)"""
    m = re.match(r'^(?:\ufeff)?---\r?\n(.*?)\r?\n---\r?\n', content, re.DOTALL)
    if not m:
        return {}, content
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    return meta, content[m.end():]


def scene_names() -> set:
    """从 init/scenes/*.yaml 读取场景名"""
    names = set()
    if INIT_SCENES_DIR.exists():
        for f in INIT_SCENES_DIR.glob('*.yaml'):
            names.add(f.stem)
    return names


def check_frontmatter(path: Path, errors: list) -> bool:
    """校验 frontmatter 必填字段 + 启发式语义"""
    ok = True
    content = path.read_text(encoding='utf-8', errors='ignore')
    meta, body = parse_frontmatter(content)

    if not meta:
        errors.append(f"{path.name}: 无 frontmatter 或解析失败")
        return False

    ktype = meta.get('knowledge_type', 'experience')
    required = REQUIRED_FIELDS_SCENE if ktype == 'scene' else REQUIRED_FIELDS
    for field in required:
        if field not in meta or meta.get(field) is None:
            errors.append(f"{path.name}: 缺必填字段 '{field}'")
            ok = False

    # weight 范围
    w = meta.get('weight')
    if w is not None:
        try:
            if not (0.0 <= float(w) <= 1.0):
                errors.append(f"{path.name}: weight 超出 0~1（{w}）")
                ok = False
        except (TypeError, ValueError):
            errors.append(f"{path.name}: weight 非数值（{w}）")
            ok = False

    # scene 值存在性（N9）
    sc = meta.get('scene')
    if sc and str(sc) != 'null' and str(sc) not in scene_names():
        errors.append(f"{path.name}: scene '{sc}' 未在 init/scenes/ 定义")
        ok = False

    # 启发式语义检查（N2：只对本次变更文件执行——调用方保证传入的是变更文件）
    full = content
    for pattern, label in SENSITIVE_PATTERNS:
        for m in re.finditer(pattern, full, re.IGNORECASE):
            # 白名单：frontmatter 里的 url 引用（如 github.com）不算残留
            snippet = full[max(0, m.start()-30):m.end()+30].replace('\n', ' ')
            errors.append(f"{path.name}: 疑似{label}残留（命中: ...{snippet}...）")
            ok = False
            break  # 每类只报一次

    return ok


def check_index_consistency(path: Path, errors: list) -> bool:
    """校验索引一致性（P0-2 升级为硬校验）：knowledge/ 分区索引.md 必须包含该文件

    规则：
    - 知识文件所在目录必须有 索引.md，且内容含该文件名 → 否则 FAIL；
    - 例外：索引文件自身（索引.md / 导航索引）不校验。
    """
    ok = True
    # 知识文件所在目录的索引.md
    index_file = path.parent / '索引.md'
    if not index_file.exists():
        errors.append(f"{path.name}: 所在目录缺少索引文件 {index_file.name}（请先创建分区索引并登记本文件）")
        return False
    idx_content = index_file.read_text(encoding='utf-8', errors='ignore')
    if path.name not in idx_content:
        errors.append(f"{path.name}: 未登记在 {index_file.name} 中（请追加索引行）")
        ok = False
    return ok


def check_links(path: Path, errors: list) -> bool:
    """校验相对链接可达"""
    ok = True
    content = path.read_text(encoding='utf-8', errors='ignore')
    # [text](relpath) 形式，排除 http(s)://
    for m in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
        target = m.group(2)
        if target.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        # 相对链接：相对于当前文件目录
        target_path = (path.parent / target).resolve()
        if not target_path.exists():
            # 允许指向索引文件内（部分链接是锚点）
            errors.append(f"{path.name}: 相对链接不可达 -> {target}")
            ok = False
    return ok


def run(targets: list[Path] = None, check_all: bool = False, repo: Path = None) -> int:
    """执行校验，返回 0=PASS / 1=FAIL"""
    errors = []
    hints = []

    # --repo 模式下知识根随 repo 推导（支持 submodule 内变更校验）
    knowledge_dir = (repo / 'knowledge') if repo else KNOWLEDGE_DIR

    def _is_kf(p: Path) -> bool:
        try:
            p.relative_to(knowledge_dir)
            return p.suffix == '.md'
        except ValueError:
            return False

    if targets is None:
        if check_all:
            targets = [p for p in knowledge_dir.rglob('*.md') if p.name != '索引.md']
            print(f"[link_check] 全量扫描 {len(targets)} 个知识文件（存量提示模式）")
        else:
            repo = repo or REPO_ROOT
            changed = git_changed_files(repo)
            targets = [repo / p for p in changed if _is_kf(repo / p)]
            print(f"[link_check] 扫描 {len(targets)} 个本次变更知识文件（N2：存量豁免）")

    for t in targets:
        if not t.exists():
            hints.append(f"[提示] 文件不存在（跳过）: {t.name}")
            continue
        # 索引.md 是表格文件（无 frontmatter），跳过 frontmatter 校验，只查链接
        if t.name == '索引.md':
            check_links(t, errors)
            continue
        check_frontmatter(t, errors)
        check_index_consistency(t, errors)
        check_links(t, errors)

    # 输出
    for h in hints:
        print(h)
    if errors:
        print(f"[link_check] FAIL：{len(errors)} 个问题")
        for e in errors:
            print(f"  [X] {e}")
        return 1
    print("[link_check] PASS：全部校验通过")
    return 0


if __name__ == '__main__':
    args = sys.argv[1:]
    check_all = '--all' in args
    # --repo 指定 git 仓库（submodule 内变更时用 --repo .dsh-memory）
    repo_arg = None
    if '--repo' in args:
        i = args.index('--repo')
        if i + 1 < len(args):
            repo_arg = (REPO_ROOT / args[i + 1]).resolve() if not Path(args[i + 1]).is_absolute() else Path(args[i + 1]).resolve()
    explicit = [a for a in args if a != '--all' and a != '--repo' and not (a == args[args.index('--repo')+1] if '--repo' in args and args.index('--repo')+1 < len(args) else False)]

    if explicit:
        targets = [(REPO_ROOT / a).resolve() for a in explicit]
        sys.exit(run(targets=targets))
    else:
        sys.exit(run(check_all=check_all, repo=repo_arg))
