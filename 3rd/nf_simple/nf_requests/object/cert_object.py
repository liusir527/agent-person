"""证书对象 — CA 证书、数字证书、证书请求文件管理。

对应 UI 页面「系统 → 证书管理」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class CertObjectFeature(NFRequests):
    """证书对象操作集合 — CA 证书、数字证书、证书请求文件的增删查导出。"""

    def create_ca_cert(self, action='create', name='sslvpn_ca', algorithm_type=
        'RSA', country='CN', province='', city='', company='', department='',
        email='', cipher_length=None, user_type='vpnuser', exist_private=True):
        """创建 CA 证书。

        对应 UI 页面「系统 → 证书管理 → CA 证书」。

        :param action: 操作类型，``"create"`` = 新建
        :type action: str
        :param name: CA 证书名称
        :type name: str
        :param algorithm_type: 算法类型，``"RSA"`` = RSA，``"SM2"`` = SM2 国密
        :type algorithm_type: str
        :param country: 国家代码
        :type country: str
        :param province: 省份
        :type province: str
        :param city: 城市
        :type city: str
        :param company: 公司
        :type company: str
        :param department: 部门
        :type department: str
        :param email: 邮箱地址
        :type email: str
        :param cipher_length: 密钥长度，RSA 默认 ``2048``，SM2 默认 ``256``；传 ``None`` 时根据算法类型自动选择
        :type cipher_length: int or None
        :param user_type: 用户类型，默认 ``"vpnuser"``
        :type user_type: str
        :param exist_private: 是否存在私钥
        :type exist_private: bool
        :return: 成功返回 API 响应 dict（包含 ``status``、``message`` 和 ``result`` 字段），失败返回 ``False``
        :rtype: dict or bool
        """
        if cipher_length is None:
            cipher_length = 256 if algorithm_type == 'SM2' else 2048
        data = {'name': name, 'action': action, 'algorithm_type':
            algorithm_type, 'country': country, 'city': city, 'province':
            province, 'company': company, 'department': department, 'email':
            email, 'cipher_length': cipher_length, 'userType': user_type,
            'exist_private': exist_private}
        req_url = f'{self.base_url}/nf/cert/ca/action_cert/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建CA证书失败: {e}')
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

    def get_ca_cert(self, page=1, size=10, search=''):
        """获取 CA 证书列表。

        对应 UI 页面「系统 → 证书管理 → CA 证书」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，``result.list`` 中每条记录含 ``id``、``name``、``algorithm_type``、
            ``country``、``province``、``city``、``company``、``department``、``email``、
            ``cipher_length``、``userType``、``exist_private`` 等字段；失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/cert/ca/cert_info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取CA证书列表失败: {e}')
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

    def get_ca_cert_id(self, page=1, size=10, search=''):
        """按名称查询 CA 证书 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 要匹配的 CA 证书名称
        :type search: str
        :return: 成功返回证书 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_ca_cert(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_ca_cert(self, cert_id):
        """删除 CA 证书。

        对应 UI 页面「系统 → 证书管理 → CA 证书」。

        :param cert_id: 证书 ID，支持单个值或列表；多个 ID 以逗号分隔发送
        :type cert_id: str or int or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(cert_id, list):
            cert_ids = ','.join([str(c_id) for c_id in cert_id])
        else:
            cert_ids = str(cert_id)
        data = {'id': cert_ids}
        req_url = f'{self.base_url}/nf/cert/ca/delete_cert/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除CA证书失败: {e}')
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

    def get_cert_content(self, name='sslvpn_ca', cert_type='root_cert',
        user_type='vpnuser'):
        """获取证书内容。

        :param name: 证书名称
        :type name: str
        :param cert_type: 证书类型，默认 ``"root_cert"``
        :type cert_type: str
        :param user_type: 用户类型，默认 ``"vpnuser"``
        :type user_type: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/cert/views/'
        params = {'name': name, 'type': cert_type, 'userType': user_type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取证书内容失败: {e}')
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

    def export_ca_cert(self, cert_id):
        """导出 CA 证书。

        对应 UI 页面「系统 → 证书管理 → CA 证书」。

        :param cert_id: CA 证书 ID
        :type cert_id: str or int
        :return: 成功返回证书文本内容（str），失败返回 ``False``
        :rtype: str or bool
        """
        req_url = f'{self.base_url}/nf/cert/ca/export/'
        params = {'id': cert_id}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'导出CA证书失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出CA证书成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def create_digital_cert(self, action='create', name='cert_req_file',
        algorithm_type='RSA', country='CN', province='', city='', company='',
        department='', email='', cipher_length=2048, ca=1, file_type=
        'cert_file', cert_type=None, user_type='vpnuser'):
        """创建数字证书。

        对应 UI 页面「系统 → 证书管理 → 本地证书」。

        :param action: 操作类型，``"create"`` = 新建
        :type action: str
        :param name: 证书名称
        :type name: str
        :param algorithm_type: 算法类型，``"RSA"`` = RSA，``"SM2"`` = SM2 国密
        :type algorithm_type: str
        :param country: 国家代码
        :type country: str
        :param province: 省份
        :type province: str
        :param city: 城市
        :type city: str
        :param company: 公司
        :type company: str
        :param department: 部门
        :type department: str
        :param email: 邮箱地址
        :type email: str
        :param cipher_length: 密钥长度
        :type cipher_length: int
        :param ca: CA 证书 ID
        :type ca: int
        :param file_type: 证书文件类型，默认 ``"cert_file"``
        :type file_type: str
        :param cert_type: 证书类型列表，默认 ``[]``
        :type cert_type: list
        :param user_type: 用户类型，默认 ``"vpnuser"``
        :type user_type: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if cert_type is None:
            cert_type = []
        data = {'name': name, 'action': action, 'algorithm_type':
            algorithm_type, 'country': country, 'city': city, 'province':
            province, 'company': company, 'department': department, 'email':
            email, 'cipher_length': cipher_length, 'ca': ca, 'file_type':
            file_type, 'cert_type': cert_type, 'userType': user_type}
        req_url = f'{self.base_url}/nf/cert/local/action_cert/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建数字证书失败: {e}')
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

    def get_digital_cert(self, page=1, size=10, search=''):
        """获取数字证书列表。

        对应 UI 页面「系统 → 证书管理 → 本地证书」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/cert/local/cert_info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取数字证书列表失败: {e}')
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

    def remove_digital_cert(self, cert_id):
        """删除数字证书。

        对应 UI 页面「系统 → 证书管理 → 本地证书」。

        :param cert_id: 证书 ID，支持单个值或列表；多个 ID 以逗号分隔发送
        :type cert_id: str or int or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(cert_id, list):
            cert_ids = ','.join([str(c_id) for c_id in cert_id])
        else:
            cert_ids = str(cert_id)
        data = {'id': cert_ids}
        req_url = f'{self.base_url}/nf/cert/local/delete_cert/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除数字证书失败: {e}')
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

    def get_digital_cert_id(self, page=1, size=10, search=''):
        """按名称查询数字证书 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 要匹配的数字证书名称
        :type search: str
        :return: 成功返回证书 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_digital_cert(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def export_digital_cert(self, cert_id):
        """导出数字证书。

        对应 UI 页面「系统 → 证书管理 → 本地证书」。

        :param cert_id: 数字证书 ID
        :type cert_id: str or int
        :return: 成功返回证书文本内容（str），失败返回 ``False``
        :rtype: str or bool
        """
        req_url = f'{self.base_url}/nf/cert/local/export/'
        params = {'id': cert_id}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'导出数字证书失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出数字证书成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def create_cert_request_file(self, action='create', name='cert_req_file',
        algorithm_type='RSA', country='CN', province='', city='', company='',
        department='', email='', cipher_length=2048):
        """创建证书请求文件。

        对应 UI 页面「系统 → 证书管理 → 证书请求」。

        :param action: 操作类型，``"create"`` = 新建
        :type action: str
        :param name: 证书请求文件名称
        :type name: str
        :param algorithm_type: 算法类型，``"RSA"`` = RSA，``"SM2"`` = SM2 国密
        :type algorithm_type: str
        :param country: 国家代码
        :type country: str
        :param province: 省份
        :type province: str
        :param city: 城市
        :type city: str
        :param company: 公司
        :type company: str
        :param department: 部门
        :type department: str
        :param email: 邮箱地址
        :type email: str
        :param cipher_length: 密钥长度
        :type cipher_length: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'name': name, 'action': action, 'algorithm_type':
            algorithm_type, 'country': country, 'city': city, 'province':
            province, 'company': company, 'department': department, 'email':
            email, 'cipher_length': cipher_length}
        req_url = f'{self.base_url}/nf/cert/req/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建证书请求文件失败: {e}')
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

    def get_cert_request_file(self, page=1, size=10, search=''):
        """获取证书请求文件列表。

        对应 UI 页面「系统 → 证书管理 → 证书请求」。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/cert/req/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取证书请求文件列表失败: {e}')
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

    def remove_cert_request_file(self, cert_id):
        """删除证书请求文件。

        对应 UI 页面「系统 → 证书管理 → 证书请求」。

        :param cert_id: 证书请求文件 ID，支持单个值或列表；多个 ID 以逗号分隔发送
        :type cert_id: str or int or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(cert_id, list):
            cert_ids = ','.join([str(c_id) for c_id in cert_id])
        else:
            cert_ids = str(cert_id)
        data = {'id': cert_ids}
        req_url = f'{self.base_url}/nf/cert/req/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除证书请求文件失败: {e}')
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

    def get_cert_request_file_id(self, page=1, size=10, search=''):
        """按名称查询证书请求文件 ID。

        :param page: 页码
        :type page: int
        :param size: 每页数量
        :type size: int
        :param search: 要匹配的证书请求文件名称
        :type search: str
        :return: 成功返回证书请求文件 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_cert_request_file(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def export_cert_request_file(self, cert_id):
        """导出证书请求文件。

        对应 UI 页面「系统 → 证书管理 → 证书请求」。

        :param cert_id: 证书请求文件 ID
        :type cert_id: str or int
        :return: 成功返回证书请求文件文本内容（str），失败返回 ``False``
        :rtype: str or bool
        """
        req_url = f'{self.base_url}/nf/cert/req/export/'
        params = {'id': cert_id}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'导出证书请求文件失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出证书请求文件成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False