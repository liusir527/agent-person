"""邮件安全日志 — 邮件安全事件的日志查询。

对应 UI 页面「日志与报表 → 邮件安全日志」。
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


class EmailSecurityLogFeature(NFRequests):
    """邮件安全日志操作集合 — 邮件安全事件的日志查询。"""

    def get_email_sec_log_info(self, page=1, size=10, s_time=None, d_time=None,
        sender='', receiver='', attach='', action='', req_body=None):
        """查询邮件安全日志。

        对应 API 文档中的 ``search_email_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 开始时间（时间戳，必填）
        :type s_time: int
        :param d_time: 结束时间（时间戳，必填）
        :type d_time: int
        :param sender: 发件人过滤
        :type sender: str
        :param receiver: 收件人过滤
        :type receiver: str
        :param attach: 附件过滤
        :type attach: str
        :param action: 动作过滤
        :type action: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'page': int(page), 'size': int(size), 's_time': s_time,
            'd_time': d_time, 'sender': sender, 'receiver': receiver,
            'attach': attach, 'action': action}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/scm/email/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取邮件安全日志信息失败: {e}')
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
