"""连通性测试。"""

import sys
import requests
import json
import os
import base64
import logging

from ..nflib.Log import logger
from ..nflib.comm import *
from ..client import NFRequests


class ConnectivityFeature(NFRequests):
    """连通性测试操作集合。"""

    def ping_config(self, status):
        """
        开启或关闭 ping 访问控制
        :param session: requests Session对象
        :param status: on/off
        :param req_body: 自定义请求体
        :return:
        """
        data = {'ping': status}
        req_url = f'{self.base_url}/nf/system/ping_config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'设置ping访问控制失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            logger.info(f'全局ping：{status}成功')
            return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}
