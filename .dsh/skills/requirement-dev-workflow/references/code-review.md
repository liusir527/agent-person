# 代码审查闭环（编码实现 主状态的强制环节）

> 代码审查不是"一个微观状态名字"，而是完整闭环：code-reviewer agent + 证据型门禁 + 多轮复审循环。
> **`code-reviewer` agent 审查代码改动本身（场景无关），直接复用 `.dsh/agents/code-reviewer/code-reviewer.md`**，
> 仅把脚本/路径参数换成 requirement 版（`--req-id`、`runtime/req/`）。

## 闭环路径（编码实现 主状态内）

```text
编码实现：修改 → 代码审查 → 编译通过 → 修复评审问题
                │
                ├─ FAIL(轮次<3) ──→ 回「修改」重新修复 ──→ 复审
                └─ 第 3 轮 FAIL ──→ 转人工接管（human_takeover=true，停止自动推进）

代码审查 PASS ──→ gate --flag code_reviewed --value true \
                      --evidence <代码审查报告-rN.md>  （证据型门禁：无文件 exit 2 拒绝）
        │
        └─ build_passed 也置位后 ──→ advance --to 测试验证
```

## 审查对象与维度（code-reviewer 逐文件审查 git diff，五维缺一判 FAIL）

1. **正确性**：改动是否实现实施计划声明的逻辑？分支/边界态/空指针/资源释放是否处理；
2. **最小性**：只动必要行，无与本需求无关的重构/风格重排/注释大改；
3. **风格一致**：缩进、命名、错误处理与所在文件一致；
4. **影响面**：调用方/依赖方/配置/测试/版本兼容/回滚成本；不触 task-boundary 层边界；
5. **编译可达**：新头文件依赖/新宏/新 struct 字段是否缺配套 .h。

## 严重度分级（P0/P1 阻塞 PASS，P2 仅记录）

- P0：阻塞编译 / 引入回归 / 越权改层（跨层扩散）——必须修复；
- P1：会引发后续 bug / 与风格严重不一致——必须修复；
- P2：纯风格建议——不阻断 PASS。

## 产物与轮次

- 落盘 `runtime/req/<需求单号>/代码审查报告-rN.md`，结论行写 `审查通过：PASS` / `审查不通过：FAIL`；
- 最多 3 轮：FAIL 且轮次<3 → 主 agent 回「修改」修正后复审（向同一 reviewer 会话续问）；
- 第 3 轮 FAIL → 状态机置 `human_takeover=true`，转人工接管；
- PASS 后主 agent 调 `gate --flag code_reviewed --evidence <报告路径>` 置位（脚本校验报告文件存在非空）。

## 评审时机与反馈处理（吸收 superpower-requesting/receiving-code-review）

- 评审时机：每任务完成后、重大功能完成后、合并到基线分支前各审一次（尽早评审、频繁评审）；
- 反馈分级：P0/Critical 立即修；P1/Important 进入下一步前必须修完；P2/Minor 记录择机处理；
- 接收反馈：先验证再实施，禁止"完全正确"式表演认同；外部评审意见须对照代码核实
  （是否破坏现有功能 / 是否 YAGNI / 评审者是否掌握完整上下文），有异议用技术理由反驳而非盲从。

## 与 file-review skill 的协同（两级审查，不冲突）

- `file-review`：所有 write/edit 落盘文件的通用落盘审查（路径硬编码、编码、字段匹配、frontmatter…），
  触发即串接，≤3 轮降级人工；
- `code-reviewer`：编码主状态的正式门禁，审查**代码改动语义**（可合并性），是 `code_reviewed` 门禁的
  唯一证据来源；
- 顺序：编码落盘后先 file-review 过一遍通用问题，再派 code-reviewer 做语义审查，避免把 P2 类问题带进
  正式门禁。
