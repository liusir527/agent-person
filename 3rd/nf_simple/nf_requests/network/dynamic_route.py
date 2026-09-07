"""BGP/OSPF/RIP 动态路由 — BGP、OSPF、RIP 协议的全局配置、邻居、路由及重分发管理。

对应 UI 页面「网络管理 → 动态路由 → BGP」「网络管理 → 动态路由 → OSPF」「网络管理 → 动态路由 → RIP」。
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


class DynamicRouteFeature(NFRequests):
    """BGP/OSPF/RIP 动态路由操作集合 — BGP 聚合/明细路由、邻居、全局配置、重分发和 OSPF 区域/接口/全局配置，以及 RIP 全局配置。"""

    def create_bgp_aggregate(self, agg_ip='', as_set='no', summary_only='no',
        ip_type='ipv4'):
        """创建 BGP 聚合路由。

        对应 API 文档中的 ``create_or_update_bgp_aggregate``。

        :param agg_ip: 聚合地址，默认 ``''``
        :type agg_ip: str
        :param as_set: 是否携带 AS 路径，``'yes'`` 携带，``'no'`` 不携带，默认 ``'no'``
        :type as_set: str
        :param summary_only: 是否抑制明细路由，``'yes'`` 抑制，``'no'`` 不抑制，默认 ``'no'``
        :type summary_only: str
        :param ip_type: IP 地址类型，默认 ``'ipv4'``
        :type ip_type: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'ip': agg_ip, 'as_set': as_set, 'summary_only': summary_only,
            'ip_type': ip_type}
        url = f'{self.base_url}/nf/network/bgp/network/aggregate_config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建BGP汇聚路由失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def update_bgp_aggregate(self, agg_id, agg_ip='', as_set='no', summary_only
        ='no', ip_type='ipv4'):
        """更新 BGP 聚合路由。

        对应 API 文档中的 ``create_or_update_bgp_aggregate``。

        :param agg_id: 聚合路由 ID
        :type agg_id: int
        :param agg_ip: 聚合地址，默认 ``''``
        :type agg_ip: str
        :param as_set: 是否携带 AS 路径，默认 ``'no'``
        :type as_set: str
        :param summary_only: 是否抑制明细路由，默认 ``'no'``
        :type summary_only: str
        :param ip_type: IP 地址类型，默认 ``'ipv4'``
        :type ip_type: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'id': agg_id, 'ip': agg_ip, 'as_set': as_set, 'summary_only':
            summary_only, 'ip_type': ip_type}
        url = f'{self.base_url}/nf/network/bgp/network/aggregate_config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'更新BGP汇聚路由失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def delete_bgp_aggregate(self, agg_ids):
        """删除 BGP 聚合路由。

        对应 API 文档中的 ``remove_bgp_aggregate``。

        :param agg_ids: 聚合路由 ID，支持 ``int``/``str``/``list``
        :type agg_ids: int or str or list
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(agg_ids, (str, int)):
            agg_ids = [int(agg_ids)]
        elif isinstance(agg_ids, list):
            agg_ids = [int(i) for i in agg_ids]
        else:
            raise Exception('agg_ids can not be None')
        body = {'id': agg_ids}
        url = f'{self.base_url}/nf/network/bgp/network/aggregate_delete/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除BGP汇聚路由失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_bgp_aggregate(self):
        """获取 BGP 聚合路由列表。

        对应 API 文档中的 ``get_bgp_aggregate``。

        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/network/bgp/network/aggregate_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取BGP汇聚路由配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_bgp_aggregate_id(self, search=''):
        """根据名称查询 BGP 聚合路由 ID。

        对应 API 文档中的 ``get_bgp_aggregate``。

        :param search: 搜索关键字（名称匹配）
        :type search: str
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_bgp_aggregate()
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def update_bgp_global_config(self, enable='no', as_id=101, local_preference
        =100, route_id='1.1.1.1', med='', is_ipv4=True, is_ipv6=False):
        """更新 BGP 全局配置。

        对应 API 文档中的 ``update_bgp_common_config``。

        :param enable: 全局配置开关，``'yes'`` 打开，``'no'`` 关闭，默认 ``'no'``
        :type enable: str
        :param as_id: AS 号，默认 ``101``
        :type as_id: int
        :param local_preference: 路由本地优先级，默认 ``100``
        :type local_preference: int
        :param route_id: Router ID，默认 ``'1.1.1.1'``
        :type route_id: str
        :param med: MED 值，默认 ``''``（空则不发）
        :type med: str
        :param is_ipv4: 是否启用 IPv4，默认 ``True``
        :type is_ipv4: bool
        :param is_ipv6: 是否启用 IPv6，默认 ``False``
        :type is_ipv6: bool
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'enable': enable, 'as_id': int(as_id), 'local_preference': int(
            local_preference), 'route_id': route_id, 'med': int(med) if med !=
            '' else '', 'is_ipv4': is_ipv4, 'is_ipv6': is_ipv6}
        url = f'{self.base_url}/nf/network/bgp/common/config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'修改BGP全局配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_bgp_global_config(self):
        """获取 BGP 全局配置。

        对应 API 文档中的 ``get_bgp_common_info``。

        :return: 成功返回 ``{"status": 2000, "result": {"enable": bool, "as_number": str, "router_id": str}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/network/bgp/common/info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'查询BGP全局配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def create_bgp_neighbor(self, ip_type='ipv4', ip='2.2.2.2', remote_as=101,
        update_source='', ebgp_multi_hop=1, keep_alive=60, hold_time=180,
        connect=120, auth='none', next_hop_self='no', weight=0, password=''):
        """创建 BGP 邻居。

        对应 API 文档中的 ``create_or_update_bgp_neighbor``。

        :param ip_type: 地址类型，``'ipv4'`` 或 ``'ipv6'``，默认 ``'ipv4'``
        :type ip_type: str
        :param ip: 邻居 IP 地址，默认 ``'2.2.2.2'``
        :type ip: str
        :param remote_as: 远端 AS 号，默认 ``101``
        :type remote_as: int
        :param update_source: 发送接口，默认 ``''``
        :type update_source: str
        :param ebgp_multi_hop: EBGP 最大跳数，默认 ``1``
        :type ebgp_multi_hop: int
        :param keep_alive: 邻居保活时间（秒），默认 ``60``
        :type keep_alive: int
        :param hold_time: 邻居老化时间（秒），默认 ``180``
        :type hold_time: int
        :param connect: 邻居重连接时间（秒），默认 ``120``
        :type connect: int
        :param auth: 认证类型，``'none'`` 无认证，``'md5'`` 为 MD5 认证，默认 ``'none'``
        :type auth: str
        :param next_hop_self: 下一跳属性，``'no'`` 默认，``'yes'`` 本机，默认 ``'no'``
        :type next_hop_self: str
        :param weight: 本地路由权重，默认 ``0``
        :type weight: int
        :param password: 认证密码，默认 ``''``
        :type password: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'ip_type': ip_type, 'ip': ip, 'remote_as': remote_as,
            'update_source': update_source, 'ebgp_multihop': ebgp_multi_hop,
            'keepalive': int(keep_alive), 'holdtime': int(hold_time), 'connect':
            int(connect), 'auth': auth, 'next_hop_self': next_hop_self,
            'weight': int(weight), 'password': password}
        url = f'{self.base_url}/nf/network/bgp/neighbor/config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建BGP邻居失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def update_bgp_neighbor(self, nbr_id, ip_type='ipv4', ip='2.2.2.2',
        remote_as=101, update_source='', ebgp_multi_hop=1, keep_alive=60,
        hold_time=180, connect=120, auth='none', next_hop_self='no', weight=0,
        password=''):
        """更新 BGP 邻居。

        对应 API 文档中的 ``create_or_update_bgp_neighbor``。

        :param nbr_id: 邻居 ID
        :type nbr_id: int
        :param ip_type: 地址类型，默认 ``'ipv4'``
        :type ip_type: str
        :param ip: 邻居 IP 地址，默认 ``'2.2.2.2'``
        :type ip: str
        :param remote_as: 远端 AS 号，默认 ``101``
        :type remote_as: int
        :param update_source: 发送接口，默认 ``''``
        :type update_source: str
        :param ebgp_multi_hop: EBGP 最大跳数，默认 ``1``
        :type ebgp_multi_hop: int
        :param keep_alive: 邻居保活时间（秒），默认 ``60``
        :type keep_alive: int
        :param hold_time: 邻居老化时间（秒），默认 ``180``
        :type hold_time: int
        :param connect: 邻居重连接时间（秒），默认 ``120``
        :type connect: int
        :param auth: 认证类型，默认 ``'none'``
        :type auth: str
        :param next_hop_self: 下一跳属性，默认 ``'no'``
        :type next_hop_self: str
        :param weight: 本地路由权重，默认 ``0``
        :type weight: int
        :param password: 认证密码，默认 ``''``
        :type password: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'id': nbr_id, 'ip_type': ip_type, 'ip': ip, 'remote_as':
            remote_as, 'update_source': update_source, 'ebgp_multihop':
            ebgp_multi_hop, 'keepalive': int(keep_alive), 'holdtime': int(
            hold_time), 'connect': int(connect), 'auth': auth, 'next_hop_self':
            next_hop_self, 'weight': int(weight), 'password': password}
        url = f'{self.base_url}/nf/network/bgp/neighbor/config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'更新BGP邻居失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def delete_bgp_neighbor(self, nbr_ids):
        """删除 BGP 邻居。

        对应 API 文档中的 ``remove_bgp_neighbor``。

        :param nbr_ids: BGP 邻居 ID，支持 ``int``/``str``/``list``
        :type nbr_ids: int or str or list
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(nbr_ids, (str, int)):
            nbr_ids = [int(nbr_ids)]
        elif isinstance(nbr_ids, list):
            nbr_ids = [int(i) for i in nbr_ids]
        else:
            raise Exception('nbr_ids can not be None')
        body = {'id': nbr_ids}
        url = f'{self.base_url}/nf/network/bgp/neighbor/delete/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除BGP邻居失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_bgp_neighbor(self, page=1, size=10):
        """获取 BGP 邻居列表。

        对应 API 文档中的 ``get_bgp_neighbor``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'page': page, 'size': size}
        url = f'{self.base_url}/nf/network/bgp/neighbor/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'查询BGP邻居表配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_bgp_neighbor_id(self, page=1, size=10, search=''):
        """根据名称查询 BGP 邻居 ID。

        对应 API 文档中的 ``get_bgp_neighbor``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字（名称匹配）
        :type search: str
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_bgp_neighbor(page=page, size=size)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def create_bgp_network_detail(self, net_ip='1.1.1.1/24', ip_type='ipv4'):
        """创建 BGP 明细路由。

        对应 API 文档中的 ``create_or_update_bgp_detail``。

        :param net_ip: 明细路由 IP/掩码，默认 ``'1.1.1.1/24'``
        :type net_ip: str
        :param ip_type: 路由类型，默认 ``'ipv4'``
        :type ip_type: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'ip': net_ip, 'ip_type': ip_type}
        url = f'{self.base_url}/nf/network/bgp/network/detail_config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建BGP明细路由失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def update_bgp_network_detail(self, net_id, net_ip='1.1.1.1/24', ip_type='ipv4'
        ):
        """更新 BGP 明细路由。

        对应 API 文档中的 ``create_or_update_bgp_detail``。

        :param net_id: 明细路由 ID
        :type net_id: int
        :param net_ip: 明细路由 IP/掩码，默认 ``'1.1.1.1/24'``
        :type net_ip: str
        :param ip_type: 路由类型，默认 ``'ipv4'``
        :type ip_type: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        body = {'id': net_id, 'ip': net_ip, 'ip_type': ip_type}
        url = f'{self.base_url}/nf/network/bgp/network/detail_config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'更新BGP明细路由失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def delete_bgp_network_detail(self, net_ids):
        """删除 BGP 明细路由。

        对应 API 文档中的 ``remove_bgp_detail``。

        :param net_ids: 明细路由 ID，支持 ``int``/``str``/``list``
        :type net_ids: int or str or list
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(net_ids, (str, int)):
            net_ids = [int(net_ids)]
        elif isinstance(net_ids, list):
            net_ids = [int(i) for i in net_ids]
        else:
            raise Exception('net_ids can not be None')
        body = {'id': net_ids}
        url = f'{self.base_url}/nf/network/bgp/network/detail_delete/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除BGP明细路由失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_bgp_network_detail(self):
        """获取 BGP 明细路由列表。

        对应 API 文档中的 ``get_bgp_detail``。

        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/network/bgp/network/detail_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'查询BGP明细路由配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_bgp_network_detail_id(self, search=''):
        """根据名称查询 BGP 明细路由 ID。

        对应 API 文档中的 ``get_bgp_detail``。

        :param search: 搜索关键字（名称匹配）
        :type search: str
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_bgp_network_detail()
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def update_bgp_redistribute(self, direct_ip_type='ipv4', direct_proto=
        'connected', direct_enable=False, direct_metric='1', static_ip_type=
        'ipv4', static_proto='static', static_enable=False, static_metric='1',
        rip_ip_type='ipv4', rip_proto='rip', rip_enable=False, rip_metric='1',
        ospf_ip_type='ipv4', ospf_proto='ospf', ospf_enable=False, ospf_metric='1'
        ):
        """更新 BGP 重分发配置。

        对应 API 文档中的 ``update_bgp_redist``。

        :param direct_ip_type: 直连 IP 类型，默认 ``'ipv4'``
        :type direct_ip_type: str
        :param direct_proto: 直连协议，默认 ``'connected'``
        :type direct_proto: str
        :param direct_enable: 是否开启直连重分发，默认 ``False``
        :type direct_enable: bool
        :param direct_metric: 直连度量值，默认 ``'1'``
        :type direct_metric: str
        :param static_ip_type: 静态 IP 类型，默认 ``'ipv4'``
        :type static_ip_type: str
        :param static_proto: 静态协议，默认 ``'static'``
        :type static_proto: str
        :param static_enable: 是否开启静态重分发，默认 ``False``
        :type static_enable: bool
        :param static_metric: 静态度量值，默认 ``'1'``
        :type static_metric: str
        :param rip_ip_type: RIP IP 类型，默认 ``'ipv4'``
        :type rip_ip_type: str
        :param rip_proto: RIP 协议，默认 ``'rip'``
        :type rip_proto: str
        :param rip_enable: 是否开启 RIP 重分发，默认 ``False``
        :type rip_enable: bool
        :param rip_metric: RIP 度量值，默认 ``'1'``
        :type rip_metric: str
        :param ospf_ip_type: OSPF IP 类型，默认 ``'ipv4'``
        :type ospf_ip_type: str
        :param ospf_proto: OSPF 协议，默认 ``'ospf'``
        :type ospf_proto: str
        :param ospf_enable: 是否开启 OSPF 重分发，默认 ``False``
        :type ospf_enable: bool
        :param ospf_metric: OSPF 度量值，默认 ``'1'``
        :type ospf_metric: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        entries = [
            (direct_enable, direct_ip_type, direct_proto, direct_metric),
            (static_enable, static_ip_type, static_proto, static_metric),
            (rip_enable,    rip_ip_type,    rip_proto,    rip_metric),
            (ospf_enable,   ospf_ip_type,   ospf_proto,   ospf_metric),
        ]
        body = [{'ip_type': ip, 'proto': p, 'enable': en, 'metric': m}
                for en, ip, p, m in entries if en]
        url = f'{self.base_url}/nf/network/bgp/redist/config/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'修改BGP重分发配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_bgp_redistribute(self):
        """获取 BGP 重分发配置。

        对应 API 文档中的 ``get_bgp_redist``。

        :return: 成功返回 ``{"status": 2000, "result": {"static": bool, "connected": bool, "ospf": bool}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/network/bgp/redist/info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取BGP重分发配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_ospf_route_id_status(self, route_id, req_body=None):
        """获取 OSPF Router ID 状态。

        对应 API 文档中的 ``update_ospf_route_id_status``。

        :param route_id: Router ID
        :type route_id: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'route_id': route_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/route_id/status/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取OSPF route-id状态失败: {e}')
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

    def update_ospf_global_config(self, enable='yes', route_id='1.1.1.1',
        compatible_rfc='yes', default_information='yes', metric_type='1',
        metric=1, passive_interface='', ha_enable=False, reboot=False, req_body
        =None):
        """更新 OSPF 全局配置。

        对应 API 文档中的 ``update_ospf_common``。

        :param enable: 是否启用，``'yes'`` 启用，``'no'`` 禁用，默认 ``'yes'``
        :type enable: str
        :param route_id: Router ID，默认 ``'1.1.1.1'``
        :type route_id: str
        :param compatible_rfc: 兼容 RFC，默认 ``'yes'``
        :type compatible_rfc: str
        :param default_information: 默认路由通告，默认 ``'yes'``
        :type default_information: str
        :param metric_type: 度量类型，默认 ``'1'``
        :type metric_type: str
        :param metric: 度量值，默认 ``1``
        :type metric: int
        :param passive_interface: 被动接口，默认 ``''``
        :type passive_interface: str
        :param ha_enable: HA 启用，默认 ``False``
        :type ha_enable: bool
        :param reboot: 重启，默认 ``False``
        :type reboot: bool
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'enable': enable, 'route_id': route_id, 'compatible_rfc':
            compatible_rfc, 'default_information': default_information,
            'metric_type': metric_type, 'metric': metric, 'passive_interface':
            passive_interface, 'ha_enable': ha_enable, 'reboot': reboot}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/common/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新OSPF全局配置失败: {e}')
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

    def update_rip_global_config(self, enable='yes', default_information='no',
        invalid_timer='180', update_timer='30', holddown_timer='120',
        passive_interface='G1/1', req_body=None):
        """更新 RIP 全局配置。

        对应 API 文档中的 ``update_rip_common``。

        :param enable: 是否启用，``'yes'`` 启用，``'no'`` 禁用，默认 ``'yes'``
        :type enable: str
        :param default_information: 默认路由通告，默认 ``'no'``
        :type default_information: str
        :param invalid_timer: 无效定时器（秒），默认 ``'180'``
        :type invalid_timer: str
        :param update_timer: 更新定时器（秒），默认 ``'30'``
        :type update_timer: str
        :param holddown_timer: 抑制定时器（秒），默认 ``'120'``
        :type holddown_timer: str
        :param passive_interface: 被动接口，默认 ``'G1/1'``
        :type passive_interface: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'enable': enable, 'default_information': default_information,
            'invalid_timer': invalid_timer, 'update_timer': update_timer,
            'holddown_timer': holddown_timer, 'passive_interface':
            passive_interface}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/rip/common/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新RIP全局配置失败: {e}')
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

    def update_rip_network(self, networks='1.2.3.4/24', req_body=None):
        """更新 RIP 网段配置。

        对应 API 文档中的 ``update_rip_network``。

        :param networks: 网段地址，默认 ``'1.2.3.4/24'``
        :type networks: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'networks': networks}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/rip/networks/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新RIP网段配置失败: {e}')
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

    def create_or_update_rip_interface(self, action='create', name='G1/2',
        auth_type='none', id='', split_horizon='yes', chain_id='',
        req_body=None):
        """创建或更新 RIP 接口配置。

        对应 API 文档中的 ``create_or_update_rip_interface``。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param name: 接口名称，默认 ``'G1/2'``
        :type name: str
        :param auth_type: 认证类型，``'none'``/``'text'``/``'md5'``，默认 ``'none'``
        :type auth_type: str
        :param id: 接口配置 ID（编辑时使用），默认 ``''``
        :type id: str
        :param split_horizon: 水平分割，``'yes'`` 启用，``'no'`` 禁用，默认 ``'yes'``
        :type split_horizon: str
        :param chain_id: 链 ID，默认 ``''``
        :type chain_id: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'name': name, 'auth_type': auth_type, 'id': id,
            'action': action, 'split_horizon': split_horizon,
            'chain_id': chain_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/rip/interfaces/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新RIP接口配置失败: {e}')
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

    def create_or_update_rip_keychain(self, name='test2', key_data=None,
        req_body=None):
        """创建或更新 RIP 密钥链配置。

        对应 API 文档中的 ``create_or_update_rip_keychain``。

        :param name: 密钥链名称，默认 ``'test2'``
        :type name: str
        :param key_data: 密钥数据列表，默认 ``None``（传空列表 ``[]``）。
            每项为一个 dict，包含以下字段：

            * ``name`` — 密钥名称
            * ``value`` — 密钥值
            * ``key_string`` — 密钥字符串
            * ``duration_accept`` — 接收持续时间（秒）
            * ``accept_lifetime`` — 接收生命周期（时间格式）
            * ``accept_lifetime_txt`` — 接收生命周期文本
            * ``duration_send`` — 发送持续时间（秒）
            * ``send_lifetime`` — 发送生命周期（时间格式）
            * ``send_lifetime_txt`` — 发送生命周期文本
        :type key_data: list or None
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'name': name, 'keyData': key_data if key_data is not None else []}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/rip/keychain/action_chain/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新RIP密钥链配置失败: {e}')
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

    def update_rip_neighbor(self, neighbors='6.2.1.1', req_body=None):
        """更新 RIP 邻居配置。

        对应 API 文档中的 ``update_rip_neighbor``。

        :param neighbors: 邻居 IP 地址，默认 ``'6.2.1.1'``
        :type neighbors: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'neighbors': neighbors}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/rip/neighbors/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新RIP邻居配置失败: {e}')
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

    def get_rip_info(self, info_type='neighbor'):
        """获取 RIP 路由信息。

        对应 API 文档中的 ``get_rip_info``。

        :param info_type: 信息类型，``'neighbor'`` 或 ``'interface'``，默认 ``'neighbor'``
        :type info_type: str
        :return: 成功返回 ``{"status": 2000, "result": [...]}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/network/route/rip/info/'
        try:
            result = self.session.get(req_url, params={'type': info_type},
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取RIP路由信息失败: {e}')
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

    def update_rip_redistribute(self, bgp_metric=None, static_metric=None,
        connect_metric=None, ospf_metric=None, req_body=None):
        """更新 RIP 路由重分发配置。

        只有显式传值的协议才会加入请求体。

        :param bgp_metric: BGP 度量值，传 ``None`` 则不下发，默认 ``None``
        :param static_metric: 静态度量值，传 ``None`` 则不下发，默认 ``None``
        :param connect_metric: 直连度量值，传 ``None`` 则不下发，默认 ``None``
        :param ospf_metric: OSPF 度量值，传 ``None`` 则不下发，默认 ``None``
        :param req_body: 自定义请求体，传入后优先使用
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        """
        entries = [('bgp', bgp_metric), ('static', static_metric),
                   ('connect', connect_metric), ('ospf', ospf_metric)]
        data = [{'proto': p, 'metric': m} for p, m in entries if m is not None]
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/rip/redistribute/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新RIP路由重分发配置失败: {e}')
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

    def create_or_update_ospf_area(self, conf_id='', action='create', area_id=
        '1.1.1.1', area_type='normal', auth_type='none', network_ip=None,
        range_ips=None, route_actions=None, metrics=None, summary=False,
        req_body=None):
        """创建或更新 OSPF 区域。

        对应 API 文档中的 ``create_or_update_ospf_area``。

        :param conf_id: 配置 ID（编辑时使用），默认 ``''``
        :type conf_id: str
        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param area_id: 区域 ID，默认 ``'1.1.1.1'``
        :type area_id: str
        :param area_type: 区域类型，``'normal'``/``'stub'``/``'nssa'``，默认 ``'normal'``
        :type area_type: str
        :param auth_type: 认证类型，``'none'``/``'key'``/``'md5'``，默认 ``'none'``
        :type auth_type: str
        :param network_ip: 网络 IP，默认 ``'1.1.1.0/24'``
        :type network_ip: str or None
        :param range_ips: 范围 IP 列表，默认 ``['1.1.1.0/24']``
        :type range_ips: list or None
        :param route_actions: 路由动作列表，默认 ``['advertise']``
        :type route_actions: list or None
        :param metrics: 度量值列表，默认 ``[0]``
        :type metrics: list or None
        :param summary: 是否汇总，默认 ``False``
        :type summary: bool
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(network_ip, list):
            network_ip = ','.join(network_ip)
        else:
            network_ip = '1.1.1.0/24' if network_ip is None else network_ip
        if isinstance(range_ips, str):
            range_ips = [range_ips]
        elif range_ips is None:
            range_ips = ['1.1.1.0/24']
        if isinstance(route_actions, str):
            route_actions = [route_actions]
        else:
            route_actions = [route_actions] if route_actions is not None else [
                'advertise']
        if isinstance(metrics, str):
            metrics = [metrics]
        else:
            metrics = [metrics] if metrics is not None else [0]
        route = [{'range_ip': range_ip, 'metric': metric, 'action':
            route_action} for range_ip, metric, route_action in zip(range_ips,
            metrics, route_actions)]
        data = {'id': conf_id, 'action': action, 'area_id': area_id, 'type':
            area_type, 'summary': summary, 'auth_type': auth_type, 'network_ip':
            network_ip, 'route': route}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/area/action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新OSPF区域失败: {e}')
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

    def get_ospf_area(self):
        """获取 OSPF 区域列表。

        对应 API 文档中的 ``get_ospf_area``。

        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/network/route/ospf/area/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取OSPF区域配置失败: {e}')
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

    def get_ospf_area_id(self, search=''):
        """根据名称查询 OSPF 区域 ID。

        对应 API 文档中的 ``get_ospf_area``。

        :param search: 搜索关键字（名称匹配）
        :type search: str
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_ospf_area()
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_ospf_area(self, conf_id, req_body=None):
        """删除 OSPF 区域。

        对应 API 文档中的 ``remove_ospf_area``。

        :param conf_id: 区域配置 ID，支持单个值或列表/元组
        :type conf_id: int or list or tuple
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(conf_id, (list, tuple)):
            conf_ids = ','.join(map(str, conf_id))
        else:
            conf_ids = str(conf_id)
        data = {'id': conf_ids}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/area/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除OSPF区域失败: {e}')
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

    def get_ospf_info(self, info_type='interface'):
        """获取 OSPF 路由信息（接口或邻居）。

        对应 API 文档中的 ``get_ospf_info``。

        :param info_type: 信息类型，``'interface'`` 或 ``'neighbor'``，默认 ``'interface'``
        :type info_type: str
        :return: 成功返回 ``{"status": 2000, "result": {...}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/network/route/ospf/info/'
        try:
            result = self.session.get(req_url, params={'type': info_type},
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取OSPF工作信息失败: {e}')
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

    def get_ospf_redistribute_config(self):
        """获取 OSPF 路由重分发配置。

        对应 API 文档中的 ``update_ospf_redistribute``。

        :return: 成功返回 ``{"status": 2000, "result": {...}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/network/route/ospf/redistribute/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取OSPF路由重分发配置失败: {e}')
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

    def update_ospf_redistribute_config(self, bgp=False, bgp_metric_type='2',
        bgp_metric_value='1', direct=False, direct_metric_type='2',
        direct_metric_value='1', static=False, static_metric_type='2',
        static_metric_value='1', rip=False, rip_metric_type='2',
        rip_metric_value='1', req_body=None):
        """更新 OSPF 路由重分发配置。

        只有显式传 ``True`` 的协议才会加入请求体。

        :param bgp: 是否导入 BGP 路由，默认 ``False``
        :param direct: 是否导入直连路由，默认 ``False``
        :param static: 是否导入静态路由，默认 ``False``
        :param rip: 是否导入 RIP 路由，默认 ``False``
        :param req_body: 自定义请求体，传入后优先使用
        :return: 成功返回响应 dict，失败返回 ``False``
        """
        entries = [
            (bgp,    'bgp',     bgp_metric_type,    bgp_metric_value),
            (direct, 'connect', direct_metric_type, direct_metric_value),
            (static, 'static',  static_metric_type, static_metric_value),
            (rip,    'rip',     rip_metric_type,    rip_metric_value),
        ]
        data = [{'type': t, 'metric_type': mt, 'metric': mv}
                for enabled, t, mt, mv in entries if enabled]
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/redistribute/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新OSPF路由重分发配置失败: {e}')
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
