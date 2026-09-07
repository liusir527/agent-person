"""运行日志。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class RunningLogFeature(NFRequests):
    """运行日志操作集合。"""

    def search_running_log(self, page=1, size=10, s_time=None, d_time=None,
        level='', module='', log_type='', content='', content_op='3', req_body=None
        ):
        """
        查询运行日志
        :param session: requests Session对象
        :param req_body: 自定义请求体
        :return:
        """
        data = {'page': page, 'size': size, 's_time': s_time, 'd_time': d_time,
            'level': level, 'module': module, 'type': log_type, 'content':
            content, 'contentOp': content_op}
        if module != '':
            data['moduleOp'] = '1'
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/run/netrun/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'查询运行日志失败: {e}')
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
