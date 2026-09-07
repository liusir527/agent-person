"""邮件安全、上网行为管理和敏感数据模板 CRUD。

对应 UI 页面「对象 → 内容安全」— 邮件安全 / 上网行为管理 / 敏感数据管理。
"""
import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class ScmObjectFeature(NFRequests):
    """SCM 对象操作集合 — 邮件安全、上网行为管理和敏感数据模板。"""

    def create_or_update_email_security_template(self, post_action='create',
        name='邮件安全', comment='', client_send=1, client_recv=0, http_send=0,
        http_recv=0, proto_pestore=0, send_key=None, recv_key=None, title_key=
        None, content_key=None, attach_key=None, event_level=0, action=0, log=1,
        tmpl_id=0):
        """创建或更新邮件安全模板。

        对应 UI 页面「对象 → 内容安全 → 邮件安全」。

        :param post_action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type post_action: str
        :param name: 模板名称
        :type name: str
        :param comment: 描述
        :type comment: str
        :param client_send: 客户端发送场景，``0`` = 关闭，``1`` = 开启
        :type client_send: int
        :param client_recv: 客户端接收场景
        :type client_recv: int
        :param http_send: HTTP 发送场景
        :type http_send: int
        :param http_recv: HTTP 接收场景
        :type http_recv: int
        :param proto_pestore: 协议存储
        :type proto_pestore: int
        :param send_key: 发件人关键字 ID 列表，默认 ``[0]``
        :type send_key: list or int or None
        :param recv_key: 收件人关键字 ID 列表，默认 ``[0]``
        :type recv_key: list or int or None
        :param title_key: 标题关键字 ID 列表，默认 ``[0]``
        :type title_key: list or int or None
        :param content_key: 正文关键字 ID 列表，默认 ``[0]``
        :type content_key: list or int or None
        :param attach_key: 附件关键字 ID 列表，默认 ``[0]``
        :type attach_key: list or int or None
        :param event_level: 事件等级，``0`` = 默认
        :type event_level: int
        :param action: 动作，``0`` = 放行，``1`` = 阻断
        :type action: int
        :param log: 是否记录日志，``0`` = 关闭，``1`` = 开启
        :type log: int
        :param tmpl_id: 模板 ID，编辑时使用
        :type tmpl_id: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if send_key is None:
            send_key = [0]
        elif isinstance(send_key, (int, str)):
            send_key = [send_key]
        if recv_key is None:
            recv_key = [0]
        elif isinstance(recv_key, (int, str)):
            recv_key = [recv_key]
        if title_key is None:
            title_key = [0]
        elif isinstance(title_key, (int, str)):
            title_key = [title_key]
        if content_key is None:
            content_key = [0]
        elif isinstance(content_key, (int, str)):
            content_key = [content_key]
        if attach_key is None:
            attach_key = [0]
        elif isinstance(attach_key, (int, str)):
            attach_key = [attach_key]
        data = {'post_action': post_action, 'name': name, 'comment': comment,
            'client_send': client_send, 'client_recv': client_recv, 'http_send':
            http_send, 'http_recv': http_recv, 'proto_pestore': proto_pestore,
            'event_level': event_level, 'action': action, 'log': log,
            'send_key': send_key, 'recv_key': recv_key, 'title_key': title_key,
            'content_key': content_key, 'attach_key': attach_key, 'id': tmpl_id}
        req_url = f'{self.base_url}/nf/object/scm/email/obj_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新邮件安全模板失败: {e}')
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

    def get_email_security_template(self, page=1, size=10, search=''):
        """获取邮件安全模板列表。

        对应 UI 页面「对象 → 内容安全 → 邮件安全」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/scm/email/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取邮件安全模板列表失败: {e}')
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
    def get_email_security_template_id(self,search='',page=1, size=10):
        """按名称查询邮件安全管理模板 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 要匹配的模板名称
        :type search: str
        :return: 成功返回模板 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_email_security_template(page=page, size=size, search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('id')
        return False

    def remove_email_security_template(self, tmpl_ids):
        """删除邮件安全模板。

        对应 UI 页面「对象 → 内容安全 → 邮件安全」。

        :param tmpl_ids: 模板 ID，支持单个值或列表
        :type tmpl_ids: int or str or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(tmpl_ids, (list, tuple)):
            tmpl_ids = [int(tmpl_id) for tmpl_id in tmpl_ids]
        elif isinstance(tmpl_ids, (int, str)):
            tmpl_ids = [int(tmpl_ids)]
        data = {'id': tmpl_ids}
        req_url = f'{self.base_url}/nf/object/scm/email/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除邮件安全模板失败: {e}')
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

    def create_or_update_obm_template(self, post_action='create', name='上网行为管理',
        comment='', log=0, scm_web_surf_enable=1, scm_web_surf_event_level=0,
        scm_web_surf_action=0, scm_web_surf_search_key=None,
        scm_web_surf_proto_restore=0, scm_web_surf_req_method=0,
        scm_web_surf_url_key=None, scm_web_surf_content_key=None,
        scm_web_post_enable=1, scm_web_post_event_level=0, scm_web_post_action=
        0, scm_web_post_url_key=None, scm_web_post_content_key=None,
        scm_web_post_title_key=None, scm_web_post_proto_restore=0,
        scm_im_enable=1, scm_im_event_level=0, scm_im_action=0, scm_im_msg_key=
        None, scm_im_user_key=None, scm_im_proto_restore=0, scm_server_enable=1,
        scm_server_event_level=0, scm_server_action=0, scm_server_cmd_key=None,
        scm_server_user_key=None, scm_server_proto_restore=0, scm_file_enable=1,
        scm_file_event_level=0, scm_file_action=0, scm_file_url_key=None,
        scm_file_file_name_key=None, scm_file_file_type_key=None,
        scm_file_file_content_key=None, scm_file_proto_restore=0, tmpl_id=None,
        scm_web_surf=None, scm_web_post=None, scm_im=None, scm_server=None,
        scm_file=None):
        """创建或修改上网行为管理模板。

        对应 UI 页面「对象 → 内容安全 → 上网行为管理」。

        :param post_action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type post_action: str
        :param name: 模板名称
        :type name: str
        :param comment: 备注
        :type comment: str
        :param log: 是否记录日志
        :type log: int
        :param tmpl_id: 模板 ID，编辑时使用
        :type tmpl_id: int or None
        :param scm_web_surf: 网页浏览完整配置 dict；传 ``None`` 时从各独立参数自动构建
        :type scm_web_surf: dict or None
        :param scm_web_post: 网页发布完整配置 dict；传 ``None`` 时从各独立参数自动构建
        :type scm_web_post: dict or None
        :param scm_im: 即时通讯完整配置 dict；传 ``None`` 时从各独立参数自动构建
        :type scm_im: dict or None
        :param scm_server: 服务端完整配置 dict；传 ``None`` 时从各独立参数自动构建
        :type scm_server: dict or None
        :param scm_file: 文件传输完整配置 dict；传 ``None`` 时从各独立参数自动构建
        :type scm_file: dict or None
        :param scm_web_surf_enable: 网页浏览启用
        :type scm_web_surf_enable: int
        :param scm_web_surf_event_level: 网页浏览事件等级
        :type scm_web_surf_event_level: int
        :param scm_web_surf_action: 网页浏览动作，``0`` = 放行
        :type scm_web_surf_action: int
        :param scm_web_surf_search_key: 搜索关键字 ID 列表
        :type scm_web_surf_search_key: int or list or None
        :param scm_web_surf_url_key: URL 关键字 ID 列表
        :type scm_web_surf_url_key: int or list or None
        :param scm_web_surf_content_key: 内容关键字 ID 列表
        :type scm_web_surf_content_key: int or list or None
        :param scm_web_surf_proto_restore: 协议还原
        :type scm_web_surf_proto_restore: int
        :param scm_web_surf_req_method: 请求方法
        :type scm_web_surf_req_method: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(scm_web_surf_search_key, int):
            scm_web_surf_search_key = [scm_web_surf_search_key]
        elif scm_web_surf_search_key is None:
            scm_web_surf_search_key = [0]
        if isinstance(scm_web_surf_url_key, int):
            scm_web_surf_url_key = [scm_web_surf_url_key]
        elif scm_web_surf_url_key is None:
            scm_web_surf_url_key = [0]
        if isinstance(scm_web_surf_content_key, int):
            scm_web_surf_content_key = [scm_web_surf_content_key]
        elif scm_web_surf_content_key is None:
            scm_web_surf_content_key = [0]
        if isinstance(scm_web_post_url_key, int):
            scm_web_post_url_key = [scm_web_post_url_key]
        elif scm_web_post_url_key is None:
            scm_web_post_url_key = [0]
        if isinstance(scm_web_post_content_key, int):
            scm_web_post_content_key = [scm_web_post_content_key]
        elif scm_web_post_content_key is None:
            scm_web_post_content_key = [0]
        if isinstance(scm_web_post_title_key, int):
            scm_web_post_title_key = [scm_web_post_title_key]
        elif scm_web_post_title_key is None:
            scm_web_post_title_key = [0]
        if isinstance(scm_im_msg_key, int):
            scm_im_msg_key = [scm_im_msg_key]
        elif scm_im_msg_key is None:
            scm_im_msg_key = [0]
        if isinstance(scm_im_user_key, int):
            scm_im_user_key = [scm_im_user_key]
        elif scm_im_user_key is None:
            scm_im_user_key = [0]
        if isinstance(scm_server_cmd_key, int):
            scm_server_cmd_key = [scm_server_cmd_key]
        elif scm_server_cmd_key is None:
            scm_server_cmd_key = [0]
        if isinstance(scm_server_user_key, int):
            scm_server_user_key = [scm_server_user_key]
        elif scm_server_user_key is None:
            scm_server_user_key = [0]
        if isinstance(scm_file_url_key, int):
            scm_file_url_key = [scm_file_url_key]
        elif scm_file_url_key is None:
            scm_file_url_key = [0]
        if isinstance(scm_file_file_name_key, int):
            scm_file_file_name_key = [scm_file_file_name_key]
        elif scm_file_file_name_key is None:
            scm_file_file_name_key = [0]
        if isinstance(scm_file_file_type_key, int):
            scm_file_file_type_key = [scm_file_file_type_key]
        elif scm_file_file_type_key is None:
            scm_file_file_type_key = [0]
        if isinstance(scm_file_file_content_key, int):
            scm_file_file_content_key = [scm_file_file_content_key]
        elif scm_file_file_content_key is None:
            scm_file_file_content_key = [0]
        if scm_web_surf is None:
            scm_web_surf = {'action': scm_web_surf_action, 'enable':
                scm_web_surf_enable, 'eventLevel': scm_web_surf_event_level,
                'urlKey': scm_web_surf_url_key, 'searchKey':
                scm_web_surf_search_key, 'contentKey': scm_web_surf_content_key,
                'reqMethod': scm_web_surf_req_method, 'protoRestore':
                scm_web_surf_proto_restore}
        if scm_web_post is None:
            scm_web_post = {'action': scm_web_post_action, 'enable':
                scm_web_post_enable, 'eventLevel': scm_web_post_event_level,
                'urlKey': scm_web_post_url_key, 'titleKey':
                scm_web_post_title_key, 'contentKey': scm_web_post_content_key,
                'protoRestore': scm_web_post_proto_restore}
        if scm_im is None:
            scm_im = {'action': scm_im_action, 'enable': scm_im_enable,
                'eventLevel': scm_im_event_level, 'msgKey': scm_im_msg_key,
                'userKey': scm_im_user_key, 'protoRestore': scm_im_proto_restore}
        if scm_server is None:
            scm_server = {'action': scm_server_action, 'enable':
                scm_server_enable, 'cmdKey': scm_server_cmd_key, 'userKey':
                scm_server_user_key, 'eventLevel': scm_server_event_level,
                'protoRestore': scm_server_proto_restore}
        if scm_file is None:
            scm_file = {'action': scm_file_action, 'enable': scm_file_enable,
                'eventLevel': scm_file_event_level, 'urlKey': scm_file_url_key,
                'fileNameKey': scm_file_file_name_key, 'fileTypeKey':
                scm_file_file_type_key, 'fileContentKey':
                scm_file_file_content_key, 'protoRestore': scm_file_proto_restore}
        data = {'post_action': post_action, 'name': name, 'comment': comment,
            'log': log, 'scm_web_surf': scm_web_surf, 'scm_web_post':
            scm_web_post, 'scm_im': scm_im, 'scm_server': scm_server,
            'scm_file': scm_file}
        if post_action == 'edit':
            data['id'] = tmpl_id
        req_url = f'{self.base_url}/nf/object/scm/obm/obj_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改上网行为管理模板失败: {e}')
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

    def get_obm_security_template(self, page=1, size=10, search=''):
        """获取上网行为管理模板列表。

        对应 UI 页面「对象 → 内容安全 → 上网行为管理」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/scm/obm/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取上网行为管理模板列表失败: {e}')
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

    def get_obm_security_template_id(self,search='', page=1, size=10):
        """按名称查询上网行为管理模板 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 要匹配的模板名称
        :type search: str
        :return: 成功返回模板 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_obm_security_template(page=page, size=size, search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('id')
        return False

    def remove_obm_template(self, tmpl_ids=None):
        """删除上网行为管理模板。

        对应 UI 页面「对象 → 内容安全 → 上网行为管理」。

        :param tmpl_ids: 模板 ID，支持单个值或列表；传 ``None`` 时删除全部
        :type tmpl_ids: int or str or list or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if tmpl_ids is not None:
            if isinstance(tmpl_ids, (list, tuple)):
                tmpl_ids = [int(tmpl_id) for tmpl_id in tmpl_ids]
            else:
                tmpl_ids = [int(tmpl_ids)]
            data = {'id': tmpl_ids}
        else:
            data = None
        req_url = f'{self.base_url}/nf/object/scm/obm/delete/'
        try:
            if data is None:
                result = self.session.post(req_url, verify=False, timeout=30)
            else:
                result = self.session.post(req_url, json=data, verify=False,
                    timeout=30)
        except Exception as e:
            logger.error(f'删除上网行为管理模板失败: {e}')
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

    def create_or_update_sensitive_data_template(self, post_action='create',
        name='敏感数据管理', comment='', check_web_post=0, check_im=0, check_mail=0,
        check_id_card=0, check_phone_num=0, check_social_num=0, key=None,
        event_level=0, log=0, action=1, tmpl_id=None):
        """创建或修改敏感数据管理模板。

        对应 UI 页面「对象 → 内容安全 → 敏感数据管理」。

        :param post_action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type post_action: str
        :param name: 模板名称
        :type name: str
        :param comment: 备注
        :type comment: str
        :param check_web_post: 是否检查网络言论发表
        :type check_web_post: int
        :param check_im: 是否检查即时通讯
        :type check_im: int
        :param check_mail: 是否检查邮件传递
        :type check_mail: int
        :param check_id_card: 是否检查身份证信息
        :type check_id_card: int
        :param check_phone_num: 是否检查手机号信息
        :type check_phone_num: int
        :param check_social_num: 是否检查社会保障信息号
        :type check_social_num: int
        :param key: 自定义敏感数据关键字 ID 列表，默认 ``[]``
        :type key: int or list or None
        :param event_level: 风险等级
        :type event_level: int
        :param log: 是否记录日志，``0`` = 关闭，``1`` = 开启
        :type log: int
        :param action: 动作，``0`` = 放行，``1`` = 阻断
        :type action: int
        :param tmpl_id: 模板 ID，编辑时使用
        :type tmpl_id: int or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(key, (int, str)):
            key = [key]
        elif key is None:
            key = []
        data = {'post_action': post_action, 'name': name, 'comment': comment,
            'check_web_post': check_web_post, 'check_im': check_im,
            'check_mail': check_mail, 'check_id_card': check_id_card,
            'check_phone_num': check_phone_num, 'check_social_num':
            check_social_num, 'event_level': event_level, 'action': action,
            'log': log, 'key': key}
        if post_action == 'edit':
            data['id'] = tmpl_id
        req_url = f'{self.base_url}/nf/object/scm/sensitive_data/obj_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改敏感数据模板失败: {e}')
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

    def get_sensitive_data_template(self, page=1, size=10, search=''):
        """获取敏感数据模板列表。

        对应 UI 页面「对象 → 内容安全 → 敏感数据管理」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/scm/sensitive_data/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取敏感数据模板列表失败: {e}')
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

    def remove_sensitive_data_template(self, tmpl_ids):
        """删除敏感数据模板。

        对应 UI 页面「对象 → 内容安全 → 敏感数据管理」。

        :param tmpl_ids: 模板 ID，支持单个值或列表
        :type tmpl_ids: int or str or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(tmpl_ids, (list, tuple)):
            tmpl_ids = [int(tmpl_id) for tmpl_id in tmpl_ids]
        else:
            tmpl_ids = [int(tmpl_ids)]
        data = {'id': tmpl_ids}
        req_url = f'{self.base_url}/nf/object/scm/sensitive_data/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除敏感数据模板失败: {e}')
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
