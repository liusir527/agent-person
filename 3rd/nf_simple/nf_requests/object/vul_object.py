"""漏洞模板对象 — 漏洞防护模板 CRUD。

对应 UI 页面「对象 → 安全防护 → 漏洞防护」。
"""
import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class VulObjectFeature(NFRequests):
    """漏洞模板对象操作集合 — 漏洞防护模板的查询和创建。"""

    def get_vul_template(self, page=1, size=10, search='', type='custom'):
        """查询漏洞模板列表。

        对应 UI 页面「对象 → 安全防护 → 漏洞防护」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param type: 模板类型，``"custom"`` = 自定义模板，``"全防护模板"`` = 全防护模板
        :type type: str
        :return: 成功返回 API 响应字典（``result.list`` 为模板列表），失败返回 False
        :rtype: dict or bool
        """
        params = {'size': size, 'page': page, 'search': search, 'type': type}
        req_url = f'{self.base_url}/nf/object/vul/template/info/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取漏洞模板列表失败: {e}')
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

    def get_vul_template_id(self, search='',page=1, size=10, type='custom'):
        """按名称查询漏洞模板 backend_id。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 模板名称
        :type search: str
        :param type: 模板类型，``"custom"`` = 自定义模板，``"全防护模板"`` = 全防护模板
        :type type: str
        :return: 成功返回模板 backend_id，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_vul_template(page=page, size=size, search=search, type=type)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('backend_id')
        return False

    def create_vul_template(self, action='create', name='test', comment='',
        rules=None):
        """创建或修改漏洞防护模板。

        对应 UI 页面「对象 → 安全防护 → 漏洞防护」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 模板名称
        :type name: str
        :param comment: 备注
        :type comment: str
        :param rules: 规则配置字典，格式 ``{rule_id: {"block": bool, "log": bool}, ...}``；
            传 ``None`` 时自动拉取全部 CVE 系统规则，默认 ``block=True, log=True``
        :type rules: dict or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if rules is None:
            all_ids_resp = self.get_vul_template_id()
            if all_ids_resp is not False and all_ids_resp.get('result'):
                rule_ids = all_ids_resp['result']
                rules = {}
                for rid in rule_ids:
                    rules[str(rid)] = {'block': True, 'log': True}
                logger.info(f'自动加载全部 {len(rules)} 条漏洞防护规则')
            else:
                rules = {}
        req_url = f'{self.base_url}/nf/object/vul/template/configuration/'
        data = {'action': action, 'name': name, 'comment': comment, 'rules':
            rules}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建漏洞模板失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
