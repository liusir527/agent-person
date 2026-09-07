"""特殊包防护 — DDoS 特殊报文防护策略的查询和更新。

对应 UI 页面「安全防护 → DDoS 防护 → 特殊包防护」。

对应 API 文档中的 ``get_ddos_special_info``、``update_ddos_special``。
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


class SpecialPacketFeature(NFRequests):
    """特殊包防护操作集合 — 特殊报文防护策略的查询和更新。"""

    def update_special_packet_config(self, big_icmp_id=33, big_icmp_d_switch=0,
        big_icmp_auto_protect=0, big_icmp_threshold=65535, icmp_unreachable_id=
        34, icmp_unreachable_d_switch=0, icmp_unreachable_auto_protect=0,
        icmp_redirect_id=35, icmp_redirect_d_switch=0,
        icmp_redirect_auto_protect=0, tracert_id=36, tracert_d_switch=0,
        tracert_auto_protect=0, src_route_id=37, src_route_d_switch=0,
        src_route_auto_protect=0, route_record_id=38, route_record_d_switch=0,
        route_record_auto_protect=0, timestamp_id=39, timestamp_d_switch=0,
        timestamp_auto_protect=0):
        """更新特殊报文防护策略（共 7 种报文类型）。

        对应 API 文档中的 ``update_ddos_special``。

        :param big_icmp_id: 超大 ICMP 报文类型 ID，默认 ``33``
        :type big_icmp_id: int
        :param big_icmp_d_switch: 超大 ICMP 开关，``1`` 启用 / ``0`` 禁用
        :type big_icmp_d_switch: int
        :param big_icmp_auto_protect: 超大 ICMP 自动保护，``1`` 开启 / ``0`` 关闭
        :type big_icmp_auto_protect: int
        :param big_icmp_threshold: 超大 ICMP 阈值，默认 ``65535``
        :type big_icmp_threshold: int
        :param icmp_unreachable_id: ICMP 不可达报文类型 ID，默认 ``34``
        :type icmp_unreachable_id: int
        :param icmp_unreachable_d_switch: ICMP 不可达开关，``1`` 启用 / ``0`` 禁用
        :type icmp_unreachable_d_switch: int
        :param icmp_unreachable_auto_protect: ICMP 不可达自动保护，``1`` 开启 / ``0`` 关闭
        :type icmp_unreachable_auto_protect: int
        :param icmp_redirect_id: ICMP 重定向报文类型 ID，默认 ``35``
        :type icmp_redirect_id: int
        :param icmp_redirect_d_switch: ICMP 重定向开关，``1`` 启用 / ``0`` 禁用
        :type icmp_redirect_d_switch: int
        :param icmp_redirect_auto_protect: ICMP 重定向自动保护，``1`` 开启 / ``0`` 关闭
        :type icmp_redirect_auto_protect: int
        :param tracert_id: Tracert 类型 ID，默认 ``36``
        :type tracert_id: int
        :param tracert_d_switch: Tracert 开关，``1`` 启用 / ``0`` 禁用
        :type tracert_d_switch: int
        :param tracert_auto_protect: Tracert 自动保护，``1`` 开启 / ``0`` 关闭
        :type tracert_auto_protect: int
        :param src_route_id: 源站路由选项 IP 报文类型 ID，默认 ``37``
        :type src_route_id: int
        :param src_route_d_switch: 源站路由开关，``1`` 启用 / ``0`` 禁用
        :type src_route_d_switch: int
        :param src_route_auto_protect: 源站路由自动保护，``1`` 开启 / ``0`` 关闭
        :type src_route_auto_protect: int
        :param route_record_id: 路由记录选项 IP 报文类型 ID，默认 ``38``
        :type route_record_id: int
        :param route_record_d_switch: 路由记录开关，``1`` 启用 / ``0`` 禁用
        :type route_record_d_switch: int
        :param route_record_auto_protect: 路由记录自动保护，``1`` 开启 / ``0`` 关闭
        :type route_record_auto_protect: int
        :param timestamp_id: 时间戳选项 IP 报文类型 ID，默认 ``39``
        :type timestamp_id: int
        :param timestamp_d_switch: 时间戳开关，``1`` 启用 / ``0`` 禁用
        :type timestamp_d_switch: int
        :param timestamp_auto_protect: 时间戳自动保护，``1`` 开启 / ``0`` 关闭
        :type timestamp_auto_protect: int
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        count = 7
        special_config = [{'typeId': int(big_icmp_id), 'dSwitch': int(
            big_icmp_d_switch), 'autoProtect': int(big_icmp_auto_protect),
            'threshold': int(big_icmp_threshold)}, {'typeId': int(
            icmp_unreachable_id), 'dSwitch': int(icmp_unreachable_d_switch),
            'autoProtect': int(icmp_unreachable_auto_protect)}, {'typeId': int(
            icmp_redirect_id), 'dSwitch': int(icmp_redirect_d_switch),
            'autoProtect': int(icmp_redirect_auto_protect)}, {'typeId': int(
            tracert_id), 'dSwitch': int(tracert_d_switch), 'autoProtect': int(
            tracert_auto_protect)}, {'typeId': int(src_route_id), 'dSwitch':
            int(src_route_d_switch), 'autoProtect': int(src_route_auto_protect)
            }, {'typeId': int(route_record_id), 'dSwitch': int(
            route_record_d_switch), 'autoProtect': int(
            route_record_auto_protect)}, {'typeId': int(timestamp_id),
            'dSwitch': int(timestamp_d_switch), 'autoProtect': int(
            timestamp_auto_protect)}]
        data = {'count': count, 'specialConfig': special_config}
        url = f'{self.base_url}/nf/strategy/ddos/special/special_configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'修改特殊报文防护策略失败: {e}')
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

    def get_special_packet_config(self):
        """获取特殊报文防护策略信息。

        对应 API 文档中的 ``get_ddos_special_info``。

        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/strategy/ddos/special/special_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取特殊报文防护策略信息失败: {e}')
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
