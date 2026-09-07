"""会话与报文过滤 — 会话配置、会话表查询和丢包统计管理。

对应 UI 页面「系统 → 会话配置」「系统 → 会话表」「系统 → 丢包统计」。
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


class SessionPacketFilterFeature(NFRequests):
    """会话与报文过滤操作集合 — 会话配置、会话表、丢包统计和快速会话同步。"""

    def update_session_manager_config(self, udp_timeout=60, icmp_timeout=30,
        tcp_est_timeout=1800, tcp_fin_timeout=1, tcp_init_timeout=1,
        is_status_check_tcp=0, is_status_check_icmp=0, ha_sync_wait=0, req_body
        =None):
        """更新会话管理配置。

        对应 API 文档中的 ``set_session_config``。
        对应 UI 页面「系统 → 会话管理 → 会话配置」。

        :param udp_timeout: UDP 会话超时时间（秒），默认 ``60``。
        :type udp_timeout: int
        :param icmp_timeout: ICMP 会话超时时间（秒），默认 ``30``。
        :type icmp_timeout: int
        :param tcp_est_timeout: TCP 已建立连接超时时间（秒），默认 ``1800``。
        :type tcp_est_timeout: int
        :param tcp_fin_timeout: TCP FIN 超时时间（秒），默认 ``1``。
        :type tcp_fin_timeout: int
        :param tcp_init_timeout: TCP 初始化超时时间（秒），默认 ``1``。
        :type tcp_init_timeout: int
        :param is_status_check_tcp: 是否开启 TCP 状态检测。``0`` = 关闭（默认），``1`` = 开启。
        :type is_status_check_tcp: int
        :param is_status_check_icmp: 是否开启 ICMP 状态检测。``0`` = 关闭（默认），``1`` = 开启。
        :type is_status_check_icmp: int
        :param ha_sync_wait: HA 同步等待时间（秒），默认 ``0``。
        :type ha_sync_wait: int
        :param req_body: 自定义请求体 dict，传入后忽略以上所有参数，直接作为 POST body 发送。用于特殊场景或调试。
        :type req_body: dict or None
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；失败时返回 ``False``。
        :rtype: dict or bool
        """
        data = {'udp_timeout': udp_timeout, 'icmp_timeout': icmp_timeout,
            'tcp_est_timeout': tcp_est_timeout, 'tcp_fin_timeout':
            tcp_fin_timeout, 'tcp_init_timeout': tcp_init_timeout,
            'is_status_check_tcp': is_status_check_tcp, 'is_status_check_icmp':
            is_status_check_icmp, 'ha_sync_wait': ha_sync_wait}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/session/config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新会话管理配置失败: {e}')
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

    def get_session_manager_config(self):
        """获取会话管理配置。

        对应 API 文档中的 ``get_session_config``。
        对应 UI 页面「系统 → 会话管理 → 会话配置」，返回当前各协议超时时间及状态检测开关。

        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"udp_timeout": 60, "icmp_timeout": 30,
                 "tcp_est_timeout": 1800, "tcp_fin_timeout": 1, "tcp_init_timeout": 1,
                 "is_status_check_tcp": 0, "is_status_check_icmp": 0, "ha_sync_wait": 0}, ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/system/session/config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取会话管理配置失败: {e}')
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

    def update_fast_sync_session_config(self, fast_session_sync=True, sync_type
        ='fastsessionsync', req_body=None):
        """更新快速会话同步配置。

        对应 API 文档中的 ``enable_fast_session_sync``。
        对应 UI 页面「高可用 → 双机热备 → 快速会话同步」。
        所需账号：weboper（系统管理员）。

        :param fast_session_sync: 是否开启快速会话同步。``True`` = 启用（默认），``False`` = 禁用。
                                  发送时会转换为字符串 ``"true"`` / ``"false"``。
        :type fast_session_sync: bool
        :param sync_type: 同步类型，默认 ``"fastsessionsync"``，一般无需修改。
        :type sync_type: str
        :param req_body: 自定义请求体 dict，传入后忽略以上所有参数，直接作为 POST body 发送。用于特殊场景或调试。
        :type req_body: dict or None
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "双机热备-快速同步配置成功", ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        data = {'type': str(sync_type).lower(), 'fast_session_sync': str(
            fast_session_sync).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/fast_session_sync/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新快速会话同步配置失败: {e}')
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

    def update_filter_config(self, sif='', src_net='0.0.0.0/0', dst_net=
        '0.0.0.0/0', s_port=0, d_port=0, proto=0, req_body=None):
        """更新丢包统计过滤配置。

        对应 API 文档中的 ``update_packet_filter``。
        对应 UI 页面「系统 → 丢包统计 → 过滤配置」，设置丢包统计的抓包过滤条件。

        :param sif: 入接口名称过滤，例如 ``"G1/1"``。默认 ``""`` 表示不过滤接口。
        :type sif: str
        :param src_net: 源网段过滤，CIDR 格式，例如 ``"10.0.0.0/8"``。默认 ``"0.0.0.0/0"`` 表示不过滤源地址。
        :type src_net: str
        :param dst_net: 目的网段过滤，CIDR 格式，例如 ``"20.0.0.0/8"``。默认 ``"0.0.0.0/0"`` 表示不过滤目的地址。
        :type dst_net: str
        :param s_port: 源端口过滤，整数，``0`` 表示不过滤，默认 ``0``。
        :type s_port: int
        :param d_port: 目的端口过滤，整数，``0`` 表示不过滤，默认 ``0``。
        :type d_port: int
        :param proto: 协议过滤，整数 IP 协议号，``0`` 表示不过滤，默认 ``0``。
        :type proto: int
        :param req_body: 自定义请求体 dict，传入后忽略以上所有参数，直接作为 POST body 发送。用于特殊场景或调试。
        :type req_body: dict or None
        :return: 成功时返回完整响应 dict；失败时返回 ``False``。
        :rtype: dict or bool
        """
        data = {'sif': sif, 'srcnet': src_net, 'dstnet': dst_net, 'sport':
            s_port, 'dport': d_port, 'proto': proto}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/packet_loss_counter/update_filter/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新丢包统计过滤配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            if status_code != 2000 and status_code != 'success':
                logger.error(resp_data)
                return False
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def action_counter_status(self, enable, req_body=None):
        """启用或禁用丢包统计。

        对应 API 文档中的 ``action_packet_counter_status``。
        对应 UI 页面「系统 → 丢包统计」的启用/禁用开关。

        :param enable: 是否启用丢包统计。传入 ``True`` / ``False`` 或字符串 ``"true"`` / ``"false"``。
        :type enable: bool or str
        :param req_body: 自定义请求体 dict，传入后忽略 ``enable`` 参数，直接作为 POST body 发送。用于特殊场景或调试。
        :type req_body: dict or None
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        data = {'enable': enable}
        if req_body is not None:
            data = req_body
        req_url = (
            f'{self.base_url}/nf/system/packet_loss_counter/action_counter_status/'
            )
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'操作丢包统计状态失败: {e}')
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

    def clear_counter_result(self):
        """清除丢包统计结果。

        对应 API 文档中的 ``clear_packet_counter_result``。
        对应 UI 页面「系统 → 丢包统计 → 清除结果」操作，清空当前已统计的丢包数据。

        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        req_url = (
            f'{self.base_url}/nf/system/packet_loss_counter/clear_counter_result/')
        try:
            result = self.session.post(req_url, data=json.dumps({}), verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'清除丢包统计结果失败: {e}')
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

    def get_filter_info(self):
        """获取丢包统计过滤配置。

        对应 API 文档中的 ``get_packet_filter_info``。
        对应 UI 页面「系统 → 丢包统计 → 过滤配置」，返回当前生效的过滤条件。

        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"sif": "", "srcnet": "0.0.0.0/0",
                 "dstnet": "0.0.0.0/0", "sport": 0, "dport": 0, "proto": 0}, ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/system/packet_loss_counter/filter_info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取丢包统计配置失败: {e}')
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

    def get_counter_status(self):
        """获取丢包统计启用状态。

        对应 API 文档中的 ``get_packet_counter_status``。
        对应 UI 页面「系统 → 丢包统计」的当前开关状态。

        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"enable": true/false}, ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        req_url = (
            f'{self.base_url}/nf/system/packet_loss_counter/get_counter_status/')
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取丢包统计状态失败: {e}')
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

    def get_counter_result(self):
        """获取丢包统计结果。

        对应 API 文档中的 ``get_packet_counter_result``。
        对应 UI 页面「系统 → 丢包统计 → 统计结果」，返回当前统计周期内各接口/方向的丢包数据。

        :return: 成功时返回完整响应 dict，``result`` 列表每条记录包含接口名称、方向、丢包计数等字段；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/system/packet_loss_counter/counter_result/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取丢包统计结果失败: {e}')
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

    def get_session_table(self, src_addr=None, dst_addr=None, src_mac=None,
        dst_mac=None, s2d_rx_if=None, d2s_rx_if=None, server_id=None,
        comp_flags=None, src_port=None, dst_port=None, protocol=None, src_zone=
        None, dst_zone=None, action=0, appid=None, size=20, page=1, vsys_id='',
        req_body=None):
        """查询会话表。

        对应 API 文档中的 ``get_session_list``。
        对应 UI 页面「系统 → 会话表」的查询过滤条件。

        :param src_addr: 源 IP 地址过滤，例如 ``"10.3.1.2"``。对应 UI「源IP」。
        :type src_addr: str or None
        :param dst_addr: 目的 IP 地址过滤，例如 ``"20.2.1.2"``。对应 UI「目的IP」。
        :type dst_addr: str or None
        :param src_mac: 源 MAC 地址过滤，字符串，不过滤时传 ``None``。
        :type src_mac: str or None
        :param dst_mac: 目的 MAC 地址过滤，字符串，不过滤时传 ``None``。
        :type dst_mac: str or None
        :param s2d_rx_if: 源到目的方向入接口名称过滤，不过滤时传 ``None``。
        :type s2d_rx_if: str or None
        :param d2s_rx_if: 目的到源方向入接口名称过滤，不过滤时传 ``None``。
        :type d2s_rx_if: str or None
        :param server_id: 服务器 ID 过滤，不过滤时传 ``None``。
        :type server_id: int or None
        :param comp_flags: 会话标志位过滤，不过滤时传 ``None``。
        :type comp_flags: int or None
        :param src_port: 源端口过滤，整数，例如 ``8081``。对应 UI「源端口」。
        :type src_port: int or None
        :param dst_port: 目的端口过滤，整数，例如 ``80``。对应 UI「目的端口」。
        :type dst_port: int or None
        :param protocol: 协议过滤，整数 IP 协议号。对应 UI「协议」下拉框。
                         支持的协议及对应整数值：

                         - ``1``  = ICMP
                         - ``6``  = TCP
                         - ``17`` = UDP
                         - ``47`` = GRE
                         - ``50`` = ESP
                         - ``51`` = AH
                         - ``58`` = ICMPv6
                         - ``None`` 或不传 = 不过滤（全部协议，对应 UI 选项「IP」）
        :type protocol: int or None
        :param src_zone: 源安全域名称过滤，不过滤时传 ``None``。
        :type src_zone: str or None
        :param dst_zone: 目的安全域名称过滤，不过滤时传 ``None``。
        :type dst_zone: str or None
        :param action: 动作过滤。对应 UI「动作」单选框。
                       ``0`` = 全部（默认），``1`` = 放行，``2`` = 阻断。
        :type action: int
        :param appid: 应用 ID 过滤，不过滤时传 ``None``。
        :type appid: int or None
        :param size: 每页返回条数，默认 ``20``。
        :type size: int
        :param page: 页码，从 ``1`` 开始，默认 ``1``。
        :type page: int
        :param vsys_id: 虚拟系统 ID，默认 ``""`` 表示全局系统。
        :type vsys_id: str
        :param req_body: 自定义请求体 dict，传入后忽略以上所有过滤参数，直接作为 POST body 发送。用于特殊场景或调试。
        :type req_body: dict or None
        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": [...], ...}``；
                 其中 ``result`` 列表每条记录包含以下关键字段：

                 - ``src_addr``     原始源 IP
                 - ``dst_addr``     原始目的 IP
                 - ``src_port``     原始源端口
                 - ``dst_port``     原始目的端口
                 - ``protocol``     协议号整数，例如 ``1`` (ICMP)、``6`` (TCP)
                 - ``snat_ip``      SNAT 后源 IP（源 NAT 转换地址）
                 - ``snat_port``    SNAT 后源端口
                 - ``dnat_ip``      DNAT 后目的 IP（目的 NAT 转换地址）
                 - ``dnat_port``    DNAT 后目的端口
                 - ``s2d_rx_if``    源到目的方向入接口
                 - ``s2d_tx_if``    源到目的方向出接口
                 - ``is_snat``      是否命中 SNAT（bool）
                 - ``is_dnat``      是否命中 DNAT（bool）
                 - ``user``         关联用户
                 - ``module``       命中策略模块名称

                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        data = {'size': size, 'page': page, 'vsysId': vsys_id, 'src_addr':
            src_addr, 'dst_addr': dst_addr, 'src_mac': src_mac, 'dst_mac':
            dst_mac, 's2d_rx_if': s2d_rx_if, 'd2s_rx_if': d2s_rx_if,
            'server_id': server_id, 'comp_flags': comp_flags, 'protocol':
            protocol, 'src_port': src_port, 'dst_port': dst_port, 'src_zone':
            src_zone, 'dst_zone': dst_zone, 'action': action, 'appid': appid}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/session/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取会话表失败: {e}')
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

    def remove_session_table(self, src_addr, dst_addr, src_port, dst_port,
        protocol, req_body=None):
        """删除指定会话表项。

        对应 API 文档中的 ``delete_session``。
        对应 UI 页面「系统 → 会话表 → 删除」操作。支持单条或批量删除：
        传入单个值时自动转为列表，传入列表时按索引对应批量删除。

        :param src_addr: 源 IP 地址，字符串或字符串列表，例如 ``"10.3.1.2"`` 或 ``["10.3.1.2", "10.3.1.3"]``。
        :type src_addr: str or list
        :param dst_addr: 目的 IP 地址，字符串或字符串列表，例如 ``"20.2.1.2"``。
        :type dst_addr: str or list
        :param src_port: 源端口，整数或整数列表，例如 ``36465``。
        :type src_port: int or list
        :param dst_port: 目的端口，整数或整数列表，例如 ``80``。
        :type dst_port: int or list
        :param protocol: 协议号，整数或整数列表。常用值：``1`` = ICMP，``6`` = TCP，``17`` = UDP。
        :type protocol: int or list
        :param req_body: 自定义请求体（list of dict），传入后忽略以上所有参数，直接作为 POST body 发送。用于特殊场景或调试。
        :type req_body: list or None
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        if isinstance(src_addr, str):
            src_addr = [src_addr]
        if isinstance(dst_addr, str):
            dst_addr = [dst_addr]
        if isinstance(src_port, int):
            src_port = [src_port]
        if isinstance(dst_port, int):
            dst_port = [dst_port]
        if isinstance(protocol, int):
            protocol = [protocol]
        data = [{'src_addr': a, 'dst_addr': b, 'src_port': c, 'dst_port': d,
            'protocol': e} for a, b, c, d, e in zip(src_addr, dst_addr,
            src_port, dst_port, protocol)]
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/session/SessioninfoDelete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除会话表项失败: {e}')
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

    def clear_session_table(self):
        """清空全部会话表。

        对应 UI 页面「系统 → 会话表 → 清空」操作，发送空列表 ``[]`` 作为请求体，
        清除设备上所有当前活跃会话。

        .. warning::
            此操作会中断所有正在进行的网络连接，生产环境请谨慎使用。

        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/system/session/SessioninfoDelete/'
        try:
            result = self.session.post(req_url, data=json.dumps([]), verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'清空会话表失败: {e}')
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
