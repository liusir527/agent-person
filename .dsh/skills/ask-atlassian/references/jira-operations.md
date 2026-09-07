# JIRA查询和操作

---

## JQL基础

### 基本查询结构

```
field OPERATOR value [AND|OR field OPERATOR value]
```

### 常用操作符

| 操作符 | 描述 | 示例 |
|--------|------|------|
| `=` | 精确匹配 | `project = "PROJ"` |
| `!=` | 不等于 | `status != Done` |
| `~` | 包含（文本搜索） | `summary ~ "login bug"` |
| `!~` | 不包含 | `description !~ "test"` |
| `>`, `<`, `>=`, `<=` | 比较 | `created >= -7d` |
| `IN` | 多个值 | `status IN (Open, "In Progress")` |
| `NOT IN` | 排除值 | `assignee NOT IN (john, jane)` |
| `IS` | 空值检查 | `assignee IS EMPTY` |
| `IS NOT` | 非空 | `resolution IS NOT EMPTY` |
| `WAS` | 历史状态 | `status WAS "In Progress"` |
| `CHANGED` | 字段变更 | `status CHANGED FROM Open` |

### 字段参考

**标准字段：**
```jql
project = PROJ
issuetype = Bug
status = "In Progress"
priority = High
assignee = currentUser()
reporter = "john.doe"
resolution = Unresolved
labels = backend
component = "API"
fixVersion = "2.0"
affectsVersion = "1.5"
```

**日期字段：**
```jql
created >= -30d                    -- 最近30天
updated >= "2024-01-01"           -- 从指定日期开始
due <= endOfWeek()                 -- 本周到期
resolved >= startOfMonth()         -- 本月解决
```

**文本搜索：**
```jql
summary ~ "authentication"         -- 摘要包含
description ~ "error AND login"    -- 描述搜索
text ~ "payment failed"            -- 所有文本字段
comment ~ "blocked"                -- 评论包含
```

## 核心JQL模式

### Bug跟踪

```jql
-- 按优先级的打开bug
issuetype = Bug AND resolution IS EMPTY ORDER BY priority DESC

-- 关键生产bug
issuetype = Bug AND priority IN (Highest, High)
  AND labels = production AND resolution IS EMPTY

-- 本周创建的bug
issuetype = Bug AND created >= startOfWeek()

-- 没有复现步骤的bug
issuetype = Bug AND "Reproduction Steps" IS EMPTY
  AND resolution IS EMPTY

-- 回归bug
issuetype = Bug AND labels = regression AND fixVersion = "2.0"
```

### 团队工作负载

```jql
-- 我的打开工单
assignee = currentUser() AND resolution IS EMPTY

-- 未分配的高优先级
assignee IS EMPTY AND priority IN (Highest, High)
  AND resolution IS EMPTY

-- 团队成员工作负载
assignee = "jane.smith"

-- 阻塞的工单
status = Blocked OR labels = blocked

-- 过时的工单（14天未更新）
updated <= -14d AND resolution IS EMPTY
```

### 发布管理

```jql
-- 发布候选
fixVersion = "2.0" AND status = "Ready for Release"

-- 缺少修复版本
resolution = Done AND fixVersion IS EMPTY AND updated >= -30d

-- 发布阻塞者
fixVersion = "2.0" AND priority = Blocker AND resolution IS EMPTY

-- 变更日志项
fixVersion = "2.0" AND resolution = Done ORDER BY issuetype
```

## MCP工具调用

### 搜索工单

```typescript
// 基本JQL搜索
const searchResult = await client.callTool({
  name: "jira_search",
  arguments: {
    jql: "project = PROJ AND status = Open",
    max_results: 50,
    fields: ["summary", "status", "assignee", "priority"]
  }
});

// 解析响应
const issues = JSON.parse(searchResult.content[0].text);
for (const issue of issues.issues) {
  console.log(`${issue.key}: ${issue.fields.summary}`);
}
```

### 获取工单详情

```typescript
// 获取带所有字段的单个工单
const issue = await client.callTool({
  name: "jira_get_issue",
  arguments: {
    issue_key: "PROJ-123",
    expand: ["changelog", "comments", "transitions"]
  }
});

// 获取带特定字段的工单
const issuePartial = await client.callTool({
  name: "jira_get_issue",
  arguments: {
    issue_key: "PROJ-123",
    fields: ["summary", "description", "customfield_10001"]
  }
});
```

### 创建工单

```typescript
// 创建bug
const newBug = await client.callTool({
  name: "jira_create_issue",
  arguments: {
    project_key: "PROJ",
    issue_type: "Bug",
    summary: "启用SSO时登录失败",
    description: {
      type: "doc",
      version: 1,
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "启用SSO时用户无法登录。" }]
        },
        {
          type: "heading",
          attrs: { level: 3 },
          content: [{ type: "text", text: "复现步骤" }]
        },
        {
          type: "orderedList",
          content: [
            { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "在设置中启用SSO" }] }] },
            { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "登出" }] }] },
            { type: "listItem", content: [{ type: "paragraph", content: [{ type: "text", text: "尝试通过SSO登录" }] }] }
          ]
        }
      ]
    },
    priority: "High",
    labels: ["sso", "authentication", "production"],
    components: ["Authentication"],
    assignee: "jane.smith"
  }
});

console.log(`创建成功: ${newBug.content[0].text}`); // PROJ-456
```

### 更新工单

```typescript
// 更新工单字段
await client.callTool({
  name: "jira_update_issue",
  arguments: {
    issue_key: "PROJ-123",
    fields: {
      summary: "更新的摘要",
      priority: { name: "Highest" },
      labels: ["urgent", "production"]
    }
  }
});

// 添加评论
await client.callTool({
  name: "jira_add_comment",
  arguments: {
    issue_key: "PROJ-123",
    body: "正在调查此问题。初步分析表明存在竞争条件。"
  }
});

// 转员工单
await client.callTool({
  name: "jira_transition_issue",
  arguments: {
    issue_key: "PROJ-123",
    transition: "In Progress"
  }
});
```

### 工单链接

使用`jira_create_issue_link`创建工单之间的依赖关系。

> **参数名称违反直觉。** 命名反映了Jira内部的"内向/外向"链接方向，而不是自然英语。根据下表验证每个链接调用。

#### "Blocks"链接的参数语义

| 参数 | 角色 | 含义 |
|------|------|------|
| `inward_issue_key` | **阻塞者** | 此工单阻塞另一个 |
| `outward_issue_key` | **被阻塞者** | 此工单被另一个阻塞 |

**记忆辅助：** `inward_issue_key` = 接收内向描述（"被...阻塞"）的工单 —— 但它是*阻塞者*。想象："inward键是箭头指向的来源。"

#### 单个阻塞链接

```typescript
// 让AUTH-1阻塞AUTH-2
// AUTH-1将显示："blocks AUTH-2"
// AUTH-2将显示："is blocked by AUTH-1"
await client.callTool({
  name: "jira_create_issue_link",
  arguments: {
    link_type: "Blocks",
    inward_issue_key: "AUTH-1",   // 阻塞者
    outward_issue_key: "AUTH-2"   // 被阻塞者
  }
});
```

#### 链接依赖链

创建链A → B → C（A阻塞B，B阻塞C）时：

```typescript
const chain = [
  { blocker: "AUTH-1", blocked: "AUTH-2" },
  { blocker: "AUTH-2", blocked: "AUTH-3" },
  { blocker: "AUTH-3", blocked: "AUTH-4" }
];

for (const dep of chain) {
  await client.callTool({
    name: "jira_create_issue_link",
    arguments: {
      link_type: "Blocks",
      inward_issue_key: dep.blocker,
      outward_issue_key: dep.blocked
    }
  });

  // 尊重链接操作之间的速率限制
  await delay(100);
}
```

#### 其他链接类型

相同的`inward`/`outward`模式适用于所有链接类型：

| 链接类型 | `inward_issue_key`显示 | `outward_issue_key`显示 |
|----------|------------------------|-------------------------|
| `Blocks` | "blocks [outward]" | "is blocked by [inward]" |
| `Duplicate` | "duplicates [outward]" | "is duplicated by [inward]" |
| `Relates` | "relates to [outward]" | "relates to [inward]" |

```typescript
// 标记PROJ-10为PROJ-5的副本
await client.callTool({
  name: "jira_create_issue_link",
  arguments: {
    link_type: "Duplicate",
    inward_issue_key: "PROJ-10",   // 副本
    outward_issue_key: "PROJ-5"    // 原件
  }
});
```

#### 反模式：参数反转

```typescript
// 错误 —— 这会让AUTH-2阻塞AUTH-1（反了！）
await client.callTool({
  name: "jira_create_issue_link",
  arguments: {
    link_type: "Blocks",
    inward_issue_key: "AUTH-2",   // 意外让AUTH-2成为阻塞者
    outward_issue_key: "AUTH-1"   // 意外让AUTH-1成为被阻塞者
  }
});
```

始终验证：创建链接后，阻塞者（`inward_issue_key`）应该在其Jira工单视图中显示"blocks [outward]"。

## 分页处理

```typescript
async function getAllIssues(jql: string): Promise<Issue[]> {
  const allIssues: Issue[] = [];
  let startAt = 0;
  const maxResults = 100;

  while (true) {
    const result = await client.callTool({
      name: "jira_search",
      arguments: {
        jql,
        start_at: startAt,
        max_results: maxResults,
        fields: ["summary", "status", "assignee"]
      }
    });

    const response = JSON.parse(result.content[0].text);
    allIssues.push(...response.issues);

    if (startAt + response.issues.length >= response.total) {
      break;
    }

    startAt += maxResults;
  }

  return allIssues;
}
```

## 批量操作

```typescript
// 使用JQL批量更新
async function bulkUpdateLabels(jql: string, addLabels: string[]) {
  const issues = await getAllIssues(jql);

  for (const issue of issues) {
    const existingLabels = issue.fields.labels || [];
    await client.callTool({
      name: "jira_update_issue",
      arguments: {
        issue_key: issue.key,
        fields: {
          labels: [...new Set([...existingLabels, ...addLabels])]
        }
      }
    });

    // 尊重速率限制
    await delay(100);
  }
}

// 使用
await bulkUpdateLabels(
  'project = PROJ AND labels = backend',
  ['q4-priority', 'needs-review']
);
```

## 错误处理

```typescript
async function safeJiraCall<T>(
  operation: () => Promise<T>,
  retries = 3
): Promise<T> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      const status = error.response?.status;

      // 不重试客户端错误（速率限制除外）
      if (status >= 400 && status < 500 && status !== 429) {
        throw error;
      }

      // 速率限制 - 等待并重试
      if (status === 429) {
        const retryAfter = parseInt(error.response?.headers?.['retry-after'] || '60');
        console.log(`速率受限。等待${retryAfter}秒...`);
        await delay(retryAfter * 1000);
        continue;
      }

      // 服务器错误 - 指数退避
      if (attempt < retries) {
        const backoff = Math.pow(2, attempt) * 1000;
        console.log(`尝试${attempt}失败。${backoff}ms后重试...`);
        await delay(backoff);
      } else {
        throw error;
      }
    }
  }
  throw new Error('重试循环意外结束');
}
```

## 常见反模式

**避免：**
```jql
-- 太宽泛（慢，可能超时）
project IS NOT EMPTY

-- 多词值缺少引号
status = In Progress  -- 错误
status = "In Progress"  -- 正确

-- 大小写敏感性问题
assignee = John  -- 可能失败
assignee = "john.doe@company.com"  -- 正确

-- 低效排序
ORDER BY created  -- 缺少方向
ORDER BY created DESC  -- 正确
```

## 相关参考

- `authentication-patterns.md` - API调用的凭证设置
