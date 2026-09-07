# Confluence操作

---

## CQL基础

### 基本查询结构

```
field OPERATOR value [AND|OR field OPERATOR value]
```

### 常用操作符

| 操作符 | 描述 | 示例 |
|--------|------|------|
| `=` | 精确匹配 | `space = "DEV"` |
| `!=` | 不等于 | `type != attachment` |
| `~` | 包含 | `title ~ "API"` |
| `!~` | 不包含 | `text !~ "deprecated"` |
| `>`, `<`, `>=`, `<=` | 比较 | `lastModified >= "2024-01-01"` |
| `IN` | 多个值 | `space IN ("DEV", "OPS")` |
| `NOT IN` | 排除值 | `creator NOT IN ("bot")` |

### 字段参考

**内容字段：**
```cql
type = page                        -- 仅页面
type = blogpost                    -- 博客文章
type = attachment                  -- 附件
type = comment                     -- 评论
space = "DEVDOCS"                  -- 特定空间
space.type = global                -- 全局空间
space.type = personal              -- 个人空间
```

**搜索字段：**
```cql
title ~ "architecture"             -- 标题包含
text ~ "kubernetes"                -- 全文搜索
content ~ "deployment"             -- 内容正文
label = "official"                 -- 有标签
label IN ("api", "reference")      -- 多个标签
```

**日期字段：**
```cql
created >= "2024-01-01"            -- 在日期后创建
lastModified >= now("-30d")        -- 最近30天修改
created >= startOfYear()           -- 今年创建
lastModified >= startOfMonth()     -- 本月修改
```

**用户字段：**
```cql
creator = currentUser()            -- 我创建的
contributor = "john.doe"           -- 用户编辑的
mention = currentUser()            -- 提到我
watcher = currentUser()            -- 我关注的页面
favourite = currentUser()          -- 我的收藏
```

## 核心CQL模式

### 文档搜索

```cql
-- 开发空间中的API文档
space = "DEV" AND label = "api-docs" AND type = page

-- 最近更新的架构文档
label = "architecture" AND lastModified >= now("-7d")

-- 搜索代码示例
text ~ "```" AND label = "tutorial"

-- 查找过时文档
label = "needs-review" OR lastModified <= now("-180d")

-- 本月的会议记录
label = "meeting-notes" AND created >= startOfMonth()
```

### 空间管理

```cql
-- 多个空间中的所有页面
space IN ("DEV", "OPS", "PRODUCT") AND type = page

-- 个人空间内容
space.type = personal AND creator = currentUser()

-- 已归档内容
label = "archived" AND space = "LEGACY"

-- 模板
type = page AND label = "template"
```

### 内容发现

```cql
-- 热门页面（频繁查看）
type = page AND space = "DOCS" ORDER BY lastModified DESC

-- 草稿页面
label = "draft" AND type = page

-- 没有标签的页面
type = page AND space = "DEV" AND label IS NULL

-- 孤立页面（无父级）
type = page AND ancestor IS NULL AND space = "DOCS"
```

## MCP工具调用

### 搜索内容

```typescript
// 基本CQL搜索
const searchResult = await client.callTool({
  name: "confluence_search",
  arguments: {
    cql: 'space = "DEV" AND label = "api-docs"',
    limit: 25,
    expand: ["body.storage", "version", "ancestors"]
  }
});

// 解析结果
const results = JSON.parse(searchResult.content[0].text);
for (const page of results.results) {
  console.log(`${page.title} - ${page._links.webui}`);
}

// 带内容预览搜索
const searchWithContent = await client.callTool({
  name: "confluence_search",
  arguments: {
    cql: 'text ~ "deployment" AND space = "OPS"',
    limit: 10,
    excerpt: true
  }
});
```

### 获取页面内容

```typescript
// 按ID获取页面
const page = await client.callTool({
  name: "confluence_get_page",
  arguments: {
    page_id: "123456",
    expand: ["body.storage", "body.view", "version", "ancestors", "children.page"]
  }
});

// 按空间和标题获取页面
const pageByTitle = await client.callTool({
  name: "confluence_get_page_by_title",
  arguments: {
    space_key: "DEV",
    title: "API Reference"
  }
});

// 获取页面子级
const children = await client.callTool({
  name: "confluence_get_children",
  arguments: {
    page_id: "123456",
    expand: ["page"]
  }
});
```

### 创建页面

```typescript
// 使用存储格式（XHTML）创建页面
const newPage = await client.callTool({
  name: "confluence_create_page",
  arguments: {
    space_key: "DEV",
    title: "API认证指南",
    parent_id: "123456",  // 可选父页面
    body: `
      <h2>概述</h2>
      <p>本指南涵盖我们API的认证方法。</p>

      <h2>PAT认证</h2>
      <p>使用个人访问令牌（PAT）进行认证：</p>
      <ac:structured-macro ac:name="info">
        <ac:rich-text-body>
          <p>PAT绑定到您的用户帐户，具有相同的权限。</p>
        </ac:rich-text-body>
      </ac:structured-macro>
    `,
    labels: ["api-docs", "authentication", "official"]
  }
});

console.log(`创建页面: ${newPage.content[0].text}`);
```

### 更新页面

```typescript
// 更新页面内容
await client.callTool({
  name: "confluence_update_page",
  arguments: {
    page_id: "123456",
    title: "API认证指南（已更新）",
    body: "<h2>更新的内容</h2><p>这里是新文档...</p>",
    version_number: 5,  // 当前版本 + 1
    version_message: "更新了PAT认证章节"
  }
});

// 追加到现有页面
const currentPage = await client.callTool({
  name: "confluence_get_page",
  arguments: {
    page_id: "123456",
    expand: ["body.storage", "version"]
  }
});

const pageData = JSON.parse(currentPage.content[0].text);
const currentBody = pageData.body.storage.value;
const newSection = `
  <h2>新章节</h2>
  <p>追加到页面的附加内容。</p>
`;

await client.callTool({
  name: "confluence_update_page",
  arguments: {
    page_id: "123456",
    title: pageData.title,
    body: currentBody + newSection,
    version_number: pageData.version.number + 1
  }
});
```

### 处理评论

```typescript
// 向页面添加评论
await client.callTool({
  name: "confluence_add_comment",
  arguments: {
    page_id: "123456",
    body: "<p>此章节需要针对v2.0更改进行更新。</p>"
  }
});

// 获取页面评论
const comments = await client.callTool({
  name: "confluence_get_comments",
  arguments: {
    page_id: "123456",
    expand: ["body.storage", "version"]
  }
});

// 回复评论
await client.callTool({
  name: "confluence_add_comment",
  arguments: {
    page_id: "123456",
    parent_comment_id: "789012",
    body: "<p>好发现！我会更新此章节。</p>"
  }
});
```

### 管理标签

```typescript
// 向页面添加标签
await client.callTool({
  name: "confluence_add_labels",
  arguments: {
    page_id: "123456",
    labels: ["reviewed", "q1-2024", "api-v2"]
  }
});

// 移除标签
await client.callTool({
  name: "confluence_remove_label",
  arguments: {
    page_id: "123456",
    label: "draft"
  }
});

// 获取页面标签
const labels = await client.callTool({
  name: "confluence_get_labels",
  arguments: {
    page_id: "123456"
  }
});
```

### 空间操作

```typescript
// 获取空间信息
const space = await client.callTool({
  name: "confluence_get_space",
  arguments: {
    space_key: "DEV",
    expand: ["description", "homepage"]
  }
});

// 列出所有空间
const spaces = await client.callTool({
  name: "confluence_list_spaces",
  arguments: {
    type: "global",
    limit: 100
  }
});

// 获取空间内容
const spaceContent = await client.callTool({
  name: "confluence_get_space_content",
  arguments: {
    space_key: "DEV",
    depth: "root",  // 或 "all"
    expand: ["children.page"]
  }
});
```

## 存储格式参考

### 常用宏

```xml
<!-- 代码块 -->
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:parameter ac:name="title">示例</ac:parameter>
  <ac:plain-text-body><![CDATA[print("Hello, World!")]]></ac:plain-text-body>
</ac:structured-macro>

<!-- 信息面板 -->
<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">注意</ac:parameter>
  <ac:rich-text-body>
    <p>这里是重要信息。</p>
  </ac:rich-text-body>
</ac:structured-macro>

<!-- 警告面板 -->
<ac:structured-macro ac:name="warning">
  <ac:rich-text-body>
    <p>小心此操作！</p>
  </ac:rich-text-body>
</ac:structured-macro>

<!-- 目录 -->
<ac:structured-macro ac:name="toc">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
</ac:structured-macro>

<!-- 展开章节 -->
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">点击展开</ac:parameter>
  <ac:rich-text-body>
    <p>这里是隐藏的内容。</p>
  </ac:rich-text-body>
</ac:structured-macro>

<!-- 包含页面 -->
<ac:structured-macro ac:name="include">
  <ac:parameter ac:name=""><ri:page ri:content-title="共享页脚" /></ac:parameter>
</ac:structured-macro>
```

### 格式化元素

```xml
<!-- 状态徽章 -->
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Green</ac:parameter>
  <ac:parameter ac:name="title">已批准</ac:parameter>
</ac:structured-macro>

<!-- 用户提及 -->
<ac:link><ri:user ri:account-id="557058:f3c7..." /></ac:link>

<!-- 页面链接 -->
<ac:link><ri:page ri:content-title="目标页面" ri:space-key="DEV" /></ac:link>

<!-- 附件 -->
<ac:link><ri:attachment ri:filename="diagram.png" /></ac:link>

<!-- 来自附件的图像 -->
<ac:image><ri:attachment ri:filename="screenshot.png" /></ac:image>

<!-- 外部图像 -->
<ac:image><ri:url ri:value="https://example.com/image.png" /></ac:image>
```

## 分页处理

```typescript
async function getAllPages(cql: string): Promise<Page[]> {
  const allPages: Page[] = [];
  let start = 0;
  const limit = 100;

  while (true) {
    const result = await client.callTool({
      name: "confluence_search",
      arguments: {
        cql,
        start,
        limit,
        expand: ["body.storage"]
      }
    });

    const response = JSON.parse(result.content[0].text);
    allPages.push(...response.results);

    if (response.results.length < limit || !response._links.next) {
      break;
    }

    start += limit;
  }

  return allPages;
}
```

## 错误处理

```typescript
async function safeConfluenceCall<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch (error: any) {
    const status = error.response?.status;

    switch (status) {
      case 404:
        throw new Error(`找不到页面或空间: ${error.message}`);
      case 403:
        throw new Error(`权限被拒绝。检查空间权限。`);
      case 409:
        throw new Error(`版本冲突。页面已被修改。刷新并重试。`);
      case 429:
        const retryAfter = error.response?.headers?.['retry-after'] || 60;
        throw new Error(`速率受限。${retryAfter}秒后重试。`);
      default:
        throw error;
    }
  }
}
```

## 常见反模式

**避免：**
```cql
-- 太宽泛（慢）
text ~ "the"

-- 缺少引号
space = DEV DOCS  -- 错误
space = "DEV DOCS"  -- 正确

-- 无效日期格式
created >= 2024-01-01  -- 错误
created >= "2024-01-01"  -- 正确
```

**最佳实践：**
- 尽可能指定空间以加快查询速度
- 使用标签进行分类和过滤
- 将文本搜索与特定字段结合使用
- 缓存频繁访问的页面内容
- 优雅处理版本冲突

## 相关参考

- `authentication-patterns.md` - API访问配置
