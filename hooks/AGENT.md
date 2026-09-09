# hooks/ · Hook 分区说明

> 本目录存放 PreToolUse 访问门控等 Hook 定义。
> 当前访问门控由 `nf-hooks` 插件（`packages/nf-hooks/`）实现，通过 cordis 事件系统拦截文件工具调用。

## 当前实现

| 功能 | 实现位置 | 说明 |
|------|----------|------|
| 访问门控（restricted 模式） | [../../packages/nf-hooks/src/index.ts](../../packages/nf-hooks/src/index.ts) | 强制文件边界：拦截文件工具（read/write/edit/glob/grep）的 file_path/path，以及 shell 工具（pwsh/bash/sh/cmd/powershell）命令中引用的盘符路径，仅允许放行目录 |

## 数据配置

- 放行目录清单：[../rules/dirs.json](../rules/dirs.json)
- 工作区模式：`restricted`（由 `dirs.json` 中的 `mode` 字段控制）

## 使用原则

- restricted 模式下，文件工具与 shell 命令仅可访问 `dirs.json` 中登记的目录
- shell 命令门控按"盘符绝对路径"静态提取（引号内完整、URL 协议段排除、POSIX 路径不检查）：
  - `git -C F:/software/NF605/npp/606/npp ...` → 命中登记目录，放行
  - `git -C F:/software/NF605/web worktree add ...` → 未登记，拒绝
  - `Get-Content F:\...` / `Invoke-WebRequest -OutFile C:\Users\...\Downloads\...` → 未登记，拒绝
- 需要临时放行路径时，使用 `python .dsh/tools/writable_dirs.py add <相对路径>` 登记
- 新增 Hook 时在本清单追加一行

---

## BUG 修复流程铁律（每次启动自动加载）

> 以下规则适用于所有 NF BUG 修复任务，脚本见 `skills/bug-fix-workflow/state_machine.py`。

### 主状态机（顺序推进，不可跳跃）

```
分析 → 审查结论 → 出修改方案 → 编码 → 上机验证 → 更新BUG单 → 结束
```

### 铁律

1. **先 init 再动作**：拿到 BUG 单后必须先执行 `state_machine.py init --bug-id <ID> --title "..." --module "..."`，后续状态一律由脚本驱动，禁止手改 state.json。

2. **审查通过才能编码**：分析结论未经对抗审查（按触发链路复现成功）不得进入编码阶段。审查最多 3 轮，FAIL 且轮次 < 3 回"分析"重新取证；第 3 轮 FAIL 自动转人工接管。

3. **出修改方案必须经用户确认**：修改方案草拟后必须请用户确认，由确认人执行 `state_machine.py confirm --bug-id <ID> --flag plan_confirmed --by <确认人> [--note]`，用户确认后才能编码。`plan_confirmed` 禁止用 `gate` 命令自行置位（脚本拦截）。

4. **编码前必须门禁检查**：每次编码前先执行 `state_machine.py gate-check --bug-id <ID>`，门禁拒绝（exit 2）时禁止修改文件，先补足前置条件。

5. **每次推进必须 advance**：每个主状态完成后必须执行 `state_machine.py advance --bug-id <ID> --to <下一状态>`，脚本会校验门禁。

6. **编译必须验证**：编码结束时必须编译验证，通过后执行 `state_machine.py gate --bug-id <ID> --flag build_passed --value true --evidence <编译日志路径>`（证据型门禁：无证据文件拒绝置位）。

7. **闭环必须交结论+沉淀经验**：修复+自测+PR+人工 review+关闭工单后，必须先执行经验沉淀（调用 memory-gen 生成经验文档到 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/`（v2 知识库真实位置）并更新索引，再调用 memory-push 推送 git，然后 `state_machine.py micro --bug-id <ID> --to 沉淀经验`），再输出结论文档并执行 `state_machine.py close --bug-id <ID> --conclusion 结论文档.md`。close 门禁强制校验微观状态已推进到「沉淀经验」，未沉淀不得关闭状态机。

8. **进度必须可观测**：状态机每次落盘自动刷新 `bug-fix-state/<单号>/progress.md`（人类可读进度卡片）；每次推进/门禁变化后回复中必须输出当前阶段横幅 `▸ 阶段：x/7 · 主状态 · 微观`，进入新回合或用户询问进度时先 `state_machine.py progress --bug-id <ID>` 展示进度总览。禁止多轮长任务中让用户看不到当前位置。

9. **会话命名动作**：收到含 BUG 单号（`NEWNF-XXXXX` 等）的用户提示词、激活 BUG 单修复流程时，当前会话标题由 `nf-bug-title` 插件自动改为「修复 <单号>」（监听 session/event → 提取单号 → 官方 `SessionTitleService.rename`，user 来源锁定标题）。本动作自动生效，agent 不得声称已改名或自行伪造；会话标题未变化时提示用户重启 `start.bat` 重新加载插件。

### 任务边界铁律（从 NEWNF-54251 教训固化为不可逾越的规则）

> 教训来源：NEWNF-54251 分析阶段，主 agent 连续多轮 SSH 翻读设备 `/opt/nsfocus/product/web` 下 WEB 源码
> （views.py / serializers.py / humansize.py），用 WEB 层逻辑倒推"显示单位"问题——任务边界明明只允许动 npp
> worktree（`task-boundary.md`），却把大量上下文烧在跨层取证上，被用户当场叫停。**边界管的不只是「写」，
> 更管「取证动作本身」：SSH 上去翻别的层的源码，等于已经在干别的仓库的活。**

1. **取证动作与修改动作同边界**：任何 SSH/文件读取，目标是 WEB（`/opt/nsfocus/product/web`）、AGENT
   （`/opt/nsfocus/product/agent`）、system-manage 等非 npp 层源码时，**即使只读、即使为了"理解需求"，也一律禁止**，
   属扩散。需要跨层理解时，先停手，向用户说明理由并等用户指示，不自行展开。
2. **显示/统计类问题从 VPP 运行态取证**：先 vppctl / show 命令 / npp 输出文件（`/tmp/portraffic`、
   `/var/run/interface` 等），缺数据再在 npp 源码内找产生方。**不从 WEB 源码倒推显示逻辑。**
3. **探索必带停判句**：每个取证/探索动作后必须输出"结论：X；若此结论为假，方案是否受影响"，
   写不出这句 = 在漫游，立即停止该方向。
4. **违规即回退**：一旦发现自己读/写了本层之外的源码或仓库，立即停止该方向，向用户说明并回退，
   不得"顺便看一眼"继续扩散；重复违规直接标记为流程事故，转用户接管。

### 分析前置流程铁律（从 NEWNF-54251 教训固化）

> 教训来源：同一 BUG 中，主 agent 跳过 environment-setup.md 流程——worktree 损坏后不修复，直接用
> `git show origin/master:...` / `git grep` 绕道读代码，导致分析无调用链/影响面支撑（还出现 `* 8`
> 搜出大量 `u8` 噪音），且分析上下文与修改上下文（worktree）脱节。被用户连续两次点名后才补建环境。

1. **先建环境，后分析，顺序不可颠倒**：拿到 BUG 单 → 读 `skills/bug-fix-workflow/references/environment-setup.md`
   → 派生/修复 `fix-<BUG单号>` worktree（基线 master，`worktree add -B fix-<ID> <path> origin/master`）→
   worktree 内 `codegraph init` → **之后**才允许做符号定位/调用链/影响面分析。
2. **禁止绕道读代码**：worktree 异常时先修复（`worktree unlock` → `remove --force` → 重新 `add -B`），
   不得用 `git show <branch>:<path>` / `git grep <branch>` 等 git 对象快照方式替代 worktree 内分析；
   绕道即失去 codegraph 支撑，视为违规。
3. **分析优先走 CodeGraph**：仓库有 `.codegraph/` 时，符号定位/调用链/影响面一律
   `codegraph explore/node/callers/callees/impact`，文本 grep 仅作补充；索引缺失先 `codegraph sync`。

### 违规后果

- 跳过门禁直接编码 → 视为流程违规，需回退到上一状态重新执行
- 手改 state.json → 状态机失效，需要 reset 重新开始
- 跨层取证（SSH/读取非本层源码）→ 视为扩散违规，回退到任务边界重新分析，并在响应中向用户致歉说明

---

## 运行时产物纪律（所有 skill / 脚本 / 子 agent 必读，2025-11-27 立）

> 教训来源：本次新建 `analysis-only-workflow` skill 时，状态目录最初锚定在 `<项目根>/analysis-state/<slug>/`，落地后才发现与现有 `runtime/<SESS>/` 约定（vpp-api-sync / ssh-tools / gdb-tools 等）冲突，不得不返工重定位到 `runtime/analysis/<slug>/`。同类新 skill / 新脚本还会撞同样的坑——必须把纪律提到全局铁律层。

### 铁律（适用于所有产线 skill / Python 脚本 / 子 agent 派发输出）

1. **运行时临时数据必须落到 `<项目根>/runtime/<分类>/<SESS>/` 下**。禁止落到 workspace 根或仓库其他位置。常见分类：
   - `runtime/analysis/<slug>/` —— 无 bug 单的简化分析闭环（analysis-only-workflow）
   - `runtime/<SESS>/<模块>.api.json` —— vpp-api-sync 暂存
   - `runtime/terminal-monitor/` —— ssh-tools 命令流水
   - 其他分类由 skill 自定义但必须以 `runtime/` 起头
2. **状态机/脚本内的 `DEFAULT_STATE_DIR`、`OUTPUT_DIR`、`out_dir` 等常量默认值必须指向 `runtime/` 子目录**；不允许默认写到 `analysis-state/` / `bug-fix-state/` / `feature-state/` / 其他仓库根平铺目录。
3. **`init` / 脚本启动时若状态目录在 workspace 外**（自定义 `--dir`），禁止自动 `mkdir -p` 到 workspace 根；只在指定目录创建。
4. **`.dsh/rules/dirs.json` 必须包含 `runtime` 登记**（路径写 `.\runtime`），否则 restricted 模式下脚本初始化会被 nf-hooks 拦截。这是 L2 硬门禁生效的前置条件。
5. **跨脚本/跨 skill 复用同一 `<SESS>/`** 时，由该 skill 的状态机统一调度，避免同一 SESS 多脚本各自建子目录。

### 反例（避免重蹈覆辙）

- ❌ `<项目根>/analysis-state/<slug>/` —— 与 runtime 约定冲突，污染 workspace 根
- ❌ `<项目根>/bug-fix-state/<BUG单号>/` —— 同上（既有 bug-fix-workflow 历史产物，本次不重定位，留待后续 PR）
- ❌ `<项目根>/feature-state/<需求单号>/` —— 反例（requirement-dev-workflow 已于落地时迁移至 `runtime/req/`，勿再新建）
- ❌ `<项目根>/tmp/<slug>/` —— 同上
- ✅ `<项目根>/runtime/analysis/<slug>/` —— analysis-only-workflow 落地后的合规落点
- ✅ `<项目根>/runtime/<SESS>/<模块>.api.json` —— vpp-api-sync 既有约定
- ✅ `<项目根>/runtime/terminal-monitor/` —— ssh-tools 既有约定

### 与现有 skill 约定对齐速查

| skill | 既有落点 | 状态 |
|---|---|---|
| bug-fix-workflow | `bug-fix-state/<BUG单号>/` | 历史产物，不在本次重定位范围（未来如需迁移到 `runtime/bugfix/<BUG单号>/` 走单独 PR） |
| requirement-dev-workflow | `runtime/req/<需求单号>/` | ✅ 已合规（落地时按纪律迁移） |
| vpp-api-sync | `runtime/<SESS>/<模块>.api.json` | ✅ 已合规 |
| ssh-tools | `runtime/terminal-monitor/` | ✅ 已合规 |
| gdb-tools | `runtime/test_gdb_guard.mjs` | ✅ 已合规 |
| analysis-only-workflow | `runtime/analysis/<slug>/` | ✅ 本次重定位后已合规 |

---

## 需求开发流程铁律（每次启动自动加载）

> 以下规则适用于所有 NF 需求开发任务（聚焦 VPP/npp 层，C 语言），脚本见
> `skills/requirement-dev-workflow/requirement_state_machine.py`。
> 与 BUG 修复流程铁律共享状态机/门禁/对抗评审/worktree 隔离/闭环沉淀骨架；
> 差异：首阶段做「需求澄清」而非「找根因」，受限环境测试是**常态策略**而非应急手段。

### 主状态机（顺序推进，不可跳跃）

```text
需求澄清 → 需求分析 → 方案评审 → 出实施计划 → 编码实现 → 测试验证 → 交付上线 → 结束
```

### 铁律

1. **先 init 再动作**：拿到需求单必须先执行 `requirement_state_machine.py init --req-id <单号> --title "..." --module "..."`，后续状态一律由脚本驱动，禁止手改 state.json。状态目录 `<项目根>/runtime/req/<需求单号>/`（运行时产物纪律）。

2. **验收标准先行**：需求理解说明书必须含可量化/可判定的验收标准，且经需求方确认（`confirm --flag requirement_confirmed`）才能进入需求分析；无验收标准的方案不得进入编码。

3. **评审通过才能编码**：需求设计说明书未经对抗评审（design-reviewer，按验收标准可推演/可测试）不得进入实施计划。评审最多 3 轮，FAIL 且轮次 < 3 回「需求分析」重新调研；第 3 轮 FAIL 自动转人工接管。

4. **用户确认双闸**：需求理解+验收标准（requirement_confirmed）、实施计划（plan_confirmed）两处均须人工 `confirm` 置位，禁止用 `gate` 命令自行置位（脚本拦截）。

5. **编码前必须门禁检查**：每次编码前先执行 `gate-check --req-id <单号>`，门禁拒绝（exit 2）时禁止修改文件，先补足前置条件。

6. **推进必 advance / 编译必验证**：每个主状态完成后必须 `advance --to <下一状态>`；编码结束必须编译验证，`build_passed` 置位须带 `--evidence <编译日志路径>`（证据型门禁）。

7. **代码审查闭环**：编码实现必须走 code-reviewer 审查（复用 `.dsh/agents/code-reviewer/code-reviewer.md`），PASS 落盘 `代码审查报告-rN.md` 后 `gate --flag code_reviewed --evidence <报告>`；FAIL 且轮次<3 回「修改」修正，第 3 轮 FAIL 转人工接管。

8. **受限环境测试（常态策略）**：VPP 层需求测试常无完整联调环境；**能测的必须测**（单测/受限环境运行态/冒烟），**不能测的显式列「交接项」**（责任人+环境+时机）进 `测试记录.md`；禁止用"环境受限"当不测试的借口；`test_passed` 含"可测项全过 + 交接项已登记"。

9. **闭环必须交结论+沉淀经验**：实现+受限测试 → 人工验收 → MR（格式 `feat: NEWNF-XXXXX 【模块】描述`）→ 人工 review → 合并/部署 → 必须先执行经验沉淀（memory-gen 生成经验文档到 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/` 并更新索引，再 memory-push 推送 git，然后 `micro --to 沉淀经验`）→ 输出 `XX需求-REQ-SEQ需求实现说明.md`（放 npp 仓库根）→ `close`。close 门禁强制校验微观状态已推进到「沉淀经验」。

10. **进度必须可观测**：状态机每次落盘自动刷新 `runtime/req/<需求单号>/progress.md`；每次推进/门禁变化后回复中必须输出当前阶段横幅 `▸ 阶段：x/8 · 主状态 · 微观`，进入新回合或用户询问进度时先 `progress --req-id <单号>` 展示进度总览。

11. **TDD 铁律**：编码实现阶段，无失败测试不写生产代码；每个新增函数/行为先写失败测试（红）→ 最小实现（绿）→ 重构；验收标准必须先转成测试用例才有判据。

12. **完成前校验**：任何"完成/通过"断言必须带当轮运行证据（命令输出/退出码/测试结果），禁止"应该/大概/似乎"或先满意后校验。

13. **外部状态变更确认**：合并/部署/上线 一律先问"谁操作"（您自行 / AI 代为 / 转他人），代为执行绝不默认 Recommended，执行前回显精确动作；`confirm --flag merged` 只登记事实，不代操作。

### 需求开发任务边界（从 bug-fix 教训固化）

1. **配置管理类需求归属 AGENT/WEB**，不作为 VPP 需求范围；VPP 只作配置消费方（biapi 接收）或数据产生方（biapi 上报）。
2. **取证动作与修改动作同边界**：SSH/文件读取目标是 WEB/AGENT/system-manage 等非 npp 层源码时，即使只读也一律禁止，属扩散；需要跨层理解时先停手问用户。
3. **显示/统计类问题从 VPP 运行态取证**：先 vppctl / show 命令 / npp 输出文件，缺数据再在 npp 源码内找产生方。
4. **探索必带停判句**：每个取证/探索动作后必须输出"结论：X；若此结论为假，方案是否受影响"，写不出这句 = 在漫游，立即停止。
5. **违规即回退**：一旦读/写本层之外的源码或仓库，立即停止并向用户说明回退，重复违规标记为流程事故转用户接管。

### 违规后果

- 跳过门禁直接编码 → 视为流程违规，需回退到上一状态重新执行
- 手改 state.json → 状态机失效，需要 reset 重新开始
- 跨层取证（SSH/读取非本层源码）→ 视为扩散违规，回退到任务边界重新分析，并在响应中向用户致歉说明
- 未登记交接项即置位 test_passed → 门禁无效，回退「测试验证」补登记

## Skill 创建/编辑强制校验铁律（每次启动自动加载，2026-09-09 立）

> 背景：`.dsh/skills/requirement-dev-workflow`（SKILL.md 缺 frontmatter）、`gns-topo` / `nf-auto-produce`
> （frontmatter 内全角冒号裸行）均被 DSH 加载器静默忽略，skill 长期不出现且无人察觉。
> 文档规约不足以防漏（SKILL_AUTHORING.md 早已写明 frontmatter 必填），故立硬校验铁律。

1. **新建或编辑 `.dsh/skills/` 下任何 skill 后，必须运行校验**：
   `python .dsh/tools/skill_lint.py --path .dsh/skills/<skill-name>`（单目录）
   或 `python .dsh/tools/skill_lint.py`（全量）。exit 0 = 无 ERROR；exit 1 = 存在 ERROR。
2. **校验不过（exit 1）= 任务未完成**：禁止交付、禁止提交、禁止声称"已完成"、禁止进入下一阶段；
   必须修复全部 ERROR 后复跑至 exit 0。WARN 允许放行但需知晓。
3. **frontmatter 是 DSH 加载器的硬性前提**：SKILL.md 首行必须为 `---`，且必含 `name` 与 `description`
   两个字段；`name` 仅允许小写字母/数字/连字符；正文引用 `references/`、`templates/` 的文件必须真实存在。
4. **全角冒号陷阱（真实事故）**：frontmatter 内键值分隔必须是半角冒号 `:`。`触发条件：xxx` 这类全角冒号行
   会被 YAML 解析器当作裸文本，导致整个 frontmatter 解析失败、skill 被静默忽略（gns-topo / nf-auto-produce）。
   触发词应写入 `description` 字段内部，而不是另起一行裸文本。
5. **新增 skill 先查本铁律与 SKILL_AUTHORING.md 8.5 节再落盘**；发现存量 skill 校验不过，先修存量再谈新增。
6. **写入级硬拦截（nf-hooks 插件自动执行，无需手动触发）**：对 `.dsh/skills/<name>/SKILL.md` 的 write/edit，
   在写入前由 `packages/nf-hooks` 自动校验 frontmatter 硬前提（首行 `---` / `name`·`description` 必填 /
   `name` 合法 / 无全角冒号裸行），不过即拒绝写入并回显原因。这是最后一道自动化防线；
   **「创建完跑全量 skill_lint」仍必须**——两者层次不同：插件防「必然不加载」的硬伤，
   全量 lint 防其余规约问题（references 缺失、章节建议等）。插件逻辑改动后需重启 DSH 生效（lib 编译产物）。