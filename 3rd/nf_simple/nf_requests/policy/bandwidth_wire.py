"""带宽线路 — 带宽线路的增删查改。

对应 UI 页面「安全策略 → 流量管理 → 带宽线路」。

对应 API 文档中的 ``create_bwm_wire``、``update_bwm_wire``、``remove_bwm_wire``、
``get_bwm_wire``。
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


class BandwidthWireFeature(NFRequests):
    """带宽线路操作集合 — 带宽线路的增删查改。"""

    def create_bw_wire(self, name='test', total_up_stream_bandwidth=1000,
        total_down_stream_bandwidth=1000, up_stream_unit='Mbps',
        down_stream_unit='Mbps', comment=''):
        """创建带宽线路。

        对应 API 文档中的 ``create_bwm_wire``。

        :param name: 线路名称，默认 ``"test"``
        :type name: str
        :param total_up_stream_bandwidth: 上行总带宽，默认 ``1000``
        :type total_up_stream_bandwidth: int
        :param total_down_stream_bandwidth: 下行总带宽，默认 ``1000``
        :type total_down_stream_bandwidth: int
        :param up_stream_unit: 上行单位，默认 ``"Mbps"``
        :type up_stream_unit: str
        :param down_stream_unit: 下行单位，默认 ``"Mbps"``
        :type down_stream_unit: str
        :param comment: 备注
        :type comment: str
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        body = {'action': 'create', 'count': 1, 'tmWires': [{'name': name,
            'total_up_stream_bandwidth': total_up_stream_bandwidth,
            'total_down_stream_bandwidth': total_down_stream_bandwidth,
            'up_stream_unit': up_stream_unit, 'down_stream_unit':
            down_stream_unit, 'comment': comment}]}
        url = f'{self.base_url}/nf/strategy/bwm_wire/wire_create/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建带宽线路失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def update_bw_wire(self, wire_id, name='test', total_up_stream_bandwidth=
        1000, total_down_stream_bandwidth=1000, up_stream_unit='Mbps',
        down_stream_unit='Mbps', comment=''):
        """更新带宽线路。

        对应 API 文档中的 ``update_bwm_wire``。

        :param wire_id: 线路 ID
        :type wire_id: int
        :param name: 线路名称，默认 ``"test"``
        :type name: str
        :param total_up_stream_bandwidth: 上行总带宽，默认 ``1000``
        :type total_up_stream_bandwidth: int
        :param total_down_stream_bandwidth: 下行总带宽，默认 ``1000``
        :type total_down_stream_bandwidth: int
        :param up_stream_unit: 上行单位，默认 ``"Mbps"``
        :type up_stream_unit: str
        :param down_stream_unit: 下行单位，默认 ``"Mbps"``
        :type down_stream_unit: str
        :param comment: 备注
        :type comment: str
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        body = {'action': 'edit', 'id': wire_id, 'name': name,
            'total_up_stream_bandwidth': total_up_stream_bandwidth,
            'total_down_stream_bandwidth': total_down_stream_bandwidth,
            'up_stream_unit': up_stream_unit, 'down_stream_unit':
            down_stream_unit, 'comment': comment}
        url = f'{self.base_url}/nf/strategy/bwm_wire/wire_edit/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'更新带宽线路失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def delete_bw_wire(self, bw_wire_ids):
        """删除带宽管理线路。

        对应 API 文档中的 ``remove_bwm_wire``。

        :param bw_wire_ids: 带宽管理线路 ID，可为 ``int``、``str`` 或 ``list``
        :type bw_wire_ids: int or str or list
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        if isinstance(bw_wire_ids, list):
            bw_wire_ids = ','.join(str(wire_id) for wire_id in bw_wire_ids)
        elif isinstance(bw_wire_ids, int):
            bw_wire_ids = str(bw_wire_ids)
        body = {'id': bw_wire_ids}
        url = f'{self.base_url}/nf/strategy/bwm_wire/wire_delete/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除带宽线路失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return True
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_bw_wire_info(self, size=10, page=1, search=''):
        """获取带宽线路列表。

        对应 API 文档中的 ``get_bwm_wire``。

        :param size: 每页数量，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索关键词
        :type search: str
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        params = {'page': page, 'size': size, 'search': search}
        url = f'{self.base_url}/nf/strategy/bwm_wire/wire_info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取带宽线路信息失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
