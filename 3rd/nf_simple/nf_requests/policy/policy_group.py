"""策略组 — 防火墙策略组的增删查改、属性清理。

对应 UI 页面「策略 → 防火墙策略组」。

对应 API 文档中的 ``get_fw_group``、``create_or_update_fw_group``、``remove_fw_group``、
``clear_fw_group_attr``。
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


class PolicyGroupFeature(NFRequests):
    """策略组操作集合 — 防火墙策略组的增删查改和属性清理。"""

    def create_or_update_policy_grp(self, name='autotest_grp', rule=None,
        comment='', grp_id=None):
        """创建或更新防火墙策略组。

        对应 API 文档中的 ``create_or_update_fw_group``。

        :param name: 策略组名称，默认 ``"autotest_grp"``
        :type name: str
        :param rule: 包含的策略 ID 列表，可为 ``str`` / ``int`` / ``list``
        :type rule: str or int or list or None
        :param comment: 备注
        :type comment: str
        :param grp_id: 策略组 ID，传入时表示编辑模式
        :type grp_id: int or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        command = 'create' if grp_id is None else 'edit'
        if rule is not None:
            if isinstance(rule, str):
                rule = [rule]
            elif isinstance(rule, list):
                rule = [str(pid) for pid in rule]
            else:
                rule = [str(rule)]
        else:
            rule = []
        data = {'command': command, 'name': name, 'rule': rule, 'comment': comment}
        if grp_id is not None:
            data['id'] = grp_id
        url = f'{self.base_url}/nf/strategy/firewall/group/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新防火墙策略组失败: {e}')
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

    def get_policy_grp(self, page=1, size=10, search=''):
        """获取防火墙策略组列表。

        对应 API 文档中的 ``get_fw_group``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        params = {'size': size, 'page': page, 'search': search}
        url = f'{self.base_url}/nf/strategy/firewall/group/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取防火墙策略组失败: {e}')
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

    def clear_policy_grp_attr(self, fw_id=None, req_body=None):
        """清空策略组中的防火墙策略（移除策略组中绑定的策略条目）。

        对应 API 文档中的 ``clear_fw_group_attr``。

        :param fw_id: 防火墙策略 ID，可为 ``int`` / ``str`` / ``list``
        :type fw_id: int or str or list or None
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(fw_id, (int, str)):
            fw_id = [fw_id]
        data = {'id': fw_id}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/firewall/group/clear_attr/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清理策略组属性失败: {e}')
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

    def remove_policy_grp(self, grp_id=None, req_body=None):
        """删除防火墙策略组。

        对应 API 文档中的 ``remove_fw_group``。

        :param grp_id: 策略组 ID，可为单个 ``int``/``str`` 或 ``list``
        :type grp_id: int or str or list or None
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(grp_id, list):
            grp_id = ','.join([str(item) for item in grp_id])
        else:
            grp_id = str(grp_id)
        data = {'id': grp_id}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/firewall/group/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除防火墙策略组失败: {e}')
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
