"""SSL VPN 资源 — SSL VPN 资源的增删查改。

对应 UI 页面「VPN → SSL VPN → 资源管理」。

对应 API 文档中的 ``get_sslvpn_resource``、``create_or_update_sslvpn_resource``、
``remove_sslvpn_resource``。
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


class SslVpnResourceFeature(NFRequests):
    """SSL VPN 资源操作集合 — SSL VPN 资源的增删查改。"""

    def create_or_update_resource(self, action='create', resource_id='', name=
        'test_resource', resource_type='L3VPN', status=True, group=None, note=
        '', address_type='ip', start_address='172.30.1.1', end_address=None,
        check=True, proto='HTTP', url='www.example.com', links=1, public_addr=
        '172.30.1.1:30000', is_nat=False, access_addr=None, addr1=None, addr2=
        None, req_body=None):
        """创建或更新 SSL VPN 资源。

        对应 API 文档中的 ``create_or_update_sslvpn_resource``。

        :param action: 操作类型，``"create"`` 创建，``"edit"`` 编辑
        :type action: str
        :param resource_id: 编辑时传入的资源 ID
        :type resource_id: str
        :param name: 资源名称
        :type name: str
        :param resource_type: 资源类型，``"L3VPN"`` / ``"L4VPN"`` / ``"WEB"``
        :type resource_type: str
        :param status: 是否启用
        :type status: bool
        :param group: 资源组 ID，支持单个或列表
        :type group: int or str or list[int] or None
        :param note: 备注
        :type note: str
        :param address_type: 地址类型，``"ip"`` 或 ``"ippool"``
        :type address_type: str
        :param start_address: 起始地址
        :type start_address: str
        :param end_address: 结束地址（ippool 模式下默认 ``"172.30.1.100"``）
        :type end_address: str or None
        :param check: 是否启用健康检查
        :type check: bool
        :param proto: 协议类型，如 ``"HTTP"``
        :type proto: str
        :param url: URL 地址
        :type url: str
        :param links: 关联链路 ID
        :type links: int
        :param public_addr: 公网地址
        :type public_addr: str
        :param is_nat: 是否 NAT 模式
        :type is_nat: bool
        :param access_addr: NAT 模式下的访问地址，默认 ``"172.30.2.1:12345"``
        :type access_addr: str or None
        :param addr1: 响应内容地址列表 1
        :type addr1: str or list[str] or None
        :param addr2: 响应内容地址列表 2
        :type addr2: str or list[str] or None
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(group, (int, str)):
            group = [int(group)]
        elif isinstance(group, list):
            group = [int(g) for g in group]
        else:
            group = [1]
        status = str(status).lower()
        if address_type == 'ippool':
            end_address = '172.30.1.100' if end_address is None else end_address
        else:
            end_address = '' if end_address is None else end_address
        check = str(check).lower()
        is_nat = str(is_nat).lower()
        if is_nat == 'true':
            access_addr = ('172.30.2.1:12345' if access_addr is None else
                access_addr)
        else:
            access_addr = '' if access_addr is None else access_addr
        if isinstance(addr1, str):
            addr1 = [addr1]
        elif addr1 is None:
            addr1 = []
        if isinstance(addr2, str):
            addr2 = [addr2]
        elif addr2 is None:
            addr2 = []
        data = {'action': action, 'id': resource_id, 'name': name, 'type':
            resource_type, 'status': status, 'check': check, 'address_type':
            address_type, 'start_address': start_address, 'end_address':
            end_address, 'proto': proto, 'url': url, 'links': links,
            'publicAddr': public_addr, 'isNat': is_nat, 'accessAddr':
            access_addr, 'group': group, 'note': note, 'responseContent': {
            'data': [{'addr1': x, 'addr2': y} for x, y in zip(addr1, addr2)]}}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/resource/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新SSL VPN资源失败: {e}')
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

    def get_resource(self, page=1, size=10, search=''):
        """获取 SSL VPN 资源列表。

        对应 API 文档中的 ``get_sslvpn_resource``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/vpn/sslvpn/resource/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取SSL VPN资源列表失败: {e}')
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

    def remove_resource(self, rsc_id, req_body=None):
        """删除 SSL VPN 资源。

        对应 API 文档中的 ``remove_sslvpn_resource``。

        :param rsc_id: 资源 ID，支持单个 ID 或 ID 列表
        :type rsc_id: int or list[int]
        :param req_body: 自定义请求体，传入后忽略 rsc_id
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(rsc_id, list):
            rsc_ids = [int(rid) for rid in rsc_id]
        else:
            rsc_ids = [int(rsc_id)]
        data = {'id': rsc_ids}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/resource/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除SSL VPN资源失败: {e}')
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
