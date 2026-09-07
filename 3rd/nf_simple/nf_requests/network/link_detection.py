"""链路探测 — 链路探测的增删查改、状态管理和链路连通性查询。

对应 UI 页面「网络管理 → 链路探测」。
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


class LinkDetectionFeature(NFRequests):
    """链路探测操作集合 — 链路探测配置的增删查改、状态管理和连通性查询。"""

    def create_or_update_link_detection(self, action='create', source='', ld_id
        ='', name='link_detect_name1', if_name='G1/1', send_state=True,
        con_failure_times=3, detection_heart=5, dst_addr=None, src_addr=None,
        method=None, dst_port=None, next_hop_ip=None, req_body=None):
        """创建或更新链路探测。

        对应 API 文档中的 ``create_or_update_link_detection``。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param source: 来源，""
        :type source: str
        :param ld_id: 探测 ID，编辑时使用，默认 ``''``
        :type ld_id: str
        :param name: 探测名称，默认 ``'link_detect_name1'``
        :type name: str
        :param if_name: 出接口，默认 ``'G1/1'``
        :type if_name: str
        :param send_state: 是否启用发送状态，默认 ``True``
        :type send_state: bool
        :param con_failure_times: 连续失败次数阈值，默认 ``3``
        :type con_failure_times: int
        :param detection_heart: 探测心跳间隔（秒），默认 ``5``
        :type detection_heart: int
        :param dst_addr: 探测目标地址（IP 或 URL 列表），默认 ``['1.1.1.2']``
        :type dst_addr: list or None
        :param src_addr: 探测源地址列表，默认自动填充
        :type src_addr: list or None 接口的地址
        :param method: 探测方式列表（``1``=ping/``2``=TCP/``3``=UDP ``[1]``
        :type method: list or None
        :param dst_port: 目的端口列表（ping=0/http=80/tftp=69），默认自动填充
        :type dst_port: list or None
        :param next_hop_ip: 下一跳 IP 列表，默认 ``['']``
        :type next_hop_ip: list or None
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(dst_addr, str):
            dst_addr = [dst_addr]
        elif dst_addr is None:
            dst_addr = ['1.1.1.2']
        if isinstance(src_addr, str):
            src_addr = [src_addr]
        elif src_addr is None:
            src_addr = ['1.1.1.1'] * len(dst_addr)
        if isinstance(method, int):
            method = [method]
        elif method is None:
            method = [1] * len(dst_addr)
        if isinstance(dst_port, int):
            dst_port = [dst_port]
        elif dst_port is None:
            temp_port = []
            for met in method:
                if met == 1:
                    temp_port.append(0)
                elif met == 2:
                    temp_port.append(80)
                elif met == 3:
                    temp_port.append(69)
            dst_port = temp_port * len(dst_addr)
        if isinstance(next_hop_ip, str):
            next_hop_ip = [next_hop_ip]
        elif next_hop_ip is None:
            next_hop_ip = [''] * len(dst_addr)
        link_detection_configs = []
        for dst, src, met, dp, nh in zip(dst_addr, src_addr, method, dst_port,
            next_hop_ip):
            link_detection_configs.append({'dst_addr': dst, 'src_addr': src,
                'method': met, 'dst_port': dp, 'nexthopip': nh})
        data = {'source': source, 'action': action, 'id': ld_id, 'name': name,
            'if_name': if_name, 'send_state': send_state, 'con_failured_times':
            con_failure_times, 'detection_heart': detection_heart,
            'linkdection_configs': link_detection_configs}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/linkdection/action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新链路探测失败: {e}')
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

    def create_or_update_link_detection_configs(self, action='create', source='',
        ld_id='', name='link_detect_name1', if_name='G1/1', send_state=True,
        con_failured_times=3, detection_heart=5, linkdection_configs=None,
        req_body=None):
        """创建或更新链路探测（直接传入 linkdection_configs 列表）。

        对应接口 ``POST /nf/network/linkdection/action/``。

        与 :meth:`create_or_update_link_detection` 不同，本函数直接接收完整的
        ``linkdection_configs`` 列表，每个元素为 dict，含以下字段：

        * ``src_addr`` — 探测源地址
        * ``dst_addr`` — 探测目标地址
        * ``dst_port`` — 目的端口（ping=0 / http=80 / tftp=69）
        * ``nexthopip`` — 下一跳 IP
        * ``method`` — 探测方式（1=ping / 2=TCP / 3=UDP）

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :param source: 来源，默认 ``''``
        :param ld_id: 探测 ID，编辑时使用，默认 ``''``
        :param name: 探测名称，默认 ``'link_detect_name1'``
        :param if_name: 出接口，默认 ``'G1/1'``
        :param send_state: 是否启用发送状态，默认 ``True``
        :param con_failured_times: 连续失败次数阈值，默认 ``3``
        :param detection_heart: 探测心跳间隔（秒），默认 ``5``
        :param linkdection_configs: 探测配置列表，每个元素为 dict，
            示例::

                [
                    {"src_addr": "113.115.32.2", "dst_addr": "223.5.5.5",
                     "dst_port": 0, "nexthopip": "113.115.32.1", "method": 1},
                    {"src_addr": "113.115.32.2", "dst_addr": "114.114.114.114",
                     "dst_port": 0, "nexthopip": "113.115.32.1", "method": 1},
                ]

        :param req_body: 自定义请求体 dict，传入后优先使用
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if linkdection_configs is None:
            linkdection_configs = [
                {'src_addr': '1.1.1.1', 'dst_addr': '1.1.1.2', 'dst_port': 0,
                 'nexthopip': '', 'method': 1}
            ]
        data = {'source': source, 'action': action, 'id': ld_id, 'name': name,
            'if_name': if_name, 'send_state': send_state, 'con_failured_times':
            con_failured_times, 'detection_heart': detection_heart,
            'linkdection_configs': linkdection_configs}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/linkdection/action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新链路探测失败: {e}')
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

    def get_link_detection(self, page=1, size=10, search='', source='', param=None
        ):
        """获取链路探测列表。

        对应 API 文档中的 ``get_link_detection``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字，默认 ``''``
        :type search: str
        :param source: 来源，默认 ``''``
        :type source: str
        :param param: 自定义查询参数，传入后优先使用
        :type param: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if param is not None:
            params = param
        else:
            params = {'page': page, 'size': size, 'search': search, 'source':
                source}
        url = f'{self.base_url}/nf/network/linkdection/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取链路探测列表失败: {e}')
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

    def get_link_detection_id(self, page=1, size=10, search='', source='',
        param=None):
        """根据名称查询链路探测 ID。

        对应 API 文档中的 ``get_link_detection``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字（名称匹配）
        :type search: str
        :param source: 来源，默认 ``''``
        :type source: str
        :param param: 自定义查询参数
        :type param: dict or None
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_link_detection(page=page, size=size, search=search,
                                       source=source, param=param)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def update_link_detection_status(self, link_id=None, enable=False,
        req_param=None):
        """更新链路探测启用状态。

        对应 API 文档中的 ``get_link_detection_status``。

        :param link_id: 链路探测 ID 或 ID 列表
        :type link_id: int or list or None
        :param enable: 是否启用，默认 ``False``
        :type enable: bool
        :param req_param: 自定义请求体，传入后优先使用
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_param is None:
            link_id = link_id if isinstance(link_id, list) else [link_id]
            data = {'id': link_id, 'enable': enable}
        else:
            data = req_param
        url = f'{self.base_url}/nf/network/linkdection_status/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新链路探测状态失败: {e}')
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

    def remove_link_detection(self, link_id=None, req_params=None):
        """删除链路探测。

        对应 API 文档中的 ``remove_link_detection``。

        :param link_id: 链路探测 ID，支持 ``int``/``str``/``list``
        :type link_id: int or str or list or None
        :param req_params: 自定义请求体，传入后优先使用
        :type req_params: dict or None
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_params is None:
            if isinstance(link_id, (int, str)):
                link_id = str(link_id)
            elif isinstance(link_id, list):
                link_id = ','.join(map(str, link_id))
            data = {'id': link_id}
        else:
            data = req_params
        url = f'{self.base_url}/nf/network/linkdection/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除链路探测失败: {e}')
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

    def get_link_status(self, url='nti.nsfocus.com'):
        """获取威胁情报云端通信状态（链路连通性）。

        对应 API 文档中的 ``get_link_connectivity``。

        :param url: 云端地址，默认 ``'nti.nsfocus.com'``
        :type url: str
        :return: 成功返回 ``{"status": 2000}``，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/threat/connectivity/info/'
        try:
            result = self.session.get(req_url, params={'url': url}, verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'获取威胁情报云端通信状态失败: {e}')
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
