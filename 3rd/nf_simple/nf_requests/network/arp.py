"""ARP 表配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class ArpFeature(NFRequests):
    """ARP 表配置操作集合。

    涵盖 ARP 表项的增删改查、绑定、同步，以及 ARP 全局配置。
    """

    def create_arp(self, ip='1.1.1.1', mac='11:11:11:11:11:11', enable=True,
        note='', interface='G1/1', arp_type='静态'):
        """创建 ARP 表项。

        对应 UI 页面「网络管理 → ARP 表 → 新建」。

        ``arp_type`` 取值：
            - ``"静态"`` = 静态 ARP 表项（默认）
            - ``"动态"`` = 动态 ARP 表项

        :param ip:        IP 地址，默认 ``"1.1.1.1"``。
        :param mac:       MAC 地址，默认 ``"11:11:11:11:11:11"``。
        :param enable:    是否启用，默认 ``True``。
        :param note:      备注，默认 ``""``。
        :param interface: 接口名称，默认 ``"G1/1"``。
        :param arp_type:  ARP 类型，默认 ``"静态"``。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'ip': ip, 'mac': mac, 'enabled': enable, 'note': note, 'id': -1,
            'action': 'create', 'type': arp_type, 'interface': interface}
        url = f'{self.base_url}/nf/network/arp/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建ARP失败: {e}')
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

    def update_arp(self, arp_id, ip='1.1.1.1', mac='11:11:11:11:11:11', enable=
        True, note='', interface='G1/1', arp_type='静态'):
        """更新 ARP 表项。

        对应 UI 页面「网络管理 → ARP 表 → 编辑」。

        ``arp_type`` 取值：
            - ``"静态"`` = 静态 ARP 表项（默认）
            - ``"动态"`` = 动态 ARP 表项

        :param arp_id:    ARP 表项 ID。
        :param ip:        IP 地址，默认 ``"1.1.1.1"``。
        :param mac:       MAC 地址，默认 ``"11:11:11:11:11:11"``。
        :param enable:    是否启用，默认 ``True``。
        :param note:      备注，默认 ``""``。
        :param interface: 接口名称，默认 ``"G1/1"``。
        :param arp_type:  ARP 类型，默认 ``"静态"``。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'ip': ip, 'mac': mac, 'enabled': enable, 'note': note, 'id':
            arp_id, 'action': 'edit', 'type': arp_type, 'interface': interface}
        url = f'{self.base_url}/nf/network/arp/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新ARP失败: {e}')
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

    def get_arp_table(self, page=1, size=10, search=''):
        """获取 ARP 表。

        对应 UI 页面「网络管理 → ARP 表」。

        调用前会自动执行 ``sync_arp_table`` 同步 ARP 数据。

        返回列表中每条记录包含：``id``、``ip``、``mac``、``interface``、``type``（``"静态"`` / ``"动态"``）、``enabled``、``note``。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        self.sync_arp_table()
        url = f'{self.base_url}/nf/network/arp/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取ARP表失败: {e}')
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

    def get_arp_table_id(self, page=1, size=10, search=''):
        """根据名称查询 ARP 表项 ID。

        对应 UI 页面「网络管理 → ARP 表」。

        调用 ``get_arp_table`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: ARP 表项名称关键字，用于匹配。
        :return: 匹配到时返回表项 ID (int)；失败返回 ``False``。
        """
        resp = self.get_arp_table(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def delete_arp(self, ips, if_names):
        """删除 ARP 表项。

        对应 UI 页面「网络管理 → ARP 表 → 删除」。

        ``ips`` 和 ``if_names`` 支持单个 str 或 list[str]，长度需一致，按索引一一对应。

        :param ips:      IP 地址，str 或 list[str]。
        :param if_names: 接口名称，str 或 list[str]，与 ``ips`` 一一对应。
        :return: 成功返回 ``True``；失败返回 ``False``。
        :raises ValueError: 当 ``ips`` 和 ``if_names`` 类型不一致时抛出。
        """
        if isinstance(ips, str) and isinstance(if_names, str):
            ips = [ips]
            if_names = [if_names]
        elif not (isinstance(ips, list) and isinstance(if_names, list)):
            raise ValueError('ips and if_names must be str or list[str]')
        data = {'action': 'delete', 'ips': [{'ip': tmp_ip, 'interface':
            tmp_name} for tmp_ip, tmp_name in zip(ips, if_names)]}
        url = f'{self.base_url}/nf/network/arp/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除ARP失败: {e}')
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

    def clean_dynamic_arp(self):
        """清空动态 ARP 表项。

        对应 UI 页面「网络管理 → ARP 表 → 清空动态 ARP」。

        请求体固定为 ``{"action": "clean_dynamic_arp", "ips": []}``。

        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'action': 'clean_dynamic_arp', 'ips': []}
        url = f'{self.base_url}/nf/network/arp/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空动态ARP失败: {e}')
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

    def bind_arp(self, ips, if_names):
        """绑定 ARP 表项。

        对应 UI 页面「网络管理 → ARP 表 → 绑定」。

        ``ips`` 和 ``if_names`` 支持单个 str 或 list[str]，长度需一致，按索引一一对应。

        :param ips:      IP 地址，str 或 list[str]。
        :param if_names: 接口名称，str 或 list[str]，与 ``ips`` 一一对应。
        :return: 成功返回 ``True``；失败返回 ``False``。
        :raises ValueError: 当 ``ips`` 和 ``if_names`` 类型不一致时抛出。
        """
        if isinstance(ips, str) and isinstance(if_names, str):
            ips = [ips]
            if_names = [if_names]
        elif not (isinstance(ips, list) and isinstance(if_names, list)):
            raise ValueError('ip and if_name must be str or list[str]')
        data = {'ips': [{'ip': tmp_ip, 'interface': tmp_name} for tmp_ip,
            tmp_name in zip(ips, if_names)]}
        url = f'{self.base_url}/nf/network/arp/bind/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'绑定ARP失败: {e}')
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

    def sync_arp_table(self):
        """同步 ARP 表数据。

        对应 UI 页面「网络管理 → ARP 表 → 刷新/同步」。

        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/arp/update/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'同步ARP表失败: {e}')
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

    def update_arp_config(self, aging_time=300, interval_time=30):
        """更新 ARP 全局配置。

        对应 UI 页面「网络管理 → ARP 配置」。

        :param aging_time:    动态 ARP 老化时间（秒），默认 ``300``。
        :param interval_time: 免费 ARP 发送间隔（秒），默认 ``30``。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        data = {'aging_time': aging_time, 'interval_time': interval_time}
        url = f'{self.base_url}/nf/network/arp_config/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新ARP配置失败: {e}')
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

    def get_arp_config(self):
        """获取 ARP 全局配置。

        对应 UI 页面「网络管理 → ARP 配置」。

        :return: 成功返回完整响应 dict，``result`` 包含 ``aging_time``、``interval_time``、``ipConflictDetect``；
                 失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/arp_config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取ARP配置失败: {e}')
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
