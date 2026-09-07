"""带宽管理策略 — 带宽策略的增删查改、导入和导出。

对应 UI 页面「安全策略 → 流量管理」。

对应 API 文档中的 ``create_bwm_policy``、``update_bwm_policy``、``remove_bwm_policy``、
``get_bwm_policy``、``upload_bwm_policy``、``export_bwm_policy``。
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


class BandwidthPolicyFeature(NFRequests):
    """带宽管理策略操作集合 — 带宽策略的增删查改、导入和导出。"""

    def create_bw_policy(self, name='test1', channel_id=1, wire_id=1, is_tm=0,
        src_zone_type=None, dst_zone_type=None, src_ip_addr=None, dst_ip_addr=
        None, time_id=None, app_id=None, service_id=None, disable=0, is_per_ip=
        0, ipv6_enable=0, comment='', priority=0, any_net_id=100000,
        any_ipv6_net_id=119999, any_time_id=800000, any_srv_id=600000):
        """创建带宽策略。

        对应 API 文档中的 ``create_bwm_policy``。

        :param name: 策略名称，默认 ``"test1"``
        :type name: str
        :param channel_id: 通道 ID，默认 ``1``
        :type channel_id: int
        :param wire_id: 线路 ID，默认 ``1``
        :type wire_id: int
        :param is_tm: 是否为 TM，默认 ``0``
        :type is_tm: int
        :param src_zone_type: 源安全区类型，可为 ``str`` / ``list``，默认 ``"TRUST"``
        :type src_zone_type: str or list or None
        :param dst_zone_type: 目的安全区类型，可为 ``str`` / ``list``，默认 ``"TRUST"``
        :type dst_zone_type: str or list or None
        :param src_ip_addr: 源地址 ID，可为 ``str`` / ``list``
        :type src_ip_addr: str or list or None
        :param dst_ip_addr: 目的地址 ID，可为 ``str`` / ``list``
        :type dst_ip_addr: str or list or None
        :param time_id: 时间对象 ID，可为 ``str`` / ``list``
        :type time_id: str or list or None
        :param app_id: 应用 ID，可为 ``str`` / ``list``
        :type app_id: str or list or None
        :param service_id: 服务对象 ID，可为 ``str`` / ``list``
        :type service_id: str or list or None
        :param disable: 是否禁用，``0``（启用）或 ``1``（禁用）
        :type disable: int
        :param is_per_ip: 是否每 IP，``0`` 或 ``1``
        :type is_per_ip: int
        :param ipv6_enable: 是否启用 IPv6，``0`` 或 ``1``
        :type ipv6_enable: int
        :param comment: 备注
        :type comment: str
        :param priority: 优先级
        :type priority: int
        :param any_net_id: 任意 IPv4 网络 ID，默认 ``100000``
        :type any_net_id: int
        :param any_ipv6_net_id: 任意 IPv6 网络 ID，默认 ``119999``
        :type any_ipv6_net_id: int
        :param any_time_id: 任意时间对象 ID，默认 ``800000``
        :type any_time_id: int
        :param any_srv_id: 任意服务对象 ID，默认 ``600000``
        :type any_srv_id: int
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(src_zone_type, (str, int)):
            src_zone_type = [str(src_zone_type)]
        elif src_zone_type is None:
            src_zone_type = ['TRUST']
        if isinstance(dst_zone_type, (str, int)):
            dst_zone_type = [str(dst_zone_type)]
        elif dst_zone_type is None:
            dst_zone_type = ['TRUST']
        if isinstance(src_ip_addr, (str, int)):
            src_ip_addr = [str(src_ip_addr)]
        elif isinstance(src_ip_addr, list):
            src_ip_addr = [str(x) for x in src_ip_addr]
        elif src_ip_addr is None:
            if ipv6_enable:
                src_ip_addr = [str(any_ipv6_net_id)]
            else:
                src_ip_addr = [str(any_net_id)]
        if isinstance(dst_ip_addr, (str, int)):
            dst_ip_addr = [str(dst_ip_addr)]
        elif isinstance(dst_ip_addr, list):
            dst_ip_addr = [str(x) for x in dst_ip_addr]
        elif dst_ip_addr is None:
            if ipv6_enable:
                dst_ip_addr = [str(any_ipv6_net_id)]
            else:
                dst_ip_addr = [str(any_net_id)]
        if isinstance(time_id, (str, int)):
            time_id = [str(time_id)]
        elif isinstance(time_id, list):
            time_id = [str(x) for x in time_id]
        elif time_id is None:
            time_id = [str(any_time_id)]
        if isinstance(app_id, (str, int)):
            app_id = [str(app_id)]
        elif isinstance(app_id, list):
            app_id = [str(x) for x in app_id]
        elif app_id is None:
            app_id = ['0']
        if isinstance(service_id, (str, int)):
            service_id = [str(service_id)]
        elif isinstance(service_id, list):
            service_id = [str(x) for x in service_id]
        elif service_id is None:
            service_id = [str(any_srv_id)]
        tm_policy = {'name': name, 'channel_id': channel_id, 'wire_id': wire_id,
            'is_tm': is_tm, 'src_zone_type': src_zone_type, 'dst_zone_type':
            dst_zone_type, 'src_ip_addr': src_ip_addr, 'dst_ip_addr':
            dst_ip_addr, 'time_id': time_id, 'app_id': app_id, 'service_id':
            service_id, 'disable': disable, 'is_per_ip': is_per_ip,
            'ipv6Enable': ipv6_enable, 'comment': comment, 'priority': priority}
        body = {'action': 'create', 'count': 1, 'tmPolicys': [tm_policy]}
        url = f'{self.base_url}/nf/strategy/bwm/bwm_create/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建带宽策略失败: {e}')
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

    def update_bw_policy(self, policy_id, name='test1', channel_id=1, wire_id=1,
        is_tm=0, src_zone_type=None, dst_zone_type=None, src_ip_addr=None,
        dst_ip_addr=None, time_id=None, app_id=None, service_id=None, disable=0,
        is_per_ip=0, ipv6_enable=0, comment='', priority=0, any_net_id=100000,
        any_ipv6_net_id=119999, any_time_id=800000, any_srv_id=600000):
        """更新带宽策略。

        对应 API 文档中的 ``update_bwm_policy``。

        :param policy_id: 策略 ID
        :type policy_id: int
        :param name: 策略名称，默认 ``"test1"``
        :type name: str
        :param channel_id: 通道 ID，默认 ``1``
        :type channel_id: int
        :param wire_id: 线路 ID，默认 ``1``
        :type wire_id: int
        :param is_tm: 是否为 TM，默认 ``0``
        :type is_tm: int
        :param src_zone_type: 源安全区类型，可为 ``str`` / ``list``
        :type src_zone_type: str or list or None
        :param dst_zone_type: 目的安全区类型，可为 ``str`` / ``list``
        :type dst_zone_type: str or list or None
        :param src_ip_addr: 源地址 ID，可为 ``str`` / ``list``
        :type src_ip_addr: str or list or None
        :param dst_ip_addr: 目的地址 ID，可为 ``str`` / ``list``
        :type dst_ip_addr: str or list or None
        :param time_id: 时间对象 ID，可为 ``str`` / ``list``
        :type time_id: str or list or None
        :param app_id: 应用 ID，可为 ``str`` / ``list``
        :type app_id: str or list or None
        :param service_id: 服务对象 ID，可为 ``str`` / ``list``
        :type service_id: str or list or None
        :param disable: 是否禁用，``0``（启用）或 ``1``（禁用）
        :type disable: int
        :param is_per_ip: 是否每 IP，``0`` 或 ``1``
        :type is_per_ip: int
        :param ipv6_enable: 是否启用 IPv6，``0`` 或 ``1``
        :type ipv6_enable: int
        :param comment: 备注
        :type comment: str
        :param priority: 优先级
        :type priority: int
        :param any_net_id: 任意 IPv4 网络 ID，默认 ``100000``
        :type any_net_id: int
        :param any_ipv6_net_id: 任意 IPv6 网络 ID，默认 ``119999``
        :type any_ipv6_net_id: int
        :param any_time_id: 任意时间对象 ID，默认 ``800000``
        :type any_time_id: int
        :param any_srv_id: 任意服务对象 ID，默认 ``600000``
        :type any_srv_id: int
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(src_zone_type, (str, int)):
            src_zone_type = [str(src_zone_type)]
        elif src_zone_type is None:
            src_zone_type = ['TRUST']
        if isinstance(dst_zone_type, (str, int)):
            dst_zone_type = [str(dst_zone_type)]
        elif dst_zone_type is None:
            dst_zone_type = ['TRUST']
        if isinstance(src_ip_addr, (str, int)):
            src_ip_addr = [str(src_ip_addr)]
        elif isinstance(src_ip_addr, list):
            src_ip_addr = [str(x) for x in src_ip_addr]
        elif src_ip_addr is None:
            if ipv6_enable:
                src_ip_addr = [str(any_ipv6_net_id)]
            else:
                src_ip_addr = [str(any_net_id)]
        if isinstance(dst_ip_addr, (str, int)):
            dst_ip_addr = [str(dst_ip_addr)]
        elif isinstance(dst_ip_addr, list):
            dst_ip_addr = [str(x) for x in dst_ip_addr]
        elif dst_ip_addr is None:
            if ipv6_enable:
                dst_ip_addr = [str(any_ipv6_net_id)]
            else:
                dst_ip_addr = [str(any_net_id)]
        if isinstance(time_id, (str, int)):
            time_id = [str(time_id)]
        elif isinstance(time_id, list):
            time_id = [str(x) for x in time_id]
        elif time_id is None:
            time_id = [str(any_time_id)]
        if isinstance(app_id, (str, int)):
            app_id = [str(app_id)]
        elif isinstance(app_id, list):
            app_id = [str(x) for x in app_id]
        elif app_id is None:
            app_id = ['0']
        if isinstance(service_id, (str, int)):
            service_id = [str(service_id)]
        elif isinstance(service_id, list):
            service_id = [str(x) for x in service_id]
        elif service_id is None:
            service_id = [str(any_srv_id)]
        body = {'action': 'edit', 'id': policy_id, 'name': name, 'channel_id':
            channel_id, 'wire_id': wire_id, 'is_tm': is_tm, 'src_zone_type':
            src_zone_type, 'dst_zone_type': dst_zone_type, 'src_ip_addr':
            src_ip_addr, 'dst_ip_addr': dst_ip_addr, 'time_id': time_id,
            'app_id': app_id, 'service_id': service_id, 'disable': disable,
            'is_per_ip': is_per_ip, 'ipv6Enable': ipv6_enable, 'comment':
            comment, 'priority': priority}
        url = f'{self.base_url}/nf/strategy/bwm/bwm_edit/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'更新带宽策略失败: {e}')
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

    def delete_bw_policy(self, bw_policy_ids):
        """删除带宽管理策略。

        对应 API 文档中的 ``remove_bwm_policy``。

        :param bw_policy_ids: 带宽管理策略 ID，可为 ``int``、``str`` 或 ``list``
        :type bw_policy_ids: int or str or list
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        if isinstance(bw_policy_ids, list):
            bw_policy_ids = ','.join(str(policy_id) for policy_id in bw_policy_ids)
        elif isinstance(bw_policy_ids, int):
            bw_policy_ids = str(bw_policy_ids)
        body = {'ids': bw_policy_ids}
        url = f'{self.base_url}/nf/strategy/bwm/bwm_delete/'
        try:
            result = self.session.post(url, data=json.dumps(body), verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除带宽策略失败: {e}')
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

    def get_bw_policy(self, size=10, page=1, search='', is_v6=''):
        """获取带宽策略列表。

        对应 API 文档中的 ``get_bwm_policy``。

        :param size: 每页数量，默认 ``10``
        :type size: int
        :param page: 页码，默认 ``1``
        :type page: int
        :param search: 搜索关键词
        :type search: str
        :param is_v6: IPv6 标志
        :type is_v6: str
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        params = {'page': page, 'size': size, 'search': search, 'is_v6': is_v6}
        url = f'{self.base_url}/nf/strategy/bwm/bwm_info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取带宽策略信息失败: {e}')
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

    def import_bw_policy(self, file_path):
        """导入带宽策略（multipart/form-data 文件上传）。

        对应 API 文档中的 ``upload_bwm_policy``。

        :param file_path: CSV 文件路径
        :type file_path: str
        :return: 成功返回 True，失败返回 False
        :rtype: bool
        """
        url = f'{self.base_url}/nf/strategy/bwm/upload/'
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.split('/')[-1], f, 'text/csv')}
                self.session.headers.update({'X-csrftoken': self.session.
                    cookies['csrftoken_vpp']})
                result = self.session.post(url, files=files, verify=False,
                    timeout=30)
        except Exception as e:
            logger.error(f'导入带宽策略失败: {e}')
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

    def export_bw_policy(self):
        """导出带宽策略。

        对应 API 文档中的 ``export_bwm_policy``。

        :return: 成功返回导出内容（bytes），失败返回 False
        :rtype: bytes or bool
        """
        url = f'{self.base_url}/nf/strategy/bwm/export/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出带宽策略失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出带宽策略成功')
            return result.content
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
