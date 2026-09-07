"""带宽通道 — 带宽通道的增删查改、导入和导出。

对应 UI 页面「安全策略 → 流量管理 → 带宽通道」。

对应 API 文档中的 ``create_bwm_channel``、``update_bwm_channel``、``remove_bwm_channel``、
``get_bwm_channel``、``upload_bwm_channel``、``export_bwm_channel``。
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


class BandwidthChannelFeature(NFRequests):
    """带宽通道操作集合 — 带宽通道的增删查改、导入和导出。"""

    def create_bw_channel(self, name='test', priority=7, cir_up_stream=1,
        cir_down_stream=1, cir_up_stream_unit='Kbps', cir_down_stream_unit=
        'Kbps', pir_up_stream=1000, pir_down_stream=1000, pir_up_stream_unit=
        'Mbps', pir_down_stream_unit='Mbps', comment=''):
        """创建带宽通道。

        对应 API 文档中的 ``create_bwm_channel``。

        :param name: 通道名称，默认 ``"test"``
        :type name: str
        :param priority: 优先级，默认 ``7``
        :type priority: int
        :param cir_up_stream: 上行 CIR，默认 ``1``
        :type cir_up_stream: int
        :param cir_down_stream: 下行 CIR，默认 ``1``
        :type cir_down_stream: int
        :param cir_up_stream_unit: 上行 CIR 单位，默认 ``"Kbps"``
        :type cir_up_stream_unit: str
        :param cir_down_stream_unit: 下行 CIR 单位，默认 ``"Kbps"``
        :type cir_down_stream_unit: str
        :param pir_up_stream: 上行 PIR，默认 ``1000``
        :type pir_up_stream: int
        :param pir_down_stream: 下行 PIR，默认 ``1000``
        :type pir_down_stream: int
        :param pir_up_stream_unit: 上行 PIR 单位，默认 ``"Mbps"``
        :type pir_up_stream_unit: str
        :param pir_down_stream_unit: 下行 PIR 单位，默认 ``"Mbps"``
        :type pir_down_stream_unit: str
        :param comment: 备注
        :type comment: str
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        body = {'action': 'create', 'count': 1, 'tmChannels': [{'name': name,
            'priority': priority, 'cir_up_stream': cir_up_stream,
            'cir_up_stream_unit': cir_up_stream_unit, 'cir_down_stream':
            cir_down_stream, 'cir_down_stream_unit': cir_down_stream_unit,
            'pir_up_stream': pir_up_stream, 'pir_down_stream': pir_down_stream,
            'pir_up_stream_unit': pir_up_stream_unit, 'pir_down_stream_unit':
            pir_down_stream_unit, 'comment': comment}]}
        url = f'{self.base_url}/nf/strategy/bwm_channel/channel_create/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建带宽通道失败: {e}')
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

    def update_bw_channel(self, channel_id, name='test', priority=7,
        cir_up_stream=1, cir_down_stream=1, cir_up_stream_unit='Kbps',
        cir_down_stream_unit='Kbps', pir_up_stream=1000, pir_down_stream=1000,
        pir_up_stream_unit='Mbps', pir_down_stream_unit='Mbps', comment=''):
        """更新带宽通道。

        对应 API 文档中的 ``update_bwm_channel``。

        :param channel_id: 通道 ID
        :type channel_id: int
        :param name: 通道名称，默认 ``"test"``
        :type name: str
        :param priority: 优先级，默认 ``7``
        :type priority: int
        :param cir_up_stream: 上行 CIR，默认 ``1``
        :type cir_up_stream: int
        :param cir_down_stream: 下行 CIR，默认 ``1``
        :type cir_down_stream: int
        :param cir_up_stream_unit: 上行 CIR 单位，默认 ``"Kbps"``
        :type cir_up_stream_unit: str
        :param cir_down_stream_unit: 下行 CIR 单位，默认 ``"Kbps"``
        :type cir_down_stream_unit: str
        :param pir_up_stream: 上行 PIR，默认 ``1000``
        :type pir_up_stream: int
        :param pir_down_stream: 下行 PIR，默认 ``1000``
        :type pir_down_stream: int
        :param pir_up_stream_unit: 上行 PIR 单位，默认 ``"Mbps"``
        :type pir_up_stream_unit: str
        :param pir_down_stream_unit: 下行 PIR 单位，默认 ``"Mbps"``
        :type pir_down_stream_unit: str
        :param comment: 备注
        :type comment: str
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        body = {'action': 'edit', 'id': channel_id, 'name': name, 'priority':
            priority, 'cir_up_stream': cir_up_stream, 'cir_up_stream_unit':
            cir_up_stream_unit, 'cir_down_stream': cir_down_stream,
            'cir_down_stream_unit': cir_down_stream_unit, 'pir_up_stream':
            pir_up_stream, 'pir_down_stream': pir_down_stream,
            'pir_up_stream_unit': pir_up_stream_unit, 'pir_down_stream_unit':
            pir_down_stream_unit, 'comment': comment}
        url = f'{self.base_url}/nf/strategy/bwm_channel/channel_edit/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'更新带宽通道失败: {e}')
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

    def delete_bw_channel(self, bw_channel_ids):
        """删除带宽管理通道。

        对应 API 文档中的 ``remove_bwm_channel``。

        :param bw_channel_ids: 带宽管理通道 ID，可为 ``int``、``str`` 或 ``list``
        :type bw_channel_ids: int or str or list
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        if isinstance(bw_channel_ids, list):
            bw_channel_ids = ','.join(str(channel_id) for channel_id in
                bw_channel_ids)
        elif isinstance(bw_channel_ids, int):
            bw_channel_ids = str(bw_channel_ids)
        body = {'ids': bw_channel_ids}
        url = f'{self.base_url}/nf/strategy/bwm_channel/channel_delete/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除带宽通道失败: {e}')
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

    def get_bw_channel_info(self, size=10, page=1, search=''):
        """获取带宽通道列表。

        对应 API 文档中的 ``get_bwm_channel``。

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
        url = f'{self.base_url}/nf/strategy/bwm_channel/channel_info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取带宽通道信息失败: {e}')
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

    def import_bw_channel(self, file_path):
        """导入带宽通道（multipart/form-data 文件上传）。

        对应 API 文档中的 ``upload_bwm_channel``。

        :param file_path: CSV 文件路径
        :type file_path: str
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        url = f'{self.base_url}/nf/strategy/bwm_channel/upload/'
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.split('/')[-1], f, 'text/csv')}
                self.session.headers.update({'X-csrftoken': self.session.
                    cookies['csrftoken_vpp']})
                result = self.session.post(url, files=files, verify=False,
                    timeout=30)
        except Exception as e:
            logger.error(f'导入带宽通道失败: {e}')
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

    def export_bw_channel(self):
        """导出带宽通道。

        对应 API 文档中的 ``export_bwm_channel``。

        :return: 成功返回导出内容（bytes），失败返回 False
        :rtype: bytes or bool
        """
        url = f'{self.base_url}/nf/strategy/bwm_channel/export/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出带宽通道失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出带宽通道成功')
            return result.content
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
