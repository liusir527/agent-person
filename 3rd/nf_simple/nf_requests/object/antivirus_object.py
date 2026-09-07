"""防病毒全局配置和模板 CRUD。

对应 UI 页面「对象 → 防病毒」。
"""
import json
import logging

from nf_requests.nflib.Log import logger
from ..client import NFRequests


class AntivirusObjectFeature(NFRequests):
    """防病毒对象操作集合 — 全局配置、模板和黑白名单管理。"""

    def update_antivirus_global_config(self, enable=0, engine=1, depth_level=1,
        min_size=0, max_size=5, mail_scan=False, max_file_cache=100, timeout=
        3000, recognition_method=1, scan_type=None, http_ban_multi_thread=0,
        http_ban_encrypt_compressed_package=0, ftp_ban_multi_thread=0,
        ftp_ban_encrypt_compressed_package=0,
        smtp_ban_encrypt_compressed_package=0,
        pop3_file_encrypt_compressed_package=0,
        imap_file_encrypt_compressed_package=0):
        """更新网络防病毒全局配置。

        对应 UI 页面「对象 → 防病毒 → 全局配置」。

        :param enable: 是否启用，``0`` = 关闭，``1`` = 开启
        :type enable: int
        :param engine: 引擎类型，``1`` = 默认
        :type engine: int
        :param depth_level: 最大解压层数
        :type depth_level: int
        :param min_size: 最小扫描文件大小 (KB)
        :type min_size: int
        :param max_size: 最大扫描文件大小 (MB)
        :type max_size: int
        :param mail_scan: 是否邮件单独扫描
        :type mail_scan: bool
        :param max_file_cache: 最大文件缓存数
        :type max_file_cache: int
        :param timeout: 超时时间 (ms)
        :type timeout: int
        :param recognition_method: 文件类型识别方式
        :type recognition_method: int
        :param scan_type: 扫描的文件类型列表，默认 ``[1, 4, 2, 8]``
        :type scan_type: list or None
        :param http_ban_multi_thread: HTTP 禁止多线程
        :type http_ban_multi_thread: int
        :param http_ban_encrypt_compressed_package: HTTP 禁止加密压缩包
        :type http_ban_encrypt_compressed_package: int
        :param ftp_ban_multi_thread: FTP 禁止多线程
        :type ftp_ban_multi_thread: int
        :param ftp_ban_encrypt_compressed_package: FTP 禁止加密压缩包
        :type ftp_ban_encrypt_compressed_package: int
        :param smtp_ban_encrypt_compressed_package: SMTP 禁止加密压缩包
        :type smtp_ban_encrypt_compressed_package: int
        :param pop3_file_encrypt_compressed_package: POP3 加密压缩包处理
        :type pop3_file_encrypt_compressed_package: int
        :param imap_file_encrypt_compressed_package: IMAP 加密压缩包处理
        :type imap_file_encrypt_compressed_package: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if scan_type is None:
            scan_type = [1, 4, 2, 8]
        data = {'enable': enable, 'engine': engine, 'file_config': {
            'is_mail_single_scan': mail_scan, 'max_decompress_depth_level':
            depth_level, 'max_file_cache': max_file_cache, 'max_size': max_size,
            'min_size': min_size, 'recognition_method': recognition_method,
            'timeout': timeout, 'type': scan_type}, 'protos': {'ftp': {
            'ban_encrypt_compressed_package':
            ftp_ban_encrypt_compressed_package, 'ban_multi_thread':
            ftp_ban_multi_thread}, 'http': {'ban_encrypt_compressed_package':
            http_ban_encrypt_compressed_package, 'ban_multi_thread':
            http_ban_multi_thread}, 'imap': {'file_encrypt_compressed_package':
            imap_file_encrypt_compressed_package}, 'pop3': {
            'file_encrypt_compressed_package':
            pop3_file_encrypt_compressed_package}, 'smtp': {
            'ban_encrypt_compressed_package': smtp_ban_encrypt_compressed_package}}
            }
        req_url = f'{self.base_url}/nf/object/antivirus/global/config_update/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'修改网络防病毒全局配置失败: {e}')
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

    def get_antivirus_global_config(self):
        """获取网络防病毒全局配置。

        对应 UI 页面「对象 → 防病毒 → 全局配置」。

        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/antivirus/global/config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取网络防病毒全局配置失败: {e}')
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

    def create_or_update_antivirus_template(self, action='create', name=
        'autotest_antivirus', tmpl_id=-1, comment='', is_enable=None, is_block=
        None, is_log=None):
        """创建或修改网络防病毒模板。

        对应 UI 页面「对象 → 防病毒 → 模板」。

        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type action: str
        :param name: 模板名称
        :type name: str
        :param tmpl_id: 模板 ID，编辑时使用
        :type tmpl_id: int
        :param comment: 备注
        :type comment: str
        :param is_enable: 各协议启用开关列表（9 个协议），传单个 int 会对所有协议设置同样值；默认全 ``0``
        :type is_enable: int or list or None
        :param is_block: 各协议阻断开关列表（9 个协议），默认全 ``0``
        :type is_block: int or list or None
        :param is_log: 各协议日志开关列表（9 个协议），默认全 ``0``
        :type is_log: int or list or None
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        protocol_count = 9
        if isinstance(is_enable, (int, str)):
            is_enable = [is_enable] * protocol_count
        elif is_enable is None:
            is_enable = [0] * protocol_count
        if isinstance(is_block, (int, str)):
            is_block = [is_block] * protocol_count
        elif is_block is None:
            is_block = [0] * protocol_count
        if isinstance(is_log, (int, str)):
            is_log = [is_log] * protocol_count
        elif is_log is None:
            is_log = [0] * protocol_count
        proto_action = []
        for enable_item, block_item, log_item in zip(is_enable, is_block, is_log):
            proto_action.append({'is_enable': enable_item, 'is_block':
                block_item, 'is_log': log_item})
        data = {'action': action, 'name': name, 'id': int(tmpl_id), 'comment':
            str(comment), 'proto_action': proto_action}
        req_url = f'{self.base_url}/nf/object/antivirus/antivirus_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改网络防病毒模板失败: {e}')
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

    def get_antivirus_template(self, size=10, page=1, search=''):
        """查询网络防病毒模板列表。

        对应 UI 页面「对象 → 防病毒 → 模板」。

        :param size: 每页数量
        :type size: int
        :param page: 页码
        :type page: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/antivirus/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'查询网络防病毒模板失败: {e}')
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

    def get_antivirus_template_id(self, search='',size=10, page=1):
        """按名称查询网络防病毒模板 ID。

        :param size: 每页数量
        :type size: int
        :param page: 页码
        :type page: int
        :param search: 要匹配的模板名称
        :type search: str
        :return: 成功返回模板 ``id``，未找到或失败返回 ``False``
        :rtype: str or bool
        """
        resp = self.get_antivirus_template(size=size, page=page, search=search)
        if resp is False:
            return False
        result = resp.get('result', {})
        if result.get('total', 0) == 0:
            return False
        for i in result.get('list', []):
            if i.get('name') == search:
                return i.get('id')
        return False

    def remove_antivirus_template(self, tmpl_id):
        """删除网络防病毒模板。

        对应 UI 页面「对象 → 防病毒 → 模板」。

        :param tmpl_id: 模板 ID，支持单个 int/str 或列表
        :type tmpl_id: int or str or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(tmpl_id, (int, str)):
            tmpl_id = [int(tmpl_id)]
        elif isinstance(tmpl_id, list):
            tmpl_id = [int(i) for i in tmpl_id]
        data = {'id': tmpl_id}
        req_url = f'{self.base_url}/nf/object/antivirus/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除网络防病毒模板失败: {e}')
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

    def get_antivirus_reference(self):
        """查询网络防病毒模板引用情况。

        对应 UI 页面「对象 → 防病毒 → 模板」。

        :return: 成功返回 API 响应 dict（含 ``antis`` 和 ``antis_reference`` 信息），失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/antivirus/reference/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'查询网络防病毒模板引用情况失败: {e}')
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

    def create_or_update_antivirus_wblist(self, page_type='black', action=
        'create', wb_id=-1, name='autotest_antivirus_wblist', wb_type=0, info=
        'autotest_antivirus_info', enable=1):
        """创建或修改网络防病毒黑白名单。

        对应 UI 页面「对象 → 防病毒 → 黑白名单」。

        :param page_type: 名单类型，``"black"`` = 黑名单，``"white"`` = 白名单
        :type page_type: str
        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑
        :type action: str
        :param wb_id: 名单 ID，编辑时使用
        :type wb_id: int
        :param name: 名单名称
        :type name: str
        :param wb_type: 匹配类型，``0`` = 文件内容
        :type wb_type: int
        :param info: 匹配信息
        :type info: str
        :param enable: 是否启用，``0`` = 关闭，``1`` = 开启
        :type enable: int
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        data = {'pageType': page_type, 'action': action, 'id': wb_id, 'name':
            name, 'type': wb_type, 'info': info, 'enable': enable}
        req_url = f'{self.base_url}/nf/object/antivirus/wblist/configuration/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或修改网络防病毒黑白名单失败: {e}')
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

    def get_antivirus_wblist(self, wb_type='black', size=10, page=1, search=''):
        """查询网络防病毒黑白名单。

        对应 UI 页面「对象 → 防病毒 → 黑白名单」。

        :param wb_type: 名单类型，``"black"`` = 黑名单，``"white"`` = 白名单
        :type wb_type: str
        :param size: 每页数量
        :type size: int
        :param page: 页码
        :type page: int
        :param search: 搜索关键字
        :type search: str
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/object/antivirus/wblist/info/'
        params = {'type': wb_type, 'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'查询网络防病毒黑白名单失败: {e}')
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

    def remove_antivirus_wblist(self, wb_type='black', list_id=None):
        """删除网络防病毒黑白名单。

        对应 UI 页面「对象 → 防病毒 → 黑白名单」。

        :param wb_type: 名单类型，``"black"`` = 黑名单，``"white"`` = 白名单
        :type wb_type: str
        :param list_id: 名单 ID，支持单个 int/str 或列表
        :type list_id: int or str or list
        :return: 成功返回 API 响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if isinstance(list_id, (int, str)):
            list_id = [int(list_id)]
        elif isinstance(list_id, list):
            list_id = [int(i) for i in list_id]
        data = {'type': wb_type, 'id': list_id}
        req_url = f'{self.base_url}/nf/object/antivirus/wblist/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除网络防病毒黑白名单失败: {e}')
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
