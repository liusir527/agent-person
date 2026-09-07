"""北向接口 Token — 北向接口用户 Token 生成。

对应 UI 页面「系统 → 北向接口」。

对应 API 文档中的 ``generate_token``。
"""

import sys
import requests
import json
import os
import base64
import logging

from ..nflib.Log import logger
from ..nflib.comm import *
from ..client import NFRequests


class TokenFeature(NFRequests):
    """北向接口 Token 操作集合 — 北向接口用户 Token 生成。"""

    def generate_token(self, name='test1', interval='120', req_body=None):
        """生成北向接口用户 Token。

        对应 API 文档中的 ``generate_token``。

        :param name: 用户名
        :type name: str
        :param interval: 令牌有效期（秒），默认 ``"120"``
        :type interval: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict（含 ``token`` 和 ``expire_time``），失败返回 False
        :rtype: dict or bool
        """
        data = {'name': name, 'interval': interval}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/restapi/user/generate_token/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'生成北向接口用户token失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}
