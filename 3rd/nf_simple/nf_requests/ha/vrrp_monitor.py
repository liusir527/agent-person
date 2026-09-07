"""VRRP 监控 — VRRP 实例的增删查改及状态切换。

对应 UI 页面「高可用 → 双机热备」。
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


class VrrpMonitorFeature(NFRequests):
    """VRRP 监控线路操作集合 — VRRP 实例的增删查改及状态管理。"""

    def create_or_update_vrrp_monitor_wire(self, action='create', identity=
        'MASTER', name='test', vire_id='', advert_int='1', link='', ins_model=
        None, ins_interface=None, ins_vrid=None, ins_ip=None, ins_ipv6=None,
        track_interface=None, track_action=None, track_id=None, track_weight=
        None, joint='', req_body=None):
        """创建或更新 VRRP 监控。

        对应 API 文档中的 ``create_or_update_vrrp``。

        .. note:: 实例参数（``ins_interface``、``ins_model``、``ins_vrid`` 等）
            为数组型参数，支持传入单个值或列表。当传入单个值时自动扩展为与
            ``ins_interface`` 长度匹配的列表。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑，默认 ``"create"``
        :type action: str
        :param identity: HA 身份，``"MASTER"`` = 主，``"BACKUP"`` = 备，默认 ``"MASTER"``
        :type identity: str
        :param name: 监控线路名称，默认 ``"test"``
        :type name: str
        :param vire_id: 线路 ID，创建时默认空字符串，编辑时必填
        :type vire_id: str
        :param advert_int: 心跳间隔（秒），默认 ``"1"``
        :type advert_int: str
        :param link: 链路探测，支持 ``str``、``int`` 或 ``list``（自动逗号拼接），默认 ``""``
        :type link: str or int or list
        :param ins_model: 实例模式列表，``"layer3"`` = 三层模式，默认 ``["layer3"]``
        :type ins_model: str or list or None
        :param ins_interface: 实例接口列表，默认 ``["G1/1"]``
        :type ins_interface: str or list or None
        :param ins_vrid: 实例 VRID 列表。三层模式下自动分配从 ``"1"`` 递增的 VRID，非三层模式填空字符串
        :type ins_vrid: str or list or None
        :param ins_ip: 实例 IP 列表（CIDR 格式），三层模式默认 ``"1.1.1.1/24"``，非三层模式填空字符串
        :type ins_ip: str or list or None
        :param ins_ipv6: 实例 IPv6 列表，默认全部为空字符串
        :type ins_ipv6: str or list or None
        :param track_interface: 监控接口列表，默认 ``[]``
        :type track_interface: str or list or None
        :param track_action: 监控动作列表（``"new"`` / ``"delete"``），默认 ``"new"``
        :type track_action: str or list or None
        :param track_id: 监控 ID 列表，默认从 ``0`` 递增
        :type track_id: int or str or list or None
        :param track_weight: 监控权重列表，默认 ``"1"``
        :type track_weight: str or int or list or None
        :param joint: 联动接口，支持 ``str`` 或 ``list``（自动逗号拼接），默认 ``""``
        :type joint: str or list
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        if ins_interface is None:
            ins_interface = ['G1/1']
        elif isinstance(ins_interface, str):
            ins_interface = [ins_interface]
        ins_len = len(ins_interface)
        if isinstance(link, list):
            link = ','.join(map(str, link))
        elif isinstance(link, (str, int)):
            link = str(link)
        else:
            link = ''
        if ins_model is None:
            ins_model = ['layer3'] * ins_len
        elif isinstance(ins_model, str):
            ins_model = [ins_model] * ins_len
        if ins_vrid is None:
            temp_ins_vrid = []
            current_vrid = 0
            for i in range(ins_len):
                if ins_model[i] == 'layer3':
                    current_vrid += 1
                    temp_ins_vrid.append(str(current_vrid))
                else:
                    temp_ins_vrid.append('')
            ins_vrid = temp_ins_vrid
        elif isinstance(ins_vrid, (str, int)):
            ins_vrid = [str(ins_vrid)] * ins_len
        elif isinstance(ins_vrid, list):
            ins_vrid = list(map(str, ins_vrid))
        if ins_ip is None:
            temp_ins_ip = []
            for i in range(ins_len):
                if ins_model[i] == 'layer3':
                    temp_ins_ip.append('1.1.1.1/24')
                else:
                    temp_ins_ip.append('')
            ins_ip = temp_ins_ip
        elif isinstance(ins_ip, str):
            ins_ip = [ins_ip] * ins_len
        if ins_ipv6 is None:
            ins_ipv6 = [''] * ins_len
        elif isinstance(ins_ipv6, str):
            ins_ipv6 = [ins_ipv6] * ins_len
        if track_interface is None:
            track_interface = []
        elif isinstance(track_interface, str):
            track_interface = [track_interface]
        if track_weight is None:
            track_weight = ['1'] * len(track_interface)
        elif isinstance(track_weight, (str, int)):
            track_weight = [str(track_weight)]
        elif isinstance(track_weight, list):
            track_weight = list(map(str, track_weight))
        if track_id is None:
            track_id = [index for index in range(len(track_interface))]
        elif isinstance(track_id, (int, str)):
            track_id = [int(track_id)]
        elif isinstance(track_id, list):
            track_id = list(map(int, track_id))
        if track_action is None:
            track_action = ['new'] * len(track_interface)
        elif isinstance(track_action, str):
            track_action = [track_action]
        if joint is None:
            joint = ''
        elif isinstance(joint, list):
            joint = ','.join(joint)
        data = {'action': action, 'identity': identity, 'name': name, 'id': '' if
            vire_id is None and action == 'create' else '1' if vire_id is None else
            str(vire_id), 'advert_int': str(advert_int), 'link': link,
            'instance': [{'interface': ins_interface[index], 'vrid': ins_vrid[
            index], 'model': ins_model[index], 'ip': ins_ip[index], 'ipv6':
            ins_ipv6[index]} for index in range(len(ins_interface))], 'track':
            [{'action': track_action[index], 'id': track_id[index], 'interface':
            track_interface[index], 'weight': track_weight[index]} for index in
            range(len(track_interface))], 'joint': joint}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/vrrp/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新VRRP监控线路失败: {e}')
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

    def get_vrrp_monitor_wire(self, page=1, size=10):
        """获取 VRRP 监控列表。

        对应 API 文档中的 ``get_vrrp``。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :return: 成功返回完整响应 dict，含 ``result.list`` 和 ``result.total``；失败返回 ``False``
        :rtype: dict or bool
        """
        url = f'{self.base_url}/nf/ha/vrrp/info/'
        params = {'page': page, 'size': size}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取VRRP监控线路失败: {e}')
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

    def remove_vrrp_monitor_wire(self, index, req_body=None):
        """删除 VRRP 监控。

        对应 API 文档中的 ``remove_vrrp``。

        :param index: VRRP 配置 ID
        :type index: int or str
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'id': str(index)}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/vrrp/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除VRRP监控线路失败: {e}')
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

    def update_vrrp_monitor_wire_status(self, vrrp_index, enable=False,
        req_body=None):
        """切换 VRRP 状态。

        对应 API 文档中的 ``change_vrrp_status``。

        .. note:: 布尔型参数会自动转换为小写字符串 ``"true"``/``"false"``。

        :param vrrp_index: VRRP 配置 ID
        :type vrrp_index: int or str
        :param enable: ``True`` = 启用，``False`` = 禁用，默认 ``False``
        :type enable: bool
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'id': str(vrrp_index), 'status': str(enable).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/change_vrrp_status/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新VRRP监控线路状态失败: {e}')
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
