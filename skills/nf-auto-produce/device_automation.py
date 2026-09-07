#!/usr/bin/env python3
"""
设备自动化生产通用脚本

支持三种操作模式:
- recover: 刷写电子盘（恢复出厂镜像）
- config: 配置管理口IP
- recover_config: 先恢复后配置的组合操作
"""

import re
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import signal

# 类型别名
PatternCallback = Callable[[List['Pattern'], int, str], Optional[List['Pattern']]]


class TelnetConnectionError(Exception):
    """Telnet连接异常"""
    pass


class TelnetClient:
    """Telnet客户端实现（支持IAC控制字符处理）"""

    # 缓冲区大小常量
    BUFFER_SIZE = 4096

    # Telnet IAC 命令
    IAC = b'\xff'
    DONT = b'\xfe'
    DO = b'\xfd'
    WONT = b'\xfc'
    WILL = b'\xfb'
    SB = b'\xfa'
    SE = b'\xf0'
    NOP = b'\xf1'
    # 常见选项
    OPT_ECHO = b'\x01'
    OPT_SUPPRESS_GO_AHEAD = b'\x03'
    OPT_TERMINAL_TYPE = b'\x18'
    OPT_NAWS = b'\x1f'
    OPT_LINEMODE = b'\x22'

    def __init__(self, host: str, port: int = 23, timeout: int = 30, debug: bool = False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.debug = debug
        self.sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """连接到Telnet服务器"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
            raise

    def _log_msg(self, msg: str):
        """内部日志（debug模式输出）"""
        if self.debug:
            print(f"  [TELNET] {msg}")

    def write(self, data: bytes):
        """发送数据，连接异常时抛出 TelnetConnectionError 而非让 Python 崩溃"""
        if not self.sock:
            raise TelnetConnectionError("Not connected")
        try:
            self.sock.sendall(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
            self._log_msg(f"发送失败，连接已断开: {e}")
            self.close()
            raise TelnetConnectionError(f"连接断开: {e}") from e

    def _strip_iac(self, data: bytes) -> tuple[bytes, bytes]:
        """剥离Telnet IAC控制序列，返回(有效数据, 剩余未完成序列)
        处理: IAC + COMMAND, IAC + WILL/WONT/DO/DONT + OPTION, IAC + SB + ... + IAC + SE
        """
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i:i+1] == self.IAC:
                if i + 1 >= len(data):
                    # 不完整的IAC序列，保留
                    return bytes(result), data[i:]
                cmd = data[i+1:i+2]
                if cmd in (self.WILL, self.WONT, self.DO, self.DONT):
                    if i + 2 >= len(data):
                        return bytes(result), data[i:]
                    # 自动响应: 对 WILL/WONT回复 DO/DONT, 对 DO/DONT回复 WILL/WONT
                    opt = data[i+2:i+3]
                    try:
                        if cmd == self.WILL:
                            self.sock.sendall(self.IAC + self.DONT + opt)
                        elif cmd == self.DO:
                            self.sock.sendall(self.IAC + self.WONT + opt)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                        # IAC 响应发送失败不中断数据处理，忽略即可
                        pass
                    i += 3
                elif cmd == self.SB:
                    # Subnegotiation: IAC SB ... IAC SE
                    se_pos = data.find(self.IAC + self.SE, i + 2)
                    if se_pos == -1:
                        return bytes(result), data[i:]
                    i = se_pos + 2
                elif cmd in (self.NOP,):
                    i += 2
                else:
                    # IAC + byte: 如果是 IAC+IAC 则是转义的 0xFF，保留一个
                    # 其他 IAC 命令（未知命令）跳过
                    if cmd == self.IAC:
                        result.append(0xff)
                    i += 2
            else:
                result.append(data[i])
                i += 1
        return bytes(result), b''

    def read_any(self, timeout: float = 0.5) -> str:
        """读取任意可用数据并剥离IAC"""
        if not self.sock:
            raise EOFError("Not connected")
        self.sock.settimeout(timeout)
        try:
            chunk = self.sock.recv(self.BUFFER_SIZE)
            if not chunk:
                raise EOFError("Connection closed")
            cleaned, _ = self._strip_iac(chunk)
            return cleaned.decode('utf-8', errors='replace')
        except socket.timeout:
            return ""

    def expect(self, patterns: list[re.Pattern], timeout: float = 60, initial: str = "") -> tuple[int, str]:
        """等待匹配任一正则，返回(匹配索引, 累计接收文本)
        initial: 探测阶段已读取的设备输出，作为初始 buffer，避免提示文本在探测后丢失
        """
        if not self.sock:
            raise EOFError("Not connected")

        buffer = initial
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                self.sock.settimeout(0.5)
                chunk = self.sock.recv(self.BUFFER_SIZE)
                if not chunk:
                    return -3, buffer
                cleaned, _ = self._strip_iac(chunk)
                text = cleaned.decode('utf-8', errors='replace')
                buffer += text

                # 逐行输出到日志（仅 debug 模式）
                if self.debug:
                    for line in text.splitlines(True):
                        if line.strip():
                            print(f"  [RECV] {line.rstrip()}")

                # 每收到新数据就重新匹配所有模式
                for i, pattern in enumerate(patterns):
                    m = pattern.search(buffer)
                    if m:
                        return i, buffer

            except socket.timeout:
                continue
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                return -3, buffer
            except EOFError:
                return -3, buffer
            except Exception as e:
                if self.debug:
                    print(f"  [WARN] read error: {e}")
                # 普通异常继续等待，但如果是连接类异常则返回断开信号
                if "connection" in str(e).lower() or "reset" in str(e).lower() or "broken" in str(e).lower():
                    return -3, buffer
                continue

        return -1, buffer

    def close(self):
        """关闭连接"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def __del__(self):
        self.close()


@dataclass
class DeviceConfig:
    """设备配置"""
    tel_ip: str
    tel_port: int = 23
    mgt_ip: str = ""
    mgt_mask: str = ""
    mgt_gw: str = ""
    server: str = ""
    image: str = ""


class Pattern:
    """模式匹配规则: 等待正则匹配 -> 发送命令 -> 执行回调"""

    def __init__(
        self,
        pattern: str,
        inputs: List[str],
        desc: str,
        callback: Optional[PatternCallback] = None,
        timeout: int = 60
    ):
        self.regex = re.compile(pattern)
        self.inputs = inputs
        self.desc = desc
        self.callback = callback
        self.timeout = timeout


class AutoFlow:
    """自动化生产流程控制器"""

    # 默认配置
    DEFAULT_REBOOT_WAIT = 180  # 秒
    MAX_RECONNECT_ATTEMPTS = 5
    DEFAULT_READ_TIMEOUT = 0.5  # 秒
    DEFAULT_SEND_DELAY = 0.5  # 秒

    def __init__(self, config: DeviceConfig, debug: bool = False,
                 reboot_wait: int = DEFAULT_REBOOT_WAIT):
        self.config = config
        self.debug = debug
        self.reboot_wait = reboot_wait
        self.telnet: Optional[TelnetClient] = None
        self.stop_requested = threading.Event()

        # 状态变量
        self.is_running = False
        self.is_done = False
        self.progress = 0
        self.current_status = "等待开始"
        self.current_phase = ""
        self.logs = []

        # 动态变量
        self.edisk_id = "0"
        self.device_hash = ""
        self.phase_complete = False
        self.progress_scale_start = 0
        self.progress_scale_end = 100
        # 阶段间重启探测结果（跨阶段传递，循环内消费）
        self._pending_probe = None
        # 探测阶段已读取的设备输出（供 expect/回调复用，避免提示文本丢失）
        self._probe_buffer = ""

        # 初始化模式
        self._init_patterns()

    def _log(self, msg: str) -> None:
        """记录日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {msg}"
        self.logs.append(log_line)
        print(log_line)

    def _update_progress(self, current_step: int, total_steps: int) -> None:
        """更新进度"""
        if self.progress_scale_start == 0 and self.progress_scale_end == 100:
            self.progress = int((current_step / total_steps) * 100)
        else:
            scale_range = self.progress_scale_end - self.progress_scale_start
            self.progress = self.progress_scale_start + int((current_step / total_steps) * scale_range)

    def _init_patterns(self) -> None:
        """初始化模式匹配规则"""

        # 恢复模式 — 重启前阶段（登录到重启系统）
        self.recover_pre_reboot_patterns = [
            Pattern(r"NSFOCUS login:", ["conadmin\n"], "登录管理员账号"),
            Pattern(r"Password:", ["conadmin\n"], "输入密码"),
            Pattern(r"2.English", ["2","\n"], "选择英文"),
            Pattern(r"You are using default password", ["\n"], "确认默认密码"),
            Pattern(r"5.Restart the system", ["5","\n", "\n"], "重新启动系统"),
        ]

        # 恢复模式 — 重启后阶段（中断启动 -> 刷机 -> 安装）
        self.recover_post_reboot_patterns = [
            Pattern(r"Press any key to continue", ["\x1b"], "跳过继续提示"),
            Pattern(r"Press `ESC' to interrupt boot", ["\x1b"], "中断启动"),
            Pattern(r"Press Enter to continue boot", ["p", "passw0rd\n"], "进入选择"),
            Pattern(r"Press ESC to choose production type", ["\x1b"], "选择生产类型"),
            Pattern(r"Input choice:", ["1","\n"], "选择选项1"),
            Pattern(r"config network.*production", ["ST","\n"], "选择静态IP配置"),
            Pattern(r"please input local ip address", [f"{self.config.mgt_ip}","\n"], "输入本地IP"),
            Pattern(r"please input netmask", [f"{self.config.mgt_mask}","\n"], "输入子网掩码"),
            Pattern(r"please input default gateway", [f"{self.config.mgt_gw}","\n"], "输入网关"),
            Pattern(r"please input file server ip", [f"{self.config.server}","\n"], "输入文件服务器IP"),
            Pattern(r"\d+\)\s*" + re.escape(self.config.image), [""], "匹配产品", self._edisk_id_match),
            Pattern(r"Select Product", [f"{self.edisk_id}","\n"], "选择产品"),
            Pattern(r">> Downloading file for " + re.escape(self.config.image), [""], "下载文件", timeout=1200),
            Pattern(r"Clear partition", [""], "开始安装电子盘", timeout=600),
            Pattern(r">> .* Install Successed!", [""], "安装成功", timeout=600),
            Pattern(r"Press Enter to reboot!", ["\n"], "重启设备", self._process_done),
            Pattern(r"Rebooting", [""], "设备自动重启", callback=self._process_done, timeout=30),
        ]

        # 恢复模式（旧版，保留兼容）
        self.recover_patterns = self.recover_pre_reboot_patterns + self.recover_post_reboot_patterns

        # 配置模式模式（配置管理口IP）
        mask_len = self._mask_to_len(self.config.mgt_mask)
        self.config_patterns = [
            Pattern(r"NSFOCUS login:", ["conadmin\n"], "登录管理员账号"),
            Pattern(r"Password:", ["conadmin\n"], "输入密码"),
            Pattern(r"English", ["2","\n"], "选择英文"),
            Pattern(r"You are using default password", ["\n"], "确认默认密码"),
            Pattern(r"1.Check system information", ["\n"], "查看系统信息"),
            Pattern(r"3.Set Manage Interface Ip Address", ["3","\n"], "设置管理口IP"),
            Pattern(r"1.M", ["\n"], "选择M口"),
            Pattern(r"Enable DHCP,sure?", ["\x1b[C", "\n"], "选择静态IP"),
            Pattern(r"Example:192.168.1.1/16", ["\n"], "确认静态IP"),
            Pattern(r"please Input ipaddr/netmask", [f"{self.config.mgt_ip}/{mask_len}\n"], "输入IP/掩码"),
            Pattern(r"please Input gateway", [f"{self.config.mgt_gw}\n"], "输入网关"),
            Pattern(r"config success!", ["\n", "0\n", "0\n", "0\n"], "配置成功", self._process_done),
        ]

        # 提取设备HASH值
        self.hash_patterns = [
            Pattern(r"NSFOCUS login:", ["conadmin\n"], "登录管理员账号"),
            Pattern(r"Password:", ["conadmin\n"], "输入密码"),
            Pattern(r"English", ["2","\n"], "选择英文"),
            Pattern(r"You are using default password", ["\n"], "确认默认密码"),
            Pattern(r"1.Check system information", ["\n"], "查看系统信息"),
            Pattern(r"8.Product Hardware ID", ["8\n"], "查看设备HASH值"),
            Pattern(r"Product ID:", ["\n", "0\n", "0\n"], "获取设备HASH值", callback=self._hash_extract),
        ]

    def _mask_to_len(self, mask: str) -> int:
        """子网掩码转 CIDR 长度"""
        try:
            parts = [int(p) for p in mask.split('.')]
            if len(parts) != 4:
                raise ValueError(f"Invalid mask format: {mask}")

            # 验证每个部分是否在有效范围
            for part in parts:
                if not 0 <= part <= 255:
                    raise ValueError(f"Invalid mask value: {part}")

            # 计算连续1的位数（从高位到低位）
            addr = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]

            # 验证是否为有效的子网掩码（连续1后跟连续0）
            inverted = (~addr) & 0xFFFFFFFF
            if inverted == 0:
                return 32  # 255.255.255.255
            if (inverted & (inverted + 1)) != 0:
                # 不是有效的子网掩码，但仍返回计算的位数
                self._log(f"警告: {mask} 不是标准的子网掩码")

            # 计算前导1的个数
            length = 0
            for bit in range(31, -1, -1):
                if addr & (1 << bit):
                    length += 1
                else:
                    break
            return length
        except (ValueError, IndexError) as e:
            self._log(f"子网掩码转换错误: {mask}, {e}")
            # fallback: 只算 255 的部分（粗略估计）
            return sum(8 for part in mask.split('.') if part == '255')

    def _edisk_id_match(self, patterns: List[Pattern], index: int, received: str) -> List[Pattern]:
        """从输出中解析产品ID"""
        # 从匹配行中提取编号，格式如 "0) NF606F03_fixpass_x86..."
        match = patterns[index].regex.search(received)
        if match:
            self.edisk_id = match.group(0).split(')')[0].strip()
            self._log(f"已选择产品: {self.config.image} (ID: {self.edisk_id})")
            # 检查边界，避免 IndexError
            if index + 1 < len(patterns):
                patterns[index + 1].inputs = [f"{self.edisk_id}\n"]
            else:
                self._log(f"警告: 无法设置下一个pattern的inputs，已到达列表末尾")
        return patterns

    def _process_done(self, patterns: List[Pattern], index: int, received: str) -> List[Pattern]:
        """标记流程完成"""
        self.is_done = True
        self.phase_complete = True
        self.progress = self.progress_scale_end
        self._log(f"进度: {self.progress}%")
        self._log("所有流程已完成")
        return patterns

    def _hash_extract(self, patterns: List[Pattern], index: int, received: str) -> List[Pattern]:
        """从接收文本中提取设备HASH值并标记完成"""
        # 等待完整输出到达buffer（设备可能分多次发送）
        buffer = received
        if self.telnet and self.telnet.sock:
            try:
                time.sleep(1)
                self.telnet.sock.settimeout(self.DEFAULT_READ_TIMEOUT)
                while True:
                    try:
                        chunk = self.telnet.sock.recv(TelnetClient.BUFFER_SIZE)
                        if not chunk:
                            break
                        cleaned, _ = self.telnet._strip_iac(chunk)
                        buffer += cleaned.decode('utf-8', errors='replace')
                    except socket.timeout:
                        break
            except socket.timeout:
                # 预期的超时，表示没有更多数据
                pass
            except (OSError, ConnectionError) as e:
                # 连接相关错误，记录但不中断流程
                self._log(f"读取额外数据时连接错误: {e}")
            except Exception as e:
                # 其他意外错误，记录但不中断
                self._log(f"读取额外数据时发生错误: {e}")

        match = re.search(r"Product ID:\s*([\w-]+)", buffer)
        if match:
            self.device_hash = match.group(1).strip()
            self._log(f"设备HASH值: {self.device_hash}")
        else:
            self.device_hash = ""
            self._log("警告: 未能从输出中提取到HASH值")

        self.is_done = True
        self.phase_complete = True
        self.progress = self.progress_scale_end
        self._log(f"进度: {self.progress}%")
        self._log("HASH值提取完成")
        return patterns

    def _connect(self, max_retries: int = 20) -> bool:
        """连接设备，支持重试"""
        self._log(f"正在连接到 {self.config.tel_ip}:{self.config.tel_port}...")
        for i in range(max_retries):
            if self.stop_requested.is_set():
                self._log("连接尝试已被中断")
                return False

            try:
                self.telnet = TelnetClient(
                    self.config.tel_ip,
                    self.config.tel_port,
                    timeout=3,
                    debug=self.debug
                )
                self.telnet.connect()
                self._log(f"已连接到 {self.config.tel_ip}:{self.config.tel_port}")
                # 等待连接稳定
                time.sleep(self.DEFAULT_SEND_DELAY)
                # 清空初始输出
                try:
                    self.telnet.read_any(timeout=1)
                except:
                    pass
                return True
            except Exception as e:
                err_msg = str(e)
                if "refused" in err_msg.lower() or "Connection refused" in err_msg:
                    msg = "连接被拒绝"
                elif "timeout" in err_msg.lower():
                    msg = "连接超时"
                else:
                    msg = "连接失败"
                self._log(f"{msg} (第 {i+1}/{max_retries} 次)")

                delay = min(3 * (i + 1), 20)
                self._log(f"等待 {delay} 秒后重试...")
                if self._sleep_interruptible(delay):
                    continue
                else:
                    return False

        self._log(f"无法在 {max_retries} 次尝试内连接到设备")
        return False

    def _sleep_interruptible(self, seconds: float) -> bool:
        """可中断的睡眠"""
        return not self.stop_requested.wait(seconds)

    def _probe_device_state(self, phase_groups, start_phase=0):
        """探测设备当前状态，返回 (phase_idx, step_idx)

        phase_groups: list of (patterns, progress_start, progress_end, name)
        在所有 phases 的所有 patterns 中查找匹配，返回 (phase_idx, step_idx)。
        未匹配返回 (0, 0)。
        start_phase: 从该 phase 开始扫描。设备状态单调推进，阶段间重启等待时
        不可能回到更早阶段；不限定的话，跨阶段重复的提示（如 "NSFOCUS login:"
        同时出现在阶段1 和阶段3）会被早期 phase 的 pattern 劫持。
        探测期间读取的设备输出保存在 self._probe_buffer，供后续 expect/回调复用。
        """
        # 构建全局探测池：[(phase_idx, step_idx, regex, desc), ...]
        probe_pool = []
        for pi, (pats, _, _, _) in enumerate(phase_groups):
            if pi < start_phase:
                continue
            for si, pat in enumerate(pats):
                probe_pool.append((pi, si, pat.regex, pat.desc))

        self._log("探测设备当前状态...")

        def _scan(buffer):
            for pi, si, regex, desc in probe_pool:
                if regex.search(buffer):
                    self._log(f"探测到设备处于: phase {pi}, step {si} ({desc})")
                    return pi, si
            return None

        # 先读取已有输出（设备可能已经有输出在等待）
        buffer = ""
        try:
            for _ in range(6):  # 最多读3秒
                chunk = self.telnet.read_any(timeout=self.DEFAULT_READ_TIMEOUT)
                if chunk:
                    buffer += chunk
                    result = _scan(buffer)
                    if result:
                        self._probe_buffer = buffer
                        return result
        except Exception as e:
            self._log(f"探测读取异常: {e}")

        # 没有匹配到，再发送回车触发输出（保留已读到的内容，不丢弃）
        self._log("未检测到设备输出，发送回车触发...")
        try:
            self.telnet.write(b"\n")
        except TelnetConnectionError:
            self._log("触发发送失败")
            self._probe_buffer = buffer
            return 0, 0

        try:
            for _ in range(10):  # 最多读5秒
                chunk = self.telnet.read_any(timeout=self.DEFAULT_READ_TIMEOUT)
                if chunk:
                    buffer += chunk
                    result = _scan(buffer)
                    if result:
                        self._probe_buffer = buffer
                        return result
        except Exception as e:
            self._log(f"探测读取异常: {e}")

        self._log("未能探测到设备状态，从第1步开始")
        self._probe_buffer = buffer
        return 0, 0

    def _send_pattern_inputs(self, matched):
        """发送pattern的输入命令。"""
        for cmd in matched.inputs:
            if cmd:
                self._log(f"发送: {repr(cmd)}")
                if self.telnet:
                    try:
                        self.telnet.write(cmd.encode('utf-8'))
                        time.sleep(self.DEFAULT_SEND_DELAY)
                    except TelnetConnectionError as e:
                        self._log(f"发送时连接断开: {e}")
                        return False
                    except Exception as e:
                        self._log(f"发送失败: {e}")
                        return False
        return True

    def _take_probe_buffer(self) -> str:
        """取出探测阶段累积的设备输出并清空，供 expect/回调复用"""
        buf = self._probe_buffer or ""
        self._probe_buffer = ""
        return buf

    def _handle_probe_step(self, patterns, probe_step):
        """处理探测到的步骤，发送对应输入。"""
        total_steps = len(patterns)
        self._log(f"跳过已完成的步骤，设备当前处于: {patterns[probe_step].desc}")
        matched = patterns[probe_step]
        self._update_progress(probe_step, total_steps)
        self._log(f"进度: {self.progress}%")
        time.sleep(self.DEFAULT_READ_TIMEOUT * 0.6)

        # 探测时已读取的设备输出传给回调（如产品列表解析需要 received 文本）
        received = self._take_probe_buffer()
        if matched.callback:
            new_pats = matched.callback(patterns, probe_step, received)
            if new_pats is not None:
                patterns = new_pats

        if not self._send_pattern_inputs(matched):
            return False

        return True

    def _execute_phase(self, patterns, progress_start, progress_end, phase_name):
        """执行单个阶段的所有步骤。"""
        reconnect_count = 0
        max_reconnect = self.MAX_RECONNECT_ATTEMPTS
        total_steps = len(patterns)
        step = 0

        self.progress_scale_start = progress_start
        self.progress_scale_end = progress_end
        self.current_phase = phase_name
        self.is_done = False
        self.phase_complete = False
        self._log(f"---------- 进入阶段: {phase_name} ----------")

        # 探测阶段已读取的设备输出不应丢失，作为首次 expect 的初始 buffer
        initial_buffer = self._take_probe_buffer()

        while not self.stop_requested.is_set() and step < len(patterns):
            pattern = patterns[step]
            remaining = patterns[step:]
            regex_list = [p.regex for p in remaining]

            self._log(f"[{step+1}/{total_steps}] 等待: {pattern.desc}")

            index, received = self.telnet.expect(regex_list, timeout=pattern.timeout, initial=initial_buffer)
            initial_buffer = ""  # 初始 buffer 仅在首次 expect 使用

            if index == -1:
                self._log(f"超时: '{pattern.desc}' ({pattern.timeout}秒)")
                self.is_done = False
                return False
            elif index == -3:
                if self.phase_complete or self.is_done:
                    self._log("阶段已完成，设备连接断开（预期重启）")
                    if self.telnet:
                        self.telnet.close()
                        self.telnet = None
                    return True
                self._log("连接断开，尝试重连...")
                self.telnet.close()
                self.telnet = None
                if reconnect_count < max_reconnect:
                    reconnect_count += 1
                    if self._connect():
                        continue
                self._log(f"重连次数耗尽({max_reconnect}次)，退出")
                self.is_done = False
                return False
            else:
                actual_index = step + index
                matched = patterns[actual_index]
                self._log(f"匹配: {matched.desc}")
                self.current_status = f"当前阶段: {matched.desc}"
                self._update_progress(actual_index, total_steps)
                self._log(f"进度: {self.progress}%")

                time.sleep(self.DEFAULT_READ_TIMEOUT * 0.6)

                if matched.callback:
                    new_pats = matched.callback(patterns, actual_index, received)
                    if new_pats is not None:
                        patterns = new_pats

                if not self._send_pattern_inputs(matched):
                    if self.phase_complete or self.is_done:
                        self._log("阶段已完成，发送失败（预期设备重启）")
                        if self.telnet:
                            self.telnet.close()
                            self.telnet = None
                        return True
                    self._log("发送失败，尝试重连...")
                    if self.telnet:
                        self.telnet.close()
                        self.telnet = None
                    if reconnect_count < max_reconnect:
                        reconnect_count += 1
                        if self._connect():
                            continue
                    self._log(f"重连次数耗尽({max_reconnect}次)，退出")
                    self.is_done = False
                    return False

                step = actual_index + 1

                if self.is_done:
                    self.progress = self.progress_scale_end
                    return True

        return True

    def _wait_for_next_phase(self, phase_groups, next_phase_idx):
        """等待设备进入下一阶段。"""
        self._log("当前阶段完成，等待设备重启...")
        if self.telnet:
            self.telnet.close()
            self.telnet = None
        self.current_status = "等待设备重启..."

        probe_phase, probe_step = 0, 0
        # 用墙钟时间计算等待时长：connect/probe 的阻塞时间也计入，避免实际等待远超配置值
        start_wait = time.monotonic()
        while not self.stop_requested.is_set():
            if not self._sleep_interruptible(1):
                self._log("等待重启期间被中断")
                return False, 0, 0

            elapsed = time.monotonic() - start_wait
            if elapsed >= self.reboot_wait:
                self._log(f"等待 {self.reboot_wait:.0f} 秒后设备仍未进入下一阶段")
                return False, 0, 0

            telnet = None
            try:
                telnet = TelnetClient(
                    self.config.tel_ip, self.config.tel_port,
                    timeout=5, debug=self.debug
                )
                telnet.connect()
            except Exception:
                if int(elapsed) % 30 == 0:
                    self._log(f"仍在等待设备重启... ({elapsed:.0f}/{self.reboot_wait}秒)")
                if telnet:
                    try:
                        telnet.close()
                    except:
                        pass
                continue

            self.telnet = telnet
            probe_phase, probe_step = self._probe_device_state(phase_groups, next_phase_idx)
            if probe_phase >= next_phase_idx:
                self._log(f"设备已进入下一阶段 ({elapsed:.0f}秒)")
                return True, probe_phase, probe_step

            self._log(f"设备已连接但尚未进入下一阶段 (phase {probe_phase})，继续等待...")
            if self.telnet:
                try:
                    self.telnet.close()
                except:
                    pass
                self.telnet = None

        # 循环仅在用户中断时到达（探测成功会立即返回）
        self._log("等待重启期间被用户中断")
        return False, 0, 0

    def _process_patterns(self, phase_groups):
        """执行多阶段模式匹配流程。"""
        self.is_running = True

        try:
            if not self.telnet:
                if not self._connect():
                    self._log("无法建立Telnet连接")
                    return

            # 首次探测设备当前处于哪个 phase 的哪个 step
            probe_phase, probe_step = self._probe_device_state(phase_groups)

            # 从探测到的 phase 开始处理
            for phase_idx in range(probe_phase, len(phase_groups)):
                patterns, progress_start, progress_end, phase_name = phase_groups[phase_idx]
                cur_step = 0

                # 消费阶段间重启的探测结果：设备可能已处于后续阶段
                if self._pending_probe is not None:
                    pending_phase, pending_step = self._pending_probe
                    if pending_phase > phase_idx:
                        # 设备已越过当前阶段（重启后启动过快），直接跳过
                        self._log(f"设备已处于阶段 {pending_phase}，跳过阶段 {phase_idx}")
                        continue
                    if pending_phase == phase_idx:
                        self._pending_probe = None
                        cur_step = pending_step
                        self._log(f"使用重启后探测结果: phase {pending_phase}, step {cur_step}")
                elif phase_idx == probe_phase:
                    cur_step = probe_step

                # 处理探测到的 step（发送该步骤的输入，推进到下一步）
                if cur_step > 0:
                    if not self._handle_probe_step(patterns, cur_step):
                        break
                    cur_step += 1

                # 执行剩余步骤
                if cur_step < len(patterns):
                    if not self._execute_phase(patterns[cur_step:], progress_start,
                                              progress_end, phase_name):
                        break

                # 阶段间重启等待（探测结果记入 _pending_probe，供下一次循环迭代消费）
                if phase_idx + 1 < len(phase_groups) and not self.stop_requested.is_set():
                    success, next_probe_phase, next_probe_step = self._wait_for_next_phase(
                        phase_groups, phase_idx + 1
                    )
                    if not success:
                        break
                    if next_probe_phase > phase_idx + 1:
                        self._log(f"设备已越过阶段 {phase_idx + 1}，将从阶段 {next_probe_phase} 继续")
                    self._pending_probe = (next_probe_phase, next_probe_step)

        finally:
            self.is_running = False

    def reset_state(self):
        """重置状态"""
        self.is_done = False
        self.progress = 0
        self.current_status = "等待开始"
        self.current_phase = ""
        self.phase_complete = False
        self.progress_scale_start = 0
        self.progress_scale_end = 100
        self.stop_requested.clear()
        self.device_hash = ""
        self._pending_probe = None
        self._probe_buffer = ""

    def auto_hash(self):
        """提取设备HASH值"""
        self.reset_state()
        self._log("========== 开始提取设备HASH值 ==========")
        self._process_patterns([(self.hash_patterns[:], 0, 100, "hash")])

    def auto_recover(self):
        """恢复设备（刷写电子盘）"""
        self.reset_state()
        self._log("========== 开始恢复阶段（刷写电子盘）==========")

        # 定义阶段组：探测会自动识别设备处于哪个阶段
        phase_groups = [
            (self.recover_pre_reboot_patterns[:], 0, 20, "recover_pre_reboot"),
            (self.recover_post_reboot_patterns[:], 20, 100, "recover_post_reboot"),
        ]

        self._process_patterns(phase_groups)

        # 刷机完成后，设备会重启，等待重启完成
        if self.phase_complete and not self.stop_requested.is_set():
            self._log("刷机完成，设备正在重启...")
            if self.telnet:
                self.telnet.close()
                self.telnet = None
            self._sleep_interruptible(10)

    def auto_config(self):
        """配置设备（管理口IP）"""
        self.reset_state()
        self._log("========== 开始配置阶段（管理口IP）==========")
        self._process_patterns([(self.config_patterns[:], 0, 100, "config")])

    def auto_recover_and_config(self):
        """先恢复后配置"""
        self.reset_state()
        self._log("========== 开始恢复+配置流程 ==========")

        # 定义阶段组：探测会自动识别设备处于哪个阶段
        phase_groups = [
            (self.recover_pre_reboot_patterns[:], 0, 20, "recover_pre_reboot"),
            (self.recover_post_reboot_patterns[:], 20, 70, "recover_post_reboot"),
            (self.config_patterns[:], 70, 100, "config"),
        ]

        self._process_patterns(phase_groups)

    def stop(self):
        """停止当前流程"""
        self.stop_requested.set()
        if self.telnet:
            self.telnet.close()
            self.telnet = None

    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "progress": self.progress,
            "status": self.current_status,
            "phase": self.current_phase,
            "is_running": self.is_running,
            "is_done": self.is_done,
        }

    def get_logs(self) -> str:
        """获取日志"""
        return "\n".join(self.logs)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="设备自动化生产工具")
    parser.add_argument("--tel-ip", required=True, help="Telnet IP地址")
    parser.add_argument("--tel-port", type=int, default=23, help="Telnet端口")
    parser.add_argument("--mgt-ip", default="", help="管理口IP")
    parser.add_argument("--mgt-mask", default="", help="子网掩码")
    parser.add_argument("--mgt-gw", default="", help="网关")
    parser.add_argument("--server", default="", help="文件服务器IP")
    parser.add_argument("--image", default="", help="镜像描述")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式（输出详细 RECV 日志）"
    )
    parser.add_argument(
        "--reboot-wait",
        type=int,
        default=180,
        help="阶段间等待设备重启的时间（秒），默认180秒（3分钟）"
    )
    parser.add_argument(
        "--mode",
        choices=["recover", "config", "recover_config", "hash"],
        required=True,
        help="操作模式"
    )

    args = parser.parse_args()

    # hash 模式只需要 tel-ip 和 tel-port
    if args.mode != "hash":
        if not args.mgt_ip or not args.mgt_mask or not args.mgt_gw:
            parser.error("--mgt-ip, --mgt-mask, --mgt-gw are required for this mode")
    if args.mode in ("recover", "recover_config"):
        if not args.server or not args.image:
            parser.error("--server and --image are required for recover mode")

    config = DeviceConfig(
        tel_ip=args.tel_ip,
        tel_port=args.tel_port,
        mgt_ip=args.mgt_ip,
        mgt_mask=args.mgt_mask,
        mgt_gw=args.mgt_gw,
        server=args.server,
        image=args.image,
    )

    flow = AutoFlow(config, debug=args.debug, reboot_wait=args.reboot_wait)

    # 信号处理：Ctrl+C 直接抛出 KeyboardInterrupt 让脚本快速退出
    def signal_handler(signum, frame):
        print("\n[中断] 用户请求终止，正在退出...")
        flow.stop()
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.mode == "recover":
            flow.auto_recover()
        elif args.mode == "config":
            flow.auto_config()
        elif args.mode == "recover_config":
            flow.auto_recover_and_config()
        elif args.mode == "hash":
            flow.auto_hash()
    except Exception as e:
        print(f"\n[ERROR] 脚本异常退出: {e}")
        import traceback
        traceback.print_exc()

    # 始终输出最终状态，即使异常也不跳过
    print("\n" + "=" * 50)
    print("最终状态:")
    final_status = flow.get_status()
    print(f"  进度: {final_status['progress']}%")
    print(f"  状态: {final_status['status']}")
    print(f"  是否完成: {final_status['is_done']}")
    if flow.device_hash:
        print(f"\n{'=' * 50}")
        print(f"设备HASH值: {flow.device_hash}")

    print("\n日志:")
    print(flow.get_logs())


if __name__ == "__main__":
    main()