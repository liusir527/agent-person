"""安全区配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class ZoneFeature(NFRequests):
    """安全区配置操作集合。"""

    def create_or_update_safe_zone(self, action='create', name='test_zone',
        type='customize', comment='', zone_type=''):
        """创建或更新安全区。

        对应 UI 页面「网络管理 → 安全区 → 新建/编辑」。

        ``type`` 取值：
            - ``"customize"`` = 用户自定义安全区（默认）
            - ``"default"`` = 系统预置安全区

        当 ``zone_type`` 为空时，自动通过 ``get_safe_zone_last_id`` 获取下一个可用值。

        :param action:    操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param name:      安全区名称，默认 ``"test_zone"``。
        :param type:      安全区类别。``"customize"`` = 自定义，``"default"`` = 系统预置。
        :param comment:   描述信息，默认 ``""``。
        :param zone_type: 安全区类型 ID（整数）。留空时自动获取下一个可用 ID。
        :return: 成功返回 ``True``；失败返回 ``False``。
        """
        if zone_type=="":
            zone_type=self.get_safe_zone_last_id()
        data = {'action': action, 'name': name, 'type': type, 'comment':
            comment, 'zone_type': zone_type}
        url = f'{self.base_url}/nf/network/zone/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新安全区失败: {e}')
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
                return True
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
    def get_safe_zone_last_id(self):
        """获取安全区总数（用于计算下一个可用 ``zone_type``）。

        通过查询安全区列表（每页 50 条）获取当前总数，创建新安全区时 ``zone_type`` 需大于已有总数。

        :return: 安全区总数 (int)；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/zone/'
        params = {'page': 1, 'size': 50, 'search': ''}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取安全区列表失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            if resp_data.get('status') != 2000:
                logger.error(resp_data.get('message'))
                return False
            return resp_data['result']['total']
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False






    def get_safe_zone(self, page=1, size=10, search=''):
        """获取安全区列表。

        对应 UI 页面「网络管理 → 安全区」。

        返回列表中 ``type`` 字段说明：
            - ``"default"`` = 系统预置安全区（GLOBAL、TRUST、UNTRUST、DMZ、UNKNOWN、SSLVPN）
            - ``"customize"`` = 用户自定义安全区

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/zone/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取安全区列表失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_safe_zone_id(self, page=1, size=10, search=''):
        """根据名称查询安全区 ID。

        对应 UI 页面「网络管理 → 安全区」。

        调用 ``get_safe_zone`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 安全区名称关键字，用于匹配。
        :return: 匹配到时返回安全区 ID (int)；失败返回 ``False``。
        """
        resp = self.get_safe_zone(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_safe_zone(self, zone_id, req_body=None):
        """删除安全区。

        对应 UI 页面「网络管理 → 安全区 → 删除」。

        :param zone_id:  安全区 ID。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': zone_id}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/zone/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除安全区失败: {e}')
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
