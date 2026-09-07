"""IPS 自定义规则和模板对象 CRUD。

对应 UI 页面「对象 → IPS」「对象 → 入侵防护」。
"""
import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class IpsObjectFeature(NFRequests):
    """IPS 对象操作集合 — 自定义规则、模板、规则库查询。"""

    def create_or_update_ips_custom_rule_obj(self, action='create', name=
        'autotest', threat_level='低', protocol_type='HTTP', enable=False,
        rule_id=None, request_type='GET', url='', pop3_sender='',
        pop3_recipient='', pop3_keyword='', smtp_sender='', smtp_recipient='',
        smtp_keyword='', user_name='', file_name='', qq='', protocol_num=0,
        ip_packet_length=0, ip_keyword='', tcp_s_port=0, tcp_d_port=0,
        tcp_packet_length=0, tcp_keyword='', udp_s_port=0, udp_d_port=0,
        udp_packet_length=0, udp_keyword=''):
        """创建或修改 IPS 自定义规则。

        对应 UI 页面「对象 → IPS → 自定义规则」。

        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type action: str
        :param name: 规则名称
        :type name: str
        :param threat_level: 威胁等级，``"低"``、``"中"``、``"高"``
        :type threat_level: str
        :param protocol_type: 协议类型，``"HTTP"``、``"POP3"``、``"SMTP"``、``"FTP"``、``"QQ"``、
            ``"IP"``、``"TCP"``、``"UDP"``
        :type protocol_type: str
        :param enable: 是否启用
        :type enable: bool
        :param rule_id: 规则 ID，编辑时使用
        :type rule_id: int or None
        :param request_type: HTTP 请求方法，仅 ``protocol_type='HTTP'`` 时有效
        :type request_type: str
        :param url: HTTP URL，仅 ``protocol_type='HTTP'`` 时有效
        :type url: str
        :param pop3_sender: POP3 发件人
        :type pop3_sender: str
        :param pop3_recipient: POP3 收件人
        :type pop3_recipient: str
        :param pop3_keyword: POP3 关键字
        :type pop3_keyword: str
        :param smtp_sender: SMTP 发件人
        :type smtp_sender: str
        :param smtp_recipient: SMTP 收件人
        :type smtp_recipient: str
        :param smtp_keyword: SMTP 关键字
        :type smtp_keyword: str
        :param user_name: FTP 用户名
        :type user_name: str
        :param file_name: FTP 文件名
        :type file_name: str
        :param qq: QQ 号码
        :type qq: str
        :param protocol_num: IP 协议号
        :type protocol_num: int
        :param ip_packet_length: IP 包长度
        :type ip_packet_length: int
        :param ip_keyword: IP 关键字
        :type ip_keyword: str
        :param tcp_s_port: TCP 源端口
        :type tcp_s_port: int
        :param tcp_d_port: TCP 目的端口
        :type tcp_d_port: int
        :param tcp_packet_length: TCP 包长度
        :type tcp_packet_length: int
        :param tcp_keyword: TCP 关键字
        :type tcp_keyword: str
        :param udp_s_port: UDP 源端口
        :type udp_s_port: int
        :param udp_d_port: UDP 目的端口
        :type udp_d_port: int
        :param udp_packet_length: UDP 包长度
        :type udp_packet_length: int
        :param udp_keyword: UDP 关键字
        :type udp_keyword: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if protocol_type == 'HTTP':
            protocol_content = {'request_type': request_type, 'url': url}
        elif protocol_type == 'POP3':
            protocol_content = {'sender': pop3_sender, 'recipient':
                pop3_recipient, 'keyword': pop3_keyword}
        elif protocol_type == 'SMTP':
            protocol_content = {'sender': smtp_sender, 'recipient':
                smtp_recipient, 'keyword': smtp_keyword}
        elif protocol_type == 'FTP':
            protocol_content = {'user_name': user_name, 'file_name': file_name}
        elif protocol_type == 'QQ':
            protocol_content = {'qq': qq}
        elif protocol_type == 'IP':
            protocol_content = {'protocol_num': protocol_num, 'packet_length':
                ip_packet_length, 'keyword': ip_keyword}
        elif protocol_type == 'TCP':
            protocol_content = {'s_port': tcp_s_port, 'd_port': tcp_d_port,
                'packet_length': tcp_packet_length, 'keyword': tcp_keyword}
        elif protocol_type == 'UDP':
            protocol_content = {'s_port': udp_s_port, 'd_port': udp_d_port,
                'packet_length': udp_packet_length, 'keyword': udp_keyword}
        else:
            protocol_content = {}
        data = {'action': action, 'name': name, 'enable': enable,
            'threat_level': threat_level, 'protocol_type': protocol_type,
            'protocol_content': protocol_content}
        if rule_id is not None:
            data['id'] = int(rule_id)
        req_url = f'{self.base_url}/nf/object/rules/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改IPS自定义规则失败: {e}')
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
    
    def create_ips_template(self, action='create', name='入侵防护2', note='', type=
        'custom', rules=None, e_rules=None,backend_id=53):
        """创建或修改 IPS 模板。
        {"action":"edit","name":"test_12345","note":"","type":"custom","rules":[{"event_object_id":101999,"block":true,"log":true},{"event_object_id":101998,"block":true,"log":true}],"e_rules":[],"backend_id":52}
        对应 UI 页面「对象 → IPS → 模板」。

        当 ``rules`` 为 ``None`` 或空列表时，自动查询威胁等级为"高"和"中"的
        系统规则 ID，并以 ``block=True``、``log=True`` 组装。

        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type action: str
        :param name: 模板名称
        :type name: str
        :param note: 备注
        :type note: str
        :param type: 模板类型，``"custom"`` = 自定义
        :type type: str
        :param rules: 包含的规则列表，每项含 ``event_object_id``、``block``、``log``；
            为 ``None`` 或空列表时自动从高/中威胁等级规则填充
        :type rules: list or None
        ：rules=[{"event_object_id":101999,"block":true,"log":true}]  event_object_id是规则id，block是否阻断bool，log是否开启日志bool，每个规则id一个字典
        :param e_rules: 排除的规则列表
        :type e_rules: list or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if not rules:
            all_ids = []
            all_ids = self.get_ips_rule_ids(type='all', threat_level='高')
            #all_ids += self.get_ips_rule_ids(type='all', threat_level='中')

            logger.info(f'自动填充 rules：威胁 {len(all_ids)} 条')
            rules = self.build_ips_rules(all_ids, block=True, log=True)
        data = {'action': action, 'name': name, 'note': note, 'type': type,
            'rules': [] if rules is None else rules,
            'e_rules': [] if e_rules is None else e_rules,
            "backend_id":backend_id,"type":"custom"}
        req_url = f'{self.base_url}/nf/object/template/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=180)
        except Exception as e:
            logger.error(f'创建或修改IPS模板失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(data)
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_ips_template(self, search, type='custom', page=1, size=10):
        """查询 IPS 模板列表。

        对应 UI 页面「对象 → IPS → 模板」。

        :param search: 搜索关键字
        :type search: str
        :param type: 模板类型，``"custom"`` = 自定义，``"system"`` = 系统内置
        :type type: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/template/info/'
        params = {'size': size, 'page': page, 'search': search, 'type': type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'查询IPS规则失败: {e}')
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

    def get_ips_template_id(self, search, type='custom', page=1, size=10):
        """按名称查询 IPS 模板 backend_id。

        :param search: 要匹配的模板名称
        :type search: str
        :param type: 模板类型
        :type type: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :return: 成功返回模板 ``backend_id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_ips_template(search=search, type=type, page=page, size=size)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('backend_id')
        return False

    def get_ips_rule(self, rule_type='custom', logic='or', page=1, size=10,
        search='', name=None, threat_level=None, cve_id=None, cnnvd_id=None,
        nsfocus_id=None, attack_technique=None, backend_id=None):
        """查询 IPS 规则库。

        对应 UI 页面「对象 → IPS → 规则库」。

        :param rule_type: 查询类型，``"custom"`` = 自定义，``"system"`` = 系统内置
        :type rule_type: str
        :param logic: 查询逻辑，``"or"`` = 或，``"and"`` = 与
        :type logic: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param name: 按规则名称筛选
        :type name: str or None
        :param threat_level: 按威胁等级筛选
        :type threat_level: str or None
        :param cve_id: 按 CVE ID 筛选
        :type cve_id: str or None
        :param cnnvd_id: 按 CNNVD ID 筛选
        :type cnnvd_id: str or None
        :param nsfocus_id: 按绿盟规则 ID 筛选
        :type nsfocus_id: str or None
        :param attack_technique: 按攻击类别筛选
        :type attack_technique: str or None
        :param backend_id: 按后台规则 ID 筛选
        :type backend_id: str or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'type': rule_type, 'logic': logic, 'page': page, 'size': size,
            'search': search}
        if backend_id is not None:
            data['backend_id'] = backend_id
        if name is not None:
            data['name'] = name
        if threat_level is not None:
            data['threat_level'] = threat_level
        if attack_technique is not None:
            data['attack_technique'] = attack_technique
        if cve_id is not None:
            data['CVE_ID'] = cve_id
        if cnnvd_id is not None:
            data['CNNVD_ID'] = cnnvd_id
        if nsfocus_id is not None:
            data['NSFOUCUS_ID'] = nsfocus_id
        req_url = f'{self.base_url}/nf/object/rules/info/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'查询IPS规则失败: {e}')
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

    def get_ips_rule_id(self, rule_type='custom', logic='or', page=1, size=10,
        search='', name=None, threat_level=None, cve_id=None, cnnvd_id=None,
        nsfocus_id=None, attack_technique=None, backend_id=None):
        """按名称查询 IPS 规则 ID。

        :param name: 要匹配的规则名称
        :type name: str
        :param rule_type: 查询类型
        :type rule_type: str
        :param logic: 查询逻辑
        :type logic: str
        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param threat_level: 威胁等级
        :type threat_level: str or None
        :param cve_id: CVE ID
        :type cve_id: str or None
        :param cnnvd_id: CNNVD ID
        :type cnnvd_id: str or None
        :param nsfocus_id: 绿盟规则 ID
        :type nsfocus_id: str or None
        :param attack_technique: 攻击类别
        :type attack_technique: str or None
        :param backend_id: 后台规则 ID
        :type backend_id: str or None
        :return: 成功返回规则 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_ips_rule(rule_type=rule_type, logic=logic, page=page,
            size=size, search=search, name=name, threat_level=threat_level,
            cve_id=cve_id, cnnvd_id=cnnvd_id, nsfocus_id=nsfocus_id,
            attack_technique=attack_technique, backend_id=backend_id)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == name:
                return i.get('id')
        return False

    def get_ips_rule_ids(self, type='all', threat_level='高'):
        """获取 IPS 规则 ID 列表。

        对应 API 端点 ``/nf/object/rules/get_ids/``，用于获取指定类型和威胁等级的
        所有规则 ID，这些 ID 可以直接作为 ``create_ips_template`` 中 ``rules`` 参数
        的 ``event_object_id``。

        :param type: 规则类型，``"all"`` = 全部，``"system"`` = 系统内置，默认 ``"all"``
        :type type: str
        :param threat_level: 威胁等级，``"高"``、``"中"``、``"低"``，默认 ``"高"``
        :type threat_level: str
        :return: 成功返回规则 ID 列表 ``list[int]``，失败返回 ``False``
        :rtype: list[int] or bool
        """
        req_url = f'{self.base_url}/nf/object/rules/get_ids/'
        params = {'type': type, 'threat_level': threat_level}
        try:
            result = self.session.get(req_url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取IPS规则ID列表失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(f'{message}，共 {len(resp_data.get("result", []))} 条')
                return resp_data.get('result', [])
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def build_ips_rules(self, ids, block=True, log=True):
        """将规则 ID 列表组装为 ``create_ips_template`` 的 ``rules`` 参数格式。

        :param ids: 规则 ID，支持单个 ``int`` 或 ``list[int]``
        :type ids: int or list[int]
        :param block: 是否阻断，默认 ``True``
        :type block: bool
        :param log: 是否开启日志，默认 ``True``
        :type log: bool
        :return: 规则字典列表，每项为 ``{"event_object_id": int, "block": bool, "log": bool}``
        :rtype: list[dict]

        用法::

            ids = nf.object.ips.get_ips_rule_ids(type='all', threat_level='高')
            rules = nf.object.ips.build_ips_rules(ids, block=True, log=True)
            nf.object.ips.create_ips_template(name='ips_test', rules=rules)
        """
        if isinstance(ids, (int, float)):
            ids = [int(ids)]
        return [{'event_object_id': int(rid), 'block': block, 'log': log} for rid in ids]

    def remove_ips_custom_rule(self, rule_ids):
        """删除 IPS 自定义规则。

        对应 UI 页面「对象 → IPS → 自定义规则」。

        :param rule_ids: 规则 ID，支持单个值或列表，多个以逗号分隔发送
        :type rule_ids: str or int or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(rule_ids, (list, tuple)):
            rule_ids = ','.join(map(str, rule_ids))
        else:
            rule_ids = str(rule_ids)
        data = {'id': rule_ids}
        req_url = f'{self.base_url}/nf/object/rules/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除IPS自定义规则失败: {e}')
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
