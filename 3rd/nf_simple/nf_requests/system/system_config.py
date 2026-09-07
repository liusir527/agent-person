"""主机与基础系统能力。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class SystemConfig(NFRequests):
    """主机与基础系统能力操作集合。"""

    def get_host_info(self):
        """获取系统总览信息。

        对应 UI 页面「全局概览 → 系统状态」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "mode": "单机",
                    "cpu_temperature": "45°C",
                    "cpu_utilization": "31.66%",
                    "disk_utilization": "0.3%",
                    "disk_size": "3667.302G",
                    "disk_employ": "10.702G",
                    "memory_utilization": "46.00%"
                }
        """
        req_url = f'{self.base_url}/nf/system/hostinfo/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取系统总览信息失败: {e}')
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

    def enable_huge_frame(self, status):
        """开启或关闭巨帧。

        对应 UI 页面「系统 → 系统配置 → 巨帧」。

        :param status: ``1`` = 开启，``0`` = 关闭
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'enable': status}
        req_url = f'{self.base_url}/nf/system/huge_frame/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'设置巨帧状态失败: {e}')
            return False
        if result.status_code == 200:
            status_code = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return json.loads(result.text)
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_huge_frame_status(self):
        """获取巨帧状态。

        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        req_url = f'{self.base_url}/nf/system/huge_frame/'
        try:
            result = self.session.post(req_url, data=json.dumps({}), verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'获取巨帧状态失败: {e}')
            return False
        if result.status_code == 200:
            status_code = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return json.loads(result.text)
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
    def change_dev_name(self,device_name,type="device_name"):
        '''
        修改设备名称
        device_name：设备名称
        '''

        req_url = f'{self.base_url}/nf/system/nfinfo/'

        data = {'type': type, 'device_name': device_name}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'NTP配置失败: {e}')
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
    def change_dev_location(self,device_location,type="device_location"):
        '''
        修改设备位置
        device_name：设备位置
        '''
        req_url = f'{self.base_url}/nf/system/nfinfo/'

        data = {'type': type, 'device_location': device_location}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'NTP配置失败: {e}')
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

    def change_dev_port(self,web_port,type="web_port"):
        '''
        修改设备登录端口
        device_name：登录端口
        '''

        req_url = f'{self.base_url}/nf/system/nfinfo/'

        data = {'type': type, 'web_port': web_port}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'NTP配置失败: {e}')
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

    def create_ntp_config(self, syncSwitch='on', ntpServer='ntp.baidu.com',
        syncInterval='3600', authSwitch='off', authAlgorithm='', file=''):
        """配置 NTP。

        对应 UI 页面「系统 → 系统配置 → NTP」。

        :param syncSwitch: NTP 同步开关，``"on"`` = 开启，``"off"`` = 关闭，默认
            ``"on"``
        :param ntpServer: NTP 服务器地址，默认 ``"ntp.baidu.com"``
        :param syncInterval: 同步间隔（秒），默认 ``"3600"``
        :param authSwitch: 认证开关，``"on"`` = 开启，``"off"`` = 关闭，默认
            ``"off"``
        :param authAlgorithm: 认证算法，默认 ``""``
        :param file: 认证文件，默认 ``""``
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        req_url = f'{self.base_url}/nf/system/ntp_config/'
        data = {'syncSwitch': syncSwitch, 'ntpServer': ntpServer,
            'syncInterval': syncInterval, 'authSwitch': authSwitch,
            'authAlgorithm': authAlgorithm, 'file': file}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'NTP配置失败: {e}')
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

    def get_ntp_config(self):
        """获取 NTP 配置。

        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "syncSwitch": "on",
                    "ntpServer": "ntp.aliyun.com",
                    "syncInterval": "3600",
                    "authSwitch": "off",
                    "authKeyPath": "/opt/nsfocus/product/etc/ntp/"
                }
        """
        req_url = f'{self.base_url}/nf/system/ntp_config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取NTP配置失败: {e}')
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

    def create_or_update_local_access_rule(self, action='create', protocol=
        'any', ip_type='ipv4', src_ip=None, dst_ip=None, src_port=None,
        dst_port=None, auth_policy='允许', rule_id=None, req_body=None, id=None):
        """创建或编辑本机访问规则。

        对应 UI 页面「系统 → 系统配置 → 本机访问规则」。

        .. note:: 该接口使用 GET 方法，参数通过查询字符串传递。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑，默认
            ``"create"``
        :param protocol: 协议，``"any"`` = 任意，``"tcp"`` = TCP，``"udp"`` =
            UDP，``"icmp"`` = ICMP，默认 ``"any"``
        :param ip_type: IP 类型，``"ipv4"`` 或 ``"ipv6"``，默认 ``"ipv4"``
        :param src_ip: 源 IP，如 ``"192.168.1.0/24"``，默认 ``"192.168.1.0/24"``。
            支持 ``list``（自动以逗号拼接）
        :param dst_ip: 目的 IP，如 ``"192.168.1.1"``，默认 ``"192.168.1.1"``。
            支持 ``list``（自动以逗号拼接）
        :param src_port: 源端口（非 any/icmp 时默认 ``"80"``）
        :param dst_port: 目的端口（非 any/icmp 时默认 ``"80"``）
        :param auth_policy: 动作，``"允许"`` = 允许，``"拒绝"`` = 拒绝，默认
            ``"允许"``
        :param rule_id: 兼容旧调用的规则 ID，会映射为 ``id`` 字段
        :param req_body: 自定义查询参数字典（传入后覆盖所有参数）
        :param id: 规则 ID 字段（编辑时必填），优先于 ``rule_id``
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        if src_ip is None:
            src_ip = '192.168.1.0/24'
        elif isinstance(src_ip, list):
            src_ip = ','.join(src_ip)
        if dst_ip is None:
            dst_ip = '192.168.1.1'
        elif isinstance(dst_ip, list):
            dst_ip = ','.join(dst_ip)
        if protocol not in ['any', 'icmp']:
            src_port = '80' if src_port is None else src_port
            dst_port = '80' if dst_port is None else dst_port
        else:
            src_port = dst_port = ''
        rule_id = id if id is not None else rule_id
        params = {'action': action, 'protocol': protocol, 'ip_type': ip_type,
            'src_ip': src_ip, 'dst_ip': dst_ip, 'src_port': src_port,
            'dst_port': dst_port, 'auth_policy': auth_policy}
        if rule_id is not None:
            params['id'] = rule_id
        if req_body is not None:
            params = req_body
        req_url = f'{self.base_url}/nf/system/access_rule/config/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'创建或更新本机访问规则失败: {e}')
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

    def remove_local_access_rule(self, rule_ids='1', req_param=None, ids=None):
        """删除本机访问规则。

        .. note:: 该接口使用 GET 方法，参数通过查询字符串传递。

        :param rule_ids: 兼容旧调用的规则 ID，多个以逗号分隔，支持 ``list``，
            默认 ``"1"``
        :param req_param: 自定义查询参数字典（传入后优先使用）
        :param ids: 规则 ID 字段，优先于 ``rule_ids``
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        rule_ids = ids if ids is not None else rule_ids
        if req_param is None:
            if isinstance(rule_ids, list):
                rule_ids = ','.join(map(str, rule_ids))
            params = {'ids': rule_ids}
        else:
            params = req_param
        req_url = f'{self.base_url}/nf/system/access_rule/delete/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'删除本机访问规则失败: {e}')
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

    def get_local_access_rule(self, size=10, page=1, search='', req_param=None):
        """获取本机访问规则列表。

        对应 UI 页面「系统 → 系统配置 → 本机访问规则」。

        :param size: 每页数量，默认 ``10``
        :param page: 页码，默认 ``1``
        :param search: 搜索关键字，默认 ``""``
        :param req_param: 自定义查询参数字典（传入后覆盖分页参数）
        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "total": 0,
                    "list": []
                }
        """
        params = {'size': size, 'page': page, 'search': search
            } if req_param is None else req_param
        req_url = f'{self.base_url}/nf/system/access_rule/info/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取本机访问规则列表失败: {e}')
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

    def clear_local_access_rule(self):
        """清空本机访问规则。

        .. note:: 该接口使用 GET 方法，无需参数。

        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        req_url = f'{self.base_url}/nf/system/access_rule/clear/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空本机访问规则失败: {e}')
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

    def update_alarm_config(self, conf_type='syslog_setting',
        first_ip='10.66.24.9', first_key='', first_port=514,
        sec_ip='0.0.0.0', sec_key='', sec_port=514,
        third_ip='0.0.0.0', third_key='', third_port=514,
        send_mode='0', log_module=None, req_body=None):
        """更新告警配置（syslog 服务器及日志模块）。

        对应 UI 页面「系统 → 系统配置 → 告警」。

        对应 API 文档中的 ``update_alarm_config``。

        send_mode 取值：
        - ``"0"`` — 自定义模块，需通过 log_module 指定发送哪些日志
        - ``"1"`` — 不发送
        - ``"2"`` / ``"3"`` — 其他预设模式

        log_module 可选值（``send_mode="0"`` 时生效）：
        ``app_event``（应用事件）、``ips_event``（IPS 事件）、
        ``av_event``（防病毒事件）、``netrun_event``（网络运行事件）、
        ``scmobm_event``（上网行为管理事件）、``scmmail_event``（邮件安全事件）、
        ``scmsensitive_event``（敏感数据事件）、``url_event``（URL 事件）

        :param conf_type: 配置类型，默认 ``"syslog_setting"``
        :type conf_type: str
        :param first_ip: 第一 syslog 服务器 IP
        :type first_ip: str
        :param first_key: 第一 syslog 密钥
        :type first_key: str
        :param first_port: 第一 syslog 端口
        :type first_port: int
        :param sec_ip: 第二 syslog 服务器 IP
        :type sec_ip: str
        :param sec_key: 第二 syslog 密钥
        :type sec_key: str
        :param sec_port: 第二 syslog 端口
        :type sec_port: int
        :param third_ip: 第三 syslog 服务器 IP
        :type third_ip: str
        :param third_key: 第三 syslog 密钥
        :type third_key: str
        :param third_port: 第三 syslog 端口
        :type third_port: int
        :param send_mode: 发送模式，``"0"``=自定义，``"1"``=不发送，``"2"``/``"3"``=预设
        :type send_mode: str
        :param log_module: 日志模块列表，仅 ``send_mode="0"`` 时生效，
            默认 ``None``（内部转为空列表）
        :type log_module: list[str] or None
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            modules = log_module if log_module is not None else []
            data = {
                'type': conf_type,
                'first_ip': first_ip,
                'first_key': first_key,
                'first_port': first_port,
                'sec_ip': sec_ip,
                'sec_key': sec_key,
                'sec_port': sec_port,
                'third_ip': third_ip,
                'third_key': third_key,
                'third_port': third_port,
                'send_mode': send_mode,
                'log_module': modules,
            }
        req_url = f'{self.base_url}/nf/system/alarmsetting/'
        try:
            result = self.session.post(req_url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新告警配置失败: {e}')
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

    def open_remoteinfo(self, enable="true", remote_ip="10.66.24.9", port=52001):
        """配置远程协助。

        对应 UI 页面「系统 → 系统配置 → 远程协助」。

        :param enable: 是否启用远程协助，``"true"`` = 启用，``"false"`` = 禁用，
            默认 ``"true"``
        :param remote_ip: 远程 IP 地址，默认 ``"10.66.24.9"``
        :param port: 远程端口，默认 ``52001``
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        req_url = f'{self.base_url}/nf/remote/remoteInfo/'
        data = {'enable': enable, "remote_ip": remote_ip, "port": port}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'远程协助开启失败: {e}')
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
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_remoteinfo(self):
        """获取远程协助信息。

        :return: 成功返回 ``(qrcode, remote_ip, port)`` 元组；失败返回 ``False``
        """
        req_url = f'{self.base_url}/nf/remote/remoteInfo/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取远程协助信息失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return (json.loads(result.text)["result"]["qrcode"],
                    json.loads(result.text)["result"]["remote_ip"],
                    json.loads(result.text)["result"]["port"])
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False