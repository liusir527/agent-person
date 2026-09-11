---
name: memory-gen
description: "任务完成后的经验沉淀生成器。从刚完成的任务（配置、排障、开发、调试等）中提取可复用的、非特定环境的、能赋能其他 agent 的知识，按 <知识概要-年月日.md> 命名沉淀到 .dsh-memory/knowledge/experiences/sparse/ 目录（v2 知识库真实位置）。当用户提到'沉淀经验、抽萃知识、总结可复用经验、生成经验文档、memory-gen、经验入册'时使用。"
scene: null
user-invocable: true
---

# 经验沉淀生成器（memory-gen）

在**整个任务完成之后**运行：把任务中隐含的可复用知识提取出来，
写成一篇独立、自洽、可被其他 agent 直接读取复用的经验文档。

## 核心原则

只沉淀以下几类知识，其余不沉淀：

| 要沉淀（可复用） | 不要沉淀（环境相关） |
|-----------------|--------------------|
| 方法论、流程、判断标准 | 本次任务的具体设备 IP / 账号 / 密码 |
| 踩坑点与避坑方法 | 临时路径、会话号、一次性日志 |
| 工具用法的通用技巧 | 仅对本次场景成立的数值配置 |
| 决策依据与权衡（为什么这么做） | 时间线流水账、情绪化描述 |

**一句话判定：** 换一个 agent、换一台设备、下次遇到同类问题时，
这条知识是否依然有用？有用 → 沉淀；没用 → 丢弃。

## 触发时机

- 任务有明确结论（排障有根因、配置已生效、功能已完成）
- 结论能提炼出至少 1 条"再次遇到同类问题时会想起的教训或流程"

## 执行流程

1. **回放任务**：回顾这次任务做了什么、关键判断点有哪些、哪个环节卡壳/走弯路。
2. **筛选知识**：按上面原则，逐条判断哪条值得沉淀（宁缺毋滥）。
3. **提炼内容**：写成"下一个人看到就能照做"的表述——
   包含**怎么判断（场景）、怎么做（步骤）、为什么（原因）**，缺一不可。
4. **写入文件**：输出到 **`<workspace_root>/.dsh-memory/knowledge/experiences/sparse/`**（v2 知识库真实位置）
   （**路径锚定**：`<workspace_root>` = 当前 git 仓库根，由 LLM 在运行时通过 `git rev-parse --show-toplevel` 解析；
   `.dsh-memory/` 是 git submodule 真身，存放在仓库根下，禁止在其他位置创建幻影路径），
   命名 `知识概要-年月日.md`（见下文命名规范）。
5. **更新索引**：维护索引文件 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/索引.md`，
   格式见下；不存在则先创建。
6. **自校验锚定**：写入后执行 `git -C "$(git rev-parse --show-toplevel)" status --short`，
   应能看到 `.dsh-memory/knowledge/experiences/sparse/` 下的新文件；
   若路径不以 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/` 开头，说明锚定错误，需改正后再继续。

> **写入方式**：优先用 MCP `mcp__memory__memory_save`（自动合并去重 + 自动更新索引）；不可用时降级用 `read/write` 工具直接操作 `.dsh-memory/knowledge/experiences/{refined,sparse,expired}/*.md`。

## 命名规范

```
<workspace_root>/.dsh-memory/knowledge/experiences/sparse/知识概要-年月日.md
```

| 部分 | 规则 | 示例 |
|------|------|------|
| 知识概要 | 中文，8~16 字，概括知识主题，不含 `/\:*?"<>|` | `交换机接口配置避坑指南` |
| 年月日 | YYYYMMDD，任务完成当日 | `20260820` |

完整示例：`<workspace_root>/.dsh-memory/knowledge/experiences/sparse/交换机接口配置避坑指南-20260820.md`

> **路径锚定（必须）**：`<workspace_root>` = 当前 git 仓库根（运行 `git rev-parse --show-toplevel` 得到）。
> 所有经验文档**必须**输出到 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/`（v2 知识库 sparse 层）。
> `.dsh-memory/` 真身位于该仓库根下（作为 git submodule），禁止在其他位置创建幻影路径。

> **重名规避**：同一天、同类知识概要若已存在同名文件，在概要后追加序号
> （如 `接口配置避坑指南-2-20260820.md`），禁止静默覆盖已有沉淀。

## 索引文件

`索引.md` 维护在 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/` 下，追加一行格式：

```markdown
- 2026-08-20 [交换机接口配置避坑指南](交换机接口配置避坑指南-20260820.md) — 一句话概述
```

> **总索引边界**：v2 知识库按 `refined > sparse > expired` 三级分层各自维护 `索引.md`；无单一"总索引"概念。
> 检索入口见 `.dsh-memory/README.md` 或通过 `mcp__memory__memory_search` 工具。
> 新经验默认落 sparse 层；命中 3 次复用成功后由 `tier_manager.py` 自动晋升到 refined 层。

## 文档模板

```markdown
---
id: exp-YYYYMMDD-NNN
tags: [tag1, tag2]
severity: high|medium|low
category: <类型>
occurrence: 1
status: active
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
---

# <知识概要>

> 一句话概述：这条经验解决什么问题。

## 适用场景
什么情况下会遇到这个问题 / 需要这条知识。

## 核心流程 / 知识点
分步骤写清"怎么做"，每步给出原因。

## 常见坑
| 坑 | 表现 | 避坑方法 |
|----|------|---------|
| ... | ... | ... |

## 判定/决策依据
何时选 A 不选 B，判断标准是什么。

## 相关
关联的可复用小工具、已有文档、或同主题经验。
```

frontmatter 必填字段：`id` / `tags` / `severity` / `category` / `occurrence` / `status` / `created_at` / `updated_at`；正文必须含 `## 适用场景` + `## 核心流程 / 知识点`（与 `## 现象` + `## 解决方案` 等价表述）。

## 质量标准

写完后自检：

- [ ] 换他人/换环境依然适用（无环境残留）
- [ ] 有"怎么做"和"为什么"，不是结论堆砌
- [ ] 步骤可操作，不是抽象口号
- [ ] 长度适中：一条经验 20~120 行，聚焦单一主题
- [ ] frontmatter 齐全
