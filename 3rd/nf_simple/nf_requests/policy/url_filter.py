"""URL 过滤 — URL 过滤全局配置（DNS 检测、Web 信誉检测、绕过阻止页面）。

对应 UI 页面「对象 → URL 过滤 → 全局配置」。
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


class UrlFilterFeature(NFRequests):
    """URL 过滤操作集合 — URL 过滤全局配置管理。"""

    def update_url_filter_global_config(self, check_dns=False, credibility=
        False, skip=False):
        """更新 URL 过滤全局配置（可信度 / DNS 检测 / 绕过阻止页面）。

        对应 UI 页面「对象 → URL 过滤 → 全局配置」。

        :param check_dns: 是否开启 DNS 检测
        :type check_dns: bool
        :param credibility: 是否开启 Web 信誉检测
        :type credibility: bool
        :param skip: 是否跳过阻止页面
        :type skip: bool
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'check_dns': check_dns, 'credibility': credibility, 'skip': skip}
        req_url = f'{self.base_url}/nf/object/url/credibility/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新URL过滤全局配置失败: {e}')
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

    def get_url_filter_global_config(self):
        """获取 URL 过滤全局配置。

        对应 UI 页面「对象 → URL 过滤 → 全局配置」。

        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/url/credibility/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取URL过滤全局配置失败: {e}')
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
