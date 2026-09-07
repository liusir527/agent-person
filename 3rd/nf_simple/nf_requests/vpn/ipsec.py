"""IPSec VPN。

对应 UI 页面「VPN → IPSec」。
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


class IpsecFeature(NFRequests):
    """IPSec VPN 操作集合。"""

    def create_or_update_ipsec(self, action='create', name='dut1_ipsec', status
        =True, local_interface='G1/5', ha_circuit_id=None, ha_circuit_name=None,
        local_addr='192.168.1.1', is_local_nat_enable=False, local_nat_type=
        'ip', local_nat_addrs=None, remote_status='ip', remote_addr=None,
        is_remote_nat_enable=False, remote_nat_type='ip', remote_nat_addrs=None,
        id_type='ip', local_id='', remote_id='', encap='no', version=1,
        auth='psk', id_secret='qwert12345', local_cert=1, remote_cert=1,
        local_gm=1, remote_gm=1, aggressive='no', encryption_proposals='aes256',
        modify_sm4='no', auth_proposals='sha256', dh='DH14', re_auth_time=28800,
        auto_aggressive='yes', dpd_action='yes', dpd_delay=30, dpd_timeout=120,
        subnet_name=None, local_ts=None, remote_ts=None, service=None,
        tunnel_id=None, ipsec_encryption_proposals='aes256',
        ipsec_auth_proposals='sha256', protocol='ESP', rekey_time=3600, pfs=
        'no', ipsec_dh='', mode='tunnel', req_body=None):
        """创建或修改 IPsec 隧道配置。

        对应 UI 页面「VPN → IPSec」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 修改，默认 ``"create"``。
        :param name: 隧道名称，默认 ``"dut1_ipsec"``。
        :param status: 隧道启用状态，``True`` = 启用，``False`` = 禁用，默认 ``True``。
        :param local_interface: 本地接口，默认 ``"G1/5"``。
        :param ha_circuit_id: HA 线路 ID，与 ``ha_circuit_name`` 配合使用，默认 ``None``。
        :param ha_circuit_name: HA 线路名称，与 ``ha_circuit_id`` 配合使用，默认 ``None``。
        :param local_addr: 本地 IP 地址，默认 ``"192.168.1.1"``。
        :param is_local_nat_enable: 是否启用本地 NAT 穿越，``True``/``False``，
            会自动转换为小写字符串 ``"true"``/``"false"``，默认 ``False``。
        :param local_nat_type: 本地 NAT 类型：

            * ``"ip"`` — IP 地址模式
            * ``"subnet"`` — 网段模式

            默认 ``"ip"``。
        :param local_nat_addrs: 本地 NAT 地址，``None`` 时根据 ``local_nat_type`` 自动填充。
        :param remote_status: 远端地址模式：

            * ``"ip"`` — IP 地址
            * ``"subnet"`` — 网段
            * ``"any"`` — 任意

            默认 ``"ip"``。
        :param remote_addr: 远端地址，``None`` 时自动填充。
        :param is_remote_nat_enable: 是否启用远端 NAT 穿越，``True``/``False``，
            会自动转换为小写字符串，默认 ``False``。
        :param remote_nat_type: 远端 NAT 类型，``"ip"``/``"subnet"``，默认 ``"ip"``。
        :param remote_nat_addrs: 远端 NAT 地址。
        :param id_type: 身份类型，``"ip"`` = IP 地址，``"name"`` = 名称，默认 ``"ip"``。
        :param local_id: 本地身份标识，``None`` 时自动使用 ``local_addr``，默认 ``""``。
        :param remote_id: 远端身份标识，``None`` 时自动使用 ``remote_addr``，默认 ``""``。
        :param encap: 封装模式，``"no"``/``"gre"``，默认 ``"no"``。
        :param version: IKE 版本，``1`` = IKEv1，``2`` = IKEv2，默认 1。
        :param auth: 认证方式：

            * ``"psk"`` — 预共享密钥
            * ``"pubkey"`` — 公钥证书（RSA）
            * ``"gm"`` — 国密证书

            默认 ``"psk"``。不同认证方式对应不同的子字段：
            ``"psk"`` 需要 ``id_secret``；``"pubkey"`` 需要 ``local_cert``/``remote_cert``；
            ``"gm"`` 需要额外 ``local_gm``/``remote_gm``。
        :param id_secret: 预共享密钥，默认 ``"qwert12345"``。仅 ``auth='psk'`` 时生效。
        :param local_cert: 本地证书 ID，默认 1。``auth='pubkey'`` 或 ``'gm'`` 时生效。
        :param remote_cert: 远端证书 ID，默认 1。``auth='pubkey'`` 或 ``'gm'`` 时生效。
        :param local_gm: 本地国密证书 ID，默认 1。仅 ``auth='gm'`` 时生效。
        :param remote_gm: 远端国密证书 ID，默认 1。仅 ``auth='gm'`` 时生效。
        :param aggressive: 是否野蛮模式，``"yes"``/``"no"``，默认 ``"no"``。
            仅 IKEv1 生效。
        :param encryption_proposals: IKE 加密算法，默认 ``"aes256"``。
        :param modify_sm4: 是否允许修改 SM4，``"yes"``/``"no"``，默认 ``"no"``。
        :param auth_proposals: IKE 认证算法，默认 ``"sha256"``。
        :param dh: IKE DH 组，如 ``"DH14"``，默认 ``"DH14"``。
        :param re_auth_time: IKE 重认证时间（秒），默认 28800。
        :param auto_aggressive: 是否主动协商模式，``"yes"`` = 主动（默认），``"no"`` = 被动。
        :param dpd_action: DPD 动作，``"yes"``/``"no"``，默认 ``"yes"``。
        :param dpd_delay: DPD 延迟（秒），默认 30。
        :param dpd_timeout: DPD 超时（秒），默认 120。
        :param subnet_name: 子网名称，str 或 list，默认 ``['subnet1']``。
            每个子网条目构成一条 sub_config 记录。
        :param local_ts: 本地流量选择器，str 或 list，默认 ``['10.0.1.0/24']``。
            与 ``subnet_name`` 长度对齐。
        :param remote_ts: 远端流量选择器，str 或 list，默认 ``['10.0.2.0/24']``。
            与 ``subnet_name`` 长度对齐。
        :param service: 服务，str 或 list，默认 ``['any']``（自动对齐 ``subnet_name`` 长度）。
        :param tunnel_id: 隧道 ID，str 或 list，默认 ``['']``（自动对齐 ``subnet_name`` 长度）。
        :param ipsec_encryption_proposals: IPSec 加密算法，默认 ``"aes256"``。
        :param ipsec_auth_proposals: IPSec 认证算法，默认 ``"sha256"``。
        :param protocol: IPSec 协议，``"ESP"``/``"AH"``，默认 ``"ESP"``。
        :param rekey_time: IPSec 重协商时间（秒），默认 3600。
        :param pfs: 是否开启 PFS，``"yes"``/``"no"``，默认 ``"no"``。
        :param ipsec_dh: IPSec DH 组，默认 ``""``。
        :param mode: IPSec 模式，``"tunnel"`` = 隧道模式，``"transport"`` = 传输模式，
            默认 ``"tunnel"``。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。

        .. note::
            ``subnet_name``、``local_ts``、``remote_ts``、``service``、``tunnel_id``
            通过 ``zip`` 对齐后生成 ``sub_config`` 列表，每个元素对应一条子隧道配置。
            ``service`` 和 ``tunnel_id`` 若为单值会自动扩展到与 ``subnet_name`` 等长。
        """
        if ha_circuit_name is not None and ha_circuit_id is not None:
            ha_circuit = {'ha_circuit_id': ha_circuit_id, 'ha_circuit_name':
                ha_circuit_name}
        else:
            ha_circuit = ''
        is_local_nat_enable = str(is_local_nat_enable).lower()
        if local_nat_addrs is None:
            local_nat_addrs = '' if local_nat_type == 'ip' else '0.0.0.0'
        if remote_addr is None:
            remote_addr = '192.168.1.2' if remote_status == 'ip' else '0.0.0.0'
        is_remote_nat_enable = str(is_remote_nat_enable).lower()
        if remote_nat_addrs is None:
            remote_nat_addrs = '' if remote_nat_type == 'ip' else '0.0.0.0'
        if local_id is None:
            local_id = local_addr
        if remote_id is None:
            remote_id = remote_addr
        data = {'action': action, 'name': name, 'status': status,
            'local_interface': local_interface, 'haCircuit': ha_circuit,
            'local_addr': local_addr, 'isLocalNatEnable': is_local_nat_enable,
            'localNatType': local_nat_type, 'localNatAddrs': local_nat_addrs,
            'remote_status': remote_status, 'remote_addr': remote_addr,
            'isRemoteNatEnable': is_remote_nat_enable, 'remoteNatType':
            remote_nat_type, 'remoteNatAddrs': remote_nat_addrs, 'idType':
            id_type, 'local_id': local_id, 'remote_id': remote_id, 'encap':
            encap, 'version': version, 'auth': auth, 'aggressive': aggressive}
        if auth == 'psk':
            data.update({'id_secret': id_secret})
        elif auth == 'pubkey':
            data.update({'local_cert': local_cert, 'remote_cert': remote_cert})
        elif auth == 'gm':
            data.update({'local_cert': local_cert, 'remote_cert': remote_cert,
                'local_gm': local_gm, 'remote_gm': remote_gm})
        data.update({'ike_params': [{'encryptionProposals':
            encryption_proposals, 'authProposals': auth_proposals, 'dh': dh}],
            'modify_sm4': modify_sm4, 'reauth_time': re_auth_time,
            'auto_aggressive': auto_aggressive, 'dpd_action': dpd_action,
            'dpd_delay': dpd_delay, 'dpd_timeout': dpd_timeout})
        ip_sec_params = {'rekey_time': rekey_time, 'ipsec_params': [{
            'encryptionProposals': ipsec_encryption_proposals, 'authProposals':
            ipsec_auth_proposals}], 'pfs': pfs, 'dh': ipsec_dh, 'protocol':
            protocol, 'mode': mode}
        if isinstance(subnet_name, str):
            subnet_name = [subnet_name]
        elif subnet_name is None:
            subnet_name = ['subnet1']
        if isinstance(local_ts, str):
            local_ts = [local_ts]
        elif local_ts is None:
            local_ts = ['10.0.1.0/24']
        if isinstance(remote_ts, str):
            remote_ts = [remote_ts]
        elif remote_ts is None:
            remote_ts = ['10.0.2.0/24']
        if isinstance(service, str):
            service = [service] * len(subnet_name)
        elif service is None:
            service = ['any'] * len(subnet_name)
        if tunnel_id is None:
            tunnel_id = [''] * len(subnet_name)
        elif isinstance(tunnel_id, str):
            tunnel_id = [tunnel_id] * len(subnet_name)
        data['sub_config'] = []
        for s_name, l_ts, r_ts, s_service, s_id in zip(subnet_name, local_ts,
            remote_ts, service, tunnel_id):
            item = dict(ip_sec_params)
            item.update({'tunnel_id': s_id, 'name': s_name, 'local_ts': l_ts,
                'remote_ts': r_ts, 'service': s_service})
            data['sub_config'].append(item)
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/vpn/ipsec/ipsec_action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或修改IPSec隧道失败: {e}')
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

    def get_ipsec(self, page=1, size=10, search=''):
        """获取 IPsec 隧道列表。

        对应 UI 页面「VPN → IPSec」。

        :param page: 页码，默认 1。
        :param size: 每页条数，默认 10。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/vpn/ipsec/ipsec_info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取IPSec隧道列表失败: {e}')
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

    def remove_ipsec(self, name, req_body=None):
        """删除 IPsec 隧道。

        对应 UI 页面「VPN → IPSec」。

        :param name: IPSec 隧道名称，支持 str（单个隧道）或 list（批量删除）。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(name, str):
            name = [name]
        data = {'name': name}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/vpn/ipsec/ipsec_delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除IPSec隧道失败: {e}')
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

    def enable_ipsec_status(self, name, enable=True, req_body=None):
        """启用或禁用 IPsec 隧道。

        对应 UI 页面「VPN → IPSec」。

        :param name: IPSec 隧道名称。
        :param enable: 是否启用，``True`` = 启用，``False`` = 禁用，默认 ``True``。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'ipsecName': name, 'enable': enable}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/vpn/ipsec/change_status/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新IPSec隧道状态失败: {e}')
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

    def get_ipsec_tunnel_monitor(self, page=1, size=10, search=''):
        """获取 IPsec 隧道监控信息。

        对应 UI 页面「VPN → IPSec → 隧道监控」。

        :param page: 页码，默认 1。
        :param size: 每页条数，默认 10。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/vpn/ipsec/monitor/traffic_info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取IPSec隧道监控信息失败: {e}')
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