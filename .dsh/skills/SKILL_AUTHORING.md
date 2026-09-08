# Skill 编写规约（SKILL_AUTHORING.md）

> 本文档是 `.dsh/skills/` 下新建 / 编辑 skill 的总规约。
> 必读对象：**LLM（agent 主体 + 子 agent）** + **skill 作者（人）**。
> 优先级：`hooks/AGENT.md` 的全局铁律 > 本文档 > 各 skill 自身 SKILL.md。

## 1. 目录与命名

```text
.dsh/skills/<skill-name>/
├── SKILL.md                  # 必填。skill 描述 / 触发词 / 阶段路由 / 门禁 / 速查
├── state_machine.py          # 可选。状态机引擎（参考 bug-fix-workflow / analysis-only-workflow）
├── templates/                # 可选。产物模板（问题分析结论.md / 审查结果-rN.md / 修改方案.md / 结论文档.md）
└── references/               # 可选。阶段 reference（task-boundary / project-intake / 等等）
```

- `<skill-name>` 仅允许 `[a-z0-9-]+`，禁止下划线、点、大写
- SKILL.md 顶部必须有合规 frontmatter（`name` + `description` 必填），与现有 skill 一致

## 2. 运行时产物约定（必读，与 hooks/AGENT.md 铁律一致）

> **铁律**：本 skill 产生的所有运行时临时数据必须落到 `<项目根>/runtime/<分类>/<SESS>/` 下，禁止平铺到仓库根或其他位置。详见 `hooks/AGENT.md` 的「运行时产物纪律」一节。

### 2.1 落点常量命名

```python
# 正确（推荐）
DEFAULT_STATE_DIR = WORKSPACE / "runtime" / "analysis"
OUTPUT_DIR = WORKSPACE / "runtime" / "<skill-class>" / "<default-sess>"

# 错误（违反铁律）
DEFAULT_STATE_DIR = WORKSPACE / "analysis-state"      # 仓库根平铺
DEFAULT_STATE_DIR = WORKSPACE / "tmp" / "analysis"    # 用了 tmp 目录
```

### 2.2 SESS 命名约定

| skill 类别 | SESS 取值 | 示例 |
|---|---|---|
| analysis-only-workflow | 用户提供的 slug | `sdwan-routing-review-20251127` |
| vpp-api-sync | 会话 ID（DSH 自带） | `<SESS>` |
| ssh-tools | 固定分类 `terminal-monitor` | `runtime/terminal-monitor/` |
| gdb-tools | 测试用 `test_gdb_guard.mjs` | `runtime/test_gdb_guard.mjs` |
| 新 skill | skill 自定义 + 时间戳 | `<topic>-<YYYYMMDD>` |

slug 走 `^[A-Za-z0-9_.\-]+$` 正则，保证目录名安全、跨平台可移植。

### 2.3 init 时必做

```python
def cmd_init(args):
    # ... 校验 args.id ...
    sess = session_dir(args.id)
    if sess.exists():
        return fatal(f"目标目录已存在，禁止覆盖：{sess}")
    sess.mkdir(parents=True)        # 在 runtime/ 下创建，不污染仓库根

    # 自动登记 dirs.json（受限模式下保证后续写入不被 nf-hooks 拦截）
    register_in_writable_dirs(sess)
```

### 2.4 dirs.json 登记

本工作区已在 `.dsh/rules/dirs.json` 中登记 `.\runtime`（覆盖所有运行时分类）。新建 skill **无需** 单独登记自己的子目录——子目录继承 `runtime/` 父目录的放行权。

## 3. 状态机设计规约

### 3.1 主状态机

- 主状态数 ≤ 7；过多说明流程没合并
- 每阶段含 ≤ 4 个微观状态
- 微观状态命名沿用：`取证 → 假设 → 验证 → 结论` / `审查 → 复现 → 判定 → 轮次记账` / `方案草拟 → 影响评估 → 方案评审 → 用户确认` / `修改 → 代码审查 → 编译通过 → 修复审查问题`

### 3.2 门禁模型

```python
HUMAN_CONFIRM_GATES = {"plan_confirmed", "manual_verify_passed", "pr_reviewed", "jira_closed"}
EVIDENCE_GATES = {"code_reviewed", "build_passed"}
```

- 人工确认门禁**只能**用 `confirm --flag <flag> --by <确认人>` 置位，禁止 `gate` 命令手拍
- 证据型门禁必须带 `--evidence <存在且非空文件>`，否则 `gate` 命令拒绝
- 工具链硬门禁（如 worktree_ready）只能由 deploy-build 等专用工具置位

### 3.3 审查轮次

- `MAX_REVIEW_ROUNDS = 3`
- 审查产物文件名：`审查结果-r{round}.md`（与 analysis-reviewer 子 agent 输出兼容）
- PASS 必须含 `复现成功：PASS` 标记（正则 `复现成功[:：]?\s*(PASS|成功)`）
- FAIL 第 3 轮 → `human_takeover=true`，停止自动推进

## 4. SKILL.md 写作规约

### 4.1 必含内容

1. **触发词**（10-20 个，含中英文、同义词、典型用户表述）
2. **何时不使用本 skill**（与兄弟 skill 的边界，避免误触发）
3. **环境前置检查**（状态机脚本、reference 数、子 agent、dirs.json 登记）
4. **阶段路由**（与 reference 文件 1:1 对应）
5. **与 bug-fix-workflow / analysis-only-workflow 的差异速查表**（如果是新流程类 skill）

### 4.2 frontmatter 模板

```yaml
---
name: <skill-name>
description: <一句话定位 + 触发词列表 + 反例（何时不使用）>
---
```

`description` 必须能在不看正文的情况下让 LLM 判断"该用本 skill / 该用别的 skill / 不该用任何 skill"。

## 5. templates/ 编写规约

- 模板文件**不预复制**——状态机只在状态目录建空目录；模板作为创建产物时的参考
- 模板内容必须是"完整可填"骨架，**字段缺失会被门禁硬校验拒绝**
- 对抗审查产物模板必须含 `复现成功：PASS` 标记段（即使是占位说明）

## 6. references/ 编写规约

- `task-boundary.md` 必含"工作区边界"+"自检清单"（参见 analysis-only-workflow lite 版）
- `project-intake.md` 极简版：5 分钟熟悉代码库即可，不展开
- 其他 reference 视 skill 复杂度而定

## 7. 子 agent 复用

优先复用 `.dsh/agents/code-reviewer/` 和 `.dsh/agents/analysis-reviewer/`，**不轻易新建**：

- 若必填字段不同（如需求开发 vs BUG 修复），新建 skill 时仍复用现有 reviewer
- 子 agent 定义文件 frontmatter `name` 与目录名一致（详见 `.dsh/agents/<agent-name>/<agent-name>.md`）

## 8. 自测 checklist（新建 skill 后必跑）

- [ ] `init --id <test-slug> --title "..."` 成功，目录落 `<项目根>/runtime/<分类>/<slug>/`
- [ ] 负向：缺产物时 `advance` 被拒（exit 2）
- [ ] 正向：完整闭环（init → micro → advance → review PASS → confirm → advance → gate → close）
- [ ] 终态 `state --id <slug>` 显示三道硬门禁 ✓
- [ ] workspace 根**无任何 `<skill>-*` / `<skill>-state/` 残留**
- [ ] 审查产物含 `复现成功：PASS` 标记才能 PASS
- [ ] `gate --flag code_reviewed` 缺 `--evidence` 被拒
- [ ] `gate --flag plan_confirmed` 被拒（必须用 confirm）

## 9. 不做的事

- ❌ 不创建 worktree / 分支（除非用户明确要求）
- ❌ 不下载附件、不 OCR、不开浏览器
- ❌ 不写与本 skill 无关的代码
- ❌ 不动 `hooks/AGENT.md` 的现有铁律（只能追加新章节）
- ❌ 不污染 workspace 根（与第 2 节约定一致）

## 9.5 已知运行时产物（不视为违规，写入 SKILL.md 让 reviewer 看到）

新建 skill 时**务必**在自身 SKILL.md 末尾写一节「已知运行时产物」，明确：

- `__pycache__/` —— Python 字节码缓存；仓库根 `.gitignore` 第 73 行已覆盖不入库；每次调用引擎自动重建，**不可根除**；不阻断审查。
- `runtime/` —— 状态机/同步类 skill 的临时目录；仓库根 `.gitignore` 第 57 行 `runtime/*` 已覆盖不入库；保留便于排查。

这样 future reviewer 看到 `__pycache__/` 残留时会直接参照该节放行，而不是当 P2 提出来（参考 analysis-only-workflow 第 3 轮 file-review #4 项的处理）。

## 10. 参考范例

- `.dsh/skills/bug-fix-workflow/` —— 完整状态机 + JIRA/PR/上机验证全流程样板
- `.dsh/skills/analysis-only-workflow/` —— lite 闭环样板（无 bug 单场景）
- `.dsh/skills/vpp-api-sync/` —— 单点同步类工具样板

新建 skill 时**先读**上述三个范例再开工。