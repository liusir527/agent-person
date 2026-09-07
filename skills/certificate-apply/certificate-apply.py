#!/usr/bin/env python3
"""
绿盟科技证书申请自动化脚本 (基于 curl)

使用 subprocess 调用 curl，避免 Python requests 与 PHP 系统的兼容问题。

用法:
    python certificate-apply.py <用户名> <PIN码> <HASH> <UIP>
    python certificate-apply.py <用户名> <PIN码> <HASH> <UIP> --version 6.0.6 --dev nf

默认参数:
  申请人相关: 与用户名相同
  产品: NF (ID=51), 2核
  功能: fw qos ddos ipsecvpn appid sdwan
  有效期: 当前日期 + 1年

可配置项:
  --version   6.0.5 (默认) / 6.0.6
  --dev       vnf (默认) / nf / sg
"""

import argparse
import datetime
import os
import re
import subprocess
import sys
import urllib.parse

# 版本号 → API value 映射（来自表单）
VERSION_MAP = {
    "6.0.5": "6",
    "6.0.6": "7",
    "6.0.3": "5",
    "6.0.2": "4",
    "6.0.1": "3",
    "6.0.0": "1",
}

# 显示产品 → API value 映射
DISPLAY_MAP = {
    "vnf": "vnf",
    "nf": "nf",
    "sg": "sg",
}

BASE_URL = "http://10.42.42.76"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# env_config 创建基准目录：固定为 AGENT_ASSETS_DIR（默认 E:\agent_assets），与 deploy-build 约定一致；
# AGENT_ASSETS_DIR 环境变量可覆盖。原实现由 SCRIPT_DIR 上溯推导，脚本被复制/重装后易漂移。
AGENT_ASSETS_DIR = os.environ.get("AGENT_ASSETS_DIR") or r"E:\agent_assets"
CERT_DIR = os.path.normpath(os.path.join(AGENT_ASSETS_DIR, ".dsh", "env_config", "certificate-apply"))
COOKIE_FILE = os.path.join(CERT_DIR, ".cookies.tmp")
os.makedirs(CERT_DIR, exist_ok=True)  # 登录阶段即写 COOKIE_FILE，目录须提前存在

DEFAULTS = {
    "applyer": "liuxing",  # fallback if username empty
    "product_line_id": "1",
    "product_id": "51",
    "device_type": "2",
    "license_type": "1",
    "sales": "0",
    "secret": "0",
    "core_num": "2",
    "nic": "0",
    "holiday_time": "1",
    "extend": "1",
    "features": ["fw", "qos", "ddos", "ipsecvpn", "appid", "sdwan"],
}


class CertError(Exception):
    pass


def _curl_run(args, timeout=30):
    """Run curl, return (stdout_bytes, returncode)."""
    cmd = ["curl", "-s", "-c", COOKIE_FILE, "-b", COOKIE_FILE] + args
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    return r.stdout, r.returncode


def curl(args, timeout=30):
    """Run curl, return stdout as decoded UTF-8 string."""
    out, _ = _curl_run(args, timeout)
    return out.decode("utf-8", errors="replace")


def curl_to_file(args, dest, timeout=30):
    """Run curl and save output to dest file."""
    cmd = ["curl", "-s", "-c", COOKIE_FILE, "-b", COOKIE_FILE] + args
    with open(dest, "wb") as f:
        subprocess.run(cmd, stdout=f, timeout=timeout)


def login(username, password):
    print(f"[1/4] 登录: {username} ...", end=" ")
    curl(["http://10.42.42.76/user/requireLogin", "-o", os.devnull])
    r = curl([
        "-X", "POST", "http://10.42.42.76/user/login",
        "--data-urlencode", f"user[account]={username}",
        "--data-urlencode", f"user[password]={password}",
        "-L",
    ])
    if "window.top.location" not in r:
        raise CertError("登录失败")
    print("OK")


def query_device(hash_val):
    print(f"[2/4] 查询设备: HASH={hash_val} ...", end=" ")
    curl([
        "-X", "POST", f"{BASE_URL}/device/index",
        "-d", f"search[hash]={hash_val}&search[serial]={hash_val}&customerId=-1",
        "-o", os.devnull,
    ])

    text = curl([
        f"{BASE_URL}/device/indexContent?search%5BcustomerId%5D=-1&search%5Bhash%5D={hash_val}&search%5Bserial%5D={hash_val}",
    ])

    m_total = re.search(r'total="(\d+)"', text)
    total = int(m_total.group(1)) if m_total else 0

    if total == 0:
        print("设备不存在")
        return None, None

    device_id = re.search(r'deviceid="(\d+)"', text)
    print(f"已存在 (id={device_id.group(1) if device_id else '?'})")

    cdata_matches = re.findall(r'<td><!\s*\[CDATA\[\s*(.*?)\s*\]\]></td>', text, re.DOTALL)
    customer_raw = cdata_matches[5].strip() if len(cdata_matches) >= 6 else ""

    m_short = re.search(r'\((-\d+)\)', customer_raw)
    customer_short = m_short.group(1) if m_short else None
    customer_full = re.sub(r'\(-\d+\)', '', customer_raw).strip()
    print(f"    客户: {customer_full} ({customer_short})")
    return customer_short, customer_full


def phase_a_apply(hash_val, customer_short, start_date, end_date, username=""):
    print("    阶段A: 提交申请 ...", end=" ")
    applyer = username or DEFAULTS["applyer"]
    curl([
        f"{BASE_URL}/licenseApply/response", "-G",
        "-d", f"field=all&show=true&serial={hash_val}",
        "-d", f"applyer={applyer}",
        "-d", f"itemName={applyer}",
        "-d", f"pactName={applyer}",
        "-d", f"customer={customer_short}",
        "-d", "agentName=", "-d", "projectNumber=",
        "-o", os.devnull,
    ])

    r = curl([
        "-X", "POST", f"{BASE_URL}/licenseApply/apply",
        "--data-urlencode", f"license[holidayTime]={DEFAULTS['holiday_time']}",
        "--data-urlencode", f"license[extend]={DEFAULTS['extend']}",
        "--data-urlencode", f"license[applyer]={applyer}",
        "--data-urlencode", f"license[applyDate]={start_date}",
        "--data-urlencode", "license[agentName]=",
        "--data-urlencode", f"license[itemName]={applyer}",
        "--data-urlencode", f"license[pactName]={applyer}",
        "--data-urlencode", f"license[folio]={applyer}",
        "--data-urlencode", "license[projectNumber]=",
        "-d", f"license[productLineId]={DEFAULTS['product_line_id']}",
        "-d", f"license[product]={DEFAULTS['product_id']}",
        "--data-urlencode", f"license[customer]={customer_short}",
        "--data-urlencode", f"license[serial]={hash_val}",
        "--data-urlencode", "license[mail]=",
        "--data-urlencode", "license[mark]=",
    ])
    if "申请下一代防火墙证书" not in r:
        raise CertError("阶段A失败: 未返回证书规格页")
    print("OK")


def phase_b_insert(hash_val, customer_full, start_date, end_date, version_val="6", display_val="vnf", username=""):
    print("    阶段B: insertNf ...", end=" ")
    applyer = username or DEFAULTS["applyer"]

    customer_enc = urllib.parse.quote(customer_full)
    title_enc = "%E7%94%B3%E8%AF%B7%E4%B8%8B%E4%B8%80%E4%BB%A3%E9%98%B2%E7%81%AB%E5%A2%99%E8%AF%81%E4%B9%A6"
    submit_enc = "%E6%8F%90%E4%BA%A4"

    body = (
        f"license%5BapplyDate%5D={start_date}"
        f"&license%5Bcustomer%5D={customer_enc}"
        f"&license%5BagentName%5D="
        f"&license%5BitemName%5D={applyer}"
        f"&license%5BpactName%5D={applyer}"
        f"&license%5BprojectNumber%5D="
        f"&license%5BproductLineId%5D={DEFAULTS['product_line_id']}"
        f"&license%5Bmodel%5D=APPLY"
        f"&license%5BlicenseApplyId%5D="
        f"&license%5BsubmitName%5D={submit_enc}"
        f"&license%5Btitle%5D={title_enc}"
        f"&license%5Bserial%5D={hash_val}"
        f"&license%5Bhash%5D="
        f"&license%5Bapplyer%5D={DEFAULTS['applyer']}"
        f"&license%5BendDate%5D={end_date}"
        f"&license%5Bproduct%5D={DEFAULTS['product_id']}"
        f"&license%5BdeviceType%5D={DEFAULTS['device_type']}"
        f"&license%5Bmail%5D="
        f"&license%5Bmark%5D="
        f"&license%5Bnumber%5D="
        f"&license%5Bstate%5D="
        f"&license%5Bsales%5D={DEFAULTS['sales']}"
        f"&license%5Bsecret%5D={DEFAULTS['secret']}"
        f"&license%5Bversion%5D={version_val}"
        f"&license%5BauthType%5D="
        f"&license%5Blanguage%5D=zh_CN"
        f"&license%5BlicenseType%5D={DEFAULTS['license_type']}"
        f"&license%5Bdisplay_model%5D={display_val}"
        f"&license%5Bnic%5D={DEFAULTS['nic']}"
        f"&license%5BstartDate%5D={start_date}"
        f"&license%5BendDate%5D={end_date}"
    )
    for feat in DEFAULTS["features"]:
        body += f"&license%5Bfeatures%5D%5B%5D={feat}"
    body += (
        f"&license%5BcoreNum%5D={DEFAULTS['core_num']}"
        f"&license%5BappendDate%5D={end_date}"
        f"&license%5BipsendDate%5D={end_date}"
        f"&license%5BavendDate%5D={end_date}"
        f"&license%5BurlendDate%5D={end_date}"
        f"&license%5BntiendDate%5D={end_date}"
        f"&license%5BwafruleendDate%5D={end_date}"
    )

    text = curl([
        "-X", "POST", f"{BASE_URL}/NfLicense/insertNf",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-d", body,
    ])

    if "Exception" in text:
        raise CertError("阶段B失败: 服务器返回 Exception")

    m_id = re.search(r'编号:(\d+)', text)
    if not m_id:
        m_dl = re.search(r'/licenseViewer/downloads/id/(\d+)', text)
        cert_id = m_dl.group(1) if m_dl else None
        if not cert_id:
            raise CertError("阶段B失败: 无法提取证书编号")
    else:
        cert_id = m_id.group(1)

    m_file = re.search(r'证书文件:\s*([^<\s]+)', text)
    cert_file = m_file.group(1).strip() if m_file else f"certificate-{cert_id}.lic"

    print(f"OK (编号: {cert_id})")
    return cert_id, cert_file


def download(cert_id, cert_file):
    print("[4/4] 下载证书 ...", end=" ")
    os.makedirs(CERT_DIR, exist_ok=True)
    dest = os.path.normpath(os.path.join(CERT_DIR, cert_file))

    curl_to_file([f"{BASE_URL}/licenseViewer/downloads/id/{cert_id}"], dest)

    size = os.path.getsize(dest)
    if size == 0:
        raise CertError("下载失败: 文件大小为 0")
    print(f"OK ({size} bytes)")
    return dest


def cleanup():
    if os.path.exists(COOKIE_FILE):
        os.remove(COOKIE_FILE)


def main():
    parser = argparse.ArgumentParser(description="绿盟科技证书申请自动化")
    parser.add_argument("username", help="登录用户名")
    parser.add_argument("pwd", help="PIN码 (固定部分)")
    parser.add_argument("hash", help="设备 HASH / 序列号")
    parser.add_argument("uip", help="UIP 口令 (一次性密码)")
    parser.add_argument("--version", default="6.0.6", choices=sorted(VERSION_MAP.keys()), help="版本号 (默认: 6.0.6)")
    parser.add_argument("--dev", default="vnf", choices=sorted(DISPLAY_MAP.keys()), help="证书显示产品 (默认: vnf)")
    args = parser.parse_args()

    version_val = VERSION_MAP[args.version]
    display_val = DISPLAY_MAP[args.dev]

    password = args.pwd + args.uip
    today = datetime.date.today()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    print(f"日期: {start_date} ~ {end_date}")

    try:
        login(args.username, password)
        customer_short, customer_full = query_device(args.hash)
        if customer_short is None:
            raise CertError(f"设备 {args.hash} 不存在，请先通过 Web 添加设备")

        phase_a_apply(args.hash, customer_short, start_date, end_date, args.username)
        cert_id, cert_file = phase_b_insert(args.hash, customer_full, start_date, end_date, version_val, display_val, args.username)
        dest = download(cert_id, cert_file)

        print(f"\n{'='*50}")
        print(f"  完成! ")
        print(f"  证书编号: {cert_id}")
        print(f"  版本:     {args.version}")
        print(f"  显示产品: {args.dev.upper()}")
        print(f"  文件:     {dest}")
        print(f"{'='*50}")
        return 0

    except CertError as e:
        print(f"\n错误: {e}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("\n超时: 请求超时，请检查网络连接", file=sys.stderr)
        return 1
    finally:
        cleanup()


if __name__ == "__main__":
    sys.exit(main())