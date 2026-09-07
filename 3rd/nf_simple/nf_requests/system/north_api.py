"""北向接口 — 北向接口用户管理、Token 生成和全局配置。

对应 UI 页面「系统 → 北向接口」。

对应 API 文档中的 ``get_north_api_user``、``create_north_api_user``、
``remove_north_api_user``、``generate_token``、``get_north_api_config``、
``renew_north_api_config``。

.. note::
   ``generate_token`` 方法从原 ``basic.token`` 模块迁移至此（2026-07-04）。
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


class NorthApiFeature(NFRequests):
    """北向接口操作集合 — 用户管理、Token 生成和全局配置。"""

    def create_or_update_north_api_user(self, action='create', expire='', name=
        'test1', user_ip='0.0.0.0/0', interval='120', status=True,
        north_api_user_id=None, token='', req_body=None):
        """创建或更新北向接口用户。

        对应 API 文档中的 ``create_north_api_user``。

        :param action: 操作类型，``"create"`` 创建，``"edit"`` 编辑
        :type action: str
        :param expire: 过期时间
        :type expire: str
        :param name: 用户名
        :type name: str
        :param user_ip: 允许访问的 IP 地址，默认 ``"0.0.0.0/0"``
        :type user_ip: str
        :param interval: 令牌有效期（秒），默认 ``"120"``
        :type interval: str
        :param status: 是否启用
        :type status: bool
        :param north_api_user_id: 编辑时传入的用户 ID
        :type north_api_user_id: int or None
        :param token: 访问令牌
        :type token: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'action': action, 'expire': expire, 'name': name, 'ip': user_ip,
            'interval': interval, 'status': status, 'token': token}
        if action == 'edit':
            data['id'] = north_api_user_id
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/restapi/user/config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新北向接口用户失败: {e}')
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

    def remove_north_api_user(self, user_id, req_body=None):
        """删除北向接口用户。

        对应 API 文档中的 ``remove_north_api_user``。

        :param user_id: 用户 ID
        :type user_id: int
        :param req_body: 自定义请求体，传入后忽略 user_id
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'id': user_id} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/restapi/user/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除北向接口用户失败: {e}')
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

    def get_north_api_user(self, size=10, page=1, search=''):
        """获取北向接口用户列表。

        对应 API 文档中的 ``get_north_api_user``。

        返回数据 ``result.list`` 中每条记录包含 ``id``、``name``、``token``、
        ``interval``、``create_time``。

        :param size: 每页数量，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索关键词
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/restapi/user/info'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取北向接口用户列表失败: {e}')
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

    def update_north_api_config(self, enabled=True, port=8081, protocol='https'):
        """更新北向接口配置。

        对应 API 文档中的 ``renew_north_api_config``。

        :param enabled: 是否启用北向接口
        :type enabled: bool
        :param port: 监听端口，默认 ``8081``
        :type port: int
        :param protocol: 协议类型，``"https"`` 或 ``"http"``
        :type protocol: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'enabled': enabled, 'port': port, 'protocol': protocol}
        req_url = f'{self.base_url}/nf/restapi/config/renew/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新北向接口配置失败: {e}')
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

    def get_north_api_config(self):
        """获取北向接口配置。

        对应 API 文档中的 ``get_north_api_config``。

        返回数据 ``result`` 中包含 ``enable``（是否启用）和 ``port``（监听端口）。

        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/restapi/config/info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取北向接口配置失败: {e}')
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

    def generate_token(self, name='test1', interval='120', req_body=None):
        """生成北向接口用户 Token。

        对应 API 文档中的 ``generate_token``。

        .. note::
           此方法从原 ``basic.token`` 模块迁移至此（2026-07-04）。

        :param name: 用户名
        :type name: str
        :param interval: 令牌有效期（秒），默认 ``"120"``
        :type interval: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict（含 ``token`` 和 ``expire_time``），失败返回 False
        :rtype: dict or bool
        """
        data = {'name': name, 'interval': interval}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/restapi/user/generate_token/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'生成北向接口用户token失败: {e}')
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
