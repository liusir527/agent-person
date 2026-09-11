---
name: vpp-api-sync
description: "VPP *.api 文件改动后的 api.json 自动暂存移交。当本次代码修改涉及 VPP 插件 `*.api` 文件（vpp 与 vpp-agent 的 biapi 消息格式变化）时，编译通过后自动把编译机 build-root/install-<ARCH>/vpp/share/vpp/api/plugins/ 下生成的 `*.api.json` 下载到本地 runtime/<SESS>/ 暂存，供 vpp-agent 开发人员同步源码。触发词：*.api、api文件、biapi、api.json、vpp-agent、pbr.api、acl.api、api格式变化。用户不可手动触发（user-invocable: false），由模型按触发条件自动执行。"
scene: debug
user-invocable: false
---

# VPP api.json 自动暂存移交（vpp-api-sync）

## 触发条件（模型自动命中，用户不可手动触发）

当本次代码修改涉及 **VPP 插件的 `*.api` 文件**（路径形如 `src/plugins/<模块>/<模块>.api`）时，即
**vpp ↔ vpp-agent 的 biapi 消息格式发生变化**，本技能自动启用：

- 本次改动新增/修改/删除了任意 `*.api` 文件中的类型、消息、字段
- 对应 vpp-agent 源码需要同步更新（由 vpp-agent 开发人员完成，本技能只负责移交输入物）

## 为什么需要

`*.api` 是 VPP 插件对外二进制 API（biapi）的消息定义。编译时 VPP 会生成：

- C 头文件（`<模块>.api_types.h` / `<模块>.api.h`），vpp 侧与 vpp-agent 侧共用
- **`*.api.json`**：机器可读的 API 完整描述，位于编译机 worktree 的
  `<worktree>/build-root/install-<ARCH>/vpp/share/vpp/api/plugins/<模块>.api.json`

vpp-agent 依赖 `*.api.json` 同步其 biapi 编解码实现。因此每次 `*.api` 改动**编译通过后**，
必须把新生成的 `*.api.json` 下载到本地暂存，移交 vpp-agent 开发人员；否则 vpp-agent 侧消息格式不匹配。

## 暂存目录约定（路径锚定，以项目根为基准）

```
<项目根>/runtime/<SESS>/<模块>.api.json
```

- `<项目根>` = `PROJECT_ROOT`（脚本内由 `__file__` 上溯推导得到，等价于本 skill 所在仓库根，**不相对当前工作目录**）
- `runtime/` 已登记为运行时目录（`.dsh/rules/dirs.json`），git 不追踪，由 AGENT 自行管理
- **SESS = 当前会话核心名称** = 环境变量 `DSH_SESSION_ID` 的值（主会话形如 `session-<uuid>`，
  子会话可能为裸 `<uuid>`，以实际值为准），用于隔离多会话并发时的同名文件冲突；可用 `--sess` 覆盖
- `<模块>` = `*.api` 源文件基名去后缀，如 `src/plugins/pbr/pbr.api` → `pbr.api.json`

## 执行步骤

1. **先确认编译通过**（编译由 deploy-build skill 完成，本技能只做下载暂存；
   若 api.json 还是旧版/旧 mtime，说明编译未通过或未重新生成）
2. 运行辅助脚本（推荐，自动识别改动；本机 Windows 用 `python`，`python3` 是 WindowsApps
   商店占位符不可用）：
   ```bash
   python "<技能目录>/sync_api_json.py" --remote-worktree-name <编译机worktree名>
   ```
   ⚠️ `--remote-worktree-name` 必须与本次 deploy-build 的 `--worktree` 名一致（如 `fix-NEWNF-54398`）；
   本地 worktree 常 checkout 在 release 分支、修复提交叠其上，本地分支名≠远端 worktree 名，
   **不可省略**（缺省且本地分支为 release/master/main 时脚本会硬失败）。基线会自动用 merge-base
   精确隔离本次改动。
   脚本自动完成：识别本地 npp worktree 中改动的 `*.api` → 映射到编译机 worktree 的
   `build-root/install-<ARCH>/vpp/share/vpp/api/plugins/<模块>.api.json`（核心 .api 映射到
   `vpp/share/vpp/api/` 根）→ SFTP 下载到 `<项目根>/runtime/<SESS>/`。其余参数均可覆盖
   （`--api-file --local-dir --base --remote-host --remote-port --remote-user --remote-base
   --arch --out-root --sess --expect-field --dry-run`）。
3. 也可显式指定模块：
   ```bash
   python "<技能目录>/sync_api_json.py" --api-file src/plugins/pbr/pbr.api \
     --remote-worktree-name fix-NEWNF-54398
   ```
4. **自检暂存结果（推荐 `--expect-field`）**：下载后自动校验暂存 api.json 包含本次新增字段，
   未命中则非零退出（提示"编译未通过/未重新生成"），防止把旧版 api.json 移交给 vpp-agent：
   ```bash
   python "<技能目录>/sync_api_json.py" --remote-worktree-name fix-NEWNF-54398 \
     --expect-field activate_egress_intf_list
   ```
   也可人工核对：`grep -n "activate_egress_intf_list" "<项目根>/runtime/<SESS>/pbr.api.json"`

> 连接默认值（编译机 `liuxing5@10.66.240.3:50222`、`packet-nf`、`x86_64`）为本项目/本机专用；
> 其他环境请用 `--remote-*`/`--arch` 覆盖。密码从 `<workspace_root>/.dsh/env_config/deploy_build/deploy_config.json` 的
> `remote_pass` 读取（`workspace_root` 由 `_resolve_workspace_root()` 解析；该目录不入库），或经环境变量 `DEPLOY_BUILD_REMOTE_PASS`/`SSH_PASSWORD` 注入；
> 不通过 CLI 传递。

## 移交说明

- 暂存目录 `runtime/<SESS>/` 内的 `*.api.json` 即为移交 vpp-agent 开发人员的输入物
- vpp-agent 根目录：`F:/software/NF605/system-management/npp-agent`（已在 `.dsh/rules/dirs.json` 登记）
- 多会话并发时各自暂存到自己的 `<SESS>/` 子目录互不覆盖；任务结束后 SESS 目录保留即可（runtime 不入库）

## 常见坑

| 坑 | 表现 | 避坑 |
|----|------|------|
| 未编译就下载 | api.json 还是旧版，不含新字段 | 必须先确认编译通过、api.json mtime 为本次构建时间 |
| 目标目录写错 | 下载到任意目录 | 以 `<项目根>/runtime/<SESS>/` 锚定，禁止相对当前目录 |
| 多会话覆盖 | 两个会话写同一文件 | SESS 用 `DSH_SESSION_ID`，天然隔离 |
| api.json 定位不到 | 模块名/ARCH 不对 | 先 `ls <worktree>/build-root/install-*/vpp/share/vpp/api/plugins/*.api.json` 确认 |
