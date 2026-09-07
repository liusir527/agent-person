import type { Context } from '@deepseek-ai/cordis'

export const name = 'nf-system-prompt'
export const inject = ['systemPrompt']

export function apply(ctx: Context) {
  // ── 1. 代码修改前四问（order -40，在 persona 之前） ──────────────
  ctx.systemPrompt.section({
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
  ctx.systemPrompt.section({
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
  ctx.systemPrompt.section({
    name: 'nf-debug-experience',
    order: 50,
    text: [
      '## NF 调试经验速查',
      '',
      '遇到以下问题时，优先加载对应的 skill 或查阅经验库（路径相对工作区根；完整索引见 `.dsh/init/experience-index.md`）：',
      '',
      '- 死锁/挂机/现场取证 → 读 `.dsh/references/调试方法论.md`',
      '- 远程挂入 GDB 会话 → 用 skill gdb-tools（`.dsh/skills/gdb-tools/SKILL.md`）',
      '- 内存泄漏/堆耗尽 → 读 `.dsh/references/堆内存分析经验.md`',
      '- 改 NPP 模块前/遇 BUG 排障 → 查 `.dsh/references/NPP-BUG战例库/README.md`',
      '- SSH 登录设备 → 用 skill ssh-tools（`.dsh/skills/ssh-tools/SKILL.md`）',
      '- NF 防火墙配置 → 用 skill nf-config-procedures（`.dsh/skills/nf-config-procedures/SKILL.md`）',
    ].join('\n'),
  })

  console.log('[nf-system-prompt] 已注入 System Prompt 规则: 四问/修复流程/调试经验')
}