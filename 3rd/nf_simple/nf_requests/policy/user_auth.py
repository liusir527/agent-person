"""用户认证策略 — 用户认证全局配置、策略、免认证用户 IP 和账号配置管理。

对应 UI 页面「策略 → 用户认证」。

对应 API 文档中的 ``get_user_identify_global_config``、``update_user_identify_global_config``、
``get_user_identify``、``create_or_update_user_identify``、``remove_user_identify``、
``export_user_identify``、``get_no_auth_user``、``create_or_update_no_auth_user``、
``remove_no_auth_user``、``get_account_config``、``update_account_config``、
``get_user_identify_config``、``create_or_update_user_identify_config``。
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


class UserAuthFeature(NFRequests):
    """用户认证策略操作集合 — 用户认证策略、免认证 IP 和账号/本地认证配置。"""

    def get_global_auth_config(self):
        """获取用户认证全局配置。

        对应 API 文档中的 ``get_user_identify_global_config``。

        :return: 成功返回 ``{"status": 2000, "result": {"enable": bool, "auth_timeout": int}}``，
            失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/strategy/userIdentify/get_global_config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取用户认证全局配置失败: {e}')
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

    def update_global_auth_config(self, auth_port=4430, auth_time_out=0,
        auth_addr='0.0.0.0', enable=False, req_body=None):
        """更新用户认证全局配置。

        对应 API 文档中的 ``update_user_identify_global_config``。

        :param auth_port: 认证端口，默认 ``4430``
        :type auth_port: int
        :param auth_time_out: 认证超时时间（秒）
        :type auth_time_out: int
        :param auth_addr: 认证地址
        :type auth_addr: str
        :param enable: 是否启用认证
        :type enable: bool
        :param req_body: 自定义请求体，传入后覆盖默认参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        data = {'authPort': auth_port, 'authTimeOut': auth_time_out, 'authAddr':
            auth_addr, 'enable': enable}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/strategy/userIdentify/update_global_config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新用户认证全局配置失败: {e}')
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

    def get_auth_config(self):
        """获取账号配置（认证超时、最大在线用户等）。

        对应 API 文档中的 ``get_account_config``。

        :return: 成功返回 ``{"status": 2000, "result": {"auth_timeout": int, "max_online": int}}``，
            失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/accounts/get_account_config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取认证配置失败: {e}')
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

    def update_auth_config(self, handle_method='ip', login_fail_count='3',
        login_fail_lock_time='3', login_overtime='600', max_inline_user_num=
        '20', max_login_link_num='0', min_password_length='6',
        password_complexity='2', password_effect_time='0', req_body=None):
        """更新账号认证配置。

        对应 API 文档中的 ``update_account_config``。

        :param handle_method: 处理方式，默认 ``"ip"``
        :type handle_method: str
        :param login_fail_count: 登录失败次数阈值
        :type login_fail_count: str
        :param login_fail_lock_time: 登录失败锁定时间（分钟）
        :type login_fail_lock_time: str
        :param login_overtime: 登录超时时间（秒）
        :type login_overtime: str
        :param max_inline_user_num: 最大同时在线用户数
        :type max_inline_user_num: str
        :param max_login_link_num: 最大登录连接数
        :type max_login_link_num: str
        :param min_password_length: 最小密码长度
        :type min_password_length: str
        :param password_complexity: 密码复杂度要求
        :type password_complexity: str
        :param password_effect_time: 密码有效期（天）
        :type password_effect_time: str
        :param req_body: 自定义请求体，传入后覆盖默认参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        data = {'handle_method': handle_method, 'login_fail_count':
            login_fail_count, 'login_fail_lock_time': login_fail_lock_time,
            'login_overtime': login_overtime, 'max_inline_user_num':
            max_inline_user_num, 'max_login_link_num': max_login_link_num,
            'min_password_length': min_password_length, 'password_complexity':
            password_complexity, 'password_effect_time': password_effect_time}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/accounts/update_account_config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新认证配置失败: {e}')
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

    def update_local_auth_config(self, min_pass=6, level=1,
        is_update_default_pass=False, ca='', is_img_code=False,
        is_ident_fail_strategy=False, fail_num=3, much_fail='user', sock_time=3):
        """更新本地用户识别/认证配置。

        对应 API 文档中的 ``create_or_update_user_identify_config``。

        :param min_pass: 最小密码长度，默认 ``6``
        :type min_pass: int
        :param level: 密码复杂度等级
        :type level: int
        :param is_update_default_pass: 是否更新默认密码
        :type is_update_default_pass: bool
        :param ca: CA 证书
        :type ca: str
        :param is_img_code: 是否启用验证码
        :type is_img_code: bool
        :param is_ident_fail_strategy: 是否启用登录失败策略
        :type is_ident_fail_strategy: bool
        :param fail_num: 失败次数阈值，默认 ``3``
        :type fail_num: int
        :param much_fail: 失败处理方式，默认 ``"user"``
        :type much_fail: str
        :param sock_time: 锁定时间（秒），默认 ``3``
        :type sock_time: int
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        data = {'minPass': min_pass, 'level': level, 'isUpdateDefaultPass':
            is_update_default_pass, 'ca': ca, 'isImgCode': is_img_code,
            'isIdentFailStragy': is_ident_fail_strategy, 'failNum': fail_num,
            'muchFail': much_fail, 'sockTime': sock_time}
        req_url = f'{self.base_url}/nf/object/user/identify/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新本地认证配置失败: {e}')
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

    def get_local_auth_config(self):
        """获取本地用户识别/认证配置。

        对应 API 文档中的 ``get_user_identify_config``。

        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/user/identify/info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取本地认证配置失败: {e}')
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

    def create_or_update_user_auth_policy(self, action='create', name=
        'auth_policy', src_zone=None, dst_zone=None, src_net_objs=None,
        dst_net_objs=None, time_objs=None, is_forbidden=0, is_log=0, is_need=
        True, comment='', user_auth_id=None, pri=None, req_body=None):
        """创建或更新用户认证策略。

        对应 API 文档中的 ``create_or_update_user_identify``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param name: 策略名称
        :type name: str
        :param src_zone: 源安全区列表，可为 ``str`` / ``list``
        :type src_zone: str or list or None
        :param dst_zone: 目的安全区列表，可为 ``str`` / ``list``
        :type dst_zone: str or list or None
        :param src_net_objs: 源网络对象 ID 列表
        :type src_net_objs: str or int or list or None
        :param dst_net_objs: 目的网络对象 ID 列表
        :type dst_net_objs: str or int or list or None
        :param time_objs: 时间对象 ID 列表
        :type time_objs: str or int or list or None
        :param is_forbidden: 是否禁止，``0`` 或 ``1``
        :type is_forbidden: int
        :param is_log: 是否记录日志，``0`` 或 ``1``
        :type is_log: int
        :param is_need: 是否需要进行认证
        :type is_need: bool
        :param comment: 备注
        :type comment: str
        :param user_auth_id: 编辑时的策略 ID
        :type user_auth_id: int or None
        :param pri: 编辑时的优先级
        :type pri: int or None
        :param req_body: 自定义请求体，传入后覆盖默认参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(src_zone, str):
            src_zone = [src_zone]
        elif src_zone is None:
            src_zone = ['TRUST']
        if isinstance(dst_zone, str):
            dst_zone = [dst_zone]
        elif dst_zone is None:
            dst_zone = ['TRUST']
        if isinstance(src_net_objs, (str, int)):
            src_net_objs = [int(src_net_objs)]
        elif isinstance(src_net_objs, list):
            src_net_objs = [int(x) for x in src_net_objs]
        elif src_net_objs is None:
            src_net_objs = [100000]
        if isinstance(dst_net_objs, (str, int)):
            dst_net_objs = [int(dst_net_objs)]
        elif isinstance(dst_net_objs, list):
            dst_net_objs = [int(x) for x in dst_net_objs]
        elif dst_net_objs is None:
            dst_net_objs = [100000]
        if isinstance(time_objs, (str, int)):
            time_objs = [int(time_objs)]
        elif isinstance(time_objs, list):
            time_objs = [int(x) for x in time_objs]
        elif time_objs is None:
            time_objs = [800000]
        data = {'action': action, 'name': name, 'srcZone': src_zone, 'dstZone':
            dst_zone, 'srcNetObjs': src_net_objs, 'dstNetObjs': dst_net_objs,
            'timeObjs': time_objs, 'comment': comment, 'isForbidden':
            is_forbidden, 'isLog': is_log, 'isNeed': is_need}
        if action == 'edit':
            data['id'] = user_auth_id
            data['pri'] = pri
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/strategy/userIdentify/config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新用户认证策略失败: {e}')
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

    def get_user_auth_policy(self, page=1, size=10, search=''):
        """获取用户认证策略列表。

        对应 API 文档中的 ``get_user_identify``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/strategy/userIdentify/info/'
        params = {'size': size, 'page': page, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取用户认证策略列表失败: {e}')
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

    def remove_user_auth(self, policy_id, req_body=None):
        """删除用户认证策略。

        对应 API 文档中的 ``remove_user_identify``。

        :param policy_id: 策略 ID，可为单个 ``int`` 或 ``list``/``tuple``
        :type policy_id: int or list or tuple
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(policy_id, (list, tuple)):
            policy_ids = [int(x) for x in policy_id]
        else:
            policy_ids = [int(policy_id)]
        data = {'id': policy_ids}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/strategy/userIdentify/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除用户认证策略失败: {e}')
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

    def export_user_auth_policy(self):
        """导出用户认证策略。

        对应 API 文档中的 ``export_user_identify``。

        :return: 成功返回导出文本内容（str），失败返回 False
        :rtype: str or bool
        """
        req_url = f'{self.base_url}/nf/strategy/userIdentify/export/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出用户认证策略失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出用户认证策略成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def create_or_update_no_auth_user_ip(self, action='create', user_ip=
        '0.0.0.0', address_flag=0, user_ip_id=None, req_body=None):
        """创建或更新免认证用户 IP。

        对应 API 文档中的 ``create_or_update_no_auth_user``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param user_ip: 用户 IP 地址
        :type user_ip: str
        :param address_flag: 地址标志
        :type address_flag: int
        :param user_ip_id: 免认证 ID，编辑时传入
        :type user_ip_id: int or None
        :param req_body: 自定义请求体，传入后覆盖默认参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        data = {'userIp': user_ip, 'addressFlag': address_flag, 'action': action}
        if user_ip_id is not None:
            data['userIpId'] = user_ip_id
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/strategy/noAuthUserIp/config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新免认证用户IP失败: {e}')
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

    def get_no_auth_user_ip(self, page=1, size=10, search=''):
        """获取免认证用户 IP 列表。

        对应 API 文档中的 ``get_no_auth_user``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/strategy/noAuthUserIp/info/'
        params = {'size': size, 'page': page, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取免认证用户IP列表失败: {e}')
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

    def remove_no_auth_user_ip(self, user_ip_id, req_body=None):
        """删除免认证用户 IP。

        对应 API 文档中的 ``remove_no_auth_user``。

        :param user_ip_id: 免认证 ID，可为单个 ``int``/``str`` 或 ``list``
        :type user_ip_id: int or str or list or tuple
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(user_ip_id, (list, tuple)):
            user_ip_id = [str(x) for x in user_ip_id]
        else:
            user_ip_id = [str(user_ip_id)]
        data = {'id': user_ip_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/strategy/noAuthUserIp/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除免认证用户IP失败: {e}')
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
