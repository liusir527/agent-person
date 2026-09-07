"""IPS 日志 — IPS 入侵防御事件的日志查询。

对应 UI 页面「日志与报表 → IPS 日志」。
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


class IpsLogFeature(NFRequests):
    """IPS 日志操作集合 — IPS 入侵防御事件的日志查询。"""

    def get_ips_log_info(self, page=1, size=10, s_time=None, d_time=None,
        rule_name='', src_ip='', dst_ip='', action='', req_body=None):
        """查询 IPS 日志。

        对应 API 文档中的 ``search_ips_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 开始时间（时间戳，必填）
        :type s_time: int
        :param d_time: 结束时间（时间戳，必填）
        :type d_time: int
        :param rule_name: 规则名称过滤
        :type rule_name: str
        :param src_ip: 源 IP 过滤
        :type src_ip: str
        :param dst_ip: 目的 IP 过滤
        :type dst_ip: str
        :param action: 动作过滤
        :type action: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'page': int(page), 'size': int(size), 's_time': s_time,
            'd_time': d_time, 'rule_name': rule_name, 'src_ip': src_ip,
            'dst_ip': dst_ip, 'action': action}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/ips/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取IPS日志失败: {e}')
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
