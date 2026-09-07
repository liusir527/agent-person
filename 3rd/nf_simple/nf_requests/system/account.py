"""账号管理。"""

import sys
import requests
import json
import os
import base64
import logging

from ..nflib.Log import logger
from ..nflib.comm import *
from ..client import NFRequests


class AccountFeature(NFRequests):
    """账号管理操作集合。"""

    def create_account(self, account_name='autotest', account_pwd='qwert12345',
        auth_method='LOCAL', cert='', email='', ip='*', mac='', restrict_method
        ='ip', restrict_type='w', roles=None, status=None, account_type=None
        ):
        """新建账号。

        对应 UI 页面「系统 → 账号管理 → 新建」。

        .. note:: 密码会经 RSA 公钥加密后 Base64 编码再发送。

        :param account_name: 账号名称，默认 ``"autotest"``
        :param account_pwd: 账号密码（明文，内部自动 RSA 加密），默认
            ``"qwert12345"``
        :param auth_method: 认证方式，``"LOCAL"`` = 本地认证，
            ``"LOCALANDCERT"`` = 本地+证书认证，默认 ``"LOCAL"``
        :param cert: 证书，默认 ``""``
        :param email: 邮箱，默认 ``""``
        :param ip: IP 地址限制，``"*"`` 表示不限，默认 ``"*"``
        :param mac: MAC 地址限制，默认 ``""``
        :param restrict_method: 限制方式，``"ip"`` = IP 限制，``"mac"`` = MAC
            限制，默认 ``"ip"``
        :param restrict_type: 限制类型，``"w"`` = 白名单，``"b"`` = 黑名单，默认
            ``"w"``
        :param roles: 角色 ID（必填）
        :param status: 兼容旧调用的状态字段；OpenAPI 未声明，仅显式传入时发送
        :param account_type: 兼容旧调用的账号类型字段；OpenAPI 未声明，仅显式传入时
            发送
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        if roles is None:
            raise Exception('roles must be role id')
        account_pwd_encrypted = encrypt_msg(account_pwd
            ) if account_pwd is not None else encrypt_msg('qwert12345')
        data = {'account_name': account_name, 'account_pwd':
            account_pwd_encrypted, 'auth_method': auth_method, 'cert': cert,
            'email': email, 'ip': ip, 'mac': mac, 'restrict_method':
            restrict_method, 'restrict_type': restrict_type, 'roles': roles}
        if status is not None:
            data['status'] = status
        if account_type is not None:
            data['type'] = account_type
        url = f'{self.base_url}/nf/accounts/insert_account/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'创建账号失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def update_account(self, account_id=None, account_name='autotest', account_pwd=
        'qwert12345', auth_method='LOCAL', cert='', email='', ip='*', mac='',
        restrict_method='ip', restrict_type=None, roles=None, id=None):
        """编辑账号。

        对应 UI 页面「系统 → 账号管理 → 编辑」。

        .. note:: 密码会经 RSA 公钥加密后 Base64 编码再发送。

        :param account_id: 兼容旧调用的账号 ID，会映射为 ``id`` 字段
        :param account_name: 账号名称，默认 ``"autotest"``
        :param account_pwd: 账号密码（明文，内部自动 RSA 加密），默认
            ``"qwert12345"``
        :param auth_method: 认证方式，``"LOCAL"`` = 本地认证，
            ``"LOCALANDCERT"`` = 本地+证书认证，默认 ``"LOCAL"``
        :param cert: 证书，默认 ``""``
        :param email: 邮箱，默认 ``""``
        :param ip: IP 地址限制，``"*"`` 表示不限，默认 ``"*"``
        :param mac: MAC 地址限制，默认 ``""``
        :param restrict_method: 限制方式，``"ip"`` = IP 限制，``"mac"`` = MAC
            限制，默认 ``"ip"``
        :param restrict_type: 兼容旧调用的限制类型字段；OpenAPI 未声明，仅显式传入
            时发送
        :param roles: 角色 ID（必填）
        :param id: 账号 ID 字段，优先于 ``account_id``
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        if roles is None:
            raise Exception('roles must be role id')
        account_pwd_encrypted = encrypt_msg(account_pwd
            ) if account_pwd is not None else encrypt_msg('qwert12345')
        account_id = id if id is not None else account_id
        data = {'account_name': account_name, 'account_pwd':
            account_pwd_encrypted, 'auth_method': auth_method, 'cert': cert,
            'email': email, 'ip': ip, 'mac': mac, 'restrict_method':
            restrict_method, 'roles': roles, 'id': account_id}
        if restrict_type is not None:
            data['restrict_type'] = restrict_type
        url = f'{self.base_url}/nf/accounts/edit_account/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'更新账号失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def delete_account(self, account_id=None, id=None):
        """删除账号。

        对应 UI 页面「系统 → 账号管理 → 删除」。

        :param account_id: 兼容旧调用的账号 ID，会映射为 ``id`` 字段
        :param id: 账号 ID 字段，优先于 ``account_id``
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        account_id = id if id is not None else account_id
        url = f'{self.base_url}/nf/accounts/delete_account/'
        data = {'id': account_id}
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'删除账号失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def open_account(self, account='webpolicy', status='true', id=None):
        """启用或禁用账号。

        对应 UI 页面「系统 → 账号管理 → 启用/禁用」。

        :param account: 兼容旧调用的账号名称（通过 :meth:`get_account_id` 查询
            ID），默认 ``"webpolicy"``
        :param status: 账号状态，``"true"`` = 启用，``"false"`` = 禁用，默认
            ``"true"``
        :param id: 账号 ID 字段，优先于 ``account``（传入后不再查询账号名称）
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        id = id if id is not None else self.get_account_id(account=account)
        req_url = f'{self.base_url}/nf/accounts/change_account_status/'
        data = {'id': id, 'status': status}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'开启账号{account}失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status_code = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            print(message)
            if status_code == 2000:
                resp_data = json.loads(result.text)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def change_account_passwd(self, account='webpolicy', passwd='qwert12345',
        account_name=None, new_account_pwd=None):
        """初始化重置账号密码。

        对应 UI 页面「系统 → 账号管理 → 重置密码」。

        .. note:: 密码会经 RSA 公钥加密后 Base64 编码再发送。

        :param account: 兼容旧调用的账号名称，默认 ``"webpolicy"``
        :param passwd: 兼容旧调用的新密码明文，默认 ``"qwert12345"``
        :param account_name: 账号名称字段，优先于 ``account``
        :param new_account_pwd: 新密码明文字段（内部自动 RSA 加密），优先于
            ``passwd``
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        account_name = account_name if account_name is not None else account
        new_account_pwd = new_account_pwd if new_account_pwd is not None else passwd
        req_url = f'{self.base_url}/nf/accounts/change_init_password/'
        data = {'account_name': account_name, 'new_account_pwd': encrypt_msg(new_account_pwd)}
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'修改账号{account_name}密码失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status_code = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            print(data)
            print(message)
            if status_code == 2000:
                resp_data = json.loads(result.text)
                logger.info(f'修改账号{account_name}密码成功')
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def create_or_update_account(self, account_name='autotest', account_pwd=
        'qwert12345', auth_method='LOCAL', cert='', email='', ip='*', mac='',
        restrict_method='ip', restrict_type='w', roles=None, status=True,
        account_type='webpolicy', account_id=None, req_body=None):
        """创建或更新账号。

        自动判断：当 ``account_id`` 不为 ``None`` 时走编辑逻辑，否则走新建逻辑。

        .. note:: 密码会经 RSA 公钥加密后 Base64 编码再发送。

        :param account_name: 账号名称，默认 ``"autotest"``
        :param account_pwd: 账号密码（明文），默认 ``"qwert12345"``
        :param auth_method: 认证方式，``"LOCAL"`` 或 ``"LOCALANDCERT"``，默认
            ``"LOCAL"``
        :param cert: 证书，默认 ``""``
        :param email: 邮箱，默认 ``""``
        :param ip: IP 地址限制，默认 ``"*"``
        :param mac: MAC 地址限制，默认 ``""``
        :param restrict_method: 限制方式，``"ip"`` 或 ``"mac"``，默认 ``"ip"``
        :param restrict_type: 限制类型，``"w"`` = 白名单，``"b"`` = 黑名单，默认
            ``"w"``
        :param roles: 角色 ID（必填）
        :param status: 账号状态（仅新建时发送），默认 ``True``
        :param account_type: 账号类型（仅新建时发送），如 ``"webpolicy"``、
            ``"weboper"``、``"webaudit"``，默认 ``"webpolicy"``
        :param account_id: 账号 ID，传入时走编辑逻辑
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        if roles is None:
            msg = 'roles must be role id'
            logger.error(msg)
            return {"success": False, "message": msg}
        data = {'account_name': account_name, 'account_pwd': encrypt_msg(
            account_pwd), 'auth_method': auth_method, 'cert': cert, 'email':
            email, 'ip': ip, 'mac': mac, 'restrict_method': restrict_method,
            'restrict_type': restrict_type, 'roles': roles}
        if account_id is None:
            data['status'] = status
            data['type'] = account_type
        else:
            data['id'] = account_id
        if req_body is not None:
            data = req_body
        if 'id' in data.keys():
            req_url = f'{self.base_url}/nf/accounts/edit_account/'
        else:
            req_url = f'{self.base_url}/nf/accounts/insert_account/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'创建或更新账号失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def remove_account(self, account_id, req_body=None):
        """删除账号。

        :param account_id: 账号 ID
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'id': account_id} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/accounts/delete_account/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'删除账号失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_accounts(self, page=1, size=10, search='', tab_type='account_info',
        type='webpolicy'):
        """获取账号列表。

        对应 UI 页面「系统 → 账号管理」的账号列表。

        :param page: 页码，默认 ``1``
        :param size: 每页数量，默认 ``10``
        :param search: 搜索关键字，默认 ``""``
        :param tab_type: 账号页签类型，默认 ``"account_info"``
        :param type: 账号类型，``"webpolicy"`` = 策略配置员，
            ``"weboper"`` = 系统管理员，``"webaudit"`` = 审计员，默认
            ``"webpolicy"``
        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result.list`` 元素结构：::

                {
                    "id": 1,
                    "account_name": "weboper",
                    "auth_method": "LOCAL",
                    "ip": "*",
                    "restrict_type": "w",
                    "restrict_method": "ip",
                    "roles": {"name": "系统管理员", "id": 1},
                    "status": true,
                    "email": "weboper@example.com",
                    "type": "weboper"
                }
        """
        req_url = f'{self.base_url}/nf/accounts/get_account/'
        params = {'page': page, 'size': size, 'search': search,
            'tab_type': tab_type, 'type': type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            msg = f'获取账号列表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_account_id(self, account='webpolicy'):
        """根据账号名称查询账号 ID。

        通过调用 :meth:`get_accounts` 遍历 ``result.list`` 匹配
        ``account_name``。

        :param account: 账号名称，默认 ``"webpolicy"``
        :return: 匹配到的账号 ID（``int``）；未匹配时返回 ``None``
        """
        accounts_list = self.get_accounts()['result']['list']
        for i in accounts_list:
            if i['account_name'] == account:
                return i['id']
    def create_role(self, name='autotest', menu_id=None, desc='', log_menu=None):
        """新建角色。

        对应 UI 页面「系统 → 账号管理 → 角色 → 新建」。

        :param name: 角色名称，默认 ``"autotest"``
        :param menu_id: 菜单 ID 列表，可以是 ``int``、``str`` 或 ``list``，
            默认 ``[34, 35]``
        :param desc: 描述，默认 ``""``
        :param log_menu: 日志菜单权限列表，不传则不发送该字段
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        if menu_id is None:
            menu_id = [34, 35]
        elif isinstance(menu_id, (str, int)):
            menu_id = [int(menu_id)]
        data = {'desc': desc, 'menu_id': menu_id, 'name': name}
        if log_menu is not None:
            data['log_menu'] = log_menu
        url = f'{self.base_url}/nf/accounts/insert_role/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'创建角色失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def update_role(self, role_id=None, name=None, menu_id=None, desc='', id=None):
        """编辑角色。

        对应 UI 页面「系统 → 账号管理 → 角色 → 编辑」。

        :param role_id: 兼容旧调用的角色 ID，会映射为 ``id`` 字段
        :param name: 兼容旧调用的角色名称；OpenAPI 未声明，仅显式传入时发送
        :param menu_id: 菜单 ID 列表，可以是 ``int``、``str`` 或 ``list``，
            默认 ``[34, 35]``
        :param desc: 描述，默认 ``""``
        :param id: 角色 ID 字段，优先于 ``role_id``
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        if menu_id is None:
            menu_id = [34, 35]
        elif isinstance(menu_id, (str, int)):
            menu_id = [int(menu_id)]
        role_id = id if id is not None else role_id
        data = {'desc': desc, 'menu_id': menu_id, 'id': role_id}
        if name is not None:
            data['name'] = name
        url = f'{self.base_url}/nf/accounts/edit_roles/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'更新角色失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def delete_role(self, role_id=None, id=None):
        """删除角色。

        对应 UI 页面「系统 → 账号管理 → 角色 → 删除」。

        :param role_id: 兼容旧调用的角色 ID，会映射为 ``id`` 字段
        :param id: 角色 ID 字段，优先于 ``role_id``
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        role_id = id if id is not None else role_id
        url = f'{self.base_url}/nf/accounts/delete_role/'
        data = {'id': role_id}
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'删除角色失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return True
        else:
            msg = f'HTTP请求失败，状态码: {result.status_code}'
            logger.error(msg)
            return {"success": False, "message": msg}

    def create_or_update_role(self, name='autotest', menu_id=None, desc='',
        role_id=None, req_body=None):
        """创建或更新角色。

        自动判断：当 ``role_id`` 不为 ``None`` 时走编辑逻辑，否则走新建逻辑。

        :param name: 角色名称，默认 ``"autotest"``
        :param menu_id: 菜单 ID，可以是 ``int``、``str`` 或 ``list``，
            默认 ``[34, 35]``
        :param desc: 描述，默认 ``""``
        :param role_id: 角色 ID，传入时走编辑逻辑
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        if isinstance(menu_id, (str, int)):
            menu_id = [int(menu_id)]
        elif isinstance(menu_id, list):
            menu_id = menu_id
        elif menu_id is None:
            menu_id = [34, 35]
        else:
            msg = 'menu_id must be int or list'
            logger.error(msg)
            return {"success": False, "message": msg}
        data = {'desc': desc, 'menu_id': menu_id, 'name': name}
        if role_id is not None:
            data['id'] = role_id
        if req_body is not None:
            data = req_body
        if 'id' in data.keys():
            req_url = f'{self.base_url}/nf/accounts/edit_roles/'
        else:
            req_url = f'{self.base_url}/nf/accounts/insert_role/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'创建或更新角色失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def remove_role(self, role_id, req_body=None):
        """删除角色。

        :param role_id: 角色 ID
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'id': role_id} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/accounts/delete_role/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'删除角色失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_roles(self, tab_type='account_info', search=''):
        """获取角色列表。

        对应 UI 页面「系统 → 账号管理 → 角色」。

        :param tab_type: 页签类型，默认 ``"account_info"``
        :param search: 搜索关键字，默认 ``""``
        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result.data`` 元素结构：::

                {
                    "name": "系统管理员",
                    "desc": "系统管理员",
                    "id": 1,
                    "is_system": 1,
                    "auth": ["总览", "系统", ...],
                    "auth_log": [],
                    "accountNum": 1
                }
        """
        req_url = f'{self.base_url}/nf/accounts/get_roles/'
        params = {'tab_type': tab_type, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            msg = f'获取角色列表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}
