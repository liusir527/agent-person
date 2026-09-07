"""HA 实例/Track 删除 — HA 实例和 Track 条目的删除操作。

对应 UI 页面「高可用 → 双机热备」。
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


class HaInstanceTrackFeature(NFRequests):
    """HA 实例/Track 删除操作集合 — HA 实例和 Track 条目的删除。"""

    def ha_delete_instance(self, index='1', interface='G1/1', vip='', vrid='1',
        req_body=None):
        """删除 HA 实例。

        对应 API 文档中的 ``remove_ha_instance``。

        :param index: HA 实例 ID，默认 ``"1"``
        :type index: str
        :param interface: HA 接口，默认 ``"G1/1"``
        :type interface: str
        :param vip: HA 虚拟 IP，默认 ``""``
        :type vip: str
        :param vrid: HA VRID，默认 ``"1"``
        :type vrid: str
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'id': index, 'interface': interface, 'vip': vip, 'vrid': vrid}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/delete_instance/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除HA实例失败: {e}')
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

    def ha_delete_track(self, index='1', track_name='G1/1', req_body=None):
        """删除 HA Track。

        对应 API 文档中的 ``remove_ha_track``。

        :param index: HA Track ID，默认 ``"1"``
        :type index: str
        :param track_name: Track 名称，默认 ``"G1/1"``
        :type track_name: str
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :type req_body: dict or None
        :return: 成功返回完整响应 dict；失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'id': index, 'track_name': track_name}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/delete_track/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除HA track失败: {e}')
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
