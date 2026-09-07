"""DHCP Snooping — DHCP Snooping 全局配置及接口动作管理。

对应 UI 页面「网络管理 → DHCP Snooping」。
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


class SnoopingFeature(NFRequests):
    """DHCP Snooping 配置操作集合 — 全局配置及接口动作管理。"""

    def get_snooping_global_config(self):
        """获取 DHCP Snooping 全局配置。

        对应 API 文档中的 ``get_snooping_global``。

        :return: 成功返回 ``{"status": 2000, "result": {"enable": bool, "vlan_list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/network/snooping/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取DHCP Snooping全局配置失败: {e}')
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

    def update_snooping_global_config(self, is_default_off=False, is_record_log
        ='false', req_body=None):
        """更新 DHCP Snooping 全局配置。

        对应 API 文档中的 ``update_snooping_global``。

        :param is_default_off: 是否默认关闭，默认 ``False``
        :type is_default_off: bool
        :param is_record_log: 是否记录日志，默认 ``'false'``
        :type is_record_log: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'isDefaultOff': is_default_off, 'isRecordLog': is_record_log
            } if req_body is None else req_body
        req_url = f'{self.base_url}/nf/network/snooping/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新DHCP Snooping全局配置失败: {e}')
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
