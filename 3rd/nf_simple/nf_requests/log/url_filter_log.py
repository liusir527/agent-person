"""URL 过滤日志 — URL 过滤事件的日志查询。

对应 UI 页面「日志与报表 → URL 过滤日志」。
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


class UrlFilterLogFeature(NFRequests):
    """URL 过滤日志操作集合 — URL 过滤事件的日志查询。"""

    def get_url_filter_log_info(self, page=1, size=10, s_time=None, d_time=None,
        digest='', info0='', card='', src_ip='', dst_ip='', src_port='',
        dst_port='', src_mac='', dst_mac='', user='', action='', digest_op='1',
        info0_op='1', src_ip_op='1', dst_ip_op='1', src_port_op='1',
        dst_port_op='1', src_mac_op='1', dst_mac_op='1', req_body=None):
        """查询 URL 过滤日志。

        对应 API 文档中的 ``search_url_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 开始时间（时间戳，必填）
        :type s_time: int
        :param d_time: 结束时间（时间戳，必填）
        :type d_time: int
        :param digest: URL 摘要过滤
        :type digest: str
        :param info0: URL 过滤（对应 API ``url`` 字段）
        :type info0: str
        :param card: 网卡过滤
        :type card: str
        :param src_ip: 源 IP 过滤
        :type src_ip: str
        :param dst_ip: 目的 IP 过滤
        :type dst_ip: str
        :param src_port: 源端口过滤
        :type src_port: str
        :param dst_port: 目的端口过滤
        :type dst_port: str
        :param src_mac: 源 MAC 过滤
        :type src_mac: str
        :param dst_mac: 目的 MAC 过滤
        :type dst_mac: str
        :param user: 用户过滤
        :type user: str
        :param action: 动作过滤
        :type action: str
        :param digest_op: URL 摘要匹配运算符，默认 ``'1'``（等于）
        :type digest_op: str
        :param info0_op: URL 匹配运算符，默认 ``'1'``
        :type info0_op: str
        :param src_ip_op: 源 IP 匹配运算符，默认 ``'1'``
        :type src_ip_op: str
        :param dst_ip_op: 目的 IP 匹配运算符，默认 ``'1'``
        :type dst_ip_op: str
        :param src_port_op: 源端口匹配运算符，默认 ``'1'``
        :type src_port_op: str
        :param dst_port_op: 目的端口匹配运算符，默认 ``'1'``
        :type dst_port_op: str
        :param src_mac_op: 源 MAC 匹配运算符，默认 ``'1'``
        :type src_mac_op: str
        :param dst_mac_op: 目的 MAC 匹配运算符，默认 ``'1'``
        :type dst_mac_op: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'s_time': s_time, 'd_time': d_time, 'digest': digest, 'info0':
            info0, 'card': card, 'src_ip': src_ip, 'dst_ip': dst_ip, 'src_port':
            src_port, 'dst_port': dst_port, 'src_mac': src_mac, 'dst_mac':
            dst_mac, 'user': user, 'action': action, 'page': page, 'size': size,
            'digestOp': digest_op, 'info0Op': info0_op, 'src_ipOp': src_ip_op,
            'dst_ipOp': dst_ip_op, 'src_portOp': src_port_op, 'dst_portOp':
            dst_port_op, 'src_macOp': src_mac_op, 'dst_macOp': dst_mac_op}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/url/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取URL过滤日志信息失败: {e}')
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
