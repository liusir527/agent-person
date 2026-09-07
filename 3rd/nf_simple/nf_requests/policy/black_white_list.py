"""黑白名单。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class BlackWhiteListFeature(NFRequests):
    """黑白名单操作集合。"""

    def create_or_update_white_list(self, action='create', ip_type='sourceIp',
        object_type='ip', ip='', zone=1, protocol='any', port='any', source=
        'user', ipv6=None, comment='', wl_id=None, status=None, extract_ip_ac=None
        ):
        """创建或更新白名单条目。

        对应 UI 页面「安全策略 → 全局黑白名单 → 白名单 → 新建/编辑」。

        :param action:       操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param ip_type:      IP 方向类型。``"sourceIp"`` = 源 IP（默认），``"destIp"`` = 目的 IP。
        :param object_type:  对象类型。``"ip"`` = IP 地址（默认），``"object"`` = 地域对象。
        :param ip:           IP 地址，字符串或列表。多个 IP 传列表，自动以逗号拼接，默认 ``""``。
        :param zone:         地域对象 ID，``object_type="object"`` 时使用，默认 ``1``。
        :param protocol:     协议过滤，默认 ``"any"``。
        :param port:         端口过滤，默认 ``"any"``。
        :param source:       来源标识，默认 ``"user"``（手动添加）。
        :param ipv6:         是否为 IPv6 条目。``True`` / ``False``，默认 ``None``（不指定）。
        :param comment:      备注，默认 ``""``。
        :param wl_id:        白名单条目 ID，``action="edit"`` 时必填。
        :param status:       条目状态，``action="edit"`` 时有效。``True`` = 启用（默认），``False`` = 禁用。
        :param extract_ip_ac: 提取 IP 地址动作，默认 ``None``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if isinstance(ip, list):
            ip = ','.join(ip)
        data = {'action': action, 'type': ip_type, 'objectType': object_type,
            'ip': ip if ip is not None else '', 'protocol': protocol, 'port':
            port, 'source': source, 'comment': comment, 'extractIpAc':
            extract_ip_ac}
        if object_type == 'object':
            data['zone'] = zone
        if action == 'edit':
            if wl_id is None:
                raise ValueError(
                    'wl_id is None, please give wl_id when action is edit !!!')
            data['id'] = wl_id
            data['status'] = True if status is None else status
        if ipv6 is not None:
            data['ipv6'] = str(ipv6).lower()
        url = f'{self.base_url}/nf/strategy/globalWb/wlist/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新白名单失败: {e}')
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

    def get_white_list(self, page=1, size=10, search='', ipv6=None, req_body=None):
        """获取白名单列表。

        对应 UI 页面「安全策略 → 全局黑白名单 → 白名单」。

        :param page:     页码，从 ``1`` 开始，默认 ``1``。
        :param size:     每页返回条数，默认 ``10``。
        :param search:   搜索关键字，默认 ``""``。
        :param ipv6:     IPv6 过滤。``True`` = 仅 IPv6，``False`` = 仅 IPv4，``None`` = 不过滤（默认）。
        :param req_body: 自定义查询参数 dict，传入后忽略以上所有参数，直接作为
                         GET query string 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"total": N, "list": [...]}, ...}``；
                 其中 ``list`` 每条记录包含 ``id``、``type``（IP 方向）、``objectType``、
                 ``ip``、``protocol``、``port``、``source``、``status``、``comment`` 等字段。
                 失败时返回 ``False``。
        """
        params = {'page': page, 'size': size, 'search': search}
        if ipv6 is not None:
            params['ipv6'] = str(ipv6).lower()
        if req_body:
            params = req_body
        url = f'{self.base_url}/nf/strategy/globalWb/wlist/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取白名单列表失败: {e}')
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

    def remove_white_list(self, wl_id=None, ipv6=None, req_body=None, id=None):
        """删除白名单条目。

        对应 UI 页面「安全策略 → 全局黑白名单 → 白名单 → 删除」操作。

        :param wl_id:    白名单条目 ID，整数、字符串或列表。与 ``id`` 参数二选一，
                         ``id`` 优先级更高。
        :param ipv6:     是否为 IPv6 条目。``True`` / ``False``，默认 ``None``（不指定）。
        :param req_body: 自定义请求体 dict，传入后忽略 ``wl_id``/``id`` 和 ``ipv6`` 参数，
                         直接作为 POST body 发送。用于特殊场景或调试。
        :param id:       白名单条目 ID（兼容参数），优先级高于 ``wl_id``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        wl_id = id if id is not None else wl_id
        if isinstance(wl_id, (list, tuple)):
            wl_id = [int(i) for i in wl_id]
        elif isinstance(wl_id, (int, str)):
            wl_id = [wl_id]
        data = {'id': wl_id}
        if ipv6 is not None:
            data['ipv6'] = str(ipv6).lower()
        if req_body:
            data = req_body
        url = f'{self.base_url}/nf/strategy/globalWb/wlist/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除白名单失败: {e}')
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

    def create_or_update_black_list(self, action='create', ip_type='sourceIp',
        object_type='ip', ip='', zone=1, protocol='any', port='any', source=
        'user', ipv6=None, is_time='f', time=0, end_time=0, bl_id=None, status=
        None, comment='', extract_ip_ac=None):
        """创建或更新黑名单条目。

        对应 UI 页面「安全策略 → 全局黑白名单 → 黑名单 → 新建/编辑」。
        在白名单基础上额外支持时间范围配置。

        :param action:       操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param ip_type:      IP 方向类型。``"sourceIp"`` = 源 IP（默认），``"destIp"`` = 目的 IP。
        :param object_type:  对象类型。``"ip"`` = IP 地址（默认），``"object"`` = 地域对象。
        :param ip:           IP 地址，字符串或列表。多个 IP 传列表，自动以逗号拼接，默认 ``""``。
        :param zone:         地域对象 ID，``object_type="object"`` 时使用，默认 ``1``。
        :param protocol:     协议过滤，默认 ``"any"``。
        :param port:         端口过滤，默认 ``"any"``。
        :param source:       来源标识，默认 ``"user"``（手动添加）。
        :param ipv6:         是否为 IPv6 条目。``True`` / ``False``，默认 ``None``（不指定）。
        :param is_time:      是否启用时间范围。``"f"`` = 否（默认），``"t"`` = 是。
        :param time:         封锁开始时间（Unix 时间戳），``is_time="t"`` 时有效，默认 ``0``。
        :param end_time:     封锁结束时间（Unix 时间戳），``is_time="t"`` 时有效，默认 ``0``。
        :param bl_id:        黑名单条目 ID，``action="edit"`` 时必填。
        :param status:       条目状态，``action="edit"`` 时有效。``True`` = 启用（默认），``False`` = 禁用。
        :param comment:      备注，默认 ``""``。
        :param extract_ip_ac: 提取 IP 地址动作，默认 ``None``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if isinstance(ip, list):
            ip = ','.join(ip)
        data = {'action': action, 'type': ip_type, 'objectType': object_type,
            'ip': ip if ip is not None else '', 'protocol': protocol, 'port':
            port, 'source': source, 'is_time': is_time, 'time': time, 'endtime':
            end_time, 'comment': comment, 'extractIpAc': extract_ip_ac}
        if object_type == 'object':
            data['zone'] = zone
        if action == 'edit':
            if bl_id is None:
                raise ValueError(
                    'bl_id is None, please give bl_id when action is edit !!!')
            data['id'] = bl_id
            edit_status = True if status is None else status
            data['status'] = edit_status
            if edit_status is False:
                data.pop('time')
                data.pop('is_time')
                data.pop('endtime')
        if ipv6 is not None:
            data['ipv6'] = str(ipv6).lower()
        url = f'{self.base_url}/nf/strategy/globalWb/blist/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新黑名单失败: {e}')
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

    def get_black_list(self, page=1, size=10, search='', ipv6=None, req_body=None):
        """获取黑名单列表。

        对应 UI 页面「安全策略 → 全局黑白名单 → 黑名单」。

        :param page:     页码，从 ``1`` 开始，默认 ``1``。
        :param size:     每页返回条数，默认 ``10``。
        :param search:   搜索关键字，默认 ``""``。
        :param ipv6:     IPv6 过滤。``True`` = 仅 IPv6，``False`` = 仅 IPv4，``None`` = 不过滤（默认）。
        :param req_body: 自定义查询参数 dict，传入后忽略以上所有参数，直接作为
                         GET query string 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"total": N, "list": [...]}, ...}``；
                 其中 ``list`` 每条记录包含 ``id``、``type``、``objectType``、``ip``、
                 ``protocol``、``port``、``source``、``status``、``comment``、
                 ``is_time``（是否启用时间）、``time``（开始时间戳）、``endtime``（结束时间戳）等字段。
                 失败时返回 ``False``。
        """
        params = {'page': page, 'size': size, 'search': search}
        if ipv6 is not None:
            params['ipv6'] = str(ipv6).lower()
        if req_body:
            params = req_body
        url = f'{self.base_url}/nf/strategy/globalWb/blist/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取黑名单列表失败: {e}')
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

    def remove_black_list(self, bl_id=None, ipv6=None, req_body=None, id=None):
        """删除黑名单条目。

        对应 UI 页面「安全策略 → 全局黑白名单 → 黑名单 → 删除」操作。

        :param bl_id:    黑名单条目 ID，整数、字符串或列表。与 ``id`` 参数二选一，
                         ``id`` 优先级更高。
        :param ipv6:     是否为 IPv6 条目。``True`` / ``False``，默认 ``None``（不指定）。
        :param req_body: 自定义请求体 dict，传入后忽略 ``bl_id``/``id`` 和 ``ipv6`` 参数，
                         直接作为 POST body 发送。用于特殊场景或调试。
        :param id:       黑名单条目 ID（兼容参数），优先级高于 ``bl_id``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        bl_id = id if id is not None else bl_id
        if isinstance(bl_id, (list, tuple)):
            bl_id = [int(i) for i in bl_id]
        elif isinstance(bl_id, (int, str)):
            bl_id = [bl_id]
        data = {'id': bl_id}
        if ipv6 is not None:
            data['ipv6'] = str(ipv6).lower()
        if req_body:
            data = req_body
        url = f'{self.base_url}/nf/strategy/globalWb/blist/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除黑名单失败: {e}')
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

    def clear_blist(self):
        #清空黑名单
        url = f'{self.base_url}/nf/strategy/globalWb/blist/clear/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空黑名单失败: {e}')
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
