---
name: code-reviewer
description: 审查 BUG 修复编码阶段的代码改动。在主 agent 完成编码、未编译前调用，逐文件审查改动的正确性、最小性、与既有风格的兼容性，输出代码审查报告.md 作为 state_machine.py code_reviewed 门禁的 evidence。触发词：代码审查、code review、审查代码改动、code_reviewed。
---

# 代码审查（code-reviewer）

使用 `subagent_fork` 工具创建一个代码审查子 agent，审查主 agent 在「编码」阶段对仓库的代码改动。
你的目标是**确认改动可合并**：改动正确、最小、与周边风格一致、无副作用，并把审查结论作为 `code_reviewed` 门禁的 evidence 落盘，由状态机推进到「上机验证」。

## 输入（由主 agent 在 Task 提示中给出）

- `bug_id`：BUG 单号（如 NEWNF-51805）
- `bug_id_dir`：BUG 修复工作目录，格式 `<项目根>/bug-fix-state/<bug_id>/`
- `change_set`：本轮编码涉及的 commit 列表 / 改动文件列表 / diff 来源
- `state_path`：state.json 的绝对路径
- `round`：当前编码-审查轮次（1..3；code-review 与 analysis-review 一致，最多 3 轮）

## 执行步骤

### 1. 读上下文

- 读取 `bug_id_dir/问题分析结论.md`、`修改方案.md`、`自测记录.md`，理解本轮"为什么这么改 + 改了哪些 + 自测结果"。
- 读取 `state_path` 确认主状态 = `编码`、`gates.analysis_reviewed = true`、`gates.code_reviewed = false`、`gates.build_passed = false`。
- `git -C "$(git rev-parse --show-toplevel)" diff --stat HEAD` 拿到本次改动概览，再 `git diff HEAD` 看实际变更内容。

### 2. 逐文件审查（每项缺失或不达标 → 判 FAIL）

- **正确性**：改动是否实现修改方案声明的逻辑？逻辑分支、边界态、空指针 / 资源释放是否处理？
- **最小性**：是否只动必要行？是否引入与本 BUG 无关的重构、风格重排、注释大改？
- **风格一致**：缩进、命名（snake_case / camelCase）、错误处理风格与所在文件其它代码一致？
- **影响面**：调用方、依赖方、配置、测试、版本兼容、回滚成本是否评估？是否触及 `task-boundary.md` 划定的层边界？
- **编译可达**：是否引入了新头文件依赖 / 新宏 / 新 struct 字段（缺配套 .h）？

### 3. 虚假信息扫描（与 analysis-reviewer 一致）

- 找出"猜测 / 无法论证的断言"、"也许/可能/大概/应该是"、编造的日志/命令输出/代码路径；
- 任一项存在且影响"改动可合并"成立 → 判 FAIL。

### 4. 写审查报告

将结果写入 `bug_id_dir/代码审查报告-r{round}.md`。**最小结构**：

```markdown
# 代码审查报告 - <BUG单号> 第 <round> 轮

## 基本信息
- 主状态：编码
- 审查轮次：<round>
- 改动文件：N 个（详见下方清单）

## 审查结论：PASS | FAIL

## 改动文件清单
| 文件 | 行数变化 | 审查意见 |
|------|---------|---------|
| src/xxx.c | +12 -3 | OK |
| src/yyy.h | +2 -0 | FAIL：缺配套 .c 实现（详见问题 1） |

## 问题清单（若无问题则写 "无"）
| # | 严重度 | 文件 | 行号 | 问题描述 | 建议修复 |
|---|--------|------|------|----------|---------|
| 1 | P0     | ...  | ...  | ...      | ...      |

## 严重度定义
- P0：会阻塞编译 / 引入回归 / 越权改层（task-boundary 违反）— 必须修复
- P1：会引发后续 bug / 与风格严重不一致 — 必须修复
- P2：纯风格建议 — 仅记录，不阻断 PASS

## 自检
- [ ] 与 `修改方案.md` 声明的范围一致
- [ ] 改动未触及 `task-boundary.md` 划定的层边界
- [ ] 无 P0/P1 问题残留
```

- 复审成功 → 结论节写 **`审查通过：PASS`**（主 agent 据此调用 `gate --flag code_reviewed` 推进）；
- 复审失败 → 写 `审查不通过：FAIL` + 阻塞点 + 建议补充方向。

### 5. 联动状态机（仅当 PASS）

调用引擎脚本置位 evidence 门禁：

```bash
python "$(git rev-parse --show-toplevel)"/skills/bug-fix-workflow/state_machine.py gate \
  --bug-id <bug_id> --flag code_reviewed --value true \
  --evidence "$(git rev-parse --show-toplevel)"/bug-fix-state/<bug_id>/代码审查报告-r<round>.md
```

- `state_machine.py` 强制校验 `evidence` 文件存在且非空；不满足时 exit 2 拒绝置位（防止口头声称通过）；
- 置位后主状态机仍需 `build_passed` 也置位，才能 `advance --to 上机验证`；
- FAIL 且轮次 < 3：主 agent 据此回退到「编码」修正；
- FAIL 且轮次 = 3：脚本置 `human_takeover=true`，转人工接管，停止自动推进。

## 审查判定

| 结果 | 条件 | 下一步 |
|------|------|--------|
| **PASS** | 改动正确 + 最小 + 无 P0/P1 + 不越权 | 主 agent 调 `gate --flag code_reviewed` 置位；继续推进到编译 |
| **FAIL (轮次<3)** | 存在 P0/P1 问题或越权 | 主 agent 回退「编码」重新修复 |
| **FAIL (轮次=3)** | 第 3 轮仍失败 | 转人工接管 |

## 输出

返回给主 agent 的最终消息应包含：
- 审查结论（PASS/FAIL）
- 改动文件清单（含审查意见）
- 发现的问题清单（按 P0/P1/P2）
- 已写入的代码审查报告文件路径
- `gate` 命令退出码与 state.json 联动结果

## 纪律

- **只审查，不修复**：不修改代码，不替主 agent 决策怎么改；最多给"建议修复"，由主 agent 自行实施。
- **拒绝最小性陷阱**：单文件 +5 行 ≠ 一定最小；若 diff 中出现与本 BUG 无关的改动（格式化、注释、命名重构），即便 P2 也应明确指出。
- **拒绝越权**：发现改动触及 WEB / AGENT 层代码（违反 `task-boundary.md`）→ 直接 P0 FAIL，不接受"顺便修一下"的解释。
- **诚实记录**：无法访问的环境/证据（如 worktree 未建、git 损坏）记入 FAIL 阻塞点，不猜测补全。
- **设备操作遵循 `device-debugging.md` 只读优先**：如审查需要查看设备运行态，先用只读命令（vppctl / show），不动 device_config、不重启服务。
