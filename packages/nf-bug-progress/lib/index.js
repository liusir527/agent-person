/**
 * @nsfocus/nf-bug-progress — 宿主半体（Node 进程内运行）。
 *
 * 读取工作区 bug-fix-state 目录下各 BUG 的 state.json 与 progress.md，
 * 通过 /api/nf-bug-progress/* 提供给浏览器半体（client.js）轮询渲染。
 *
 * 状态机 schema 与 .dsh/skills/bug-fix-workflow/state_machine.py 保持一致，
 * 这里静态复制一份，避免浏览器半体再去 import 后端模块。
 */
import { readdirSync, readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'

export const name = 'nf-bug-progress'
export const inject = []

/* ------------------------------------------------------------------ *
 * 状态机 schema（与 state_machine.py 对齐）
 * ------------------------------------------------------------------ */
const MAIN_STATES = ['分析', '审查结论', '出修改方案', '编码', '上机验证', '更新BUG单', '结束']
const MICRO_STATES = {
  '分析': ['取证', '假设', '验证', '结论'],
  '审查结论': ['审查', '复现', '判定', '轮次记账'],
  '出修改方案': ['方案草拟', '影响评估', '方案评审', '用户确认'],
  '编码': ['修改', '代码审查', '编译通过', '修复审查问题'],
  '上机验证': ['自测记录', '基础测试', '转人工验证', '人工验证通过'],
  '更新BUG单': ['生成PR描述', '提交PR', '人工review PR', '关闭工单'],
  '结束': [],
}
const GATES = [
  'analysis_reviewed', 'plan_confirmed', 'worktree_ready', 'code_reviewed', 'build_passed',
  'selftest_done', 'basic_test_done', 'manual_verify_handed', 'manual_verify_passed',
  'pr_reviewed', 'jira_closed',
]
const MAX_REVIEW_ROUNDS = 3

/* ------------------------------------------------------------------ *
 * 工作区定位：web 进程 cwd 一般为工作区根（E:\agent_assets），
 * 但也向上逐级探测，找到包含 bug-fix-state 的目录。
 * ------------------------------------------------------------------ */
function findWorkspace() {
  let dir = process.cwd()
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(dir, 'bug-fix-state'))) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

function stateBase() {
  return join(findWorkspace(), 'bug-fix-state')
}

function readState(bugId) {
  const file = join(stateBase(), bugId, 'state.json')
  if (!existsSync(file)) return undefined
  try {
    return JSON.parse(readFileSync(file, 'utf8'))
  } catch {
    return undefined
  }
}

/** 汇总列表：按 updated_at 倒序，供前端一次拉取渲染全部候选。 */
function listSummary() {
  const base = stateBase()
  const items = []
  if (existsSync(base)) {
    for (const entry of readdirSync(base, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue
      const state = readState(entry.name)
      if (state === undefined) continue
      const gates = state.gates ?? {}
      items.push({
        bugId: entry.name,
        title: typeof state.title === 'string' ? state.title : '',
        module: typeof state.module === 'string' ? state.module : '',
        main: typeof state.main_state === 'string' ? state.main_state : '分析',
        micro: typeof state.micro_state === 'string' ? state.micro_state : '',
        updatedAt: typeof state.updated_at === 'string' ? state.updated_at : '',
        reviewRound: typeof state.review_round === 'number' ? state.review_round : 0,
        humanTakeover: state.human_takeover === true,
        escalated: state.escalated === true,
        gatesPassed: GATES.filter((g) => gates[g] === true),
        gatesPending: GATES.filter((g) => gates[g] !== true),
        active: state.main_state !== '结束',
      })
    }
  }
  items.sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
  return items
}

/* ------------------------------------------------------------------ *
 * HTTP 工具（同 dsh-codegraph 的模式：loopback-only）
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
      path: '/api/nf-bug-progress/list',
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
          writeJson(res, 200, {
            ok: true,
            workspace: findWorkspace(),
            schema: { mainStates: MAIN_STATES, microStates: MICRO_STATES, gates: GATES, maxReviewRounds: MAX_REVIEW_ROUNDS },
            items: listSummary(),
          })
        } catch (error) {
          writeJson(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) })
        }
      },
    },
    {
      kind: 'exact',
      path: '/api/nf-bug-progress/state',
      handler: async (req, res) => {
        if (!isLoopbackRequest(req)) {
          writeJson(res, 403, { ok: false, error: 'forbidden: loopback-only' })
          return
        }
        if (req.method !== 'GET') {
          writeJson(res, 405, { ok: false, error: 'method not allowed' })
          return
        }
        const bugId = new URL(req.url ?? '/', 'http://localhost').searchParams.get('bug')?.trim() ?? ''
        if (bugId === '') {
          writeJson(res, 400, { ok: false, error: '缺少 bug 参数' })
          return
        }
        const state = readState(bugId)
        if (state === undefined) {
          writeJson(res, 404, { ok: false, error: 'bug 状态不存在: ' + bugId })
          return
        }
        let progressMd = ''
        try {
          progressMd = readFileSync(join(stateBase(), bugId, 'progress.md'), 'utf8')
        } catch {
          /* progress.md 缺失不阻塞 */
        }
        writeJson(res, 200, { ok: true, bugId, state, progressMd })
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
    }, 'nf-bug-progress: routes')
  })
  console.log('[nf-bug-progress] mounted, workspace=' + findWorkspace())
}
