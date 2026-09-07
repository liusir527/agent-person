#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NF Simple MCP Server - 简单直接的方案
只注册 3 个工具：查看索引、读取文件、执行代码
"""

import json
import sys
import os
import io
import subprocess
import tempfile
from pathlib import Path

# ── 强制 stdout 为 UTF-8 ──
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdin.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

# ── 路径设置 ──
_MCP_DIR = Path(__file__).parent
_INDEX_PATH = _MCP_DIR / "index.md"
_NF_REQUESTS_DIR = _MCP_DIR / "nf_requests"


def nf_check_object(**kwargs):
    """检查对象是否存在

    :param object_type: 对象类型（network_object, service_object, zone, interface, time_object, user_object）
    :param base_url: NF 设备地址
    :param username: 用户名
    :param password: 密码
    :param object_name: 要查询的对象名称
    """
    object_type = kwargs.get("object_type", "").strip()
    base_url = kwargs.get("base_url", "").strip()
    username = kwargs.get("username", "").strip()
    password = kwargs.get("password", "").strip()
    object_name = kwargs.get("object_name", "").strip()

    if not all([object_type, base_url, username, password, object_name]):
        return json.dumps({
            "error": "缺少必需参数",
            "hint": "需要提供: object_type, base_url, username, password, object_name"
        }, ensure_ascii=False)

    # 构建查询代码
    check_code_map = {
        "network_object": f"""
from nf_requests.client import NFRequests
nf = NFRequests(base_url="{base_url}")
nf.basic.auth.manager_login(username="{username}", password="{password}")
result = nf.object.network_object.get_network_obj()
print("查询网络对象列表:")
if result:
    found = False
    for obj in result:
        if obj.get('name') == "{object_name}":
            print(f"✅ 对象存在: {{obj}}")
            found = True
            break
    if not found:
        print(f"❌ 对象不存在: {object_name}")
        print("需要先创建该网络对象")
else:
    print("获取网络对象列表失败")
""",
        "service_object": f"""
from nf_requests.client import NFRequests
nf = NFRequests(base_url="{base_url}")
nf.basic.auth.manager_login(username="{username}", password="{password}")
result = nf.object.server.get_service_obj()
print("查询服务对象列表:")
if result:
    found = False
    for obj in result:
        if obj.get('name') == "{object_name}":
            print(f"✅ 对象存在: {{obj}}")
            found = True
            break
    if not found:
        print(f"❌ 对象不存在: {object_name}")
        print("需要先创建该服务对象")
else:
    print("获取服务对象列表失败")
""",
        "zone": f"""
from nf_requests.client import NFRequests
nf = NFRequests(base_url="{base_url}")
nf.basic.auth.manager_login(username="{username}", password="{password}")
result = nf.network.zone.get_zone()
print("查询安全区列表:")
if result:
    found = False
    for zone in result:
        if zone.get('name') == "{object_name}":
            print(f"✅ 安全区存在: {{zone}}")
            found = True
            break
    if not found:
        print(f"❌ 安全区不存在: {object_name}")
        print("需要先创建该安全区")
else:
    print("获取安全区列表失败")
""",
        "interface": f"""
from nf_requests.client import NFRequests
nf = NFRequests(base_url="{base_url}")
nf.basic.auth.manager_login(username="{username}", password="{password}")
result = nf.network.interface.get_l3_physical_interface()
print("查询接口列表:")
if result:
    found = False
    for iface in result:
        if iface.get('name') == "{object_name}":
            print(f"✅ 接口存在: {{iface}}")
            found = True
            break
    if not found:
        print(f"❌ 接口不存在: {object_name}")
        print("需要先创建该接口")
else:
    print("获取接口列表失败")
"""
    }

    check_code = check_code_map.get(object_type)
    if not check_code:
        return json.dumps({
            "error": f"不支持的对象类型: {object_type}",
            "hint": "支持的类型: network_object, service_object, zone, interface"
        }, ensure_ascii=False)

    # 执行检查代码
    return nf_exec(code=check_code)


def nf_index(**kwargs):
    """返回 index.md 的完整内容

    AI 可以从中找到需要的模块和文件路径
    """
    if not _INDEX_PATH.exists():
        return json.dumps({
            "error": f"索引文件不存在: {_INDEX_PATH}"
        }, ensure_ascii=False)

    try:
        with open(_INDEX_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        return json.dumps({
            "success": True,
            "index_file": str(_INDEX_PATH),
            "content": content
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "error": f"读取索引文件失败: {e}"
        }, ensure_ascii=False)


def nf_read_file(**kwargs):
    """读取指定的 Python 文件内容

    :param file_path: 文件路径，相对于 nf_requests/，如 "policy/black_white_list.py"
    """
    file_path = kwargs.get("file_path", "").strip()

    if not file_path:
        return json.dumps({
            "error": "缺少文件路径",
            "hint": "请提供 file_path 参数，如: file_path='policy/black_white_list.py'"
        }, ensure_ascii=False)

    # 支持 index.md 中的路径格式
    if file_path.startswith("lib/nflib/nf_requests/"):
        file_path = file_path.replace("lib/nflib/nf_requests/", "")

    full_path = _NF_REQUESTS_DIR / file_path

    if not full_path.exists():
        return json.dumps({
            "error": f"文件不存在: {full_path}",
            "hint": "请从 nf_index 返回的 index.md 中获取正确的文件路径"
        }, ensure_ascii=False)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return json.dumps({
            "success": True,
            "file_path": str(full_path),
            "content": content
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "error": f"读取文件失败: {e}"
        }, ensure_ascii=False)


def _extract_dependencies(code):
    """从代码中提取可能的依赖关系

    :param code: Python 代码
    :return: 依赖信息字典
    """
    deps = {
        "needs_login": False,
        "references": []  # 引用的对象（网络对象、服务对象等）
    }

    # 检测是否需要登录
    if "nf.policy." in code or "nf.network." in code or "nf.object." in code:
        deps["needs_login"] = True

    # 检测网络对象引用
    if "src_obj=" in code or "dst_obj=" in code or "network_obj" in code:
        deps["references"].append({
            "type": "network_object",
            "hint": "需要先创建网络对象：nf.object.network_object.create_or_update_network_obj()"
        })

    # 检测服务对象引用
    if "server_obj=" in code or "service_obj=" in code:
        deps["references"].append({
            "type": "service_object",
            "hint": "需要先创建服务对象：nf.object.server.create_or_update_service_obj()"
        })

    # 检测安全区引用
    if "src_zone=" in code or "dst_zone=" in code or "zone=" in code:
        deps["references"].append({
            "type": "zone",
            "hint": "需要先创建安全区：nf.network.zone.create_or_update_zone()"
        })

    # 检测接口引用
    if "interface=" in code or "in_interface=" in code or "out_interface=" in code:
        deps["references"].append({
            "type": "interface",
            "hint": "需要先创建接口：nf.network.interface.create_l3_physical_interface()"
        })

    # 检测时间对象引用
    if "time_obj=" in code or "schedule=" in code:
        deps["references"].append({
            "type": "time_object",
            "hint": "需要先创建时间对象：nf.object.time.create_or_update_time_obj()"
        })

    # 检测用户对象引用
    if "user_obj=" in code or "user_group=" in code:
        deps["references"].append({
            "type": "user_object",
            "hint": "需要先创建用户对象：nf.object.user.create_or_update_user_obj()"
        })

    return deps


def _analyze_error(stderr, code):
    """分析错误信息并给出建议

    :param stderr: 标准错误输出
    :param code: 执行的代码
    :return: 错误分析和建议
    """
    analysis = []

    # 提取依赖信息
    deps = _extract_dependencies(code)

    # 常见错误模式分析
    if "AttributeError" in stderr and "has no attribute" in stderr:
        if "'NFRequests' object has no attribute" in stderr:
            analysis.append("❌ NFRequests 对象缺少属性")
            analysis.append("💡 可能原因：")
            analysis.append("  1. 模块未正确加载 - 检查是否调用了正确的模块路径")
            analysis.append("  2. 需要先登录 - 某些模块需要先调用 nf.basic.auth.manager_login()")
            analysis.append("  3. 拼写错误 - 检查模块名和方法名是否正确")

    elif "ModuleNotFoundError" in stderr or "ImportError" in stderr:
        analysis.append("❌ 模块导入失败")
        analysis.append("💡 可能原因：")
        analysis.append("  1. nf_requests 路径未正确设置")
        analysis.append("  2. 缺少依赖包 - 检查 requests 等依赖是否安装")

    elif "NameError" in stderr and "is not defined" in stderr:
        analysis.append("❌ 变量或函数未定义")
        analysis.append("💡 可能原因：")
        analysis.append("  1. 忘记创建 NFRequests 对象")
        analysis.append("  2. 变量名拼写错误")

        # 检查是否忘记创建 nf 对象
        if "nf" not in code or "NFRequests" not in code:
            analysis.append("  ⚠️  代码中似乎没有创建 nf = NFRequests(...)")

    elif "TypeError" in stderr:
        if "missing" in stderr and "required positional argument" in stderr:
            analysis.append("❌ 缺少必需参数")
            analysis.append("💡 使用 nf_read_file 查看函数签名，确认所有必需参数")
        elif "got an unexpected keyword argument" in stderr:
            analysis.append("❌ 参数名错误")
            analysis.append("💡 使用 nf_read_file 查看函数的正确参数名")

    elif "ConnectionError" in stderr or "Timeout" in stderr or "Failed to establish" in stderr:
        analysis.append("❌ 网络连接失败")
        analysis.append("💡 可能原因：")
        analysis.append("  1. base_url 地址错误或设备不可达")
        analysis.append("  2. 端口号错误")
        analysis.append("  3. 网络防火墙阻止连接")
        analysis.append("  4. SSL 证书验证失败（NF 默认禁用了 SSL 警告）")

    elif "401" in stderr or "Unauthorized" in stderr:
        analysis.append("❌ 认证失败")
        analysis.append("💡 可能原因：")
        analysis.append("  1. 用户名或密码错误")
        analysis.append("  2. 账号被锁定或禁用")
        analysis.append("  3. 使用了错误权限的账号（weboper/webpolicy/webaudit）")

    elif "403" in stderr or "Forbidden" in stderr:
        analysis.append("❌ 权限不足")
        analysis.append("💡 账号权限不匹配：")
        analysis.append("  - weboper: 用于 nf.system.* 模块")
        analysis.append("  - webpolicy: 用于 nf.network.*, nf.policy.*, nf.object.* 等")
        analysis.append("  - webaudit: 用于 nf.log.* 部分功能")

    elif "404" in stderr or "Not Found" in stderr:
        analysis.append("❌ API 端点不存在")
        analysis.append("💡 可能原因：")
        analysis.append("  1. 方法名错误")
        analysis.append("  2. 设备版本不支持该功能")

    elif "500" in stderr or "Internal Server Error" in stderr:
        analysis.append("❌ 设备内部错误")
        analysis.append("💡 可能原因：")
        analysis.append("  1. 参数格式错误导致设备处理失败")
        analysis.append("  2. 设备服务异常")
        analysis.append("  3. 查看设备日志获取详细信息")

    elif "KeyError" in stderr:
        analysis.append("❌ 字典键不存在")
        analysis.append("💡 API 返回的数据结构与预期不符，检查返回值")

    # 检查对象不存在的错误
    if "不存在" in stderr or "does not exist" in stderr.lower() or "not found" in stderr.lower():
        analysis.append("❌ 引用的对象不存在")
        analysis.append("💡 需要先创建依赖的对象：")

        # 根据代码中的引用给出具体建议
        if deps["references"]:
            for ref in deps["references"]:
                analysis.append(f"  - {ref['type']}: {ref['hint']}")
        else:
            analysis.append("  - 检查网络对象、服务对象、安全区、接口等是否已创建")
            analysis.append("  - 使用 nf.object.network_object.get_network_obj() 等方法检查对象是否存在")

    # 检查是否缺少登录步骤
    if "login" not in code.lower() and deps["needs_login"]:
        analysis.append("")
        analysis.append("⚠️  注意：代码中没有看到登录操作")
        analysis.append("大多数操作需要先调用: nf.basic.auth.manager_login(username='...', password='...')")

    # 依赖检查提示
    if deps["references"] and len(analysis) > 0:
        analysis.append("")
        analysis.append("📋 依赖检查建议：")
        analysis.append("  1. 先查询对象是否存在（get_xxx 方法）")
        analysis.append("  2. 如果不存在，先创建依赖对象")
        analysis.append("  3. 再创建引用这些对象的策略")

    return "\n".join(analysis) if analysis else None


def nf_exec(**kwargs):
    """执行 Python 代码

    :param code: Python 代码（多行字符串），例如：
        from nf_requests.client import NFRequests
        nf = NFRequests(base_url="https://10.66.240.122:9433")
        nf.basic.auth.manager_login(username="webpolicy", password="qwert12345")
        result = nf.policy.black_white_list.create_or_update_black_list(
            action="create",
            ip_type="destIp",
            ip="5.5.6.1",
            comment="黑名单测试"
        )
        print(result)
    """
    code = kwargs.get("code", "").strip()

    if not code:
        return json.dumps({
            "error": "缺少代码",
            "hint": "请提供 code 参数"
        }, ensure_ascii=False)

    # 创建临时执行脚本
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        script_path = f.name

        # 添加必要的路径设置和错误追踪
        full_code = f"""# -*- coding: utf-8 -*-
import sys
import traceback
from pathlib import Path

# 设置路径
_MCP_DIR = Path(r'{_MCP_DIR}')
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

try:
    # 用户代码
"""
        # 缩进用户代码
        indented_code = '\n'.join('    ' + line if line.strip() else '' for line in code.split('\n'))
        full_code += indented_code
        full_code += f"""
except Exception as e:
    print(f"\\n{'='*60}", file=sys.stderr)
    print(f"执行出错: {{type(e).__name__}}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        f.write(full_code)

    try:
        # 执行脚本（Windows 需要特别处理编码）
        import locale
        system_encoding = locale.getpreferredencoding()

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'  # 替换无法解码的字符
        )

        # 分析错误
        error_analysis = None
        if result.returncode != 0 and result.stderr:
            error_analysis = _analyze_error(result.stderr, code)

        output = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

        if error_analysis:
            output["error_analysis"] = error_analysis

        # 清理临时文件
        try:
            Path(script_path).unlink()
        except:
            pass

        return json.dumps(output, ensure_ascii=False)

    except subprocess.TimeoutExpired:
        try:
            Path(script_path).unlink()
        except:
            pass
        return json.dumps({
            "error": "执行超时（60秒）",
            "hint": "可能是网络请求hang住或者代码进入死循环"
        }, ensure_ascii=False)

    except Exception as e:
        try:
            Path(script_path).unlink()
        except:
            pass
        return json.dumps({
            "error": f"执行失败: {e}"
        }, ensure_ascii=False)


# ================================================================
# MCP JSON-RPC 2.0 Server
# ================================================================

class NfSimpleServer:
    """NF Simple MCP Server - 注册 4 个工具"""

    def __init__(self):
        self.tools = {
            "nf_index": {
                "name": "nf_index",
                "description": "返回 index.md 的完整内容。包含所有 NF 模块的调用方式、文件路径和使用示例。",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "nf_read_file": {
                "name": "nf_read_file",
                "description": "读取指定的 Python 源文件内容。从 index.md 中找到文件路径后，使用此工具查看具体的函数定义和参数。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径，相对于 nf_requests/，如 'policy/black_white_list.py'"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "nf_check_object": {
                "name": "nf_check_object",
                "description": "检查对象是否存在。在创建策略前，检查依赖的对象（网络对象、服务对象、安全区、接口等）是否已创建。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "object_type": {
                            "type": "string",
                            "description": "对象类型：network_object, service_object, zone, interface"
                        },
                        "base_url": {
                            "type": "string",
                            "description": "NF 设备地址，如 https://10.66.240.122:9433"
                        },
                        "username": {
                            "type": "string",
                            "description": "用户名（webpolicy/weboper/webaudit）"
                        },
                        "password": {
                            "type": "string",
                            "description": "密码"
                        },
                        "object_name": {
                            "type": "string",
                            "description": "要查询的对象名称"
                        }
                    },
                    "required": ["object_type", "base_url", "username", "password", "object_name"]
                }
            },
            "nf_exec": {
                "name": "nf_exec",
                "description": "执行 Python 代码调用 NF API。按照 index.md 中的示例格式编写代码，创建 NFRequests 对象并调用对应的方法。自动分析错误并给出依赖检查建议。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python 代码（多行字符串）"
                        }
                    },
                    "required": ["code"]
                }
            }
        }

    def _send(self, response):
        """向 stdout 写入 JSON-RPC 响应"""
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + '\n')
        sys.stdout.flush()

    def _handle_initialize(self, req_id, params):
        """处理 initialize 请求"""
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "nf-simple",
                    "version": "1.0.0",
                },
            },
        }

    def _handle_list(self, req_id):
        """处理 tools/list 请求"""
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["inputSchema"],
                    }
                    for t in self.tools.values()
                ]
            },
        }

    def _handle_call(self, req_id, name, arguments):
        """处理 tools/call 请求"""
        handlers = {
            "nf_index": nf_index,
            "nf_read_file": nf_read_file,
            "nf_check_object": nf_check_object,
            "nf_exec": nf_exec,
        }

        if name not in handlers:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {name}"},
            }

        try:
            result = handlers[name](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)},
            }

    def handle_request(self, request):
        """路由 JSON-RPC 请求到对应 handler"""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return self._handle_initialize(req_id, params)
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return self._handle_list(req_id)
        elif method == "tools/call":
            return self._handle_call(req_id, params.get("name", ""), params.get("arguments", {}))
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    def run(self):
        """stdio 主循环"""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            response = self.handle_request(request)
            if response is not None:
                self._send(response)


def main():
    server = NfSimpleServer()
    server.run()


if __name__ == "__main__":
    main()
