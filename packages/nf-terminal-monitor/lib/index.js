/**
 * @nsfocus/nf-terminal-monitor — 宿主半体（Node 进程内运行）。
 *
 * 读取工作区 runtime/terminal-monitor/ops.jsonl（由 ssh-tools / deploy-build
 * 埋点写入的终端命令审计日志），通过 /api/nf-terminal-monitor/* 提供给
 * 浏览器半体（client.js）轮询渲染，在 DSH Web GUI 中实时展示 agent 在
 * 编译机 / NF 设备上执行的命令。
 *
 * API:
 *   GET /api/nf-terminal-monitor/list?limit=50&target=all&host=10.66.23.115&owner=session-xxx&errors=1
 *       → { ok, workspace, logPath, total, items: [...] }  最新在前
 *   GET /api/nf-terminal-monitor/summary
 *       → { ok, workspace, logPath, total, targets: {...}, hosts: {...}, owners: {...}, currentSession, latestTs }
 *   POST /api/nf-terminal-monitor/clear
 *       → 清空 ops.jsonl（手动清空，loopback-only）→ { ok: true, cleared: n }
 */
import { existsSync, readFileSync, statSync, writeFileSync, truncateSync } from 'node:fs'
import { join, dirname } from 'node:path'

export const name = 'nf-terminal-monitor'
export const inject = []

/* ------------------------------------------------------------------ *
 * 工作区定位：web 进程 cwd 一般为工作区根（E:\agent_assets），
 * 但也向上逐级探测，找到含 .dsh 目录的目录。
 * ------------------------------------------------------------------ */
function findWorkspace() {
  let dir = process.cwd()
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, '.dsh'))) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

function logPath() {
  return join(findWorkspace(), 'runtime', 'terminal-monitor', 'ops.jsonl')
}

/** 读取审计日志，返回记录数组（新→旧）。文件缺失/损坏时返回空数组，绝不抛错。 */
function readRecords(limit) {
  const path = logPath()
  if (!existsSync(path)) return []
  let text
  try {
    text = readFileSync(path, 'utf8')
  } catch {
    return []
  }
  const lines = text.split('\n').filter((l) => l.trim() !== '')
  // 从尾部取最近 limit 条（limit<=0 表示全量）
  const slice = limit > 0 ? lines.slice(-limit) : lines
  const records = []
  for (let i = slice.length - 1; i >= 0; i--) {
    try {
      records.push(JSON.parse(slice[i]))
    } catch {
      /* 行损坏（写入中断）跳过 */
    }
  }
  return records
}

/* ------------------------------------------------------------------ *
 * HTTP 工具（同 nf-bug-progress / dsh-codegraph 的模式：loopback-only）
 * ------------------------------------------------------------------ */
function isLoopbackRequest(request) {
  const address = request.socket?.remoteAddress
  if (address !== '127.0.0.1' && address !== '::1' && address !== '::ffff:127.0.0.1') return false
  const host = request.headers.host
  if (typeof host !== 'string') return false
  let hostUrl
  try {
    hostUrl = new URL('http://' + host)
  } catch {
    return false
  }
  if (hostUrl.hostname !== '127.0.0.1' && hostUrl.hostname !== 'localhost' && hostUrl.hostname !== '[::1]') return false
  return true
}

function writeJson(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'referrer-policy': 'no-referrer' })
  res.end(JSON.stringify(body))
}

function makeRoutes() {
  return [
    {
      kind: 'exact',
      path: '/api/nf-terminal-monitor/list',
      handler: async (req, res) => {
        if (!isLoopbackRequest(req)) {
          writeJson(res, 403, { ok: false, error: 'forbidden: loopback-only' })
          return
        }
        if (req.method !== 'GET') {
          writeJson(res, 405, { ok: false, error: 'method not allowed' })
          return
        }
        try {
          const url = new URL(req.url ?? '/', 'http://localhost')
          const limit = Math.min(Math.max(parseInt(url.searchParams.get('limit') ?? '50', 10) || 50, 1), 500)
          const target = (url.searchParams.get('target') ?? 'all').trim()
          const host = (url.searchParams.get('host') ?? '').trim()
          const owner = (url.searchParams.get('owner') ?? '').trim()
          const onlyErrors = url.searchParams.get('errors') === '1'

          let items = readRecords(limit * 4) // 预取多一些，便于过滤后仍够展示
          if (target && target !== 'all') {
            items = items.filter((r) => String(r.target ?? 'unknown') === target)
          }
          if (host) {
            items = items.filter((r) => String(r.host ?? '') === host)
          }
          if (owner) {
            items = items.filter((r) => String(r.owner ?? '') === owner)
          }
          if (onlyErrors) {
            items = items.filter((r) => {
              const exit = r.result?.exit
              return exit !== undefined && (exit !== 0 || r.result?.timed_out === true || r.result?.error)
            })
          }
          items = items.slice(0, limit)

          writeJson(res, 200, {
            ok: true,
            workspace: findWorkspace(),
            logPath: logPath(),
            total: items.length,
            items,
          })
        } catch (error) {
          writeJson(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) })
        }
      },
    },
    {
      kind: 'exact',
      path: '/api/nf-terminal-monitor/summary',
      handler: async (req, res) => {
        if (!isLoopbackRequest(req)) {
          writeJson(res, 403, { ok: false, error: 'forbidden: loopback-only' })
          return
        }
        if (req.method !== 'GET') {
          writeJson(res, 405, { ok: false, error: 'method not allowed' })
          return
        }
        try {
          const records = readRecords(0) // 全量用于统计
          const targets = {}
          const hosts = {}
          const owners = {}
          let latestTs = ''
          let latestOwner = ''
          for (const r of records) {
            const t = String(r.target ?? 'unknown')
            targets[t] = (targets[t] ?? 0) + 1
            const h = String(r.host ?? '?')
            hosts[h] = (hosts[h] ?? 0) + 1
            const o = String(r.owner ?? 'unknown')
            owners[o] = (owners[o] ?? 0) + 1
            if (String(r.ts ?? '') > latestTs) {
              latestTs = String(r.ts ?? '')
              latestOwner = o
            }
          }
          writeJson(res, 200, {
            ok: true,
            workspace: findWorkspace(),
            logPath: logPath(),
            total: records.length,
            targets,
            hosts,
            owners,
            // 宿主进程注入的会话 ID + 最近一条记录的 owner（退化判定"当前会话"）
            currentSession: process.env.DSH_SESSION_ID ?? '',
            latestOwner,
            latestTs,
          })
        } catch (error) {
          writeJson(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) })
        }
      },
    },
    {
      kind: 'exact',
      path: '/api/nf-terminal-monitor/clear',
      handler: async (req, res) => {
        if (!isLoopbackRequest(req)) {
          writeJson(res, 403, { ok: false, error: 'forbidden: loopback-only' })
          return
        }
        if (req.method !== 'POST') {
          writeJson(res, 405, { ok: false, error: 'method not allowed' })
          return
        }
        try {
          const path = logPath()
          const before = existsSync(path) ? readRecords(0).length : 0
          // 清空审计日志：截断文件。目录不存在时无需动作。
          if (existsSync(path)) {
            truncateSync(path, 0)
          }
          writeJson(res, 200, { ok: true, cleared: before, logPath: path })
        } catch (error) {
          writeJson(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) })
        }
      },
    },
  ]
}

/* ------------------------------------------------------------------ *
 * 插件本体
 * ------------------------------------------------------------------ */
export function apply(ctx) {
  ctx.inject(['webServer'], (webCtx) => {
    webCtx.effect(() => {
      const server = webCtx.webServer
      const disposers = makeRoutes().map((route) => server.register(route))
      return () => {
        for (const dispose of disposers) {
          try {
            dispose()
          } catch {
            /* 释放失败不阻塞 */
          }
        }
      }
    }, 'nf-terminal-monitor: routes')
  })
  const ws = findWorkspace()
  const lp = logPath()
  console.log(`[nf-terminal-monitor] mounted, workspace=${ws}, log=${lp}`)
}