"""DHCP 服务 — DHCP Server/Relay 的增删查改、启用/禁用和租约详情查询。

对应 UI 页面「网络管理 → DHCP」。
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


class DhcpFeature(NFRequests):
    """DHCP 服务操作集合 — DHCP Server/Relay 的增删查改、启停和详情查询。"""

    def create_or_update_dhcp_service(self, action='create', dhcp_srv_id=-1,
        name='test', protocol_type='0', service_type='0', enable_status='1',
        bind_interface='G1/1', relay_server=None, ip_pool=None, sub_mask=None,
        dhcp_gw=None, lease_time=None, pri_dns='', sec_dns='', pri_wins='',
        sec_wins='', dhcp_config_name=None, dhcp_config_addr=None,
        dhcp_config_mac=None):
        """创建或更新 DHCP 服务。

        对应 API 文档中的 ``create_or_update_dhcp``。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param dhcp_srv_id: DHCP 服务 ID，更新时使用，默认 ``-1``
        :type dhcp_srv_id: int
        :param name: DHCP 服务名称，默认 ``'test'``
        :type name: str
        :param protocol_type: 协议类型，默认 ``'0'``
        :type protocol_type: str
        :param service_type: 服务类型，``'0'`` 为 Server，``'1'`` 为 Relay，默认 ``'0'``
        :type service_type: str
        :param enable_status: 启用状态，``'0'`` 禁用，``'1'`` 启用，默认 ``'1'``
        :type enable_status: str
        :param bind_interface: 绑定接口，默认 ``'G1/1'``
        :type bind_interface: str
        :param relay_server: 中继服务器地址（``service_type='1'`` 时），默认 ``'1.1.1.2'``
        :type relay_server: str or None
        :param ip_pool: 地址池（``service_type='0'`` 时），默认 ``'1.1.1.10-1.1.1.20'``
        :type ip_pool: str or None
        :param sub_mask: 子网掩码（``service_type='0'`` 时），默认 ``'255.255.255.0'``
        :type sub_mask: str or None
        :param dhcp_gw: DHCP 网关（``service_type='0'`` 时），默认 ``'1.1.1.1'``
        :type dhcp_gw: str or None
        :param lease_time: 租约时间（秒），Server 默认 ``3600``，Relay 默认 ``300``
        :type lease_time: int or None
        :param pri_dns: 主 DNS，默认 ``''``
        :type pri_dns: str
        :param sec_dns: 备 DNS，默认 ``''``
        :type sec_dns: str
        :param pri_wins: 主 WINS，默认 ``''``
        :type pri_wins: str
        :param sec_wins: 备 WINS，默认 ``''``
        :type sec_wins: str
        :param dhcp_config_name: 静态分配名称列表，默认 ``['pc1']``
        :type dhcp_config_name: str or list or None
        :param dhcp_config_addr: 静态分配地址列表，默认自动填充
        :type dhcp_config_addr: str or list or None
        :param dhcp_config_mac: 静态分配 MAC 列表，默认自动生成
        :type dhcp_config_mac: str or list or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if service_type == '0':
            ip_pool = ip_pool if ip_pool is not None else '1.1.1.10-1.1.1.20'
            sub_mask = sub_mask if sub_mask is not None else '255.255.255.0'
            dhcp_gw = dhcp_gw if dhcp_gw is not None else '1.1.1.1'
            lease_time = lease_time if lease_time is not None else 3600
        elif service_type == '1':
            relay_server = relay_server if relay_server is not None else '1.1.1.2'
            lease_time = lease_time if lease_time is not None else 300
        if (dhcp_config_name is None and dhcp_config_addr is None and 
            dhcp_config_mac is None):
            dhcp_configs = []
        else:
            if isinstance(dhcp_config_name, str):
                dhcp_config_name = [dhcp_config_name]
            elif dhcp_config_name is None:
                dhcp_config_name = ['pc1']
            if isinstance(dhcp_config_addr, str):
                dhcp_config_addr = [dhcp_config_addr]
            elif dhcp_config_addr is None:
                dhcp_config_addr = [f'10.10.10.{x}' for x in range(101, len(
                    dhcp_config_name) + 101)]
            if isinstance(dhcp_config_mac, str):
                dhcp_config_mac = [dhcp_config_mac]
            elif dhcp_config_mac is None:
                dhcp_config_mac = []
                for index in range(len(dhcp_config_name)):
                    suffix = index + 1
                    dhcp_config_mac.append(f'23:de:54:00:00:{suffix:02x}')
            dhcp_configs = [{'name': item_name, 'addr': addr, 'mac': mac} for 
                item_name, addr, mac in zip(dhcp_config_name, dhcp_config_addr,
                dhcp_config_mac)]
        data = {'action': action, 'id': dhcp_srv_id, 'name': name,
            'protocol_type': protocol_type, 'service_type': service_type,
            'enable_status': enable_status, 'bind_interface': bind_interface,
            'relay_server': relay_server, 'ip_pool': ip_pool, 'submask':
            sub_mask, 'dhcpgw': dhcp_gw, 'lease_time': lease_time, 'pri_dns':
            pri_dns, 'sec_dns': sec_dns, 'pri_wins': pri_wins, 'sec_wins':
            sec_wins, 'dhcp_configs': dhcp_configs}
        url = f'{self.base_url}/nf/network/dhcp/action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新DHCP服务失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def remove_dhcp_service(self, dhcp_srv_id, req_body=None):
        """删除 DHCP 服务。

        对应 API 文档中的 ``remove_dhcp``。

        :param dhcp_srv_id: 服务 ID，支持单个 ``int`` 或列表
        :type dhcp_srv_id: int or list
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(dhcp_srv_id, int):
            dhcp_srv_id = [dhcp_srv_id]
        data = {'id': dhcp_srv_id} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/network/dhcp/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除DHCP服务失败: {e}')
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

    def get_dhcp_service(self, page=1, size=10, search='', params=None):
        """获取 DHCP 服务列表。

        对应 API 文档中的 ``get_dhcp``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字，默认 ``''``
        :type search: str
        :param params: 自定义查询参数，传入后优先使用
        :type params: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        query_params = {'page': page, 'size': size, 'search': search
            } if params is None else params
        req_url = f'{self.base_url}/nf/network/dhcp/'
        try:
            result = self.session.get(req_url, params=query_params, verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'获取DHCP服务列表失败: {e}')
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

    def get_dhcp_service_id(self, page=1, size=10, search='', params=None):
        """根据名称查询 DHCP 服务 ID。

        对应 API 文档中的 ``get_dhcp``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字（名称匹配）
        :type search: str
        :param params: 自定义查询参数
        :type params: dict or None
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_dhcp_service(page=page, size=size, search=search,
                                     params=params)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def enable_or_disable_dhcp_service(self, dhcp_srv_id, enable, req_body=None):
        """启用或禁用 DHCP 服务。

        对应 API 文档中的 ``enable_dhcp``。

        :param dhcp_srv_id: 服务 ID，支持单个 ``int`` 或列表
        :type dhcp_srv_id: int or list
        :param enable: ``True`` 启用，``False`` 禁用
        :type enable: bool
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(dhcp_srv_id, int):
            dhcp_srv_id = [dhcp_srv_id]
        data = {'id': dhcp_srv_id, 'enable': enable
            } if req_body is None else req_body
        req_url = f'{self.base_url}/nf/network/dhcp/enable/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'启用或禁用DHCP服务失败: {e}')
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

    def get_dhcp_service_detail(self, page=1, size=10, search='',
        bind_interface=None, params=None):
        """获取 DHCP 服务详情（租约信息）。

        对应 API 文档中的 ``get_dhcp_detail``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字，默认 ``''``
        :type search: str
        :param bind_interface: 绑定接口过滤
        :type bind_interface: str or None
        :param params: 自定义查询参数，传入后优先使用
        :type params: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        query_params = {'page': page, 'size': size, 'search': search,
            'bind_interface': bind_interface} if params is None else params
        req_url = f'{self.base_url}/nf/network/dhcp/detail'
        try:
            result = self.session.get(req_url, params=query_params, verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'获取DHCP服务详情失败: {e}')
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
