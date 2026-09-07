"""SD-WAN — SD-WAN 本地配置的查询和更新。

对应 UI 页面「系统 → SD-WAN」。

对应 API 文档中的 ``get_sdwan_local_config``、``update_sdwan_local_config``。
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


class SdWanFeature(NFRequests):
    """SD-WAN 配置操作集合 — SD-WAN 本地配置的查询和更新。"""

    def sd_wan_configuration(self, status=True, local_edit=True, req_body=None):
        """配置 SD-WAN 开关状态。

        对应 API 文档中的 ``update_sdwan_local_config``（简化版，仅控制启用状态）。

        :param status: 是否启用 SD-WAN
        :type status: bool
        :param local_edit: 是否允许本地编辑
        :type local_edit: bool
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'status': status, 'local_edit': local_edit
            } if req_body is None else req_body
        req_url = f'{self.base_url}/nf/sdwan/local_config/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'配置SD-WAN开关失败: {e}')
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

    def update_sd_wan_local_config(self, ip='', ip_addr='', ip_interface='',
        link_heartbeat_interval=10, link_if_type='', link_if_vlan_id=None,
        req_body=None):
        """更新 SD-WAN 本地配置（完整参数）。

        对应 API 文档中的 ``update_sdwan_local_config``。

        :param ip: 控制器 IP 地址
        :type ip: str
        :param ip_addr: IP 地址
        :type ip_addr: str
        :param ip_interface: IP 接口
        :type ip_interface: str
        :param link_heartbeat_interval: 链路心跳间隔（秒），默认 ``10``
        :type link_heartbeat_interval: int
        :param link_if_type: 链路接口类型
        :type link_if_type: str
        :param link_if_vlan_id: 链路接口 VLAN ID
        :type link_if_vlan_id: int or None
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'ip': ip, 'ip_addr': ip_addr, 'ip_interface': ip_interface,
            'link_heartbeat_interval': link_heartbeat_interval, 'link_if_type':
            link_if_type, 'link_if_vlan_id': link_if_vlan_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/sdwan/local_config/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新SD-WAN本地配置失败: {e}')
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

    def get_sd_wan_local_config(self):
        """获取 SD-WAN 本地配置。

        对应 API 文档中的 ``get_sdwan_local_config``。

        返回数据 ``result`` 中包含 ``enable``（是否启用）、``controller_ip``
        （控制器 IP）、``controller_port``（控制器端口）。

        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/sdwan/local_config/info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取SD-WAN本地配置失败: {e}')
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
