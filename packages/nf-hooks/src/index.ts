import type { Context } from '@deepseek-ai/cordis'
import type { PreToolDecision, ToolExecution } from '@deepseek-ai/dsh-tools'
import * as path from 'node:path'
import * as fs from 'node:fs'
import * as os from 'node:os'

export const name = 'nf-hooks'
export const inject = ['tools']

// 文件工具列表（带明确 file_path/path，可可靠校验）
const FILE_TOOLS = new Set(['read', 'write', 'edit', 'glob', 'grep'])
// shell 工具列表：从 command 参数提取盘符路径做门控，堵住 read/write/edit 的旁路
const SHELL_TOOLS = new Set(['pwsh', 'bash', 'sh', 'cmd', 'powershell'])

// ---------------------------------------------------------------------------
// SKILL.md frontmatter 硬校验（判据与 .dsh/tools/skill_lint.py 的 DSH 加载器硬前提对齐：
// frontmatter 缺失 / 解析失败（含全角冒号裸行陷阱）/ 缺 name·description / name 非法。
// 只校验 SKILL.md 文本自身，不依赖目录状态（references 等由创建完成后的 skill_lint 全量把关）。
// 命中任一条即等于 DSH 加载器会静默忽略该 skill，因此直接 deny 写入。
// ---------------------------------------------------------------------------
export function validateSkillFrontmatter(text: string): string[] {
  const errors: string[] = []
  const lines = text.split(/\r?\n/)
  if (lines.length === 0 || lines[0].trimEnd() !== '---') {
    errors.push('缺少 YAML frontmatter：首行必须为 ---（DSH 加载器将静默忽略本 skill）')
    return errors
  }
  // 找 frontmatter 结束标记（前 100 行内）
  let fmEnd = -1
  for (let i = 1; i < Math.min(lines.length, 100); i++) {
    if (lines[i].trimEnd() === '---') {
      fmEnd = i
      break
    }
  }
  if (fmEnd < 0) {
    errors.push('frontmatter 未闭合：缺少结束标记 ---')
    return errors
  }

  const fields = new Map<string, string>()
  let curKey: string | null = null
  const fmLines = lines.slice(1, fmEnd)
  for (const raw of fmLines) {
    const ln = raw
    if (!ln.trim() || ln.trimStart().startsWith('#')) continue
    if (/^[ \t]/.test(ln) || /^[-*]/.test(ln.trimStart())) {
      // continuation：缩进行 / 列表项并入上一个 value（与 YAML folding 对齐）
      if (curKey) fields.set(curKey, (fields.get(curKey) ?? '') + ' ' + ln.trim())
      continue
    }
    const m = /^([^:]+):\s*(.*)$/.exec(ln)
    if (!m) {
      errors.push(
        `frontmatter 存在无法解析的行: ${ln.slice(0, 40)}（应为 'key: value' 形式；注意中文全角冒号 '：' 会让整行变成裸文本，导致 YAML 解析失败、DSH 忽略本 skill）`,
      )
      continue
    }
    const key = m[1].trim()
    const val = m[2].trim()
    if (curKey === key) {
      fields.set(key, (fields.get(key) ?? '') + ' ' + val)
    } else {
      fields.set(key, val)
      curKey = key
    }
  }

  const name = fields.get('name') ?? ''
  const description = fields.get('description') ?? ''
  if (!name) {
    errors.push('frontmatter 缺少必填字段: name')
  } else if (!/^[a-z0-9-]+$/.test(name)) {
    errors.push(`frontmatter name 不合法: ${name}（仅允许小写字母/数字/连字符）`)
  }
  if (!description) {
    errors.push('frontmatter 缺少必填字段: description（触发词应写入 description 内，不要另起一行裸文本）')
  }
  return errors
}

// 命中 .dsh/skills/<skill-name>/SKILL.md 的 write/edit：预演目标内容并做 frontmatter 硬校验
function skillFrontmatterErrors(workspaceRoot: string, exec: { arguments: Record<string, unknown> }): { skillDir: string; errors: string[] } | null {
  const filePath = (exec.arguments?.file_path ?? exec.arguments?.path) as string | undefined
  if (!filePath || typeof filePath !== 'string') return null
  const resolved = path.resolve(workspaceRoot, filePath)
  const rel = path.relative(workspaceRoot, resolved)
  const seg = rel.split(path.sep)
  // 必须恰为 .dsh/skills/<name>/SKILL.md（不拦截 references/ 等其他文件）
  if (seg.length !== 4 || seg[0] !== '.dsh' || seg[1] !== 'skills' || seg[3] !== 'SKILL.md' || !seg[2]) {
    return null
  }

  let nextText: string
  if (exec.arguments?.content !== undefined) {
    // write：全量覆盖
    nextText = String(exec.arguments.content)
  } else if (typeof exec.arguments?.old_string === 'string' && typeof exec.arguments?.new_string === 'string') {
    // edit：读现有文件 + 应用替换，预演终态
    let current = ''
    try {
      current = fs.readFileSync(resolved, 'utf-8')
    } catch {
      /* 文件尚不存在：以空文本为基底 */
    }
    const oldStr = exec.arguments.old_string
    const newStr = exec.arguments.new_string
    if (exec.arguments.replace_all === true) {
      nextText = current.split(oldStr).join(newStr)
    } else {
      // 与 edit 工具语义对齐：仅当唯一出现才替换；出现多次时工具自身会拒绝，预演按单次替换
      nextText = current.replace(oldStr, newStr)
    }
  } else {
    return null
  }

  return { skillDir: seg[2], errors: validateSkillFrontmatter(nextText) }
}

export function apply(ctx: Context) {
  // 工作区根 = 启动进程的 cwd（目录迁移后即仓库根，如 E:\agent_assets），统一规范化路径分隔符
  const workspaceRoot = path.resolve(process.cwd())
  const dirsJsonPath = path.resolve(workspaceRoot, '.dsh', 'rules', 'dirs.json')

  // 系统必需放行目录：DSH 框架/依赖（node_modules）与系统临时目录，
  // 避免误伤正常使用框架文档/临时文件的合法操作
  const systemAllowed = [
    path.resolve(os.tmpdir()),          // C:\Users\<user>\AppData\Local\Temp
    path.resolve(os.tmpdir(), '..'),    // AppData\Local（dsh-spill 等）
  ]

  // 动态读取 dirs.json 配置（每次检查时重读，避免缓存失效）
  // restricted 模式：放行范围 = workspace 根内全部内容 + dirs.json 登记的外部目录
  // open 模式：全部放行
  // 返回 null 表示 open（全放行），否则返回外部追加目录列表
  function loadExternalDirs(): string[] | null {
    const dirs: string[] = []
    try {
      if (fs.existsSync(dirsJsonPath)) {
        const data = JSON.parse(fs.readFileSync(dirsJsonPath, 'utf-8'))
        if (data.mode !== 'restricted') {
          return null
        }
        if (Array.isArray(data.dirs)) {
          for (const entry of data.dirs) {
            const dir = typeof entry === 'string' ? entry : entry.path
            if (dir) dirs.push(dir)
          }
        }
      }
    } catch (e) {
      console.error(`[nf-hooks] dirs.json 解析失败: ${e}`)
    }
    return dirs
  }

  // 判断路径是否在放行集内
  function isPathAllowed(filePath: string): boolean {
    const resolved = path.resolve(workspaceRoot, filePath)
    // 工作区根目录本身及其下所有内容始终放行（restricted 的边界 = 工作区根）
    if (resolved === workspaceRoot || resolved.startsWith(workspaceRoot + path.sep)) return true

    // 系统必需目录放行（Temp / node_modules 依赖）
    if (systemAllowed.some((allowed) => resolved.startsWith(allowed + path.sep) || resolved === allowed)) return true
    if (resolved.includes(`${path.sep}node_modules${path.sep}`)) return true

    const externalDirs = loadExternalDirs()
    // null 表示 open 模式，全放行
    if (externalDirs === null) return true

    // 追加放行 dirs.json 登记的外部绝对目录（如 F:/software/...）
    return externalDirs.some((dir) => {
      const allowedPath = path.resolve(workspaceRoot, dir)
      return resolved.startsWith(allowedPath + path.sep) || resolved === allowedPath
    })
  }

  // 从 shell 命令字符串提取所有盘符绝对路径（引号内完整保留，URL 协议段排除）
  function extractWindowsPaths(command: string): string[] {
    const found: string[] = []
    let m: RegExpExecArray | null

    // 1) 引号内的盘符路径：允许含空格，完整取到闭合引号
    const quotedRe = /["']([A-Za-z]:[\\/][^"']*)["']/g
    while ((m = quotedRe.exec(command)) !== null) {
      const p = m[1].replace(/[),.;]+$/, '')
      if (p.length > 3) found.push(p)
    }

    // 2) 引号外（含被替换的引号串）的无空格盘符路径；
    //    lookbehind 排除 URL 协议段（https://x 中 s://x 前有字母数字）
    const withoutQuoted = command.replace(/["'][^"']*["']/g, ' ')
    const bareRe = /(?<![A-Za-z0-9])([A-Za-z]:[\\/][^\s"'`;|&<>(){}[\]!$*?]*)/g
    while ((m = bareRe.exec(withoutQuoted)) !== null) {
      const p = m[1].replace(/[),.;]+$/, '')
      if (p.length > 3) found.push(p)
    }

    return [...new Set(found)]
  }

  // 注册 tools/pre-execute 拦截器（与 DSH hooks-claude-code 插件同模式）
  ctx.on('tools/pre-execute', async (exec: ToolExecution, next: () => Promise<PreToolDecision>): Promise<PreToolDecision> => {
    const toolName = exec.name.toLowerCase()
    const args = exec.arguments as Record<string, unknown>

    // 文件工具：校验 file_path / path 参数
    if (FILE_TOOLS.has(toolName)) {
      const filePath = (args?.file_path ?? args?.path) as string | undefined
      if (!filePath || typeof filePath !== 'string') {
        return next()
      }
      if (!isPathAllowed(filePath)) {
        return {
          kind: 'deny',
          reason: `路径 "${filePath}" 不在可访问范围内。`,
        }
      }
      // SKILL.md 写入格式门禁（用户可选软/硬：硬校验 —— 命中即拒，防 skill 被 DSH 静默忽略）
      if (toolName === 'write' || toolName === 'edit') {
        const skillHit = skillFrontmatterErrors(workspaceRoot, { arguments: args })
        if (skillHit !== null && skillHit.errors.length > 0) {
          console.log(`[nf-hooks] deny skill 写入（${skillHit.skillDir}/SKILL.md）：${skillHit.errors.length} 个格式问题`)
          return {
            kind: 'deny',
            reason:
              `SKILL.md 格式校验未通过（若不修复，DSH 加载器将静默忽略此 skill），共 ${skillHit.errors.length} 个问题：\n` +
              skillHit.errors.map((e) => `- ${e}`).join('\n') +
              `\n修复后重试。完整规约校验请运行：python .dsh/tools/skill_lint.py --path .dsh/skills/${skillHit.skillDir}`,
          }
        }
      }
      return next()
    }

    // shell 工具：提取命令中的盘符路径逐条校验，堵住 read/write/edit 的旁路
    if (SHELL_TOOLS.has(toolName)) {
      const command = args?.command as string | undefined
      if (!command || typeof command !== 'string') {
        return next()
      }
      const paths = extractWindowsPaths(command)
      for (const p of paths) {
        if (!isPathAllowed(p)) {
          return {
            kind: 'deny',
            reason: `命令引用了未放行路径 "${p}"，不在可访问范围内。如需读取/修改该路径，请先登记到 .dsh/rules/dirs.json。`,
          }
        }
      }
      return next()
    }

    return next()
  })

  console.log(`[nf-hooks] 已注册访问门控(restricted 模式, cwd=${process.cwd()}, dirsJson=${dirsJsonPath})`)
}