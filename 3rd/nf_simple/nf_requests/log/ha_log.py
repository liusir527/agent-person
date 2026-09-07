"""HA 日志 — HA 高可用运行日志查询。

对应 UI 页面「日志与报表 → HA 日志」。
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


class HaLogFeature(NFRequests):
    """HA 日志操作集合 — HA 高可用运行日志查询。"""

    def get_ha_log(self, page=1, size=10, s_time=None, d_time=None, level='',
        content='', content_op='3', req_body=None):
        """查询 HA 日志。

        对应 API 文档中的 ``search_ha_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 开始时间（时间戳，必填）
        :type s_time: int
        :param d_time: 结束时间（时间戳，必填）
        :type d_time: int
        :param level: 日志级别过滤
        :type level: str
        :param content: 内容过滤
        :type content: str
        :param content_op: 内容匹配运算符，默认 ``'3'``（模糊匹配）
        :type content_op: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {...}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'page': int(page), 'size': int(size), 's_time': s_time,
            'd_time': d_time, 'level': level, 'content': content,
            'contentOp': content_op}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/run/ha/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取HA日志失败: {e}')
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
