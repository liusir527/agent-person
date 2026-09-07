# 交接文档 · agent-person skill 系统性审查与修复

> **会话类型**：单次会话协作（非 goal 模式）
> **生成时间**：本次会话末尾
> **承接人**：任何后续接手这个仓库的 agent（含下一次会话的自己）
> **作用**：让接手人 5 分钟内了解"哪些 skill 被改过、改了什么、为什么改、未做完哪些"

---

## 1. 本次会话做了什么

对 `E:\数字永生\agent-person\skills/` 下 16 个 skill 做系统性审查，按 P0/P1/P2 分级列出 **24 项问题**，并按用户"一个个修"的指示依次修复了 6 项（每项独立小改动）。**所有改动均已通过编译/自检/--help 验证**。

### 1.1 已修复的 6 项（按修复顺序）

| # | 修复项 | 严重度 | 改动文件数 | 净增行数 |
|---|---|---|---|---|
| 1 | **P1-1**：`mr-merge.py` + SKILL.md 路径硬编码 | P1 | 2 | +57 |
| 2 | **P0-4**：`.gitignore` 缺 env_config 屏蔽（凭证泄露） | P0 | 1 | +38 |
| 3 | **P0-1 大范围**：8 份 SKILL.md + 3 个脚本的 `REDACTED_WORKSPACE_PATH` | P0 | 11 | ~+150 |
| 4 | **P0-2**：bug-fix-workflow 资源引用 / 插件依赖未验证 | P0 | 1 | +34 |
| 5 | **agent 角色定义规范化**：`agents/code-reviewer/` 重写 | — | 1 | +95 |
| 6 | **AGENTS.md 索引文件**（DSH 自动注入的项目级入口） | — | 1 | +23 |
| 7 | **NPP-BUG 战例库缺口**（analysis-reviewer 引用的错路径） | 中 | 2 | 改 2 行 |

### 1.2 已删除
- `skills/analysis-reviewer/SKILL.md`（已迁移到 `agents/analysis-reviewer/analysis-reviewer.md`，旧路径被废除）

### 1.3 新增文件
- `AGENTS.md`（仓库根，947 字节）
- `agents/analysis-reviewer/analysis-reviewer.md`（4932 字节，从旧 SKILL.md 迁移）
- `agents/code-reviewer/code-reviewer.md`（6119 字节，整文件重写）
- `.dsh/references/handover-2026-session-skill-audit.md`（本文件）

---

## 2. 关键设计决策（接手人必须知道）

### 2.1 路径解析统一约定
**所有"项目根"语义都改成了"以 git 仓库根为基准 + 环境变量可覆盖 + cwd 兜底"**，由 4 个脚本各自内联的 `_resolve_workspace_root()` / `_resolve_project_root()` 实现：

| 脚本 | 环境变量 | 优先级链 |
|---|---|---|
| `mr_merge.py` | `MR_PROJECT_ROOT` | env → git 探测 → cwd + warning |
| `deploy_build.py` | `AGENT_ASSETS_DIR` | 同上 |
| `certificate-apply.py` | `AGENT_ASSETS_DIR` | 同上 |
| `sync_api_json.py` | `AGENT_ASSETS_DIR` | 同上 |

**不再使用 `REDACTED_WORKSPACE_PATH` 这个用户机器特定路径**。SKILL.md 里统一用 `<workspace_root>` 占位符。

### 2.2 DSH 最佳实践路径
- **铁律文档**：`hooks/AGENT.md`（仓库根），不是 `.dsh/hooks/AGENT.md`
- **agent 定义**：`agents/<name>/<name>.md`
- **agent 索引**：`AGENTS.md`（仓库根，DSH 自动注入）
- **环境前置检查**：`bug-fix-workflow/SKILL.md` 顶部新增了 27 行表格 + 自检命令

### 2.3 `.gitignore` 新增 9 类规则
详见 `.gitignore` 第 13–48 行。所有凭证/敏感文件被屏蔽，包括：
- `.dsh/env_config/`、`**/env_config/`
- `**/deploy_config.json`、`**/device_config.json`、`**/.cookies.tmp`
- `.env`、`.env.*`、`**/.env`、`**/*.credentials`、`**/credentials.json`
- `**/id_rsa`、`**/id_rsa.pub`、`**/*.pem`、`**/*.key`
- `deploy.log`、`**/deploy.log`

**自检命令**：`git check-ignore -v <path>`，详见 `.gitignore` 第 50–54 行。

---

## 3. 未做完的项（按风险/价值排序）

接手人如要继续，建议按此顺序：

| 优先级 | 项 | 严重度 | 说明 |
|---|---|---|---|
| 1 | **P1-6** nf-auto-produce 外部状态变更铁律 | 高 | 48 行 SKILL.md，生产设备操作无防误触护栏 |
| 2 | **P1-5** lightrag 内网 URL 硬编码 | 中 | `http://10.66.23.38:18080` 内网 IP |
| 3 | **F:/software/NF605/...** 8 处机器特定路径 | 中 | vpp-api-sync / bug-fix-workflow/references/environment-setup.md 仍在 |
| 4 | **NPP 战例库 README** 第 76-79 行的 `F:/software/...` | 低 | 来源说明，不影响使用 |
| 5 | `bug-fix-workflow/SKILL.md` 5 处 `analysis-reviewer` 引用 | 低 | 路径变了但仍可工作 |
| 6 | `templates/代码审查报告.md` 与 code-reviewer 配套模板 | 低 | 功能已可用，独立化是扩张动作 |
| 7 | `.dsh/references/调试方法论.md` / `.dsh/references/堆内存分析经验.md` / `.dsh/init/experience-index.md` | 中 | system-prompt 插件第 50/52/54 行引用了不存在的文件 |
| 8 | **P1-2** gns-topo 加载清单 | 低 | |
| 9 | **P1-4** file-review 超时 | 低 | |
| 10 | 整体 P2 收尾（测试覆盖、双写哲学、依赖矩阵等） | 低 | |

---

## 4. 验证清单（接手人可重跑）

| 验证项 | 命令 | 预期 |
|---|---|---|
| 4 个脚本 `--help` | `python skills/{deploy-build/deploy_build.py,certificate-apply/certificate-apply.py,vpp-api-sync/sync_api_json.py,mr-merge/mr_merge.py} --help` | 全部 exit 0 |
| state_machine.py | `python skills/bug-fix-workflow/state_machine.py --help` | exit 0 |
| 4 个脚本路径解析 | `python -c "import importlib.util; spec=importlib.util.spec_from_file_location('m', r'<脚本>'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.AGENT_ASSETS_DIR or m.PROJECT_ROOT)"` | 落到 git 根 |
| 环境变量覆盖 | `AGENT_ASSETS_DIR=E:\数字永生\agent-person\packages python ...` | 落到 packages |
| `.gitignore` 屏蔽 | `git check-ignore -v .dsh/env_config/deploy_build/deploy_config.json` | 命中规则 |
| bug-fix-workflow 前置 | 跑 SKILL.md 顶部"统一自检命令"（bash 版） | SM:OK / HOOK:OK / REF:OK (7/7) |
| agents/ 一致性 | `agents/<name>/<name>.md` 路径与 frontmatter `name` 一致 | ✅ |
| AGENTS.md 存在 | `Test-Path AGENTS.md` | True |

---

## 5. 已知陷阱

1. **CRLF → LF 警告**：修改过的多个 .md / .py 文件当前是 CRLF，`.gitattributes` 配了 `text eol=lf`，下次 git 操作会自动转。**功能无影响**，但若手动提交前介意可 `git add --renormalize .`
2. **`F:/software/NF605/...`** 在 `vpp-api-sync`、`bug-fix-workflow/references/environment-setup.md`、`memory-push`（github.com/liusir527）里仍存在 —— 按用户"独立小改动"指示未清，列在第 3 节
3. **`.dsh/` 子模块未展开**：仓库根的 `.dsh/` 是占位目录（`.gitmodules` 指向 `.dsh-memory`，不是 `.dsh`），所以 `.gitignore` 第 21 行精确规则 `.dsh/env_config/` 当前未触发，由第 24 行 `**/env_config/` 兜底
4. **本会话内的 reviewer subagent 不是 fresh-agent**：按 `file-review` SKILL.md 要求，派发后保留 subagent_id 续接；本会话未真正派发（skill 工具不可用），reviewer 任务以本文件 + 下方 reviewer prompt 包形式留给接手人执行

---

## 6. 下次会话建议的第一步

按用户优先级：

1. 完成 **P1-6 nf-auto-produce 外部状态变更铁律**（48 行 SKILL.md 缺 6 节护栏）
2. 完成 **P1-5 lightrag 内网 URL**
3. 跑 reviewer subagent（用下方"5. reviewer prompt 包"）做一次本会话所有改动的完整审查
4. 处理 review 报告里的 P0/P1 问题

---

## 7. 补遗：v2 知识库迁移（session 第 3 阶段）

> 该段在初次交接文档（session 第 1-2 阶段）之后追加。session 末尾追加了第 3 轮审查闭环，**最终 PASS**。

### 7.1 触发点
接手人按"未做完"列表里的 `packages/nf-*-monitor/README.md 残留 REDACTED_WORKSPACE_PATH/packages/...（低）` 与 `.dsh/init/experience-index.md + 2 份 .dsh/references/*.md 缺口（中）` 提示继续修。
接手人核心反馈：**dsh 直接运行在这个工作区**，因此：
- 文档写死路径会让 DSH 跟着错（必须治本）
- 但 v2 知识库的真实位置是 `.dsh-memory/`（已通过 git submodule 引入），DSH 可直接 `read` 到
- MCP `mcp__memory__*` 工具用于"检索"场景（关键词搜索）

### 7.2 设计原则（已固化为 system-prompt 注入）

`packages/nf-system-prompt/src/index.ts` 第 3 节注入的 4 条**路径策略**（DSH 看到的规则）：

1. 文档/注释里**禁止**用户机器特定绝对路径（`E:/数字永生/...`、`REDACTED_WORKSPACE_PATH/...`）
2. **允许**相对仓库根占位符（`<workspace_root>/...`）或 `$(git rev-parse --show-toplevel)` 锚定
3. **检索场景必须用 MCP 工具**（`mcp__memory__memory_search` / `memory_read` / `memory_save`）
4. MCP 不可用时降级：用 `read/write` 工具直接读 `.dsh-memory/knowledge/experiences/{refined,sparse,expired}/*.md`

### 7.3 本轮改动文件（9 个，已 reviewer 第 3 轮 PASS）

修改：
- `packages/nf-system-prompt/src/index.ts` — 第 3 节整段重写（v2 知识库 + 4 条路径策略 + 场景化指引）
- `skills/memory-gen/SKILL.md` — 整文件重写（v2 sparse 层 + MCP 写入优先 + frontmatter 模板）
- `skills/memory-push/SKILL.md` — 整文件重写（v2 sparse/refined 索引 + git add 路径）
- `skills/bug-fix-workflow/SKILL.md` — 第 61 行沉淀路径改 v2
- `skills/bug-fix-workflow/references/reasoning-extraction.md` — 写入路径改 v2
- `skills/bug-fix-workflow/templates/XX问题-BUG-SEQ问题分析.md` — 2 处 v1 路径改 v2
- `hooks/AGENT.md` — 第 53 行沉淀路径改 v2
- `packages/nf-terminal-monitor/README.md` — 第 48 行 `dsh plugin add link` 用 `$(git rev-parse --show-toplevel)`
- `packages/nf-bug-progress/README.md` — 第 26 行同上

### 7.4 reviewer 第 3 轮列出的 5 项 P2（不阻断 PASS，全部留作后续）

| # | 文件 | 行 | 问题 | 严重度 |
|---|---|---|---|---|
| 1 | `skills/memory-push/SKILL.md` | 44 | `.dsh/tools/link_check.py` 不存在 | P2 |
| 2 | `skills/memory-push/SKILL.md` | 38 | `nf-auto-produce 已并入主仓` 描述与现状不符（其实仍在 skills/）| P2 |
| 3 | `skills/memory-push/SKILL.md` | 46 | `.dsh/init/` 目录不存在（与交接文档"未做完项 7"一致）| P2 |
| 4 | `.gitmodules` | 9 | `file:///C:/Users/DELL/.dsh-memory` 机器特定 URL（应改为 SSH/HTTPS 占位）| P2 范围外 |
| 5 | `packages/nf-terminal-monitor/README.md` | 36 | 含 `E:\agent_assets` 文字描述（prompt 明确范围外）| P2 范围外 |

### 7.5 更新后的"未做完"列表（与原列表合并）

按风险/价值排序：

| 优先级 | 项 | 严重度 | 说明 |
|---|---|---|---|
| 1 | **P1-6** nf-auto-produce 外部状态变更铁律 | 高 | 48 行 SKILL.md 缺 6 节护栏 |
| 2 | **P1-5** lightrag 内网 URL | 中 | `http://10.66.23.38:18080` 内网 IP |
| 3 | **3rd/atlassian/update_config.py** 6 处 `REDACTED_WORKSPACE_PATH` | 中 | cordis patch 生成器，整脚本需改成模板渲染 |
| 4 | `packages/nf-*-monitor/lib/index.js`、`packages/nf-hooks/src/index.ts`、`packages/nf-brand/README.md` 残留 `E:\agent_assets` | 中 | 跨 5 个文件 |
| 5 | `.gitmodules` URL 含 `C:/Users/DELL/.dsh-memory` | 低 | 应改为 SSH/HTTPS 占位 |
| 6 | `skills/memory-push/SKILL.md` 行 38/44/46 的 3 项 P2 | 低 | 与 v1 路径假设残留 |
| 7 | `bug-fix-workflow/SKILL.md` 5 处 `analysis-reviewer` 引用 | 低 | 路径变了但仍可工作 |
| 8 | `templates/代码审查报告.md` 与 code-reviewer 配套模板 | 低 | 功能已可用 |
| 9 | `F:/software/NF605/...` 8 处机器特定路径（按之前指示保留）| 低 | |
| 10 | `github.com/liusir527/agent_assets.git` 远端 URL（按之前指示保留）| 低 | |
| 11 | 整体 P2 收尾（测试覆盖、双写哲学、依赖矩阵等）| 低 | |

---

## 5. reviewer prompt 包（接手人直接复制执行）

接手人按以下步骤派发 file-reviewer subagent：

### 5.1 派发命令

```python
subagent_fork(
  description="file-review for skill audit session",
  prompt=<下方模板整段>,
  run_in_background=True
)
```

### 5.2 reviewer prompt 模板

```text
你是「文件落盘审查 reviewer」。你的职责是：对主 agent 在本次"agent-person skill 审查与修复"会话中
刚刚修改的所有文件进行结构化审查，并对作者回传的修复结果进行复审。全程保持同一会话，不丢失上下文。

【本次审查范围】（共 21 个修改文件 + 4 个新增文件 = 25 个文件）

新增文件（4）：
- AGENTS.md (947 字节，仓库根)
- agents/analysis-reviewer/analysis-reviewer.md (4932 字节)
- agents/code-reviewer/code-reviewer.md (6119 字节)
- .dsh/references/handover-2026-session-skill-audit.md (本交接文档)

修改文件（21）：
- .gitignore (11 → 54 行)
- skills/mr-merge/mr_merge.py (硬编码路径 → _resolve_project_root())
- skills/mr-merge/SKILL.md (路径锚定段重写)
- skills/deploy-build/deploy_build.py (硬编码 → _resolve_workspace_root())
- skills/deploy-build/SKILL.md (3 处路径改写)
- skills/certificate-apply/certificate-apply.py (同上模式)
- skills/certificate-apply/SKILL.md (2 处路径改写)
- skills/vpp-api-sync/sync_api_json.py (同上模式)
- skills/vpp-api-sync/SKILL.md (2 处路径改写)
- skills/memory-gen/SKILL.md (11 处路径改写)
- skills/memory-push/SKILL.md (4 处路径改写 + cd 命令改写)
- skills/ssh-tools/SKILL.md (2 处路径改写)
- skills/bug-fix-workflow/SKILL.md (环境前置检查 27 行 + 3 处错路径修复 + 1 处 P0-1 顺手)
- skills/bug-fix-workflow/references/device-debugging.md (1 处路径改写)
- packages/nf-system-prompt/src/index.ts (NPP-BUG 战例库路径修复)

删除文件（1）：
- skills/analysis-reviewer/SKILL.md (94 行，已迁移到 agents/)

完整修改清单见 .dsh/references/handover-2026-session-skill-audit.md 第 1.1 节。

【审查重点】（按文件类型差异化）

1. 通用：
   - 路径硬编码：禁止出现 REDACTED_WORKSPACE_PATH / E:\数字永生（除非在注释中说明"用户机器示例"）
   - 编码：UTF-8，无 BOM；中文文档需保留中文
   - 前后端字段匹配：文档中提及的字段名、参数名与代码实际定义一致
   - 是否引入新硬编码：原审计发现的"REDACTED_WORKSPACE_PATH / E:\agent_assets / github.com/liusir527 / F:/software/"等

2. .md 文档：
   - frontmatter 必填字段是否齐全（name、description 等）
   - 标题层级连续（# → ## → ###，不跳级）
   - 代码块语言标识是否正确
   - 内部链接是否存在
   - agents/<name>/<name>.md 的 frontmatter `name` 与目录名/文件名是否一致

3. .py 脚本：
   - 语法合法性（py_compile）
   - 4 个 _resolve_*() 函数实现是否一致（mr_merge 用 MR_PROJECT_ROOT，其他用 AGENT_ASSETS_DIR）
   - 异常处理是否有 swallow（裸 except: pass）
   - 资源句柄是否关闭（with / try-finally）
   - 是否可在干净环境跑通最小用例（--help）

4. .ts 脚本（packages/nf-system-prompt/src/index.ts）：
   - TypeScript 语法合法性
   - ctx.systemPrompt.section() 调用是否正确
   - 引用路径是否真实存在

【输出格式】（必须严格遵守）

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
- 你只能审查、输出报告，不得修改任何文件
- 不得跨越本会话上下文执行作者尚未发来的修复
- 不得自行决定 PASS / FAIL 之外的结论
- 关键验证动作：跑 py_compile 与 --help 是你的责任，不是主 agent 的责任
```

### 5.3 主 agent 调度循环

```text
loop_count = 0
reviewer_id = subagent_fork(prompt=<上方模板>, run_in_background=True).id
write_review_round(round=1):
  report = send_message(reviewer_id, message="请按上方 prompt 开始审查").result
  if report.contains("PASS") and no_P0/P1:
    log("第 1 轮通过"); 终止
  else:
    send fix task back to author (主 agent 自己修)
    loop_count++
    if loop_count >= 3:
      escalate_to_human(report); 终止
    else:
      write_review_round(round=loop_count+1)
```

### 5.4 降级处理（第 3 轮失败后输出）

```
⚠️ 文件审查降级至人工处理
- 落盘文件：见本交接文档第 1.1 节
- 累计轮次：3
- 当前剩余 P0/P1 问题：
  <报告原文>
- 请人工决定：强制通过 / 手动修复 / 回滚
```
