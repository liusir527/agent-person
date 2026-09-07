"""SSL VPN 全局配置 — SSL VPN 全局配置的查询和更新。

对应 UI 页面「VPN → SSL VPN → 全局配置」。

对应 API 文档中的 ``get_sslvpn_setting``、``update_sslvpn_setting``。
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


class SslVpnGlobalFeature(NFRequests):
    """SSL VPN 全局配置操作集合 — SSL VPN 全局配置的查询和更新。"""

    def update_ssl_vpn_global_config(self, enable=True, auth='none', cipher=
        'AES-256-GCM', inactive='3600', is_compress=False, is_open_gateway=
        False, reneg_time=86400, ip='10.0.0.1/16', web_ssl_version=None,
        web_ssl_cipher=None, algorithm='rsa', cert='test', ca=
        'test', dns='0.0.0.0', access_log='no', dev='tun', enc='', sig='',
        log=0, duplicate_cn='no', duplicate_cn_action='new', user_count='3',
        req_body=None):
        """更新 SSL VPN 全局配置。

        对应 API 文档中的 ``update_sslvpn_setting``。

        :param enable: 是否启用 SSL VPN，默认 ``True``
        :type enable: bool
        :param auth: 认证类型，``"none"`` / ``"local"`` / ``"radius"``
        :type auth: str
        :param cipher: 加密算法，默认 ``"AES-256-GCM"``
        :type cipher: str
        :param inactive: 无操作超时时间（秒），默认 ``"3600"``
        :type inactive: str
        :param is_compress: 是否启用压缩
        :type is_compress: bool
        :param is_open_gateway: 是否启用网关模式
        :type is_open_gateway: bool
        :param reneg_time: 重协商时间（秒），默认 ``86400``
        :type reneg_time: int
        :param ip: VPN 客户端地址池，如 ``"10.0.0.1/16"``
        :type ip: str
        :param web_ssl_version: Web SSL 版本列表，默认 ``[None, 'TLSv1.1', 'TLSv1.2']``
        :type web_ssl_version: list[str] or None
        :param web_ssl_cipher: Web SSL 加密套件列表
        :type web_ssl_cipher: list[str] or None
        :param algorithm: 证书算法，默认 ``"rsa"``
        :type algorithm: str
        :param cert: SSL 证书名称
        :type cert: str
        :param ca: CA 证书名称
        :type ca: str
        :param dns: DNS 服务器地址
        :type dns: str
        :param access_log: 访问日志开关，``"yes"`` 或 ``"no"``
        :type access_log: str
        :param dev: 虚拟设备类型，默认 ``"tun"``
        :type dev: str
        :param enc: 加密算法
        :type enc: str
        :param sig: 签名算法
        :type sig: str
        :param log: 日志级别
        :type log: int
        :param duplicate_cn: 是否允许重复 CN，``"yes"`` 或 ``"no"``，默认 ``"no"``
        :type duplicate_cn: str
        :param duplicate_cn_action: 重复 CN 处理，``"old"`` 或 ``"new"``，默认 ``"new"``
        :type duplicate_cn_action: str
        :param user_count: 最大同时在线用户数，默认 ``"3"``
        :type user_count: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if web_ssl_version is None:
            web_ssl_version = [None, 'TLSv1.1', 'TLSv1.2']
        if web_ssl_cipher is None:
            web_ssl_cipher = ['ECDHE-RSA-AES256-GCM-SHA384',
                'ECDHE-ECDSA-AES256-GCM-SHA384',
                'ECDHE-ECDSA-CHACHA20-POLY1305',
                'ECDHE-RSA-CHACHA20-POLY1305',
                'ECDHE-ECDSA-AES128-GCM-SHA256',
                'ECDHE-RSA-AES128-GCM-SHA256']
        data = {'enable': enable, 'algorithm': algorithm, 'cert': cert, 'ca':
            ca, 'inactive': inactive, 'DNS': dns, 'isCompress': is_compress,
            'isOpenGateway': is_open_gateway, 'renegTime': reneg_time, 'auth':
            auth, 'ip': ip, 'cipher': cipher, 'webSslVersion': web_ssl_version,
            'accessLog': access_log, 'webSslCipher': web_ssl_cipher, 'dev': dev,
            'enc': enc, 'sig': sig, 'log': log, 'duplicateCn': duplicate_cn,
            'duplicateCnAction': duplicate_cn_action, 'userCount': user_count}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/vpn/sslvpn/setting/config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新SSL VPN全局配置失败: {e}')
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

    def get_ssl_vpn_global_config(self):
        """获取 SSL VPN 全局配置。

        对应 API 文档中的 ``get_sslvpn_setting``。

        返回数据 ``result`` 中包含 ``enable``、``port``、``cert``、``auth_type``。

        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/vpn/sslvpn/setting/info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取SSL VPN全局配置失败: {e}')
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
