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