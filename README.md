# agent-person

DSH 工作区 —— 自托管的 `@deepseek-ai/dsh` 浏览器 Harness，
附带 6 个 NF (NSFOCUS) 插件源（`packages/*`）。

## 蜂巢大脑（Hive Brain）—— 本工作区同时是中央知识大脑

> 已实施（2026-09-11，M0-M6 全链路通过）。这是一个**可复用、git 管理、汇总到 git 仓库的 AI 工作目录**：
> 分散 agent 采集知识饲喂中央大脑，通过 git 双向共享。

### 快速开始（新 agent 加入共享）

```powershell
# 1. 克隆（含知识大脑 submodule）
git clone --recursive https://github.com/liusir527/agent-person.git
cd agent-person

# 2. 拉取最新大脑知识
git submodule update --remote --merge

# 3. 读统一入口
#    init/manifest.yaml            → 工作区身份 + 当前场景
#    init/scenes/<scene>.yaml      → 场景说明
#    .dsh-memory/hive.yaml         → 蜂巢能力清单（唯一事实源）

# 4. 检索知识（按场景）
python .dsh-memory/scripts/search.py "关键词" --scene debug

# 5. 沉淀知识（去毒四问 → memory-gen → memory-push）
```

### 核心组件

| 组件 | 位置 | 说明 |
|------|------|------|
| 统一入口 | `init/` | 工作区身份 + 场景定义 + 新 agent 引导 |
| 中央大脑 | `.dsh-memory/`（submodule） | 四类知识：product / skills / scenes / experiences |
| 记忆曲线漏斗 | `.dsh-memory/scripts/{tier_manager,search,backfill_weights}.py` | 权重命中/复用上调、Ebbinghaus 衰减、分层流转 |
| 场景命名空间 | skill `scene:` 标签 + `knowledge/scenes/<scene>/` | develop/debug 场景隔离，免 git 分支切换 |
| 蜂巢派生 | `.dsh-memory/hive.yaml` + `.dsh/agents/hive/base.md` + `.dsh/tools/hive_spawn.py` | agent 出生携带全部能力，可 spawn/sync 裂变 |
| 去毒门禁 | `.dsh/rules/knowledge-sedimentation.md` + `.dsh/tools/link_check.py` | 沉淀前必过"去毒四问"，提交前 link_check PASS |

### 沉淀流程（每个 agent 的义务）

```
任务完成 → 去毒四问（通用/普适/非一次性/可验证）→ memory-gen 写入 knowledge/<类别>/
        → link_check PASS → memory-push（git -C .dsh-memory add/commit/push → 主仓 gitlink → push）
```

---

## 5 分钟启动

### 前置

- **Node.js ≥ 22.19** （`node -v`）
- **pnpm ≥ 9** （`npm i -g pnpm`）
- **git**
- **DSH** （`npm i -g @deepseek-ai/dsh`）

### 第一次跑（任何新机器 / clone 后）

```powershell
# 仓库根
pwsh -File scripts/bootstrap-nf-plugins.ps1
```

幂等脚本会：
1. 把 `packages/nf-hooks / nf-gdb-guard / nf-system-prompt` 这3 个 TS 包
   编译到 `lib/index.js`；
2. 把6 个 NF 包（`@nsfocus/nf-*`）以 `link:` 形式装到 DSH web profile
   （`~/.dsh/profiles/web/package.json`），DSH 自动 reconcile 进 `bundles`；
3. **首次**写入 `.dsh/rules/dirs.json`（含 `~/.dsh` + `~/.dsh-memory` 白名单），
   否则 `nf-hooks` 会拒绝 bootstrap 自己写到 `~/.dsh/...`；
4. 解析 Python 解释器（`$env:DSH_PYTHON` > `~/.dsh/python.txt` > well-known > `PATH`），
   把路径钉到 `~/.dsh/python.txt`；
5. `pip install pyyaml paramiko requests`（缺哪个装哪个，已装即跳过）；
6. 语法检查 `.dsh-memory/scripts/{search,tier_manager,backfill_frontmatter,fix_yaml_summary}.py`；
7. 渲染 `config/mcp-memory.patch.yml.template` 并幂等注入
   `~/.dsh/profiles/web/cordis.patch.yml`；
8. 写入占位 `mcp_memory.py` stub 到 `~/.dsh-memory/scripts/`
   （**仅在缺失时**；P4 真实实现落地后由人工替换，bootstrap 不会覆盖）。

> ⚠️ 步骤3 写 `dirs.json` 之后，**必须重启一次 `dsh web`**，nf-hooks 才会加载新白名单，
> bootstrap 后续阶段才能写到 `~/.dsh/...`。首次 clone 用户跑完一次 bootstrap 后，
> 关闭再打开 web 即可。

完成后启动 GUI：

```powershell
dsh web
```

浏览器打开 `http://127.0.0.1:3080`。
预期能看到：
- 侧边栏品牌 / logo 被 NF 品牌插件覆盖（不再显示 DeepSeek）；
- 对话页输入框上方有「BUG 进度」面板（`@nsfocus/nf-bug-progress`）；
- 侧栏底部设置按钮上方有「终端命令监控」入口（`@nsfocus/nf-terminal-monitor`）。

### 验证

```powershell
# 3 个 client bundle 必须 200
curl -I http://127.0.0.1:3080/plugins/@nsfocus/nf-brand/client.js
curl -I http://127.0.0.1:3080/plugins/@nsfocus/nf-bug-progress/client.js
curl -I http://127.0.0.1:3080/plugins/@nsfocus/nf-terminal-monitor/client.js

# 2 个 API 必须返回 JSON
curl http://127.0.0.1:3080/api/nf-bug-progress/list
curl http://127.0.0.1:3080/api/nf-terminal-monitor/list

# 6 个 NF 包应在 bundles 列表
dsh web --dump-config 2>$null | Select-String -Pattern 'nf-'
```

## 日常开发（**不要** 重跑 bootstrap）

bootstrap 脚本只管"编译产物 + 链接到 profile"两件事，日常改代码根本不需要碰它。

| 你改了 | 要做什么 |
|---|---|
| `packages/<p>/src/*.ts` | `cd packages/<p> && pnpm exec tsc`（或 `-w` 监听） |
| `packages/<p>/client.js` | 浏览器刷新 / 重启 `dsh web` |
| `packages/<p>/cordis.patch.yml` | **重启 `dsh web`**（Loader 启动时读一次） |
| `packages/<p>/package.json`（manifest 字段） | **重启 `dsh web`** |
| `packages/<p>/README.md`、`packages/README.md`、`scripts/*` | 无 |

**只在以下情况重跑 `scripts/bootstrap-nf-plugins.ps1`：**

1. 首次 clone（`lib/`、`node_modules/` 都还不存在）；
2. 换了一台机器；
3. DSH web profile 被重置（`rm -rf ~/.dsh/profiles/web` 或卸载了 `@nsfocus/*`）；
4. 显式 `FORCE_REBUILD=1 FORCE_RELINK=1 pwsh -File scripts/bootstrap-nf-plugins.ps1` 想清空重做。

脚本每次都会打印跳过 / 重做的项；幂等可重复运行。

## 集成架构

```
┌─ DSH web profile (~/.dsh/profiles/web) ────────────────┐
│  bundles[] ──► cordis Loader entries ──► apply(ctx)    │
│                                                       │
│   ┌─────────────────────────────────────────────────┐ │
│   │ @nsfocus/nf-brand           (dual: node+web)   │ │
│   │ @nsfocus/nf-bug-progress    (dual: API+web)     │ │
│   │ @nsfocus/nf-terminal-monitor(dual: API+web)     │ │
│   │ @nsfocus/nf-hooks           (node: tools gate)  │ │
│   │ @nsfocus/nf-gdb-guard       (node: shell gate)  │ │
│   │ @nsfocus/nf-system-prompt   (node: prompt inj)  │ │
│   └─────────────────────────────────────────────────┘ │
│                                                       │
│   /plugins/<id>/client.js ◄── dsh-client-modules      │
│   /api/nf-*/*           ◄── nf-bug-progress /          │
│                            nf-terminal-monitor        │
└───────────────────────────────────────────────────────┘
```

每个 NF 包的加载面：
- `dsh.bundle.patch` → 声明 `cordis.patch.yml`，让 Loader 在该包作为 entry 时插入一行；
- `dsh.client.platform: "web"` + `exports["./client"]` → 把 `client.js` 注入浏览器
  （仅前3 个 dual-face 包声明；其余 3 个纯 node 拦截器不写这个字段）。

详细说明见 [`packages/README.md`](packages/README.md)。

## Python 依赖

| 包 | 必需性 | 谁在用 | 装它干什么 |
|---|---|---|---|
| `pyyaml` | 必需（bootstrap 自动装） | `.dsh-memory/scripts/*` + `.dsh/skills/gns-topo/*` | 解析经验索引 YAML |
| `paramiko` | 必需（bootstrap 自动装） | `.dsh/skills/{ssh-tools,deploy-build,vpp-api-sync}/scripts/*.py` | SSH/SCP 到 NF 设备 / 编译机 |
| `requests` | 必需（bootstrap 自动装） | `.dsh/skills/gns-topo/gns-topo参考代码.py` | 调外部 HTTP API |
| `evengsdk` | 可选（`BOOTSTRAP_OPTIONAL_PYDEPS=1`） | `.dsh/skills/gns-topo/eve-ng.py` | EVE-NG 拓扑 |
| `mcp-atlassian` | 可选（按需） | `.dsh/skills/ask-atlassian/references/mcp-server-setup.md` | JIRA/Confluence MCP（`uv tool install mcp-atlassian`） |

**Python 解释器解析顺序**（bootstrap 第4 步）：

1. `$env:DSH_PYTHON` 显式路径
2. `~/.dsh/python.txt`（bootstrap 钉的文件，方便其他工具共享）
3. well-known 路径（`C:\Python314\python.exe`、`C:\Python313\python.exe`、`C:\Python312\python.exe`）
4. `PATH` 上的 `python3` / `python` / `py`

要换 Python：在终端 `setx DSH_PYTHON "D:\path\to\python.exe"`，然后重跑 bootstrap。

## 目录

```
.
├── AGENTS.md                # 子 agent 索引（DSH 注入）
├── packages/                # 6 个 NF 插件源
│   ├── README.md
│   ├── nf-brand/
│   ├── nf-bug-progress/
│   ├── nf-terminal-monitor/
│   ├── nf-hooks/            # src/index.ts + 编译产物 lib/
│   ├── nf-gdb-guard/
│   └── nf-system-prompt/
├── scripts/
│   └── bootstrap-nf-plugins.ps1  # 首次装载脚本（幂等）
├── runtime/                 # 运行时产物（不入库）
├── .dsh/                    # 子模块占位 / skill 目录
├── .dsh-memory/             # v2 经验知识库
└── .gitignore
```

## 故障排查

| 症状 | 原因 / 修复 |
|---|---|
| `bash-rtk not found` 警告 | `~/.dsh/profiles/web/cordis.patch.yml` 里有未注册的 disable 目标；无害，可保留 |
| `task-board ledger is already owned by process X` | 同时跑两个 `dsh web`；停掉旧的那个再启动新的 |
| 浏览器看不到 NF 品牌 / BUG 进度 | 重启 `dsh web`（PID 切到新进程才会读最新 manifest） |
| `/plugins/@nsfocus/...` 404 | 那是改 manifest 前的旧 web 进程；停掉后 launcher 会自动起新的 |
| bootstrap 报 `Missing packages/<p>/package.json` | 子目录布局漂移；核对 `packages/README.md` 与实际目录一致 |
| powershell 5.1 跑 bootstrap 中文乱码 | 已在脚本里把 `Get-Content` 全部加 `-Encoding UTF8`；如果 profile 文件有中文还需修 `chcp 65001` |
| `FORCE_REBUILD=1` 重编后 server 仍用旧代码 | cordis Loader 缓存在内存里；重启 `dsh web` |
| bootstrap 写到 `~/.dsh/...` 被拦 | nf-hooks restricted 模式没读到 dirs.json；删除 `.dsh/rules/dirs.json` 重跑 bootstrap，再重启 `dsh web` |
| `mcp-memory` 启动失败（`python: can't open '...mcp_memory.py'`） | stub 没装；跑 bootstrap，会自动写入 `~/.dsh-memory/scripts/mcp_memory.py` |
| `pip install` 报权限错 | 当前 Python 没写 site-packages 的权限；改用 user install 或设 `$env:DSH_PYTHON` 指向可写的 venv |

### MCP stub 烟测

```powershell
# 测试 workspace 副本（无外部依赖）
cd runtime/test-mcp-memory
python drive.py

# 测试真实 stub（DSH web 实际 spawn 的那个）
python drive_real.py
```

期望输出：6 / 6（或 4 / 4）响应 OK，1 个未知 method 返回 JSON-RPC `-32601 method not found`（这是 spec 要求，不是 bug）。

## 路径策略（重要）

文档、注释、脚本里**禁止**使用机器特定的绝对路径
（`E:/数字永生/...`、`REDACTED_WORKSPACE_PATH/...`）。
本仓库所有脚本都用 `git rev-parse --show-toplevel` 锚定工作区根，
跨机器 / 跨目录都能解析。

## License

仓库内部使用，未指定开源协议。
