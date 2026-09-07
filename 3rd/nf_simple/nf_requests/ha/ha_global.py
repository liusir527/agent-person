"""HA 全局配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class HaGlobalFeature(NFRequests):
    """HA 全局配置操作集合。"""

    def get_ha_global_config(self):
        """获取 HA 全局配置。

        对应 UI 页面「高可用性 → 双机热备」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "common": {
                        "ha_enable": "false",
                        "models": "1",
                        "preempt": "false",
                        "preempt_delay": "0",
                        "use_vmac": "false",
                        ...
                    },
                    "h_link": {
                        "interface": "",
                        "src_ip": "",
                        "peer_ip": "",
                        "hb_interval": "5000",
                        "hb_lost_times": "3"
                    },
                    "c_link": { ... }
                }

            ``common.models`` 说明：``"1"`` = 主备模式，``"2"`` = 负载均衡模式。
        """
        url = f'{self.base_url}/nf/ha/ha_config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取HA全局配置失败: {e}')
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
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def update_ha_global_config(self, models='1', h_interface='G1/1', h_src_ip=
        '11.1.1.1', h_peer_ip='11.1.1.2', reuse_heart_link=True, c_interface='',
        c_src_ip='', c_peer_ip='', h_hb_interval='1000', h_hb_lost_times='3',
        preempt=True, preempt_delay='0', use_vmac=False, label='send',
        use_hb_intf=True, config_sync=False, firewall_sync=False, auto_sync=
        False, config_sync_pass='',security_enhancement="false",req_body=None):
        """更新 HA 全局配置。

        对应 UI 页面「高可用性 → 双机热备 → 编辑」。

        .. note:: 布尔型参数会自动转换为小写字符串 ``"true"``/``"false"``。

        :param models: HA 模式，``"1"`` = 主备模式，``"2"`` = 负载均衡模式，默认
            ``"1"``
        :param h_interface: 心跳接口，如 ``"G1/1"``
        :param h_src_ip: 心跳本端 IP，如 ``"11.1.1.1"``
        :param h_peer_ip: 心跳对端 IP，如 ``"11.1.1.2"``
        :param reuse_heart_link: 是否复用心跳接口同步配置，默认 ``True``。

            - 为 ``True`` 时，配置同步接口参数自动置空。
            - 为 ``False`` 时，需提供 ``c_interface``、``c_src_ip``、
              ``c_peer_ip``。
        :param c_interface: 配置同步接口（不复用时必填）
        :param c_src_ip: 配置同步本端 IP
        :param c_peer_ip: 配置同步对端 IP
        :param h_hb_interval: 心跳间隔（毫秒），默认 ``"1000"``
        :param h_hb_lost_times: 失去心跳次数阈值，默认 ``"3"``
        :param preempt: 抢占模式，默认 ``True``
        :param preempt_delay: 抢占延迟（秒），默认 ``"0"``
        :param use_vmac: 是否使用虚拟 MAC，默认 ``False``
        :param label: 设备同步标签，``"send"`` = 发送端，``"accept"`` = 接收端，
            默认 ``"send"``
        :param use_hb_intf: 是否使用心跳口传送 VRRP 报文，默认 ``True``
        :param config_sync: 配置同步开关，默认 ``False``
        :param firewall_sync: 会话同步开关，默认 ``False``
        :param auto_sync: 自动同步开关，默认 ``False``
        :param config_sync_pass: HA 同步配置密码
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        reuse_heart_link_value = str(reuse_heart_link).lower()
        if reuse_heart_link_value == 'true':
            c_interface_value = '' if c_interface is None else c_interface
            c_src_ip_value = '' if c_src_ip is None else c_src_ip
            c_peer_ip_value = '' if c_peer_ip is None else c_peer_ip
        else:
            c_interface_value = 'G1/1' if c_interface is None else c_interface
            c_src_ip_value = '11.1.1.1' if c_src_ip is None else c_src_ip
            c_peer_ip_value = '11.1.1.2' if c_peer_ip is None else c_peer_ip
        data = {'models': models, 'use_hb_intf': str(use_hb_intf).lower(),
            'use_vmac': str(use_vmac).lower(), 'config_sync': str(config_sync).
            lower(), 'config_sync_pass': config_sync_pass, 'firewall_sync': str
            (firewall_sync).lower(), 'h_interface': h_interface, 'h_src_ip':
            h_src_ip, 'h_peer_ip': h_peer_ip, 'h_hb_interval': str(
            h_hb_interval), 'h_hb_lost_times': str(h_hb_lost_times),
            'Reuse_heatlink': reuse_heart_link_value, 'auto_sync': str(
            auto_sync).lower(), 'c_interface': c_interface_value, 'c_src_ip':
            c_src_ip_value, 'c_peer_ip': c_peer_ip_value, 'label': label,
            'preempt': str(preempt).lower(), 'preempt_delay': str(preempt_delay),"security_enhancement":security_enhancement}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/ha_config/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新HA全局配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                logger.error(data)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def enable_or_disable_ha(self, ha_enable=True, req_body=None):
        """启用或禁用 HA。

        对应 UI 页面「高可用性 → 双机热备 → 启用/禁用」。

        .. note:: 布尔型参数会自动转换为小写字符串 ``"true"``/``"false"``。

        :param ha_enable: ``True`` = 启用 HA，``False`` = 禁用 HA，默认 ``True``
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'ha_enable': str(ha_enable).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/ha_control/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'启用或禁用HA失败: {e}')
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
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
