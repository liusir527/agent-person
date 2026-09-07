"""防火墙日志。

对应 UI 页面「日志管理 → 防火墙日志」。
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


class FirewallLogFeature(NFRequests):
    """防火墙日志操作集合。"""

    def search_fw_log(self, page=1, size=10, s_time=None, d_time=None, action=
        '', risk='', vsys_id='0', user='', module='', category='', comment='',
        app_name='', app_name_op='3', src_ip='', src_ip_op='3', src_port='',
        src_port_op='3', dst_ip='', dst_ip_op='3', dst_port='', dst_port_op='3',
        rule_id='', rule_id_op='3', protocol='', protocol_op='3', src_card='',
        src_card_op='3', dst_card='', dst_card_op='3', nat_src_ip='',
        nat_src_ip_op='3', nat_src_port='', nat_src_port_op='3', nat_dst_ip='',
        nat_dst_ip_op='3', nat_dst_port='', nat_dst_port_op='3', tb='', db='',
        offset=0, is_all=True, is_search=True, slice_start=0, slice_end=20,
        req_body=None):
        """查询防火墙日志。

        对应 UI 页面「日志管理 → 防火墙日志」。

        :param page: 页码，默认 1。
        :param size: 每页条数，默认 10。
        :param s_time: 查询起始时间（必填），格式如 ``"2024-01-01 00:00:00"``，
            ``None`` 时不上报该字段。
        :param d_time: 查询结束时间（必填），格式同 ``s_time``。
        :param action: 动作筛选（``"allow"``/``"deny"``）。
        :param risk: 风险等级筛选。
        :param vsys_id: 虚拟系统 ID，默认 ``"0"``。
        :param user: 用户筛选。
        :param module: 模块筛选。
        :param category: 分类筛选。
        :param comment: 备注筛选。
        :param app_name: 应用名称筛选。
        :param app_name_op: 应用名称匹配操作符，默认 ``"3"`` = 包含。
        :param src_ip: 源 IP 筛选。
        :param src_ip_op: 源 IP 匹配操作符，默认 ``"3"``。
        :param src_port: 源端口筛选。
        :param src_port_op: 源端口匹配操作符，默认 ``"3"``。
        :param dst_ip: 目的 IP 筛选。
        :param dst_ip_op: 目的 IP 匹配操作符，默认 ``"3"``。
        :param dst_port: 目的端口筛选。
        :param dst_port_op: 目的端口匹配操作符，默认 ``"3"``。
        :param rule_id: 规则 ID 筛选。
        :param rule_id_op: 规则 ID 匹配操作符，默认 ``"3"``。
        :param protocol: 协议筛选。
        :param protocol_op: 协议匹配操作符，默认 ``"3"``。
        :param src_card: 源网卡筛选。
        :param src_card_op: 源网卡匹配操作符，默认 ``"3"``。
        :param dst_card: 目的网卡筛选。
        :param dst_card_op: 目的网卡匹配操作符，默认 ``"3"``。
        :param nat_src_ip: NAT 源 IP 筛选。
        :param nat_src_ip_op: NAT 源 IP 匹配操作符，默认 ``"3"``。
        :param nat_src_port: NAT 源端口筛选。
        :param nat_src_port_op: NAT 源端口匹配操作符，默认 ``"3"``。
        :param nat_dst_ip: NAT 目的 IP 筛选。
        :param nat_dst_ip_op: NAT 目的 IP 匹配操作符，默认 ``"3"``。
        :param nat_dst_port: NAT 目的端口筛选。
        :param nat_dst_port_op: NAT 目的端口匹配操作符，默认 ``"3"``。
        :param tb: 数据表名筛选。
        :param db: 数据库名筛选。
        :param offset: 偏移量，默认 0。
        :param is_all: 是否全量查询，默认 ``True``。
        :param is_search: 是否查询模式，默认 ``True``。
        :param slice_start: 分片起始索引，默认 0。
        :param slice_end: 分片结束索引，默认 20。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。

        .. note::
            ``s_time`` 和 ``d_time`` 参数不能为 ``None``，否则后端接口会报错。
            操作符值含义：``"0"`` = 等于，``"1"`` = 不等于，``"2"`` = 大于，
            ``"3"`` = 包含，``"4"`` = 小于。
        """
        data = {'page': page, 'size': size, 's_time': s_time, 'd_time': d_time,
            'risk': risk, 'action': action, 'vsysid': vsys_id, 'user': user,
            'module': module, 'category': category, 'comment': comment,
            'app_name': app_name, 'app_nameOp': app_name_op, 'src_ip': src_ip,
            'src_ipOp': src_ip_op, 'src_port': src_port, 'src_portOp':
            src_port_op, 'dst_ip': dst_ip, 'dst_ipOp': dst_ip_op, 'dst_port':
            dst_port, 'dst_portOp': dst_port_op, 'rule_id': rule_id,
            'rule_idOp': rule_id_op, 'protocol': protocol, 'protocolOp':
            protocol_op, 'src_card': src_card, 'src_cardOp': src_card_op,
            'dst_card': dst_card, 'dst_cardOp': dst_card_op, 'nat_src_ip':
            nat_src_ip, 'nat_src_ipOp': nat_src_ip_op, 'nat_src_port':
            nat_src_port, 'nat_src_portOp': nat_src_port_op, 'nat_dst_ip':
            nat_dst_ip, 'nat_dst_ipOp': nat_dst_ip_op, 'nat_dst_port':
            nat_dst_port, 'nat_dst_portOp': nat_dst_port_op, 'tb': tb, 'db': db,
            'offset': offset, 'isAll': is_all, 'isSearch': is_search,
            'sliceStart': slice_start, 'sliceEnd': slice_end}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/log/firewall/info/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'查询防火墙日志失败: {e}')
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

    def get_fw_log_result(self):
        """获取防火墙日志缓存结果。

        对应 UI 页面「日志管理 → 防火墙日志」。

        在调用 [`search_fw_log()`](firewall_log.py) 后使用此方法获取已缓存的查询结果。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/log/firewall/result/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取防火墙日志缓存结果失败: {e}')
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

    def export_fw_log(self, req_body):
        """导出防火墙日志。

        对应 UI 页面「日志管理 → 防火墙日志」。

        :param req_body: 请求体 dict，格式与
            [`search_fw_log()`](firewall_log.py) 的参数一致，通过 ``data`` 而非 ``json`` 发送。
        :return: 成功返回导出的文件内容（bytes）；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/log/firewall/export_log/'
        try:
            result = self.session.post(req_url, data=json.dumps(req_body),
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出防火墙日志失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出防火墙日志成功')
            return result.content
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_fw_log_dashboard(self):
        """获取防火墙日志仪表板数据。

        对应 UI 页面「日志管理 → 防火墙日志 → 仪表板」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/log/firewall/get_log_dashboard/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取防火墙日志仪表板数据失败: {e}')
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
