"""畸形包防护 — DDoS 畸形包防护策略的查询和更新。

对应 UI 页面「安全防护 → DDoS 防护 → 畸形包防护」。

对应 API 文档中的 ``get_ddos_deformity_info``、``update_ddos_deformity``。
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


class DeformityFeature(NFRequests):
    """畸形包防护操作集合 — 畸形包防护策略的查询和更新。"""

    def update_deformity_config(self, ip_frag_flood_id=3,
        ip_frag_flood_d_switch=0, ip_frag_flood_threshold=60000,
        ip_frag_flood_period=30, teardrop_id=26, teardrop_d_switch=0,
        teardrop_period=10, ip_frag_pack_id=25, ip_frag_pack_d_switch=0,
        ip_frag_pack_auto_protect=0, smurf_attack_id=27, smurf_attack_d_switch=
        0, smurf_attack_auto_protect=0, ping_of_death_id=28,
        ping_of_death_d_switch=0, ping_of_death_auto_protect=0, frag_gle_id=29,
        frag_gle_d_switch=0, frag_gle_auto_protect=0, win_nuke_id=30,
        win_nuke_d_switch=0, win_nuke_auto_protect=0, land_id=31, land_d_switch
        =0, land_auto_protect=0, tcp_mark_lawful_id=32,
        tcp_mark_lawful_d_switch=0, tcp_mark_lawful_auto_protect=0,
        abnormal_arp_id=40, abnormal_arp_d_switch=0, abnormal_arp_auto_protect=
        0, ip_cheat_id=24, ip_cheat_d_switch=0, ip_cheat_auto_protect=0):
        """更新畸形报文防护策略（共 11 种攻击类型）。

        对应 API 文档中的 ``update_ddos_deformity``。

        :param ip_frag_flood_id: IP 分片洪泛类型 ID，默认 ``3``
        :type ip_frag_flood_id: int
        :param ip_frag_flood_d_switch: IP 分片洪泛开关，``1`` 启用 / ``0`` 禁用
        :type ip_frag_flood_d_switch: int
        :param ip_frag_flood_threshold: IP 分片洪泛阈值，默认 ``60000``
        :type ip_frag_flood_threshold: int
        :param ip_frag_flood_period: IP 分片洪泛检测周期（秒）
        :type ip_frag_flood_period: int
        :param teardrop_id: Teardrop 攻击类型 ID，默认 ``26``
        :type teardrop_id: int
        :param teardrop_d_switch: Teardrop 攻击开关，``1`` 启用 / ``0`` 禁用
        :type teardrop_d_switch: int
        :param teardrop_period: Teardrop 检测周期（秒）
        :type teardrop_period: int
        :param ip_frag_pack_id: IP 分片包类型 ID，默认 ``25``
        :type ip_frag_pack_id: int
        :param ip_frag_pack_d_switch: IP 分片包开关，``1`` 启用 / ``0`` 禁用
        :type ip_frag_pack_d_switch: int
        :param ip_frag_pack_auto_protect: IP 分片包自动保护，``1`` 开启 / ``0`` 关闭
        :type ip_frag_pack_auto_protect: int
        :param smurf_attack_id: Smurf 攻击类型 ID，默认 ``27``
        :type smurf_attack_id: int
        :param smurf_attack_d_switch: Smurf 攻击开关，``1`` 启用 / ``0`` 禁用
        :type smurf_attack_d_switch: int
        :param smurf_attack_auto_protect: Smurf 攻击自动保护，``1`` 开启 / ``0`` 关闭
        :type smurf_attack_auto_protect: int
        :param ping_of_death_id: Ping of Death 类型 ID，默认 ``28``
        :type ping_of_death_id: int
        :param ping_of_death_d_switch: Ping of Death 开关，``1`` 启用 / ``0`` 禁用
        :type ping_of_death_d_switch: int
        :param ping_of_death_auto_protect: Ping of Death 自动保护，``1`` 开启 / ``0`` 关闭
        :type ping_of_death_auto_protect: int
        :param frag_gle_id: 碎片包类型 ID，默认 ``29``
        :type frag_gle_id: int
        :param frag_gle_d_switch: 碎片包开关，``1`` 启用 / ``0`` 禁用
        :type frag_gle_d_switch: int
        :param frag_gle_auto_protect: 碎片包自动保护，``1`` 开启 / ``0`` 关闭
        :type frag_gle_auto_protect: int
        :param win_nuke_id: WinNuke 攻击类型 ID，默认 ``30``
        :type win_nuke_id: int
        :param win_nuke_d_switch: WinNuke 攻击开关，``1`` 启用 / ``0`` 禁用
        :type win_nuke_d_switch: int
        :param win_nuke_auto_protect: WinNuke 自动保护，``1`` 开启 / ``0`` 关闭
        :type win_nuke_auto_protect: int
        :param land_id: Land 攻击类型 ID，默认 ``31``
        :type land_id: int
        :param land_d_switch: Land 攻击开关，``1`` 启用 / ``0`` 禁用
        :type land_d_switch: int
        :param land_auto_protect: Land 自动保护，``1`` 开启 / ``0`` 关闭
        :type land_auto_protect: int
        :param tcp_mark_lawful_id: TCP 标记合法性类型 ID，默认 ``32``
        :type tcp_mark_lawful_id: int
        :param tcp_mark_lawful_d_switch: TCP 标记合法性开关，``1`` 启用 / ``0`` 禁用
        :type tcp_mark_lawful_d_switch: int
        :param tcp_mark_lawful_auto_protect: TCP 标记自动保护，``1`` 开启 / ``0`` 关闭
        :type tcp_mark_lawful_auto_protect: int
        :param abnormal_arp_id: 异常 ARP 类型 ID，默认 ``40``
        :type abnormal_arp_id: int
        :param abnormal_arp_d_switch: 异常 ARP 开关，``1`` 启用 / ``0`` 禁用
        :type abnormal_arp_d_switch: int
        :param abnormal_arp_auto_protect: 异常 ARP 自动保护，``1`` 开启 / ``0`` 关闭
        :type abnormal_arp_auto_protect: int
        :param ip_cheat_id: IP 欺骗类型 ID，默认 ``24``
        :type ip_cheat_id: int
        :param ip_cheat_d_switch: IP 欺骗开关，``1`` 启用 / ``0`` 禁用
        :type ip_cheat_d_switch: int
        :param ip_cheat_auto_protect: IP 欺骗自动保护，``1`` 开启 / ``0`` 关闭
        :type ip_cheat_auto_protect: int
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        count = 11
        deformity_config = [{'typeId': int(ip_frag_flood_id), 'dSwitch': int(
            ip_frag_flood_d_switch), 'threshold': int(ip_frag_flood_threshold),
            'period': int(ip_frag_flood_period)}, {'typeId': int(teardrop_id),
            'dSwitch': int(teardrop_d_switch), 'period': int(teardrop_period)},
            {'typeId': int(ip_frag_pack_id), 'dSwitch': int(
            ip_frag_pack_d_switch), 'autoProtect': int(
            ip_frag_pack_auto_protect)}, {'typeId': int(smurf_attack_id),
            'dSwitch': int(smurf_attack_d_switch), 'autoProtect': int(
            smurf_attack_auto_protect)}, {'typeId': int(ping_of_death_id),
            'dSwitch': int(ping_of_death_d_switch), 'autoProtect': int(
            ping_of_death_auto_protect)}, {'typeId': int(frag_gle_id),
            'dSwitch': int(frag_gle_d_switch), 'autoProtect': int(
            frag_gle_auto_protect)}, {'typeId': int(win_nuke_id), 'dSwitch':
            int(win_nuke_d_switch), 'autoProtect': int(win_nuke_auto_protect)},
            {'typeId': int(land_id), 'dSwitch': int(land_d_switch),
            'autoProtect': int(land_auto_protect)}, {'typeId': int(
            tcp_mark_lawful_id), 'dSwitch': int(tcp_mark_lawful_d_switch),
            'autoProtect': int(tcp_mark_lawful_auto_protect)}, {'typeId': int(
            abnormal_arp_id), 'dSwitch': int(abnormal_arp_d_switch),
            'autoProtect': int(abnormal_arp_auto_protect)}, {'typeId': int(
            ip_cheat_id), 'dSwitch': int(ip_cheat_d_switch), 'autoProtect': int
            (ip_cheat_auto_protect)}]
        data = {'count': count, 'deformityConfig': deformity_config}
        url = (
            f'{self.base_url}/nf/strategy/ddos/deformity/deformity_configuration/')
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'修改畸形报文防护策略失败: {e}')
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

    def get_deformity_config(self):
        """获取畸形报文防护策略信息。

        对应 API 文档中的 ``get_ddos_deformity_info``。

        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/strategy/ddos/deformity/deformity_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取畸形报文防护策略失败: {e}')
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
