---
name: file-review
description: "主 agent（或被派发的写作者 subagent）完成文件落盘后，强制派发一个长期持有的 reviewer subagent（DSH run_in_background + send_message）对写入的文件进行多轮审查—修复—复审循环。每轮审查产出结构化问题清单，由原作者负责修复，reviewer 在同一会话中复审。最长 3 轮，第 3 轮仍未通过则降级为人工处理。"
user-invocable: false
---

# 文件落盘审查器（多轮状态保持版）

将本 skill 作为**主 agent 在每次成功写入文件之后必须串接的审查调度器**。reviewer 是一个**有状态的、可被 send_message 续接的 subagent**，不是 fresh-agent。

## 核心原则

1. **审查对象**：所有通过 write/edit 工具成功落盘的文件（`.md` / `.py` / `.sh` / `.json` / `.yaml` / 任何文本文件）。
2. **reviewer 持有**：每次触发本 skill 时，派发**新的 reviewer subagent 并保留其 subagent_id**，整个 review 循环期间所有轮次都向**同一个 id** 发送消息，避免上下文丢失。
3. **修复者**：默认是**写文件的原始作者**（大多数情况下就是主 agent 本身；若落盘动作是某个 write-author subagent 完成的，则由那个 subagent 修复）。
4. **修复后必须复审**：任何对审查标的的修改都必须再次交由原 reviewer 复审，禁止作者自行宣称"已修复"。
5. **硬上限 3 轮**：第 1 轮审查 → 修复 → 第 2 轮复审 → 修复 → 第 3 轮复审。第 3 轮 reviewer 仍未输出 `PASS` 则整个流程降级为人工。

## 触发条件

满足以下任一条件立即触发本 skill：

- 调用了 `write` 工具并返回成功。
- 调用了 `edit` 工具并返回成功，且修改对象是审查类敏感文件（见下方"审查重点"中的文件类型）。
- 用户显式说"审查一下 / review 一下 / 检查一下刚才写的"。

无需触发：

- 仅 `read` / `grep` / `glob` 等只读操作。
- 修改的对象是本 skill 文件本身（避免循环）。
- 修改的对象是机器生成的产物目录（构建产物、依赖缓存、版本控制元数据等）。

## 派发 reviewer subagent（首次）

主 agent 必须用 `subagent` 工具派发一个长期持有的 reviewer：

```text
subagent(
  description: "reviewer for <本次写入的文件列表>",
  prompt: <见下方"reviewer 角色 Prompt 模板">,
  run_in_background: true   # 关键：必须 background
)
```

**拿到 `subagent_id` 后必须把它记入主 agent 的 todo 列表**，整个 review 循环都引用同一个 id。

### reviewer 角色 Prompt 模板

```
你是「文件落盘审查 reviewer」。你的职责是：对主 agent（或其它写作者 subagent）刚刚写入的文件进行结构化审查，
并对作者回传的修复结果进行复审。全程保持同一会话，不丢失上下文。

【本次审查范围】
- 落盘的文件：
  - <path1>（<类型 md/py/sh/...>）
  - <path2>（...）
- 作者 subagent_id（若有，否则写 "主agent"）：<author_id>
- 本次是第 <N> 轮审查（N=1 为初查，N≥2 为复审）

【审查重点】（按文件类型差异化）
1. 通用：
   - 路径硬编码：禁止出现 C:\Users\xxx、/home/xxx 等用户特定路径（除非有正当理由并加注释）
   - 编码：UTF-8，无 BOM；中文文档需保留中文
   - 前后端字段匹配：文档中提及的字段名、参数名与代码实际定义一致

2. .md 文档（尤其经验 / skill / README）：
   - frontmatter 必填字段是否齐全（name、description 等）
   - 标题层级连续（# → ## → ###，不跳级）
   - 代码块语言标识是否正确
   - 内部链接是否存在

3. .py 脚本：
   - 语法合法性（用 py_compile 或 ast.parse 验证）
   - import 是否齐全、路径是否正确
   - 异常处理是否有 swallow（裸 except: pass）
   - 资源句柄是否关闭（with / try-finally）
   - 是否可在干净环境跑通最小用例

4. .sh 脚本：
   - shebang 是否正确（#!/usr/bin/env bash 或 #!/bin/bash）
   - 关键命令路径是否用变量化
   - 是否使用了未在文件中定义的外部命令

5. .json / .yaml：
   - JSON 合法性（json.loads）
   - YAML 缩进一致

【输出格式】（必须严格遵守，使用本格式，否则视为审查失败）
## 审查报告

### 本轮次：N
### 审查结论：PASS | FAIL

### 问题清单（若无问题则写 "无"）
| # | 严重度 | 文件 | 行号 | 问题描述 | 建议修复 |
|---|--------|------|------|----------|----------|
| 1 | P0     | ...  | ...  | ...      | ...      |
| 2 | P1     | ...  | ...  | ...      | ...      |
| 3 | P2     | ...  | ...  | ...      | ...      |

### 严重度定义
- P0：会导致工具失效、阻塞主流程、破坏数据、引入安全风险 — 必须立即修复
- P1：会导致功能异常、文档误导、复用障碍 — 必须修复
- P2：风格问题、轻微不一致、文档措辞 — 仅记录，不阻断 PASS

### 复审指令（仅 N≥2 时填写）
- 对照上一轮问题清单逐项验证：已修复 / 未修复 / 部分修复
- 如有未修复或新问题，列入上方问题清单并保持 FAIL

【行为约束】
- 你只能审查、输出报告，不得修改任何文件。
- 不得跨越本会话上下文执行作者尚未发来的修复。
- 不得自行决定 PASS / FAIL 之外的结论。
```

## 主 agent 调度循环（关键路径）

```pseudo
loop_count = 0
reviewer_id = subagent(prompt=<模板，N=1>, run_in_background=true).id
write_review_round(round=1):
  report = send_message(reviewer_id, message="<本轮上下文>")   # 同步等待本轮
  if report.contains("PASS") and no_P0/P1:
    log("第 1 轮通过"); 终止
  else:
    send fix task back to author (主 agent 自己修，或 send_message 给 write-author subagent)
    loop_count++
    if loop_count >= 3:
      escalate_to_human(report); 终止
    else:
      write_review_round(round=loop_count+1)
```

具体规则：

1. **报告解析**：使用 `job_output(wait=true)` 或 `send_message` 同步等待 reviewer 的回复。必须从回复中抽取 `审查结论` 字段：值为 `PASS` 且无 P0/P1 才算通过。
2. **修复派发**：
   - 若写文件者是主 agent 自己 → 主 agent 立即用 read/edit/write 修复。
   - 若写文件者是某个 write-author subagent → 用 `send_message(write_author_id, "<修复指令 + reviewer 报告原文>")` 把任务派回原作者。
3. **复审触发**：修复完成后，**立即** `send_message(reviewer_id, "请按上一轮报告复审，本次是第 N 轮，对照问题清单逐项验证")`。**不要重新派发 reviewer**。
4. **轮次计数**：维护一个 `review_round` 变量（1→2→3），第 3 轮若仍 FAIL，将最近一份 reviewer 报告原样转发给用户并降级。
5. **降级处理**：第 3 轮失败后输出：
   ```
   ⚠️ 文件审查降级至人工处理
   - 落盘文件：<list>
   - 累计轮次：3
   - 当前剩余 P0/P1 问题：
     <报告原文>
   - 请人工决定：强制通过 / 手动修复 / 回滚
   ```
   然后把决策权交给用户，**不要自动继续**。

## 审查清单（主 agent 在派发 reviewer 前自检）

派发 reviewer 前，主 agent 应先用以下清单做一次轻量自检，能在本地立刻发现的就不要交给 reviewer：

- [ ] 文件实际写入了吗？（write/edit 返回值确认）
- [ ] 是否含绝对用户路径？
- [ ] frontmatter 必填项是否齐全？
- [ ] 代码块是否有 language 标识？
- [ ] Python 是否有明显语法错误？

自检发现问题：直接修复后再派发 reviewer，避免浪费 review 轮次。

## 与其它机制的协同

- **memory_save**：当本 skill 审查的是经验类 md（写入 `~/.dsh-memory/`），复审通过前**不要**对外宣称"经验已沉淀"。审查通过后才允许在主对话中提及"经验已沉淀"。
- **codegraph**：若被审查的是代码且项目根存在 `.codegraph/`，可由 reviewer 在 prompt 中要求其使用 codegraph 做交叉验证。
- **git commit**：未经本 skill 审查通过的文件，不应进入 commit 队列。

## 反例（不应触发本 skill 的场景）

- 主 agent 仅 `read` 了文件，未做任何修改。
- 修改的是机器生成的产物目录（构建产物、依赖缓存、版本控制元数据等）。
- 修改的是本 skill 文件本身。
- 同一文件、同一变更在最近一轮已通过审查（避免无限循环）。

## 交接机制（不写本地文件）

reviewer 输出的结构化报告本身就是主 agent 与原作者之间的**唯一交付物**，不再追加任何本地审计文件。所有信息通过以下三条通道流转，全程在 subagent 会话间传递：

1. **reviewer → 主 agent**：通过 `send_message(reviewer_id, ...)` 同步等待的回复中抽取 `审查结论` 字段（PASS/FAIL）+ 问题清单表格，作为调度依据。
2. **主 agent → 原作者**：把 reviewer 报告**原文**（含问题表）作为 `send_message(write_author_id, ...)` 的内容派回，避免二次加工导致信息失真。
3. **原作者 → reviewer**：主 agent 在 send_message 中明确告诉 reviewer "本次是第 N 轮复审，对照上一轮问题清单逐项验证"，由 reviewer 自己在会话上下文中维护"上一轮报告"——这正是为什么 reviewer 必须是有状态的、不能 fresh-agent。

**不写本地文件的好处**：避免双写不一致；review 状态只在内存会话中流转，关闭会话后自然清理；后续如需审计，再单独设计持久化方案，不耦合在本 skill 内。

## 自动加载约定

当本仓库被作为工作区打开时，DSH 会自动扫描仓库内的 skill 目录并把本 skill 纳入可用列表。不需要把 SKILL.md 复制到全局 skill 目录，也不需要在主对话中手动 `skill` 调用——主 agent 在触发本 skill 的条件命中时，自行按本文件指引执行派发与循环即可。
