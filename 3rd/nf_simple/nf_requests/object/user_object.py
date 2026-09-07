"""用户对象 — 用户、用户组、域和外部认证服务器 CRUD。

对应 UI 页面「对象 → 用户对象」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import encrypt_msg
from ..client import NFRequests


class UserObjectFeature(NFRequests):
    """用户对象操作集合 — 用户、用户组、域和外部认证服务器的增删查改。"""

    def create_or_update_user_obj(self, action='create', group_name='test',
        username='user1', password='qwert12345', real_name='', email='', note=
        '', status=True, user_id=None):
        """创建或编辑用户对象。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param group_name: 用户组名称（通过 [`get_user_grp_id`](#get_user_grp_id) 按名称查询 ID）
        :type group_name: str
        :param username: 用户名
        :type username: str
        :param password: 密码（RSA 加密后 Base64），默认 ``"qwert12345"``
        :type password: str
        :param real_name: 真实姓名
        :type real_name: str
        :param email: 邮箱
        :type email: str
        :param note: 备注
        :type note: str
        :param status: 状态，``True`` = 启用，``False`` = 禁用
        :type status: bool
        :param user_id: 编辑时必填，用户 ID
        :type user_id: int or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        group = self.get_user_grp_id(search=group_name)
        data = {'group': group, 'username': username, 'password': encrypt_msg(
            password) if password is not None else encrypt_msg('qwert12345'),
            'realname': real_name, 'email': email, 'note': note, 'status': str(
            status).lower(), 'action': action}
        if action == 'edit':
            data['id'] = user_id
        req_url = f'{self.base_url}/nf/object/user/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改用户对象失败: {e}')
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

    def get_user_obj(self, page=1, size=50, search=''):
        """获取用户对象列表。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典（含 ``result.list`` 和 ``result.total``），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/user/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取用户对象列表失败: {e}')
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

    def get_user_obj_id(self, page=1, size=50, search=''):
        """按名称查询用户对象所属组 ID。

        内部调用 [`get_user_obj`](#get_user_obj)，当返回结果只有一条匹配时直接返回该用户的 ``group.id``；
        否则遍历列表找到 ``group.name`` 与 search 匹配的条目。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 用户名或组名关键字
        :type search: str
        :return: 成功返回用户组 ID（int），失败返回 False
        :rtype: int or bool
        """
        resp = self.get_user_obj(page=page, size=size, search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        if result['total'] == 1:
            return result['list'][0]['group']['id']
        for i in result.get('list', []):
            if i.get('group', {}).get('name') == search:
                return i['group']['id']
        return False

    def remove_user_obj(self, user_id):
        """删除用户对象。

        :param user_id: 用户 ID 或 ID 列表
        :type user_id: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        :raises ValueError: 当 user_id 类型不是 int/str/list 时抛出
        """
        if isinstance(user_id, (int, str)):
            user_ids = [user_id]
        elif isinstance(user_id, list):
            user_ids = [int(x) for x in user_id]
        else:
            raise ValueError('user_id must be int or list[int]')
        data = {'id': user_ids}
        req_url = f'{self.base_url}/nf/object/user/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除用户对象失败: {e}')
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

    def get_user_home_view(self):
        """获取用户首页视图。

        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/user_homeviews/info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取用户首页视图失败: {e}')
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

    def create_or_update_user_grp(self, action='create', name='grp1', domain=
        None, note='', grp_id=None):
        """创建或编辑用户组。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 用户组名称
        :type name: str
        :param domain: 关联域 ID 列表，默认 ``[1]``
        :type domain: list[int] or int or None
        :param note: 备注
        :type note: str
        :param grp_id: 编辑时必填，用户组 ID
        :type grp_id: int or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if domain is None:
            domain = [1]
        elif isinstance(domain, (int, str)):
            domain = [int(domain)]
        data = {'action': action, 'name': name, 'domain': domain, 'note': note}
        if action == 'edit':
            data['id'] = grp_id
        req_url = f'{self.base_url}/nf/object/user_group/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改用户组失败: {e}')
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

    def get_user_grp(self, page=1, size=10, search=''):
        """获取用户组列表。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典（含 ``result.list`` 和 ``result.total``），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/user_group/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取用户组列表失败: {e}')
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

    def get_user_grp_id(self, page=1, size=10, search=''):
        """按名称查询用户组 ID。

        内部调用 [`get_user_grp`](#get_user_grp)，当返回结果只有一条匹配时直接返回该记录的 ``id``；
        否则遍历列表找到 ``name`` 与 search 匹配的条目。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 用户组名称关键字
        :type search: str
        :return: 成功返回用户组 ID（int），失败返回 False
        :rtype: int or bool
        """
        resp = self.get_user_grp(page=page, size=size, search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        if result['total'] == 1:
            return result['list'][0]['id']
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('id')
        return False

    def remove_user_grp(self, grp_id):
        """删除用户组。

        :param grp_id: 用户组 ID 或 ID 列表
        :type grp_id: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        :raises ValueError: 当 grp_id 类型不是 int/str/list 时抛出
        """
        if isinstance(grp_id, (int, str)):
            grp_ids = [grp_id]
        elif isinstance(grp_id, list):
            grp_ids = [int(x) for x in grp_id]
        else:
            raise ValueError('grp_id must be int or list[int]')
        data = {'id': grp_ids}
        req_url = f'{self.base_url}/nf/object/user_group/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除用户组失败: {e}')
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

    def get_user_access_status(self, page=1, size=10, search=''):
        """获取用户认证访问信息。

        对应 API 文档中的 ``get_user_auth_access``。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/strategy/userAuthAcess/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取用户接入状态失败: {e}')
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

    def create_or_update_auth_domain(self, action='create', name='auth_domain',
        auth_type=0, note='', server=None, status=True, auth_method=None,
        scenario=None, domain_id=None):
        """创建或编辑认证域。

        对应 API 文档中的 ``create_or_update_user_domain``。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param name: 域名称
        :type name: str
        :param auth_type: 认证类型，``0`` = 本地认证
        :type auth_type: int
        :param note: 备注
        :type note: str
        :param server: 认证服务器列表，默认 ``["Localhost"]``
        :type server: list or str or None
        :param status: 状态，``True`` = 启用，``False`` = 禁用
        :type status: bool
        :param auth_method: 认证方式列表，默认 ``[1]``
        :type auth_method: list or int or None
        :param scenario: 场景列表，默认 ``[1, 2, 3]``
        :type scenario: list or int or None
        :param domain_id: 编辑时必填，域 ID
        :type domain_id: int or None
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(server, (str, int)):
            server = [server]
        elif server is None:
            server = ['Localhost']
        if isinstance(scenario, list):
            pass
        elif isinstance(scenario, (str, int)):
            scenario = [scenario]
        elif scenario is None:
            scenario = [1, 2, 3]
        if isinstance(auth_method, list):
            pass
        elif isinstance(auth_method, (str, int)):
            auth_method = [auth_method]
        elif auth_method is None:
            auth_method = [1]
        data = {'action': action, 'name': name, 'note': note, 'server': server,
            'status': status, 'type': auth_type, 'scenario': scenario,
            'auth_method': auth_method}
        if action == 'edit':
            data['id'] = domain_id
        req_url = f'{self.base_url}/nf/object/domain/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改认证域失败: {e}')
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

    def get_auth_domain(self, page=1, size=10, search=''):
        """获取认证域列表。

        对应 API 文档中的 ``get_user_domain``。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/domain/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取认证域列表失败: {e}')
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

    def remove_auth_domain(self, domain_id):
        """删除认证域。

        对应 API 文档中的 ``remove_user_domain``。

        :param domain_id: 域 ID 或 ID 列表
        :type domain_id: int or str or list
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if isinstance(domain_id, list):
            domain_ids = [int(x) for x in domain_id]
        elif isinstance(domain_id, (int, str)):
            domain_ids = [int(domain_id)]
        else:
            domain_ids = []
        data = {'id': domain_ids}
        req_url = f'{self.base_url}/nf/object/domain/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除认证域失败: {e}')
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

    def create_or_update_ext_auth_server(self, action='create', server_type=
        'radius', name='auth_server1', ip='1.1.1.1', port=162, overtime=5,
        auth_method='pap', auth_pk='1234567890', base_dn='', username='',
        password='', server_id=''):
        """创建或编辑外部认证服务器。

        对应 API 文档中的 ``create_or_update_user_exidentify``。

        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑
        :type action: str
        :param server_type: 服务器类型，``"radius"`` = RADIUS，``"ldap"`` = LDAP
        :type server_type: str
        :param name: 服务器名称
        :type name: str
        :param ip: 服务器 IP 地址
        :type ip: str
        :param port: 服务器端口
        :type port: int
        :param overtime: 超时时间（秒）
        :type overtime: int
        :param auth_method: 认证方法，如 ``"pap"``、``"chap"``
        :type auth_method: str
        :param auth_pk: 认证密钥
        :type auth_pk: str
        :param base_dn: LDAP 基础 DN（LDAP 类型使用）
        :type base_dn: str
        :param username: 用户名（LDAP 类型使用）
        :type username: str
        :param password: 密码（LDAP 类型使用）
        :type password: str
        :param server_id: 编辑时必填，服务器 ID
        :type server_id: str or int
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        if server_id is None and action == 'create':
            server_id = ''
        data = {'action': action, 'name': name, 'serverType': server_type, 'ip':
            ip, 'port': port, 'overtime': overtime, 'authMethod': auth_method,
            'authPk': auth_pk, 'baseDN': base_dn, 'username': username,
            'password': password, 'id': server_id}
        req_url = f'{self.base_url}/nf/object/user/exidentify/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改外部认证服务器失败: {e}')
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

    def get_ext_auth_server(self, page=1, size=10, search='', srv_type='radius'):
        """获取外部认证服务器列表。

        对应 API 文档中的 ``get_user_exidentify``。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :param srv_type: 服务器类型，``"radius"`` = RADIUS，``"ldap"`` = LDAP
        :type srv_type: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/user/exidentify/info/'
        params = {'page': page, 'size': size, 'search': search, 'type': srv_type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取外部认证服务器列表失败: {e}')
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

    def remove_ext_auth_server(self, srv_id, srv_type='radius'):
        """删除外部认证服务器。

        对应 API 文档中的 ``remove_user_exidentify``。

        :param srv_id: 服务器 ID 或 ID 列表
        :type srv_id: int or str or list
        :param srv_type: 服务器类型，``"radius"`` = RADIUS，``"ldap"`` = LDAP
        :type srv_type: str
        :return: 成功返回 API 响应字典，失败返回 False
        :rtype: dict or bool
        """
        data = {'type': srv_type, 'id': srv_id}
        req_url = f'{self.base_url}/nf/object/user/exidentify/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除外部认证服务器失败: {e}')
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