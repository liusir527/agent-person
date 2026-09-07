"""DDoS 全局配置。

对应 UI 页面「安全防护 → DDoS 防护 → 全局配置」。
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


class DdosGlobalFeature(NFRequests):
    """DDoS 全局配置操作集合。"""

    def update_ddos_global_config(self, reset_time=30, log_merge_time=30,
        dns_custom_port=None, http_custom_port=None, https_custom_port=None,
        sip_custom_port=None, check_after_nat=0):
        """更新 DDoS 全局配置。

        对应 UI 页面「安全防护 → DDoS 防护 → 全局配置」。

        :param reset_time: 复位时间（秒），默认 30。
        :param log_merge_time: 日志归并时间（秒），默认 30。
        :param dns_custom_port: DNS 自定义端口，支持 int/str/list，None 表示不上报。
        :param http_custom_port: HTTP 自定义端口，支持 int/str/list，None 表示不上报。
        :param https_custom_port: HTTPS 自定义端口，支持 int/str/list，None 表示不上报。
        :param sip_custom_port: SIP 自定义端口，支持 int/str/list，None 表示不上报。
        :param check_after_nat: NAT 后保护开关，``0`` = 关闭，``1`` = 开启，默认 0。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        reset_time = int(reset_time)
        logMergeTime = int(log_merge_time)
        if isinstance(dns_custom_port, str):
            dnsCustomPort = [int(dns_custom_port)]
        elif isinstance(dns_custom_port, int):
            dnsCustomPort = [dns_custom_port]
        elif isinstance(dns_custom_port, list):
            dnsCustomPort = list(map(int, dns_custom_port))
        else:
            dnsCustomPort = None
        if isinstance(http_custom_port, str):
            httpCustomPort = [int(http_custom_port)]
        elif isinstance(http_custom_port, int):
            httpCustomPort = [http_custom_port]
        elif isinstance(http_custom_port, list):
            httpCustomPort = list(map(int, http_custom_port))
        else:
            httpCustomPort = None
        if isinstance(https_custom_port, str):
            httpsCustomPort = [int(https_custom_port)]
        elif isinstance(https_custom_port, int):
            httpsCustomPort = [https_custom_port]
        elif isinstance(https_custom_port, list):
            httpsCustomPort = list(map(int, https_custom_port))
        else:
            httpsCustomPort = None
        if isinstance(sip_custom_port, str):
            sipCustomPort = [int(sip_custom_port)]
        elif isinstance(sip_custom_port, int):
            sipCustomPort = [sip_custom_port]
        elif isinstance(sip_custom_port, list):
            sipCustomPort = list(map(int, sip_custom_port))
        else:
            sipCustomPort = None
        checkAfterNat = int(check_after_nat)
        data = {'reset_time': reset_time, 'logMergeTime': logMergeTime,
            'dnsCustomPort': dnsCustomPort, 'httpCustomPort': httpCustomPort,
            'httpsCustomPort': httpsCustomPort, 'sipCustomPort': sipCustomPort,
            'checkAfterNat': checkAfterNat}
        url = f'{self.base_url}/nf/strategy/ddos/global/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新DDoS全局配置失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return True
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_ddos_global_config(self):
        """获取 DDoS 全局配置。

        对应 UI 页面「安全防护 → DDoS 防护 → 全局配置」。

        :return: 成功返回完整响应 dict，格式为 ``{"status": 2000, "result": {...}, "message": "..."}``；
            失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ddos/global/info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取DDoS全局配置失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
