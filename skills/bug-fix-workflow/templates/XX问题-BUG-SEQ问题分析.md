# {BUG_ID}问题-BUG-SEQ问题分析

> 结论文档。按 AGENT.md 约定：**最终成品放置于 npp 仓库根目录**，命名 `XX问题-BUG-SEQ问题分析.md`。
> 本模板位于 `templates/`，init 时不预复制——由 agent 按本模板结构创建终稿（放 npp 仓库根），`close` 时经 `--conclusion` 传该文件路径。

## 1. 问题现象

＿＿

## 2. 根因

＿＿（引用审查通过的 问题分析结论.md 第 4 节）

## 3. 证据链

＿＿（决定性证据 + 代码路径 + 复现链路）

## 4. 修复方案

＿＿（引用 修改方案.md 第 2 节改动设计）

## 5. 验证

＿＿（编译/自测/上机结果，引用 自测记录.md）

## 6. 影响/风险

＿＿

## 7. 可复用经验（强制沉淀）

> 闭环必做：close 前必须完成经验沉淀（状态机门禁校验「沉淀经验」微观状态）。
> 抽取内容与边界见 `references/reasoning-extraction.md`，调用 `memory-gen` 生成经验文档
> （落盘 `.dsh/references/稀疏经验/` + 更新索引）后 `memory-push` 推送 git。

- 经验文档：`＿＿（.dsh/references/稀疏经验/<知识概要>-<年月日>.md）`
- 可选回写候选：＿＿（知识库/Confluence/JIRA/战例库，需用户确认）
