"""时间对象 — 自定义时间和时间组 CRUD。

对应 UI 页面「对象 → 时间对象」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class TimeObjectFeature(NFRequests):
    """时间对象操作集合 — 自定义时间和时间组的增删查改。"""

    def create_or_update_time_obj(self, name='auto', time_type='day', stime=
        '00:00:00', dtime='23:59:59', scope='*', note='', obj_type='custom',
        obj_id=None, date=None, contain_object=None, action=None):
        """创建或修改时间对象（自定义时间或时间组）。

        对应 UI 页面「对象 → 时间对象」。

        :param name: 对象名称
        :type name: str
        :param time_type: 时间类型，``"day"`` = 每天，``"week"`` = 按星期，``"month"`` = 按月
        :type time_type: str
        :param stime: 开始时间，格式 ``"HH:MM:SS"``
        :type stime: str
        :param dtime: 结束时间，格式 ``"HH:MM:SS"``
        :type dtime: str
        :param scope: 生效范围，默认 ``"*"``
        :type scope: str
        :param note: 备注
        :type note: str
        :param obj_type: 对象类型，``"custom"`` = 自定义时间，``"group"`` = 时间组
        :type obj_type: str
        :param obj_id: 对象 ID，编辑时使用
        :type obj_id: int or None
        :param date: 日期配置：``time_type='day'`` 时取 ``"*"``；``time_type='week'`` 时取 ``"周一,周二,..."``；``time_type='month'`` 时取 ``"1-31"``
        :type date: str or None
        :param contain_object: 包含的时间对象名称，字符串或列表，仅 ``obj_type='group'`` 时使用
        :type contain_object: str or list or None
        :param action: 操作类型，``"create"`` 或 ``"edit"``，不传时根据 ``obj_id`` 自动判断
        :type action: str or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if action is None:
            action = 'create' if obj_id is None else 'edit'
        if time_type == 'week':
            date = date if date is not None else '周一,周二,周三,周四,周五,周六,周日'
        elif time_type == 'month':
            date = date if date is not None else '1-31'
        else:
            date = date if date is not None else '*'
        if contain_object is None:
            contain_object = 'any'
        elif isinstance(contain_object, list):
            contain_object = ','.join(contain_object)
        data = {'action': action, 'type': obj_type, 'name': name, 'note': note}
        if obj_type == 'custom':
            data.update({'scope': scope, 'time_type': time_type, 'stime': stime,
                'dtime': dtime})
            if time_type in ('week', 'month'):
                data['date'] = date
        elif obj_type == 'group':
            data['contain_object'] = contain_object
        if action == 'edit':
            data['id'] = obj_id
        req_url = f'{self.base_url}/nf/object/timeobj/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改时间对象失败: {e}')
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

    def get_time_obj(self, obj_type='custom', page=1, size=10, search=''):
        """获取时间对象列表。

        对应 UI 页面「对象 → 时间对象」。

        :param obj_type: 对象类型，``"custom"`` = 自定义时间，``"group"`` = 时间组
        :type obj_type: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典（``result.list`` 为时间对象列表，``result.overview`` 含引用统计），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/timeobj/'
        params = {'type': obj_type, 'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取时间对象列表失败: {e}')
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

    def get_time_obj_id(self, obj_type='custom', search='', page=1, size=10):
        """按名称获取时间对象 ID。

        :param obj_type: 对象类型，``"custom"`` = 自定义时间，``"group"`` = 时间组
        :type obj_type: str
        :param search: 对象名称
        :type search: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :return: 成功返回 id 值，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_time_obj(obj_type=obj_type, page=page, size=size,
                                 search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for item in result.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_time_obj(self, obj_id, obj_type='custom'):
        """删除时间对象。

        对应 UI 页面「对象 → 时间对象」。

        :param obj_id: 对象 ID，单个值、列表或 ``"all"``（删除全部）
        :type obj_id: int or str or list
        :param obj_type: 对象类型，``"custom"`` = 自定义时间，``"group"`` = 时间组，``obj_id='all'`` 时使用
        :type obj_type: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(obj_id, (list, tuple)):
            obj_ids = ','.join(map(str, obj_id))
        else:
            obj_ids = str(obj_id)
        data = {'id': obj_ids}
        if obj_id == 'all':
            data['type'] = obj_type
        req_url = f'{self.base_url}/nf/object/timeobj_delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除时间对象失败: {e}')
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