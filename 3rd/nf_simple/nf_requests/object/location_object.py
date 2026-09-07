"""地理位置对象 — 基于国家/省份/城市的地理位置对象 CRUD 及全局配置。

对应 UI 页面「对象 → 安全防护 → 地理位置」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class LocationObjectFeature(NFRequests):
    """地理位置对象操作集合 — 地理位置对象的增删查改、详情、全局配置。"""

    def create_or_update_location_obj(self, action='create', name=None, country
        ='CN', province='', city='', district='', obj_id=None):
        """创建或修改地理位置对象。

        对应 UI 页面「对象 → 安全防护 → 地理位置」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 对象名称，默认使用国家代码（``country`` 参数值）
        :type name: str or None
        :param country: 国家代码，默认 ``"CN"``
        :type country: str
        :param province: 省份代码，默认 ``""``
        :type province: str
        :param city: 城市代码，默认 ``""``
        :type city: str
        :param district: 区县代码，默认 ``""``
        :type district: str
        :param obj_id: 对象 ID，编辑时必填
        :type obj_id: int or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        :raises ValueError: 当 ``action != 'create'`` 且 ``obj_id`` 为 None 时抛出
        """
        if name is None:
            name = country
        data = {'action': action, 'id': '', 'name': name, 'country': country,
            'province': province, 'city': city, 'district': district}
        if action != 'create':
            if obj_id is None:
                raise ValueError(
                    'obj_id is None, please give obj_id when action is edit !!!')
            data['id'] = obj_id
        req_url = f'{self.base_url}/nf/object/geography/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改地理位置对象失败: {e}')
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

    def get_location_obj(self, page=1, size=10, name='', where='OR', country=
        None, province=None, city=None, district=None):
        """获取地理位置对象列表。

        对应 UI 页面「对象 → 安全防护 → 地理位置」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param name: 对象名称（模糊搜索）
        :type name: str
        :param where: 查询条件逻辑，``"OR"`` = 或，``"AND"`` = 与
        :type where: str
        :param country: 国家代码过滤
        :type country: str or None
        :param province: 省份代码过滤
        :type province: str or None
        :param city: 城市代码过滤
        :type city: str or None
        :param district: 区县代码过滤
        :type district: str or None
        :return: 成功返回 API 响应字典（``result.list`` 为对象列表），失败返回 False
        :rtype: dict or bool
        """
        data = {'page': page, 'size': size, 'name': name, 'where': where}
        if country is not None:
            data['country'] = country
        if province is not None:
            data['province'] = province
        if city is not None:
            data['city'] = city
        if district is not None:
            data['district'] = district
        req_url = f'{self.base_url}/nf/object/geography/info/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取地理位置对象列表失败: {e}')
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

    def get_location_obj_id(self, page=1, size=10, name='', where='OR',
                            country=None, province=None, city=None, district=None):
        """按名称查询地理位置对象 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param name: 对象名称
        :type name: str
        :param where: 查询条件逻辑，``"OR"`` = 或，``"AND"`` = 与
        :type where: str
        :param country: 国家代码过滤
        :type country: str or None
        :param province: 省份代码过滤
        :type province: str or None
        :param city: 城市代码过滤
        :type city: str or None
        :param district: 区县代码过滤
        :type district: str or None
        :return: 成功返回对象 id，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_location_obj(page=page, size=size, name=name,
                                     where=where, country=country,
                                     province=province, city=city,
                                     district=district)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == name:
                return item.get('id')
        return False

    def remove_location_obj(self, obj_id):
        """删除地理位置对象。

        对应 UI 页面「对象 → 安全防护 → 地理位置」。

        :param obj_id: 对象 ID，可以是单个值或列表
        :type obj_id: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(obj_id, list):
            obj_ids = [int(item) for item in obj_id]
        elif isinstance(obj_id, (int, str)):
            obj_ids = [int(obj_id)]
        else:
            obj_ids = []
        data = {'id': obj_ids}
        req_url = f'{self.base_url}/nf/object/geography/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除地理位置对象失败: {e}')
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

    def get_location_detail(self, module='country', key=''):
        """获取地理位置详情（国家/省份/城市/区县联动数据）。

        对应 UI 页面「对象 → 安全防护 → 地理位置」。

        :param module: 模块类型，``"country"`` = 国家，``"province"`` = 省份，``"city"`` = 城市，``"district"`` = 区县
        :type module: str
        :param key: 上一级区域代码，查询子区域时必填（如查询省份时传入国家代码）
        :type key: str
        :return: 成功返回 API 响应字典（``result`` 包含区域列表），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/geography/detail_info/'
        params = {'module': module, 'key': key}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取地理位置详情失败: {e}')
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

    def get_global_location_config(self):
        """获取地理位置全局配置。

        对应 UI 页面「对象 → 安全防护 → 地理位置 → 全局配置」。

        :return: 成功返回 API 响应字典（``result.enable`` 为启用状态），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/geography/get_global_config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取地理位置全局配置失败: {e}')
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

    def global_config_switch(self, enable=True):
        """设置地理位置全局配置开关。

        对应 UI 页面「对象 → 安全防护 → 地理位置 → 全局配置」。

        :param enable: 是否启用地理位置功能，``True`` = 启用，``False`` = 禁用
        :type enable: bool
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'enable': enable}
        req_url = f'{self.base_url}/nf/object/geography/global_config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'设置地理位置全局配置失败: {e}')
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