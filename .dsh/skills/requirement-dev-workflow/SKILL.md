# 需求开发工作流（requirement-dev-workflow）

将本 skill 作为需求开发（VPP/npp 层，C 语言）的总调度器。保持当前上下文精简：按阶段加载对应 reference，
必要时调用更窄的 skill 或工具，并在进入下一阶段前记录关键判断。

> **与 bug-fix-workflow 的关系**：本 skill 由 bug-fix-workflow 骨架推导，共享状态机引擎/门禁/对抗评审/
> worktree 隔离/闭环沉淀等机制；差异在于首阶段做「需求澄清」而非「找根因」，且**受限环境测试是人机协作的常态策略**。

## 环境前置检查（开工前必跑，缺一不可）

| 类别 | 资源 | 存在判定 | 缺失时的降级路径 |
|------|------|---------|------------------|
| 状态机引擎 | `requirement_state_machine.py` | `[ -f "$(git rev-parse --show-toplevel)/skills/requirement-dev-workflow/requirement_state_machine.py" ]` | **阻塞**——门禁硬校验是闭环铁律，无脚本则整套流程不可执行 |
| 铁律文档 | `hooks/AGENT.md`（仓库根） | `[ -f hooks/AGENT.md ]` | **阻塞**——需求开发流程铁律（13 条）出自该文档 |
| 阶段 reference | `references/{task-boundary,requirement-intake,environment-setup,design,implementation,code-review,testing}.md` | `[ -d references ] && [ "$(ls references/*.md \| wc -l)" -eq 7 ]` | **阻塞**——每阶段开工前必读对应 reference |
| 兄弟 agent/skill | `design-reviewer`（`.dsh/agents/design-reviewer/design-reviewer.md`）、`code-reviewer`、`memory-gen`、`memory-push` | `[ -f ../../agents/design-reviewer/design-reviewer.md ] && [ -f ../../agents/code-reviewer/code-reviewer.md ]` | 阻断对应阶段：缺 `design-reviewer` → 「方案评审」停摆；缺 `memory-gen`/`memory-push` → 闭环收尾无法沉淀 |
| 可选增强 | `.codegraph/` 索引（仓库根） | `[ -d .codegraph ]` | 自动降级——缺失时回退到本地 grep/glob/Read |

> 路径说明：命令用 `git rev-parse --show-toplevel` 锚定仓库根，跨机/跨仓无需修改。

## 环境配置参数

优先读取 env_config 配置文件（`<workspace_root>/.dsh/env_config/deploy_build/deploy_config.json`（编译机）与
`device_config.json`（设备））；缺省时不猜默认，必要时向用户询问：

编译机参数: [地址] [端口] [用户名] [密码] [ npp仓库地址 ]
测试设备参数: [地址] [端口] [用户名] [密码]

## 阶段路由

0. **开工必读**：先读取 `references/task-boundary.md`（需求边界与防扩散约束），确认本次只改哪个仓库/工作区、
   需求属于哪一层（WEB/AGENT/VPP）、取证与停止条件。**本工作流聚焦 VPP(npp) 层**；配置管理类需求归 AGENT/WEB。
1. 拿到需求单/PRD/口头需求时，读取 `references/requirement-intake.md`（需求理解、范围界定、需求拆解、验收标准）。
2. 进入新仓库、新分支、新产品线或陌生模块时，先读取 `references/environment-setup.md`。
3. 需要派生隔离工作区（git worktree）编码时，读取 `references/environment-setup.md`（git pull → 派生
   `feature-<需求单号>` 分支与工作区 → worktree 内 `codegraph init` → 开放 dirs.json 读写权限）。
4. 需求理解完成、准备设计时，读取 `references/design.md`（需求设计五步法、数据流、边界态、影响评估）。
5. 准备编码前，读取 `references/implementation.md`（编码规范与影响范围评估）。
6. 编码完成后、置 `code_reviewed` 门禁前，读取 `references/code-review.md`（代码审查闭环）。
7. 进入测试验证时，读取 `references/testing.md`（受限环境测试策略、交接项登记）。
8. **闭环收尾必做沉淀**：`交付上线` 阶段必须推进到微观状态「沉淀经验」才可 `close`（状态机门禁强制校验）——
   调用 `memory-gen` 生成经验文档到 `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/` 并更新索引，
   再调用 `memory-push` 推送 git。

## 工具串接规则

- **分层判断优先**：需求归属 WEB/AGENT/VPP 三层。转发/选路/运行态需求先在 VPP 侧确认（vppctl/CLI/show），
  缺字段才考虑 biapi 上报链路；**配置管理类需求属于 AGENT/WEB**，不作为 VPP 需求范围。
- 涉及 `*.api` 改动编译后走 `vpp-api-sync` 暂存 api.json，且上机验证**退化为冒烟验证**（仅 npp 启动 +
  基础命令可用）——这是需求开发的**常态策略**，不是应急手段。
- **受限环境测试是默认策略**：能测的必须测（单测/受限环境运行态/冒烟），不能测的显式列「交接项」
  （责任人+环境+时机）进 `测试记录.md`；配置类验证走**人机协作**（agent 先出 `测试方案.md`，
  用户按方案配置，agent 再检查）——细则见 `references/testing.md`。
- 仓库根目录存在 `.codegraph/` 时，理解架构、定位符号、分析影响面前优先使用 CodeGraph；不存在时使用
  快速本地搜索和常规文件读取。
- 真实设备命令优先使用 SSH、k3s、container 等专用 skill（ssh-tools / gdb-tools）。不要自行拼凑密码处理、
  文件传输或容器进入流程。
- 区分发现、诊断、变更和验证。不要把会改变设备状态的动作藏在只读诊断步骤里。
- **TDD 铁律**：编码实现阶段无失败测试不写生产代码（红-绿-重构），验收标准必须先转成测试用例。
- **完成前校验**：任何"完成/通过"断言必须带当轮运行证据，禁止"应该/大概/似乎"。

## 需求设计五步法（防止浅设计，每条需求必过）

1. **先画数据流再设计**：新字段/新流程同样要写 `谁产生 → 谁消费 → 怎么消费 → 空/边界怎么办`；
2. **参考方案只作线索不作答案**：借鉴旧需求/同模块实现必须验证在当前分支成立；
3. **强制自我证伪**：列出"这个设计在哪些场景不成立"；列不出 = 没想透，不进实施计划；
4. **必须追到边界态**：至少四类——输入为空/超限、状态全失效、来源异常、并发竞争；每个边界态转测试用例；
5. **推进前提**：全门禁一关不能跳。

> 记忆口诀：**验收 ≠ 现象，参考 ≠ 答案，证伪才敢定设计，边界才叫完整，门禁一关不能跳。**

## 必要检查点

执行过程中输出这些检查点记录：
- `上下文`：仓库、代码分支、产品/设备分支、当前假设。
- `证据`：需求单事实、代码路径、运行态信息、已执行命令。
- `假设`：按优先级排列的可能方案，以及每个方案的验证/证伪方式。
- `计划`：最小实施计划、影响范围、回退或安全注意事项。
- `验证`：受限环境自测范围、交接项清单、回归风险。
- `沉淀`：可复用经验、命令模式、代码模式或知识库更新候选。

## 状态机驱动（每条需求单强制）

每条需求单的状态统一由引擎脚本 `requirement_state_machine.py` 管理（铁律见仓库根 `hooks/AGENT.md` 的
「需求开发流程铁律」一节）。状态文件位于 `<项目根>/runtime/req/<需求单号>/`，产物模板在 `templates/`。

主状态机：`需求澄清→需求分析→方案评审→出实施计划→编码实现→测试验证→交付上线→结束`，每个主状态含微观状态机。

**硬性规则：**
- **起步**：拿到需求单先 `init`（`python "$(git rev-parse --show-toplevel)"/skills/requirement-dev-workflow/requirement_state_machine.py init --req-id <单号> --title <摘要> --module <模块>`）。
- **每完成一步**：`micro` / `advance` 推进状态，`record` 累计工时，`review` 登记评审轮次——先 `state` 看当前节点再动作。
- **门禁硬校验**：`advance` 到下一主状态前，脚本强制校验前置产物与 gates；不满足会 exit 2 拒绝。
  **设计方案未经对抗评审（可推演）不得进入实施计划。**
- **小改动也走全门禁**：改动大小不决定要不要审，理解深度才决定；`requirement_confirmed`/`plan_confirmed`/
  `test_passed`/`mr_reviewed`/`merged` 等人工确认门禁只能 `confirm` 置位，`design_reviewed` 只能由对抗评审
  PASS 自动置位，`code_reviewed`/`build_passed` 置位须带 `--evidence <存在文件>`。
- **评审**：需求设计说明书齐 → 调 `design-reviewer` 子 agent 对抗评审（按验收标准可推演/可测试），
  其落盘 `评审结果-rN.md` 并调 `review` 命令记账。FAIL 且轮次<3 回「需求分析」，3 轮 FAIL 转人工接管。
- **断点**：中断后用 `state` / `resolve` 定位当前节点并获取恢复指引。
- **闭环必须沉淀**：实现+受限测试 → 转人工验收 → MR（格式 `feat: NEWNF-XXXXX 【模块】描述`）→ 人工 review
  → 合并/部署 → **沉淀经验**（memory-gen 生成经验文档 + 更新索引，memory-push 推送 git）→ 输出
  `XX需求-REQ-SEQ需求实现说明.md`（放 npp 仓库根）→ `close`。**close 门禁强制校验微观状态已推进到
  「沉淀经验」**，跳过沉淀无法闭环。

## 进度展示（长程任务可观测）

- **progress.md 自动刷新**：状态机每次落盘自动刷新 `<项目根>/runtime/req/<需求单号>/progress.md`
  （人类可读进度卡片）。长任务中用户随时打开该文件即可看到当前阶段。
- **progress 命令**：`python .../requirement_state_machine.py progress --req-id <单号>` 输出可视化进度总览。
- **每次状态变更自动带横幅**：`【进度 x/8 · 主状态 · 微观状态】`。
- **回复必须带阶段横幅**：需求开发任务的每轮回复开头输出一行阶段横幅：
  ```text
  ▸ 阶段：3/8 方案评审 · 判定
  ```
- **用户问"走到哪了"**：先 `progress --req-id <单号>` 刷新总览，再以横幅 + 总览回复。

## 需要反向提问的情况

只有缺失信息会阻塞安全推进时才向用户提问。典型阻塞包括：
- 没有需求单文本，也没有可复现/可验收的目标描述。
- 缺少设备地址、凭据、串口访问方式或一次一密/hash 获取路径，并且不能安全推断。
- 某个真实设备命令可能改变转发行为、重启服务、attach 到时序敏感进程或暴露敏感信息。
- 当前代码分支与运行设备分支不匹配，并且该差异会影响诊断。

## 外部状态变更确认规范（防歧义提问）

**铁律：涉及外部系统状态变更（MR 合并/推送、设备部署/重启、配置下发、工单流转）的选项，必须遵守：**

1. **「谁操作」与「怎么操作」分开问**。第一问只问归属：状态变更由谁执行（选项：A. 您自己执行
   B. AI 代为执行 C. 转他人/测试）。归属明确后再做对应动作，不再把动作方案写成选项。
2. **代为执行选项绝不默认 Recommended**。默认推荐永远是「最小干预」：不主动改动外部状态、由用户/测试人
   自行操作、agent 只记录与置位本地门禁。
3. **执行前回显精确动作**。任何外部写操作执行前，先输出一行「即将执行：`<精确命令/动作>`（影响：…；
   可逆性：…）」并等用户本轮回显确认。
4. **措辞禁用歧义代词**。AI 侧一律写「AI 代为…」，用户侧写「您自行…」。
5. **状态变更可逆性提示**。会产生 changelog/留痕、强推覆盖、重启服务的动作，选项描述必须带「不可逆/可回退=xxx」。
6. **本地门禁 ≠ 外部状态**。`confirm --flag merged` 只登记"合并/部署已被用户/他人在外部完成"这一事实，
   agent 不得自行合并/部署；若要代为执行，必须先走第 2/3 条。

## 安全默认值

- 未明确说明前，将真实设备视为类生产环境。
- 修改状态前优先执行只读命令。
- 涉及 GDB 时，逐条执行命令，并在解引用前验证每个前置指针/地址依赖可访问。
- 对转发相关或时序敏感问题，交互式调试前先判断是否需要锁调度器/线程。
- 代码修改保持与周边风格一致，避免无关重构，始终保持最小改动。
