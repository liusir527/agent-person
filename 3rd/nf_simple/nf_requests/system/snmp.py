"""SNMP 配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class SnmpFeature(NFRequests):
    """SNMP 配置操作集合。"""

    def create_snmp_agent(self, action='create', enable=True, name='11', ip=
        '192.66.0.11', port='161', version='v2c', securitylevel='noAuthNoPriv',
        user='', community='qwert12345', authalgorithm='MD5', authpassword='',
        encryptionalgorithm='DES', encryptionpassword=''):
        """创建 SNMP Agent。

        .. note:: 该函数对应旧版 SNMP 接口
            ``/nf/network/snmp_agent_mac/server/action_snmp_server/``，与
            :meth:`create_or_update_snmp_agent_config` 使用的
            ``/nf/system/snmp/agent/configuration/`` 端点不同。建议新代码优先使用
            :meth:`create_or_update_snmp_agent_config`。

        :param action: 操作类型，默认 ``"create"``
        :param enable: 是否启用，默认 ``True``
        :param name: Agent 名称，默认 ``"11"``
        :param ip: SNMP 主机 IP，默认 ``"192.66.0.11"``
        :param port: 端口，默认 ``"161"``
        :param version: SNMP 版本，``"v2c"`` 或 ``"v3"``，默认 ``"v2c"``
        :param securitylevel: 安全级别，默认 ``"noAuthNoPriv"``
        :param user: 用户名，默认 ``""``
        :param community: 团体名，默认 ``"qwert12345"``
        :param authalgorithm: 认证算法，默认 ``"MD5"``
        :param authpassword: 认证密码，默认 ``""``
        :param encryptionalgorithm: 加密算法，默认 ``"DES"``
        :param encryptionpassword: 加密密码，默认 ``""``
        :return: 成功返回 ``None``，失败返回 ``False``
        """
        data = {'action': action, 'enable': enable, 'name': name, 'ip': ip,
            'port': '161', 'version': version, 'securitylevel': securitylevel,
            'user': user, 'community': community, 'authalgorithm':
            authalgorithm, 'authpassword': authpassword, 'encryptionalgorithm':
            encryptionalgorithm, 'encryptionpassword': encryptionpassword}
        url = (
            f'{self.base_url}/nf/network/snmp_agent_mac/server/action_snmp_server/'
            )
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
            print(json.dumps(data))
        except Exception as e:
            logger.error(e)
            return False
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)

    def update_snmp_basic_config(self, agent_enable='off', trap_enable='off',
        sys_info='NF', contact_info='support@nsfocus.com', req_body=None):
        """更新 SNMP 基础配置。

        对应 UI 页面「系统 → SNMP」。

        :param agent_enable: Agent 开关，``"on"`` = 开启，``"off"`` = 关闭，默认
            ``"off"``
        :param trap_enable: Trap 开关，``"on"`` = 开启，``"off"`` = 关闭，默认
            ``"off"``
        :param sys_info: 系统信息，默认 ``"NF"``
        :param contact_info: 联系信息，默认 ``"support@nsfocus.com"``
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'agent_enable': agent_enable, 'trap_enable': trap_enable,
            'sys_info': sys_info, 'contact_info': contact_info}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/system/snmp/global/config_update/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新SNMP基础配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_snmp_basic_config(self):
        """获取 SNMP 基础配置。

        对应 UI 页面「系统 → SNMP」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "agent_enable": "on",
                    "trap_enable": "on",
                    "sys_info": "NF",
                    "contact_info": "support@nsfocus.com"
                }
        """
        url = f'{self.base_url}/nf/system/snmp/global/config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取SNMP基础配置失败: {e}')
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

    def create_or_update_snmp_agent_config(self, version='v1v2', action=
        'create', public_name='team1', ip='*', oid='1', accessible='rw',
        security='noauthnopriv', auth_type='MD5', phrase='12345678', priv_type=
        'DES', priv_phrase='12345678', agent_id=None, req_body=None):
        """创建或更新 SNMP Agent 配置。

        对应 UI 页面「系统 → SNMP → Agent 配置」。

        :param version: SNMP 版本，``"v1v2"`` 或 ``"v3"``，默认 ``"v1v2"``。

            - 当 version 为 ``"v3"`` 时，额外发送 v3 相关字段（security、
              auth_type、phrase、priv_type、priv_phrase）。
        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑，默认
            ``"create"``
        :param public_name: 团体名，默认 ``"team1"``
        :param ip: 允许访问的 IP，``"*"`` 表示不限，默认 ``"*"``
        :param oid: OID，默认 ``"1"``
        :param accessible: 访问权限，``"rw"`` = 读写，``"ro"`` = 只读，默认
            ``"rw"``
        :param security: v3 安全级别，``"noauthnopriv"`` = 无认证无加密，
            ``"authnopriv"`` = 认证无加密，``"authpriv"`` = 认证加密，默认
            ``"noauthnopriv"``
        :param auth_type: v3 认证算法，``"MD5"`` 或 ``"SHA"``，默认 ``"MD5"``
        :param phrase: v3 认证密码，默认 ``"12345678"``
        :param priv_type: v3 加密算法，``"DES"`` 或 ``"AES"``，默认 ``"DES"``
        :param priv_phrase: v3 加密密码，默认 ``"12345678"``
        :param agent_id: 编辑时必填，Agent 配置 ID
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'version': version, 'action': action, 'public_name':
            public_name, 'ip': ip, 'oid': str(oid), 'accessable': accessible}
        if version == 'v3':
            data.update({'security': security, 'authtype': auth_type, 'phrase':
                phrase, 'privtype': priv_type, 'privphrase': priv_phrase})
        if action == 'edit':
            if agent_id is None:
                logger.error(
                    'agent_id is None, please give agent id when edit agent config.'
                    )
                return False
            data['id'] = int(agent_id)
            data['oid'] = str(agent_id)
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/system/snmp/agent/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新SNMP agent配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_snmp_agent_config(self, page=1, size=10, search='', version='v1v2'):
        """获取 SNMP Agent 配置列表。

        对应 UI 页面「系统 → SNMP → Agent 配置」。

        :param page: 页码，默认 ``1``
        :param size: 每页数量，默认 ``10``
        :param search: 搜索关键字，默认 ``""``
        :param version: 版本筛选，``"v1v2"`` 或 ``"v3"``，默认 ``"v1v2"``
        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "total": 4,
                    "list": [
                        {"id": 1, "public_name": "test", "ip": "*",
                         "accessable": "rw", "oid": "1"}
                    ]
                }
        """
        url = f'{self.base_url}/nf/system/snmp/agent/info/'
        params = {'page': page, 'size': size, 'search': search, 'version': version}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取SNMP agent配置列表失败: {e}')
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

    def remove_snmp_agent_config(self, conf_id=1, version='v1v2', req_body=None):
        """删除 SNMP Agent 配置。

        :param conf_id: Agent 配置 ID，默认 ``1``
        :param version: SNMP 版本，``"v1v2"`` 或 ``"v3"``，默认 ``"v1v2"``
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'id': conf_id, 'version': version}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/system/snmp/agent/delete/'
        try:
            result = self.session.delete(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除SNMP agent配置失败: {e}')
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

    def create_or_update_trap_config(self, page_version='v1v2', action='create',
        nms='127.0.0.1', port='162', community='team1', version=None, engine_id
        ='0x8000000001020304', sec_level='noauthnopriv', auth_proto='MD5',
        auth_key='12345678', priv_proto='DES', priv_key='12345678', trap_id=
        None, req_body=None):
        """创建或更新 SNMP Trap 配置。

        对应 UI 页面「系统 → SNMP → Trap 配置」。

        :param page_version: 页面版本，``"v1v2"`` 或 ``"v3"``，默认 ``"v1v2"``。

            - 当 = ``"v3"`` 时，默认 ``version`` 为 ``"v3"``，并额外发送 v3
              字段（secLevel、authProto、authKey、privProto、privKey、
              engineID）。
            - 当 = ``"v1v2"`` 时，默认 ``version`` 为 ``"v1"``。
        :param action: 操作类型，``"create"`` = 创建，``"edit"`` = 编辑，默认
            ``"create"``
        :param nms: NMS 地址，默认 ``"127.0.0.1"``
        :param port: 端口，默认 ``"162"``
        :param community: 团体名，默认 ``"team1"``
        :param version: Trap 版本，``"v1"`` 或 ``"v2"``（v1v2 模式下），或
            ``"v3"``（v3 模式下）。默认由 ``page_version`` 决定
        :param engine_id: v3 引擎 ID，默认 ``"0x8000000001020304"``
        :param sec_level: v3 安全级别，``"noauthnopriv"`` = 无认证无加密，
            ``"authnopriv"`` = 认证无加密，``"authpriv"`` = 认证加密，默认
            ``"noauthnopriv"``
        :param auth_proto: v3 认证协议，``"MD5"`` 或 ``"SHA"``，默认 ``"MD5"``
        :param auth_key: v3 认证密钥，默认 ``"12345678"``
        :param priv_proto: v3 加密协议，``"DES"`` 或 ``"AES"``，默认 ``"DES"``
        :param priv_key: v3 加密密钥，默认 ``"12345678"``
        :param trap_id: 编辑时必填，Trap 配置 ID
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        if page_version == 'v3':
            version = 'v3' if version is None else version
        else:
            version = 'v1' if version is None else version
        data = {'pageVersion': page_version, 'action': action, 'nms': nms,
            'port': str(port), 'community': community, 'version': version}
        if version == 'v3':
            data.update({'secLevel': sec_level, 'authProto': auth_proto,
                'authKey': auth_key, 'privProto': priv_proto, 'privKey':
                priv_key, 'engineID': engine_id})
        if action == 'edit':
            if trap_id is None:
                logger.error(
                    'trap_id is None, please give trap id when edit trap config.')
                return False
            data['id'] = int(trap_id)
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/system/snmp/trap/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新SNMP trap配置失败: {e}')
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

    def get_snmp_trap_config(self, page=1, size=10, search='', version='v1v2'):
        """获取 SNMP Trap 配置列表。

        对应 UI 页面「系统 → SNMP → Trap 配置」。

        :param page: 页码，默认 ``1``
        :param size: 每页数量，默认 ``10``
        :param search: 搜索关键字，默认 ``""``
        :param version: 版本筛选，``"v1v2"`` 或 ``"v3"``，默认 ``"v1v2"``
        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result`` 结构：::

                {
                    "total": 0,
                    "list": []
                }
        """
        url = f'{self.base_url}/nf/system/snmp/trap/info/'
        params = {'page': page, 'size': size, 'search': search, 'version': version}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取SNMP trap配置列表失败: {e}')
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

    def remove_snmp_trap_config(self, conf_id=1, version='v1v2', req_body=None):
        """删除 SNMP Trap 配置。

        :param conf_id: Trap 配置 ID，默认 ``1``
        :param version: SNMP 版本，``"v1v2"`` 或 ``"v3"``，默认 ``"v1v2"``
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        data = {'id': conf_id, 'version': version}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/system/snmp/trap/delete/'
        try:
            result = self.session.delete(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除SNMP trap配置失败: {e}')
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
