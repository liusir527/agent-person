"""SSL VPN 链路 — SSL VPN 链路的增删查改。

对应 UI 页面「VPN → SSL VPN → 链路配置」。

对应 API 文档中的 ``get_sslvpn_links``、``create_or_update_sslvpn_link``、
``remove_sslvpn_link``。
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


class SslVpnLinkFeature(NFRequests):
    """SSL VPN 链路操作集合 — SSL VPN 链路的增删查改。"""

    def create_or_update_ssl_vpn_link(self, action='create', name='link1',
        model='direct', interface='G1/1', ha='', status=None, vpn_access_ip=
        '172.30.1.1', vpn_map_ip=None, l3vpn_port=None, https_port=None,
        vpn_link_id=-1, req_body=None):
        """创建或更新 SSL VPN 链路。

        对应 API 文档中的 ``create_or_update_sslvpn_link``。

        :param action: 操作类型，``"create"`` 创建，``"edit"`` 编辑
        :type action: str
        :param name: 链路名称
        :type name: str
        :param model: 链路模式，``"direct"`` 直连，``"nat"`` NAT 模式
        :type model: str
        :param interface: 绑定接口
        :type interface: str
        :param ha: HA 线路
        :type ha: str
        :param status: 链路状态
        :type status: bool or None
        :param vpn_access_ip: VPN 接入 IP
        :type vpn_access_ip: str
        :param vpn_map_ip: VPN 映射 IP（NAT 模式下有效，默认 ``"172.30.1.100"``）
        :type vpn_map_ip: str or None
        :param l3vpn_port: L3VPN 端口（NAT 模式下有效，默认 ``"50001"``）
        :type l3vpn_port: str or None
        :param https_port: HTTPS 端口（NAT 模式下有效，默认 ``"4433"``）
        :type https_port: str or None
        :param vpn_link_id: 编辑时传入的链路 ID，默认 ``-1``（创建）
        :type vpn_link_id: int
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if model == 'nat':
            vpn_map_ip = '172.30.1.100' if vpn_map_ip is None else vpn_map_ip
            l3vpn_port = '50001' if l3vpn_port is None else l3vpn_port
            https_port = '4433' if https_port is None else https_port
        else:
            vpn_map_ip = '' if vpn_map_ip is None else vpn_map_ip
            l3vpn_port = '' if l3vpn_port is None else l3vpn_port
            https_port = '' if https_port is None else https_port
        data = {'action': action, 'name': name, 'model': model, 'interface':
            interface, 'ha': ha, 'vpn_access_ip': vpn_access_ip, 'vpn_map_ip':
            vpn_map_ip, 'l3vpn_port': l3vpn_port, 'https_port': https_port,
            'id': vpn_link_id}
        if status is not None:
            data['status'] = status
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/links/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新SSL VPN链路失败: {e}')
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

    def get_ssl_vpn_link(self, page=1, size=10, where='OR', name='', model='',
        interface='', vpn_access_ip='', vpn_map_ip='', status='', ha=''):
        """获取 SSL VPN 链路列表（支持精确过滤）。

        对应 API 文档中的 ``get_sslvpn_links``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param where: 过滤逻辑，``"OR"`` 或 ``"AND"``
        :type where: str
        :param name: 链路名称过滤
        :type name: str
        :param model: 链路模式过滤
        :type model: str
        :param interface: 接口过滤
        :type interface: str
        :param vpn_access_ip: VPN 接入 IP 过滤
        :type vpn_access_ip: str
        :param vpn_map_ip: VPN 映射 IP 过滤
        :type vpn_map_ip: str
        :param status: 状态过滤
        :type status: str
        :param ha: HA 线路过滤
        :type ha: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'page': page, 'size': size, 'where': where, 'name': name,
            'model': model, 'interface': interface, 'vpn_access_ip':
            vpn_access_ip, 'vpn_map_ip': vpn_map_ip, 'status': status, 'ha': ha}
        req_url = f'{self.base_url}/nf/vpn/sslvpn/links/info/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取SSL VPN链路列表失败: {e}')
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

    def remove_ssl_vpn_link(self, vpn_link_id, req_body=None):
        """删除 SSL VPN 链路。

        对应 API 文档中的 ``remove_sslvpn_link``。

        :param vpn_link_id: 链路 ID，支持单个 ID 或 ID 列表
        :type vpn_link_id: int or list[int]
        :param req_body: 自定义请求体，传入后忽略 vpn_link_id
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(vpn_link_id, list):
            vpn_link_ids = [int(v_id) for v_id in vpn_link_id]
        else:
            vpn_link_ids = [int(vpn_link_id)]
        data = {'id': vpn_link_ids}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/links/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除SSL VPN链路失败: {e}')
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
