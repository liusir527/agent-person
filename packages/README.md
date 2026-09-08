# NF 插件（packages/*）

本目录是 DSH Web profile 的6 个 NF 插件源。每个子包都是一个独立的 npm package，
通过 `dsh plugin --profile web add link:<path>` 装载到 DSH。

## 插件清单

| 包 | 角色 | node 半体 | browser 半体 |
|---|---|---|---|
| `@nsfocus/nf-brand` | 自定义品牌（覆盖 DeepSeek logo / 品牌名） | 空 `apply()` 占位 | `client.js` 注入 sidebar + hero 插槽 |
| `@nsfocus/nf-bug-progress` | BUG 修复工作流进度面板 | `/api/nf-bug-progress/{list,state}` | dock 插槽 + 浮动兜底 |
| `@nsfocus/nf-terminal-monitor` | 终端命令审计面板 | `/api/nf-terminal-monitor/{list,summary,clear}` | sidebar footer 入口 + 居中模态 |
| `@nsfocus/nf-hooks` | 文件访问门控（restricted 模式） | `tools/pre-execute` 拦截 | — |
| `@nsfocus/nf-gdb-guard` | GDB 危险命令防护 | `tools/pre-execute` 拦截 | — |
| `@nsfocus/nf-system-prompt` | System Prompt 注入（四问 / 修复流程 / 调试经验） | `systemPrompt.section()` | — |

前3 个是「dual-face」包（node + browser），后3 个是纯 node 拦截器 / 提示词注入。

## 集成方式

DSH 的加载管线是：
1. **`dsh.profile.bundles[]`** —— profile manifest 里登记的 Loader entry 名；
2. **`dsh.bundle.patch`** —— 每个包声明的 `cordis.patch.yml`，用 `- insert` 把它作为 cordis row 插入；
3. **`dsh.client.platform: "web"` + `exports["./client"]`** —— 仅前3 个包用此让 DSH `ClientModuleRegistry` 把 `client.js` 通过 `/plugins/<id>/client.js` 注入浏览器。

修改任一字段都需要 **重启 `dsh web`** 才会生效（cordis Loader 每次启动重读 manifest）。

## 装载流程（首次 / 重新装机）

详见 [`scripts/bootstrap-nf-plugins.ps1`](../scripts/bootstrap-nf-plugins.ps1)：

```powershell
# 在仓库根
pwsh -File scripts/bootstrap-nf-plugins.ps1
```

脚本幂等：
- `lib/` 已存在 → 跳过 TS 编译；
- web profile 已声明 `link:*` 依赖 → 跳过 `dsh plugin add`；
- 都失败会有明确错误码与提示。

强制全量重建：`FORCE_REBUILD=1 FORCE_RELINK=1 pwsh -File scripts/bootstrap-nf-plugins.ps1`

## 日常开发（不需要重跑 bootstrap）

| 改了什么 | 要做什么 |
|---|---|
| `packages/<p>/src/*.ts` | `cd packages/<p> && pnpm exec tsc`（或 `pnpm exec tsc -w`） |
| `packages/<p>/client.js` | 浏览器刷新即可（HMR 或 F5） |
| `packages/<p>/cordis.patch.yml` | **重启 `dsh web`**（cordis Loader 只读一次 patch） |
| `packages/<p>/package.json`（manifest） | 重启 `dsh web`（`ClientModuleRegistry` 在启动时按 manifest hash） |
| 调试 API 路由 | 重启 `dsh web`（路由注册在 `apply()` 里，effect 释放/重建） |

**只有以下情况才重跑 bootstrap：**
1. clone 后第一次启动（`node_modules`、`lib/` 都不存在）；
2. 换了一台新机器；
3. DSH web profile 被清空 / 重置（`rm -rf ~/.dsh/profiles/web` 或 `dsh plugin ... remove` 把 NF 依赖卸了）；
4. `FORCE_REBUILD=1` 想清空 lib 重编。

## 验证

启动后:

```powershell
# 浏览器侧：3 个 client bundle 必须 200
curl -I http://127.0.0.1:3080/plugins/@nsfocus/nf-brand/client.js
curl -I http://127.0.0.1:3080/plugins/@nsfocus/nf-bug-progress/client.js
curl -I http://127.0.0.1:3080/plugins/@nsfocus/nf-terminal-monitor/client.js

# 服务端 API：必须 200 + JSON
curl http://127.0.0.1:3080/api/nf-bug-progress/list
curl http://127.0.0.1:3080/api/nf-terminal-monitor/list

# 配置 dump：6 个 NF 包应在 bundles 列表
dsh web --dump-config 2>$null | Select-String -Pattern 'nf-'
```

期望输出包含以下6 行：

```
# == @nsfocus/nf-brand
- id: nf-brand
- id: nf-bug-progress
- id: nf-gdb-guard
- id: nf-hooks
- id: nf-system-prompt
- id: nf-terminal-monitor
```

## 路径策略（重要）

源码、注释、文档中**禁止**使用机器特定绝对路径（如 `E:/数字永生/...`、`REDACTED_WORKSPACE_PATH/...`）。
bootstrap 脚本用 `git rev-parse --show-toplevel` 锚定仓库根，
保证换机 / 换目录都能解析。

跨机器迁移的两种模式：
- **方案 A（本仓库采用）**：git 仓库 + `link:` 依赖 + bootstrap 脚本；
- **方案 B**：发布到私有 npm registry，每机 `dsh plugin --profile web add @nsfocus/nf-<x>`。
