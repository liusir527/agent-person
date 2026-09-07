#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ssh-tools skill 自检测试：本地起一个 paramiko SSH 服务，端到端验证两个脚本。

覆盖场景:
  - ssh_batch.py: 批量执行 / 退出码汇总 / 命令文件 / 环境变量密码 / 密码错误 / 连接拒绝
  - ssh_shell.py: --script 批处理 / --oneshot 单发 / stdin REPL / 超时 / banner 丢弃

用法:
  python .dsh/skills/ssh-tools/tests/test_ssh_skills.py
  无需真实设备，仅依赖 paramiko。
"""

import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

try:
    import paramiko
except ImportError:
    sys.stderr.write("错误: 缺少 paramiko 依赖，请先执行: pip install paramiko\n")
    sys.exit(3)

# 客户端断开时 paramiko transport 线程会打 ERROR 日志到 stderr，测试中静音
logging.getLogger("paramiko").setLevel(logging.CRITICAL)

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(TESTS_DIR, "..", "scripts")
BATCH = os.path.join(SCRIPTS_DIR, "ssh_batch.py")
SHELL = os.path.join(SCRIPTS_DIR, "ssh_shell.py")
HOST = "127.0.0.1"
USER = "test"
PASSWORD = "secret"


# ---------- 测试用 SSH 服务（paramiko ServerInterface） ----------

class TestServer(paramiko.ServerInterface):
    """密码认证；exec 走真实子进程；shell 模拟 VPP 风格网络设备 CLI。"""

    def check_auth_password(self, username, password):
        if username == USER and password == PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height,
                                  pixelwidth, pixelheight, modes):
        return True

    def check_channel_exec_request(self, channel, command):
        threading.Thread(target=self._exec, args=(channel, command), daemon=True).start()
        return True

    def _exec(self, channel, command):
        try:
            # paramiko 传入的命令是 bytes；Windows 上 subprocess 不允许 bytes 参数
            command = command.decode("utf-8", "replace")
            if command.startswith("slow:"):  # 慢命令，用于超时测试
                time.sleep(float(command[len("slow:"):]))
            proc = subprocess.run(command, shell=True, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=10)
            channel.sendall(proc.stdout.encode("utf-8", "replace"))
            channel.sendall_stderr(proc.stderr.encode("utf-8", "replace"))
            channel.send_exit_status(proc.returncode)
        except Exception:
            # 客户端可能已断开，send_exit_status 也可能失败，不能再抛
            try:
                channel.send_exit_status(1)
            except Exception:
                pass
        finally:
            channel.close()

    def check_channel_shell_request(self, channel):
        threading.Thread(target=self._shell, args=(channel,), daemon=True).start()
        return True

    def _shell(self, channel):
        """模拟网络设备 CLI：每个命令后回显 'vpp# ' 提示符。"""
        channel.sendall(b"Welcome to fake VPP CLI\r\n\r\nvpp# ")
        data = b""
        while True:
            try:
                chunk = channel.recv(1024)
            except Exception:
                break
            if not chunk:
                break
            data += chunk
            while b"\n" in data:
                line, data = data.split(b"\n", 1)
                line = line.rstrip(b"\r").decode("utf-8", "replace")
                if line == "exit":
                    channel.close()
                    return
                if line == "show version":
                    channel.sendall(b"vpp v23.10-rc0~g1234567 built by root\r\nvpp# ")
                elif line == "show clock":
                    channel.sendall(b"Wed Aug  7 10:00:00 2026\r\nvpp# ")
                elif line == "slow":
                    time.sleep(3)
                    channel.sendall(b"slow done\r\nvpp# ")
                else:
                    channel.sendall(("unknown cmd: " + line + "\r\nvpp# ").encode("utf-8"))
        channel.close()


def start_server():
    """启动测试 SSH 服务，返回监听端口（端口 0 自动分配）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, 0))
    sock.listen(5)
    port = sock.getsockname()[1]

    try:
        host_key = paramiko.RSAKey.generate(2048)
    except Exception:
        host_key = paramiko.ECDSAKey.generate()

    def handle(conn):
        try:
            transport = paramiko.Transport(conn)
            transport.add_server_key(host_key)
            transport.start_server(server=TestServer())
            while transport.is_active():
                time.sleep(0.1)
        except Exception:
            pass
        finally:
            conn.close()

    def accept_loop():
        while True:
            try:
                conn, _ = sock.accept()
            except OSError:
                return
            threading.Thread(target=handle, args=(conn,), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return port


def run_script(script, *args, stdin_text=None, env=None):
    """以子进程运行 skill 脚本，返回 CompletedProcess。"""
    return subprocess.run(
        [sys.executable, script, *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=60,
    )


# ---------- 测试用例 ----------

class SshBatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = start_server()
        time.sleep(0.3)  # 等服务线程就绪

    def base_args(self, password=PASSWORD):
        return ["--host", HOST, "--port", str(self.port),
                "--user", USER, "--password", password]

    def test_batch_mixed_exit_status(self):
        proc = run_script(BATCH, *self.base_args(),
                          "--commands", "echo hello", "exit 3")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertFalse(result["ok"])
        statuses = [c["exit_status"] for c in result["commands"]]
        self.assertEqual(statuses, [0, 3])
        self.assertIn("hello", result["commands"][0]["stdout"])
        self.assertEqual(result["host"], HOST)

    def test_batch_all_success(self):
        proc = run_script(BATCH, *self.base_args(), "--commands", "echo ok")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(result["commands"][0]["exit_status"], 0)

    def test_batch_commands_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# 注释行应跳过\n\necho fromfile\necho line2\n")
            path = fh.name
        try:
            proc = run_script(BATCH, *self.base_args(), "--commands-file", path)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            cmds = [c["cmd"] for c in result["commands"]]
            self.assertEqual(cmds, ["echo fromfile", "echo line2"])
            self.assertIn("fromfile", result["commands"][0]["stdout"])
        finally:
            os.unlink(path)

    def test_batch_env_password(self):
        env = dict(os.environ)
        env["SSH_PASSWORD"] = PASSWORD
        proc = run_script(BATCH, "--host", HOST, "--port", str(self.port),
                          "--user", USER, "--commands", "echo envpass", env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("envpass", json.loads(proc.stdout)["commands"][0]["stdout"])

    def test_batch_wrong_password(self):
        proc = run_script(BATCH, *self.base_args(password="wrong"), "--commands", "echo x")
        self.assertEqual(proc.returncode, 2)
        result = json.loads(proc.stdout)
        self.assertFalse(result["ok"])
        self.assertIn("error", result)

    def test_batch_conn_refused(self):
        proc = run_script(BATCH, "--host", HOST, "--port", "59999",
                          "--user", USER, "--password", PASSWORD, "--commands", "echo x")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error", json.loads(proc.stdout))

    def test_batch_timeout(self):
        proc = run_script(BATCH, *self.base_args(),
                          "--timeout", "0.5", "--commands", "slow:2")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        result = json.loads(proc.stdout)
        entry = result["commands"][0]
        self.assertTrue(entry["timed_out"])
        self.assertEqual(entry["exit_status"], -1)

    def test_batch_stderr_captured(self):
        proc = run_script(BATCH, *self.base_args(), "--commands", "echo err 1>&2")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertIn("err", result["commands"][0]["stderr"])

    def test_batch_missing_password(self):
        env = {k: v for k, v in os.environ.items() if k != "SSH_PASSWORD"}
        proc = run_script(BATCH, "--host", HOST, "--user", USER,
                          "--commands", "echo x", env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("密码", proc.stderr)

    def test_batch_empty_commands(self):
        proc = run_script(BATCH, *self.base_args())
        self.assertEqual(proc.returncode, 2)
        self.assertIn("未提供任何命令", proc.stderr)


class SshShellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = start_server()
        time.sleep(0.3)

    def base_args(self):
        return ["--host", HOST, "--port", str(self.port),
                "--user", USER, "--password", PASSWORD]

    def test_script_mode_order_and_banner_discard(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("show version\nshow clock\nexit\n")
            path = fh.name
        try:
            proc = run_script(SHELL, *self.base_args(), "--script", path)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertIn("vpp v23.10-rc0", out)
        self.assertIn("Wed Aug  7", out)
        self.assertNotIn("Welcome to fake VPP CLI", out)  # 登录 banner 应被丢弃
        self.assertLess(out.index("SEND: show version"), out.index("SEND: show clock"))
        self.assertIn("DONE", out)

    def test_oneshot(self):
        proc = run_script(SHELL, *self.base_args(), "--oneshot", "show clock")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Wed Aug  7", proc.stdout)
        self.assertIn("DONE", proc.stdout)

    def test_repl_stdin(self):
        proc = run_script(SHELL, *self.base_args(), stdin_text="show version\nexit\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("vpp v23.10-rc0", proc.stdout)

    def test_timeout(self):
        proc = run_script(SHELL, *self.base_args(),
                          "--timeout", "0.5", "--oneshot", "slow")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("TIMEOUT", proc.stdout)

    def test_exit_then_more_commands(self):
        """回归: exit 关闭通道后不应崩溃，后续命令应停止。"""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("show version\nexit\nshow clock\n")
            path = fh.name
        try:
            proc = run_script(SHELL, *self.base_args(), "--script", path)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("vpp v23.10-rc0", proc.stdout)
        self.assertIn("CHANNEL CLOSED", proc.stdout)
        self.assertNotIn("SEND: show clock", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)