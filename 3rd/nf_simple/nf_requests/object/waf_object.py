"""WAF 全局配置和自定义规则/模板 CRUD。

对应 UI 页面「对象 → WAF」。
"""
import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class WafObjectFeature(NFRequests):
    """WAF 对象操作集合 — 全局配置、自定义规则和模板的增删查改。"""

    def update_waf_global_config(self, xff_enable=0, nti_enable=0):
        """更新 WAF 全局配置 (XFF/NTI)。

        对应 UI 页面「对象 → WAF → 全局配置」。

        :param xff_enable: XFF 字段检测，``0`` = 关闭，``1`` = 开启
        :type xff_enable: int
        :param nti_enable: NTI 威胁检测，``0`` = 关闭，``1`` = 开启
        :type nti_enable: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'xffEnable': int(xff_enable), 'ntiEnable': int(nti_enable)}
        req_url = f'{self.base_url}/nf/object/waf/template/updateGlobalConfig/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新WAF全局配置失败: {e}')
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

    def get_waf_global_config(self):
        """获取 WAF 全局配置。

        对应 UI 页面「对象 → WAF → 全局配置」。

        :return: 成功返回 API 响应 dict（含 ``xffEnable`` 和 ``ntiEnable``），失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/waf/template/globalConfigInfo/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取WAF全局配置失败: {e}')
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

    def create_or_update_waf_custom_rule(self, action='create', enable=False,
        name='autotest', request_type='GET', url='', protocol_type='HTTP',
        threat_level='低', rule_id=None):
        """创建或编辑 WAF 自定义规则。

        对应 UI 页面「对象 → WAF → 自定义规则」。

        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type action: str
        :param enable: 是否启用
        :type enable: bool
        :param name: 规则名称
        :type name: str
        :param request_type: HTTP 请求方法，``"GET"``、``"POST"`` 等
        :type request_type: str
        :param url: 匹配 URL
        :type url: str
        :param protocol_type: 协议类型，``"HTTP"`` 等
        :type protocol_type: str
        :param threat_level: 威胁等级，``"低"``、``"中"``、``"高"``
        :type threat_level: str
        :param rule_id: 规则 ID，编辑时必填
        :type rule_id: int or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'action': action, 'enable': enable, 'name': name,
            'protocol_type': protocol_type, 'threat_level': threat_level,
            'protocol_content': {'request_type': request_type, 'url': url}}
        if rule_id is not None:
            data['id'] = rule_id
        req_url = f'{self.base_url}/nf/object/waf/rules/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改WAF自定义规则失败: {e}')
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

    def remove_custom_waf_rules(self, rule_ids):
        """删除 WAF 自定义规则。

        对应 UI 页面「对象 → WAF → 自定义规则」。

        :param rule_ids: 规则 ID，支持单个 int 或列表
        :type rule_ids: int or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(rule_ids, int):
            rule_ids = [rule_ids]
        data = {'id': rule_ids}
        req_url = f'{self.base_url}/nf/object/waf/rules/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除WAF自定义规则失败: {e}')
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

    def get_waf_rules_ids(self, rule_type='all', rule_id=None, threat_level=
        None, protection_type=None, search=None):
        """获取 WAF 规则 ID 列表。

        对应 UI 页面「对象 → WAF → 规则列表」。

        :param rule_type: 规则类型，``"all"`` = 全部，``"custom"`` = 自定义
        :type rule_type: str
        :param rule_id: 按规则 ID 筛选
        :type rule_id: int or None
        :param threat_level: 按威胁等级筛选，``"低"``、``"中"``、``"高"``
        :type threat_level: str or None
        :param protection_type: 按防护类型筛选
        :type protection_type: str or None
        :param search: 搜索关键字
        :type search: str or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'type': rule_type}
        if rule_id is not None:
            params['id'] = rule_id
        if threat_level is not None:
            params['threat_level'] = threat_level
        if protection_type is not None:
            params['protection_type'] = protection_type
        if search is not None:
            params['search'] = search
        req_url = f'{self.base_url}/nf/object/waf/rules/get_ids/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取WAF规则ID失败: {e}')
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

    def get_waf_rule_id_list(self, rule_type='all', threat_level=None,
                              protection_type=None, search=None):
        """获取 WAF 规则 ID 列表（仅返回 ID 列表）。

        :param rule_type: 规则类型，``"all"`` = 全部，默认 ``"all"``
        :type rule_type: str
        :param threat_level: 威胁等级，``"低"``、``"中"``、``"高"``
        :type threat_level: str or None
        :param protection_type: 防护类型
        :type protection_type: str or None
        :param search: 搜索关键字
        :type search: str or None
        :return: 成功返回规则 ID 列表 ``list[int]``，失败返回 ``False``
        :rtype: list[int] or bool
        """
        resp = self.get_waf_rules_ids(rule_type=rule_type,
                                       threat_level=threat_level,
                                       protection_type=protection_type,
                                       search=search)
        if resp is False:
            return False
        id_list = resp.get('result', [])
        logger.info(f'获取WAF规则ID列表：共 {len(id_list)} 条')
        return id_list

    def build_waf_rules(self, ids, is_action=True, is_log=True):
        """将规则 ID 列表组装为 ``create_or_update_waf_template`` 的 ``wafRule`` 参数格式。

        :param ids: 规则 ID，支持单个 ``int`` 或 ``list[int]``
        :type ids: int or list[int]
        :param is_action: 是否阻断，默认 ``True``
        :type is_action: bool
        :param is_log: 是否记录日志，默认 ``True``
        :type is_log: bool
        :return: wafRule 列表，每项为 ``{"id": int, "isAction": bool, "isLog": bool}``
        :rtype: list[dict]

        用法::

            ids = nf.object.waf.get_waf_rule_id_list()
            rules = nf.object.waf.build_waf_rules(ids, is_action=True, is_log=True)
            nf.object.waf.create_or_update_waf_template(name='waf_test', waf_rule=rules)
        """
        if isinstance(ids, (int, float)):
            ids = [int(ids)]
        return [{'id': int(rid), 'isAction': is_action, 'isLog': is_log} for rid in ids]

    def get_waf_rules_info(self, page=1, size=10, rule_type='all', rule_id=None,
        threat_level=None, protection_type=None, search=''):
        """获取 WAF 规则详情列表。

        对应 UI 页面「对象 → WAF → 规则列表」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param rule_type: 规则类型，``"all"`` = 全部，``"custom"`` = 自定义
        :type rule_type: str
        :param rule_id: 按规则 ID 筛选
        :type rule_id: int or None
        :param threat_level: 按威胁等级筛选
        :type threat_level: str or None
        :param protection_type: 按防护类型筛选
        :type protection_type: str or None
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'type': rule_type, 'page': page, 'size': size, 'search': search}
        if rule_id is not None:
            params['id'] = rule_id
        if threat_level is not None:
            params['threat_level'] = threat_level
        if protection_type is not None:
            params['protection_type'] = protection_type
        req_url = f'{self.base_url}/nf/object/waf/rules/info/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取WAF规则详情失败: {e}')
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


    def create_or_update_waf_template(self, action='create', name='autotest',
        comment='', waf_rule_id=None, is_action=None, is_log=None, waf_tmpl_id=
        None, waf_rule=None):
        """创建或编辑 WAF 模板。

        对应 UI 页面「对象 → WAF → 模板」。

        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type action: str
        :param name: 模板名称
        :type name: str
        :param comment: 备注
        :type comment: str
        :param waf_rule_id: WAF 规则 ID 列表，默认 ``[10000]``；传入单个 int 或 list 均可
        :type waf_rule_id: int or list or None
        :param is_action: 对应每项规则的阻断开关列表，默认全 ``True``
        :type is_action: bool or list or None
        :param is_log: 对应每项规则的日志开关列表，默认全 ``True``
        :type is_log: bool or list or None
        :param waf_tmpl_id: 模板 ID，编辑时使用
        :type waf_tmpl_id: int or None
        :param waf_rule: 完整的规则配置列表，每项为 `` :{"id":10448,"isAction":true,"isLog":true}``
            则使用默认全开配置
        :type waf_rule: list or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        use_default_waf_rules = (waf_rule is None and waf_rule_id is None and
            is_action is None and is_log is None)
        if use_default_waf_rules and waf_rule is None:
            # 未传任何规则参数时，自动获取所有 WAF 规则 ID
            all_ids = self.get_waf_rule_id_list()
            if all_ids is False:
                logger.error('自动填充 waf_rule 失败：获取 WAF 规则 ID 列表失败')
                return False
            logger.info(f'自动填充 waf_rule：共 {len(all_ids)} 条，'
                        f'is_action=True, is_log=True')
            waf_rule = self.build_waf_rules(all_ids, is_action=True, is_log=True)
        if waf_rule is not None:
            pass  # waf_rule already set, skip old logic
        else:
            if isinstance(waf_rule_id, (int, str)):
                waf_rule_id = [int(waf_rule_id)]
            elif isinstance(waf_rule_id, list):
                waf_rule_id = list(map(int, waf_rule_id))
            elif waf_rule_id is None:
                waf_rule_id = [10000]
            if isinstance(is_action, bool):
                is_action = [is_action] * len(waf_rule_id)
            elif is_action is None:
                is_action = [True] * len(waf_rule_id)
            if isinstance(is_log, bool):
                is_log = [is_log] * len(waf_rule_id)
            elif is_log is None:
                is_log = [True] * len(waf_rule_id)
            waf_rule = []
            for _rule_id, _ac, _l in zip(waf_rule_id, is_action, is_log):
                waf_rule.append({'id': _rule_id, 'isAction': _ac, 'isLog': _l})
        data = {'action': action, 'name': name, 'comment': comment, 'wafRule':
            waf_rule}
        if waf_tmpl_id is not None:
            data['id'] = waf_tmpl_id
        req_url = f'{self.base_url}/nf/object/waf/template/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=300
                )
        except Exception as e:
            logger.error(f'创建或修改WAF模板失败: {e}')
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

    def remove_waf_template(self, waf_tmpl_id=None):
        """删除 WAF 模板。

        对应 UI 页面「对象 → WAF → 模板」。

        :param waf_tmpl_id: 模板 ID，支持单个 int 或列表；传 ``None`` 时删除全部
        :type waf_tmpl_id: int or list or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if waf_tmpl_id is not None:
            if isinstance(waf_tmpl_id, (int, str)):
                waf_tmpl_id = [int(waf_tmpl_id)]
            elif isinstance(waf_tmpl_id, list):
                waf_tmpl_id = [int(i) for i in waf_tmpl_id]
            data = {'id': waf_tmpl_id}
        else:
            data = None
        req_url = f'{self.base_url}/nf/object/waf/template/delete/'
        try:
            if data is None:
                result = self.session.post(req_url, verify=False, timeout=30)
            else:
                result = self.session.post(req_url, json=data, verify=False,
                    timeout=30)
        except Exception as e:
            logger.error(f'删除WAF模板失败: {e}')
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

    def get_waf_template_info(self, page=1, size=10, search='', type='custom'):
        """查询 WAF 模板列表。

        对应 UI 页面「对象 → WAF → 模板」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param type: 模板类型，``"custom"`` = 自定义，``"system"`` = 系统内置
        :type type: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'size': size, 'page': page, 'search': search, 'type': type}
        req_url = f'{self.base_url}/nf/object/waf/template/info/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取WAF模板列表失败: {e}')
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

    def get_waf_template_info_id(self, search='',page=1, size=10,type='custom'):
        """按名称查询 WAF 模板 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 要匹配的模板名称
        :type search: str
        :param type: 模板类型
        :type type: str
        :return: 成功返回模板 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_waf_template_info(page=page, size=size, search=search,
            type=type)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('id')
        return False

    def get_waf_template_details(self, tmpl_id=None, query_type=None):
        """获取 WAF 模板详情。

        对应 UI 页面「对象 → WAF → 模板」。

        :param tmpl_id: 模板 ID
        :type tmpl_id: int or None
        :param query_type: 查询类型
        :type query_type: str or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'id': tmpl_id, 'type': query_type}
        req_url = f'{self.base_url}/nf/object/waf/template/details/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取WAF模板详情失败: {e}')
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
