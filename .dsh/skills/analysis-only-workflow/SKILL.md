---
name: analysis-only-workflow
description: 无 bug 单的简化分析闭环工作流。适用于用户拿到一段代码/日志/原始问题描述，需要做 取证→对抗审查→修改方案→编码→代码审查 的最短闭环，但**没有 JIRA bug 单**、不需要 PR、不需要上机验证的场景。触发词：分析一下、代码审查、方案评审、闭环分析、无bug单分析、轻量分析、无工单分析、analysis-only-workflow。当用户提供 BUG 单号（如 NEWNF-XXXXX）时，应使用 bug-fix-workflow 而非本 skill。
---

# analysis-only-workflow（无 bug 单的简化分析闭环）

将本 skill 作为「无 bug 单」场景的端到端串接器。**与 bug-fix-workflow 完全解耦**：
JIRA / PR / 上机验证 / 工单关闭 全流程不触发；仅保留分析深度、对抗审查、方案用户确认、代码审查这四道硬门禁。

## 何时使用本 skill

- 用户给的是一段代码、日志、崩溃描述、设计问题、临时 issue，**没有 JIRA 单号**。
- 用户明确要求"先分析一下"、"帮我做代码审查"、"做个方案评审"、"走一遍闭环"。
- 用户说"先不动 bug 单"、"就讨论一下"、"轻量分析"。

## 何时不使用本 skill（应转 bug-fix-workflow）

- 用户提示词含 BUG 单号（`NEWNF-XXXXX` 等）→ 转 bug-fix-workflow。
- 用户明确要求走 PR / JIRA / 上机验证 / 工单关闭 → 转 bug-fix-workflow。
- 用户要求部署到设备并做业务回归 → 转 bug-fix-workflow（lite 模式也不覆盖）。

## 环境前置检查

| 资源 | 存在判定 | 缺失降级 |
|------|---------|---------|
| 状态机引擎 | `state_machine.py`（同级目录） | **阻塞**——门禁硬校验依赖脚本 |
| 阶段 reference | `references/{task-boundary,project-intake,analysis-only-intake,fix-and-verify,reasoning-extraction}.md`（5 个） | 阻塞 |
| 兄弟 skill | `bug-fix-workflow`（产线 BUG 模板/铁律引用）、`memory-gen` | 缺 `memory-gen` → 关闭门禁的「沉淀经验」不强制校验 |
| 子 agent | `.dsh/agents/analysis-reviewer/`、`.dsh/agents/code-reviewer/` | 缺 review agent → 仍可跑门禁，但 PASS 标记需人工写审查结果-rN.md |

统一自检：

```bash
WS="$(git rev-parse --show-toplevel)" && cd "$WS" && \
  test -f "$WS/.dsh/skills/analysis-only-workflow/state_machine.py" && echo "SM:OK" || echo "SM:FAIL"; \
  ls "$WS/.dsh/skills/analysis-only-workflow/references"/*.md 2>/dev/null | wc -l | awk '{print ($1==5?"REF:OK":"REF:FAIL(" $1 "/5)")}'
```

## 阶段路由

0. **开工必读**：`references/task-boundary.md`（任务边界与防扩散约束）。
1. 进入新代码库/陌生模块：`references/project-intake.md`。
3. 拿到代码/日志/现象开始取证：`references/analysis-only-intake.md`。
5. 已知根因或代码区域：`references/fix-and-verify.md`。
6. 结论稳定后：`references/reasoning-extraction.md`。

## 状态机驱动（每条 session 强制）

引擎：`analysis-only-workflow/state_machine.py`
状态目录：`<项目根>/runtime/analysis/<SESSION_SLUG>/`（与 vpp-api-sync 等 skill 的 `runtime/<SESS>/` 约定一致；`runtime/` 已登记为可写运行时目录）

主状态（5 个）：
```text
分析 → 审查结论 → 出修改方案 → 编码 → 结束
```

微观状态沿用 bug-fix-workflow 命名：
- 分析：取证 → 假设 → 验证 → 结论
- 审查结论：审查 → 复现 → 判定 → 轮次记账
- 出修改方案：方案草拟 → 影响评估 → 方案评审 → 用户确认
- 编码：修改 → 代码审查 → 编译通过（可选）→ 修复审查问题

**硬性规则：**
- **起步**：拿到任务先 `init`（`python "$(git rev-parse --show-toplevel)"/.dsh/skills/analysis-only-workflow/state_machine.py init --id <slug> --title "..." --module "..."`）。
- **slug 规则**：`^[A-Za-z0-9_.\-]+$`，且不能为 `.` / `..`；建议格式 `<topic>-<YYYYMMDD>-<short>`，如 `sdwan-routing-review-20251127`。
- **每完成一步**：`micro` / `advance` 推进状态，`record` 累计工时，`review` 登记审查轮次。
- **门禁硬校验**：`advance` 到下一主状态前脚本强制校验；不满足 exit 2 拒绝。
- **保留门禁**：`analysis_reviewed`（对抗审查 PASS）、`plan_confirmed`（用户确认方案）、`code_reviewed`（带 evidence）。
- **可选门禁**：`build_passed`（编译日志存在时建议置位；纯文档改动可豁免）。
- **审查**：分析产物齐 → 调 `analysis-reviewer` 子 agent 对抗审查（按触发链路复现），其落盘 `审查结果-rN.md` 并调 `review` 命令记账。FAIL 且轮次<3 回「分析·取证」；第 3 轮 FAIL 转人工接管（human_takeover=true）。
- **断点**：中断后用 `state` / `resolve` 定位当前节点。
- **闭环收尾**：`close --conclusion 结论文档.md`；**不强制** memory-gen 沉淀（lite 流程灵活），但建议用户在结论文档中保留可复用解题思路。

## 与 bug-fix-workflow 的差异速查

| 维度 | bug-fix-workflow | analysis-only-workflow（本 skill） |
|------|------------------|-----------------------------------|
| 入口 | JIRA BUG 单号 | session slug（任意短串） |
| 状态目录 | `bug-fix-state/<BUG单号>/` | `runtime/analysis/<SESSION_SLUG>/` |
| 主状态数 | 7 | 5 |
| PR 流程 | 强制（`pr_reviewed`） | 不需要 |
| JIRA 流转 | 强制（`jira_closed`） | 不需要 |
| 上机验证 | 强制（自测+人工验证） | 可选 |
| 编译门禁 | 强制（`build_passed`） | 可选 |
| 保留门禁 | analysis_reviewed / plan_confirmed / code_reviewed / build_passed / selftest / manual_verify / pr_reviewed / jira_closed | analysis_reviewed / plan_confirmed / code_reviewed（build_passed 可选） |
| 经验沉淀 | close 强制校验 | 建议但不强制 |

## 必要检查点（每轮回复输出）

- 上下文：仓库、代码分支、当前假设
- 证据：现象/日志/代码路径/已执行命令
- 假设：按优先级排列 + 验证/证伪方式
- 计划：最小修复计划 + 影响范围 + 回退
- 验证：自测范围 + 回归风险
- 沉淀：可复用经验（写进结论文档）

## 进度展示

回复必须带阶段横幅 `▸ 阶段：x/5 · 主状态 · 微观`（x 取自脚本 `【进度 x/5 · …】`）。
多轮长任务中，每个自然段（切换取证/代码/动作）之间至少输出一次当前阶段；用户问"走到哪了"时先 `progress --id <slug>`。

## 反向提问

只有缺失信息会阻塞安全推进时才向用户提问。典型阻塞：
- 任务边界（哪个仓库/工作区）未明确
- 已知可能的代码改动区域，需用户确认是否需要 worktree 派生
- 编译/测试命令需要设备参数但未提供

## 安全默认值

- 未明确说明前，真实设备/编译机视为类生产环境
- 修改状态前优先执行只读命令
- 代码修改保持与周边风格一致，避免无关重构，始终保持最小改动

## 已知运行时产物（不视为违规）

- `.dsh/skills/<skill>/__pycache__/` —— Python 字节码缓存，每次调用引擎自动重建（不可根除）。
  - **不入库**：仓库根 `.gitignore` 第 73 行 `__pycache__/` 已覆盖；`git check-ignore -v` 命中该目录。
  - **不阻断审查**：未来 reviewer 不应把"__pycache__ 存在"列为 P1/P2 残留（详见第 3 轮 file-review 报告 #4 项）。
  - **运行时规避**（可选）：如需避免落盘，可在调用命令前加 `PYTHONDONTWRITEBYTECODE=1` 或 `python -B`；本 skill 默认不做，要求用户按需启用。
- `runtime/` —— 状态机引擎的临时产物目录。
  - **不入库**：仓库根 `.gitignore` 第 57 行 `runtime/*` 已覆盖；详见 hooks/AGENT.md「运行时产物纪律」。
  - **保留策略**：任务结束后保留即可，便于人工排查；不需要入 .gitignore 黑名单外的"清理脚本"。