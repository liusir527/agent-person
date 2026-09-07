---
name: ssh-tools
description: "Windows 平台的轻量 SSH 工具：批量/交互式执行远端命令，支持自定义端口、用户名、密码。当需要 SSH 登录服务器（批量命令、退出码）或网络设备（VPP、Cisco、华为等交互式 CLI）执行命令时使用。"
user-invocable: true
allowed-tools:
  - Bash(python *)
  - Read
---

# SSH 远程执行（ssh-tools）

仅依赖已安装的 paramiko（纯 Python），不修改系统配置、不引入 sshpass/plink 等外部工具。
Windows 控制台编码已处理（UTF-8 输出，避免 GBK 乱码）。

## 场景选择

| 场景                                       | 工具           | 模式                                        |
| ------------------------------------------ | -------------- | ------------------------------------------- |
| 服务器批量执行，需要每条命令的退出码       | `ssh_batch.py` | `--commands` / `--commands-file`，JSON 输出 |
| 网络设备交互式 CLI（VPP / Cisco / 华为等） | `ssh_shell.py` | PTY 会话，发命令→等提示符→输出              |
| 只发一条命令                               | `ssh_shell.py` | `--oneshot "命令"`                          |
| 逐步操作（先看输出再决定下一条）           | `ssh_shell.py` | 从 stdin 逐行读命令（管道/AI 驱动）         |
| 多条命令按序执行（设备场景）               | `ssh_shell.py` | `--script 文件`（每行一条，# 注释行跳过）   |

> 网络设备通常没有 exec 通道（`ssh_batch.py` 会失败），一律用 `ssh_shell.py`；
> 服务器两种都能用，要退出码用 `ssh_batch.py`。

## 终端操作留痕规则（总览）

| 目标 | 强制工具 | 会话命名 | 详见 |
|------|---------|---------|------|
| NF 设备（CLI / vppctl / GDB / 调试） | screen | `nf_<设备>` | 下方「NF 设备操作标准」 |
| 编译机（NPP 编译 / 扫描 / 状态检查） | tmux | `fix-<BUG单号>` | 下方「编译机操作标准」 |
| 普通服务器 | 不强制（有旁路需求可选 tmux） | — | — |

## NF 设备操作标准（强制：一律走 screen）

> **硬规则**：对 NF 设备（VPP CLI、Linux shell、k3s、GDB 等）做任何 SSH 命令操作时，
> **必须**先在设备上建立（或复用）一个 **screen 会话**，全部命令都在该会话内执行并保留现场，
> 使用户可以实时查看 agent 的每一步操作。此规则为工作区级硬规则（见 [../../AGENT.md](../../AGENT.md)）。
> 例外：deploy-build 的纯自动化批量推送（scp 式 install）不强制；但推送后的确认、服务状态检查等
> 交互命令仍走 screen。

### 会话命名

统一命名 `nf_<设备IP或别名>`，例如 `nf_10.66.23.115`；GDB 场景为 `nf_<设备>-gdb`。
会话名不含空格、冒号、斜杠。

### 标准动作序列

```bash
# 1) 检查已有会话（先看 Attached / Detached 状态）
screen -ls

# 2) 复用规则（用户先建好的会话必须复用，绝不重复创建）：
#    - 找到命名符合约定（nf_<host> 或 nf_<host>-gdb）的会话 →
#      用户正挂着(Attached)用 screen -x，游离(Detached)用 screen -r 挂入
#    - 会话名不符约定 / 有多个候选分不清 → 把 screen -ls 结果列给用户，
#      明确询问用哪个会话，不得猜名、不得新建
#    - 完全没有会话 → 才创建（detached 后台起一个 shell）
screen -dmS nf_<host> bash

# 3) 向用户通报（每条回复都必须写明）：会话名 + 查看方式
#    ssh <user>@<host> 后执行：
#      screen -x nf_<host>   # 会话被挂载(Attached)时
#      screen -r nf_<host>   # 会话游离(Detached)时

# 4) 下发命令（二选一）
#    注入式：单条命令，不改变自身挂载状态
screen -S nf_<host> -X stuff 'vppctl\n'
#    读回输出：hardcopy 落盘 + cat
screen -S nf_<host> -X hardcopy /tmp/nf_<host>.out; cat /tmp/nf_<host>.out

#    挂载式：连续交互（vppcli / gdb / 逐步操作）时把本会话 PTY 挂进共享屏幕
screen -r nf_<host>        # Attached 时用 screen -x
#    之后所有命令直接在共享屏幕里执行，用户同步可见

# 5) 收尾：会话默认保留供用户回看；需清理时
screen -S nf_<host> -X quit
```

### 纪律

1. **先 `screen -ls` 再动手**：**用户先建好的会话必须复用**——Attached 用 `-x`、Detached 用 `-r` 挂入，绝不静默重复创建；会话名不符约定或存在多个候选时，列出结果询问用户用哪个，不得猜名。
2. **每条命令都要落在 screen 内**：不允许在裸 PTY 上对设备发命令——包括只读查询
   （如 `cat /opt/nsfocus/etc/version.txt`）——确保用户可全程旁观。
3. **共享屏幕输入互通**：用户可能在同时输入；发命令前先观察屏幕状态，一次一条、间隔确认输出。
4. **操作开始前必报**：在对话回复中告知用户「会话名 + `ssh` 后 `screen -x/-r` 查看方式」。
5. **解析注意**：挂载/读回输出可能带 `[H[J` 重绘控制码，过滤后再解读（见
   [../../references/screen使用经验.md](../../references/screen使用经验.md)）。
6. **设备无 screen**：极少数设备缺 screen 时先尝试 `screen --version` 确认，确实没有则告知用户
   并改用其他可旁观方式（如 tee 落盘留痕）后再操作，不得静默裸跑。

## 编译机操作标准（强制：一律走 tmux）

> **硬规则**：对编译服务器（如 `liuxing5@10.66.240.3:50222`，NPP 编译 / 扫描 / 安装中转）做命令操作时，
> **必须**在编译机上的 **tmux 会话**内执行。编译机用 tmux、NF 设备用 screen，是两类目标的固定约定
> （见上方总览表）。此规则为工作区级硬规则（见 [../../AGENT.md](../../AGENT.md)）。
> 例外：纯文件传输（SFTP 同步、scp 推送、api.json 下载）不强制；但传输后的确认、编译、状态检查等
> 命令仍走 tmux。

### 会话命名

统一命名 **`fix-<BUG单号>`**（与 fix 分支 / worktree 同名，便于按单追溯），如 `fix-NEWNF-54405`；
无 BUG 单号的临时任务用 `bd_<任务名>` 兜底。会话名不含空格、冒号。

### 标准动作序列

```bash
# 1) 确保会话存在——一条命令完成"有则复用、无则新建"：
#    ⚠️ tmux new-session 必需 PTY：用 exec 通道（ssh_batch.py）会报
#    "open terminal failed: not a terminal"；必须走 ssh_shell.py（PTY）
#    ⚠️ ls / send-keys / capture-pane 用 exec 通道即可（ssh_batch.py --commands-file
#    实测可用；命令文件方式还能避开本机 shell 的引号转义问题）
#    -A -d 组合：会话名已存在 → 直接复用；不存在 → detached 后台新建，均不挂载、不阻塞
tmux new-session -A -d -s fix-<BUG单号>
#     ⚠️ 小写 -d 是"不挂载"；大写 -D 才是踢人（等同 attach -d），禁用！
#     会话名不符约定 / 有多个候选 → 先 tmux ls 列结果询问用户，确认会话名后再用 -A，
#     不得猜名、不得随便新建

# 2) 先观察再动手（共享终端，允许用户同时挂着）
tmux ls                          # 看会话状态（谁在挂 / 几个客户端）
tmux capture-pane -t fix-<BUG单号> -p -S -     # 看当前画面，别把命令拼到用户输入后面

# 3) 向用户通报（每条回复都必须写明）：会话名 + 查看方式
#    ssh <user>@<编译机> 后执行 tmux attach -t fix-<BUG单号>
#    （用户交互终端也可用 tmux new-session -A -s fix-<BUG单号>：有则挂入、无则新建并挂入）

# 4) 下发命令（注入式为主，读回用 capture-pane）
tmux send-keys -t fix-<BUG单号> 'nsbuild-git -d | grep -i error' Enter
tmux capture-pane -t fix-<BUG单号> -p -S -     # -S - 取整个滚动缓冲，比可见区域更全

# 5) 收尾：构建中的会话默认保留供用户盯进度/回看；需清理时
tmux kill-session -t fix-<BUG单号>
```

### 纪律

1. **`tmux new-session -A -d -s fix-<BUG单号>` 一条搞定复用/新建**：会话名已存在直接复用（不挂载、不踢人），
   不存在则 detached 新建；**会话名不符约定 / 有多个候选时，先 `tmux ls` 列结果询问用户，确认会话名后
   再用 -A，不得猜名、不得随便新建**。
2. **长时构建必须在 tmux 里跑**（`nsbuild-git -d/-di/-b/-i`、全量编译、`cmake_target_scan.py` 等）：
   tmux 会话不随 SSH 通道关闭而终止——根治「后台构建被 SSH 断开杀死」（见
   [../../references/稀疏经验/deploy_build_worktree编译避坑-20260825.md](../../references/稀疏经验/deploy_build_worktree编译避坑-20260825.md) 坑3），
   也不受 deploy_build 内部 540s 通道超时限制；构建期间定期 `capture-pane` 读进度。
3. **每条命令都落在 tmux 内**，包括只读检查（`--status`、`ps`、`tail` 日志）。
4. **操作开始前必报**：在对话回复中告知用户「会话名 + `ssh` 后 `tmux attach -t fix-<BUG单号>` 查看方式」。
5. **禁止踢人**：`tmux attach -d` 与 `new-session -A -D` 都会强制断开其他客户端（把用户挤下线），一律禁用；
   只允许用 `-d`（小写，不挂载）。
6. **解析注意**：`capture-pane` 输出含状态行 / 控制码，过滤后再解读（经验见
   [../../references/tmux使用经验.md](../../references/tmux使用经验.md)）。
7. **编译机无 tmux**：先 `tmux -V` 确认；确实没有则告知用户安装后继续，或经用户同意改用 screen
   兜底，不得静默裸跑。

```
.dsh/skills/ssh-tools/
├── SKILL.md
├── scripts/
│   ├── ssh_batch.py    # 批量执行（exec_command，JSON 输出）
│   └── ssh_shell.py    # 交互式（invoke_shell PTY，提示符等待）
└── tests/
    └── test_ssh_skills.py   # 本地自检（起 paramiko 测试 SSH 服务，无需真实设备）
```

在项目根目录以 `python .dsh/skills/ssh-tools/scripts/ssh_batch.py ...` 调用。

## 快速开始

```bash
# 批量执行两条命令（密码直接传）
python .dsh/skills/ssh-tools/scripts/ssh_batch.py \
    --host 192.168.1.10 --port 22 --user admin --password 'p@ss' \
    --commands "uname -a" "df -h"

# 命令写入文件（每行一条，支持 # 注释）
python .dsh/skills/ssh-tools/scripts/ssh_batch.py \
    --host 192.168.1.10 --user admin --commands-file cmds.txt

# 网络设备交互式：单发一条
python .dsh/skills/ssh-tools/scripts/ssh_shell.py \
    --host 192.168.1.10 --user admin --password 'p@ss' \
    --oneshot "show version"

# 网络设备按序执行多条
python .dsh/skills/ssh-tools/scripts/ssh_shell.py \
    --host 192.168.1.10 --user admin --password 'p@ss' --script cmds.txt

# 管道驱动逐步交互（每条命令等提示符返回后再发下一条）
echo "show interfaces\nexit" | python .dsh/skills/ssh-tools/scripts/ssh_shell.py \
    --host 192.168.1.10 --user admin --password 'p@ss'
```

## 输出格式

**ssh_batch.py** — stdout 输出单个 JSON 文档：

```json
{
  "host": "192.168.1.10", "port": 22, "user": "admin",
  "ok": false,
  "commands": [
    {"cmd": "uname -a", "exit_status": 0, "stdout": "Linux ...", "stderr": "", "timed_out": false}
  ]
}
```

退出码：全部成功 0 / 任一命令失败 1 / 连接或参数错误 2。

**ssh_shell.py** — 每条命令带标记，便于解析：

```
=== SEND: show version ===
vpp v23.10-rc0~g1234567 built by root
=== DONE (0.42s) ===
```

标记含义：`DONE` 正常 / `TIMEOUT` 超时（输出可能不完整）/ `CHANNEL CLOSED` 远端会话结束。

## 参数说明

| 参数                           | 默认                              | 说明                                            |
| ------------------------------ | --------------------------------- | ----------------------------------------------- |
| `--host`                       | 必填                              | 目标 IP/域名                                    |
| `--port`                       | 22                                | SSH 端口                                        |
| `--user` / `--password`        | 必填                              | 用户名/密码；密码也可用环境变量 `SSH_PASSWORD` 或从 env_config 配置文件读取（`E:\agent_assets\.dsh\env_config\`） |
| `--timeout`                    | batch 30 / shell 10               | 命令/等待提示符超时（秒）                       |
| `--connect-timeout`            | 15                                | 连接与认证超时（秒）                            |
| `--encoding`                   | utf-8                             | 远端输出解码编码                                |
| `--known-hosts`                | 无                                | 主机密钥文件；不指定时自动信任并提示风险        |
| `--commands-file` / `--script` | 无                                | 命令文件（UTF-8，每行一条，# 注释跳过）         |
| `--prompt`                     | `(?:^\|[\r\n])[^\r\n]*[>#$%]\s*$` | 提示符正则（仅 shell）                          |
| `--eol`                        | `\n`                              | 命令行尾符（仅 shell；老设备用 `\r` 或 `\r\n`） |
| `--width/--height`             | 200/50                            | PTY 尺寸（仅 shell，宽终端防换行截断）          |
| `--allow-cross-layer`          | 关闭                              | 显式放行跨层源码路径命令（`/opt/nsfocus/product/web|agent|system`）；**默认一律拒绝**（任务边界硬拦截，教训源自 NEWNF-54251），仅经用户确认后使用 |

## 注意事项

1. **密码来源**：优先从 env_config 配置文件读取（`E:\agent_assets\.dsh\env_config\`，如 `deploy_build/deploy_config.json#remote_pass`、`device_config.json#devices[].pass`，该目录不入库）；也可 `set SSH_PASSWORD=p@ss` 环境变量注入；避免在 `--password` 参数里传明文（命令行对同机其他进程可见）。
2. **设备分页**：输出出现 `--More--` 时先发关闭分页命令（Cisco：`terminal length 0`，华为：`screen-length 0 temporary`）。
3. **提示符不匹配**：登录后看到 `警告: 登录后未检测到提示符` 时，用 `--prompt` 指定该设备提示符正则。
4. **输出行以 % # $ 结尾可能被误判为提示符**（如 `100%`）——属启发式固有局限，可收紧 `--prompt`。
5. **命令文件编码**：记事本默认 GBK，脚本会报错并提示；请另存为 UTF-8。
6. **退出命令**：shell 模式发 `exit` 结束远端会话；stdin 模式也可用 `__EXIT__` 提前结束。
7. **中途断连**：batch 单条命令异常不会中断后续命令（错误写入对应条目）；shell 通道关闭后自动停止后续命令。
8. **跨层路径硬拦截（任务边界铁律，不可逾越）**：两个脚本均内置 `check_cross_layer`——命令文本命中
   `/opt/nsfocus/product/web|agent|system` 源码路径时，**默认拒绝执行**（batch 返回 `BLOCKED` 条目 + exit 1，
   shell 打印 `=== BLOCKED ===`），防止通过 SSH 在设备上翻读 WEB/AGENT 层源码、从上层倒推下层问题
   （教训来源：NEWNF-54251）。确需跨层取证时，先请用户确认，再显式传 `--allow-cross-layer`。
9. **自检**：`python .dsh/skills/ssh-tools/tests/test_ssh_skills.py` 可在无真实设备时验证工具可用性（本地起 paramiko 测试服务）。
