"""扫描防护 — DDoS 扫描窥探防护和多端口扫描防护的查询和更新。

对应 UI 页面「安全防护 → DDoS 防护 → 扫描防护」。

对应 API 文档中的 ``get_ddos_scan_info``、``update_ddos_scan``、
``get_ddos_mport_info``、``update_ddos_mport``。
"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class ScanFeature(NFRequests):
    """扫描防护操作集合 — 扫描窥探防护和多端口扫描防护的查询和更新。"""

    def update_scan_config(self, tcp_type_id=21, tcp_d_switch=0, tcp_threshold=
        60000, tcp_period=10, tcp_auto_protect=0, tcp_protect_time=3600,
        udp_type_id=22, udp_d_switch=0, udp_threshold=60000, udp_period=10,
        udp_auto_protect=0, udp_protect_time=3600, ping_type_id=20,
        ping_d_switch=0, ping_threshold=60000, ping_period=10,
        ping_auto_protect=0, ping_protect_time=3600):
        """更新扫描窥探防护策略（TCP/UDP/ICMP 三类）。

        对应 API 文档中的 ``update_ddos_scan``。

        :param tcp_type_id: TCP 扫描类型 ID，默认 ``21``
        :type tcp_type_id: int
        :param tcp_d_switch: TCP 扫描开关，``1`` 启用 / ``0`` 禁用
        :type tcp_d_switch: int
        :param tcp_threshold: TCP 检测阈值（包数），默认 ``60000``
        :type tcp_threshold: int
        :param tcp_period: TCP 检测周期（秒），默认 ``10``
        :type tcp_period: int
        :param tcp_auto_protect: TCP 自动保护，``1`` 开启 / ``0`` 关闭
        :type tcp_auto_protect: int
        :param tcp_protect_time: TCP 保护时间（秒），默认 ``3600``
        :type tcp_protect_time: int
        :param udp_type_id: UDP 扫描类型 ID，默认 ``22``
        :type udp_type_id: int
        :param udp_d_switch: UDP 扫描开关，``1`` 启用 / ``0`` 禁用
        :type udp_d_switch: int
        :param udp_threshold: UDP 检测阈值（包数），默认 ``60000``
        :type udp_threshold: int
        :param udp_period: UDP 检测周期（秒），默认 ``10``
        :type udp_period: int
        :param udp_auto_protect: UDP 自动保护，``1`` 开启 / ``0`` 关闭
        :type udp_auto_protect: int
        :param udp_protect_time: UDP 保护时间（秒），默认 ``3600``
        :type udp_protect_time: int
        :param ping_type_id: ICMP 扫描类型 ID，默认 ``20``
        :type ping_type_id: int
        :param ping_d_switch: ICMP 扫描开关，``1`` 启用 / ``0`` 禁用
        :type ping_d_switch: int
        :param ping_threshold: ICMP 检测阈值（包数），默认 ``60000``
        :type ping_threshold: int
        :param ping_period: ICMP 检测周期（秒），默认 ``10``
        :type ping_period: int
        :param ping_auto_protect: ICMP 自动保护，``1`` 开启 / ``0`` 关闭
        :type ping_auto_protect: int
        :param ping_protect_time: ICMP 保护时间（秒），默认 ``3600``
        :type ping_protect_time: int
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        count = 3
        scan_config = [{'typeId': int(tcp_type_id), 'dSwitch': int(tcp_d_switch
            ), 'threshold': int(tcp_threshold), 'period': int(tcp_period),
            'autoProtect': int(tcp_auto_protect), 'protectTime': int(
            tcp_protect_time)}, {'typeId': int(udp_type_id), 'dSwitch': int(
            udp_d_switch), 'threshold': int(udp_threshold), 'period': int(
            udp_period), 'autoProtect': int(udp_auto_protect), 'protectTime':
            int(udp_protect_time)}, {'typeId': int(ping_type_id), 'dSwitch':
            int(ping_d_switch), 'threshold': int(ping_threshold), 'period': int
            (ping_period), 'autoProtect': int(ping_auto_protect), 'protectTime':
            int(ping_protect_time)}]
        data = {'count': count, 'scanConfig': scan_config}
        url = f'{self.base_url}/nf/strategy/ddos/scan/scan_configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新扫描窥探防护策略失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return True
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_scan_config(self):
        """获取扫描窥探防护策略信息。

        对应 API 文档中的 ``get_ddos_scan_info``。

        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/strategy/ddos/scan/scan_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取扫描窥探防护策略失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return json.loads(result.text)
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def update_mport_scan_config(self, check=False, limit_count=10, limit_time=10):
        """更新管理口多端口扫描防护配置。

        对应 API 文档中的 ``update_ddos_mport``。

        :param check: 是否启用检测，``True`` 开启 / ``False`` 关闭
        :type check: bool
        :param limit_count: 检测阈值（端口数），默认 ``10``
        :type limit_count: int
        :param limit_time: 检测周期（秒），默认 ``10``
        :type limit_time: int
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        check = True if check is not None else False
        data = {'check': check, 'limit_count': int(limit_count), 'limit_time':
            int(limit_time)}
        url = f'{self.base_url}/nf/strategy/ddos/mport_scan/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新管理口扫描配置失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return True
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_mport_scan_config(self):
        """获取管理口多端口扫描防护配置信息。

        对应 API 文档中的 ``get_ddos_mport_info``。

        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/strategy/ddos/mport_scan/info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取管理口扫描配置失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return json.loads(result.text)
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
