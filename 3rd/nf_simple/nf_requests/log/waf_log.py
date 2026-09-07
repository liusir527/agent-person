"""WAF 日志 — WAF（Web 应用防火墙）事件的日志查询。

对应 UI 页面「日志与报表 → WAF 日志」。
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


class WafLogFeature(NFRequests):
    """WAF 日志操作集合 — WAF 事件的日志查询。"""

    def get_waf_log(self, page=1, size=10, s_time=None, d_time=None, waf_type=
        '', rule_id='', rule_name='', src_ip='', src_mac='', src_port='',
        dst_ip='', dst_mac='', dst_port='', action='', protection_type='',
        threat_level='', exact=True, trace=False, rule_name_op='3', src_ip_op=
        '3', src_mac_op='3', src_port_op='3', dst_ip_op='3', dst_mac_op='3',
        dst_port_op='3', rule_id_op='3', trace_source='', trace_source_op='3',
        url='', url_op='3', description='', description_op='3', req_body=None):
        """查询 WAF 日志。

        对应 API 文档中的 ``search_waf_log``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param s_time: 开始时间（时间戳，必填）
        :type s_time: int
        :param d_time: 结束时间（时间戳，必填）
        :type d_time: int
        :param waf_type: WAF 类型过滤
        :type waf_type: str
        :param rule_id: 规则 ID 过滤
        :type rule_id: str
        :param rule_name: 规则名称过滤
        :type rule_name: str
        :param src_ip: 源 IP 过滤
        :type src_ip: str
        :param src_mac: 源 MAC 过滤
        :type src_mac: str
        :param src_port: 源端口过滤
        :type src_port: str
        :param dst_ip: 目的 IP 过滤
        :type dst_ip: str
        :param dst_mac: 目的 MAC 过滤
        :type dst_mac: str
        :param dst_port: 目的端口过滤
        :type dst_port: str
        :param action: 动作过滤
        :type action: str
        :param protection_type: 防护类型过滤
        :type protection_type: str
        :param threat_level: 威胁等级过滤
        :type threat_level: str
        :param exact: 是否精确匹配，默认 ``True``
        :type exact: bool
        :param trace: 是否追踪，默认 ``False``
        :type trace: bool
        :param rule_name_op: 规则名称匹配运算符，默认 ``'3'``（模糊匹配）
        :type rule_name_op: str
        :param src_ip_op: 源 IP 匹配运算符，默认 ``'3'``
        :type src_ip_op: str
        :param src_mac_op: 源 MAC 匹配运算符，默认 ``'3'``
        :type src_mac_op: str
        :param src_port_op: 源端口匹配运算符，默认 ``'3'``
        :type src_port_op: str
        :param dst_ip_op: 目的 IP 匹配运算符，默认 ``'3'``
        :type dst_ip_op: str
        :param dst_mac_op: 目的 MAC 匹配运算符，默认 ``'3'``
        :type dst_mac_op: str
        :param dst_port_op: 目的端口匹配运算符，默认 ``'3'``
        :type dst_port_op: str
        :param rule_id_op: 规则 ID 匹配运算符，默认 ``'3'``
        :type rule_id_op: str
        :param trace_source: 追踪源过滤
        :type trace_source: str
        :param trace_source_op: 追踪源匹配运算符，默认 ``'3'``
        :type trace_source_op: str
        :param url: URL 过滤
        :type url: str
        :param url_op: URL 匹配运算符，默认 ``'3'``
        :type url_op: str
        :param description: 描述过滤
        :type description: str
        :param description_op: 描述匹配运算符，默认 ``'3'``
        :type description_op: str
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'page': int(page), 'size': int(size), 's_time': s_time,
            'd_time': d_time, 'type': waf_type, 'rule_id': rule_id, 'rule_name':
            rule_name, 'src_ip': src_ip, 'src_mac': src_mac, 'src_port':
            src_port, 'dst_ip': dst_ip, 'dst_mac': dst_mac, 'dst_port':
            dst_port, 'action': action, 'protection_type': protection_type,
            'threat_level': threat_level, 'exact': exact, 'trace': trace,
            'rule_nameOp': rule_name_op, 'src_ipOp': src_ip_op, 'src_macOp':
            src_mac_op, 'src_portOp': src_port_op, 'dst_ipOp': dst_ip_op,
            'dst_macOp': dst_mac_op, 'dst_portOp': dst_port_op, 'rule_idOp':
            rule_id_op, 'trace_source': trace_source, 'trace_sourceOp':
            trace_source_op, 'url': url, 'urlOp': url_op, 'description':
            description, 'descriptionOp': description_op}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/waf/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取WAF日志信息失败: {e}')
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
