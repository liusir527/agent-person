"""HA 同步配置 — HA 同步状态查询、配置同步和会话同步管理。

对应 UI 页面「高可用 → 双机热备 → 同步配置」。
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


class HaSyncFeature(NFRequests):
    """HA 同步配置操作集合 — 同步状态、手动同步、自动同步和会话同步。"""

    def get_ha_sync_config_status(self):
        """获取 HA 同步配置状态。

        对应 API 文档中的 ``get_ha_sync_status``。

        :return: 成功返回完整响应 dict，含 ``result.sync_status`` 和 ``result.last_sync_time``；失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/ha/ha_sync_status/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取HA同步配置状态失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def manual_sync_ha_config(self):
        """手动同步 HA 配置。

        对应 API 文档中的 ``get_peer_sync_config``。

        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/ha/peer_sync_config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'手动同步HA配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def enable_or_disable_sync_config(self, config_sync=True, req_body=None):
        """启用或禁用 HA 配置同步。

        对应 API 文档中的 ``trigger_config_sync``。

        .. note:: 布尔型参数会自动转换为小写字符串 ``"true"``/``"false"``。

        :param config_sync: ``True`` = 启用配置同步，``False`` = 禁用，默认 ``True``
        :type config_sync: bool
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'config_sync': str(config_sync).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/config_sync/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'启用或禁用HA配置同步失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def enable_or_disable_auto_sync_config(self, auto_sync=True, req_body=None):
        """启用或禁用 HA 自动同步配置。

        对应 API 文档中的 ``trigger_auto_sync``。

        .. note:: 布尔型参数会自动转换为小写字符串 ``"true"``/``"false"``。

        :param auto_sync: ``True`` = 启用自动同步，``False`` = 禁用，默认 ``True``
        :type auto_sync: bool
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'auto_sync': str(auto_sync).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/auto_sync/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'启用或禁用HA自动同步配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def sync_ha_session(self, firewall_sync=True, sync_type='firewallsync',
        req_body=None):
        """启用或禁用 HA 会话同步。

        对应 API 文档中的 ``trigger_session_sync``。

        .. note:: 布尔型参数会自动转换为小写字符串 ``"true"``/``"false"``。

        :param firewall_sync: ``True`` = 启用会话同步，``False`` = 禁用，默认 ``True``
        :type firewall_sync: bool
        :param sync_type: 同步类型，默认 ``"firewallsync"``
        :type sync_type: str
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'firewall_sync': str(firewall_sync).lower(), 'type': str(
            sync_type).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/session_sync/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'启用或禁用HA会话同步失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
