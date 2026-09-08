---
name: ask-atlassian
description: 通过MCP协议对接公司JIRA Server和Confluence Server，支持使用JQL/CQL查询、创建和更新工单/文档、管理附件或设置MCP服务器认证。当需要查询JIRA问题、创建工单、搜索Confluence内容、创建文档或与Atlassian套件集成时使用此技能。
author: BSA Team
version: 1.0.0
---
# Ask Atlassian

## 何时使用此技能

### JIRA 相关

- 使用JQL过滤器查询JIRA工单
- 创建和更新工单（带自定义字段）
- 设置MCP服务器认证（PAT）
- 调试JIRA API集成问题

### Confluence 相关

- 使用CQL过滤器搜索Confluence页面
- 创建和编辑Wiki文档
- 管理空间和附件
- 设置MCP服务器认证（PAT）
- 同步文档到Confluence
- 调试Confluence API集成问题

## 核心工作流程

1. **配置MCP服务器** - 使用开源sooperset/mcp-atlassian连接公司Atlassian套件
2. **认证** - 配置PAT（个人访问令牌）凭证
3. **设计查询** - 编写JQL/CQL，先使用 `maxResults=1`/`limit=1`验证再完整执行
4. **实现工作流** - 构建工具调用，处理分页、错误恢复
5. **验证权限** - 在任何写入或批量操作前，用只读探测确认所需范围
6. **部署** - 配置IDE集成，测试权限，监控速率限制

## 参考指南

根据上下文加载详细指导：

| 主题           | 参考文件                                  | 加载时机                        |
| -------------- | ----------------------------------------- | ------------------------------- |
| 服务器设置     | `references/mcp-server-setup.md`        | 安装、选择服务器、配置时        |
| JIRA操作       | `references/jira-operations.md`         | JQL语法、工单CRUD、工单链接时   |
| Confluence操作 | `references/confluence-operations.md`   | CQL搜索、页面创建、空间、评论时 |
| 认证模式       | `references/authentication-patterns.md` | PAT配置时                       |

## 快速入门示例

### JQL查询示例

```
# 当前分配给当前用户的打开工单
project = PROJ AND status = "In Progress" AND assignee = currentUser() ORDER BY priority DESC

# 过去7天创建的未解决bug
project = PROJ AND issuetype = Bug AND status != Done AND created >= -7d ORDER BY created DESC

# 批量操作前验证：先用maxResults=1测试
project = PROJ AND status = Open ORDER BY created DESC
```

### CQL查询示例

```
# 在特定空间中最近更新的页面
space = "ENG" AND type = page AND lastModified >= "2024-01-01" ORDER BY lastModified DESC

# 搜索页面文本中的关键字
space = "ENG" AND type = page AND text ~ "deployment runbook"
```

### MCP服务器配置

根据您使用的AI编程工具选择对应的配置方式：

#### Claude Code CLI 用户

使用 `claude mcp add` 命令直接添加（推荐，最简单）：

```bash
export JIRA_PERSONAL_TOKEN="你的JIRA_PAT令牌"
export CONFLUENCE_PERSONAL_TOKEN="你的Confluence_PAT令牌"
claude mcp add \
  -e JIRA_URL=https://inone.intra.nsfocus.com/jira \
  -e JIRA_PERSONAL_TOKEN="$JIRA_PERSONAL_TOKEN" \
  -e CONFLUENCE_URL=https://inone.intra.nsfocus.com/confluence \
  -e CONFLUENCE_PERSONAL_TOKEN="$CONFLUENCE_PERSONAL_TOKEN" \
  -s user \
  atlassian -- uvx mcp-atlassian
```

> **重要：** 配置完成后，请**重启当前 Claude Code 会话**以使配置生效。

#### 其他AI编程工具用户

手动编辑配置文件，添加以下JSON配置：

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://inone.intra.nsfocus.com/jira",
        "JIRA_PERSONAL_TOKEN": "${JIRA_PERSONAL_TOKEN}",
        "CONFLUENCE_URL": "https://inone.intra.nsfocus.com/confluence",
        "CONFLUENCE_PERSONAL_TOKEN": "${CONFLUENCE_PERSONAL_TOKEN}"
      }
    }
  }
}
```

> **注意：** 始终从环境变量或密钥管理器加载凭证，切勿硬编码。
>
> **提示：** 更详细的配置说明请参考 `references/mcp-server-setup.md`。

## 约束

### 必须做

- 尊重用户权限和工作区访问控制
- 执行前验证JQL/CQL查询（先用 `maxResults=1`/`limit=1`探测）
- 使用指数退避处理速率限制
- 对大结果集使用分页（每页50-100项）
- 实现网络失败的错误恢复
- 记录API调用用于调试和审计追踪
- 先用只读操作测试
- 记录所需的权限范围
- 对生产数据的任何写入或批量操作前确认

### 禁止做

- 在代码中硬编码PAT令牌
- 忽略Atlassian API的速率限制头
- 未验证必填字段就创建工单/页面
- 跳过用户提供查询字符串的输入清理
- 未测试权限边界就部署
- 无确认提示就更新生产数据
- 在日志或错误消息中暴露敏感数据

### JIRA/Confluence 环境变量放哪里

四个凭证变量必须按下面规则落地：

| 变量 | 放哪里 | 说明 |
|---|---|---|
| `JIRA_URL` | `<cwd>/.env` | 应用层配置，可 hot-reload |
| `JIRA_PERSONAL_TOKEN` | `<cwd>/.env` | 应用层配置，可 hot-reload |
| `CONFLUENCE_URL` | `<cwd>/.env` | 应用层配置，可 hot-reload |
| `CONFLUENCE_PERSONAL_TOKEN` | `<cwd>/.env` | 应用层配置，可 hot-reload |

`<cwd>/.env` 是工作区根目录（PowerShell launcher 的 `WorkingDirectory`）下的 `.env` 文件。
仓库里的 `@nsfocus/nf-env-watcher` 插件会在它变化时**自动 hot-reload 到 dsh web 的 `process.env`**，无需重启。

**禁止**把以上变量写到：

- `~/.dsh/.env`（DSH home 层，会跟 cwd 层混淆优先级）
- 启动 dsh web 的 shell 里 export（如 `setx` 永久写注册表）—— 这些不是应用层变量，混在一起不安全
- `cordis.patch.yml` 的 `!!js process.env.X` 表达式里硬编码（除非是占位符）
- **bootstrap-only 变量**（`DSH_*` / `PATH` / `*_PROXY` / `NODE_*` 等）—— DSH 设计上禁止出现在 `.env` 里，nf-env-watcher 会拒绝整个 reload 并日志告警

**首次部署**（无 token）：先在 JIRA/Confluence 创建 PAT → 用 `write` 工具创建 `<cwd>/.env` 写入 token → 验证 `runtime/nf-env-watcher.log` 出现 `event=reload applied=[..., JIRA_PERSONAL_TOKEN, ...]` 行 → 在对话里问"agent 调一下 jira_search 看看我是谁"验证 token 生效。

**轮换 token**：直接编辑 `<cwd>/.env` 替换值即可，无需重启 dsh web。


## 输出模板

实现Atlassian MCP功能时，提供：

1. MCP服务器配置（JSON/环境变量）
2. 查询示例（带解释的JQL/CQL）
3. 带错误处理的工具调用实现
4. 认证设置说明
5. 权限要求的简要说明
