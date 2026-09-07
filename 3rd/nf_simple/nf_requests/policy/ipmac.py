"""IPMAC 绑定策略。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class IpmacFeature(NFRequests):
    """IPMAC 绑定策略操作集合。

    涵盖 IPMAC 绑定策略的增删改查、CSV 批量导入导出，以及全局配置。
    """

    def update_ipmac_global_config(self, is_log=False, is_block=False, req_body
        =None):
        """更新 IPMAC 全局配置。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 全局配置」。

        :param is_log:   是否记录日志，默认 ``False``。
        :param is_block: 是否阻断，默认 ``False``。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'is_log': is_log, 'is_block': is_block}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/ipmac/global_config_update/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新IPMAC全局配置失败: {e}')
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

    def get_ipmac_global_config(self):
        """获取 IPMAC 全局配置。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 全局配置」。

        :return: 成功返回完整响应 dict，``result`` 包含 ``is_block``、``is_log``、``ip_mac_enable``、
                 ``snmp_mac_enable``、``is_strict_match``；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/global_config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取IPMAC全局配置失败: {e}')
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

    def create_or_update_ipmac(self, action='create', ipmac_id=-1, is_enable=
        'yes', ip_addr='0.0.0.0', mac_addr='00:00:00:00:00:00', description='',
        req_body=None):
        """创建或修改 IPMAC 绑定策略。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 新建/编辑」。

        ``is_enable`` 取值：
            - ``"yes"`` = 启用（默认）
            - ``"no"`` = 禁用

        :param action:      操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param ipmac_id:    策略 ID。创建时传 ``-1``（默认），编辑时传实际 ID。
        :param is_enable:   是否启用，默认 ``"yes"``。
        :param ip_addr:     IP 地址，默认 ``"0.0.0.0"``。
        :param mac_addr:    MAC 地址，默认 ``"00:00:00:00:00:00"``。
        :param description: 备注描述，默认 ``""``。
        :param req_body:    自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'action': action, 'list': [{'id': ipmac_id, 'is_enable':
            is_enable, 'ip_addr': ip_addr, 'mac_addr': mac_addr, 'description':
            description}]}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/ipmac/ipmac_action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或修改IPMAC策略失败: {e}')
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
    def upload_ipmac_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入 IPMAC 绑定策略。

        对应接口 ``POST /nf/strategy/ipmac/upload/``。

        :param file_path: CSV 文件路径
        :type file_path: str
        :param req_body: 自定义 form-data 参数，传入后与默认参数合并
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if not os.path.exists(file_path):
            logger.error(f'CSV 文件不存在: {file_path}')
            return False

        url = f'{self.base_url}/nf/strategy/ipmac/upload/'
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as f:
                files = {
                    "file": (filename, f, "text/csv")
                }

                data = {}
                if req_body is not None:
                    data.update(req_body)

                result = self.session.post(
                    url,
                    files=files,
                    data=data,
                    verify=False,
                    timeout=300
                )

        except Exception as e:
            logger.error(f'上传IPMAC策略CSV失败: {e}')
            return False

        if result.status_code == 200:
            resp = json.loads(result.text)
            if resp.get("status") != 2000:
                logger.error(resp.get("message"))
                return False

            logger.info(resp.get("message"))
            return resp

        logger.error(f'HTTP请求失败，状态码:{result.status_code}')
        return False

    @staticmethod
    def gen_ipmac_csv(file_path, ipmacs, encoding="utf-8-sig"):
        """生成 IPMAC 绑定策略 CSV。

        :param file_path: CSV保存路径
        :type file_path: str

        :param ipmacs: IPMAC 策略列表，例如::

            [
                {
                    "ip_addr": "10.0.0.1",
                    "mac_addr": "00:1A:A0:AB:16:72",
                    "is_enable": "yes",
                    "description": "备注信息"
                }
            ]

        :type ipmacs: list[dict]

        :param encoding: 文件编码
        :type encoding: str

        :return: 成功返回策略数量，失败返回 False
        :rtype: int or bool
        """
        import csv

        headers = [
            "IP地址",
            "MAC地址",
            "启用状态",
            "备注",
        ]

        try:
            with open(file_path, "w", encoding=encoding, newline="") as f:

                writer = csv.writer(f)

                # 注释
                f.write("#注意！用excel修改此配置后，需要另存为CSV格式,,,\n")
                f.write("#IP地址支持IPv4和IPv6，不支持全0地址和ff开头的IPv6地址,,,\n")
                f.write("#启用状态为yes表示启用，为no表示禁用,,,\n")
                f.write("#IP地址,MAC地址,启用状态,备注\n")
                f.write("#示例1：10.0.0.1,00:1A:A0:AB:16:72,yes,备注信息\n")

                # 表头
                writer.writerow(["#" + headers[0], headers[1], headers[2],
                                 headers[3]])

                count = 0

                for item in ipmacs:
                    is_enable = item.get("is_enable", "yes")
                    if isinstance(is_enable, bool):
                        is_enable = "yes" if is_enable else "no"

                    writer.writerow([
                        item.get("ip_addr", ""),
                        item.get("mac_addr", ""),
                        is_enable,
                        item.get("description", ""),
                    ])
                    count += 1

            logger.info(f"生成IPMAC策略CSV成功：{file_path} ({count} 条)")
            return count

        except Exception as e:
            logger.error(f"生成IPMAC策略CSV失败: {e}")
            return False

    def remove_ipmac(self, ipmac_id, req_body=None):
        """根据 ID 删除 IPMAC 策略。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 删除」。

        ``ipmac_id`` 支持 int、str 或 list[int/str]，传入单个值时自动包装为列表。

        :param ipmac_id:  IPMAC 策略 ID，支持 int、str 或 list（如 ``[1, 2]``）。
        :param req_body:  自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(ipmac_id, (str, int)):
            ipmac_id = [int(ipmac_id)]
        elif isinstance(ipmac_id, list):
            ipmac_id = [int(i) for i in ipmac_id]
        else:
            logger.error('ipmac_id can not be None')
            return False
        data = {'id': ipmac_id}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/strategy/ipmac/ipmac_delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除IPMAC策略失败: {e}')
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

    def clear_ipmac(self):
        """清空全部 IPMAC 策略。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 清空」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/clear/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清除IPMAC策略失败: {e}')
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

    def get_ipmac(self, size=10, page=1, search=''):
        """获取 IPMAC 策略列表。

        对应 UI 页面「安全策略 → IPMAC 绑定」。

        :param size:   每页数量，默认 ``10``。
        :param page:   页码，默认 ``1``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/info/'
        params = {'size': size, 'page': page, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取IPMAC策略列表失败: {e}')
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

    def get_ipmac_id(self, size=10, page=1, search=''):
        """根据名称查询 IPMAC 策略 ID。

        对应 UI 页面「安全策略 → IPMAC 绑定」。

        调用 ``get_ipmac`` 后在返回列表中按 ``name`` 精确匹配。

        :param size:   每页数量，默认 ``10``。
        :param page:   页码，默认 ``1``。
        :param search: IPMAC 策略名称关键字，用于匹配。
        :return: 匹配到时返回策略 ID (int)；失败返回 ``False``。
        """
        resp = self.get_ipmac(size=size, page=page, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def export_ipmac(self):
        """导出 IPMAC 配置为 CSV/文本格式。

        对应 UI 页面「安全策略 → IPMAC 绑定 → 导出」。

        :return: 成功返回 CSV/文本字符串内容；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/strategy/ipmac/export/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出IPMAC配置失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出IPMAC配置成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
