# 认证模式

---

## 认证方法概述

公司JIRA Server和Confluence Server仅支持PAT（个人访问令牌）认证。

| 方法 | 平台 | 用例 | 安全级别 |
|------|------|------|----------|
| PAT | 服务器/DC | 服务器集成 | 中 |

## 个人访问令牌（PAT）

### 创建PAT

**Jira服务器/DC：**
1. 个人资料 > 个人访问令牌
2. 创建令牌
3. 设置过期日期
4. 选择权限

**Confluence服务器/DC：**
1. 个人资料 > 设置 > 个人访问令牌
2. 创建令牌
3. 配置权限

### 使用PAT

```typescript
// JIRA Bearer令牌认证
const jiraResponse = await fetch('https://inone.intra.nsfocus.com/jira/rest/api/2/myself', {
  headers: {
    Authorization: `Bearer ${personalAccessToken}`,
    Accept: 'application/json',
  },
});

// Confluence Bearer令牌认证
const confluenceResponse = await fetch('https://inone.intra.nsfocus.com/confluence/rest/api/user/current', {
  headers: {
    Authorization: `Bearer ${personalAccessToken}`,
    Accept: 'application/json',
  },
});

// MCP服务器配置
const config = {
  JIRA_URL: 'https://inone.intra.nsfocus.com/jira',
  JIRA_PERSONAL_TOKEN: 'your-jira-personal-access-token',
  CONFLUENCE_URL: 'https://inone.intra.nsfocus.com/confluence',
  CONFLUENCE_PERSONAL_TOKEN: 'your-confluence-personal-access-token',
};
```

### PAT权限

| 权限 | Jira | Confluence |
|------|------|------------|
| 读取 | 浏览项目，查看工单 | 查看页面 |
| 写入 | 创建/编辑工单 | 创建/编辑页面 |
| 管理 | 项目管理 | 空间管理 |

## 令牌管理

### 令牌轮换策略

```typescript
class TokenRotationManager {
  private rotationInterval = 365 * 24 * 60 * 60 * 1000; // 365天

  async checkAndRotate(tokenCreatedAt: Date): Promise<boolean> {
    const age = Date.now() - tokenCreatedAt.getTime();

    if (age > this.rotationInterval) {
      console.warn('PAT需要轮换');
      return true;
    }

    return false;
  }

  async sendRotationReminder(email: string, tokenLabel: string, platform: 'JIRA' | 'Confluence' | 'both'): Promise<void> {
    // 与您的通知系统集成
    await sendEmail({
      to: email,
      subject: `${platform} PAT轮换提醒`,
      body: `您的${platform} PAT"${tokenLabel}"需要轮换。
             请创建新令牌并更新您的集成。`,
    });
  }
}
```

## 权限验证

### 检查当前权限

```typescript
interface PermissionReport {
  hasAllPermissions: boolean;
  details: Array<{
    operation: string;
    status: 'granted' | 'denied';
    error?: string;
  }>;
}

async function verifyPermissions(
  client: MCPClient,
  requiredOperations: string[]
): Promise<PermissionReport> {
  const report: PermissionReport = {
    hasAllPermissions: true,
    details: [],
  };

  for (const operation of requiredOperations) {
    try {
      switch (operation) {
        case 'read:jira':
          await client.callTool({
            name: 'jira_search',
            arguments: { jql: 'project is not empty', max_results: 1 },
          });
          break;
        case 'read:confluence':
          await client.callTool({
            name: 'confluence_search',
            arguments: { cql: 'type = page', limit: 1 },
          });
          break;
      }

      report.details.push({ operation, status: 'granted' });
    } catch (error: any) {
      report.hasAllPermissions = false;
      report.details.push({
        operation,
        status: 'denied',
        error: error.message,
      });
    }
  }

  return report;
}
```

## 安全检查清单

### 要做：
- 在专用密钥管理系统中存储密钥
- 实现令牌轮换策略
- 记录认证事件（不包含密钥）
- 在应用级别实现速率限制
- 使用前验证令牌

### 不要做：
- 在源代码中硬编码PAT令牌
- 记录令牌或密钥
- 在环境之间共享令牌
- 提交带有真实凭证的`.env`文件

### 环境配置模板

```bash
# .env.example（提交此文件）
JIRA_URL=https://inone.intra.nsfocus.com/jira
JIRA_AUTH_TYPE=pat
CONFLUENCE_URL=https://inone.intra.nsfocus.com/confluence
CONFLUENCE_AUTH_TYPE=pat

# PAT设置
JIRA_PERSONAL_TOKEN=
CONFLUENCE_PERSONAL_TOKEN=
```

```bash
# .gitignore
.env
.env.local
.env.*.local
credentials.json
**/secrets/**
```

## 故障排除

### 常见认证错误

**401未授权：**
- 无效或过期的PAT
- 缺少Authorization头

**403禁止：**
- PAT有效但缺少必要权限
- 资源级权限被拒绝
- IP允许列表阻止请求

### 调试认证

```typescript
async function debugJiraAuth(token: string): Promise<void> {
  // 检查令牌有效性
  const meResponse = await fetch(
    'https://inone.intra.nsfocus.com/jira/rest/api/2/myself',
    { headers: { Authorization: `Bearer ${token}` } }
  );

  console.log('JIRA令牌状态:', meResponse.status);

  if (meResponse.ok) {
    const me = await meResponse.json();
    console.log('JIRA认证身份:', me.name);
  }
}

async function debugConfluenceAuth(token: string): Promise<void> {
  // 检查令牌有效性
  const meResponse = await fetch(
    'https://inone.intra.nsfocus.com/confluence/rest/api/user/current',
    { headers: { Authorization: `Bearer ${token}` } }
  );

  console.log('Confluence令牌状态:', meResponse.status);

  if (meResponse.ok) {
    const me = await meResponse.json();
    console.log('Confluence认证身份:', me.displayName || me.username);
  }
}
```

## 相关参考

- `mcp-server-setup.md` - 带凭证的服务器配置
- `jira-operations.md` - 需要认证的JIRA操作
- `confluence-operations.md` - 需要认证的Confluence操作
