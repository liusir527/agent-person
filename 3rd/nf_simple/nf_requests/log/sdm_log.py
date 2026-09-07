"""敏感数据安全日志 — 敏感数据管理事件的日志查询。

对应 UI 页面「日志与报表 → 敏感数据安全日志」。
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


class SdmLogFeature(NFRequests):
    """数据安全日志操作集合 — 敏感数据管理事件的日志查询。"""

    def get_sdm_log_info(self, page=1, size=10, s_time=None, d_time=None,
        src_card='', src_zone='', src_ip='', src_mac='', src_port='', dst_card=
        '', dst_zone='', dst_ip='', dst_mac='', dst_port='', user='', level='',
        action='', event_type='', app_name='', data_type='', app_name_op='1',
        src_ip_op='1', src_mac_op='1', src_zone_op='1', src_port_op='1',
        dst_ip_op='1', dst_mac_op='1', dst_zone_op='1', dst_port_op='1',
        src_card_op='1', dst_card_op='1', req_body=None):
        """查询敏感数据管理日志。

        对应 API 文档中的 ``search_sdm_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 开始时间（时间戳，必填）
        :type s_time: int
        :param d_time: 结束时间（时间戳，必填）
        :type d_time: int
        :param src_card: 源网卡过滤
        :type src_card: str
        :param src_zone: 源安全区过滤
        :type src_zone: str
        :param src_ip: 源 IP 过滤
        :type src_ip: str
        :param src_mac: 源 MAC 过滤
        :type src_mac: str
        :param src_port: 源端口过滤
        :type src_port: str
        :param dst_card: 目的网卡过滤
        :type dst_card: str
        :param dst_zone: 目的安全区过滤
        :type dst_zone: str
        :param dst_ip: 目的 IP 过滤
        :type dst_ip: str
        :param dst_mac: 目的 MAC 过滤
        :type dst_mac: str
        :param dst_port: 目的端口过滤
        :type dst_port: str
        :param user: 用户过滤
        :type user: str
        :param level: 级别过滤
        :type level: str
        :param action: 动作过滤
        :type action: str
        :param event_type: 事件类型过滤
        :type event_type: str
        :param app_name: 应用名称过滤
        :type app_name: str
        :param data_type: 数据类型过滤
        :type data_type: str
        :param app_name_op: 应用名称匹配运算符，默认 ``'1'``（等于）
        :type app_name_op: str
        :param src_ip_op: 源 IP 匹配运算符，默认 ``'1'``
        :type src_ip_op: str
        :param src_mac_op: 源 MAC 匹配运算符，默认 ``'1'``
        :type src_mac_op: str
        :param src_zone_op: 源安全区匹配运算符，默认 ``'1'``
        :type src_zone_op: str
        :param src_port_op: 源端口匹配运算符，默认 ``'1'``
        :type src_port_op: str
        :param dst_ip_op: 目的 IP 匹配运算符，默认 ``'1'``
        :type dst_ip_op: str
        :param dst_mac_op: 目的 MAC 匹配运算符，默认 ``'1'``
        :type dst_mac_op: str
        :param dst_zone_op: 目的安全区匹配运算符，默认 ``'1'``
        :type dst_zone_op: str
        :param dst_port_op: 目的端口匹配运算符，默认 ``'1'``
        :type dst_port_op: str
        :param src_card_op: 源网卡匹配运算符，默认 ``'1'``
        :type src_card_op: str
        :param dst_card_op: 目的网卡匹配运算符，默认 ``'1'``
        :type dst_card_op: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'page': int(page), 'size': int(size), 's_time': s_time,
            'd_time': d_time, 'src_card': src_card, 'src_zone': src_zone,
            'src_ip': src_ip, 'src_mac': src_mac, 'src_port': src_port,
            'dst_card': dst_card, 'dst_zone': dst_zone, 'dst_ip': dst_ip,
            'dst_mac': dst_mac, 'dst_port': dst_port, 'user': user, 'level':
            level, 'action': action, 'data_type': data_type, 'event_type':
            event_type, 'app_name': app_name, 'app_nameOp': app_name_op,
            'src_ipOp': src_ip_op, 'src_macOp': src_mac_op, 'src_zoneOp':
            src_zone_op, 'src_portOp': src_port_op, 'dst_ipOp': dst_ip_op,
            'dst_macOp': dst_mac_op, 'dst_zoneOp': dst_zone_op, 'dst_portOp':
            dst_port_op, 'src_cardOp': src_card_op, 'dst_cardOp': dst_card_op}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/scm/sensitive/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取敏感数据日志信息失败: {e}')
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
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
