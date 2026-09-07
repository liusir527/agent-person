"""关键字对象 — 系统关键字和自定义关键字 CRUD。

对应 UI 页面「对象 → 安全防护 → 内容安全 → 关键字」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class KeywordObjectFeature(NFRequests):
    """关键字对象操作集合 — 系统关键字和自定义关键字的增删查改。"""

    def create_or_update_keyword_obj(self, action='create', keyword_type=
        'custom', name='keyword1', key=None, comment='', key_list=None, obj_id=None
        ):
        """创建或修改关键字对象。

        对应 UI 页面「对象 → 安全防护 → 内容安全 → 关键字」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param keyword_type: 关键字类型，``"custom"`` = 自定义关键字，``"system"`` = 系统关键字
        :type keyword_type: str
        :param name: 关键字对象名称
        :type name: str
        :param key: 关键字内容，可以是字符串或列表，默认 ``['keywords']``
        :type key: str or list
        :param comment: 备注
        :type comment: str
        :param key_list: 系统关键字对象 ID 列表，默认 ``[0]``，仅 ``keyword_type='system'`` 时使用
        :type key_list: list
        :param obj_id: 对象 ID，编辑时必填
        :type obj_id: int or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if key is None:
            key = ['keywords']
        elif isinstance(key, str):
            key = [key]
        if key_list is None:
            key_list = [0]
        elif isinstance(key_list, int):
            key_list = [key_list]
        data = {'action': action, 'type': keyword_type, 'name': name, 'comment':
            comment}
        if keyword_type == 'custom':
            data['key'] = key
        else:
            data['key_list'] = key_list
        if action != 'create':
            data['id'] = obj_id
        req_url = f'{self.base_url}/nf/object/scm/key/obj_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改关键字对象失败: {e}')
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

    def get_keyword_obj(self, keyword_type='system', page=1, size=10, search=''):
        """获取关键字对象列表。

        对应 UI 页面「对象 → 安全防护 → 内容安全 → 关键字」。

        :param keyword_type: 关键字类型，``"custom"`` = 自定义关键字，``"system"`` = 系统关键字
        :type keyword_type: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典（``result.list`` 为关键字列表），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/scm/key/info/'
        params = {'type': keyword_type, 'page': page, 'size': size, 'search':
            search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取关键字对象列表失败: {e}')
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

    def get_keyword_obj_id(self, keyword_type='system', page=1, size=10, search=''):
        """按名称查询关键字对象 ID。

        :param keyword_type: 关键字类型，``"custom"`` = 自定义关键字，``"system"`` = 系统关键字
        :type keyword_type: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 关键字对象名称
        :type search: str
        :return: 成功返回对象 id，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_keyword_obj(keyword_type=keyword_type, page=page,
                                    size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_keyword_obj(self, obj_id):
        """删除关键字对象。

        对应 UI 页面「对象 → 安全防护 → 内容安全 → 关键字」。

        :param obj_id: 对象 ID，可以是单个值或列表
        :type obj_id: int or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(obj_id, (list, tuple)):
            obj_ids = [int(x) for x in obj_id]
        else:
            obj_ids = [int(obj_id)]
        data = {'id': obj_ids}
        req_url = f'{self.base_url}/nf/object/scm/key/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除关键字对象失败: {e}')
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