"""DNS 服务 — DNS 透明代理、第三方 DNS 服务器和 DNS Doctoring 的增删查改及系统 DNS 配置。

对应 UI 页面「网络管理 → DNS」。
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


class DnsFeature(NFRequests):
    """DNS 服务操作集合 — DNS 透明代理、第三方服务器、Doctoring 和系统 DNS 配置。"""

    def create_or_update_dns_transparent_proxy(self, action='create', domain='*',
        dst_addr='*', enable=True, exceptions_domains=None,
        exceptions_actions=None, exceptions_server_obj_ids=None, proxy_id=0,
        interface_name='G1/5,G1/6,G1/7', name='test', proxy=True,
        server_obj_id=1, src_addr='*'):
        """创建或更新 DNS 透明代理。

        对应接口 ``POST /nf/network/dns/transparent_proxy/action_dns/``。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param domain: 域名匹配规则。字符串直接使用；列表自动用逗号拼接。
            默认 ``'*'`` 表示匹配所有域名
        :type domain: str or list
        :param dst_addr: 目的地址匹配规则。字符串直接使用；列表自动用逗号拼接。
            默认 ``'*'`` 表示匹配所有目的地址
        :type dst_addr: str or list
        :param enable: 是否启用，默认 ``True``
        :type enable: bool
        :param exceptions_domains: 例外域名列表，如 ``['qq.com', 'baidu.com']``
        :type exceptions_domains: str or list or None
        :param exceptions_actions: 例外动作列表，与 exceptions_domains 一一对应。
            ``0`` = 代理，``1`` = 不代理。单值会自动扩展为列表。
            默认 ``0``（代理）
        :type exceptions_actions: int or list or None
        :param exceptions_server_obj_ids: 例外 DNS 第三方服务器 ID 列表，
            与 exceptions_domains 一一对应。单值会自动扩展为列表。
            默认 ``0``（不指定第三方服务器）
        :type exceptions_server_obj_ids: int or list or None
        :param proxy_id: DNS 透明代理 ID（编辑时使用），默认 ``0``
        :type proxy_id: int
        :param interface_name: 入接口，支持多接口逗号分隔，如 ``'G1/5,G1/6,G1/7'``。
            也可传列表自动拼接。默认 ``'G1/5,G1/6,G1/7'``
        :type interface_name: str or list
        :param name: 透明代理名称，默认 ``'test'``
        :type name: str
        :param proxy: 动作，``True`` 为代理，``False`` 为不代理，默认 ``True``
        :type proxy: bool
        :param server_obj_id: 关联的 DNS 第三方服务器 ID，默认 ``1``
        :type server_obj_id: int
        :param src_addr: 源地址匹配规则。字符串直接使用；列表自动用逗号拼接。
            默认 ``'*'`` 表示匹配所有源地址
        :type src_addr: str or list
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool

        请求体示例::

            {
                "action": "create",
                "id": 0,
                "name": "test",
                "enable": true,
                "domain": "*",
                "src_addr": "*",
                "dst_addr": "*",
                "interface_name": "G1/5,G1/6,G1/7",
                "server_obj_id": 1,
                "proxy": true,
                "exceptions": [
                    {"domain": "qq.com", "action": 1, "serverObjId": 0},
                    {"domain": "baidu.com", "action": 0, "serverObjId": 1}
                ]
            }
        """
        if isinstance(src_addr, list):
            src_addr = ','.join(src_addr)
        if isinstance(dst_addr, list):
            dst_addr = ','.join(dst_addr)
        if isinstance(domain, list):
            domain = ','.join(domain)
        if isinstance(interface_name, list):
            interface_name = ','.join(interface_name)
        if exceptions_domains is None:
            exceptions = []
        else:
            if isinstance(exceptions_domains, str):
                exceptions_domains = [exceptions_domains]
            elif not isinstance(exceptions_domains, list):
                exceptions_domains = [exceptions_domains]
            if exceptions_actions is None:
                exceptions_actions = [0] * len(exceptions_domains)
            elif isinstance(exceptions_actions, (int, str)):
                exceptions_actions = [exceptions_actions] * len(exceptions_domains)
            if exceptions_server_obj_ids is None:
                exceptions_server_obj_ids = [0] * len(exceptions_domains)
            elif isinstance(exceptions_server_obj_ids, (int, str)):
                exceptions_server_obj_ids = [exceptions_server_obj_ids] * len(
                    exceptions_domains)
            exceptions = [{'domain': exception_domain, 'action':
                exception_action, 'serverObjId': exception_server_obj_id} for
                exception_domain, exception_action, exception_server_obj_id in
                zip(exceptions_domains, exceptions_actions,
                exceptions_server_obj_ids)]
        data = {'action': action, 'domain': domain, 'dst_addr': dst_addr,
            'enable': enable, 'exceptions': exceptions, 'interface_name':
            interface_name, 'id': proxy_id, 'name': name, 'proxy': proxy,
            'server_obj_id': server_obj_id, 'src_addr': src_addr}
        if action == 'edit':
            data['id'] = proxy_id
        url = f'{self.base_url}/nf/network/dns/transparent_proxy/action_dns/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新DNS透明代理失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def remove_dns_transparent_proxy(self, proxy_id, req_body=None):
        """删除 DNS 透明代理。

        对应 API 文档中的 ``remove_dns_proxy``。

        :param proxy_id: DNS 透明代理 ID 或 ID 列表
        :type proxy_id: int or list
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            if isinstance(proxy_id, int):
                proxy_id = [proxy_id]
            data = {'id': proxy_id}
        url = f'{self.base_url}/nf/network/dns/transparent_proxy/delete_dns/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除DNS透明代理失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns_transparent_proxy(self, size=10, page=1, search='', req_param=None
        ):
        """获取 DNS 透明代理列表。

        对应 API 文档中的 ``get_dns_proxy``。

        :param size: 每页显示条数，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索条件，默认 ``''``
        :type search: str
        :param req_param: 自定义查询参数，传入后优先使用
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'size': size, 'page': page, 'search': search
            } if req_param is None else req_param
        url = f'{self.base_url}/nf/network/dns/transparent_proxy/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取DNS透明代理列表失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns_transparent_proxy_id(self, size=10, page=1, search='',
        req_param=None):
        """根据名称查询 DNS 透明代理 ID。

        对应 API 文档中的 ``get_dns_proxy``。

        :param size: 每页显示条数，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索关键字（名称匹配）
        :type search: str
        :param req_param: 自定义查询参数
        :type req_param: dict or None
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_dns_transparent_proxy(size=size, page=page, search=search,
                                              req_param=req_param)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def clear_dns_transparent_proxy_hit_count(self, proxy_id, req_body=None):
        """清除 DNS 透明代理命中计数。

        对应 API 文档中的 ``clear_dns_proxy_hit_count``。

        :param proxy_id: DNS 透明代理 ID 或 ID 列表
        :type proxy_id: int or list
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            if isinstance(proxy_id, int):
                proxy_id = [proxy_id]
            data = {'id': proxy_id}
        url = f'{self.base_url}/nf/network/dns/transparent_proxy/clear_hit_count/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清除DNS透明代理命中次数失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def update_dns_transparent_proxy_status(self, proxy_ids, enable, req_param=None
        ):
        """启用或禁用 DNS 透明代理。

        对应 API 文档中的 ``enable_dns_proxy``。

        :param proxy_ids: DNS 透明代理 ID 或 ID 列表
        :type proxy_ids: int or list
        :param enable: 是否启用
        :type enable: bool
        :param req_param: 自定义请求体，传入后优先使用
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_param is None:
            if isinstance(proxy_ids, int):
                proxy_ids = [proxy_ids]
            data = {'ids': proxy_ids, 'enable': enable}
        else:
            data = req_param
        url = f'{self.base_url}/nf/network/dns/transparent_proxy/enable_dns/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新DNS透明代理状态失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def create_or_update_dns_third_server(self, action='create', comment='',
        detect=True, domain='test.com', server_id=-1, master_server='8.8.8.8',
        name='test', stand_by_server1='', stand_by_server2=''):
        """创建或更新 DNS 第三方服务器。

        对应 API 文档中的 ``create_or_update_dns_third_server``。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param comment: 备注，默认 ``''``
        :type comment: str
        :param detect: 是否开启 DNS 探测，默认 ``True``
        :type detect: bool
        :param domain: 域名，默认 ``'test.com'``
        :type domain: str
        :param server_id: 第三方服务器 ID（编辑时使用），默认 ``-1``
        :type server_id: int
        :param master_server: DNS 服务器一，默认 ``'8.8.8.8'``
        :type master_server: str
        :param name: 名称，默认 ``'test'``
        :type name: str
        :param stand_by_server1: DNS 服务器二，默认 ``''``
        :type stand_by_server1: str
        :param stand_by_server2: DNS 服务器三，默认 ``''``
        :type stand_by_server2: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'action': action, 'comment': comment, 'detect': detect,
            'domain': domain, 'id': server_id, 'master_server': master_server,
            'name': name, 'stand_by_server1': stand_by_server1,
            'stand_by_server2': stand_by_server2}
        url = f'{self.base_url}/nf/network/dns/third_server/action_dns/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新DNS三方服务器失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def create_or_update_dns_doctoring(self, action='create', enable=True,
        domain='www.test2.com', orig_ip='192.168.92.3', trans_ip=
        '203.13.56.101', comment='', lb_algo=1):
        """创建或更新 DNS Doctoring。

        对应 API 文档中的 ``create_or_update_dns_doctoring``。

        :param action: 操作类型，默认 ``'create'``
        :type action: str
        :param enable: 是否启用，默认 ``True``
        :type enable: bool
        :param domain: 域名，默认 ``'www.test2.com'``
        :type domain: str
        :param orig_ip: 原始 IP，默认 ``'192.168.92.3'``
        :type orig_ip: str
        :param trans_ip: 转换后 IP，默认 ``'203.13.56.101'``
        :type trans_ip: str
        :param comment: 备注，默认 ``''``
        :type comment: str
        :param lb_algo: 负载均衡算法，默认 ``1``
        :type lb_algo: int
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'action': action, 'enable': enable, 'domain': domain, 'orig_ip':
            orig_ip, 'trans_ip': trans_ip, 'comment': comment, 'lb_algo': lb_algo}
        url = f'{self.base_url}/nf/network/dns/dns_doctoring/action_doctoring/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建DNS Doctoring失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def create_or_update_dns_proxy_config(self, is_enable=True, interface_id=None,
        is_enable_proxy=True, server_obj_id=1, cache_age_time=10, proxy_timeout=3,
        proxy_retry=2, req_body=None):
        """配置 DNS 代理（一次绑定多接口）。

        对应接口 ``POST /nf/network/dns/dns_proxy/config/``。

        与 :meth:`create_or_update_dns_transparent_proxy`（单接口透明代理）不同，
        本接口支持一次性绑定多个接口，并配置缓存、超时、重试等参数。

        :param is_enable: 是否启用 DNS 代理，默认 ``True``
        :type is_enable: bool
        :param interface_id: 绑定接口列表，如 ``["G1/5", "G1/6", "G1/7"]``，
            默认 ``["G1/5", "G1/6", "G1/7"]``
        :type interface_id: list[str] or str or None
        :param is_enable_proxy: 是否启用代理（转发解析模式），默认 ``True``
        :type is_enable_proxy: bool
        :param server_obj_id: 关联的 DNS 第三方服务器 ID，默认 ``1``
        :type server_obj_id: int
        :param cache_age_time: 缓存老化时间（分钟），默认 ``10``
        :type cache_age_time: int
        :param proxy_timeout: 代理超时时间（秒），默认 ``3``
        :type proxy_timeout: int
        :param proxy_retry: 代理重试次数，默认 ``2``
        :type proxy_retry: int
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if interface_id is None:
            interface_id = ['G1/5', 'G1/6', 'G1/7']
        elif isinstance(interface_id, str):
            interface_id = [interface_id]
        data = {'is_enable': is_enable, 'interface_id': interface_id,
            'is_enable_proxy': is_enable_proxy, 'server_obj_id': server_obj_id,
            'cache_age_time': cache_age_time, 'proxy_timeout': proxy_timeout,
            'proxy_retry': proxy_retry}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/dns/dns_proxy/config/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'配置 DNS 代理失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def remove_dns_third_server(self, server_id, req_param=None):
        """删除 DNS 第三方服务器。

        对应 API 文档中的 ``remove_dns_third_server``。

        :param server_id: DNS 第三方服务器 ID 或 ID 列表
        :type server_id: int or list
        :param req_param: 自定义请求体，传入后优先使用
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_param is None:
            if isinstance(server_id, int):
                server_id = [server_id]
            data = {'id': server_id}
        else:
            data = req_param
        url = f'{self.base_url}/nf/network/dns/third_server/delete_dns/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除DNS三方服务器失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns_third_server(self, size=10, page=1, search='', req_param=None):
        """获取 DNS 第三方服务器列表。

        对应 API 文档中的 ``get_dns_third_server``。

        :param size: 每页显示条数，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索条件，默认 ``''``
        :type search: str
        :param req_param: 自定义查询参数，传入后优先使用
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'size': size, 'page': page, 'search': search
            } if req_param is None else req_param
        url = f'{self.base_url}/nf/network/dns/third_server/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取DNS三方服务器列表失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns_third_server_id(self, size=10, page=1, search='', req_param=None):
        """根据名称查询 DNS 第三方服务器 ID。

        对应 API 文档中的 ``get_dns_third_server``。

        :param size: 每页显示条数，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索关键字（名称匹配）
        :type search: str
        :param req_param: 自定义查询参数
        :type req_param: dict or None
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_dns_third_server(size=size, page=page, search=search,
                                          req_param=req_param)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def update_dns_config(self, pri_dns='0.0.0.0', sec_dns='0.0.0.0', req_body=None
        ):
        """更新系统 DNS 配置。

        对应 API 文档中的 ``get_dns_system_config``。

        :param pri_dns: 主 DNS，默认 ``'0.0.0.0'``
        :type pri_dns: str
        :param sec_dns: 备 DNS，默认 ``'0.0.0.0'``
        :type sec_dns: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'priDns': pri_dns, 'secDns': sec_dns}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/dns_config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新DNS配置失败: {e}')
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

    def create_or_update_dns_domain_record(self, action='create', domain_name=
        'test1.com', record_id=0, addr_ip='10.0.0.1', addr_owner='internal',
        is_enable=True, req_body=None):
        """创建或更新 DNS 本地缓存记录（域名静态解析）。

        对应接口 ``POST /nf/network/dns/domain_record/action_record/``。

        用于配置本地域名→IP 的静态映射，不依赖外部 DNS 服务器解析。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param domain_name: 域名，默认 ``'test1.com'``
        :type domain_name: str
        :param record_id: 记录 ID，编辑时必填，默认 ``0``
        :type record_id: int
        :param addr_ip: 映射的 IP 地址，默认 ``'10.0.0.1'``
        :type addr_ip: str
        :param addr_owner: 地址来源，``'internal'`` 内部或 ``'external'`` 外部，
            默认 ``'internal'``
        :type addr_owner: str
        :param is_enable: 是否启用，默认 ``True``
        :type is_enable: bool
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'action': action, 'domain_name': domain_name, 'id': record_id,
            'addr_ip': addr_ip, 'addr_owner': addr_owner, 'is_enable': is_enable}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/dns/domain_record/action_record/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新DNS本地缓存记录失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns_config(self):
        """获取系统 DNS 配置。

        对应 API 文档中的 ``get_dns_system_config``。

        :return: 成功返回 ``{"status": 2000, "result": {...}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/system/dns_config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取DNS配置失败: {e}')
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

    def create_or_update_dns_domain_record(self, action='create', domain_name=
        'test1.com', record_id=0, addr_ip='10.0.0.1', addr_owner='internal',
        is_enable=True, req_body=None):
        """创建或更新 DNS 本地缓存记录（域名静态解析）。

        对应接口 ``POST /nf/network/dns/domain_record/action_record/``。

        用于配置本地域名→IP 的静态映射，不依赖外部 DNS 服务器解析。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param domain_name: 域名，默认 ``'test1.com'``
        :type domain_name: str
        :param record_id: 记录 ID，编辑时必填，默认 ``0``
        :type record_id: int
        :param addr_ip: 映射的 IP 地址，默认 ``'10.0.0.1'``
        :type addr_ip: str
        :param addr_owner: 地址来源，``'internal'`` 内部或 ``'external'`` 外部，
            默认 ``'internal'``
        :type addr_owner: str
        :param is_enable: 是否启用，默认 ``True``
        :type is_enable: bool
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'action': action, 'domain_name': domain_name, 'id': record_id,
            'addr_ip': addr_ip, 'addr_owner': addr_owner, 'is_enable': is_enable}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/dns/domain_record/action_record/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新DNS本地缓存记录失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
