"""应用对象 — 系统应用和应用对象组 CRUD 及引用查询。

对应 UI 页面「对象 → 应用对象」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class AppObjectFeature(NFRequests):
    """应用对象操作集合 — 系统应用查询和应用对象组的增删查改及引用查询。"""

    def create_or_update_app(self, action='create', app_type='group', name=
        'test_app_group', contain_object=None, comment='', app_group_id=None):
        """创建或更新应用对象组。

        对应 UI 页面「对象 → 应用对象」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param app_type: 对象类型，固定 ``"group"``
        :type app_type: str
        :param name: 对象组名称
        :type name: str
        :param contain_object: 包含的应用对象名称，字符串或列表（多个以逗号分隔）
        :type contain_object: str or list or None
        :param comment: 备注
        :type comment: str
        :param app_group_id: 对象组 ID，编辑时使用
        :type app_group_id: int or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if contain_object is None:
            contain_object = ['test_app_obj']
        elif isinstance(contain_object, tuple):
            contain_object = list(contain_object)
        if isinstance(contain_object, list):
            contain_object = ','.join(contain_object)
        data = {'action': action, 'type': app_type, 'name': name,
            'contain_object': contain_object, 'comment': comment}
        if app_group_id is not None:
            data['id'] = app_group_id
        req_url = f'{self.base_url}/nf/object/appobj/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新应用对象组失败: {e}')
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

    def get_app(self, page=1, size=10, search='', app_type='system'):
        """查询应用对象列表。

        对应 UI 页面「对象 → 应用对象」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param app_type: 对象类型，``"system"`` = 系统内置（共 8044 个），``"group"`` = 用户自定义组
        :type app_type: str
        :return: 成功返回 API 响应字典（``result.list`` 为应用对象列表），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/appobj/'
        params = {'type': app_type, 'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'查询应用对象失败: {e}')
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

    def get_app_id(self, page=1, size=10, search='', app_type='system'):
        """按名称查询应用对象 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 应用对象名称
        :type search: str
        :param app_type: 对象类型，``"system"`` = 系统内置，``"group"`` = 用户自定义组
        :type app_type: str
        :return: 成功返回 id 值，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_app(page=page, size=size, search=search, app_type=app_type)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_app_group(self, obj_id):
        """删除应用对象组。

        对应 UI 页面「对象 → 应用对象」。

        :param obj_id: 对象组 ID，单个值或列表（多个以逗号拼接）
        :type obj_id: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(obj_id, (list, tuple)):
            obj_ids = ','.join(map(str, obj_id))
        else:
            obj_ids = str(obj_id)
        data = {'ids': obj_ids}
        req_url = f'{self.base_url}/nf/object/appobj/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除应用对象组失败: {e}')
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

    def get_app_referenced(self):
        """获取应用对象引用信息。

        对应 UI 页面「对象 → 应用对象」。

        :return: 成功返回 API 响应字典（``result.overview`` 含平台和应用总数及引用统计），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/appobj/referenced/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取应用对象引用情况失败: {e}')
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