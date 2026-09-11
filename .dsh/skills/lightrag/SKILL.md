---
name: lightrag
description: "LightRAG知识图谱工具。通过CLI与LightRAG服务器交互，支持文档管理、知识查询、实体/关系操作。当用户需要向LightRAG插入文档、查询知识图谱、管理文档生命周期、或操作实体和关系时使用此技能。"
scene: null
user-invocable: true
allowed-tools:
  - Bash(npx tsx *$SKILL_DIR/lightrag-cli.ts *)
  - Bash(node *$SKILL_DIR/lightrag-cli.ts *)
---

# LightRAG 知识图谱工具

通过 CLI 与 LightRAG 服务器交互。CLI 脚本位于 `$SKILL_DIR/lightrag-cli.ts`。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LIGHTRAG_URL` | 服务器地址 | `http://10.66.23.38:18080` |
| `LIGHTRAG_API_KEY` | API 密钥 | 无 |
| `LIGHTRAG_TOKEN` | Bearer Token | 无 |

默认服务器地址：`http://10.66.23.38:18080`（所有命令自动使用，无需额外指定）

也可通过 `--url` 覆盖、`--api-key`、`--token` 参数传入。

## 用户请求

$ARGUMENTS

## 命令速查

### 查询知识库

```bash
# 基础查询（返回自然语言回答）
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 query -q "问题内容"

# 指定查询模式
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 query -q "问题内容" --mode hybrid

# 仅获取上下文（不生成回答）
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 query -q "问题内容" --context-only

# 获取结构化数据（实体、关系、块）
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 query-data -q "问题内容"
```

查询模式说明：
| 模式 | 适用场景 |
|------|----------|
| `mix` | **默认**，自动混合 local + global |
| `local` | 局部上下文，适合精确问题 |
| `global` | 全局知识，适合概览性问题 |
| `hybrid` | 混合检索 |
| `naive` | 简单文本匹配 |
| `bypass` | 跳过 RAG，直接调用 LLM |

### 插入文档

```bash
# 插入文本
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 insert -t "要插入的文本内容"

# 带来源标记
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 insert -t "文本" --source "文档名.md"

# 上传文件
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 insert-file -f /path/to/file.txt
```

### 文档管理

```bash
# 列出文档（支持分页和状态过滤）
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 docs
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 docs --page 2 --page-size 10
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 docs --status processed

# 查看状态统计
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 status-counts

# 查看 pipeline 状态
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 pipeline-status

# 跟踪处理进度
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 track <track-id>

# 删除指定文档
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 delete --ids doc1,doc2,doc3

# 清空所有文档
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 clear

# 清理缓存
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 clear-cache

# 扫描新文档
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 scan

# 重新处理失败的文档
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 reprocess

# 取消当前 pipeline
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 cancel
```

### 实体和关系管理

```bash
# 删除实体
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 delete-entity --name "实体名称"

# 删除关系
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 delete-relation --src "源实体" --tgt "目标实体"
```

### 认证

```bash
# 登录获取 token
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 login -u admin -p password123
```

## 典型工作流

### 1. 导入本地文档到知识库

```bash
# 上传文件
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 insert-file -f ./README.md

# 查看处理状态
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 docs --status processing

# 等待处理完成后查询
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 query -q "总结文档内容"
```

### 2. 批量插入文本

```bash
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 insert -t "第一条知识" --source "来源A"
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 insert -t "第二条知识" --source "来源B"
```

### 3. 查询知识图谱结构

```bash
# 获取实体和关系数据
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 query-data -q "所有相关实体"
```

## 输出格式

所有命令输出 JSON，可通过 `jq` 进一步处理：

```bash
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://10.66.23.38:18080 status-counts | jq '.status_counts'
```

## 错误处理

- 所有错误输出到 stderr，格式为 `Error: <message>`
- 非零退出码表示失败
- HTTP 错误会包含状态码和响应体
