# AGENTS.md

> 项目级 Agent 角色索引（DSH 自动注入）。本文件仅指引**子 agent 定义位置**，
> 不重复子 agent 的职责描述（详见各 agent 自身文件）。

## 子 agent 定义位置

`agents/` 目录下的每个子目录即一个角色；agent 角色定义为该目录下与目录同名的 `.md` 文件。

```text
agents/<agent-name>/<agent-name>.md
```

例：`agents/analysis-reviewer/analysis-reviewer.md`、`agents/code-reviewer/code-reviewer.md`

## 调用方式

主 agent 用 `subagent_fork` 工具派发子 agent 时，**将 `agents/<agent-name>/<agent-name>.md` 的内容作为 prompt 喂给子 agent**，并在调用参数中明确子任务目标与所需输入（bug_id / 文件路径 / 上下文等）。

## 新增子 agent

1. 创建 `agents/<agent-name>/<agent-name>.md`，frontmatter `name` 与目录/文件名一致；
2. 不需要改本文件 —— 主 agent 会按目录扫描发现新角色。
