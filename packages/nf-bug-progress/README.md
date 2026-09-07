# @nsfocus/nf-bug-progress

NF BUG 修复工作流**进度面板**插件：在 DSH Web GUI 对话页面右下角浮动展示状态机进度。

## 功能

- 每 4s 轮询 `/api/nf-bug-progress/list`，把最新的「进行中 BUG」（`bug-fix-state/*/state.json` 中 `main_state != 结束`）渲染到面板；
- 面板表头显示 `🛠 <BUG单号> · x/7 · 主状态 · 微观状态`，点击展开完整流水线（7 个主状态 ✓/▶/○ + 当前微观状态 + 门禁通过数 + 审查轮次）；
- 阶段切换时表头闪一下，所有进行中 BUG 以 chips 展示在展开区。

## 结构

```
packages/nf-bug-progress/
├── package.json    # name=@nsfocus/nf-bug-progress, dsh.client.platform=web, exports["./client"]
├── lib/index.js    # 宿主半体：读取 bug-fix-state，服务 /api/nf-bug-progress/*（loopback-only）
└── client.js       # 浏览器半体：window.__ModuleLoader__.load 格式，纯 DOM 浮动面板
```

状态机 schema（MAIN_STATES/MICRO_STATES/GATES）在 `lib/index.js` 里静态复制自
`.dsh/skills/bug-fix-workflow/state_machine.py`，改状态机时需同步这里。

## 启用 / 更新

1. 安装到 web profile（已执行过，重装后按需再跑）：
   `dsh plugin --profile web add link:$(git rev-parse --show-toplevel)/packages/nf-bug-progress`
2. 把插件写进启动 patch：`start.bat` / `.dsh/tmp/restart_dsh.bat` /
   `.dsh/.cordis.patch.generated.yml` 都已含
   `- id: nf-bug-progress, name: '@nsfocus/nf-bug-progress'`。
3. 重启 dsh web（关窗重开 / 跑 start.bat / 跑 restart_dsh.bat）。

## 验证

- API：`GET http://127.0.0.1:3080/api/nf-bug-progress/list` → `{ ok, workspace, schema, items }`；
- UI：对话页右下角出现面板；`bug-fix-state` 下新建状态机后自动显示进度并随状态推进刷新。

## 备注

- 后端工作区定位：从 web 进程 cwd 向上找含 `bug-fix-state` 的目录，找不到则回落 `process.cwd()`。
- 前端失败策略：挂载/请求失败只 console.error，绝不拖垮 Web shell。
