"""device_automation 多阶段续跑回归测试

验证场景：recover_config 流程中设备重启后已显示到下一阶段的中途步骤，
流程应从探测到的步骤续跑（而非从 step 0 重来导致 expect 逐个超时）。

历史缺陷（已修复）：
1. _pending_probe 在 for 循环内写入、循环前读取，导致阶段间重启后的
   探测结果永远不被消费，下一阶段从 step 0 重来。
2. 探测阶段读取的设备输出被丢弃，后续 expect 从空 buffer 等待设备
   不会再发送的提示，挂到超时。
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import device_automation as da


def build_device_script():
    """模拟设备状态机：[(输入匹配, 输出文本), ...]，None 表示自动输出。

    阶段2 从 "Press Enter to continue boot"（step2）开始 —— 模拟设备
    重启后已越过 step0/1，探测必须发现 (phase=1, step=2) 并续跑。
    """
    return [
        # ---- 阶段1：recover_pre_reboot（登录 → 重启系统）----
        (None, "NSFOCUS login: "),
        ("conadmin\n", "Password: "),
        ("conadmin\n", "2.English ...\n"),
        ("2\n", "You are using default password ...\n"),
        ("\n", "5.Restart the system ...\n"),
        ("5\n", "... rebooting ...\n"),
        # ---- 阶段2：recover_post_reboot ----
        (None, "Press Enter to continue boot: "),
        ("p", "passw0rd: "),
        ("passw0rd\n", "Press ESC to choose production type: "),
        ("\x1b", "Input choice: "),
        ("1\n", "config network static production: "),
        ("ST\n", "please input local ip address: "),
        ("1.1.1.1\n", "please input netmask: "),
        ("255.255.255.0\n", "please input default gateway: "),
        ("1.1.1.254\n", "please input file server ip: "),
        ("10.0.0.2\n", "0) NF606F03_test\nSelect Product: "),
        ("0\n", ">> Downloading file for NF606F03_test ...\n"
                "Clear partition ...\n"
                ">> ... Install Successed!\n"
                "Press Enter to reboot! "),
        ("\n", "Rebooting ..."),
        # ---- 阶段3：config（刷机完成后登录并配置管理口 IP）----
        (None, "NSFOCUS login: "),
        ("conadmin\n", "Password: "),
        ("conadmin\n", "2.English ...\n"),
        ("2\n", "You are using default password ...\n"),
        ("\n", "1.Check system information ...\n"),
        ("\n", "3.Set Manage Interface Ip Address ...\n"),
        ("3\n", "1.M ...\n"),
        ("\n", "Enable DHCP,sure? ...\n"),
        ("\x1b[C", "Example:192.168.1.1/16 ...\n"),
        ("\n", "please Input ipaddr/netmask: "),
        ("1.1.1.1/24\n", "please Input gateway: "),
        ("1.1.1.254\n", "config success! ...\n"),
    ]


class FakeTelnet:
    """模拟设备 Telnet 会话：按脚本推进状态机，支持行缓冲与无换行输入"""

    def __init__(self, script, collector, state):
        self.script = script
        # 设备全局状态跨连接共享（设备重启后状态延续，新会话重显提示）
        self.state = state
        self.outbox = []
        self.recv_log = []
        self.input_buf = ""
        self.closed = False
        collector.append(self)
        self._push_auto_outputs()

    def _emit(self, out):
        self.outbox.append(out)
        lines = out.splitlines()
        self.state["prompt"] = lines[-1] if lines else out

    def _push_auto_outputs(self):
        """连续输出无输入条件的脚本项（设备自动发出的提示）"""
        while self.state["idx"] < len(self.script):
            in_pat, out = self.script[self.state["idx"]]
            if in_pat is None:
                self._emit(out)
                self.state["idx"] += 1
            else:
                break

    def connect(self):
        self.closed = False
        # 模拟设备重启后 console 重显当前提示行（旧连接的 outbox 随会话关闭丢失）
        if self.state["prompt"]:
            self.outbox.append(self.state["prompt"])
        return True

    def read_any(self, timeout=0.5):
        if self.outbox:
            return self.outbox.pop(0)
        time.sleep(0.02)
        return ""

    def _try_match(self, text):
        if self.state["idx"] >= len(self.script):
            return False
        in_pat, out = self.script[self.state["idx"]]
        if in_pat is not None and in_pat in text:
            self._emit(out)
            self.state["idx"] += 1
            self._push_auto_outputs()
            return True
        return False

    def write(self, data):
        self.recv_log.append(data)
        text = data.decode("utf-8", errors="replace")
        if not text:
            return
        # 无换行输入（如 "p"、ESC）立即匹配
        if self._try_match(text):
            return
        # 行缓冲匹配（\n 结尾）
        self.input_buf += text
        matched = False
        while "\n" in self.input_buf:
            line, _, self.input_buf = self.input_buf.partition("\n")
            if self._try_match(line + "\n"):
                matched = True
                break
        # 未知输入：模拟 console 设备重显当前提示行
        # （真实设备在连接时输出提示，被 _connect 清空后，回车可触发重显）
        if not matched and self.state["prompt"]:
            self.outbox.append(self.state["prompt"])

    def expect(self, patterns, timeout=60, initial=""):
        buffer = initial
        # 测试用短超时：逻辑错误时快速失败而非等待 60s
        deadline = time.time() + min(timeout, 5)
        while time.time() < deadline:
            if self.outbox:
                buffer += self.outbox.pop(0)
            for i, p in enumerate(patterns):
                m = p.search(buffer)
                if m:
                    # 设备输出是持续流：匹配位置之后的文本存回 outbox，
                    # 供下一次 expect 消费（否则一次性输出的多段提示会丢失）
                    tail = buffer[m.end():]
                    if tail:
                        self.outbox.insert(0, tail)
                    return i, buffer
            time.sleep(0.01)
        return -1, buffer

    def close(self):
        self.closed = True


class RecoverConfigResumeTest(unittest.TestCase):

    def setUp(self):
        self.script = build_device_script()
        self.instances = []
        self.state = {"idx": 0, "prompt": ""}  # 设备全局状态（跨连接共享）
        self.config = da.DeviceConfig(
            tel_ip="10.0.0.1", tel_port=23,
            mgt_ip="1.1.1.1", mgt_mask="255.255.255.0", mgt_gw="1.1.1.254",
            server="10.0.0.2", image="NF606F03_test",
        )
        self.original_telnet_cls = da.TelnetClient

        def factory(*args, **kwargs):
            return FakeTelnet(self.script, self.instances, self.state)

        da.TelnetClient = factory

    def tearDown(self):
        da.TelnetClient = self.original_telnet_cls

    def test_recover_config_resumes_from_probed_step_after_reboot(self):
        """重启后设备处于阶段2中途（step2），应从探测位置续跑而非从 step 0 重来"""
        flow = da.AutoFlow(self.config, debug=False, reboot_wait=30)

        start = time.monotonic()
        flow.auto_recover_and_config()
        elapsed = time.monotonic() - start

        # 流程应完成（旧逻辑下阶段2 从 step 0 重来会逐个 expect 超时失败）
        self.assertTrue(flow.is_done,
                        "流程未完成——若从 step 0 重来会因设备提示已消费而超时")
        # 核心断言：重启后探测结果被消费，从 (phase 1, step 2) 续跑
        logs = "\n".join(flow.logs)
        self.assertIn("使用重启后探测结果: phase 1, step 2", logs)
        # 阶段2 step2 的输入（"p" + "passw0rd"）被发送，证明确实从中途续跑
        sent_all = b"".join(b"".join(t.recv_log) for t in self.instances)
        self.assertIn(b"p", sent_all)
        self.assertIn(b"passw0rd", sent_all)
        # 流程应在合理时间内完成：正常约 35s（每步固有 0.3s+0.5s 延迟），
        # 若阶段2 从 step 0 重来会叠加 expect 超时 + 30s 重启等待而明显超限
        self.assertLess(elapsed, 60,
                        f"流程耗时 {elapsed:.1f}s，疑似等待超时")

    def test_probe_buffer_not_lost_after_reboot(self):
        """探测读取的设备输出应传递给后续 expect（阶段3 的登录提示不丢失）"""
        flow = da.AutoFlow(self.config, debug=False, reboot_wait=30)
        flow.auto_recover_and_config()

        # 阶段3 的 "NSFOCUS login:" 由探测读取后传给首次 expect；
        # 若丢失，登录步骤会 expect 超时导致流程失败
        self.assertTrue(flow.is_done)
        logs = "\n".join(flow.logs)
        # 阶段3 最终走到"配置成功"（config_patterns 最后一步，is_done 由 _process_done 置位）
        self.assertIn("配置成功", logs)


if __name__ == "__main__":
    unittest.main()
