# @nsfocus/nf-terminal-monitor

NF **终端命令监控面板**插件：嵌入 DSH Web GUI **左侧面板**（侧栏底部、设置按钮上方），实时展示 agent 在编译机 / NF 设备上执行的命令。UI 布局与会话管理（`dsh-session-manager`）一致：侧栏入口按钮 + 居中模态对话框。

## 功能

- agent 每次通过 `ssh-tools`（`ssh_batch.py` / `ssh_shell.py`）或 `deploy-build`（`deploy_build.py`）向编译机 / NF 设备发送命令时，自动把 **时间 / 主机 / 用户 / 命令原文 / 目标类型（编译机|NF 设备）/ 执行结果（退出码、耗时、超时、拦截）/ 会话 owner** 追加写入审计日志：
  `<项目根>/runtime/terminal-monitor/ops.jsonl`（JSONL，每行一条记录）
- 前端每 3s 轮询 `/api/nf-terminal-monitor/list`，侧栏底部「🖥️ 终端命令监控」入口（设置按钮上方，样式与会话管理 footer 按钮一致，带累计条数徽标）点击后弹出**居中模态对话框**；支持过滤：
  - 目标类型：全部 / 编译机 / NF 设备 / 异常
  - 会话 owner：全部会话 / 当前会话（`DSH_SESSION_ID`，宿主缺失时退化为最新活跃会话）/ 各 owner chips
  - 底部 🗑 清空按钮：弹**二次确认对话框**（红色确认按钮，替代 `window.confirm`）确认后清空全部审计日志
- 模态对话框布局（对齐会话管理）：半透明 backdrop + 居中面板（header：标题/累计条数/关闭按钮；body：过滤按钮组 + 会话 chips + 命令列表；footer：清空按钮）；Esc / 点击 backdrop / 关闭按钮均可收起，面板打开期间才轮询
- `ops.jsonl` 不入库（`runtime/` 已在 .gitignore），持续累积作为操作审计留痕

## 结构

```
packages/nf-terminal-monitor/
├── package.json    # name=@nsfocus/nf-terminal-monitor, dsh.client.platform=web, exports["./client"]
├── lib/index.js    # 宿主半体：读 ops.jsonl，服务 /api/nf-terminal-monitor/*（loopback-only，4 路由）
└── client.js       # 浏览器半体：window.__ModuleLoader__.load，侧栏 footer.action 入口 + 模态对话框
```

交互范式（与会话管理 `dsh-session-manager` 一致）：极薄 React 壳注册官方插槽 `sidebar.footer.action`（list 槽位，位于设置按钮上方），宽态渲染「图标 + 文字 + 计数徽标」按钮、rail 折叠态只显示圆形图标；点击后经 React portal 弹出居中模态对话框（backdrop + header/body/footer），内部由纯 DOM 面板填充；危险操作（清空）走自绘二次确认对话框。槽位注册失败时仅 console.error，不做浮动兜底（与会话管理同样策略）。

配套埋点（采集端，改动均在原脚本内追加 import + 调用，异常静默不影响主流程）：

| 发送方 | 埋点位置 | mode |
|--------|---------|------|
| `ssh_batch.py` | 命令循环内，逐条记录 + 结果 | `batch` |
| `ssh_shell.py` | `_run_one`，逐条记录 + 结果 | `shell` |
| `deploy_build.py` | `ssh_connect` 写入连接上下文，`ssh_exec` 逐条记录 | `deploy` |
| 共享模块 | `.dsh/tools/terminal_audit.py`（JSONL 落盘 + 目标类型判定） | — |

目标类型判定：读 `E:\agent_assets\.dsh\env_config\deploy_build\device_config.json#devices[].host` → `nf`；`deploy_config.json#remote_host` → `compile`；其余主机 → `unknown`（env_config 创建基准固定为 `E:\agent_assets`）。

## API

- `GET /api/nf-terminal-monitor/list?limit=50&target=all|nf|compile|unknown&host=IP&owner=session-xxx&errors=1`
  → `{ ok, workspace, logPath, total, items: [{ts, owner, host, port, user, target, mode, cmd, result:{exit,dur,timed_out,error}}] }`（最新在前）
- `GET /api/nf-terminal-monitor/summary` → `{ ok, workspace, total, targets:{nf,compile,unknown}, hosts:{...}, owners:{owner:count}, currentSession, latestOwner, latestTs }`
- `POST /api/nf-terminal-monitor/clear` → 清空 ops.jsonl → `{ ok:true, cleared:n }`（loopback-only，非 POST 405）

## 启用 / 更新

1. 安装到 web profile（已执行过，重装后按需再跑）：
   `dsh plugin --profile web add link:REDACTED_WORKSPACE_PATH/packages/nf-terminal-monitor`
2. 把插件写进启动 patch：`start.bat` / `.dsh/tmp/restart_dsh.bat` /
   `.dsh/.cordis.patch.generated.yml` 都已含 `- id: nf-terminal-monitor, name: '@nsfocus/nf-terminal-monitor'`。
3. 重启 dsh web（关窗重开 / 跑 start.bat / 跑 restart_dsh.bat）。

## 验证

- 采集端：`python .dsh/tools/terminal_audit.py` `record()` 手动插一条，或跑一次 `ssh_batch.py`/`ssh_shell.py`（对任意可达主机），确认 `runtime/terminal-monitor/ops.jsonl` 新增行
- API：`curl http://127.0.0.1:3080/api/nf-terminal-monitor/list` → `{ ok:true, items:[...] }`
- UI：左侧面板底部（设置按钮上方）出现「🖥️ 终端命令监控」入口（带条数徽标），点击弹出**居中模态对话框**（半透明 backdrop），header 显示标题/条数/关闭，body 为过滤按钮组 + 会话 chips + 命令列表，footer 为清空按钮；Esc / 点击 backdrop / 点击关闭按钮均可收起；点清空弹二次确认对话框，确认后清空审计日志；侧栏折叠为 rail 时入口仅显示圆形图标按钮

## 备注

- 后端工作区定位：从 web 进程 cwd 向上找含 `.dsh` 的目录，找不到回落 `process.cwd()`。
- 前端失败策略：挂载/请求失败只 console.error，绝不拖垮 Web shell；槽位注册失败不浮动兜底（与会话管理一致）。
- 前端布局参照：`dsh-session-manager`（会话管理）的按钮 + 模态对话框范式（入口按钮、backdrop、header/body/footer、二次确认对话框）。
- 数据安全：审计日志含命令原文（可能含路径/关键参数），只供本机回看，`runtime/` 不入库不推送。