import base64
import html
import json
import re
from pathlib import Path

import rsa
import requests
requests.packages.urllib3.disable_warnings()
from .Log import logger

PUBLIC_KEY = '''-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCCOd4TubIzK5GLd1O3lfLlp0vnRlD8OgAdbUC6zHhkSqVifRIX8xwh08cHM+fjym4J0HfutpuRMHW0NFitQrdcL7vHYBan5G6PVqjTYd01SKz1ox6SRq2VXaKwZTClSXoz7W1xLNrkH2ABFffoi+fqWoAw6LvoWPKc4g636+J+SwIDAQAB
-----END PUBLIC KEY-----'''

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OTPD_COOKIE_DIR = PROJECT_ROOT / "runtime" / "cookies" / "otpd"
AUTHSOURCE_URL = "https://auth.nsfocus.com/uip/api/au/authsource/"
AUTHENTICATE_URL = "https://auth.nsfocus.com/uip/api/custom/authenticate/"
LOGIN_SERVICE_URL = "https://auth.nsfocus.com/uip/api/sso/cas/login?service=https://boxotpd.intra.nsfocus.com/auth/login"
OTPD_URL = "https://boxotpd.intra.nsfocus.com/otpd/"
OTPD_HEADERS = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
              "application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


def _resolve_otpd_cookie_dir(cookie_dir=None) -> Path:
    return Path(cookie_dir) if cookie_dir is not None else DEFAULT_OTPD_COOKIE_DIR


def save_otpd_auth_info(auth_info, name: str, cookie_dir=None) -> dict:
    """保存 OTPD V2 认证信息到 runtime/cookies/otpd，不保存 --opt 传入的口令。"""
    if hasattr(auth_info, "items"):
        auth_dict = dict(auth_info)
    else:
        auth_dict = requests.utils.dict_from_cookiejar(auth_info)

    auth_dir = _resolve_otpd_cookie_dir(cookie_dir)
    auth_dir.mkdir(parents=True, exist_ok=True)
    file_path = auth_dir / (name if name.endswith(".json") else f"{name}.json")
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(auth_dict, file, ensure_ascii=False)
    return auth_dict


def load_otpd_auth_info(name: str, cookie_dir=None) -> dict:
    """读取 OTPD V2 本地认证信息，不存在时返回空字典。"""
    file_path = _resolve_otpd_cookie_dir(cookie_dir) / (name if name.endswith(".json") else f"{name}.json")
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as file:
        return json.load(file)


def parse_otpd_password_html(response_text: str) -> dict:
    """解析一次一密页面，返回远程协助端口和 develop 口令。"""
    port_match = re.search(
        r"<td[^>]*>\s*远程协助端口\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>",
        response_text or "",
        re.S,
    )
    password_match = re.search(
        r"<td[^>]*>\s*develop\s*口令.*?</td>\s*<td[^>]*>\s*<div[^>]*>\s*(.*?)\s*</div>",
        response_text or "",
        re.S,
    )
    if not port_match or not password_match:
        raise ValueError("无法从一次一密页面解析远程协助端口或 develop 口令")
    return {
        "remote_port": int(port_match.group(1)),
        "develop_password": html.unescape(password_match.group(1).strip()),
    }


def parse_otpd_csrf_token(response_text: str) -> str:
    """解析 OTPD 页面中的 csrf_token。"""
    token_match = re.search(
        r"<input[^>]*name=[\"']csrf_token[\"'][^>]*value=[\"']([^\"']+)[\"']",
        response_text or "",
        re.S,
    )
    if token_match:
        return html.unescape(token_match.group(1).strip())

    token_match = re.search(
        r"<input[^>]*value=[\"']([^\"']+)[\"'][^>]*name=[\"']csrf_token[\"']",
        response_text or "",
        re.S,
    )
    if token_match:
        return html.unescape(token_match.group(1).strip())

    return ""


def parse_cookie_string(cookie_string: str) -> dict:
    """解析浏览器 Cookie 字符串，返回可传给 requests cookie jar 的字典。"""
    cookies = {}
    for item in (cookie_string or "").split(";"):
        if "=" not in item:
            continue
        key, value = item.strip().split("=", 1)
        if key:
            cookies[key] = value
    return cookies


def get_auth_server_id(otpd_session=None, timeout: int = 60):
    """获取 OTPD V2 auth_server_id。"""
    otpd_session = otpd_session or requests.session()
    response = otpd_session.post(url=AUTHSOURCE_URL, data={}, headers=OTPD_HEADERS, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"获取 auth_server_id 失败: HTTP {response.status_code}")
    result = response.json()
    return result["data"]["auth_types"][0]["auth_server_id"]


def login_otpd_v2(otpd_session, username: str, auth_code: str, cookie_dir=None, timeout: int = 60) -> bool:
    """使用用户名和完整认证口令完成 OTPD V2 登录，并保存认证后返回的信息。"""
    if not username or not auth_code:
        raise ValueError("OTPD V2 登录需要 username 和 auth_code")

    headers = dict({"Referer": "https://auth.nsfocus.com/no-referrer"}, **OTPD_HEADERS)
    data = {
        "username": username,
        "captcha": auth_code,
        "auth_server_id": get_auth_server_id(otpd_session, timeout=timeout),
        "auth_type": "otp",
        "redirect_uri": "https://boxotpd.intra.nsfocus.com/auth/login",
    }
    response = otpd_session.post(url=AUTHENTICATE_URL, data=data, headers=headers, timeout=timeout)
    
    if response.status_code != 200:
        raise RuntimeError(f"获取 auth_session 失败: HTTP {response.status_code}")
    else:
        logger.info("opt认证成功")
    save_otpd_auth_info(response.cookies, "auth_session", cookie_dir=cookie_dir)

    return refresh_otpd_session(otpd_session, cookie_dir=cookie_dir, timeout=timeout)


def refresh_otpd_session(otpd_session, cookie_dir=None, timeout: int = 60) -> bool:
    """使用已保存的 auth_session/CASTGC 获取并保存 OTPD session。"""
    headers = dict({"Referer": "https://auth.nsfocus.com/"}, **OTPD_HEADERS)
    auth_session = load_otpd_auth_info("auth_session", cookie_dir=cookie_dir)
    if not auth_session:
        return False

    castgc = load_otpd_auth_info("CASTGC", cookie_dir=cookie_dir)
    cookies = dict(auth_session)
    if castgc:
        cookies.update(castgc)
    else:
        cookies.setdefault("auth_cfg_session", "")

    response = otpd_session.get(url=LOGIN_SERVICE_URL, headers=headers, cookies=cookies, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"获取 OTPD session 失败: HTTP {response.status_code}")
    if len(response.cookies.values()) == 0:
        return False

    if response.history:
        save_otpd_auth_info(response.history[0].cookies, "CASTGC", cookie_dir=cookie_dir)
    save_otpd_auth_info(response.cookies, "session", cookie_dir=cookie_dir)
    return True


def get_otpd_csrf_token(otpd_session, cookie_dir=None, timeout: int = 60) -> str:
    """使用本地 session Cookie 获取 OTPD 页面 csrf_token。"""
    headers = dict({"Host": "boxotpd.intra.nsfocus.com"}, **OTPD_HEADERS)
    cookies = load_otpd_auth_info("session", cookie_dir=cookie_dir)
    if cookies:
        otpd_session.cookies.update(cookies)

    response = otpd_session.get(url=OTPD_URL, headers=headers, cookies=cookies or None, verify=False, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"获取 csrf_token 失败: HTTP {response.status_code}")

    csrf_token = parse_otpd_csrf_token(response.text)
    if response.cookies:
        save_otpd_auth_info(response.cookies, "session", cookie_dir=cookie_dir)
    return csrf_token


def get_otpd_password(
    secret_code=None,
    customer=1,
    reason=1,
    onsite_engineer="zhanggongquan",
    remote_engineer="zhanggongquan",
    cookie=None,
    username=None,
    auth_code=None,
    cookie_dir=None,
    timeout: int = 60,
):
    """获取 OTPD V2 远程协助端口和 develop 口令。"""
    if not secret_code:
        raise ValueError("get_otpd_password 需要 secret_code")

    otpd_session = requests.session()
    otpd_session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})

    if username and auth_code:
        login_otpd_v2(otpd_session, username=username, auth_code=auth_code, cookie_dir=cookie_dir, timeout=timeout)
    elif cookie:
        otpd_session.cookies.update(parse_cookie_string(cookie))
    else:
        if not refresh_otpd_session(otpd_session, cookie_dir=cookie_dir, timeout=timeout):
            raise RuntimeError("刷新 OTPD session 失败，请使用 --opt username auth_code 重新刷新认证信息")
        otpd_session.cookies.update(load_otpd_auth_info("session", cookie_dir=cookie_dir))
    csrf_token = get_otpd_csrf_token(otpd_session, cookie_dir=cookie_dir, timeout=timeout)
    if not csrf_token:
        raise RuntimeError("获取 csrf_token 失败，请使用 --opt username auth_code 刷新认证信息")

    data = {"customer": customer,
            "reason": reason,
            "onsite_engineer": onsite_engineer,
            "remote_engineer": remote_engineer,
            "secret_code": secret_code,
            "csrf_token": csrf_token}
    headers = dict({
        "Referer": OTPD_URL,
        "Origin": "https://boxotpd.intra.nsfocus.com",
        "Host": "boxotpd.intra.nsfocus.com",
    }, **OTPD_HEADERS)
    response = otpd_session.post(url=OTPD_URL, data=data, headers=headers, verify=False, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"OTPD 请求失败: HTTP {response.status_code}")
    if response.cookies:
        save_otpd_auth_info(response.cookies, "session", cookie_dir=cookie_dir)

    return parse_otpd_password_html(response.text)


def encrypt_msg(message, public_key=None):
    """

    :param str message: the message to encrypt.
    :param str public_key: RSA public key
    :return:
    """
    #print(message)
    public_key = public_key if public_key is not None else PUBLIC_KEY
    message = message.encode('utf-8')

    # 兼容 PEM 格式公钥（包含 BEGIN/END PUBLIC KEY）
    if 'BEGIN PUBLIC KEY' in public_key:
        pub = rsa.PublicKey.load_pkcs1_openssl_pem(public_key.encode('utf-8'))
    else:
        pub = rsa.PublicKey.load_pkcs1_openssl_der(base64.b64decode(public_key))

    encrypted = rsa.encrypt(message, pub)
    result = base64.b64encode(encrypted).decode("utf-8")
    return result

def dict_get_id(dict_data):
    if isinstance(dict_data, dict):
        if(dict_data['status']==2000):
            return dict_data['result']['list'][0]['id']
    else:
        return False


def range_ipv4(ip_str="1.1.1.1", n=1000):
    """
    生成从起始IP开始的n个连续IP地址
    :param start_ip: 起始IP地址，如 "192.168.1.1"
    :param n: 要生成的IP数量
    :return: 结束IP地址
    """
    # 分割起始IP
    parts = list(map(int, ip_str.split('.')))

    # 将IP地址转换为整数
    ip_num = (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]

    # 加上n-1（因为包含起始IP）
    ip_num += n

    # 转换回点分十进制格式
    a = (ip_num >> 24) & 0xFF
    b = (ip_num >> 16) & 0xFF
    c = (ip_num >> 8) & 0xFF
    d = ip_num & 0xFF

    return f"{a}.{b}.{c}.{d}"

def range_ipv4_sub(a=1,b=1,c=1,d=1,sub=24,n=1000):
    c = n % 255
    b += n // 255
    if b > 255:
        a = b //255
        b = b % 255
    ip = str(a)+"."+str(b)+"."+str(c)+"."+str(d)+"/"+ str(sub)
    return  ip

def range_ipv4_addr(a=1,b=1,c=1,d=1,n=20):
    if((d+n) > 255):
        c += (d+n) // 255
        d = (d+n) % 255
    else:
        d = d+n
    if c > 255:
        b = c //255
        c = c % 255
    ip = str(a)+"."+str(b)+"."+str(c)+"."+str(d)
    return  ip

def range_ipv4_addr_sub(a=1,b=1,c=1,d=1,sub=24,n=20):
    d = n+d
    ip = str(a)+"."+str(b)+"."+str(c)+"."+str(d)+"/"+ str(sub)
    return  ip

def rang_ip6_sub(ip6="200:1:1::1",sub=64,n=1000):
    ip6_split=ip6.split("::")
    ip6=ip6_split[0].split(":")
    ip6_host=ip6_split[1]
    ip6_0 =ip6[:-1]
    ip6_1 = ip6[-1]


    ip6_1 = str(hex(int(ip6_1,16)+n))[2:]
    ip6=ip6_0[0]
    if(len(ip6_0) >1):
        for i in range(1,len(ip6_0)):
            ip6 = ip6+":"+ip6_0[i]
    ip6 =ip6 +":"+ip6_1+"::"+ip6_host+"/"+str(sub)
    return ip6


def range_mac_address(mac_str="00:00:00:00:00:00", n=1):
    """
    根据MAC地址字符串和增量n生成新的MAC地址
    :param mac_str: MAC地址字符串，支持 : - . 分隔或无分隔符
    :param n: 增量值
    :return: 新的MAC地址字符串
    """
    import re

    # 移除所有分隔符和空格
    mac_clean = re.sub(r'[:\-\.\s]', '', mac_str)

    # 确保是12个十六进制字符
    if len(mac_clean) != 12:
        raise ValueError(f"MAC地址格式错误: {mac_str}")

    # 将MAC地址转换为整数
    mac_int = int(mac_clean, 16)

    # 加上增量
    mac_int += n

    # 提取各个字节（从最高位到最低位）
    a = (mac_int >> 40) & 0xFF
    b = (mac_int >> 32) & 0xFF
    c = (mac_int >> 24) & 0xFF
    d = (mac_int >> 16) & 0xFF
    e = (mac_int >> 8) & 0xFF
    f = mac_int & 0xFF

    # 格式化为MAC地址字符串
    return f"{a:02X}:{b:02X}:{c:02X}:{d:02X}:{e:02X}:{f:02X}"


