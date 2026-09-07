"""GRE VPN — GRE 隧道的增删查改和启用/禁用。

对应 UI 页面「VPN → GRE VPN」。

对应 API 文档中的 ``get_gre``、``create_or_update_gre``、``remove_gre``、
``enable_gre``。
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


class GreFeature(NFRequests):
    """GRE 隧道操作集合 — GRE 隧道的增删查改和启用/禁用。"""

    def create_or_update_gre(self, action='create', name='gre1', status=True,
        gre_zone='TRUST', ipv4=None, src_swifinterface='T2/1', ha_circuit_id=
        None, ha_circuit_name=None, src='30.0.0.254', dst_type=0, dst=None,
        gre_key=None, check_sw=False, mtu=1350, mss_sw=1, tcp_mss=0,
        description=None, keepalive_sw=False, gre_keepalive_period=5,
        gre_keepalive_maxtime=3, send_state=False, detection_heart=5,
        confailured_times=3, is_ip4=True, is_edit=False, m_host_ip='19.3.0.2',
        m_sip='19.3.0.1', detection_method=1, host_port=0, next_hop_ip='',
        detection_id=None, req_body=None):
        """创建或更新 GRE 隧道。

        对应 API 文档中的 ``create_or_update_gre``。

        :param action: 操作类型，``"create"`` 创建，``"edit"`` 编辑
        :type action: str
        :param name: GRE 隧道名称
        :type name: str
        :param status: 隧道接口状态，``True`` 启用，``False`` 禁用
        :type status: bool
        :param gre_zone: 所属安全区
        :type gre_zone: str
        :param ipv4: IPv4 地址列表，默认 ``['193.0.0.1/24']``
        :type ipv4: list[str] or None
        :param src_swifinterface: 生效接口名称
        :type src_swifinterface: str
        :param ha_circuit_id: HA 线路 ID
        :type ha_circuit_id: int or None
        :param ha_circuit_name: HA 线路名称
        :type ha_circuit_name: str or None
        :param src: 隧道源 IP
        :type src: str
        :param dst_type: 隧道目的配置方式，``0`` 为 IP，``1`` 为域名
        :type dst_type: int
        :param dst: 隧道目的 IP 或域名
        :type dst: str or None
        :param gre_key: 隧道识别关键字
        :type gre_key: str or None
        :param check_sw: 校验和检查开关
        :type check_sw: bool
        :param mtu: 最大传输单元
        :type mtu: int
        :param mss_sw: TCP MSS 开关，``1`` 动态，``0`` 手动
        :type mss_sw: int
        :param tcp_mss: TCP MSS 值
        :type tcp_mss: int
        :param description: 描述
        :type description: str or None
        :param keepalive_sw: keepalive 开关
        :type keepalive_sw: bool
        :param gre_keepalive_period: keepalive 发送间隔
        :type gre_keepalive_period: int
        :param gre_keepalive_maxtime: keepalive 最大发送次数
        :type gre_keepalive_maxtime: int
        :param send_state: 链路探测开关
        :type send_state: bool
        :param detection_heart: 链路探测发送间隔
        :type detection_heart: int
        :param confailured_times: 链路探测最大失败次数
        :type confailured_times: int
        :param is_ip4: 是否 IPv4 探测
        :type is_ip4: bool
        :param is_edit: 探测项是否为编辑态
        :type is_edit: bool
        :param m_host_ip: 探测目的主机 IP
        :type m_host_ip: str
        :param m_sip: 探测报文源 IP
        :type m_sip: str
        :param detection_method: 探测方式，``1`` ICMP，``2`` TCP，``3`` UDP
        :type detection_method: int
        :param host_port: 探测端口
        :type host_port: int
        :param next_hop_ip: 下一跳 IP
        :type next_hop_ip: str
        :param detection_id: 探测 ID
        :type detection_id: int or None
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if ipv4 is None:
            ipv4 = ['193.0.0.1/24']
        elif isinstance(ipv4, str):
            ipv4 = [ipv4]
        if ha_circuit_name is not None and ha_circuit_id is not None:
            ha_circuit = {'ha_circuit_id': ha_circuit_id, 'ha_circuit_name':
                ha_circuit_name}
        else:
            ha_circuit = ''
        if dst is None:
            dst = '30.0.0.1' if dst_type == 0 else 'www.example.com'
        if send_state:
            probe_example = [{'isIP4': is_ip4, 'is_edit': is_edit, 'mHostip':
                m_host_ip, 'hostPort': host_port, 'mSip': m_sip,
                'detectionMethod': detection_method, 'nexthopip': next_hop_ip,
                'id': detection_id}]
        else:
            probe_example = []
        data = {'action': action, 'name': name, 'status': status, 'gre_zone':
            gre_zone, 'ipv4': ipv4, 'src_swifinterface': src_swifinterface,
            'ha_circuit': ha_circuit, 'src': src, 'dst_type': dst_type, 'dst':
            dst, 'gre_key': gre_key, 'check_sw': check_sw, 'mtu': mtu, 'mss_sw':
            mss_sw, 'tcp_mss': tcp_mss, 'description': description,
            'keepalive_sw': keepalive_sw, 'gre_keepalive_period':
            gre_keepalive_period, 'gre_keepalive_maxtime':
            gre_keepalive_maxtime, 'send_state': send_state, 'detection_heart':
            detection_heart, 'confailured_times': confailured_times,
            'probe_example': probe_example}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/gre/gre_action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新GRE接口失败: {e}')
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

    def get_gre(self, page=1, size=10, search='', req_params=None):
        """获取 GRE 隧道列表。

        对应 API 文档中的 ``get_gre``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param req_params: 自定义查询参数，传入后忽略其他参数
        :type req_params: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/gre/gre_info/'
        params = {'page': page, 'size': size, 'search': search}
        if req_params is not None:
            params = req_params
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取GRE接口列表失败: {e}')
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

    def remove_gre(self, name, req_body=None):
        """删除 GRE 隧道。

        对应 API 文档中的 ``remove_gre``。

        :param name: GRE 隧道名称，支持单个名称或名称列表
        :type name: str or list[str]
        :param req_body: 自定义请求体，传入后忽略 name
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(name, str):
            names = [name]
        elif isinstance(name, list):
            names = name
        else:
            names = [name]
        data = {'name': names}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/gre/gre_delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除GRE接口失败: {e}')
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

    def update_gre_status(self, name='gre1', status=True, req_body=None):
        """启用或禁用 GRE 隧道。

        对应 API 文档中的 ``enable_gre``。

        :param name: GRE 隧道名称
        :type name: str
        :param status: ``True`` 启用，``False`` 禁用
        :type status: bool
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        data = {'name': name, 'status': status}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/gre/gre_enable/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新GRE接口状态失败: {e}')
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
