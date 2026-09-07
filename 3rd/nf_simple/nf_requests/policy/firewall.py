"""防火墙策略。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class FirewallFeature(NFRequests):
    """防火墙策略操作集合。"""

    def update_fw_policy_global_config(self, is_snat_org_ip=1, is_dnat_org_ip=1,
        default_action=2, req_body=None):
        """更新防火墙策略全局配置。

        对应 UI 页面「安全策略 → 防火墙策略 → 全局配置」。

        :param is_snat_org_ip: SNAT 地址匹配模式，整数。
                               ``1`` = 使用 SNAT 转换前地址（默认），``0`` = 使用转换后地址。
        :param is_dnat_org_ip: DNAT 地址匹配模式，整数。
                               ``1`` = 使用 DNAT 外部地址（默认），``0`` = 使用转换后地址。
        :param default_action: 默认动作，整数。``1`` = 放行，``2`` = 阻断（默认）。
        :param req_body:       自定义请求体 dict，传入后忽略以上所有参数，直接作为
                               POST body 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        data = {'isSnatOrgIp': is_snat_org_ip, 'isDnatOrgIp': is_dnat_org_ip,
            'defaultAction': default_action}
        if req_body:
            data = req_body
        url = f'{self.base_url}/nf/strategy/firewall/global_config/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新防火墙策略全局配置失败: {e}')
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


    def get_fw_global_info(self):
        """获取防火墙策略全局信息。

        对应 UI 页面「安全策略 → 防火墙策略 → 全局配置」，返回当前全局配置项。

        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"isDnatOrgIp": 1, "isSnatOrgIp": 1,
                 "defaultAction": 2, "isHandleLocal": 0, "isHandleInnerIp": 0,
                 "vsysId": 0}, ...}``；
                 其中 ``defaultAction``：``1`` = 放行，``2`` = 阻断。
                 失败时返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/firewall/global_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取防火墙策略全局信息失败: {e}')
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


    def _get_any_obj_id(self, ipv6_enable, net_obj):
        """获取 any / any_ipv6 地址对象 ID（实例级缓存，避免重复查询）。"""
        if not hasattr(self, '_any_obj_cache'):
            self._any_obj_cache = {}
        key = 'any_ipv6' if ipv6_enable else 'any'
        if key not in self._any_obj_cache:
            self._any_obj_cache[key] = net_obj.get_network_obj_id(name=key)
        return self._any_obj_cache[key]

    def _get_any_service_id(self):
        """获取 any 服务对象 ID（实例级缓存，避免重复查询）。"""
        if not hasattr(self, '_any_service_id'):
            from ..object.server_object import ServerObjectFeature
            ser_obj = ServerObjectFeature(self)
            self._any_service_id = ser_obj.get_service_obj_id(search='any')
        return self._any_service_id

    def _get_any_time_id(self):
        """获取 any 时间对象 ID（实例级缓存，避免重复查询）。"""
        if not hasattr(self, '_any_time_id'):
            from ..object.time_object import TimeObjectFeature
            time_obj = TimeObjectFeature(self)
            self._any_time_id = time_obj.get_time_obj_id(search='any')
        return self._any_time_id

    def create_or_update_fw_policy(self, command='create', name='ipv4_policy',
        group='', ipv6_enable=0, s_safety_zone=None, d_safety_zone=None,
        s_address=None, d_address=None, user=None, service=None, application=
        None, time=None, vlan_id=None, action='1', log='0', long_link_enable=
        False, long_link_age_time=1, session_time=None, safety_protect='0',
        hit_count=None, broadband=None, is_forbidden=0, extern_headers=None,
        ips='', obm_module='', sd_module='', mail_module='', url_filter='',
        antivirus='', waf_module='', vul_module='', policy_id=None):
        """创建或更新防火墙策略。

        对应 UI 页面「安全策略 → 防火墙策略 → 新建/编辑」。

        .. note::
            源/目的地址、服务、时间等对象需先通过对应接口创建，再将返回的 ID 传入本函数。
            不能直接填写 IP 地址或网段字符串。

        :param command:          操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param name:             策略名称，默认 ``"ipv4_policy"``。
        :param group:            策略组名称，默认 ``""`` 表示未分组。
        :param ipv6_enable:      IP 版本。``0`` = IPv4（默认），``1`` = IPv6。
        :param s_safety_zone:    源安全区，字符串或字符串列表，默认 ``["GLOBAL"]``。
        :param d_safety_zone:    目的安全区，字符串或字符串列表，默认 ``["GLOBAL"]``。
        :param s_address:        源地址对象 ID，字符串/整数或列表。
                                 传 ``None`` 时自动使用 ``any`` 对象 ID。
        :param d_address:        目的地址对象 ID，字符串/整数或列表。
                                 传 ``None`` 时自动使用 ``any`` 对象 ID。
        :param user:             用户对象。可传 dict ``{"userIdObjs": [], "userGroupObjs": []}``、
                                 字符串/整数（单个用户 ID）或列表（多个用户 ID）。
        :param service:          服务对象 ID，字符串/整数或列表。
                                 传 ``None`` 时自动使用 ``any`` 服务 ID。
        :param application:      应用对象 ID，字符串/整数或列表，默认 ``[]``。
        :param time:             时间对象 ID，字符串/整数或列表。
                                 传 ``None`` 时自动使用 ``any`` 时间 ID。
        :param vlan_id:          VLAN ID，字符串，默认 ``None``。
        :param action:           策略动作。``"1"`` = 放行（默认），``"2"`` = 阻断。
        :param log:              日志记录。``"1"`` = 记录，``"0"`` = 不记录（默认）。
        :param long_link_enable: 是否启用长连接，默认 ``False``。
        :param long_link_age_time: 长连接老化时间（秒），默认 ``1``。
        :param session_time:     会话时间，默认 ``None``。
        :param safety_protect:   安全防护开关，默认 ``"0"``。
        :param hit_count:        命中次数，默认 ``None``。
        :param broadband:        带宽对象，默认 ``None``。
        :param is_forbidden:     策略启用状态。``0`` = 启用（默认），``1`` = 禁用。
        :param extern_headers:   扩展请求头列表，默认 ``[]``。
        :param ips:              IPS 模板的ID，默认 ``""``。
        :param obm_module:       上网行为管理模板的ID，默认 ``""``。
        :param sd_module:        敏感数据模板ID，默认 ``""``。
        :param mail_module:      邮件安全模板ID，默认 ``""``。
        :param url_filter:       URL 过滤模板的ID，默认 ``""``。
        :param antivirus:        防病毒模板的ID，默认 ``""``。
        :param waf_module:       WAF 模板名称的ID，默认 ``""``。
        :param policy_id:        编辑时必填，策略 ID（整数）。新建时传 ``None``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        from ..object.network_object import NetworkObjectFeature
        net_obj = NetworkObjectFeature(self)
        if isinstance(s_safety_zone, str):
            s_safety_zone = [s_safety_zone]
        elif s_safety_zone is None:
            s_safety_zone = ['GLOBAL']
        if isinstance(d_safety_zone, str):
            d_safety_zone = [d_safety_zone]
        elif isinstance(d_safety_zone, (list, tuple)):
            d_safety_zone = [item for item in d_safety_zone]
        elif d_safety_zone is None:
            d_safety_zone = ['GLOBAL']
        if isinstance(s_address, (str, int)):
            s_address = [str(s_address)]
        elif isinstance(s_address, list):
            s_address = [str(item) for item in s_address]
        elif s_address is None:
            s_address = []
            s_address.append(self._get_any_obj_id(ipv6_enable, net_obj))
        if isinstance(d_address, (str, int)):
            d_address = [str(d_address)]
        elif isinstance(d_address, list):
            d_address = [str(item) for item in d_address]
        elif d_address is None:
            d_address = []
            d_address.append(self._get_any_obj_id(ipv6_enable, net_obj))
        if isinstance(service, (str, int)):
            service = [str(service)]
        elif isinstance(service, list):
            service = [str(item) for item in service]
        elif service is None:
            service = []
            service.append(self._get_any_service_id())
        if isinstance(application, (str, int)):
            application = [str(application)]
        elif isinstance(application, list):
            application = [str(item) for item in application]
        elif application is None:
            application = []
        if isinstance(time, (str, int)):
            time = [str(time)]
        elif isinstance(time, list):
            time = [str(item) for item in time]
        elif time is None:
            time = []
            time.append(self._get_any_time_id())
        if isinstance(user, dict):
            user = {'userIdObjs': user.get('userIdObjs', []), 'userGroupObjs':
                user.get('userGroupObjs', [])}
        elif isinstance(user, (str, int)):
            user = {'userIdObjs': [str(user)], 'userGroupObjs': []}
        elif isinstance(user, list):
            user = {'userIdObjs': [str(item) for item in user], 'userGroupObjs': []
                }
        elif user is None:
            user = {'userIdObjs': [], 'userGroupObjs': []}
        if extern_headers is None:
            extern_headers = []
        data = {'command': command, 'name': name, 'group': group,
            's_safety_zone': s_safety_zone, 'd_safety_zone': d_safety_zone,
            's_address': s_address, 'd_address': d_address, 'user': user,
            'service': service, 'application': application, 'time': time,
            'vlan_id': vlan_id, 'action': str(action), 'log': str(log),
            'ipv6Enable': ipv6_enable, 'longLinkEnable': long_link_enable,
            'longLinkAgeTime': long_link_age_time, 'session_time': session_time,
            'safety_protect': str(safety_protect), 'hit_count': hit_count,
            'broadband': broadband, 'isForbidden': is_forbidden,
            'externHeaders': extern_headers, 'ips': ips, 'obmModule':
            obm_module, 'sdModule': sd_module, 'mailModule': mail_module,
            'url_filter': url_filter, 'antivirus': antivirus, 'wafModule':
            waf_module, 'vulModule': vul_module}
        if command == 'edit':
            if policy_id is None:
                raise Exception(
                    'policy_id is None, please give policy_id when action is edit')
            data['id'] = int(policy_id)
            data['backend_id'] = str(policy_id)
        url = f'{self.base_url}/nf/strategy/firewall/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新防火墙策略失败: {e}')
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

    def get_fw_policy(self, search_type='all', page=1, size=10, search='',
        match_type='match', reload=False, is_v6='', name='', zone='', action='',
        req_body=None):
        """获取防火墙策略列表。

        对应 UI 页面「安全策略 → 防火墙策略」。

        :param search_type: 查找类型，默认 ``"all"``。
        :param page:        页码，从 ``1`` 开始，默认 ``1``。
        :param size:        每页返回条数，默认 ``10``。
        :param search:      搜索关键字，默认 ``""``。
        :param match_type:  查询匹配类型，``"match"`` = 精确匹配（默认）。
        :param reload:      是否强制重新加载，默认 ``False``。
        :param is_v6:       IPv6 过滤，``""`` = 不过滤（默认），``"true"`` = 仅 IPv6。
        :param name:        策略名称过滤，默认 ``""``。
        :param zone:        安全区过滤，默认 ``""``。
        :param action:      动作过滤，``""`` = 不过滤（默认），``"1"`` = 放行，``"2"`` = 阻断。
        :param req_body:    自定义查询参数 dict，传入后忽略以上所有参数，直接作为
                            GET query string 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"total": N, "list": [...], ...}, ...}``；
                 其中 ``list`` 每条记录包含 ``id``、``name``、``action``、``s_safety_zone``、
                 ``d_safety_zone``、``s_address``、``d_address``、``service`` 等字段。
                 失败时返回 ``False``。
        """
        params = {'searchType': search_type, 'size': size, 'page': page,
            'search': search, 'type': match_type, 'reload': reload, 'is_v6':
            is_v6, 'name': name, 'zone': zone, 'action': action}
        if req_body is not None:
            params = req_body
        url = f'{self.base_url}/nf/strategy/firewall/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取防火墙策略信息失败: {e}')
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



    def remove_fw_policy(self, policy_id):
        """删除防火墙策略。

        对应 UI 页面「安全策略 → 防火墙策略 → 删除」操作。

        :param policy_id: 策略 ID，整数、字符串或列表。多个 ID 传列表，例如 ``[1, 2, 3]``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if isinstance(policy_id, (list, tuple)):
            policy_ids = ','.join(map(str, policy_id))
        else:
            policy_ids = str(policy_id)
        data = {'id': policy_ids}
        url = f'{self.base_url}/nf/strategy/firewall/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除防火墙策略失败: {e}')
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

    @staticmethod
    def gen_fw_policy_csv(file_path, policies, encoding='utf-8-sig'):
        """生成防火墙策略 CSV 文件（标准格式，可直接上传）。

        生成的 CSV 格式与防火墙导出格式一致，可直接通过
        :meth:`upload_fw_policy_csv` 上传导入。配合上传接口，可实现大批量
        策略的快速导入（替代逐条 :meth:`create_or_update_fw_policy`）。

        :param file_path: 输出 CSV 文件路径
        :type file_path: str
        :param policies: 策略列表，每个元素为 dict，支持以下字段（均可选，
            未提供的字段留空）：

            * ``name`` — 策略名称（必填）
            * ``s_safety_zone`` — 源安全区，str 或 list[str]（多值自动逗号拼接）
            * ``d_safety_zone`` — 目的安全区，str 或 list[str]
            * ``s_address`` — 源地址，str（默认 ``"any"``）
            * ``d_address`` — 目的地址，str（默认 ``"any"``）
            * ``service`` — 服务，str（默认 ``"any"``）
            * ``time`` — 时间，str（默认 ``"any"``）
            * ``application`` — 应用
            * ``url_filter`` — URL 过滤
            * ``antivirus`` — 网络防病毒
            * ``ips`` — 入侵防护检测
            * ``obm_module`` — 上网行为管理
            * ``mail_module`` — 邮件安全
            * ``sd_module`` — 敏感数据
            * ``waf_module`` — WEB 应用通用防护
            * ``action`` — 动作，``"1"`` 放行 / ``"2"`` 阻断，默认 ``"1"``
            * ``log`` — 日志记录，``"0"`` / ``"1"``，默认 ``"0"``
            * ``enable`` — 启用，``"0"`` 启用 / ``"1"`` 禁用，默认 ``"0"``
            * ``long_link_enable`` — 启用长连接，``"TRUE"`` / ``"FALSE"``，默认 ``"FALSE"``
            * ``long_link_age_time`` — 长连接老化时长（小时）
            * ``ipv6_enable`` — 是否 IPv6 策略，``"TRUE"`` / ``"FALSE"``，默认 ``"FALSE"``
            * ``group`` — 策略分组
            * ``vlan_id`` — VLAN ID
            * ``extern_headers`` — IPv6 扩展头
            * ``vul_module`` — 漏洞防护模板
        :type policies: list[dict]
        :param encoding: 文件编码，默认 ``"utf-8-sig"``（带 BOM，兼容 Excel/WPS）
        :type encoding: str
        :return: 成功返回写入的策略条数，失败返回 ``False``
        :rtype: int or bool

        .. warning::

            **IPv4 和 IPv6 对象不能同时存在于一条策略中**：

            * ``ipv6_enable="FALSE"`` 的 IPv4 策略，源/目的地址必须使用 IPv4 对象
              （如 ``any``、IPv4 地址对象、IPv4 域名对象）
            * ``ipv6_enable="TRUE"`` 的 IPv6 策略，源/目的地址必须使用 IPv6 对象
              （如 ``any_ipv6``、IPv6 地址对象、IPv6 域名对象）
            * 域名对象也分 IPv4/IPv6，创建时需通过 ``is_ipv6`` 参数区分；
              IPv6 策略引用 IPv4 域名对象会报错"不能同时存在v4和v6对象"

        使用示例::

            policies = [
                {"name": "ipv4_test", "s_safety_zone": ["G1_5安全区","G1_6安全区"],
                 "d_safety_zone": "G1_1安全区", "action": "1"},
                {"name": "ipv6_test", "ipv6_enable": "TRUE",
                 "s_address": "any_ipv6", "d_address": "any_ipv6"},
            ]
            FirewallFeature.gen_fw_policy_csv("fw_policy.csv", policies)
            nf.policy.firewall.upload_fw_policy_csv("fw_policy.csv")
        """
        import csv
        headers = ['策略名称', '源安全区', '目的安全区', '源地址', '目的地址',
            '服务', '时间', '应用', 'URL过滤', '网络防病毒', '入侵防护检测',
            '上网行为管理', '邮件安全', '敏感数据', 'WEB应用通用防护',
            '动作(1/2)', '日志记录(0/1)', '启用(0/1)', '启用长连接(T/F)',
            '长连接老化时长(小时)', '是否为IPv6策略', '策略分组', 'VLAN ID',
            'IPv6扩展头', '漏洞防护模板']

        def _join(val):
            """list 自动逗号拼接，None 返回空字符串。"""
            if val is None:
                return ''
            if isinstance(val, list):
                return ','.join(str(v) for v in val)
            return str(val)

        try:
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                w = csv.writer(f)
                # 注释行（与防火墙导出格式一致）
                w.writerow(['#以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略'])
                w.writerow(['#部分版本office、wps无法自动识别csv文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件'])
                w.writerow(['#如果服务，平台，应用都为空，则默认会将服务设为any；时间为空时，默认给定any'])
                w.writerow(['#如果一个字段下需要输入多个值，值与值之间用逗号作为分隔符'])
                w.writerow(['#动作默认为阻断:2、允许：1，日志记录默认为1，启用默认为0，启用状态默认为:0 禁用:1'])
                w.writerow(['#如果用文本编辑器编辑策略，带有逗号的字段，请用""将这整个字段括起来。如果使用excel编辑的话，带有逗号的字段，保存后，excel会把这个字段用""括起来'])
                w.writerow(['#' + ','.join(headers)])
                # 数据行
                count = 0
                for p in policies:
                    row = [
                        p.get('name', ''),
                        _join(p.get('s_safety_zone')),
                        _join(p.get('d_safety_zone')),
                        p.get('s_address', 'any'),
                        p.get('d_address', 'any'),
                        p.get('service', 'any'),
                        p.get('time', 'any'),
                        _join(p.get('application')),
                        _join(p.get('url_filter')),
                        _join(p.get('antivirus')),
                        _join(p.get('ips')),
                        _join(p.get('obm_module')),
                        _join(p.get('mail_module')),
                        _join(p.get('sd_module')),
                        _join(p.get('waf_module')),
                        p.get('action', '1'),
                        p.get('log', '0'),
                        p.get('enable', '0'),
                        p.get('long_link_enable', 'FALSE'),
                        p.get('long_link_age_time', ''),
                        p.get('ipv6_enable', 'FALSE'),
                        _join(p.get('group')),
                        _join(p.get('vlan_id')),
                        _join(p.get('extern_headers')),
                        _join(p.get('vul_module')),
                    ]
                    w.writerow(row)
                    count += 1
            logger.info(f'生成防火墙策略 CSV: {file_path} ({count} 条)')
            return count
        except Exception as e:
            logger.error(f'生成防火墙策略 CSV 失败: {e}')
            return False

    def clear_fw_policy(self):
        """清空所有防火墙策略。

        对应 UI 页面「安全策略 → 防火墙策略 → 清空」操作，删除设备上全部防火墙策略。

        .. warning::
            此操作不可逆，生产环境请谨慎使用。

        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/firewall/clear/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空防火墙策略失败: {e}')
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

    def move_fw_policy(self, name=None, location=None, req_body=None,
        src_rule_id=None, dst_rule_id=None):
        """移动防火墙策略位置。

        对应 UI 页面「安全策略 → 防火墙策略 → 移动」操作。

        :param name:        策略名称，仅作兼容保留，实际不参与请求，默认 ``None``。
        :param location:    移动位置。``"top"`` = 移到顶部，``"bottom"`` = 移到底部，
                            其他值或 ``None`` = 移动到指定策略旁边。
        :param req_body:    自定义请求体 dict，传入后忽略以上所有参数，直接作为
                            POST body 发送。用于特殊场景或调试。
        :param src_rule_id: 要移动的源策略 ID（字符串或整数）。
        :param dst_rule_id: 目标策略 ID，移动到 ``top``/``bottom`` 时可不传，默认 ``None``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if req_body:
            data = req_body
        elif location in ['top', 'bottom']:
            data = {'type': location, 'srcRuleId': str(src_rule_id)}
        else:
            data = {'dstRuleId': str(dst_rule_id), 'srcRuleId': str(src_rule_id)}
        url = f'{self.base_url}/nf/strategy/firewall/move/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'移动防火墙策略失败: {e}')
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

    def switch_fw_policy_status(self, fw_id='1', status=1, req_body=None):
        """启用或禁用防火墙策略。

        对应 UI 页面「安全策略 → 防火墙策略」列表中的启用/禁用开关。

        :param fw_id:    策略 ID，字符串或整数，默认 ``"1"``。
        :param status:   目标状态。``0`` = 启用，``1`` = 禁用（默认）。
        :param req_body: 自定义请求体 dict，传入后忽略以上所有参数，直接作为
                         POST body 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        data = {'id': fw_id, 'status': status}
        if req_body:
            data = req_body
        url = f'{self.base_url}/nf/strategy/firewall/status/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'切换防火墙策略状态失败: {e}')
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


    def batch_update_fw_policy(self, s_address=None, d_address=None,
        s_safety_zone=None, d_safety_zone=None, service=None, time=None,
        application=None, policy_id=None, action=None, log=None):
        """批量修改防火墙策略属性。

        对应 UI 页面「安全策略 → 防火墙策略 → 批量修改」操作。
        只传入需要修改的字段，未传入的字段保持不变。

        :param s_address:    源地址对象列表，字符串或列表，默认 ``None``（不修改）。
        :param d_address:    目的地址对象列表，字符串或列表，默认 ``None``（不修改）。
        :param s_safety_zone: 源安全区列表，字符串或列表，默认 ``None``（不修改）。
        :param d_safety_zone: 目的安全区列表，字符串或列表，默认 ``None``（不修改）。
        :param service:      服务对象列表，字符串或列表，默认 ``None``（不修改）。
        :param time:         时间对象列表，字符串或列表，默认 ``None``（不修改）。
        :param application:  应用对象列表，字符串或列表，默认 ``None``（不修改）。
        :param policy_id:    要修改的策略 ID，字符串、整数或列表，必填。
        :param action:       动作。``1`` = 放行，``2`` = 阻断，默认 ``None``（不修改）。
        :param log:          日志记录。``1`` = 记录，``0`` = 不记录，默认 ``None``（不修改）。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        parameters = {'s_address': s_address, 'd_address': d_address,
            's_safety_zone': s_safety_zone, 'd_safety_zone': d_safety_zone,
            'service': service, 'time': time, 'application': application}
        data = {}
        for key, value in parameters.items():
            if value is not None:
                data[key] = value if not isinstance(value, str) else [value]
        if policy_id is not None:
            if isinstance(policy_id, str):
                policy_id = [policy_id]
            elif isinstance(policy_id, list):
                policy_id = [str(pid) for pid in policy_id]
            else:
                policy_id = [str(policy_id)]
            data['id'] = policy_id
        if action is not None:
            data['action'] = action
        if log is not None:
            data['log'] = log
        url = f'{self.base_url}/nf/strategy/firewall/batch/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'批量修改防火墙策略失败: {e}')
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

    def clear_fw_hit_count(self, policy_id=None):
        """清除防火墙策略命中计数。

        对应 UI 页面「安全策略 → 防火墙策略 → 清除命中次数」操作。

        :param policy_id: 策略 ID（整数或字符串）。传 ``None`` 时清除全部策略的命中计数（等同于传 ``-1``）。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        data = {'id': str(policy_id) if policy_id is not None else '-1'}
        url = f'{self.base_url}/nf/strategy/firewall/clear_hit_count/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清除防火墙命中计数失败: {e}')
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


    def upload_fw_policy_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入防火墙策略。

        对应接口 ``POST /nf/strategy/firewall/upload/``，``multipart/form-data`` 上传。

        当策略数量较多（如 500+ 条）时，建议用本接口替代逐条
        :meth:`create_or_update_fw_policy`，避免大量 HTTP 请求开销。

        :param file_path: CSV 文件路径。文件格式参考防火墙导出的策略 CSV，
            第 1-7 行为注释，第 7 行为表头，字段顺序：
            ``策略名称,源安全区,目的安全区,源地址,目的地址,服务,时间,应用,
            URL过滤,网络防病毒,入侵防护检测,上网行为管理,邮件安全,敏感数据,
            WEB应用通用防护,动作(1/2),日志记录(0/1),启用(0/1),启用长连接(T/F),
            长连接老化时长(小时),是否为IPv6策略,策略分组,VLAN ID,IPv6扩展头,
            漏洞防护模板``
        :type file_path: str
        :param req_body: 自定义请求体字段，传入后会合并到上传请求的 form data 中。
            一般场景无需传入。
        :type req_body: dict or None
        :return: 成功返回完整响应 dict，失败返回 ``False``
        :rtype: dict or bool

        CSV 文件示例::

            #以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略
            ...
            #策略名称,源安全区,目的安全区,源地址,目的地址,服务,时间,...
            ipv4_test,"G1_5安全区,G1_6安全区,G1_7安全区",G1_1安全区,any,any,any,any,...,默认模板,1,0,0,FALSE,,FALSE,,,,全防护模板
        """
        import os
        if not os.path.exists(file_path):
            logger.error(f'CSV 文件不存在: {file_path}')
            return False
        url = f'{self.base_url}/nf/strategy/firewall/upload/'
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'text/csv')}
                data = req_body if req_body is not None else {}
                result = self.session.post(url, files=files, data=data,
                    verify=False, timeout=300)
        except Exception as e:
            logger.error(f'上传防火墙策略 CSV 失败: {e}')
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
