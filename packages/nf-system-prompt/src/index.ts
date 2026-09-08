import type { Context } from '@deepseek-ai/cordis'

export const name = 'nf-system-prompt'
export const inject = ['systemPrompt']

export function apply(ctx: Context) {
  // ctx.systemPrompt 由 dsh-base 注入；TS 不知道该字段，用 any 旁路编译期类型检查
  const sp = (ctx as any).systemPrompt as { section: (section: { name: string; order: number; text: string }) => void }
  // ── 1. 代码修改前四问（order -40，在 persona 之前） ──────────────
  sp.section({
    name: 'nf-rules-four-questions',
    order: -40,
    text: [
      '## 落盘前四问（修改代码必答）',
      '',
      '对命中可读写清单目录内的代码文件执行 Edit/Write 前，必须先完成四问：',
      '',
      '1. **为什么要这么改** —— 答根因：这条改动解决的是什么问题，不是现象描述。',
      '2. **有没有更小的改动方式** —— 是否只动必要行？能否少改文件、少改函数接口？',
      '3. **当前这样改是不是最优** —— 对比 ≥2 个备选方案后说明为何选它。',
      '4. **影响面多大** —— 调用方、依赖方、配置、测试、文档、版本兼容、回滚成本，逐项顺一遍。',
      '',
      '文档、配置(非逻辑段)、注释增删、纯重命名、格式化等非逻辑改动，可短答："最小改动、无影响面"后实施。',
    ].join('\n'),
  })

  // ── 2. BUG 修复流程约束（order -39） ────────────────────────────
  sp.section({
    name: 'nf-bug-fix-rules',
    order: -39,
    text: [
      '## 问题修复约束流程',
      '',
      '当用户输入明确的 NF BUG 单或问题描述时，按以下铁律执行：',
      '',
      '1. **先 init 再动作**：拿到 BUG 单先执行状态机初始化，此后状态一律由脚本驱动，禁止手改 state.json。',
      '2. **审查通过才能编码**：分析结论未经对抗审查（按触发链路复现成功）不得进入编码。',
      '3. **3 轮 FAIL 转人工**：审查最多 3 轮，FAIL 且轮次<3 回"分析"重新取证；第 3 轮 FAIL 自动转人工接管。',
      '4. **闭环必须交结论**：修复+自测+PR+人工 review+关闭工单后，输出结论文档。',
      '',
      '主状态机：分析 → 审查结论 → 出修改方案 → 编码 → 上机验证 → 更新BUG单 → 结束。',
    ].join('\n'),
  })

  // ── 3. NF 调试经验索引（order 50，在 persona 之后） ──────────────
  sp.section({
    name: 'nf-debug-experience',
    order: 50,
    text: [
      '## NF 调试经验速查（v2 知识库 + 工具语义）',
      '',
      '本工作区是 DSH 的独立 harness 运行环境（DSH 直接读/写仓库）。知识库根：',
      '`.dsh-memory/`（v2 设计，git submodule，位于仓库根），内部三级分层：',
      '- `.dsh-memory/knowledge/experiences/refined/` —— 精炼经验（高频验证）',
      '- `.dsh-memory/knowledge/experiences/sparse/` —— 稀疏经验（新经验入口）',
      '- `.dsh-memory/knowledge/experiences/expired/` —— 过期经验',
      '',
      '**路径策略（重要 — 必须遵守）**：',
      '',
      '1. **文档/注释里禁止出现用户机器特定的绝对路径**（如 `E:/数字永生/...`、`REDACTED_WORKSPACE_PATH/...`）。',
      '   这些路径在一台机器上对，换台机器就错。',
      '2. **允许使用相对仓库根的占位符**（如 `<workspace_root>/.dsh-memory/...`），',
      '   或 `$(git rev-parse --show-toplevel)` 锚定的命令。DSH 自己就是该仓库的运行者，',
      '   可直接用 `read` 工具读到。',
      '3. **检索场景必须用 MCP 工具**（路径只能"知道在哪"，不能"找到要找的"）：',
      '',
      '```text',
      'mcp__memory__memory_search  # 关键词检索（支持 tag/severity/project 过滤）',
      'mcp__memory__memory_read    # 按经验 ID 读取完整 Markdown 原文',
      'mcp__memory__memory_save    # 沉淀新经验（含 frontmatter 自动合并去重）',
      '```',
      '',
      '4. **MCP 不可用时降级**：用 `read/write` 工具直接操作 `.dsh-memory/knowledge/experiences/{refined|sparse|expired}/*.md`，',
      '   入口见 `.dsh-memory/README.md`。',
      '',
      '**场景化指引**：',
      '',
      '- 死锁/挂机/现场取证 → `memory_search` query="死锁排查" / "VPP 死锁" → 按 ID 读全文',
      '- 远程挂入 GDB 会话 → 加载 skill gdb-tools（`.dsh/skills/gdb-tools/SKILL.md`）',
      '- 内存泄漏/堆耗尽 → `memory_search` query="堆内存泄漏" / "dlmalloc"',
      '- 改 NPP 模块前/遇 BUG 排障 → `memory_search` query="NPP战例" / "<模块名>" → 按 ID 读 README+战例',
      '  （README 位于 `.dsh-memory/knowledge/experiences/refined/npp-bug/README.md`，含 248 战例汇总入口）',
      '- SSH 登录设备 → 加载 skill ssh-tools（`.dsh/skills/ssh-tools/SKILL.md`）',
      '- NF 防火墙配置 → 加载 skill nf-config-procedures（`.dsh/skills/nf-config-procedures/SKILL.md`）',
      '',
      '**沉淀新经验**：完成任务后用 `mcp__memory__memory_save`（含 frontmatter，必填',
      '`id/tags/severity/category/occurrence/status/created_at/updated_at`，',
      '正文含 `## 适用场景` + `## 核心流程 / 知识点`）；',
      '模板见 `.dsh-memory/EXPERIENCE-FORMAT.md` 与 `.dsh-memory/knowledge/experiences/` 示例。',
    ].join('\n'),
  })

  console.log('[nf-system-prompt] 已注入 System Prompt 规则: 四问/修复流程/调试经验')
}