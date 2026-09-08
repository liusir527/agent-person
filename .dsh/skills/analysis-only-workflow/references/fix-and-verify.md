# 编码与验证（lite 版）

> 对齐 bug-fix-workflow `references/fix-and-verify.md` 的"已知根因后怎么改"流程，但**没有上机验证、没有 PR、没有 JIRA**。

## 1. 编码前门禁硬校验

```bash
python "$(git rev-parse --show-toplevel)"/.dsh/skills/analysis-only-workflow/state_machine.py \
  gate-check --id <slug>
```

门禁不满足（exit 2）时禁止修改文件，先补足前置条件。

> 所有产物均落到 `<项目根>/runtime/analysis/<slug>/`，`runtime/` 已登记为可写运行时目录；`--dir` 仅用于临时外迁调试。

## 2. 编码约束

- **最小改动原则**：只动必要行，不顺手重构。
- **保持与周边风格一致**：缩进、命名、注释风格。
- **不动无关文件**：禁止顺手"修个 typo"、"补点注释"。
- **不写无关测试**：lite 流程不要求新增单元测试。

## 3. 改动自检（编码完成后）

每个改动文件写完后自问：

- [ ] 与 `修改方案.md` 第 2 节一致（无超范围改动）
- [ ] 边界态用例覆盖到位（见 问题分析结论.md §7）
- [ ] 没引入新的循环依赖 / 头文件污染
- [ ] 编译命令（如 VPP/npp）能跑通 / 静态检查过
- [ ] `git diff` 自查无误（无临时调试 print / 注释）

## 4. 代码审查（必走）

- 落盘 `代码审查记录.md`（在 session 目录下）。
- 调用 code-reviewer 子 agent（`.dsh/agents/code-reviewer/code-reviewer.md`）做审查。
- 审查产物（`代码审查记录.md`）作为 `gate --flag code_reviewed --evidence <path>` 的 evidence。
- 审查 FAIL → 回「编码·修改」重做；最多 3 轮（同 review 轮次上限规则）。

## 5. 验证（lite 限定）

- **不强制上机**。
- 验证方式以**代码静态分析 + diff 自查 + 边界态用例回看**为主。
- 如有单元测试 / 静态检查命令，可由用户手动运行或 agent 用只读命令检查。
- 边界态用例必须逐条写明"实际观察"（哪怕是"代码静态分析已覆盖，运行时未验证"）。

## 6. 编译（如适用）

- 涉及 VPP/npp 改动时建议走 `deploy-build` skill 在编译机验证；
- **纯文档 / 配置改动**：跳过编译，build_passed 保持 false；
- 编译通过：`gate --flag build_passed --value true --evidence <编译日志>`。

## 7. close 前清单

- [ ] `问题分析结论.md` 存在
- [ ] `审查结果-r1.md` 含「复现成功：PASS」（或更新版本）
- [ ] `修改方案.md` 存在 + plan_confirmed 置位
- [ ] `代码审查记录.md` 存在 + code_reviewed 置位（evidence=本文件）
- [ ] `结论文档.md` 存在（仅当 `close --conclusion` 传入时才校验；不传时跳过此条）
- [ ] （可选）编译日志 + build_passed 置位

最后执行：

```bash
python "$(git rev-parse --show-toplevel)"/.dsh/skills/analysis-only-workflow/state_machine.py \
  close --id <slug> --conclusion 结论文档.md
```