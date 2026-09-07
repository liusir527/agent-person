"""管理员登录退出。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class AuthFeature(NFRequests):
    """管理员登录退出操作集合。"""

    def manager_login(self, username=None, password='qwert12345',
        account_name=None, account_pwd=None):
        """用户登录。

        对应 UI 页面「登录页 → 用户登录」。

        登录成功后自动将响应 Cookie 中的 ``csrftoken_vpp`` 写入后续请求头
        ``X-csrftoken``。

        :param username: 兼容旧调用的用户名，如 ``"webpolicy"``, ``"weboper"``,
            ``"admin"``
        :param password: 兼容旧调用的密码明文，默认 ``"qwert12345"``
        :param account_name: 账号名字段（RSA 加密后 Base64），优先于 ``username``
        :param account_pwd: 密码明文字段（RSA 加密后 Base64），优先于 ``password``
        :return: 成功返回 ``requests.Session`` 对象（已设置 Cookie 和
            ``X-csrftoken`` 头）；失败返回 ``False``
        """
        account_name = account_name if account_name is not None else username
        account_pwd = account_pwd if account_pwd is not None else password
        data = {'account_name': encrypt_msg(account_name), 'account_pwd':
            encrypt_msg(account_pwd)}
        url = f'{self.base_url}/nf/accounts/login/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'账号：{account_name} 登录失败')
            logger.debug(e)
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(f'账号：{account_name} 登录失败')
                logger.error(message)
                return False
            else:
                logger.info(f'账号：{account_name} 登录成功')
                self.session.headers.update({'X-csrftoken': self.session.
                    cookies['csrftoken_vpp']})
                return self.session
        logger.error(f'账号：{account_name} 登录失败')
        return False

    def manager_logout(self, req_body=None):
        """用户退出。

        对应 UI 页面「首页 → 退出登录」。

        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回 ``True``，失败返回 ``False``
        """
        data = {'url': '/'}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/accounts/logout/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'退出登录失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            else:
                logger.info(f'账号退出登录成功: {message}')
                return True
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
