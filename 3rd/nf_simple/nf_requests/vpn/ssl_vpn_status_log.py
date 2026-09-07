"""SSL VPN 状态与日志 — SSL VPN 在线用户状态查询、客户端登出和运行日志查询。

对应 UI 页面「VPN → SSL VPN → 运行状态」。

对应 API 文档中的 ``get_sslvpn_status``、``logout_sslvpn_user``、
``get_sslvpn_log``。
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


class SslVpnStatusLogFeature(NFRequests):
    """SSL VPN 状态与日志操作集合 — 在线状态、客户端登出和运行日志查询。"""

    def get_ssl_vpn_status(self, page=1, size=10, search=''):
        """获取 SSL VPN 在线用户状态列表。

        对应 API 文档中的 ``get_sslvpn_status``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/vpn/sslvpn/status/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取SSL VPN在线用户失败: {e}')
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

    def logout_ssl_vpn_client(self, name='test', ip='192.168.2.2', domain=
        'global', req_body=None):
        """登出 SSL VPN 客户端（强制下线）。

        对应 API 文档中的 ``logout_sslvpn_user``。

        :param name: 用户名
        :type name: str
        :param ip: 客户端 IP 地址
        :type ip: str
        :param domain: 认证域，默认 ``"global"``
        :type domain: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'name': name, 'ip': ip, 'domain': domain}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/status/logout/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'登出SSL VPN客户端失败: {e}')
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

    def get_ssl_vpn_log(self, page=1, size=10, s_time=None, d_time=None, level=
        '', username='', content='', ip='', req_param=None, req_body=None):
        """查询 SSL VPN 运行日志。

        对应 API 文档中的 ``get_sslvpn_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 起始时间
        :type s_time: str or None
        :param d_time: 结束时间
        :type d_time: str or None
        :param level: 日志级别
        :type level: str
        :param username: 用户名
        :type username: str
        :param content: 日志内容搜索
        :type content: str
        :param ip: 客户端 IP
        :type ip: str
        :param req_param: 自定义查询参数，传入后忽略其他参数
        :type req_param: dict or None
        :param req_body: 自定义请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        params = {'page': page, 'size': size, 'sTime': s_time, 'dTime': d_time,
            'level': level, 'username': username, 'content': content, 'ip': ip}
        if req_param is not None:
            params = req_param
        if req_body is not None:
            params = req_body
        req_url = f'{self.base_url}/nf/log/run/ssl_vpn/'
        try:
            result = self.session.post(req_url, json=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'查询SSL VPN运行日志失败: {e}')
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
