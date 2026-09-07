"""全局联动 — 全局应用联动配置的删除。

对应 UI 页面「系统 → 全局联动」。

对应 API 文档中的 ``remove_global_association``。
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


class GlobalAssociationFeature(NFRequests):
    """全局联动操作集合 — 全局应用联动配置的删除。"""

    def remove_ga_data(self, action='delete_acl', rule_id='policy1', req_body=None
        ):
        """删除全局联动配置（GA 数据）。

        对应 API 文档中的 ``remove_global_association``。

        :param action: 操作类型，默认 ``"delete_acl"``
        :type action: str
        :param rule_id: 联动配置 ID
        :type rule_id: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'action': action, 'rule_id': rule_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/gadata/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除GA数据失败: {e}')
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
