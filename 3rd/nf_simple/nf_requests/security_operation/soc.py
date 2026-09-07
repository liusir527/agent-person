"""SOC/平台联动。

对应 UI 页面「安全运营 → SOC/平台联动」。
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


class SocFeature(NFRequests):
    """SOC/平台联动操作集合。"""

    def create_or_update_soc_config(self, addr='192.168.0.100', enable=True,
        err_msg='', conf_id=-1, isop_block='false', log_switch=None, port='443',
        soc_type='espc', takeover_status=True, send_port_data=False, req_body=None):
        """创建或更新安全管理平台配置。

        对应 UI 页面「安全运营 → SOC/平台联动」。

        :param addr: 平台地址，默认 ``"192.168.0.100"``。
        :param enable: 是否启用，``True`` = 启用，``False`` = 禁用，默认 ``True``。
        :param err_msg: 错误信息，默认 ``""``。
        :param conf_id: 配置 ID，``-1`` 表示新建，>0 表示编辑已有配置，默认 -1。
        :param isop_block: ISOP 阻断开关，``"true"``/``"false"``，默认 ``"false"``。
        :param log_switch: 日志开关列表，支持 str 或 list。

            当 ``soc_type='espc'`` 或 ``soc_type='las'`` 时默认追加
            ``['heart_beats', 'dev_status', 'fw_log', 'ips_log', 'av_log',
            'scm_log', 'url_log', 'vpn_log', 'auth_log', 'sys_log']``；
            当 ``soc_type='isop'`` 时默认追加
            ``['heart_beats', 'dev_status', 'dev_version', 'dev_license',
            'fw_log', 'ips_log', 'av_log', 'scm_log', 'url_log', 'vpn_log',
            'auth_log', 'sys_log']``。
        :param port: 端口，默认 ``"443"``。
        :param soc_type: 平台类型：

            * ``"espc"`` — ESPC 平台
            * ``"isop"`` — ISOP 平台
            * ``"las"`` — LAS 平台

            默认 ``"espc"``。
        :param takeover_status: 接管状态，默认 ``True``。
        :param send_port_data: 是否发送端口数据，默认 ``False``。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(log_switch, str):
            log_switch = [log_switch]
        if soc_type == 'isop':
            default_log_switch = ['heart_beats', 'dev_status', 'dev_version',
                'dev_license', 'fw_log', 'ips_log', 'av_log', 'scm_log',
                'url_log', 'vpn_log', 'auth_log', 'sys_log']
            log_switch = (log_switch + default_log_switch if log_switch is not
                None else default_log_switch)
        else:
            default_log_switch = ['heart_beats', 'dev_status', 'fw_log',
                'ips_log', 'av_log', 'scm_log', 'url_log', 'vpn_log',
                'auth_log', 'sys_log']
            log_switch = (log_switch + default_log_switch if log_switch is not
                None else default_log_switch)
        data = {'addr': addr, 'enable': enable, 'err_msg': err_msg, 'id':
            conf_id, 'isop_block': isop_block, 'log_switch': log_switch, 'port':
            port, 'status': 2, 'type': soc_type, 'takeover_status': takeover_status,
            'send_port_data': send_port_data
            }
        if conf_id != -1 or conf_id:
            data['addrError'] = False
            data['isopBlockParams'] = {'token': '', 'name': '', 'expire': '',
                'port': '8081'}
            data['portError'] = False
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/soc/config_update/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新安全管理平台配置失败: {e}')
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

    def remove_soc_config(self, conf_id=None, req_param=None):
        """删除安全管理平台配置。

        对应 UI 页面「安全运营 → SOC/平台联动」。

        :param conf_id: 配置 ID，指定要删除的联动配置。
        :param req_param: 自定义请求体 dict，传入后优先使用，覆盖 ``conf_id`` 构造的默认体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': conf_id} if req_param is None else req_param
        req_url = f'{self.base_url}/nf/soc/config_delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除安全管理平台配置失败: {e}')
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

    def get_soc_config(self):
        """获取安全管理平台配置列表。

        对应 UI 页面「安全运营 → SOC/平台联动」。

        :return: 成功返回完整响应 dict，格式为 ``{"status": 2000, "result": {...}, "message": "..."}``；
            失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/soc/config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取安全管理平台配置失败: {e}')
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

    def update_soc_global_config(self, local_addr=None, req_param=None):
        """更新安全管理平台全局配置（本机联动地址）。

        对应 UI 页面「安全运营 → SOC/平台联动 → 全局配置」。

        :param local_addr: 本机联动 IP 地址。
        :param req_param: 自定义请求体 dict，传入后优先使用，覆盖 ``local_addr`` 构造的默认体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'local_addr': local_addr} if local_addr is not None else req_param
        req_url = f'{self.base_url}/nf/soc/global_set/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新安全管理平台全局配置失败: {e}')
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

    def get_soc_diagnosis(self, addr, req_param=None):
        """获取安全管理平台诊断信息。

        对应 UI 页面「安全运营 → SOC/平台联动 → 诊断」。

        :param addr: 要诊断的平台 IP 地址。
        :param req_param: 自定义查询参数字典，传入后优先使用，覆盖默认 ``{'ip': addr}``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        params = {'ip': addr} if req_param is None else req_param
        req_url = f'{self.base_url}/nf/system/get_diagnosis_info/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取安全管理平台诊断信息失败: {e}')
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

    def update_sse_global_config(self, local_addr=None, req_param=None):
        """更新 SSE 全局配置（本机联动 IP）。

        对应接口 ``/nf/sse/sse_global_update/``，用于配置 TONE 平台联动的本机 IP。

        :param local_addr: 本机联动 IP 地址。
        :param req_param: 自定义请求体 dict，传入后优先使用，覆盖 ``local_addr`` 构造的默认体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'local_addr': local_addr} if local_addr is not None else req_param
        req_url = f'{self.base_url}/nf/sse/sse_global_update/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新 SSE 全局配置失败: {e}')
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

    def create_or_update_sse_config(self, connect_type=1, connect_addr=None,
        connect_list=None, req_body=None):
        """创建或更新绿盟合作运营节点（SSE 联动配置）。

        对应接口 ``/nf/sse/config_update/``，用于配置 TONE 平台的运营节点连接。

        :param connect_type: 连接类型，默认 ``1``。
        :param connect_addr: 连接地址（平台 IP）。
        :param connect_list: 连接节点列表，每个元素为 dict，含：

            * ``connect_type`` — 连接类型
            * ``addr`` — 节点地址
            * ``province_list`` — 省份列表，默认 ``[]``
            * ``connect_status`` — 连接状态，默认 ``1``
            * ``id`` — 节点 ID，新建时为 ``0``
            * ``statusColor`` — 状态颜色，默认 ``"processing"``
            * ``statusTxt`` — 状态文本，默认 ``"连接中"``
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if req_body is not None:
            data = req_body
        else:
            if connect_list is None:
                connect_list = [{
                    'connect_type': connect_type,
                    'addr': connect_addr,
                    'province_list': [],
                    'connect_status': 1,
                    'id': 0,
                    'statusColor': 'processing',
                    'statusTxt': '连接中',
                }]
            data = {
                'connect_type': connect_type,
                'connect_addr': connect_addr,
                'connect_list': connect_list,
            }
        req_url = f'{self.base_url}/nf/sse/config_update/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新 SSE 联动配置失败: {e}')
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
