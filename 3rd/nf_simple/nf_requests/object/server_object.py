"""服务对象 — 自定义服务、系统服务和服务器组 CRUD 及引用查询。

对应 UI 页面「对象 → 服务对象」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class ServerObjectFeature(NFRequests):
    """服务对象操作集合 — 自定义服务、系统服务和服务器组的增删查改及引用查询。"""

    def create_or_update_service_obj(self, action='create', srv_type='custom',
        name='srv1', protocol='TCP', s_port='0-65535', d_port='0-65535', note=
        '', ip_protocol_type='ip', obj_id=None, contain_object=None):
        """创建或修改服务对象（自定义服务或服务组）。

        对应 UI 页面「对象 → 服务对象」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param srv_type: 服务对象类型，``"custom"`` = 自定义服务，``"group"`` = 服务组
        :type srv_type: str
        :param name: 对象名称
        :type name: str
        :param protocol: 协议，``"TCP"``、``"UDP"``、``"ICMP"`` 等，仅 ``srv_type='custom'`` 时使用
        :type protocol: str
        :param s_port: 源端口范围，仅 ``srv_type='custom'`` 时使用
        :type s_port: str
        :param d_port: 目的端口范围，仅 ``srv_type='custom'`` 时使用
        :type d_port: str
        :param note: 备注
        :type note: str
        :param ip_protocol_type: IP 协议类型，仅 ``srv_type='custom'`` 时使用
        :type ip_protocol_type: str
        :param obj_id: 对象 ID，编辑时必填
        :type obj_id: int or None
        :param contain_object: 包含的服务对象名称，字符串或列表，仅 ``srv_type='group'`` 时使用
        :type contain_object: str or list or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        :raises Exception: 当 ``action != 'create'`` 且 ``obj_id`` 为 None 时抛出
        """
        if contain_object is None:
            contain_object = 'any'
        elif isinstance(contain_object, list):
            contain_object = ','.join(contain_object)
        data = {'action': action, 'type': srv_type, 'name': name, 'note': note}
        if srv_type == 'custom':
            data.update({'protocol': protocol, 's_port': s_port, 'd_port':
                d_port, 'ip_protocol_type': ip_protocol_type})
        else:
            data['contain_object'] = contain_object
        if action != 'create':
            if obj_id is None:
                raise Exception('obj_id is None')
            data['id'] = obj_id
        req_url = f'{self.base_url}/nf/object/serviceobj/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改服务对象失败: {e}')
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

    def get_service_obj(self, srv_type='system', page=1, size=10, search=''):
        """获取服务对象列表。

        对应 UI 页面「对象 → 服务对象」。

        :param srv_type: 服务对象类型，``"system"`` = 系统内置，``"custom"`` = 自定义，``"group"`` = 服务组
        :type srv_type: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典（``result.list`` 为服务对象列表），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/serviceobj/'
        params = {'type': srv_type, 'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取服务对象列表失败: {e}')
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

    def get_service_obj_id(self, srv_type='system', search='', page=1, size=10):
        """按名称获取服务对象 backend_id。

        :param srv_type: 服务对象类型，``"system"`` = 系统内置，``"custom"`` = 自定义，``"group"`` = 服务组
        :type srv_type: str
        :param search: 对象名称
        :type search: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :return: 成功返回 backend_id 值，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_service_obj(srv_type=srv_type, page=page, size=size,
                                    search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for item in result.get('list', []):
            if item.get('name') == search:
                return item.get('backend_id')
        return False

    def remove_service_obj(self, obj_id, srv_type=None):
        """删除服务对象。

        对应 UI 页面「对象 → 服务对象」。

        :param obj_id: 对象 ID，单个值或列表（多个以逗号拼接）
        :type obj_id: int or str or list
        :param srv_type: 服务对象类型，可选
        :type srv_type: str or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(obj_id, (list, tuple)):
            obj_ids = ','.join(map(str, obj_id))
        else:
            obj_ids = str(obj_id)
        data = {'id': obj_ids}
        if srv_type is not None:
            data['type'] = srv_type
        req_url = f'{self.base_url}/nf/object/serviceobj_delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除服务对象失败: {e}')
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

    def get_service_referenced(self):
        """获取服务对象引用信息。

        对应 UI 页面「对象 → 服务对象」。

        :return: 成功返回 API 响应字典（``result.overview`` 含各类型服务对象数量和引用统计），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/service_obj_referenced/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取服务对象引用信息失败: {e}')
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