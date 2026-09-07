"""配置应用。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class ApplyFeature(NFRequests):
    """配置应用操作集合。"""

    def apply_config(self):
        """
        应用所有配置
        :param session: requests Session对象
        :return:
        """
        url = f'{self.base_url}/nf/strategy/nat/application/'
        data = {}
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'应用配置失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return True
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def apply_config_isp_route(self):
        """
        应用ISP路由配置
        :param session: requests Session对象
        :return:
        """
        url = f'{self.base_url}/nf/network/route/policy/application/'
        try:
            result = self.session.post(url, data=json.dumps({}), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'应用ISP路由配置失败: {e}')
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
