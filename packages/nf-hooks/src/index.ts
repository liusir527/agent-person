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