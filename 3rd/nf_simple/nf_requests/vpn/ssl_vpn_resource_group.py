"""SSL VPN 资源组 — SSL VPN 资源组的增删查改。

对应 UI 页面「VPN → SSL VPN → 资源组管理」。

对应 API 文档中的 ``get_sslvpn_resource_group``、
``create_or_update_sslvpn_resource_group``、``remove_sslvpn_resource_group``。
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


class SslVpnResourceGroupFeature(NFRequests):
    """SSL VPN 资源组操作集合 — SSL VPN 资源组的增删查改。"""

    def create_or_update_resource_grp(self, action='create', grp_id='', name=
        'rsc_grp_name', note='', req_body=None):
        """创建或更新 SSL VPN 资源组。

        对应 API 文档中的 ``create_or_update_sslvpn_resource_group``。

        :param action: 操作类型，``"create"`` 创建，``"edit"`` 编辑
        :type action: str
        :param grp_id: 编辑时传入的资源组 ID
        :type grp_id: str
        :param name: 资源组名称
        :type name: str
        :param note: 备注
        :type note: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'action': action, 'id': grp_id, 'name': name, 'note': note}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/resource_group/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新SSL VPN资源组失败: {e}')
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

    def get_resource_grp(self, page=1, size=10, search=''):
        """获取 SSL VPN 资源组列表。

        对应 API 文档中的 ``get_sslvpn_resource_group``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/vpn/sslvpn/resource_group/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取SSL VPN资源组列表失败: {e}')
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

    def remove_resource_grp(self, grp_id, req_body=None):
        """删除 SSL VPN 资源组。

        对应 API 文档中的 ``remove_sslvpn_resource_group``。

        :param grp_id: 资源组 ID，支持单个 ID 或 ID 列表
        :type grp_id: int or list[int]
        :param req_body: 自定义请求体，传入后忽略 grp_id
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(grp_id, list):
            grp_ids = [int(gid) for gid in grp_id]
        else:
            grp_ids = [int(grp_id)]
        data = {'id': grp_ids}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/resource_group/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除SSL VPN资源组失败: {e}')
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
