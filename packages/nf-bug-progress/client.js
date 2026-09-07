/* eslint-disable */
/**
 * @nsfocus/nf-bug-progress — 浏览器半体：对话页动态 BUG 修复进度条。
 *
 * 首选挂载点：官方插槽 `conversation.input.dock`（输入框上方整行，GoalBar/
 * TodoDock 同座位）——用一个极薄的 React 壳组件输出 `[data-nfbp-dock-slot]`
 * 容器，实际内容由纯 DOM 进度条填充（对 props 契约零依赖）。
 * 若 dock 未出现（非会话页 / 注册失败），退回右下角浮动面板。
 *
 * 数据：每 4s 轮询 /api/nf-bug-progress/list，展示最新「进行中 BUG」的
 * 主状态流水线 + 微观状态 + 门禁；阶段切换时头部闪一下。
 *
 * 失败策略：任何挂载/请求失败只 console.error，绝不让 Web shell 启动失败。
 */
window.__ModuleLoader__.load({
  id: '@nsfocus/nf-bug-progress',
  factory: (require) => {
    const exports = {}

    const React = require('react')

    /* ================================ CSS ================================ */
    const CSS = [
      '.nfbp_strip{font-family:var(--dsw-font-family,ui-sans-serif,system-ui,sans-serif);box-sizing:border-box;border:1px solid var(--dsw-alias-border-l2,#333);border-radius:10px;background:var(--dsw-alias-bg-layer-3,rgba(28,28,30,.97));color:var(--dsw-alias-label-primary,#e6e6e6);overflow:hidden;font-size:12.5px}',
      '.nfbp_strip *{box-sizing:border-box}',
      '.nfbp_float{position:fixed;right:16px;bottom:16px;width:330px;max-width:calc(100vw - 32px);z-index:2147483000;box-shadow:0 8px 28px rgba(0,0,0,.3)}',
      '.nfbp_strip:not(.nfbp_float){box-sizing:border-box;width:calc(100% - var(--dsh-composer-side-clearance) - var(--dsh-composer-side-clearance) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset));max-width:calc(var(--dsh-composer-card-max-width) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset) - var(--dsh-composer-dock-inset));margin:0 auto;flex:none}',
      '.nfbp_head{appearance:none;width:100%;display:flex;align-items:center;gap:8px;padding:8px 12px;background:transparent;border:0;color:inherit;font:inherit;cursor:pointer;text-align:left}',
      '.nfbp_head:focus-visible{outline:2px solid var(--dsw-alias-brand-primary,#4f8cff);outline-offset:-2px}',
      '.nfbp_badge{flex:none}',
      '.nfbp_text{flex:1;min-width:0;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.nfbp_meta{flex:none;font-size:10.5px;color:var(--dsw-alias-label-secondary,#999);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:nowrap}',
      '.nfbp_chevron{flex:none;color:var(--dsw-alias-label-tertiary,#777);transition:transform .16s}',
      '.nfbp_open .nfbp_chevron{transform:rotate(180deg)}',
      '.nfbp_body{display:none;padding:4px 12px 10px;border-top:1px solid var(--dsw-alias-border-l1,#2a2a2c)}',
      '.nfbp_open .nfbp_body{display:block}',
      '.nfbp_row{display:flex;align-items:center;gap:6px;padding:2.5px 0;font-size:12px}',
      '.nfbp_mark{flex:none;width:14px;text-align:center;color:var(--dsw-alias-label-tertiary,#777)}',
      '.nfbp_ok .nfbp_mark{color:var(--dsw-alias-state-success-primary,#4caf50)}',
      '.nfbp_cur .nfbp_name{color:var(--dsw-alias-brand-primary,#4f8cff);font-weight:600}',
      '.nfbp_cur .nfbp_mark{color:var(--dsw-alias-brand-primary,#4f8cff)}',
      '.nfbp_name{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.nfbp_micro{flex:none;font-size:10px;color:var(--dsw-alias-label-tertiary,#777);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}',
      '.nfbp_bar{height:4px;border-radius:2px;background:var(--dsw-alias-border-l1,#2a2a2c);overflow:hidden;margin:8px 0 2px}',
      '.nfbp_barfill{height:100%;background:var(--dsw-alias-brand-primary,#4f8cff);border-radius:2px;transition:width .3s}',
      '.nfbp_foot{font-size:10.5px;color:var(--dsw-alias-label-tertiary,#777);margin-top:6px;line-height:1.5}',
      '.nfbp_chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}',
      '.nfbp_chip{font-size:10.5px;padding:1px 6px;border-radius:6px;background:var(--dsw-alias-bg-layer-2,#1f1f21);border:1px solid var(--dsw-alias-border-l1,#2a2a2c);color:var(--dsw-alias-label-secondary,#999)}',
      '.nfbp_chip.nfbp_chipActive{border-color:var(--dsw-alias-brand-primary,#4f8cff);color:var(--dsw-alias-label-primary,#e6e6e6)}',
      '.nfbp_empty{padding:8px 12px 10px;font-size:12px;color:var(--dsw-alias-label-tertiary,#777)}',
      '.nfbp_error{color:var(--dsw-alias-state-error-primary,#f66);font-size:11px;padding:6px 12px 10px}',
      '.nfbp_flash{animation:nfbpFlash .8s ease}',
      '@keyframes nfbpFlash{0%{background:rgba(79,140,255,.28)}100%{background:transparent}}',
    ].join('\n')

    let styleEl
    function ensureStyle() {
      if (document.getElementById('nf-bug-progress-style')) return
      styleEl = document.createElement('style')
      styleEl.id = 'nf-bug-progress-style'
      styleEl.textContent = CSS
      document.head.appendChild(styleEl)
    }

    function esc(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;')
    }

    /* ================================ API ================================ */
    async function api(path) {
      const response = await fetch(path, { cache: 'no-store' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status))
      return data
    }

    /* ================================ 进度条 DOM ================================ */
    function createStrip() {
      const root = document.createElement('div')
      root.className = 'nfbp_strip'
      root.setAttribute('data-nfbp-strip', '')
      root.setAttribute('data-dsh-plugin', 'nf-bug-progress')
      root.innerHTML =
        '<button type="button" class="nfbp_head" aria-expanded="false">' +
        '<span class="nfbp_badge">🛠</span>' +
        '<span class="nfbp_text">BUG 进度 …</span>' +
        '<span class="nfbp_meta"></span>' +
        '<svg class="nfbp_chevron" width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3 5l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
        '</button>' +
        '<div class="nfbp_body"><div class="nfbp_empty">加载中…</div></div>'
      const head = root.querySelector('.nfbp_head')
      head.addEventListener('click', () => {
        const open = root.classList.toggle('nfbp_open')
        head.setAttribute('aria-expanded', String(open))
      })

      const textEl = root.querySelector('.nfbp_text')
      const metaEl = root.querySelector('.nfbp_meta')
      const bodyEl = root.querySelector('.nfbp_body')

      function buildPipeline(schema, item) {
        const mainStates = schema.mainStates || []
        const microStates = schema.microStates || {}
        const cur = mainStates.indexOf(item.main)
        const rows = []
        for (let i = 0; i < mainStates.length; i++) {
          const s = mainStates[i]
          const mark = i < cur ? '✓' : (i === cur ? '▶' : '○')
          const cls = i < cur ? 'nfbp_ok' : (i === cur ? 'nfbp_cur' : '')
          let microText = ''
          if (i === cur) {
            const micros = microStates[s] || []
            if (micros.length > 0) {
              const mi = micros.indexOf(item.micro)
              const curIdx = mi >= 0 ? mi : 0
              microText = micros.map((m, j) => (j < curIdx ? '✓' : (j === curIdx ? '▶' : '·')) + m).join(' ')
            }
          }
          rows.push('<div class="nfbp_row ' + cls + '"><span class="nfbp_mark">' + mark + '</span>' +
            '<span class="nfbp_name">' + esc(s) + '</span>' +
            (microText ? '<span class="nfbp_micro">' + esc(microText) + '</span>' : '') + '</div>')
        }
        return rows.join('')
      }

      function update(data, flash) {
        const items = Array.isArray(data.items) ? data.items : []
        const active = items.filter((it) => it.active)
        const item = active[0] || items[0] || null
        const schema = data.schema || {}

        if (item === null) {
          textEl.textContent = 'BUG 进度 · 无进行中'
          metaEl.textContent = ''
          bodyEl.innerHTML = '<div class="nfbp_empty">暂无进行中的 BUG 修复（bug-fix-state 下无活动状态机）。</div>'
          return
        }
        const mainStates = schema.mainStates || []
        const idx = mainStates.indexOf(item.main) + 1
        const total = mainStates.length || 7
        const stage = item.micro ? (item.main + ' · ' + item.micro) : item.main
        textEl.textContent = item.bugId + ' · ' + idx + '/' + total + ' ' + stage
        const gatesTotal = (schema.gates || []).length
        const passed = item.gatesPassed.length
        metaEl.textContent = '门禁 ' + passed + '/' + gatesTotal +
          ' · 轮次 ' + item.reviewRound + '/' + (schema.maxReviewRounds || 3) +
          ' · ' + String(item.updatedAt || '').slice(5, 16)

        const pct = gatesTotal > 0 ? Math.round((passed / gatesTotal) * 100) : 0
        const human = item.humanTakeover ? ' ⚠已转人工接管' : ''
        const chips = active.slice(0, 6).map((it) =>
          '<span class="nfbp_chip' + (it.bugId === item.bugId ? ' nfbp_chipActive' : '') + '">' + esc(it.bugId) + ' ' + esc(it.main) + '</span>').join('')
        bodyEl.innerHTML =
          buildPipeline(schema, item) +
          '<div class="nfbp_bar"><div class="nfbp_barfill" style="width:' + pct + '%"></div></div>' +
          '<div class="nfbp_foot">门禁 ' + passed + '/' + gatesTotal + ' 已通过 · 审查轮次 ' + item.reviewRound + '/' + (schema.maxReviewRounds || 3) + human + '</div>' +
          (chips ? '<div class="nfbp_chips">' + chips + '</div>' : '')

        if (flash) {
          root.classList.remove('nfbp_flash')
          void root.offsetWidth
          root.classList.add('nfbp_flash')
        }
      }

      function error(message) {
        textEl.textContent = 'BUG 进度 · 读取失败'
        metaEl.textContent = ''
        bodyEl.innerHTML = '<div class="nfbp_error">' + esc(message) + '</div>'
      }

      return { root, update, error }
    }

    /* ================================ 插件入口 ================================ */
    exports.inject = ['slots']

    /** 极薄 React 壳：只输出挂载容器，内容由纯 DOM 进度条填充。 */
    function BugFixDock() {
      return React.createElement('div', { 'data-nfbp-dock-slot': '' })
    }

    exports.apply = (ctx) => {
      ctx.effect(() => {
        ensureStyle()
        const bootTime = performance.now()
        let dockRegistered = false
        try {
          ctx.slots.inject('conversation.input.dock', () => {
            try {
              const unregister = ctx.slots.register({
                name: 'conversation.input.dock',
                id: 'bugfix',
                order: 5,
              }, BugFixDock)
              return () => { try { unregister() } catch { /* 释放失败不阻塞 */ } }
            } catch (error) {
              console.error('[nf-bug-progress] dock register 失败，退回浮动面板：', error)
              return () => {}
            }
          })
          dockRegistered = true
        } catch (error) {
          console.error('[nf-bug-progress] dock 注入失败，退回浮动面板：', error)
        }

        const strip = createStrip()
        let mounted = false
        let timer = null
        let lastKey = ''
        let last = null

        const refresh = async () => {
          try {
            const data = await api('/api/nf-bug-progress/list')
            const items = Array.isArray(data.items) ? data.items : []
            const active = items.filter((it) => it.active)
            const item = active[0] || items[0] || null
            const key = item === null ? 'none' : item.bugId + '|' + item.main + '|' + item.micro + '|' + item.updatedAt
            const flash = last !== null && lastKey !== key
            lastKey = key
            last = data
            strip.update(data, flash)
          } catch (error) {
            strip.error(String(error && error.message ? error.message : error))
          }
        }

        // 优先进 dock 容器；dock 4s 内未出现（非会话页/注册失败）则浮动兜底；
        // 之后 dock 出现时把进度条从浮动位置挪进去。
        const reconcile = () => {
          const dockEl = document.querySelector('[data-nfbp-dock-slot]')
          if (dockEl !== null) {
            if (strip.root.parentElement !== dockEl) {
              if (strip.root.parentElement === document.body) strip.root.classList.remove('nfbp_float')
              dockEl.appendChild(strip.root)
              dockEl.setAttribute('data-nfbp-mounted', '')
            }
            mounted = true
            return
          }
          if (!mounted && (!dockRegistered || performance.now() - bootTime > 4000)) {
            document.body.appendChild(strip.root)
            strip.root.classList.add('nfbp_float')
            mounted = true
          }
        }

        const observer = new MutationObserver(reconcile)
        observer.observe(document.body, { childList: true, subtree: true })
        reconcile()
        timer = window.setInterval(refresh, 4000)
        void refresh()

        return () => {
          window.clearInterval(timer)
          observer.disconnect()
          strip.root.remove()
        }
      }, 'nf-bug-progress: widget')
    }

    return exports
  },
})
