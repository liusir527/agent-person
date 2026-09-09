import type { Context } from '@deepseek-ai/cordis'
import * as path from 'node:path'
import * as fs from 'node:fs'

export const name = 'nf-system-prompt'
export const inject = ['systemPrompt']

// ---------------------------------------------------------------------------
// `.dsh/rules/*.md` 规则文件自动注入
// ---------------------------------------------------------------------------
// 约定：本目录下的规则文件带 YAML frontmatter 即会被自动注入系统提示词，
// 无 frontmatter（如 process-files.md 这种"完整版参考文档"）默认跳过，避免
// 与插件内硬编码的摘要 section 重复。
//
// frontmatter 字段：
//   order   : number 必填。section 排序位（与硬编码 section 同一 order 空间）。
//   name    : string 可选。section 名（仅小写字母/数字/连字符）。缺省用文件名派生。
//   enabled : boolean 可选。false 时跳过本文件。缺省 true。
// 正文 = frontmatter 之后的所有内容，原样注入。
//
// 新增规则 = 往 .dsh/rules/ 丢一个带 frontmatter 的 md 文件，重启 dsh web 生效。

/** 解析规则文件的 frontmatter + 正文。无 frontmatter 返回 null（不注入）。 */
export function parseRuleFile(text: string): { fields: Map<string, string>; body: string } | null {
  const lines = text.split(/\r?\n/)
  if (lines.length === 0 || lines[0].replace(/^\uFEFF/, '').trimEnd() !== '---') return null
  let fmEnd = -1
  for (let i = 1; i < Math.min(lines.length, 100); i++) {
    if (lines[i].trimEnd() === '---') {
      fmEnd = i
      break
    }
  }
  if (fmEnd < 0) return null
  const fields = new Map<string, string>()
  for (const raw of lines.slice(1, fmEnd)) {
    const ln = raw.trim()
    if (!ln || ln.startsWith('#')) continue
    const m = /^([^:]+):\s*(.*)$/.exec(ln)
    if (m) fields.set(m[1].trim(), m[2].trim())
  }
  const body = lines.slice(fmEnd + 1).join('\n').trim()
  return { fields, body }
}

/** 派生安全 section 名：优先 frontmatter name，否则文件名规范化。 */
function deriveSectionName(basename: string, nameRaw: string | undefined): string {
  if (nameRaw && /^[a-z0-9-]+$/.test(nameRaw)) return `nf-rules-file-${nameRaw}`
  const slug = basename.replace(/\.md$/i, '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '') || 'rule'
  return `nf-rules-file-${slug}`
}

/** 扫描 .dsh/rules/*.md，按 frontmatter 注入规则 section。 */
export function injectRuleFiles(ctx: Context): void {
  const sp = (ctx as any).systemPrompt as { section: (section: { name: string; order: number; text: string }) => void }
  const workspaceRoot = path.resolve(process.cwd())
  const rulesDir = path.resolve(workspaceRoot, '.dsh', 'rules')
  let files: string[] = []
  try {
    files = fs.readdirSync(rulesDir).filter((f) => f.toLowerCase().endsWith('.md'))
  } catch {
    console.log(`[nf-system-prompt] .dsh/rules 目录不可读（${rulesDir}），跳过规则文件注入`)
    return
  }
  for (const file of files.sort()) {
    try {
      const full = path.join(rulesDir, file)
      const parsed = parseRuleFile(fs.readFileSync(full, 'utf-8'))
      if (parsed === null) {
        console.log(`[nf-system-prompt] 跳过 ${file}：无 frontmatter（不注入）`)
        continue
      }
      const { fields, body } = parsed
      if (fields.get('enabled')?.toLowerCase() === 'false') {
        console.log(`[nf-system-prompt] 跳过 ${file}：enabled: false`)
        continue
      }
      const orderRaw = fields.get('order')
      if (orderRaw === undefined) {
        console.log(`[nf-system-prompt] 跳过 ${file}：frontmatter 缺 order 字段`)
        continue
      }
      const order = Number(orderRaw)
      if (!Number.isFinite(order)) {
        console.log(`[nf-system-prompt] 跳过 ${file}：order 非有效数值（${orderRaw}）`)
        continue
      }
      if (!body) {
        console.log(`[nf-system-prompt] 跳过 ${file}：正文为空`)
        continue
      }
      const sectionName = deriveSectionName(file, fields.get('name'))
      sp.section({ name: sectionName, order, text: body })
      console.log(`[nf-system-prompt] 已注入规则文件 ${file} → section ${sectionName} (order ${order})`)
    } catch (e) {
      console.warn(`[nf-system-prompt] 注入规则文件 ${file} 失败: ${e}`)
    }
  }
}

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

  // ── 3. 过程文件归属规则（order -38，在 persona 之前） ─────────────
  sp.section({
    name: 'nf-process-files-rule',
    order: -38,
    text: [
      '## 过程文件归属规则',
      '',
      '执行任何会产出过程文件 / 中间产物 / scratch / 缓存 / 临时表格 / 调试 patch 的任务时，必须遵守本规则（踩坑教训固化，完整版见 `.dsh/rules/process-files.md`）：',
      '',
      '**核心规则**：过程文件只能写到 *当前会话所在工作仓库* 的 `runtime/` 子目录下，不得写入任何其他项目的源码树。',
      '',
      '**"当前仓库"的定义**：会话 `workdir` / `pwd` / `git rev-parse --show-toplevel` 解析出的 git 仓库根。DSH 一次会话通常只服务于一个项目；若要在另一仓库做实际改动，当前仓库必须先切到那一个。',
      '',
      '**允许**：中间产物 → `<当前仓库根>/runtime/<子目录>/`（推荐命名 `<task-slug>-<date>/` 或 `<branch-or-bug-id>/`）；最终交付物默认同此，用户另行指定则从其。',
      '',
      '**禁止**：写入非当前仓库的源码树、其他用户工程源码目录（不在当前工作区内的其他项目根）、`$HOME` 顶层与系统根（`C:\\Windows`、`C:\\Program Files`）——除非用户明确授权。',
      '',
      '**跨仓库查询（只读）合法**：可在其他仓库做 `git log` / `git show` 等只读操作，数据带回方式：直接对话输出 / `git -C <other-repo>` 结果写到当前仓库 `runtime/` / 临时中转目录（任务结束清理）。禁止在被查询仓库内落地文件、`git checkout` 或写文件。',
      '',
      '**验证 checklist**（声称任务完成前）：`git status` 在被查询仓库无未跟踪新文件；本次所有新文件位于 `<当前仓库根>/runtime/...`；不在 commit 夹带过程文件。',
      '',
      '调试现场快照 / 日志 / crash dump 放 `<当前仓库根>/runtime/<task-slug>/evidence/`。',
    ].join('\n'),
  })

  // ── 4. NF 调试经验索引（order 50，在 persona 之后） ──────────────
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

  console.log('[nf-system-prompt] 已注入 System Prompt 规则: 四问/修复流程/过程文件归属/调试经验')

  // 目录扫描注入：.dsh/rules/*.md（带 frontmatter 的规则文件）
  injectRuleFiles(ctx)
}