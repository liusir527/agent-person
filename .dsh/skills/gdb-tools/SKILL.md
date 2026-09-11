---
name: gdb-attach
description: "GDB调试会话接入工具。以最小代价接入远程设备上已attach到VPP的GDB会话，支持reptyr抢占。当需要让AI操控远程设备上正在运行的GDB调试会话时使用。"
scene: debug
user-invocable: true
allowed-tools:
  - Bash(pgrep *)
  - Bash(gdb *)
  - Bash(scp *)
  - Bash(ssh *)
---

# GDB 调试会话接入

以最小代价让 AI 接入远程设备上已在运行的 GDB 会话。

## 总体思路

```
AI (Claude Code) ──ssh-skill──► 远程设备
                                 ├── reptyr 抢占已有 GDB 会话
                                 └── 或直接 gdb attach（无已运行 GDB 时）
```

**原则**：不注入 Python、不修改系统配置、不碰原有栈帧。

**关键**：所有 GDB 命令必须先 `set pagination off`，否则输出分页 `--More--` 会卡住 AI。

---

## 命令安全防护（由 nf-gdb-guard 插件承担）

> 本 skill 目录下不再内置 `hooks/block-gdb-dangerous.*`——那是 Claude Code 时代未接线的
> 旧 hook。DSH 环境下的 GDB 危险命令防护由工作区插件 `packages/nf-gdb-guard` 接管：

- 挂载点：cordis `tools/pre-execute`（经 `start.bat` 注册，重启 dsh web 生效）；
- 拦截：Bash/pwsh 工具中 `continue/c, run/r, start, jump/j, signal, kill/k, quit/q, call,
  shell, python, make, define, return, commands, set` 等改执行/写内存命令；
- 豁免：`x/, disassemble, break, watch, info, print/p, bt, list, thread, frame, help, find,
  set pagination/height/width/print` 等只读命令与偏好设置；
- 自测：`runtime/test_gdb_guard.mjs`（17/17 PASS）。

---

## 第一步：判断当前状态

```bash
# 找到 VPP 和 GDB
ssh <user>@<device> "pgrep -f 'vpp.*startup.conf'"
ssh <user>@<device> "ps aux | grep 'gdb.*vpp\|gdb.*attach' | grep -v grep"
```

| 状态 | 操作 |
|------|------|
| VPP 运行中，无 GDB attach | [路径 A：直接 attach](#路径-a直接-attach) |
| VPP 运行中，已有 GDB attach | [路径 B：reptyr 抢占](#路径-breptyr-抢占) |
| 需要反复发送多条 GDB 命令 | [路径 C：screen 持久化会话](#路径-cscreen-持久化会话) |

---

## 路径 C：screen持久化会话

当需要多次发送 GDB 命令、或需要交互式调试但不想用 reptyr 时，
用 screen 创建持久化 GDB 会话。

### C1. 创建 screen 会话

```bash
ssh <user>@<device> "screen -dmS gdb-debug bash"
```

> **命名与旁观**：GDB screen 会话也支持用户实时旁观——新开会话建议按 ssh-tools 统一规范命名为
> `nf_<设备>-gdb`，用户 `ssh` 登录设备后执行 `screen -x nf_<设备>-gdb` 即可查看调试过程；
> 沿用 `gdb-debug` 同样可用 `screen -x gdb-debug` 旁观。命令仍按下方 `-X stuff` 注入即可。

### C2. 在 screen 中启动 GDB

```bash
ssh <user>@<device> "screen -r gdb-debug -X stuff 'gdb -q -p <PID>\n'"
```

等待 GDB 启动完成后，关闭分页：

```bash
ssh <user>@<device> "screen -r gdb-debug -X stuff 'set pagination off\n'"
```

### C3. 发送 GDB 命令

```bash
# 查看线程列表
ssh <user>@<device> "screen -r gdb-debug -X stuff 'info threads\n'"

# 查看某个线程的堆栈
ssh <user>@<device> "screen -r gdb-debug -X stuff 'thread 1\nbt 20\n'"

# 查看寄存器
ssh <user>@<device> "screen -r gdb-debug -X stuff 'info registers\n'"
```

### C4. 获取 screen 输出

```bash
# 将 screen 内容保存到文件
ssh <user>@<device> "screen -r gdb-debug -X hardcopy /tmp/gdb-out.txt"
# 读取输出
ssh <user>@<device> "cat /tmp/gdb-out.txt"
```

如果输出被 `--More--` 卡住，先发送 `q` 退出分页：

```bash
ssh <user>@<device> "screen -r gdb-debug -X stuff 'q\n'"
```

### C5. 结束会话

```bash
# 正常退出 GDB
ssh <user>@<device> "screen -r gdb-debug -X stuff 'quit\n'"
# 强制关闭 screen 会话
ssh <user>@<device> "screen -S gdb-debug -X quit"
```

### 适用场景

- 需要逐条发送 GDB 命令（如 `thread 1, bt, thread 2, bt...`）
- 需要交互式调试但 reptyr 不可用
- 设备上无 reptyr 二进制，但 screen 可用
- 调试多线程进程（如 VPP），需要逐个线程查看堆栈
- 需要长时间保持调试会话，SSH 断开后不丢失状态

### 注意事项

- `hardcopy` 只捕获可见区域，如果输出很长需要滚动，需结合 `screen -X scrollback` 或分次捕获
- 如果 GDB 输出被分页卡住，先用 `set pagination off`，或发送 `q` 退出分页
- screen 会话在 SSH 断开后依然保留，适合长时间调试
- 如果进程重启导致 PID 变化，需要重新 attach：`screen -r gdb-debug -X stuff 'attach <新PID>\n'`

---

## 路径 A：直接 attach

通过 SSH 在设备上启动 GDB attach，-batch 模式执行命令后自动退出，不留残留：

```bash
# 单次执行：attach → 执行命令 → 退出
ssh <user>@<device> \
  "gdb --pid \$(pgrep -f 'vpp.*startup.conf') -batch -ex 'set pagination off' -ex 'bt' -ex 'info threads' -ex 'detach' -ex 'quit'"
```

如果需要交互式调试，不加 `-batch`：

```bash
ssh <user>@<device> \
  "gdb --pid \$(pgrep -f 'vpp.*startup.conf') -ex 'set pagination off'"
```

---

## 路径 B：reptyr 抢占

已有 GDB attach 到 VPP 时，用 reptyr 把会话拉到当前终端。

### B1. 推送 reptyr

```bash
ARCH=$(ssh <user>@<device> "uname -m")
case $ARCH in
    x86_64)  SRC="$SKILL_DIR/tools/x86/reptyr" ;;
    aarch64) SRC="$SKILL_DIR/tools/arm64/reptyr" ;;
    *) echo "不支持的架构"; exit 1 ;;
esac

# 用 ssh-file-transfer 或 scp 推送
scp "$SRC" <user>@<device>:/root/reptyr
ssh <user>@<device> "chmod +x /root/reptyr"
```

如果设备上 `/root/reptyr` 已存在且可用，跳过推送。

### B2. 执行抢占

```bash
# reptyr 需要 root 权限来 attach 非子进程
ssh -t root@<device> "/root/reptyr $(ssh <user>@<device> "ps aux | grep 'gdb' | grep -v grep | awk '{print \$2}'")"
```

抢占后 GDB 提示符出现在当前终端，即可直接交互。

### B3. 抢占后 AI 操控

抢占成功后有两种操控方式：

**方式 1：直接交互**（抢占后终端由 AI 操控，直接输入 GDB 命令）

**方式 2：单次命令**（在另一个 SSH 连接中向 GDB 所在 TTY 写入命令，先用 `set pagination off` 关闭分页）

```bash
# 找到 GDB 所在的 TTY
TTY=$(ssh <user>@<device> "readlink /proc/\$(pgrep gdb)/fd/0")
# 发送命令
ssh <user>@<device> "echo 'bt' > $TTY"
```

---

## reptyr 注意事项

- reptyr 抢占非子进程需要 **root** 权限，请用 root 登录
- reptyr 仅 Linux 可用，需与设备架构一致（x86_64 / aarch64）
- 抢占后原终端会丢失 GDB 控制权
- 如果抢占失败：kill 旧 GDB → 走路径 A 重建

---

## 常用单次调试命令

通过 SSH 执行单次 attach 调试（不抢占、不留会话）：

```bash
# 调用栈
ssh <user>@<device> \
  "gdb --pid \$(pgrep -f 'vpp.*startup.conf') -batch -ex 'set pagination off' -ex 'bt full' -ex 'detach' -ex 'quit'"

# 线程状态
ssh <user>@<device> \
  "gdb --pid \$(pgrep -f 'vpp.*startup.conf') -batch -ex 'set pagination off' -ex 'info threads' -ex 'detach' -ex 'quit'"

# 局部变量
ssh <user>@<device> \
  "gdb --pid \$(pgrep -f 'vpp.*startup.conf') -batch -ex 'set pagination off' -ex 'info locals' -ex 'detach' -ex 'quit'"
```

`-batch` 保证执行完立即退出，不会残留 GDB 进程。

---

## 依赖

- **SSH**：所有操作通过 SSH 在远程设备上执行，优先使用 ssh-skill（如可用），否则回退到原生 ssh/scp
- **reptyr**：二进制文件随本技能分发（`$SKILL_DIR/tools/<arch>/reptyr`），按架构自动选择
