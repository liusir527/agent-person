"""URL 分类和模板对象 CRUD — URL 分类管理、在线查询和过滤模板操作。

对应 UI 页面「对象 → URL 分类」「对象 → URL 过滤模板」。
"""
import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class UrlObjectFeature(NFRequests):
    """URL 对象操作集合 — URL 分类和过滤模板的增删查改及在线查询。"""

    def create_or_update_url_classified(self, action='create', name=
        'url_class_1', describe='', domain='', key_word='', class_id=''):
        """创建或修改 URL 分类。

        对应 UI 页面「对象 → URL 分类」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 分类名称
        :type name: str
        :param describe: 描述
        :type describe: str
        :param domain: 域名
        :type domain: str
        :param key_word: 关键字
        :type key_word: str
        :param class_id: 分类 ID，编辑时必填
        :type class_id: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'action': action, 'name': name, 'describe': describe, 'domain':
            domain, 'key_word': key_word, 'id': class_id}
        req_url = f'{self.base_url}/nf/object/url/classified/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改URL分类失败: {e}')
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

    def get_url_class(self, page=1, size=1000, search='', url_type='custom'):
        """获取 URL 分类列表。

        对应 UI 页面「对象 → URL 分类」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param url_type: 分类类型，``"custom"`` = 自定义，``"system"`` = 系统内置
        :type url_type: str
        :return: 成功返回 API 响应字典（``result.list`` 为分类列表），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/url/classified/'
        params = {'page': page, 'size': size, 'search': search, 'type': url_type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取URL分类列表失败: {e}')
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

    def get_online_url_class(self, url):
        """在线查询 URL 分类。

        对应 UI 页面「对象 → URL 分类」。

        :param url: 要查询的 URL 地址
        :type url: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/url/url_online_test/'
        params = {'search': url}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'在线查询URL分类失败: {e}')
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

    def remove_url_classified(self, classified_ids):
        """删除 URL 分类。

        对应 UI 页面「对象 → URL 分类」。

        :param classified_ids: 分类 ID，单个值或列表
        :type classified_ids: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(classified_ids, (list, tuple)):
            classified_ids = ','.join(map(str, classified_ids))
        else:
            classified_ids = str(classified_ids)
        data = {'id': classified_ids}
        req_url = f'{self.base_url}/nf/object/url/classified/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除URL分类失败: {e}')
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

    def create_or_update_url_template(self, action='create', name='url_tmpl_1',
        note='', enable=True, tmpl_id='', url_class=None, url_class_name=None,
        url_class_id=None, url_class_describe=None, url_class_domain=None,
        url_class_keyword=None, url_class_type=None, url_class_backend_id=None,
        url_class_block=None, url_class_log=None):
        """创建或修改 URL 过滤模板。

        对应 UI 页面「对象 → URL 过滤模板」。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 模板名称
        :type name: str
        :param note: 备注
        :type note: str
        :param enable: 是否启用模板
        :type enable: bool
        :param tmpl_id: 模板 ID，编辑时必填
        :type tmpl_id: str
        :param url_class: URL 分类配置列表（dict list），每项含分类信息和 block/log 设置
        :type url_class: list or None
        :param url_class_name: URL 分类名称列表（未传 ``url_class`` 时使用）
        :type url_class_name: list or None
        :param url_class_id: URL 分类 ID 列表
        :type url_class_id: list or None
        :param url_class_describe: URL 分类描述列表
        :type url_class_describe: list or None
        :param url_class_domain: URL 分类域名列表
        :type url_class_domain: list or None
        :param url_class_keyword: URL 分类关键字列表
        :type url_class_keyword: list or None
        :param url_class_type: URL 分类类型列表
        :type url_class_type: list or None
        :param url_class_backend_id: URL 分类 backend_id 列表
        :type url_class_backend_id: list or None
        :param url_class_block: 是否阻断列表，每个对应一个分类
        :type url_class_block: list or bool or None
        :param url_class_log: 是否记录日志列表，每个对应一个分类
        :type url_class_log: list or bool or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if url_class is not None:
            if isinstance(url_class, dict):
                url_class = [url_class]
        else:
            if url_class_name is None:
                url_class_name = ['未知']
            elif isinstance(url_class_name, str):
                url_class_name = [url_class_name]
            if url_class_id is None:
                url_class_id = [1]
            elif isinstance(url_class_id, (int, str)):
                url_class_id = [url_class_id]
            if url_class_describe is None:
                url_class_describe = ['']
            elif isinstance(url_class_describe, str):
                url_class_describe = [url_class_describe]
            if url_class_domain is None:
                url_class_domain = [None]
            elif isinstance(url_class_domain, str):
                url_class_domain = [url_class_domain]
            if url_class_keyword is None:
                url_class_keyword = [None]
            elif isinstance(url_class_keyword, str):
                url_class_keyword = [url_class_keyword]
            if url_class_type is None:
                url_class_type = ['system']
            elif isinstance(url_class_type, str):
                url_class_type = [url_class_type]
            if url_class_backend_id is None:
                url_class_backend_id = ['0']
            elif isinstance(url_class_backend_id, (int, str)):
                url_class_backend_id = [url_class_backend_id]
        url_class_count = len(url_class_name
            ) if url_class_name is not None else len(url_class)
        if url_class_log is None:
            url_class_log = [True] * url_class_count
        elif isinstance(url_class_log, bool):
            url_class_log = [url_class_log] * url_class_count
        if url_class_block is None:
            url_class_block = [False] * url_class_count
        elif isinstance(url_class_block, bool):
            url_class_block = [url_class_block] * url_class_count
        url_classes = []
        if url_class is not None:
            for item, block, log_item in zip(url_class, url_class_block,
                url_class_log):
                item = dict(item)
                item.update({'block': block, 'log': log_item})
                url_classes.append(item)
        else:
            for u_name, u_id, u_des, u_dm, u_kw, u_type, u_back_id, u_blk, u_log in zip(
                url_class_name, url_class_id, url_class_describe,
                url_class_domain, url_class_keyword, url_class_type,
                url_class_backend_id, url_class_block, url_class_log):
                url_classes.append({'id': u_id, 'name': u_name, 'describe':
                    u_des, 'domain': u_dm, 'key_word': u_kw, 'type': u_type,
                    'backend_id': u_back_id, 'block': u_blk, 'log': u_log})
        data = {'id': tmpl_id, 'action': action, 'name': name, 'note': note,
            'enable': enable, 'url_class': url_classes}
        req_url = f'{self.base_url}/nf/object/url/template/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改URL模板失败: {e}')
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



    def create_url_temlates(self, id='', action='create', name='test', note='',
        enable=True, url_class=None):
        """创建 URL 模板（简化版，直接传入 url_class 列表）。

        对应 UI 页面「对象 → URL 过滤模板」。

        当 ``url_class`` 为 ``None`` 或空时，自动获取所有系统内置 URL 分类，
        以 ``block=False``、``log=True`` 填充，并自动去除 ``id=1``（"未知"分类）。

        :param id: 模板 ID，编辑时使用
        :type id: str
        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 模板名称
        :type name: str
        :param note: 备注
        :type note: str
        :param enable: 是否启用
        :type enable: bool
        :param url_class: URL 分类配置列表；为 ``None`` 或空时自动填充
        :type url_class: list or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if not url_class:
            class_list = self.get_url_class_list()
            if class_list is False:
                logger.error('自动填充 url_class 失败：获取 URL 分类列表失败')
                return False
            class_list = [c for c in class_list if c.get('id') != 1]
            logger.info(f'自动填充 url_class：去除 id=1 后共 {len(class_list)} 条')
            url_class = self.build_url_class_rules(class_list, block=False, log=True)
        data = {'id': id, 'action': action, 'name': name, 'note': note,
            'enable': enable, 'url_class': url_class }
        req_url = f'{self.base_url}/nf/object/url/template/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建URL模板失败: {e}')
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

    def remove_url_template(self, tmpl_ids):
        """删除 URL 过滤模板。

        对应 UI 页面「对象 → URL 过滤模板」。

        :param tmpl_ids: 模板 ID，单个值或列表
        :type tmpl_ids: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(tmpl_ids, (list, tuple)):
            tmpl_ids = ','.join(map(str, tmpl_ids))
        else:
            tmpl_ids = str(tmpl_ids)
        data = {'id': tmpl_ids}
        req_url = f'{self.base_url}/nf/object/url/template/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除URL模板失败: {e}')
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

    def get_url_template(self, page=1, size=10, search=''):
        """获取 URL 过滤模板列表。

        对应 UI 页面「对象 → URL 过滤模板」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典（``result.list`` 为模板列表），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/url/template/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取URL模板列表失败: {e}')
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

    def get_url_template_id(self, search='',page=1, size=10):
        """按名称查询 URL 过滤模板 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 模板名称
        :type search: str
        :return: 成功返回模板 id，失败返回 False
        :rtype: int or bool
        """
        resp = self.get_url_template(page=page, size=size, search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('id')
        return False

    def get_url_class_list(self, page=1, size=100000, search='', url_type='system'):
        """获取 URL 分类列表，返回 ``result.list`` 原始数据。

        对应 API 端点 ``/nf/object/url/classified/``（GET），返回的每项分类
        可直接作为 ``create_url_temlates`` 中 ``url_class`` 参数的元素。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``100000``（一次性取回全部）
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param url_type: 分类类型，``"system"`` = 系统内置，``"custom"`` = 自定义，默认 ``"system"``
        :type url_type: str
        :return: 成功返回分类列表 ``list[dict]``，失败返回 ``False``
        :rtype: list[dict] or bool
        """
        resp = self.get_url_class(page=page, size=size, search=search,
                                  url_type=url_type)
        if resp is False:
            return False
        result = resp.get('result', {})
        class_list = result.get('list', [])
        logger.info(f'获取URL分类：共 {len(class_list)} 条')
        return class_list

    def build_url_class_rules(self, class_list, block=False, log=True):
        """将 URL 分类列表组装为 ``create_url_temlates`` 的 ``url_class`` 参数格式。

        自动提取每项分类的 ``id``、``name``、``describe``、``domain``、
        ``key_word``、``type``、``backend_id`` 字段，并附加 ``block`` 和 ``log``。

        :param class_list: URL 分类列表，来自 ``get_url_class_list`` 的返回值
        :type class_list: list[dict]
        :param block: 是否阻断，默认 ``False``
        :type block: bool
        :param log: 是否记录日志，默认 ``True``
        :type log: bool
        :return: url_class 配置列表
        :rtype: list[dict]

        用法::

            class_list = nf.object.url.get_url_class_list()
            url_class = nf.object.url.build_url_class_rules(class_list, block=False, log=True)
            nf.object.url.create_url_temlates(name='url_test', url_class=url_class)
        """
        return [{
            'id': item.get('id'),
            'name': item.get('name'),
            'describe': item.get('describe', ''),
            'domain': item.get('domain'),
            'key_word': item.get('key_word'),
            'type': item.get('type', 'system'),
            'backend_id': item.get('backend_id'),
            'block': block,
            'log': log,
        } for item in class_list]
