---
name: deploy-build
user-invocable: true
description: "增量部署编译NPP项目：worktree 派生隔离 → filesync 同步本地改动到远端 → 多模式 nsbuild-git 编译 → CMake 反向依赖图扫描 → 从 .nsbuild/install/edisk 精确推送目标设备。支持 sync/build/install/diff/status 等模式"
scene: develop
allowed-tools:
  - Bash(python3 *deploy_build.py *)
---

# 增量部署编译 NPP 项目

根据用户请求，运行 deploy_build.py 脚本，按 **worktree 工作区设计** 完成「派生 → 同步 → 编译 → 安装」闭环：

1. **worktree 派生**（`--worktree <名>`）：编译机上基于 NPP_BASE 的 npp 仓库切到基线分支，`git worktree add ../<名>` 派生隔离工作区，编译、产物、扫描均在 worktree 内进行，与原 npp 仓库隔离。
2. **filesync**：将本地改动文件同步到远端 worktree 目录（SFTP 同步/删除）。
3. **编译**：`nsbuild-git -d/-b/-i/-di/-bi/-c` 多模式。
4. **扫描+安装**：CMake 反向依赖图扫描定位受影响产物，从 `.nsbuild/install/edisk` 按 `nsfocus/→/opt/nsfocus`、`root/→/root` 映射推送到目标设备并重启服务。

## 工作区设计（编译机目录布局）

```
packet-nf/
├── npp            # 原始仓库（NPP_BASE），仅用于派生 worktree
└── fix-NEWNF-12345  # worktree 工作区（git worktree add ../{名} 派生）
```

`git worktree add ../{XX}` 在 NPP_BASE 的兄弟目录创建 worktree（如 `packet-nf/fix-NEWNF-12345`），复用源码、实现隔离。

## 用户请求

$ARGUMENTS

## 编译操作必须走 tmux（强制）

对编译机的一切命令操作（worktree 派生、`nsbuild-git` 编译/打包、`cmake_target_scan.py` 扫描、
`--status` 状态检查等）**必须**在编译机上的 tmux 会话内执行：

- 会话命名 **`fix-<BUG单号>`**（与 fix 分支 / worktree 同名，如 `fix-NEWNF-54405`；无 BUG 单号用
  `bd_<任务名>` 兜底）；**`tmux new-session -A -d -s fix-<BUG单号>` 一条命令完成"有则复用、无则新建"**
  （`-d` 不挂载不阻塞；禁止 `-D` / `attach -d` 踢人），命名不符/多候选时先 `tmux ls` 列结果询问用户再动手；
- **长时构建（`nsbuild-git -d/-di/-b/-i`、全量编译）必须在 tmux 内跑**：tmux 会话不随 SSH 通道关闭
  终止，根治「后台构建被杀」，也不受本脚本 540s 通道超时限制；构建期间 `tmux capture-pane -p -S -`
  定期读进度，结束后核对 `exit` 结果再继续；
- **操作开始前告知用户**：会话名 + 查看方式（`ssh` 登录编译机后 `tmux attach -t fix-<BUG单号>`，
  绝不用 `attach -d` 踢人）；
- 约定：编译机用 tmux、NF 设备用 screen，标准见 [../ssh-tools/SKILL.md](../ssh-tools/SKILL.md)。

## 配置流程

首次使用时（无配置文件），需要收集连接参数并**让用户确认后**才保存。

### 步骤 1：检查配置文件

检查是否存在配置文件 `<workspace_root>/.dsh/env_config/deploy_build/deploy_config.json`（env_config 创建基准为 `AGENT_ASSETS_DIR`，缺省通过 git 探测定位当前仓库根，环境变量可覆盖；详见 `deploy_build.py` 顶部的 `_resolve_workspace_root()`）。

如果已有配置文件，直接跳到"执行操作"步骤。

### 步骤 2：收集参数

向用户询问以下连接参数（如用户一次性提供了，直接整理）：

1. **编译服务器**: 地址、SSH端口、用户名、远端NPP代码仓库基地址（NPP_BASE，如 `/home/liuxing5/newnf-605-master/packet-nf/npp`）
   - ⚠️ **只有编译机地址/端口有默认值**（`10.66.240.3:50222`）；用户名、NPP_BASE **无默认**，必须由用户提供
2. **目标设备**（可多台）: 每台的描述（`NF-{DESC}` 或 `NF{NUM}`）、地址、SSH端口、用户名（**无默认**，需用户提供；纯编译不同步设备时可不提供）
3. **基线分支**: worktree 派生基准（**无默认**——优先从本地 npp 的 git 读取当前分支，读不到则询问用户指定；严禁默认 `master`）
4. **重启服务名**: 设备上 NPP 服务名（**无默认**，需用户提供，如实测为 `pss-npp` 则填该值）

**密码直接保存到 env_config 配置文件**（`.dsh/env_config/` 已被 gitignore 忽略、不入库，不会进 GitHub）：
- `deploy_config.json` 的 `remote_pass`：编译服务器 SSH 密码
- `device_config.json` 的 `devices[].pass`：目标设备 SSH 密码（多台设备共用时每台填写）
- 环境变量 `DEPLOY_BUILD_REMOTE_PASS` / `DEPLOY_BUILD_DEVICE_PASS` 作为覆盖源（优先级高于配置文件）

### 步骤 3：用户确认（必须）

将收集到的参数整理成表格，使用 AskUserQuestion 让用户确认。示例格式：

| 项目         | 值                                                           |
| ------------ | ------------------------------------------------------------ |
| 编译服务器   | liuxing5@10.66.240.3:50222                                   |
| 远端NPP_BASE | /home/liuxing5/newnf-605-master/packet-nf/npp                |
| 目标设备     | NF-1: develop@10.66.23.115:30022                             |
| 基线分支     | （本地 npp 当前分支 / 用户指定）                             |
| 重启服务     | （用户指定，如实测 pss-npp 填该值）                          |
| 密码存储 | env_config 配置文件（不入库）：`deploy_config.json#remote_pass` / `device_config.json#devices[].pass`（环境变量可覆盖） |

用户确认无误后才保存配置。如果用户指出错误，修正后重新确认。

### 步骤 4：保存配置

确认后使用 `--save-config` 保存配置（**含密码字段**，存于不入库的 `env_config/`）：
```bash
export DEPLOY_BUILD_REMOTE_PASS='<编译服务器密码>'
export DEPLOY_BUILD_DEVICE_PASS='<设备密码>'

python3 "$SKILL_DIR/deploy_build.py" --save-config \
  --remote-host <地址> --remote-port <端口> --remote-user <用户> --remote-dir <NPP_BASE> \
  --device-host <地址> --device-port <端口> --device-user <用户>
```

配置将保存到 `<workspace_root>/.dsh/env_config/deploy_build/deploy_config.json`（编译服务器）+ `device_config.json`（目标设备，`devices` 数组，支持多台）。日志和同步清单也统一在该目录下管理。

**配置加载优先级**（高到低）：CLI 参数 → 环境变量 → 配置文件 → 默认值。**默认值仅限编译机地址 `10.66.240.3` 与端口 `50222`**，其余字段（编译机用户名/NPP_BASE/设备信息/基线分支/重启服务名）均无默认——未从 CLI 或配置文件取得时，脚本会交互询问补齐，绝不带默认值继续。密码保存在配置文件（`remote_pass` / `device_pass` 字段），运行时直接读取，也可用环境变量覆盖。

**注意**：所有 Linux 路径参数（`--remote-dir` 等）会被 Git Bash 自动转换为 Windows 路径。脚本内置了 `fix_msys_path()` 函数自动还原，无需手动处理。

## 执行操作

配置保存后（或已有配置文件时），根据 `$ARGUMENTS` 判断用户意图，选择对应的命令模式。如果参数为空，询问用户需要哪种操作。

所有命令都使用脚本绝对路径执行，**Bash 工具必须设置 `timeout=600000`**（`ssh_exec` 内部编译超时为 540s，需预留 ≥60s 余量）：
```bash
export DEPLOY_BUILD_REMOTE_PASS='<编译服务器密码>'
export DEPLOY_BUILD_DEVICE_PASS='<设备密码>'

python3 "$SKILL_DIR/deploy_build.py" <模式参数>
```

进行编译时，因为build动作会产生非常多的日志，所以需要使用**grep**操作，只过滤**error**相关的日志信息。

```shell
nsbuild-git -d | grep -i -E "error|fatal" -A 10 -B 10 # 通过这种方式能压缩token消耗,只关心编译出错的信息
```

### 可用模式

| 模式           | 命令                             | 说明                                                         |
| -------------- | -------------------------------- | ------------------------------------------------------------ |
| worktree 派生  | `--worktree <名>`                | 编译机 npp 切基线分支 + `git worktree add ../<名>`，后续操作在 worktree 内 |
| 同步+编译      | `--build`                        | 默认完整流程：同步→**CMake**扫描→精确编译                    |
| 只同步         | `--sync-only`                    | 仅同步文件到远端                                             |
| 只编译         | `--build-only`                   | 仅编译（不同步）                                             |
| 编译模式       | `--mode <d\|b\|i\|di\|bi\|c>`    | `nsbuild-git` 模式：d=debug、b=release、i=release 编译+安装、**di=debug 编译+安装（默认，上机验证一律用它）**、bi=release 编译+安装、c=清理 |
| 同步+编译+安装 | `--build --install`              | 编译后从 edisk 推送目标设备                                  |
| 只安装         | `--install-only`                 | 仅推送（不编译，依赖已有 edisk 产物）                        |
| 安装指定文件   | `--install-only --files <列表>`  | 在 edisk 中按文件名定位后推送                                |
| 全量安装       | `--install-full`                 | edisk 全量推送                                               |
| 目标设备       | `--device <desc>`                | 指定推送设备（`NF-1` 等），默认推送全部设备                  |
| 只看差异       | `--diff-only`                    | 查看本地与基线的差异                                         |
| 远端状态       | `--status`                       | 查看远端编译服务器状态                                       |
| 清理编译       | `--clean`                        | 执行 `nsbuild-git -c` 清理                                   |
| 安装不重启     | `--build --install --no-restart` | 推送后不重启服务                                             |
| 自定义基线     | `--build --base <分支>`          | 指定对比/派生基线分支                                        |
| 重启服务名     | `--restart-service <名>`         | 指定设备重启服务名（无默认，需用户提供）                     |
| 预览（不执行） | `--dry-run`                      | 打印计划操作，不连接 SSH                                     |
| 只扫描         | `--scan-only`                    | 仅执行 CMake 反向依赖图扫描，不编译                          |

> ⚠️ **编译模式铁律（教训：NEWNF-54405）**：上机验证/日常安装**一律用 `-di`（debug 编译+安装）**，`deploy_build.py
> 带 --install 且不写 --mode 时默认就是 di，**不要手动绕过脚本在编译机裸跑 `nsbuild-git -i`**——`-i` 是
> release（-O2）全量编译，耗时 25min+（nAclNode.c 两个变体各 10min+），debug 编译显著更快且功能一致。
> 只有明确需要发布级产物（交付/压测）时才用 `-bi`/`-i`。需要重编 debug 产物时：`--build-only --mode di`。

### 典型调用

```bash
# BUG 修复：派生 worktree → 同步改动 → debug 编译打包 → 精确推送到 NF-1 并重启
python3 "$SKILL_DIR/deploy_build.py" --worktree fix-NEWNF-12345 --build --install --device NF-1

# 编译已有 worktree（不重复派生）
python3 "$SKILL_DIR/deploy_build.py" --worktree fix-NEWNF-12345 --build-only --mode di

# release 编译打包后全量推全部设备
python3 "$SKILL_DIR/deploy_build.py" --worktree fix-NEWNF-12345 --build --mode bi --install-full
```

### CMake 反向依赖图工作原理

`--build` 模式（默认）的工作流程：

1. **同步**：将改动文件通过 SFTP 同步到远端 worktree 目录
2. **扫描**：在远端编译机上执行 `cmake_target_scan.py`，基于反向依赖图（CMakeCache.txt + build.make + Depends/ + link.txt + cmake_install.cmake）做 BFS 传递闭包
3. **精确编译**：仅编译受影响目标（直接受影响 + 传递依赖目标）
4. **精确安装**：从 `.nsbuild/install/edisk` 定位受影响产物的相对路径，按 `nsfocus/→/opt/nsfocus`、`root/→/root` 映射到设备绝对路径，仅推送必要产物

与旧的全量编译相比，可将编译时间从数十分钟缩短到数分钟。

## 安装说明（edisk 产物）

设计约定：执行 `nsbuild-git -i`（含 `-di`/`-bi`）后，产物落在 worktree 的 `nf/.nsbuild/install/edisk` 目录，该目录**镜像设备根文件系统**：

| edisk 前缀    | 设备映射           |
| ------------- | ------------------ |
| `nsfocus/...` | `/opt/nsfocus/...` |
| `root/...`    | `/root/...`        |

推送前先通过 CMake 扫描/全量/指定文件三种方式确定产物，再按上表映射，`scp` 到每台目标设备对应路径。

**服务重启**：替换完成后执行 `systemctl daemon-reload && systemctl restart <restart_service>`。服务名**无默认**，由用户提供（如实测设备为 `pss-npp`，用 `--restart-service pss-npp` 指定）。

## install.sh 安全说明

`remote_install` 生成的 `install.sh` **不包含明文密码**：设备密码由 deploy_build.py 从配置文件
`device_config.json#devices[].pass`（或环境变量 `DEPLOY_BUILD_DEVICE_PASS`）读取后，仅在远端 shell 的
环境变量中注入使用，**不落盘到设备**；未提供时运行时交互式输入。

## 执行后

1. 向用户报告结果，包括日志文件路径（位于 `<workspace_root>/.dsh/env_config/deploy_build/logs/deploy.log`，每次运行覆盖，只保留最新）。
2. 如编译失败，分析错误输出并协助诊断。
3. 如安装失败遇到 "Text file busy"，提示用户先停止设备上 NPP 服务后再重新推送。
4. 如用户希望预览计划操作而不实际执行，使用 `--dry-run`。
