"""SSL VPN 认证访问 — SSL VPN 认证访问策略的增删查改。

对应 UI 页面「VPN → SSL VPN → 认证访问策略」。

对应 API 文档中的 ``get_sslvpn_auth_access``、
``create_or_update_sslvpn_auth_access``、``remove_sslvpn_auth_access``。
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


class SslVpnAuthAccessFeature(NFRequests):
    """SSL VPN 认证访问操作集合 — SSL VPN 认证访问策略的增删查改。"""

    def create_or_update_auth_access(self, action='create', auth_access_id='',
        name='name1', user_group=None, resource_group=None, status=True, note=
        '', req_body=None):
        """创建或更新 SSL VPN 认证访问策略。

        对应 API 文档中的 ``create_or_update_sslvpn_auth_access``。

        :param action: 操作类型，``"create"`` 创建，``"edit"`` 编辑
        :type action: str
        :param auth_access_id: 编辑时传入的策略 ID
        :type auth_access_id: str
        :param name: 策略名称
        :type name: str
        :param user_group: 用户组 ID，支持单个或列表
        :type user_group: int or str or list[int] or None
        :param resource_group: 资源组 ID，支持单个或列表
        :type resource_group: int or str or list[int] or None
        :param status: 是否启用
        :type status: bool
        :param note: 备注
        :type note: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(user_group, list):
            user_group = [int(ug) for ug in user_group]
        elif isinstance(user_group, (int, str)):
            user_group = [int(user_group)]
        elif user_group is None:
            user_group = [1]
        if isinstance(resource_group, list):
            resource_group = [int(rg) for rg in resource_group]
        elif isinstance(resource_group, (int, str)):
            resource_group = [int(resource_group)]
        elif resource_group is None:
            resource_group = [1]
        data = {'action': action, 'id': auth_access_id, 'name': name,
            'userGroup': user_group, 'resourceGroup': resource_group, 'status':
            status, 'note': note}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/auth_access/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新SSL VPN授权访问失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_auth_access(self, page=1, size=10, search=''):
        """获取 SSL VPN 认证访问策略列表。

        对应 API 文档中的 ``get_sslvpn_auth_access``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/vpn/sslvpn/auth_access/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取SSL VPN授权访问列表失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def remove_auth_access(self, auth_access_id, req_body=None):
        """删除 SSL VPN 认证访问策略。

        对应 API 文档中的 ``remove_sslvpn_auth_access``。

        :param auth_access_id: 策略 ID，支持单个 ID 或 ID 列表
        :type auth_access_id: int or list[int]
        :param req_body: 自定义请求体，传入后忽略 auth_access_id
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(auth_access_id, list):
            auth_access_id = [int(aid) for aid in auth_access_id]
        else:
            auth_access_id = [int(auth_access_id)]
        data = {'id': auth_access_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/auth_access/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除SSL VPN授权访问失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
