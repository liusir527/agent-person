"""审计日志。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class AuditLogFeature(NFRequests):
    """审计日志操作集合。"""

    def get_audit_log(self, page=1, size=10, s_time=-1, d_time=-1, source_ip='',
        source_ip_op='1', status='true', account_name='', account_name_op='1',
        module='', description='', description_op='1', vsys='', req_body=None,
        source_ipOp=None, account_nameOp=None, descriptionOp=None):
        """
        获取审计日志，对应 ``GET /nf/audit/log/info/``。

        OpenAPI 查询参数: ``page``, ``size``, ``s_time``, ``d_time``,
        ``source_ip``, ``source_ipOp``, ``status``, ``account_name``,
        ``account_nameOp``, ``module``, ``description``, ``descriptionOp``,
        ``vsys``。
        OpenAPI 必填查询参数: ``page``, ``size``, ``s_time``, ``d_time``。
        兼容参数 ``source_ip_op``、``account_name_op``、``description_op`` 会分别映射为
        OpenAPI 字段 ``source_ipOp``、``account_nameOp``、``descriptionOp``。
        :param page: 页码，默认 1
        :param size: 每页数量，默认 10
        :param s_time: 开始时间，默认 -1
        :param d_time: 结束时间，默认 -1
        :param source_ip: 源IP过滤条件
        :param source_ip_op: 兼容旧调用的源IP匹配操作符
        :param source_ipOp: OpenAPI 源IP匹配操作符，优先于 ``source_ip_op``
        :param status: 状态过滤条件
        :param account_name: 账号名过滤条件
        :param account_name_op: 兼容旧调用的账号名匹配操作符
        :param account_nameOp: OpenAPI 账号名匹配操作符，优先于 ``account_name_op``
        :param module: 模块过滤条件
        :param description: 描述过滤条件
        :param description_op: 兼容旧调用的描述匹配操作符
        :param descriptionOp: OpenAPI 描述匹配操作符，优先于 ``description_op``
        :param vsys: 虚拟系统过滤条件
        :param req_body: 兼容旧调用的自定义参数字典，传入后优先使用为查询参数
        :return:
        """
        source_ip_op = source_ipOp if source_ipOp is not None else source_ip_op
        account_name_op = account_nameOp if account_nameOp is not None else account_name_op
        description_op = descriptionOp if descriptionOp is not None else description_op
        params = {'page': page, 'size': size, 's_time': s_time, 'd_time': d_time,
            'source_ip': source_ip, 'source_ipOp': source_ip_op, 'account_name':
            account_name, 'account_nameOp': account_name_op, 'module': module,
            'description': description, 'descriptionOp': description_op, 'vsys':
            vsys, 'status': status}
        if req_body is not None:
            params = req_body
        req_url = f'{self.base_url}/nf/audit/log/info/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取审计日志失败: {e}')
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
