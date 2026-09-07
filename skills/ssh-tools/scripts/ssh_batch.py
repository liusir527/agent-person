#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量执行 SSH 命令（Windows 平台，基于 paramiko，无其它依赖）。

每条命令通过独立的 exec_command 通道执行，可获取各自的退出码与输出。
适用于普通服务器（Linux/Windows 远端）。网络设备（VPP、Cisco、华为等）
的交互式 CLI 请使用 ssh_shell.py。

用法示例:
  python ssh_batch.py --host 192.168.1.10 --user admin --password 'p@ss' ^
      --commands "uname -a" "df -h"
  python ssh_batch.py --host 192.168.1.10 --user admin --password 'p@ss' ^
      --commands-file cmds.txt
  set SSH_PASSWORD=p@ss   :: 或通过环境变量传密码，避免出现在进程列表/历史记录

输出: stdout 输出单个 JSON 文档（含每条命令的退出码/stdout/stderr），
      便于机器解析；命令全部成功退出码为 0，任一失败为 1，连接/参数错误为 2。
"""

import argparse
import json
import os
import re
import socket
import sys
import time

try:
    import paramiko
except ImportError:
    sys.stderr.write("错误: 缺少 paramiko 依赖，请先执行: pip install paramiko\n")
    sys.exit(3)

# === 终端命令审计埋点（monitor） ===
# 每条发往远端的命令写入 runtime/terminal-monitor/ops.jsonl，供
# nf-terminal-monitor 插件在 DSH Web GUI 实时展示。import 失败不影响主流程。
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "tools"))
    from terminal_audit import record as audit_record
except Exception:
    audit_record = None


# === 任务边界硬拦截（教训源自 NEWNF-54251，不可逾越） ===
# 此前主 agent 通过 ssh 在设备上连续翻读 /opt/nsfocus/product/web 下 WEB 源码
# （views.py/serializers.py/humansize.py）用于倒推显示逻辑，违反"只允许动 npp worktree"
# 的任务边界。现将「取证动作边界 = 修改边界」机制化：命令文本命中非本层源码路径时
# 默认拒绝执行，只有显式传参 --allow-cross-layer（须经用户确认）才放行。
CROSS_LAYER_PATTERNS = [
    r"/opt/nsfocus/product/web(?:/|['\"\s]|$)",
    r"/opt/nsfocus/product/agent(?:/|['\"\s]|$)",
    r"/opt/nsfocus/product/system(?:/|['\"\s]|$)",
]


def check_cross_layer(cmd, allow_cross_layer=False):
    """检查命令是否命中跨层源码路径。返回拦截原因；放行返回 None。"""
    if allow_cross_layer:
        return None
    for pat in CROSS_LAYER_PATTERNS:
        if re.search(pat, cmd):
            return (f"命令命中跨层源码路径 {pat}，属任务边界扩散（见 .dsh/hooks/AGENT.md "
                    f"「任务边界铁律」）；如需跨层取证须用户确认后显式传 --allow-cross-layer")
    return None


def _utf8_stdio():
    """Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文/设备输出乱码。"""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="批量执行 SSH 命令，输出 JSON 结果")
    parser.add_argument("--host", required=True, help="目标主机 IP/域名")
    parser.add_argument("--port", type=int, default=22, help="SSH 端口，默认 22")
    parser.add_argument("--user", required=True, help="用户名")
    parser.add_argument("--password", default=os.environ.get("SSH_PASSWORD"),
                        help="密码（也可用环境变量 SSH_PASSWORD 传入）")
    parser.add_argument("--commands", nargs="*", metavar="CMD",
                        help="要执行的命令，可跟多个")
    parser.add_argument("--commands-file", help="命令文件，每行一条；空行和 # 注释行跳过")
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="单条命令超时（秒），默认 30")
    parser.add_argument("--connect-timeout", type=float, default=15.0,
                        help="TCP 连接/认证超时（秒），默认 15")
    parser.add_argument("--encoding", default="utf-8",
                        help="远端输出解码编码，默认 utf-8")
    parser.add_argument("--known-hosts",
                        help="主机密钥文件路径；指定后校验主机密钥（未知主机仅警告并接受）")
    parser.add_argument("--allow-cross-layer", action="store_true",
                        help="显式放行跨层源码路径命令（如 /opt/nsfocus/product/web|agent|system），"
                             "仅经用户确认后使用；默认一律拒绝")
    args = parser.parse_args()
    if args.port < 1 or args.timeout <= 0:
        parser.error("--port 必须 >= 1，--timeout 必须 > 0")
    return args


def load_commands(args):
    commands = list(args.commands or [])
    if args.commands_file:
        try:
            with open(args.commands_file, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        commands.append(line)
        except (OSError, UnicodeDecodeError) as exc:
            sys.stderr.write(f"错误: 无法读取命令文件 {args.commands_file}: {exc}"
                             "（Windows 记事本默认 GBK 编码，请另存为 UTF-8）\n")
            sys.exit(2)
    if not commands:
        sys.stderr.write("错误: 未提供任何命令（--commands 或 --commands-file）\n")
        sys.exit(2)
    return commands


def run_one(client, command, timeout, encoding):
    """执行单条命令，返回 (exit_status, stdout, stderr, timed_out)。

    交替读取 stdout/stderr（不依赖 EOF），exit-status 就绪且输出取完后即收尾，
    避免 stderr 写满窗口或 nohup 后台进程持有 stdout 导致的误报超时。
    """
    transport = client.get_transport()
    if transport is None:
        return -1, "", "", False, "连接已断开"
    chan = transport.open_session()
    chan.settimeout(timeout)
    chan.exec_command(command)
    deadline = time.monotonic() + timeout
    stdout_bytes, stderr_bytes = b"", b""
    timed_out = False
    error = None

    while True:
        # 有数据就读，两个流都轮询，避免任一方向写满窗口
        if chan.recv_ready():
            chunk = chan.recv(65536)
            if chunk:
                stdout_bytes += chunk
        if chan.recv_stderr_ready():
            chunk = chan.recv_stderr(65536)
            if chunk:
                stderr_bytes += chunk
        # 完成条件：exit-status 已就绪且两个流都已读空。
        # 注意不能以 stdout EOF 为完成标志——stderr 可能仍在写，
        # 且通道 close 会唤醒 recv 返回 b''，此时 stderr 可能还没读。
        if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
            break
        if time.monotonic() >= deadline:
            timed_out = True
            break
        # 分片阻塞等待数据（0.1s 片，保证 deadline 生效、stderr 轮询及时）
        chan.settimeout(min(deadline - time.monotonic(), 0.1))
        try:
            chunk = chan.recv(65536)
        except socket.timeout:
            continue
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            break
        if chunk:
            stdout_bytes += chunk
        else:
            # stdout EOF 或通道关闭：稍等 stderr/exit-status 到达后回到循环顶
            time.sleep(0.05)

    if chan.exit_status_ready():
        exit_status = chan.recv_exit_status()
    else:
        exit_status = -1
        timed_out = True
    chan.close()
    return (exit_status,
            stdout_bytes.decode(encoding, "replace"),
            stderr_bytes.decode(encoding, "replace"),
            timed_out,
            error)


def main():
    _utf8_stdio()
    args = parse_args()
    if not args.password:
        sys.stderr.write("错误: 未提供密码（--password 或环境变量 SSH_PASSWORD）\n")
        sys.exit(2)

    commands = load_commands(args)
    result = {
        "host": args.host,
        "port": args.port,
        "user": args.user,
        "ok": True,
        "commands": [],
    }

    client = paramiko.SSHClient()
    if args.known_hosts:
        try:
            client.load_host_keys(args.known_hosts)
        except OSError as exc:
            sys.stderr.write(f"错误: 无法读取主机密钥文件 {args.known_hosts}: {exc}\n")
            sys.exit(2)
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sys.stderr.write("提示: 未指定 --known-hosts，首次连接的主机密钥将被自动信任"
                         "（存在中间人风险，建议对敏感主机使用 --known-hosts）\n")
    try:
        client.connect(
            hostname=args.host,
            port=args.port,
            username=args.user,
            password=args.password,
            timeout=args.connect_timeout,
            banner_timeout=args.connect_timeout,
            auth_timeout=args.connect_timeout,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as exc:
        result["ok"] = False
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    try:
        for command in commands:
            # 任务边界硬拦截：跨层源码路径命令一律拒绝（除非用户显式放行）
            blocked_reason = check_cross_layer(command, args.allow_cross_layer)
            if blocked_reason is not None:
                entry = {"cmd": command, "exit_status": -1, "stdout": "", "stderr": "",
                         "timed_out": False, "error": "BLOCKED: " + blocked_reason}
                result["ok"] = False
                result["commands"].append(entry)
                if audit_record is not None:
                    audit_record(host=args.host, port=args.port, user=args.user, cmd=command,
                                 mode="batch", result={"exit": -1, "dur": 0, "timed_out": False,
                                                       "error": "BLOCKED: " + blocked_reason})
                continue
            # 单条命令异常隔离：断连/通道错误不中断后续命令，错误写入对应条目
            start = time.monotonic()
            try:
                status, out, err, timed_out, run_error = run_one(
                    client, command, args.timeout, args.encoding)
            except Exception as exc:
                entry = {"cmd": command, "exit_status": -1, "stdout": "", "stderr": "",
                         "timed_out": False, "error": f"{type(exc).__name__}: {exc}"}
                result["ok"] = False
                result["commands"].append(entry)
                if audit_record is not None:
                    audit_record(host=args.host, port=args.port, user=args.user, cmd=command,
                                 mode="batch", result={"exit": -1, "dur": time.monotonic() - start,
                                                       "timed_out": False, "error": entry["error"]})
                continue
            entry = {
                "cmd": command,
                "exit_status": status,
                "stdout": out,
                "stderr": err,
                "timed_out": timed_out,
            }
            if run_error:
                entry["error"] = run_error
            result["commands"].append(entry)
            if audit_record is not None:
                audit_record(host=args.host, port=args.port, user=args.user, cmd=command,
                             mode="batch", result={"exit": status, "dur": time.monotonic() - start,
                                                   "timed_out": timed_out, "error": run_error})
            if status != 0 or timed_out or run_error:
                result["ok"] = False
    except KeyboardInterrupt:
        sys.stderr.write("\n已中断\n")
        result["ok"] = False
    finally:
        client.close()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
