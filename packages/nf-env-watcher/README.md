# @nsfocus/nf-env-watcher

DSH 启动后监听 `<cwd>/.env` 文件变化，重读到 `process.env`，让 agent 写 `.env` 之后无需重启 dsh web 即可生效。

## 工作原理

DSH 启动时 `@deepseek-ai/dsh-app-boot` 的 `loadLayeredEnv` 一次性 `process.loadEnvFile('.env')`。之后没人监听 `.env`，agent 改完得重启 DSH 才生效。

本插件在 cordis `apply()` 里：

1. 建立 `fs.watch(<cwd>/.env)`
2. 200ms debounce
3. 重读 `.env`，用 Node 标准库 `util.parseEnv` 解析（语义跟 dsh-app-boot 一致）
4. 过滤 bootstrap-only 变量（`DSH_*` / `PATH` / `*_PROXY` / `NODE_*` 等）；任一命中 → **整个 reload 拒绝**，不修改 `process.env`
5. 通过则把 `process.env[k] = v` 全量覆盖（包括从 shell 继承来的同名变量）
6. 活动日志写入 `<cwd>/runtime/nf-env-watcher.log`（JSONL 格式，agent 可读）

## 覆盖策略（与产品决策对齐）

| 情况 | 行为 |
|---|---|
| `.env` 写了 `JIRA_TOKEN=x`，shell 已有 `JIRA_TOKEN=y` | 用 x（覆盖） |
| `.env` 没写某个 key | 保留 shell 继承的 |
| `.env` 写了 `PATH=...` / `DSH_PERMISSION_MODE=...` | **拒绝 reload**，日志告警，进程不挂 |

要让 bootstrap-only 变量生效，仍然要在启动 DSH 的 shell 里 export（一次性，参考仓库根 README.md "如何在 dsh 启动时注入环境变量"）。

## 监听范围

只听 `<cwd>/.env`（DSH 启动进程的工作目录）。

> 在典型的 harness 部署里，PowerShell 用 `-WorkingDirectory "<workspace>"` 启动 launcher，dsh web 子进程的 cwd 继承自此，**等于工作区根**——所以 agent 在工作区根写的 `.env` 直接被监听。如果你的 launcher 在别处启动 dsh，需要在 launcher shell 里 `cd <workspace>`。

不监听：

- `~/.dsh/.env`：避免热加载两层之间的优先级模糊
- `cordis.patch.yml`、`~/.dsh/rules/dirs.json`：改这些需要重启 dsh web
- 已 spawn 的子进程（mcp-memory / python -c 等）：子进程保留 spawn 时的 env snapshot；要看新 env 要重启

## 验证

```bash
# 1. 启动 dsh web 后，看 runtime/nf-env-watcher.log 应该有 start 事件：
#    {"ts":"...","event":"start","envFile":"...","cwd":"..."}
#
# 2. 修改 .env（用 write 工具完整重写，部分 append 在 Windows fs.watch
#    上可能漏报）：
#    NF_TEST_VAR=hello
#
# 3. 看 runtime/nf-env-watcher.log 应该有 reload 事件：
#    {"ts":"...","event":"reload","applied":["NF_TEST_VAR"]}
#
# 4. 在对话里问 agent："NF_TEST_VAR 是什么？"，应该答 hello
```

`runtime/test-env-watcher/drive.py` 是等价的离线 Python 测试驱动（不依赖 DSH），验证 parseEnv + bootstrap-only 拒绝 + reload 语义。

## bootstrap 自动集成

`scripts/bootstrap-nf-plugins.ps1` 第 4 步（link 6 个 NF 包到 web profile）会自动包含本包。无需额外操作。

## 已知限制

- **Windows fs.watch 对 `Out-File -Append` / 增量编辑漏报率较高**——使用 `write` 工具完整重写文件最稳定
- **子进程不感知 reload**——已 spawn 的 python/node 进程保留当时的 env；要让它们看到新值需要重启
- **第一次 reload 之前的 ESM 模块级 `import.meta.env.X`** 不会更新（导入时绑定）
