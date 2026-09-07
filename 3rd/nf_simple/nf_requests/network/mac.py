"""MAC 表配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class MacFeature(NFRequests):
    """MAC 表配置操作集合。

    涵盖 MAC 表项的增删改查、绑定、刷新。
    """

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
            logger.error(f'创建或更新MAC表失败: {e}')
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
            logger.error('vlan_id and mac must be list[int]/list[str] or int/str')
            return False
        data = {'action': action, 'uuid': uuid
            } if req_params is None else req_params
        req_url = f'{self.base_url}/nf/network/mac/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除MAC表失败: {e}')
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
            logger.error(f'获取MAC表列表失败: {e}')
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
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def refresh_mac_table(self):
        """刷新 MAC 表数据。

        对应 UI 页面「网络管理 → MAC 表 → 刷新」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/network/mac/update/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'刷新MAC表失败: {e}')
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
            logger.error('vlan_id and mac must be list[int]/list[str] or int/str')
            return False
        data = {'uuid': uuid} if req_params is None else req_params
        req_url = f'{self.base_url}/nf/network/mac/bind/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'绑定MAC表失败: {e}')
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
