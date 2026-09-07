"""初始化登录、修改密码及证书导入。"""

import sys
import requests
import json
import os
import base64
import logging
import glob

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class InitLoginCertImportFeature(NFRequests):
    """初始化登录、修改密码及证书导入操作集合。"""

    LOGIN_PATH = '/nf/accounts/login/'
    CHANGE_INIT_PASS = '/nf/accounts/change_init_password/'
    IMPORT_CERT = '/nf/cert/parse_upload_cert/'
    IMPORT_CERT_SUBMIT = '/nf/cert/import_cert/'

    def init_login_change_passwd(self, account_name="weboper", account_pwd="weboper",
                                  new_account_pwd="qwert12345"):
        """
        初始化登录并修改初始密码
        :param account_name: 账号名
        :param account_pwd: 初始密码
        :param new_account_pwd: 新密码
        :return: True 成功，False 失败
        """
        body = {"account_name": encrypt_msg(account_name), "account_pwd": encrypt_msg(account_pwd)}
        url = f'{self.base_url}{self.LOGIN_PATH}'
        try:
            result = self.session.post(url, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'账号：{account_name} 初始登录失败')
            logger.debug(e)
            return False
        if result.status_code != 200:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
        resp_data = json.loads(result.text)
        if resp_data.get("status") != 2000:
            logger.error(f'账号：{account_name} 初始登录失败: {resp_data.get("message")}')
            return False
        if not resp_data.get("result", {}).get("is_need_change_password"):
            logger.error('无需修改密码')
            return False
        # 修改密码
        body = {"account_name": account_name, "new_account_pwd": encrypt_msg(new_account_pwd)}
        self.session.headers.update({"X-csrftoken": self.session.cookies["csrftoken_vpp"]})
        url = f'{self.base_url}{self.CHANGE_INIT_PASS}'
        try:
            result = self.session.post(url, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'账号：{account_name} 修改密码请求失败')
            logger.debug(e)
            return False
        if result.status_code != 200:
            logger.error(f'修改密码HTTP请求失败，状态码: {result.status_code}')
            return False
        resp_data = json.loads(result.text)
        if resp_data.get("status") != 2000:
            logger.error(f'修改密码失败: {resp_data.get("message")}')
            return False
        # 用新密码重新登录
        body = {"account_name": encrypt_msg(account_name), "account_pwd": encrypt_msg(new_account_pwd)}
        url = f'{self.base_url}{self.LOGIN_PATH}'
        try:
            result = self.session.post(url, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'账号：{account_name} 新密码登录失败')
            logger.debug(e)
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            if resp_data.get("status") == 2000:
                logger.info('web登录密码修改成功')
                return True
        logger.error(f'新密码登录失败，HTTP状态码: {result.status_code}')
        return False

    def login_get_token(self, account_name="weboper", account_pwd="qwert12345"):
        """
        登录获取 token 和证书 hash
        :param account_name: 账号名
        :param account_pwd: 密码
        :return: [headers, cert_hash] 成功，False 失败
        """
        body = {"account_name": encrypt_msg(account_name), "account_pwd": encrypt_msg(account_pwd)}
        url = f'{self.base_url}{self.LOGIN_PATH}'
        try:
            result = self.session.post(url, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'账号：{account_name} 登录获取token失败')
            logger.debug(e)
            return False
        if result.status_code != 200:
            logger.error(f'登录获取token HTTP请求失败，状态码: {result.status_code}')
            return False
        resp_data = json.loads(result.text)
        if resp_data.get("status") == 2000:
            headers = {
                "X-csrftoken": self.session.cookies["csrftoken_vpp"],
                "Cookie": '; '.join(f'{c.name}={c.value}' for c in self.session.cookies)
            }
            cert_hash = resp_data["result"]["hash"]
            return [headers, cert_hash]
        else:
            logger.error(f'登录获取token失败: {resp_data.get("message")}')
            return False

    def change_password(self, headers, account_name="webpolicy", account_pwd="qwert12345"):
        """
        修改指定账号的密码
        :param headers: 请求头（包含已登录的 csrftoken 和 Cookie）
        :param account_name: 要修改密码的账号名
        :param account_pwd: 新密码
        :return: True 成功，False 失败
        """
        headers.update({"content-type": "application/json"})
        body = {"account_name": account_name, "new_account_pwd": encrypt_msg(account_pwd)}
        url = f'{self.base_url}{self.CHANGE_INIT_PASS}'
        try:
            result = self.session.post(url, json=body, headers=headers, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'账号：{account_name} 修改密码失败')
            logger.debug(e)
            return False
        if result.status_code != 200:
            logger.error(f'修改密码HTTP请求失败，状态码: {result.status_code}')
            return False
        resp_data = json.loads(result.text)
        if resp_data.get("status") == 2000:
            logger.info(f'账号：{account_name} 开启成功')
            return True
        else:
            logger.error(f'账号：{account_name} 修改密码失败: {resp_data.get("message")}')
            return False

    def import_license(self, headers, hash_val, filepath=None):
        """
        导入证书/license 文件
        :param headers: 请求头（包含已登录的 csrftoken 和 Cookie）
        :param hash_val: 证书 hash 值
        :param filepath: 证书文件所在目录路径，默认从环境变量 PYTHONPATH 拼接
        :return: True 成功，False 失败
        """
        if filepath is None:
            pwd = os.environ.get('PYTHONPATH', '')
            filepath = pwd + os.path.join("/tests_data/vpp/nf_test/002_auto_produce/004_nf_sync_time_and_init_web/")
        matched = glob.glob(os.path.join(filepath, "*" + hash_val + "*.lic"))
        if not matched:
            logger.error(f'未找到匹配的证书文件: {filepath} *{hash_val}*.lic')
            return False
        file_path_name = matched[0]
        file_name = os.path.basename(file_path_name)
        logger.info(f'证书文件名: {file_name}')
        try:
            with open(file_path_name, 'rb') as f:
                files = [('file', (file_name, f, 'application/octet-stream'))]
                result = self.session.post(
                    f'{self.base_url}{self.IMPORT_CERT}',
                    files=files,
                    headers=headers,
                    verify=False,
                    timeout=30
                )
        except Exception as e:
            logger.error(f'证书上传失败')
            logger.debug(e)
            return False
        if result.status_code != 200:
            logger.error(f'证书上传HTTP请求失败，状态码: {result.status_code}')
            return False
        resp_data = json.loads(result.text)
        if resp_data.get("status") != 2000:
            logger.error(f'证书上传失败: {resp_data.get("message")}')
            return False
        # 提交证书导入
        try:
            result = self.session.post(
                f'{self.base_url}{self.IMPORT_CERT_SUBMIT}',
                headers=headers,
                verify=False,
                timeout=30
            )
        except Exception as e:
            logger.error(f'证书导入提交失败')
            logger.debug(e)
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            if resp_data.get("status") == 2000:
                logger.info('证书导入成功')
                return True
        logger.error(f'证书导入提交失败，HTTP状态码: {result.text}')
        return False

    def init_login_cert_import(self, account_name="weboper", account_pwd="weboper",
                                new_account_pwd="qwert12345", filepath=None):
        """
        完整流程：初始化登录 → 修改密码 → 导入证书 → 开启 webpolicy/webaudit 账号
        :param account_name: 初始账号名
        :param account_pwd: 初始密码
        :param new_account_pwd: 新密码（用于所有账号）
        :param filepath: 证书文件路径
        :return: True 成功，False 失败
        """
        if not self.init_login_change_passwd(account_name, account_pwd, new_account_pwd):
            logger.error('初始化登录修改密码失败')
            return False
        data = self.login_get_token(account_name, new_account_pwd)
        if not data:
            logger.error('登录获取token失败')
            return False
        headers, hash_val = data[0], data[1]
        if not self.import_license(headers, hash_val, filepath):
            logger.error('证书导入失败')
            return False
        data = self.login_get_token(account_name, new_account_pwd)
        if not data:
            logger.error('证书导入后重新登录获取token失败')
            return False
        headers = data[0]
        self.change_password(headers, account_name="webpolicy", account_pwd=new_account_pwd)
        self.change_password(headers, account_name="webaudit", account_pwd=new_account_pwd)
        return True