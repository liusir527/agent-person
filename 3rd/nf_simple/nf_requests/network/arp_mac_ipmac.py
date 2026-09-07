"""ARP/MAC/IPMAC 配置。"""

import sys
import requests
import json
import os
import base64
import logging

from ..nflib.Log import logger
from ..nflib.comm import *
from ..client import NFRequests


class ArpMacIpmacFeature(NFRequests):
    """ARP/MAC/IPMAC 配置操作集合。

    涵盖 ARP 表项管理、MAC 表项管理、IPMAC 绑定策略。
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
            msg = f'创建ARP失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

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
            msg = f'更新ARP失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

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
            msg = f'获取ARP表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

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
        if isinstance(resp, dict) and resp.get("success") is False:
            return resp
        result_data = resp.get("result", {})
        if result_data.get('total', 0) == 0:
            return {"success": False, "message": "未找到匹配项"}
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return {"success": False, "message": "操作失败"}

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
            msg = f'删除ARP失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

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
            msg = f'清空动态ARP失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

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
            msg = f'绑定ARP失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def sync_arp_table(self):
        """同步 ARP 表数据。

        对应 UI 页面「网络管理 → ARP 表 → 刷新/同步」。

        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/arp/update/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            msg = f'同步ARP表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

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
            msg = f'更新ARP配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

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
            msg = f'获取ARP配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def update_ipmac_global_config(self, is_log=False, is_block=False, req_body
        =None):
        """更新 IPMAC 全局配置。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 全局配置」。

        :param is_log:   是否记录日志，默认 ``False``。
        :param is_block: 是否阻断，默认 ``False``。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'is_log': is_log, 'is_block': is_block}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/ipmac/global_config_update/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'更新IPMAC全局配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_ipmac_global_config(self):
        """获取 IPMAC 全局配置。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 全局配置」。

        :return: 成功返回完整响应 dict，``result`` 包含 ``is_block``、``is_log``、``ip_mac_enable``、
                 ``snmp_mac_enable``、``is_strict_match``；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/global_config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            msg = f'获取IPMAC全局配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def create_or_update_ipmac(self, action='create', ipmac_id=-1, is_enable=
        'yes', ip_addr='0.0.0.0', mac_addr='00:00:00:00:00:00', description='',
        req_body=None):
        """创建或修改 IPMAC 绑定策略。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 新建/编辑」。

        ``is_enable`` 取值：
            - ``"yes"`` = 启用（默认）
            - ``"no"`` = 禁用

        :param action:      操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param ipmac_id:    策略 ID。创建时传 ``-1``（默认），编辑时传实际 ID。
        :param is_enable:   是否启用，默认 ``"yes"``。
        :param ip_addr:     IP 地址，默认 ``"0.0.0.0"``。
        :param mac_addr:    MAC 地址，默认 ``"00:00:00:00:00:00"``。
        :param description: 备注描述，默认 ``""``。
        :param req_body:    自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'action': action, 'list': [{'id': ipmac_id, 'is_enable':
            is_enable, 'ip_addr': ip_addr, 'mac_addr': mac_addr, 'description':
            description}]}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/ipmac/ipmac_action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'创建或修改IPMAC策略失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def remove_ipmac(self, ipmac_id, req_body=None):
        """根据 ID 删除 IPMAC 策略。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 删除」。

        ``ipmac_id`` 支持 int、str 或 list[int/str]，传入单个值时自动包装为列表。

        :param ipmac_id:  IPMAC 策略 ID，支持 int、str 或 list（如 ``[1, 2]``）。
        :param req_body:  自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(ipmac_id, (str, int)):
            ipmac_id = [int(ipmac_id)]
        elif isinstance(ipmac_id, list):
            ipmac_id = [int(i) for i in ipmac_id]
        else:
            msg = 'ipmac_id can not be None'
            logger.error(msg)
            return {"success": False, "message": msg}
        data = {'id': ipmac_id}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/ipmac/ipmac_delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'删除IPMAC策略失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def clear_ipmac(self):
        """清空全部 IPMAC 策略。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 清空」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/clear/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            msg = f'清除IPMAC策略失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_ipmac(self, size=10, page=1, search=''):
        """获取 IPMAC 策略列表。

        对应 UI 页面「安全策略 → IPMAC 绑定」。

        :param size:   每页数量，默认 ``10``。
        :param page:   页码，默认 ``1``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/info/'
        params = {'size': size, 'page': page, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            msg = f'获取IPMAC策略列表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_ipmac_id(self, size=10, page=1, search=''):
        """根据名称查询 IPMAC 策略 ID。

        对应 UI 页面「安全策略 → IPMAC 绑定」。

        调用 ``get_ipmac`` 后在返回列表中按 ``name`` 精确匹配。

        :param size:   每页数量，默认 ``10``。
        :param page:   页码，默认 ``1``。
        :param search: IPMAC 策略名称关键字，用于匹配。
        :return: 匹配到时返回策略 ID (int)；失败返回 ``False``。
        """
        resp = self.get_ipmac(size=size, page=page, search=search)
        if isinstance(resp, dict) and resp.get("success") is False:
            return resp
        result_data = resp.get("result", {})
        if result_data.get('total', 0) == 0:
            return {"success": False, "message": "未找到匹配项"}
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return {"success": False, "message": "操作失败"}

    def export_ipmac(self):
        """导出 IPMAC 配置为 CSV/文本格式。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 导出」。

        :return: 成功返回 CSV/文本字符串内容；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/export/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            msg = f'导出IPMAC配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            logger.info('导出IPMAC配置成功')
            return result.text
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def create_or_update_mac_table(self, action='create', vlan_id=1, mac=
        '00:00:00:00:00:00', interface='G1/1', note='', enabled=True, table_id=
        '0', req_body=None):
        """创建或更新 MAC 表项。

        对应 UI 页面「网络管理 → MAC 表 → 新建/编辑」。

        :param action:    操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param vlan_id:   VLAN ID，默认 ``1``。
        :param mac:       MAC 地址，默认 ``"00:00:00:00:00:00"``。
        :param interface: 接口名称，默认 ``"G1/1"``。
        :param note:      备注，默认 ``""``。
        :param enabled:   是否启用，默认 ``True``。
        :param table_id:  编辑时必填，表项 ID 字符串，默认 ``"0"``。
        :param req_body:  自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'action': action, 'vlan': vlan_id, 'mac': mac, 'interface':
            interface, 'note': note, 'enabled': enabled}
        if action == 'edit':
            data['id'] = table_id
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/mac/action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'创建或更新MAC表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def remove_mac_table(self, vlan_id=1, mac='00:00:00:00:00:00', action=
        'delete', req_params=None):
        """删除 MAC 表项。

        对应 UI 页面「网络管理 → MAC 表 → 删除」。

        ``vlan_id`` 和 ``mac`` 支持单个值（int/str）或 list，组成 ``uuid`` 格式 ``"vlan_id+mac"``。

        :param vlan_id:    VLAN ID，int 或 list[int]。默认 ``1``。
        :param mac:        MAC 地址，str 或 list[str]。默认 ``"00:00:00:00:00:00"``。
        :param action:     操作动作，固定 ``"delete"``。
        :param req_params: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(vlan_id, int) and isinstance(mac, str):
            uuid = [str(vlan_id) + '+' + mac]
        elif isinstance(vlan_id, list) and isinstance(mac, list):
            uuid = [(str(i) + '+' + j) for i, j in zip(vlan_id, mac)]
        else:
            msg = 'vlan_id and mac must be list[int]/list[str] or int/str'
            logger.error(msg)
            return {"success": False, "message": msg}
        data = {'action': action, 'uuid': uuid
            } if req_params is None else req_params
        req_url = f'{self.base_url}/nf/network/mac/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'删除MAC表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_mac_table(self, page=1, size=10, search=''):
        """获取 MAC 表列表。

        对应 UI 页面「网络管理 → MAC 表」。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/network/mac/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            msg = f'获取MAC表列表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_mac_table_id(self, page=1, size=10, search=''):
        """根据名称查询 MAC 表项 ID。

        对应 UI 页面「网络管理 → MAC 表」。

        调用 ``get_mac_table`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: MAC 表项名称关键字，用于匹配。
        :return: 匹配到时返回表项 ID (int)；失败返回 ``False``。
        """
        resp = self.get_mac_table(page=page, size=size, search=search)
        if isinstance(resp, dict) and resp.get("success") is False:
            return resp
        result_data = resp.get("result", {})
        if result_data.get('total', 0) == 0:
            return {"success": False, "message": "未找到匹配项"}
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return {"success": False, "message": "操作失败"}

    def refresh_mac_table(self):
        """刷新 MAC 表数据。

        对应 UI 页面「网络管理 → MAC 表 → 刷新」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/network/mac/update/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            msg = f'刷新MAC表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def bind_mac_table(self, vlan_id=1, mac='00:00:00:00:00:00', req_params=None):
        """绑定 MAC 表项。

        对应 UI 页面「网络管理 → MAC 表 → 绑定」。

        ``vlan_id`` 和 ``mac`` 支持单个值（int/str）或 list，组成 ``uuid`` 格式 ``"vlan_id+mac"``。

        :param vlan_id:    VLAN ID，int 或 list[int]。默认 ``1``。
        :param mac:        MAC 地址，str 或 list[str]。默认 ``"00:00:00:00:00:00"``。
        :param req_params: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(vlan_id, int) and isinstance(mac, str):
            uuid = [str(vlan_id) + '+' + mac]
        elif isinstance(vlan_id, list) and isinstance(mac, list):
            uuid = [(str(i) + '+' + j) for i, j in zip(vlan_id, mac)]
        else:
            msg = 'vlan_id and mac must be list[int]/list[str] or int/str'
            logger.error(msg)
            return {"success": False, "message": msg}
        data = {'uuid': uuid} if req_params is None else req_params
        req_url = f'{self.base_url}/nf/network/mac/bind/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'绑定MAC表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}
