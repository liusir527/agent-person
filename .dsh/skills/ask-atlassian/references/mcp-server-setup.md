# MCP服务器设置

---

## 服务器选项

### mcp-atlassian (sooperset)

使用开源的 mcp-atlassian (sooperset) 连接公司Atlassian套件：

```bash
# 使用uv安装（推荐）
uv tool install mcp-atlassian

# 或使用pip
pip install mcp-atlassian
```

**功能：**
- Jira Server/DC集成
- Confluence Server/DC集成
- PAT（个人访问令牌）认证
- 工单和页面的读写操作
- JQL和CQL查询支持

## 配置方式

根据您使用的AI编程工具选择对应的配置方式：

---

### Claude Code CLI 用户

使用 `claude mcp add` 命令直接添加 MCP 服务器，无需手动编辑配置文件：

```bash
# 先设置环境变量
export JIRA_PERSONAL_TOKEN="你的JIRA_PAT令牌"
export CONFLUENCE_PERSONAL_TOKEN="你的Confluence_PAT令牌"

# 添加到用户级配置（所有项目通用）
claude mcp add \
  -e JIRA_URL=https://inone.intra.nsfocus.com/jira \
  -e JIRA_PERSONAL_TOKEN="$JIRA_PERSONAL_TOKEN" \
  -e CONFLUENCE_URL=https://inone.intra.nsfocus.com/confluence \
  -e CONFLUENCE_PERSONAL_TOKEN="$CONFLUENCE_PERSONAL_TOKEN" \
  -s user \
  atlassian -- uvx mcp-atlassian
```

**Scope 选项说明：**
- `-s user` - 用户级配置（所有项目通用）
- `-s project` - 项目级配置（仅当前项目）
- `-s local` - 本地配置（默认）

> **重要：** 配置完成后，请**重启当前 Claude Code 会话**以使配置生效。

---

### 其他AI编程工具用户

手动编辑配置文件，添加JSON配置：

**Claude Desktop 应用配置文件位置：**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/claude/claude_desktop_config.json`

**其他工具请参考其MCP配置文档。**

### 配置示例

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

## 环境变量参考

### JIRA配置

| 变量 | 描述 | 必需 |
|------|------|------|
| `JIRA_URL` | Jira实例的基础URL | 是 |
| `JIRA_PERSONAL_TOKEN` | PAT（个人访问令牌） | 是 |
| `JIRA_SSL_VERIFY` | 验证SSL证书（默认：true） | 否 |

### Confluence配置

| 变量 | 描述 | 必需 |
|------|------|------|
| `CONFLUENCE_URL` | Confluence实例的基础URL | 是 |
| `CONFLUENCE_PERSONAL_TOKEN` | PAT（个人访问令牌） | 是 |

### 高级选项

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `MCP_LOG_LEVEL` | 日志详细程度（DEBUG, INFO, WARN, ERROR） | INFO |
| `MCP_TIMEOUT` | 请求超时（秒） | 30 |
| `MCP_MAX_RETRIES` | 最大重试次数 | 3 |
| `MCP_RATE_LIMIT` | 每秒请求数 | 10 |

## 验证和测试

### 检查服务器状态

```bash
# 测试sooperset服务器
uvx mcp-atlassian --help

# 验证环境变量
env | grep -E "(JIRA_|CONFLUENCE_)"
```

### 测试连接

创建一个简单的测试脚本：

```typescript
// test-connection.ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function testConnection() {
  const transport = new StdioClientTransport({
    command: "uvx",
    args: ["mcp-atlassian"],
    env: process.env,
  });

  const client = new Client(
    { name: "test-client", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);

  // 列出可用工具
  const tools = await client.listTools();
  console.log("可用工具:", tools.tools.map(t => t.name));

  await client.close();
}

testConnection().catch(console.error);
```

## 故障排除

### 常见问题

**"Connection refused"错误：**
```bash
# 检查服务器是否正在运行
ps aux | grep mcp-atlassian

# 验证URL是否可访问
curl -I https://inone.intra.nsfocus.com/jira
curl -I https://inone.intra.nsfocus.com/confluence

# 检查防火墙/代理设置
echo $HTTP_PROXY $HTTPS_PROXY
```

**"Authentication failed"错误：**
```bash
# 验证JIRA PAT有效
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://inone.intra.nsfocus.com/jira/rest/api/2/myself"

# 验证Confluence PAT有效
curl -H "Authorization: Bearer YOUR_PAT" \
  "https://inone.intra.nsfocus.com/confluence/rest/api/user/current"
```

**"Rate limit exceeded"错误：**
```json
{
  "mcpServers": {
    "atlassian": {
      "env": {
        "MCP_RATE_LIMIT": "5"
      }
    }
  }
}
```

### 调试模式

启用详细日志：

```json
{
  "mcpServers": {
    "atlassian": {
      "env": {
        "MCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## 安全最佳实践

1. **永远不要提交凭证** - 使用环境变量或密钥管理
2. **定期轮换PAT** - 设置365天轮换的日历提醒
3. **启用审计日志** - 跟踪API使用以合规
4. **限制网络访问** - 在可能的情况下使用允许列表

## 相关参考

- `authentication-patterns.md` - PAT设置详情
- `jira-operations.md` - 连接建立后的JQL语法
- `confluence-operations.md` - 连接建立后的CQL语法
