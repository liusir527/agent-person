/* eslint-disable */
/**
 * @nsfocus/nf-terminal-monitor — 浏览器半体：终端命令监控（模态对话框布局）。
 *
 * 挂载点：官方插槽 `sidebar.footer.action`（侧栏底部、设置按钮上方）——
 * 入口按钮采用与会话管理（dsh-session-manager）一致的简洁 footer 按钮
 * （图标 + 文字 + 计数徽标；rail 折叠态仅图标），点击后弹出**居中模态对话框**：
 * 半透明 backdrop + 面板（header：标题/条数/关闭；body：目标过滤按钮组、
 * 会话 owner chips、命令列表；footer：清空按钮）。Esc / 点击 backdrop /
 * 关闭按钮均可关闭；危险操作（清空）走二次确认对话框（红色确认按钮），
 * 不再使用 window.confirm。内容仍由纯 DOM 填充，轮询保持 3s。
 *
 * 失败策略：任何挂载/请求失败只 console.error，绝不让 Web shell 启动失败。
 */
window.__ModuleLoader__.load({
  id: '@nsfocus/nf-terminal-monitor',
  factory: (require) => {
    const exports = {}
    const React = require('react')

    /* React portal：把模态层渲染到 body，逃脱侧栏 overflow 裁剪 */
    let createPortal = null
    try {
      const RD = require('react-dom')
      if (RD && typeof RD.createPortal === 'function') createPortal = RD.createPortal
    } catch (_) { /* react-dom 不可用时降级为内联渲染（fixed 定位仍可显示） */ }
    let portalHost = null
    function ensurePortalHost() {
      if (portalHost === null) {
        portalHost = document.createElement('div')
        portalHost.setAttribute('data-nftm-portal-host', '')
        portalHost.style.cssText = 'position:fixed;inset:0;z-index:9999;pointer-events:none'
        document.body.appendChild(portalHost)
      }
      return portalHost
    }

    /* ================================ CSS ================================ */
    const CSS = [
      /* --- 入口按钮（仿会话管理 footer 按钮） --- */
      '.nftm_action{box-sizing:border-box;display:flex;flex-direction:column;gap:2px;padding:2px 8px 4px}',
      '.nftm_actionBtn{box-sizing:border-box;min-height:28px;color:var(--dsw-alias-label-tertiary,#555);cursor:pointer;background:0 0;border:0;border-radius:6px;align-items:center;gap:6px;padding:3px 8px;font-size:12px;line-height:18px;display:inline-flex;font-family:inherit;text-decoration:none;white-space:nowrap}',
      '.nftm_actionBtn:hover,.nftm_actionBtn[data-active]{color:var(--dsw-alias-label-secondary,#333);background:var(--dsw-alias-interactive-bg-hover,#eee)}',
      '.nftm_actionIcon{flex:none;display:inline-flex;justify-content:center;align-items:center;font-size:14px}',
      '.nftm_actionLabel{flex:none}',
      '.nftm_actionCount{flex:none;margin-left:2px;border-radius:999px;padding:0 6px;font-size:10px;line-height:16px;color:var(--dsw-alias-label-secondary,#555);background:var(--dsw-alias-fill-l2,#eee);font-variant-numeric:tabular-nums}',
      /* rail 折叠态：只留圆形图标按钮（与会话管理一致地保持薄壳） */
      '.nftm_actionRail{padding:2px 8px 2px}',
      '.nftm_actionRail .nftm_actionBtn{width:36px;height:36px;border-radius:50%;justify-content:center;padding:0;gap:0}',
      '.nftm_actionRail .nftm_actionIcon{font-size:16px}',
      /* --- 模态层（仿会话管理 native dialog） --- */
      '.nftm_modalLayer{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;pointer-events:auto}',
      '.nftm_modalBackdrop{position:absolute;inset:0;background:rgba(0,0,0,.45)}',
      '.nftm_modal{position:relative;box-sizing:border-box;width:640px;max-width:calc(100vw - 32px);max-height:80vh;display:flex;flex-direction:column;overflow:hidden;background:var(--dsw-alias-surface-l1,#fff);color:var(--dsw-alias-label-primary,#111);border:1px solid var(--dsw-alias-border-l2,#ddd);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.25)}',
      '.nftm_modal:focus{outline:none}',
      /* --- 面板本体（撑满模态层） --- */
      '.nftm_panel{font-family:var(--dsw-font-family,ui-sans-serif,system-ui,sans-serif);box-sizing:border-box;width:100%;min-width:0;display:flex;flex-direction:column;min-height:0;flex:1 1 auto;color:var(--dsw-alias-label-primary,#111);font-size:12px}',
      '.nftm_panel *{box-sizing:border-box}',
      '.nftm_modalHead{display:flex;align-items:center;gap:8px;padding:10px 16px;border-bottom:1px solid var(--dsw-alias-border-l2,#eee);flex:none}',
      '.nftm_badge{flex:none;font-size:14px}',
      '.nftm_title{flex:1;min-width:0;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:14px;line-height:20px}',
      '.nftm_meta{flex:none;font-size:10.5px;color:var(--dsw-alias-label-secondary,#555);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:nowrap}',
      '.nftm_close{flex:none;min-height:26px;padding:2px 9px;border:1px solid var(--dsw-alias-border-l2,#ddd);border-radius:7px;background:transparent;color:var(--dsw-alias-label-secondary,#555);cursor:pointer;font-size:12px;line-height:18px;font-family:inherit}',
      '.nftm_close:hover:not(:disabled){background:var(--dsw-alias-interactive-bg-hover,#eee);color:var(--dsw-alias-label-primary,#111)}',
      '.nftm_filters{display:flex;gap:6px;padding:10px 12px 4px;flex-wrap:wrap;flex:none}',
      '.nftm_fbtn{font-size:12px;padding:3px 12px;border-radius:999px;border:1px solid var(--dsw-alias-border-l2,#ddd);background:transparent;color:var(--dsw-alias-label-secondary,#555);cursor:pointer;font-family:inherit;line-height:18px}',
      '.nftm_fbtn:hover{background:var(--dsw-alias-interactive-bg-hover,#eee)}',
      '.nftm_fbtn.on{color:var(--dsw-alias-label-primary,#111);background:var(--dsw-alias-fill-l2,#f5f5f5);border-color:transparent}',
      '.nftm_fbtn.ow{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}',
      '.nftm_body{flex:1 1 auto;min-height:0;max-height:min(48vh,380px);overflow-y:auto;border-top:1px solid var(--dsw-alias-border-l1,#eee);margin-top:6px}',
      '.nftm_item{display:flex;gap:8px;padding:6px 12px;border-bottom:1px solid var(--dsw-alias-border-l1,#f0f0f0);align-items:flex-start}',
      '.nftm_item:last-child{border-bottom:0}',
      '.nftm_item:hover{background:var(--dsw-alias-interactive-bg-hover,#f5f5f5)}',
      '.nftm_tag{flex:none;margin-top:1px;font-size:10px;padding:1px 6px;border-radius:6px;white-space:nowrap;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}',
      '.nftm_tag.nf{background:rgba(244,67,54,.10);color:#c62828;border:1px solid rgba(244,67,54,.35)}',
      '.nftm_tag.compile{background:rgba(79,140,255,.10);color:#1e5fbf;border:1px solid rgba(79,140,255,.35)}',
      '.nftm_tag.unknown{background:rgba(0,0,0,.04);color:var(--dsw-alias-label-tertiary,#888);border:1px solid #e0e0e0}',
      '.nftm_main{flex:1;min-width:0}',
      '.nftm_cmd{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px;line-height:1.45;white-space:pre-wrap;word-break:break-all;color:var(--dsw-alias-label-primary,#111)}',
      '.nftm_st{display:flex;gap:10px;margin-top:2px;font-size:10px;color:var(--dsw-alias-label-tertiary,#777);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:nowrap;overflow:hidden}',
      '.nftm_st .ok{color:var(--dsw-alias-state-success-primary,#2e7d32)}',
      '.nftm_st .bad{color:var(--dsw-alias-state-error-primary,#d32f2f)}',
      '.nftm_empty{padding:18px 12px;text-align:center;color:var(--dsw-alias-label-tertiary,#888);font-size:11.5px}',
      '.nftm_error{color:var(--dsw-alias-state-error-primary,#d32f2f);font-size:11px;padding:6px 12px 10px}',
      '.nftm_dtm{flex:none;font-size:10px;color:var(--dsw-alias-label-tertiary,#777);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:nowrap}',
      /* --- footer：清空按钮 --- */
      '.nftm_foot{display:flex;justify-content:flex-end;align-items:center;gap:8px;padding:10px 16px;border-top:1px solid var(--dsw-alias-border-l2,#eee);flex:none;flex-wrap:wrap}',
      '.nftm_footStatus{flex:1;min-width:0;color:var(--dsw-alias-label-tertiary,#777);font-size:11px;line-height:18px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.nftm_footStatus.nftm_error{color:var(--dsw-alias-state-error-primary,#d32f2f)}',
      '.nftm_footBtn{flex:none;box-sizing:border-box;min-height:28px;color:var(--dsw-alias-label-secondary,#555);cursor:pointer;background:0 0;border:1px solid var(--dsw-alias-border-l2,#ddd);border-radius:7px;align-items:center;gap:6px;padding:3px 12px;font-size:12px;line-height:18px;display:inline-flex;font-family:inherit}',
      '.nftm_footBtn:hover:not(:disabled){background:var(--dsw-alias-interactive-bg-hover,#eee)}',
      '.nftm_footBtn:disabled{opacity:.5;cursor:not-allowed}',
      '.nftm_footBtnDanger{color:var(--dsw-alias-state-error-primary,#d32f2f);border-color:var(--dsw-alias-state-error-primary,#d32f2f)}',
      '.nftm_footBtnDanger:hover:not(:disabled){background:rgba(244,67,54,.08)}',
      /* --- 二次确认对话框（模态，仿会话管理 confirm dialog） --- */
      '.nftm_confirmLayer{position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;pointer-events:auto}',
      '.nftm_confirmBackdrop{position:absolute;inset:0;background:rgba(0,0,0,.4)}',
      '.nftm_confirm{position:relative;box-sizing:border-box;width:380px;max-width:calc(100vw - 32px);background:var(--dsw-alias-surface-l1,#fff);color:var(--dsw-alias-label-primary,#111);border:1px solid var(--dsw-alias-border-l2,#ddd);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.25);padding:16px;display:flex;flex-direction:column;gap:10px}',
      '.nftm_confirmTitle{font-size:14px;line-height:20px;font-weight:600}',
      '.nftm_confirmDesc{font-size:12.5px;line-height:19px;color:var(--dsw-alias-label-secondary,#555)}',
      '.nftm_confirmErr{color:var(--dsw-alias-state-error-primary,#d32f2f);font-size:12px;line-height:18px}',
      '.nftm_confirmFoot{display:flex;justify-content:flex-end;gap:8px}',
      '.nftm_dlgBtn{flex:none;box-sizing:border-box;min-height:32px;padding:5px 14px;border-radius:8px;border:1px solid var(--dsw-alias-border-l2,#ddd);background:transparent;color:var(--dsw-alias-label-secondary,#555);font-size:13px;line-height:18px;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center}',
      '.nftm_dlgBtn:hover:not(:disabled){background:var(--dsw-alias-interactive-bg-hover,#eee);color:var(--dsw-alias-label-primary,#111)}',
      '.nftm_dlgBtn:disabled{opacity:.5;cursor:not-allowed}',
      '.nftm_dlgBtnDanger{background:var(--dsw-alias-state-error-primary,#dc3545);border-color:transparent;color:#fff}',
      '.nftm_dlgBtnDanger:hover:not(:disabled){background:var(--dsw-alias-state-error-primary-hover,#e04858);color:#fff}',
    ].join('\n')

    let styleEl
    function ensureStyle() {
      if (document.getElementById('nf-terminal-monitor-style')) return
      styleEl = document.createElement('style')
      styleEl.id = 'nf-terminal-monitor-style'
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

    /* ================================ 面板 DOM ================================ */
    function createPanel() {
      const root = document.createElement('div')
      root.className = 'nftm_panel'
      root.setAttribute('data-nftm-panel', '')
      root.setAttribute('data-dsh-plugin', 'nf-terminal-monitor')
      root.innerHTML =
        '<div class="nftm_modalHead">' +
        '<span class="nftm_badge">🖥️</span>' +
        '<span class="nftm_title">终端命令监控</span>' +
        '<span class="nftm_meta"></span>' +
        '<button type="button" class="nftm_close" title="关闭">关闭</button>' +
        '</div>' +
        '<div class="nftm_filters">' +
        '<button type="button" class="nftm_fbtn on" data-ft="all">全部</button>' +
        '<button type="button" class="nftm_fbtn" data-ft="compile">编译机</button>' +
        '<button type="button" class="nftm_fbtn" data-ft="nf">NF 设备</button>' +
        '<button type="button" class="nftm_fbtn" data-ft="errors">异常</button>' +
        '</div>' +
        '<div class="nftm_filters">' +
        '<button type="button" class="nftm_fbtn ow on" data-owner="all">全部会话</button>' +
        '<span class="nftm_owchips"></span>' +
        '</div>' +
        '<div class="nftm_body"><div class="nftm_empty">加载中…</div></div>' +
        '<div class="nftm_foot">' +
        '<span class="nftm_footStatus"></span>' +
        '<button type="button" class="nftm_footBtn nftm_footBtnDanger" title="清空全部审计记录">🗑 清空记录</button>' +
        '</div>'

      const body = root.querySelector('.nftm_body')
      const metaEl = root.querySelector('.nftm_meta')
      const closeBtn = root.querySelector('.nftm_close')
      const statusEl = root.querySelector('.nftm_footStatus')
      const owChips = root.querySelector('.nftm_owchips')
      const clearBtn = root.querySelector('.nftm_footBtn')

      const TAG_NAMES = { nf: 'NF', compile: '编译机', unknown: '其他' }
      function render(items) {
        if (items.length === 0) {
          body.innerHTML = '<div class="nftm_empty">暂无命令记录 —— agent 通过 ssh-tools / deploy-build 操作编译机或 NF 设备后，这里会实时出现。</div>'
          return
        }
        body.innerHTML = items.map((it) => {
          const tag = TAG_NAMES[it.target] ?? '其他'
          const r = it.result || {}
          let status
          if (r.error && String(r.error).startsWith('BLOCKED')) {
            status = '<span class="bad">⛔ 拦截</span>'
          } else if (r.error) {
            status = '<span class="bad">✗ ' + esc(r.error) + '</span>'
          } else if (r.timed_out) {
            status = '<span class="bad">⏱ 超时</span>'
          } else if (r.exit !== undefined && r.exit !== null && r.exit !== 0) {
            status = '<span class="bad">✗ exit ' + esc(r.exit) + '</span>'
          } else {
            status = '<span class="ok">✓</span>'
          }
          const dur = r.dur !== undefined && r.dur !== null ? (Number(r.dur).toFixed(2) + 's') : ''
          const who = esc(String(it.user ?? '') + '@' + String(it.host ?? ''))
          return '<div class="nftm_item">' +
            '<span class="nftm_tag ' + esc(it.target ?? 'unknown') + '">' + esc(tag) + '</span>' +
            '<div class="nftm_main">' +
            '<div class="nftm_cmd">' + esc(it.cmd) + '</div>' +
            '<div class="nftm_st"><span>' + who + '</span><span>' + status + '</span>' +
            (dur ? '<span>' + dur + '</span>' : '') + '</div>' +
            '</div>' +
            '<span class="nftm_dtm">' + esc(String(it.ts ?? '').slice(5, 19)) + '</span>' +
            '</div>'
        }).join('')
      }

      function error(message) {
        body.innerHTML = '<div class="nftm_error">' + esc(message) + '</div>'
      }

      function setStatus(text, isError) {
        if (text) {
          statusEl.textContent = text
          statusEl.classList.toggle('nftm_error', !!isError)
        } else {
          statusEl.textContent = ''
          statusEl.classList.remove('nftm_error')
        }
      }

      function setMeta(text) {
        metaEl.textContent = text
      }

      return { root, body, closeBtn, clearBtn, owChips, render, error, setStatus, setMeta }
    }

    /* ================================ 确认对话框 DOM ================================ */
    function createConfirm() {
      const layer = document.createElement('div')
      layer.className = 'nftm_confirmLayer'
      layer.style.display = 'none'
      layer.setAttribute('data-nftm-confirm', '')
      layer.innerHTML =
        '<div class="nftm_confirmBackdrop"></div>' +
        '<div class="nftm_confirm" role="dialog" aria-modal="true" tabindex="-1">' +
        '<div class="nftm_confirmTitle"></div>' +
        '<div class="nftm_confirmDesc"></div>' +
        '<div class="nftm_confirmErr" style="display:none"></div>' +
        '<div class="nftm_confirmFoot">' +
        '<button type="button" class="nftm_dlgBtn" data-confirm-cancel></button>' +
        '<button type="button" class="nftm_dlgBtn nftm_dlgBtnDanger" data-confirm-ok></button>' +
        '</div>' +
        '</div>'
      document.body.appendChild(layer)

      const titleEl = layer.querySelector('.nftm_confirmTitle')
      const descEl = layer.querySelector('.nftm_confirmDesc')
      const errEl = layer.querySelector('.nftm_confirmErr')
      const okBtn = layer.querySelector('[data-confirm-ok]')
      const cancelBtn = layer.querySelector('[data-confirm-cancel]')
      let onConfirm = null
      let busy = false
      let current = null

      function close() {
        current = null
        onConfirm = null
        layer.style.display = 'none'
        errEl.style.display = 'none'
        document.removeEventListener('keydown', onKey, true)
      }
      function onKey(ev) {
        if (ev.key === 'Escape' && !busy) {
          ev.preventDefault()
          close()
        } else if (ev.key === 'Enter' && !busy) {
          ev.preventDefault()
          if (onConfirm) onConfirm()
        }
      }
      function open(opts) {
        current = opts || {}
        titleEl.textContent = opts.title || '确认'
        descEl.textContent = opts.description || ''
        okBtn.textContent = opts.confirmLabel || '确认'
        okBtn.disabled = false
        cancelBtn.textContent = opts.cancelLabel || '取消'
        errEl.style.display = 'none'
        busy = false
        onConfirm = () => {
          if (typeof opts.onConfirm === 'function') opts.onConfirm()
        }
        layer.style.display = 'flex'
        document.addEventListener('keydown', onKey, true)
        layer.querySelector('.nftm_confirm').focus()
      }
      okBtn.addEventListener('click', () => {
        if (!busy && onConfirm) onConfirm()
      })
      cancelBtn.addEventListener('click', () => {
        if (!busy) close()
      })
      layer.querySelector('.nftm_confirmBackdrop').addEventListener('mousedown', (ev) => {
        if (ev.target === ev.currentTarget && !busy) close()
      })
      return {
        open,
        close,
        setBusy(v) {
          busy = !!v
          okBtn.disabled = busy
          cancelBtn.disabled = busy
        },
        setError(message) {
          errEl.textContent = message
          errEl.style.display = message ? '' : 'none'
        },
        isOpen() { return current !== null }
      }
    }

    /* ================================ 侧栏入口壳 ================================ */
    /**
     * 极薄 React 壳：渲染侧栏底部（设置上方）的入口按钮，点击后经 portal
     * 弹出居中模态对话框容器 `[data-nftm-modal]`，内容由纯 DOM 面板填充。
     * 契约：sidebar.footer.action 的 occupant 接收 { wide }（false = 56px rail）。
     */
    function TerminalMonitorAction({ wide }) {
      const [open, setOpen] = React.useState(false)
      const rootRef = React.useRef(null)

      // 模态打开时：Esc / 面板内关闭按钮（nftm:request-close）均可关闭
      React.useEffect(() => {
        if (!open) return
        const onKey = (ev) => {
          if (ev.key === 'Escape') setOpen(false)
        }
        const onRequestClose = () => setOpen(false)
        document.addEventListener('keydown', onKey, true)
        document.addEventListener('nftm:request-close', onRequestClose)
        return () => {
          document.removeEventListener('keydown', onKey, true)
          document.removeEventListener('nftm:request-close', onRequestClose)
        }
      }, [open])

      const action = React.createElement('div', {
        ref: rootRef,
        className: 'nftm_action' + (wide ? '' : ' nftm_actionRail'),
      },
        React.createElement('button', {
          type: 'button',
          className: 'nftm_actionBtn',
          'data-active': open || undefined,
          title: '终端命令监控',
          'aria-expanded': String(open),
          'aria-haspopup': 'dialog',
          onClick: () => setOpen((v) => !v),
        },
          React.createElement('span', { className: 'nftm_actionIcon' }, '🖥️'),
          wide
            ? React.createElement(React.Fragment, null,
                React.createElement('span', { className: 'nftm_actionLabel' }, '终端命令监控'),
                React.createElement('span', { className: 'nftm_actionCount', 'data-nftm-count': '' }))
            : null
        )
      )

      if (!open) return action

      // 模态层：backdrop 点击关闭（仅点到 backdrop 自身，避免误关面板内交互）
      const layer = React.createElement('div', {
        className: 'nftm_modalLayer',
        'data-nftm-modal-layer': '',
      },
        React.createElement('div', {
          className: 'nftm_modalBackdrop',
          onMouseDown: (ev) => {
            if (ev.target === ev.currentTarget) setOpen(false)
          },
        }),
        React.createElement('div', {
          className: 'nftm_modal',
          role: 'dialog',
          'aria-modal': 'true',
          'aria-label': '终端命令监控',
        },
          React.createElement('div', {
            'data-nftm-modal': '',
            style: { display: 'flex', flexDirection: 'column', minHeight: 0, flex: '1 1 auto', width: '100%' },
          })
        )
      )

      if (createPortal) {
        return React.createElement(React.Fragment, null,
          action,
          createPortal(layer, ensurePortalHost())
        )
      }
      // 降级：内联渲染（fixed 定位仍可显示在侧栏之上）
      return React.createElement(React.Fragment, null, action, layer)
    }

    /* ================================ 插件入口 ================================ */
    exports.inject = ['slots']

    exports.apply = (ctx) => {
      ctx.effect(() => {
        ensureStyle()
        const bootTime = performance.now()
        let slotRegistered = false

        // 注册侧栏底部入口（设置按钮上方）
        try {
          ctx.slots.inject('sidebar.footer.action', () => {
            try {
              const unregister = ctx.slots.register({
                name: 'sidebar.footer.action',
                id: 'nf-terminal-monitor',
                order: 100,
                label: '终端命令监控',
              }, TerminalMonitorAction)
              return () => { try { unregister() } catch { /* 释放失败不阻塞 */ } }
            } catch (error) {
              console.error('[nf-terminal-monitor] sidebar register 失败：', error)
              return () => {}
            }
          })
          slotRegistered = true
        } catch (error) {
          console.error('[nf-terminal-monitor] sidebar 注入失败：', error)
        }

        const panel = createPanel()
        const confirm = createConfirm()
        let mounted = false
        let timer = null
        let filter = 'all'
        let ownerFilter = 'all' // 会话过滤：'all' 或具体 owner id
        let lastKey = ''
        let lastSignal = ''
        let lastError = ''

        // 面板关闭请求 → 通知 React 壳收起模态
        panel.closeBtn.addEventListener('click', () => {
          document.dispatchEvent(new CustomEvent('nftm:request-close'))
        })

        const targetButtons = panel.root.querySelectorAll('.nftm_fbtn[data-ft]')
        targetButtons.forEach((btn) => {
          btn.addEventListener('click', () => {
            filter = btn.getAttribute('data-ft')
            targetButtons.forEach((b) => b.classList.toggle('on', b === btn))
            void refresh(true)
          })
        })

        // 会话过滤 chips：全部会话(静态) + 当前会话(高亮) + 各 owner
        const ownerButtons = panel.root.querySelectorAll('.nftm_fbtn.ow')
        ownerButtons.forEach((btn) => {
          btn.addEventListener('click', () => {
            ownerFilter = btn.getAttribute('data-owner')
            panel.root.querySelectorAll('.nftm_fbtn.ow').forEach((b) => b.classList.toggle('on', b === btn))
            void refresh(true)
          })
        })

        const refresh = async (forceFlash) => {
          try {
            const params = new URLSearchParams({ limit: '150' })
            if (filter === 'errors') params.set('errors', '1')
            else if (filter !== 'all') params.set('target', filter)
            if (ownerFilter !== 'all') params.set('owner', ownerFilter)
            const data = await api('/api/nf-terminal-monitor/list?' + params.toString())
            const items = Array.isArray(data.items) ? data.items : []
            const kv = items.length > 0 ? items.map((it) => String(it.ts) + '|' + String(it.cmd)).join('\n') : ''
            if (lastKey !== kv || forceFlash) {
              lastKey = kv
              panel.render(items)
            }
            const summary = await api('/api/nf-terminal-monitor/summary').catch(() => null)
            const total = summary && typeof summary.total === 'number' ? summary.total : items.length
            if (String(total) !== lastSignal) {
              lastSignal = String(total)
              panel.setMeta(total + ' 条')
              const countEl = document.querySelector('[data-nftm-count]')
              if (countEl) countEl.textContent = String(total)
            }
            renderOwnerChips(summary)
            if (lastError) {
              lastError = ''
              panel.setStatus('', false)
            }
          } catch (error) {
            lastError = String(error && error.message ? error.message : error)
            panel.error(lastError)
            panel.setStatus('读取失败', true)
          }
        }

        // 渲染会话过滤 chips：当前会话(如存在) + 各 owner（无记录时仅"全部会话"）
        function renderOwnerChips(summary) {
          if (!summary) return
          const owners = (summary.owners && typeof summary.owners === 'object') ? summary.owners : {}
          const cur = summary.currentSession || summary.latestOwner || ''
          const chips = []
          if (cur) {
            const short = String(cur).length > 24 ? String(cur).slice(0, 24) + '…' : String(cur)
            const label = (summary.currentSession ? '当前▸' : '最新▸') + short
            chips.push('<button type="button" class="nftm_fbtn ow' + (ownerFilter === cur ? ' on' : '') +
              '" data-owner="' + esc(cur) + '" title="' + esc(cur) + '">' + esc(label) + '</button>')
          }
          panel.owChips.innerHTML = chips.join('')
          // 绑定动态 chips 点击
          panel.owChips.querySelectorAll('.nftm_fbtn.ow').forEach((btn) => {
            btn.addEventListener('click', () => {
              ownerFilter = btn.getAttribute('data-owner')
              panel.root.querySelectorAll('.nftm_fbtn.ow').forEach((b) => b.classList.toggle('on', b === btn))
              void refresh(true)
            })
          })
        }

        // 清空记录：二次确认对话框（不再使用 window.confirm）
        panel.clearBtn.addEventListener('click', () => {
          confirm.open({
            title: '清空全部记录',
            description: '确定清空全部终端命令审计记录？此操作不可恢复。',
            confirmLabel: '清空记录',
            cancelLabel: '取消',
            onConfirm: async () => {
              confirm.setBusy(true)
              confirm.setError('')
              try {
                const response = await fetch('/api/nf-terminal-monitor/clear', { method: 'POST', cache: 'no-store' })
                const data = await response.json().catch(() => ({}))
                if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status))
                ownerFilter = 'all'
                panel.root.querySelectorAll('.nftm_fbtn.ow').forEach((b) => b.classList.toggle('on', b.getAttribute('data-owner') === 'all'))
                lastKey = ''
                lastSignal = ''
                panel.owChips.innerHTML = ''
                confirm.close()
                panel.setStatus('已清空 ' + (typeof data.cleared === 'number' ? data.cleared : '') + ' 条记录', false)
                void refresh(true)
              } catch (error) {
                const message = String(error && error.message ? error.message : error)
                confirm.setError(message)
                confirm.setBusy(false)
              }
            },
          })
        })

        // 挂载：面板随模态层出现而挂入 [data-nftm-modal]，模态收起时回归隐藏容器；
        // 仅挂载期间执行轮询。注册失败且 4s 内无槽位时仅报错（与会话管理一致，不做浮动兜底）。
        const holdHost = (() => {
          const el = document.createElement('div')
          el.style.display = 'none'
          document.body.appendChild(el)
          return el
        })()

        const reconcile = () => {
          const modalEl = document.querySelector('[data-nftm-modal]')
          if (modalEl !== null) {
            if (panel.root.parentElement !== modalEl) {
              if (panel.root.parentElement === document.body) panel.root.remove()
              holdHost.appendChild(panel.root)
              modalEl.appendChild(panel.root)
            }
            mounted = true
            if (timer === null) {
              timer = window.setInterval(refresh, 3000)
              void refresh(true)
            }
            return
          }
          if (panel.root.parentElement !== holdHost && panel.root.parentElement !== null) {
            panel.root.remove()
            holdHost.appendChild(panel.root)
          }
          if (timer !== null) {
            window.clearInterval(timer)
            timer = null
          }
        }

        const observer = new MutationObserver(reconcile)
        observer.observe(document.body, { childList: true, subtree: true })
        reconcile()
        // 注册失败兜底提示（不浮动：与会话管理同样的"无槽位即无 UI"策略）
        if (!slotRegistered) {
          console.error('[nf-terminal-monitor] sidebar footer.action 槽位不可用，入口按钮不会渲染')
        }
        void bootTime

        return () => {
          if (timer !== null) window.clearInterval(timer)
          observer.disconnect()
          panel.root.remove()
          confirm.close()
        }
      }, 'nf-terminal-monitor: widget')
    }

    return exports
  },
})