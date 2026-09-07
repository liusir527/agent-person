"""威胁防御 — 威胁防御配置更新和威胁情报在线查询。

对应 UI 页面「安全防护 → 威胁防御」。

对应 API 文档中的 ``get_threat_defense``、``update_threat_defense``、
``get_threat_inquiry``。
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


class ThreatDefenseFeature(NFRequests):
    """威胁防御操作集合 — 威胁防御配置和威胁情报在线查询。"""

    def update_threat_defense_config(self, is_enable=0, ransomware_block=0,
        ransomware_log=0, ransomware_enable=0, extortion_block=0,
        extortion_log=0, extortion_enable=0, mining_block=0, mining_log=0,
        mining_enable=0, apt_block=0, apt_log=0, apt_enable=0,
        malice_ip_block=0, malice_ip_log=0, malice_ip_enable=0,
        malice_url_block=0, malice_url_log=0, malice_url_enable=0,
        malice_domain_block=0, malice_domain_log=0, malice_domain_enable=0,
        req_body=None):
        """更新威胁防御配置。

        对应 API 文档中的 ``update_threat_defense``。

        支持 7 种威胁类型的防御配置，每种类型包含阻断（block）、日志（log）和
        启用（enable）三个开关：

        - 勒索软件（type 5）：``ransomware_block`` / ``ransomware_log`` / ``ransomware_enable``
        - 勒索（type 7）：``extortion_block`` / ``extortion_log`` / ``extortion_enable``
        - 挖矿（type 6）：``mining_block`` / ``mining_log`` / ``mining_enable``
        - APT（type 4）：``apt_block`` / ``apt_log`` / ``apt_enable``
        - 恶意 IP（type 0）：``malice_ip_block`` / ``malice_ip_log`` / ``malice_ip_enable``
        - 恶意 URL（type 1）：``malice_url_block`` / ``malice_url_log`` / ``malice_url_enable``
        - 恶意域名（type 2）：``malice_domain_block`` / ``malice_domain_log`` / ``malice_domain_enable``

        :param is_enable: 全局威胁防御开关，``1`` 启用，``0`` 禁用
        :type is_enable: int
        :param ransomware_block: 勒索软件阻断开关
        :type ransomware_block: int
        :param ransomware_log: 勒索软件日志开关
        :type ransomware_log: int
        :param ransomware_enable: 勒索软件启用开关
        :type ransomware_enable: int
        :param extortion_block: 勒索阻断开关
        :type extortion_block: int
        :param extortion_log: 勒索日志开关
        :type extortion_log: int
        :param extortion_enable: 勒索启用开关
        :type extortion_enable: int
        :param mining_block: 挖矿阻断开关
        :type mining_block: int
        :param mining_log: 挖矿日志开关
        :type mining_log: int
        :param mining_enable: 挖矿启用开关
        :type mining_enable: int
        :param apt_block: APT 阻断开关
        :type apt_block: int
        :param apt_log: APT 日志开关
        :type apt_log: int
        :param apt_enable: APT 启用开关
        :type apt_enable: int
        :param malice_ip_block: 恶意 IP 阻断开关
        :type malice_ip_block: int
        :param malice_ip_log: 恶意 IP 日志开关
        :type malice_ip_log: int
        :param malice_ip_enable: 恶意 IP 启用开关
        :type malice_ip_enable: int
        :param malice_url_block: 恶意 URL 阻断开关
        :type malice_url_block: int
        :param malice_url_log: 恶意 URL 日志开关
        :type malice_url_log: int
        :param malice_url_enable: 恶意 URL 启用开关
        :type malice_url_enable: int
        :param malice_domain_block: 恶意域名阻断开关
        :type malice_domain_block: int
        :param malice_domain_log: 恶意域名日志开关
        :type malice_domain_log: int
        :param malice_domain_enable: 恶意域名启用开关
        :type malice_domain_enable: int
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'isEnable': int(is_enable), 'malConfig': [{'type': 5, 'isBlock':
            int(ransomware_block), 'isLog': int(ransomware_log),'isEnabled': int(ransomware_enable)},{'type': 7, 'isBlock':
            int(extortion_block), 'isLog': int(extortion_log), 'isEnabled': int
            (extortion_enable)}, {'type': 6, 'isBlock': int(mining_block),
            'isLog': int(mining_log), 'isEnabled': int(mining_enable)}, {'type':
            4, 'isBlock': int(apt_block), 'isLog': int(apt_log), 'isEnabled':
            int(apt_enable)}, {'type': 0, 'isBlock': int(malice_ip_block),
            'isLog': int(malice_ip_log), 'isEnabled': int(malice_ip_enable)}, {
            'type': 1, 'isBlock': int(malice_url_block), 'isLog': int(
            malice_url_log), 'isEnabled': int(malice_url_enable)}, {'type': 2,
            'isBlock': int(malice_domain_block), 'isLog': int(malice_domain_log
            ), 'isEnabled': int(malice_domain_enable)}]}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/threat/defense/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新威胁情报防御配置失败: {e}')
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

    def get_online_intelligence(self, query_type='ip', data='', addr=
        'nti.nsfocus.com'):
        """威胁情报在线查询。

        对应 API 文档中的 ``get_threat_inquiry``。

        :param query_type: 查询类型，``"ip"`` / ``"url"`` / ``"domain"``
        :type query_type: str
        :param data: 查询内容（IP 地址、URL 或域名）
        :type data: str
        :param addr: 威胁情报远程服务器地址，默认 ``"nti.nsfocus.com"``
        :type addr: str
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/threat/inquiry/info/'
        params = {'type': query_type, 'data': data, 'addr': addr}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'威胁情报在线查询失败: {e}')
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
