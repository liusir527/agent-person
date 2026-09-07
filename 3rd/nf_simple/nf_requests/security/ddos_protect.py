"""DDoS 攻击防护规则。

对应 UI 页面「安全防护 → DDoS 防护 → 攻击防护」。
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


class DdosProtectFeature(NFRequests):
    """DDoS 攻击防护规则操作集合。"""

    def create_ddos_protect(self, action='create', type_id=1, auto_protect=1,
        limit_traffic=1000, period=10, protect_time=3600, switch=1, threshold=60000
        ):
        """创建 DDoS 防护策略。

        对应 UI 页面「安全防护 → DDoS 防护 → 攻击防护」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 修改，默认 ``"create"``。
        :param type_id: 防护类型 ID（int）：

            * ``0`` — ARP 欺骗
            * ``1`` — ARP 请求 Flood
            * ``2`` — IP Flood
            * ``4`` — Ping 请求 Flood
            * ``5`` — Ping 应答 Flood
            * ``6`` — UDP Flood
            * ``7`` — TCP SYN Flood
            * ``8`` — TCP ACK Flood
            * ``9`` — TCP SYN-ACK Flood
            * ``10`` — TCP FIN Flood
            * ``11`` — TCP RST Flood
            * ``13`` — DNS 请求 Flood
            * ``14`` — DNS 应答 Flood
            * ``15`` — HTTP GET Flood
            * ``16`` — HTTP POST Flood
            * ``17`` — HTTPS Flood
            * ``18`` — SIP Flood

            默认 1。
        :param auto_protect: 保护功能是否开启，``1`` = 开，``0`` = 关，默认 1。
        :param limit_traffic: 限制流量（PPS），默认 1000。
        :param period: 检测周期（秒），默认 10。
        :param protect_time: 保护时间（秒），默认 3600。
        :param switch: 防护开关，``1`` = 开，``0`` = 关，默认 1。
        :param threshold: 检测阈值（包数），默认 60000。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'action': action, 'type_id': int(type_id), 'auto_protect': int(
            auto_protect), 'limit_traffic': int(limit_traffic), 'period': int(
            period), 'protect_time': int(protect_time), 'switch': int(switch),
            'threshold': int(threshold)}
        url = f'{self.base_url}/nf/strategy/ddos/attack/attack_configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建DDoS防护策略失败: {e}')
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

    def update_ddos_protect(self, type_id, auto_protect=1, limit_traffic=1000,
        period=10, protect_time=3600, switch=1, threshold=60000):
        """修改 DDoS 防护策略。

        对应 UI 页面「安全防护 → DDoS 防护 → 攻击防护」。

        :param type_id: 防护类型 ID（int），参见
            [`create_ddos_protect()`](ddos_protect.py) 的 ``type_id`` 枚举说明。
        :param auto_protect: 保护功能是否开启，``1`` = 开，``0`` = 关，默认 1。
        :param limit_traffic: 限制流量（PPS），默认 1000。
        :param period: 检测周期（秒），默认 10。
        :param protect_time: 保护时间（秒），默认 3600。
        :param switch: 防护开关，``1`` = 开，``0`` = 关，默认 1。
        :param threshold: 检测阈值（包数），默认 60000。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'action': 'edit', 'type_id': int(type_id), 'auto_protect': int(
            auto_protect), 'limit_traffic': int(limit_traffic), 'period': int(
            period), 'protect_time': int(protect_time), 'switch': int(switch),
            'threshold': int(threshold)}
        url = f'{self.base_url}/nf/strategy/ddos/attack/attack_configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新DDoS防护策略失败: {e}')
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

    def delete_ddos_protect(self, type_id):
        """根据类型 ID 删除 DDoS 防护策略。

        对应 UI 页面「安全防护 → DDoS 防护 → 攻击防护」。

        :param type_id: 防护类型 ID（int），参见
            [`create_ddos_protect()`](ddos_protect.py) 的 ``type_id`` 枚举说明。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'action': 'delete', 'type_id': int(type_id)}
        url = f'{self.base_url}/nf/strategy/ddos/attack/attack_configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除DDoS防护策略失败: {e}')
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

    def get_ddos_protect_rules(self, keyword=None):
        """获取 DDoS 攻击防护规则列表。

        对应 UI 页面「安全防护 → DDoS 防护 → 攻击防护」。

        :param keyword: 搜索关键字，``None`` 查询全部，传入字符串则按名称/类型搜索。
        :return: 成功返回完整响应 dict，格式为 ``{"status": 2000, "result": {...}, "message": "..."}``；
            失败返回 ``False``。
        """
        keyword = str(keyword) if keyword is not None else ''
        url = f'{self.base_url}/nf/strategy/ddos/attack/attack_info/'
        params = {'search': keyword}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'查询DDoS防护规则失败: {e}')
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
