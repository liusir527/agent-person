# @nsfocus/nf-brand

把 dsh Web 面板里的 DeepSeek 品牌替换成你自己的（侧边栏 logo + 品牌文字 + 会话空状态 hero logo + 浏览器标签页）。

## 原理（为什么这样能覆盖）

- dsh Web 是「插槽 + 优先级」的客户端插件体系。官方 `@deepseek-ai/dsh-client-ui-brand-official` 以 `priority=0` 注册 `sidebar.brand.mark` / `sidebar.brand.name` / `conversation.hero.brand.mark` 三个插槽。
- 插槽内核（SlotCore）对 single 插槽的规则：**priority 数值更小的 occupant 先渲染**（源码注释原文 "register at a different priority to shadow it (lowest renders)"；同 priority 会直接抛错）。
- 本插件以 `priority: -100` 注册同名三个插槽 → 永远压过官方品牌，且与插件加载先后无关。
- 与官方插件注册结构完全一致（嵌套 `slots.inject` + generator yield），保证声明方就绪前先等待、可整体撤回。

## 改你自己的品牌

1. 打开 `client.js`，把 `CustomLogo` 里的两个 `React.createElement`（占位圆角方块 + N 字母）换成你自己 SVG 的内容。viewBox 保持 `0 0 50 50`（侧边栏按 24px 渲染，hero 更大）。
2. 改 `BRAND_TEXT` 常量为你自己的产品名。
3. （可选）删掉 apply 末尾的 `document.title` / favicon 覆盖段。

## 接入启动流程（重启后生效）

1. 首次安装到 web profile（与 nf-bug-progress 同样方式）：

   ```bat
   cd /d C:\Users\DELL\.dsh\profiles\web
   pnpm add link:E:\agent_assets\packages\nf-brand
   ```

2. `start.bat` 已写入生成 patch 的清单（`- id: nf-brand / name: '@nsfocus/nf-brand'`），重新运行 start.bat 即可。

> 注意：重启 `dsh web` 会中断当前会话运行；替换后强刷浏览器（Ctrl+F5）查看效果。
> 若只想换浏览器标签页图标，也可以不动本插件，直接把 `node_modules\@deepseek-ai\dsh-web-frontend\dist\favicon.svg` 换成你自己的 SVG（npm 更新 dsh 时会被还原）。

## 回滚

- 从 `start.bat` 删掉 nf-brand 两行（或从 patch 清单移除），重启即恢复 DeepSeek 品牌；
- 或直接删除 `packages\nf-brand` 并在 web profile 里 `pnpm rm @nsfocus/nf-brand`。