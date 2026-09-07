"""URL 黑白名单 — URL 白名单和黑名单的增删查改及回收站恢复。

对应 UI 页面「对象 → URL 分类 → 白名单」「对象 → URL 分类 → 黑名单」。
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


class UrlBlackWhiteListFeature(NFRequests):
    """URL 黑白名单操作集合 — 白名单和黑名单的增删查改及回收站操作。"""

    def create_or_update_url_white_list(self, action='create', content='',
        url_id='', status=True):
        """创建或修改 URL 白名单。

        对应 UI 页面「对象 → URL 分类 → 白名单」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param content: URL 地址
        :type content: str
        :param url_id: 白名单 ID，编辑时必填
        :type url_id: str
        :param status: 是否启用
        :type status: bool
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'action': action, 'content': content, 'id': url_id, 'status':
            status}
        req_url = f'{self.base_url}/nf/object/url/white_list/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改URL白名单失败: {e}')
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

    def create_or_update_url_black_list(self, action='create', content='',
        url_id='', status=True):
        """创建或修改 URL 黑名单。

        对应 UI 页面「对象 → URL 分类 → 黑名单」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param content: URL 地址
        :type content: str
        :param url_id: 黑名单 ID，编辑时必填
        :type url_id: str
        :param status: 是否启用
        :type status: bool
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'action': action, 'content': content, 'id': url_id, 'status':
            status}
        req_url = f'{self.base_url}/nf/object/url/black_list/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改URL黑名单失败: {e}')
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

    def get_url_white_list(self, page=1, size=10, search='', url_type=''):
        """获取 URL 白名单列表。

        对应 UI 页面「对象 → URL 分类 → 白名单」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param url_type: 列表类型过滤
        :type url_type: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/url/white_list/'
        params = {'page': page, 'size': size, 'search': search, 'type': url_type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取URL白名单失败: {e}')
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

    def get_url_black_list(self, page=1, size=10, search='', url_type=''):
        """获取 URL 黑名单列表。

        对应 UI 页面「对象 → URL 分类 → 黑名单」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param url_type: 列表类型过滤
        :type url_type: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/url/black_list/'
        params = {'page': page, 'size': size, 'search': search, 'type': url_type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取URL黑名单失败: {e}')
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

    def remove_url_white_list(self, url_id='', recycle=False):
        """删除 URL 白名单。

        对应 UI 页面「对象 → URL 分类 → 白名单」。

        :param url_id: 白名单 ID，多个以逗号分隔
        :type url_id: str
        :param recycle: 是否放入回收站（可从回收站恢复）
        :type recycle: bool
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'id': url_id, 'recycle': recycle}
        req_url = f'{self.base_url}/nf/object/url/white_list/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除URL白名单失败: {e}')
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

    def remove_url_black_list(self, url_id='', recycle=False):
        """删除 URL 黑名单。

        对应 UI 页面「对象 → URL 分类 → 黑名单」。

        :param url_id: 黑名单 ID，多个以逗号分隔
        :type url_id: str
        :param recycle: 是否放入回收站（可从回收站恢复）
        :type recycle: bool
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'id': url_id, 'recycle': recycle}
        req_url = f'{self.base_url}/nf/object/url/black_list/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除URL黑名单失败: {e}')
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
