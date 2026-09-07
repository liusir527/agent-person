/* eslint-disable */
/**
 * @nsfocus/nf-brand —— 浏览器半体：把 dsh Web 面板里的 DeepSeek 品牌换成你自己的。
 *
 * 原理：
 *   dsh Web 是「插槽 + 优先级」体系。官方 @deepseek-ai/dsh-client-ui-brand-official
 *   以 priority=0 注册 sidebar.brand.mark / sidebar.brand.name /
 *   conversation.hero.brand.mark；SlotCore 对 single 插槽的规则是
 *   「register at a different priority to shadow it (lowest renders)」——
 *   即 priority 数值更小的 occupant 先渲染。本插件以 priority=-100 注册同名插槽，
 *   因此无论加载先后，都会覆盖官方品牌（侧边栏 + 会话 hero 两处）。
 *
 * 换成你自己的图标：
 *   1) 把下方「← 你的图标 1」处的 path 数据替换成你 SVG 的 path（或换成
 *      React.createElement('circle'/'rect'...) 组合）。viewBox 保持 0 0 50 50
 *      最稳，与官方 FishLogo 的尺寸契约一致（侧边栏 24px、hero 更大）。
 *   2) 把「← 你的图标 2」处的品牌文字替换成你自己的产品名。
 *   3) 可选：apply 里已带 document.title / favicon 兜底替换（仅当标题含 DeepSeek
 *      时生效），不需要就删掉那段。
 */
window.__ModuleLoader__.load({
  id: '@nsfocus/nf-brand',
  factory: (require) => {
    var module = { exports: {} }
    var exports = module.exports
    Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' })

    const React = require('react')

    /* ============================ 你的图标（mark） ============================ */
    // ← 你的图标 1：占位为「圆角方块 + N 字母」。把 d 换成你自己 SVG 的 path 即可。
    // 注意：这是纯 JS，不能写 JSX；多个图形就并列多个 React.createElement。
    function CustomLogo(props) {
      const size = typeof props.size === 'number' ? props.size : 24
      return React.createElement(
        'svg',
        {
          width: size,
          height: size,
          viewBox: '0 0 50 50',
          className: props.className,
          fill: 'none',
          'aria-hidden': true,
        },
        React.createElement('rect', {
          x: 4, y: 4, width: 42, height: 42, rx: 10,
          fill: 'var(--dsw-alias-brand-primary, #4f8cff)',
        }),
        React.createElement('path', {
          d: 'M16 35V15h6.5l13.5 16.5V15h6v20h-6.5L21.5 18.5V35z',
          fill: 'var(--dsw-alias-bg-layer-3, #101014)',
        })
      )
    }

    /* ============================ 你的品牌文字（wordmark） ============================ */
    // ← 你的图标 2：品牌名文字。sidebar 的官方 occupant 是 "HARNESS" 样式字标。
    const BRAND_TEXT = 'YOUR BRAND' // ← 改成你自己的产品名

    function CustomBrandName() {
      return React.createElement(
        'span',
        {
          style: {
            fontWeight: 700,
            letterSpacing: '0.04em',
            fontSize: 13,
            color: 'var(--dsw-alias-label-primary, #e6e6e6)',
          },
        },
        BRAND_TEXT
      )
    }

    /* ============================ 插槽注册 ============================ */
    exports.inject = ['slots']

    // 官方插件的注册结构是嵌套 slots.inject + generator yield：
    // inject 保证「等声明方就绪后再注册」，yield 保证整体事务式安装/撤销。
    // 我们唯一的不同点是 priority: -100（官方是默认 0）—— 低者先渲染，覆盖生效。
    exports.apply = (ctx) => {
      ctx.slots.inject('sidebar.brand.mark', () =>
        ctx.slots.inject('sidebar.brand.name', () =>
          ctx.slots.inject('conversation.hero.brand.mark', function* () {
            yield ctx.slots.register(
              { name: 'sidebar.brand.mark', id: 'nf-brand', priority: -100 },
              CustomLogo
            )
            yield ctx.slots.register(
              { name: 'sidebar.brand.name', id: 'nf-brand', priority: -100 },
              CustomBrandName
            )
            yield ctx.slots.register(
              { name: 'conversation.hero.brand.mark', id: 'nf-brand', priority: -100 },
              CustomLogo
            )
          })
        )
      )

      // 可选：浏览器标签页标题 / favicon 兜底（dist 里是构建期的 DeepSeek 默认值，
      // 运行时覆盖一次即可让标签页也换成你自己的；不想要就删掉）。
      try {
        if (document.title && document.title.indexOf('DeepSeek') !== -1) {
          document.title = BRAND_TEXT
        }
        const favicon = document.querySelector('link[rel="icon"]')
        if (favicon && favicon.href.indexOf('favicon') !== -1) {
          const svg =
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">' +
            '<rect x="4" y="4" width="42" height="42" rx="10" fill="currentColor"/></svg>'
          favicon.href = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
        }
      } catch (error) {
        console.error('[nf-brand] title/favicon override failed:', error)
      }
    }

    return module.exports
  },
})