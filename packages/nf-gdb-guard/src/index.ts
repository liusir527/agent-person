import type { Context } from '@deepseek-ai/cordis'
import type { PreToolDecision, ToolExecution } from '@deepseek-ai/dsh-tools'

export const name = 'nf-gdb-guard'
export const inject = ['tools']

/**
 * nf-gdb-guard：GDB 危险命令防护插件（dsh 侧替代 gdb-tools/hooks/block-gdb-dangerous）
 *
 * 背景：gdb-tools skill 自带的 block-gdb-dangerous.sh/.bat 是 Claude Code 时代的
 * PreToolUse hook，从 stdin JSON 提取 serial_conn.py --cmd 内容做黑名单。dsh 的
 * 执行通道是 Bash/pwsh 工具（内部经 ssh-tools 的 ssh_batch.py / ssh_shell.py，
 * 或直接 gdb -p <pid> -batch -ex ...），该 hook 完全未接线 —— 存在"agent 在
 * dsh 里发 gdb 危险命令无护栏"的真实缺口。
 *
 * 设计要点（含防误伤）：
 *   - 仅对 Bash / pwsh 工具生效；
 *   - 入口必须是「gdb 作为命令调用」形态（gdb 后跟空格+参数/管道/引号），
 *     目录名 gdb-tools / nf-gdb-guard 等不触发；
 *   - 危险词判定要求词后跟空白/分隔符/行尾（而非 \b），避免 start.bat /
 *     continue.log 这类文件、变量名被误拦；
 *   - 指令块按 `;` 分段逐段判定，防 "x/10gx ; continue" 绕过；
 *   - 命中黑名单 → deny 并给出可读原因。
 */
const SHELL_TOOLS = new Set(['bash', 'pwsh', 'run_code'])

// gdb 作为命令调用形态：gdb 后跟空白（-p/--pid/-batch...）、引号、管道或行尾
const GDB_CALL_RE = /(^|[;&|)\s"'`])(?:[\w./-]*\/)?gdb(?=\s|-|["'`]|&|\||$)/i

// 危险 gdb 词（变更执行/写内存/执行代码）。后置断言：词后必须是空白/分隔符/行尾，
// 防止 start.bat / continue.log / reset 之类文件名、变量名被 \b 误伤
const DANGEROUS_RE =
  /(?:^|[\s;&|,(])(?:c|r|j|k|q|continue|run|start|jump|signal|kill|quit|call|shell|python|make|define|return|commands|set)(?=[\s;&|.,)'"`]|$)/i

// 只读 set 豁免：set pagination/height/width/print/confirm 等纯偏好设置
const SAFE_SET_RE =
  /^set\s+(pagination|height|width|print|confirm|follow|basename|language|scheduler-locking|osabi|architecture|endian|warranty|version|sched-lock)\b/i

// 只读命令词开头（独立子命令放行）
const SAFE_LEAD_RE =
  /^(?:x\/|disassemble|break|watch|info|print|backtrace|bt|list|thread|frame|up|down|where|registers|memory|dump|disable|enable|ignore|condition|attach|detach|logging|help|find|maintenance\s+info|maint\s+info)(?=\s|$)/i

// 单字母白名单（独立成词时才放行）
const SAFE_CHAR_SET = new Set(['p', 'i', 'b', 'f', 'h', 'l'])

function stripInlineGdbPrefix(s: string): string {
  const t = s.replace(/^(?:[\w./-]*\/)?gdb(\s+-[^\s]+)*\s+/, '').trim()
  return t || s
}

function extractGdbBlocks(command: string): string[] {
  const blocks: string[] = []
  // -ex / --eval-command / --command / --cmd / stuff 后引号内容（允许含换行）
  const re = /(?:-ex|--eval-command|--command|--cmd|stuff)\s*(?:=['"]?\s*|['"]?)(['"])([\s\S]*?)\1/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(command)) !== null) {
    const body = m[2] ?? ''
    if (body.trim()) blocks.push(body.trim())
  }
  // 兼容 ssh_batch.py --commands "..." 整段：按 ; 或换行切分，仅保留 gdb 相关分段
  const whole = /--commands\s+(['"])([\s\S]*?)\1/gi
  while ((m = whole.exec(command)) !== null) {
    const seg = (m[2] ?? '').trim()
    if (!seg) continue
    for (const part of seg.split(/[;\n]/)) {
      const t = part.trim()
      if (t && GDB_CALL_RE.test(t)) blocks.push(t)
    }
  }
  return blocks
}

/** 对单个指令块判定：返回命中的危险词或 null */
function isDangerousBlock(block: string): string | null {
  const b = block.trim()
  if (!b) return null
  // 先按 `;` 拆成独立子命令，逐段判定
  for (const seg of b.split(';')) {
    const s = seg.trim()
    if (!s) continue
    // 只读豁免
    if (SAFE_SET_RE.test(s) || SAFE_LEAD_RE.test(s)) continue
    if (s.length === 1 && SAFE_CHAR_SET.has(s)) continue
    // 危险词：满足「词前分隔符 + 词 + 词后分隔符」的完整词才能命中
    const m = s.match(DANGEROUS_RE)
    if (m) {
      // DANGEROUS_RE 允许单词出现在子串（如 "reset" 含 "set"），但前置断言要求
      // 分隔符，因此 "reset" 中 set 前是 'r'（非分隔符）不会误命中；
      // 此处再校验命中的词确实是独立词边界（防 "foocontinue"）
      const word = m[0].replace(/^[\s;&|,(]+/, '').replace(/[\s;&|.,)'"`]+$/, '')
      if (word.length > 0) return word
    }
  }
  return null
}

export function apply(ctx: Context) {
  ctx.on('tools/pre-execute', async (exec: ToolExecution, next: () => Promise<PreToolDecision>): Promise<PreToolDecision> => {
    const toolName = exec.name.toLowerCase()
    if (!SHELL_TOOLS.has(toolName)) return next()

    const args = exec.arguments as Record<string, unknown>
    const command = typeof args?.command === 'string' ? args.command : ''
    if (!command) return next()

    // 入口：必须是 gdb 命令调用 / serial_conn / screen stuff，目录名不触发
    if (!GDB_CALL_RE.test(command) && !/serial_conn|stuff\s+['"]/.test(command)) return next()

    const blocks = extractGdbBlocks(command)
    if (blocks.length === 0) {
      // 整串兜底：仅当命令本身就以 gdb 调用开头（如 `gdb -p 123 -ex ...`）时检查
      const stripped = stripInlineGdbPrefix(command)
      if (stripped !== command) {
        const hit = isDangerousBlock(stripped)
        if (hit) {
          return {
            kind: 'deny',
            reason: `[SECURITY BLOCKED] gdb 危险命令 "${hit}" 被 nf-gdb-guard 拦截：${command}`,
          }
        }
      }
      return next()
    }

    for (const block of blocks) {
      const hit = isDangerousBlock(block)
      if (hit) {
        return {
          kind: 'deny',
          reason: `[SECURITY BLOCKED] gdb 危险命令 "${hit}" 被 nf-gdb-guard 拦截（指令块: ${block}）。允许执行只读命令：x/, disassemble, break, watch, info/i, print/p, backtrace/bt, list, thread, frame, help, find, set pagination/height/width 等。需要变更执行/写内存类操作时请先说明用途，由人工确认。`,
        }
      }
    }
    return next()
  })

  console.log('[nf-gdb-guard] 已注册 gdb 危险命令防护 (tools/pre-execute)')
}