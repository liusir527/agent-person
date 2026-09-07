"""NAT66 策略 — NAT66 源/目的 NAT 策略的增删查改、启用/禁用、移动、导出和总览。

对应 UI 页面「策略 → NAT66」。

对应 API 文档中的 ``create_or_update_nat66``、``get_nat66``、``get_nat66_tree``、
``remove_nat66``、``clear_nat66``、``enable_nat66``、``move_nat66``、``export_nat66``。
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


class Nat66Feature(NFRequests):
    """NAT66 策略操作集合 — NAT66 策略的增删查改、启停、移动、导出和总览。"""

    def create_or_update_nat66_policy(self, name='test', nat_type=0, enabled=1,
        action='create', id='', s_safety_zone='GLOBAL', d_safety_zone='GLOBAL',
        s_address='66::1/64', d_address='any_ipv6', service='any',
        out_interface='G1/1', transf_mode=2, nat_object='88::/64',
        in_interface='G1/2', port_map_type=2, internal_address='77::/64',
        external_address='77::/64', internal_port='', external_port='',
        protocol='any', HA='',priority=4):
        """创建或更新 NAT66 策略。

        对应 API 文档中的 ``create_or_update_nat66``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param name: 策略名称
        :type name: str
        :param nat_type: NAT 类型，``0``（源 NAT66）或 ``1``（目的 NAT66）
        :type nat_type: int
        :param enabled: 是否启用，``1`` 启用，``0`` 禁用
        :type enabled: int
        :param id: 策略 ID，编辑时传入
        :type id: str or int
        :param s_safety_zone: 源安全区
        :type s_safety_zone: str
        :param d_safety_zone: 目的安全区
        :type d_safety_zone: str
        :param s_address: 源 IPv6 地址/对象
        :type s_address: str
        :param d_address: 目的 IPv6 地址/对象
        :type d_address: str
        :param service: 服务对象
        :type service: str
        :param out_interface: 源 NAT66 出接口
        :type out_interface: str
        :param transf_mode: 转换模式
        :type transf_mode: int
        :param nat_object: 源 NAT66 转换对象
        :type nat_object: str
        :param in_interface: 目的 NAT66 入接口
        :type in_interface: str
        :param port_map_type: 目的 NAT66 端口映射类型
        :type port_map_type: int
        :param internal_address: 目的 NAT66 内部地址
        :type internal_address: str
        :param external_address: 目的 NAT66 外部地址
        :type external_address: str
        :param internal_port: 目的 NAT66 内部端口
        :type internal_port: str
        :param external_port: 目的 NAT66 外部端口
        :type external_port: str
        :param protocol: 目的 NAT66 协议
        :type protocol: str
        :param HA: HA 线路
        :type HA: str
        :param priority: 优先级，编辑时生效
        :type priority: int
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if nat_type == 0:
            data = {
                'name': name,
                'nat_type': nat_type,
                'action': action,
                'id': id,
                's_safety_zone': s_safety_zone,
                'd_safety_zone': d_safety_zone,
                's_address': s_address,
                'd_address': d_address,
                'service': service,
                'dst_port': out_interface,
                'transf_mode': transf_mode,
                'nat_object': nat_object,
                'enabled': enabled,
            }
        elif nat_type == 1:
            data = {
                'name': name,
                'nat_type': nat_type,
                'action': action,
                'enabled': enabled,
                'id': id,
                'interface': in_interface,
                'transf_mode': transf_mode,
                'port_map_type': port_map_type,
                'internal_address': internal_address,
                'external_address': external_address,
                'internal_port': internal_port,
                'external_port': external_port,
                'protocol': protocol,
                'HA': HA,
            }
        else:
            logger.error(f'不支持的 NAT66 类型: {nat_type}')
            return False
        if action=="edit":
            data.update({"priority":priority})
        req_url = f'{self.base_url}/nf/strategy/nat66/nat66_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新NAT66策略失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(data)
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_nat66_policy(self, page=1, size=10, sort_type='priority', where='OR',
        reload=False, name=None, id=None):
        """获取 NAT66 策略列表。

        对应 API 文档中的 ``get_nat66``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param sort_type: 排序/查询类型，默认 ``"priority"``
        :type sort_type: str
        :param where: 查询条件组合方式，默认 ``"OR"``
        :type where: str
        :param reload: 是否重新加载
        :type reload: bool
        :param name: 策略名称过滤
        :type name: str or None
        :param id: 策略 ID 过滤
        :type id: str or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        data = {'page': page, 'size': size, 'where': where, 'type': sort_type,
            'reload': reload, 'name': name, 'id': id}
        req_url = f'{self.base_url}/nf/strategy/nat66/info/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取NAT66策略列表失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_nat66_policy_id(self, name, page=1, size=10):
        """按名称查询 NAT66 策略 ID。

        通过 ``get_nat66`` 接口查找，支持精确名称匹配。

        :param name: 策略名称
        :type name: str
        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :return: 成功返回策略 ID（int），未找到或失败返回 False
        :rtype: int or bool
        """
        resp = self.get_nat66_policy(name=name, size=size, page=page)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        if result_data['total'] == 1:
            return result_data['list'][0]['id']
        for item in result_data.get('list', []):
            if item.get('name') == name:
                return item.get('id')
        return False

    def remove_nat66_policy(self, ids, req_body=None):
        """删除 NAT66 策略。

        对应 API 文档中的 ``remove_nat66``。

        :param ids: 策略 ID，支持 ``str`` 或 ``list``
        :type ids: str or list
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(ids, list):
            ids = ','.join(map(str, ids))
        elif isinstance(ids, str):
            ids = str(ids)
        data = {'ids': str(ids)} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/strategy/nat66/delete_nat/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除NAT66策略失败: {e}')
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

    def clear_nat66_policy(self):
        """清空 NAT66 策略。

        对应 API 文档中的 ``clear_nat66``。

        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/strategy/nat66/clear_nat/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空NAT66策略失败: {e}')
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

    def enable_nat66_policy(self, ids, enabled=True, req_body=None):
        """启用或禁用 NAT66 策略。

        对应 API 文档中的 ``enable_nat66``。

        :param ids: 策略 ID，支持 ``str`` 或 ``list``
        :type ids: str or list
        :param enabled: ``True`` 启用，``False`` 禁用
        :type enabled: bool
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(ids, list):
            ids = ','.join(map(str, ids))
        data = {'ids': ids, 'enabled': enabled} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/strategy/nat66/enable_nat/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'启用或禁用NAT66策略失败: {e}')
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

    def move_nat66_policy(self, nat_type=1, transfer_nat1=1, transfer_nat2=2,
        move_type=None, req_param=None):
        """移动 NAT66 策略。

        对应 API 文档中的 ``move_nat66``。

        :param nat_type: NAT 类型
        :type nat_type: int
        :param transfer_nat1: 源策略索引
        :type transfer_nat1: int
        :param transfer_nat2: 目标策略索引
        :type transfer_nat2: int
        :param move_type: 移动类型，传入时仅使用 ``transfer_nat1``
        :type move_type: str or None
        :param req_param: 自定义请求体，传入后覆盖默认参数
        :type req_param: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        data = {'transfer_nat1': transfer_nat1, 'transfer_nat2': transfer_nat2,
            'type': nat_type}
        if move_type is not None:
            data['move_type'] = move_type
            data.pop('transfer_nat2')
        if req_param is not None:
            data = req_param
        req_url = f'{self.base_url}/nf/strategy/nat66/move/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'移动NAT66策略失败: {e}')
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

    def export_nat66_policy(self, export_type='priority'):
        """导出 NAT66 策略。

        对应 API 文档中的 ``export_nat66``。

        :param export_type: 导出类型，``"create"`` 或 ``"priority"``
        :type export_type: str
        :return: 成功返回导出文本内容（str），失败返回 False
        :rtype: str or bool
        """
        req_url = f'{self.base_url}/nf/strategy/nat66/export_nat/'
        try:
            result = self.session.get(req_url, params={'type': export_type},
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出NAT66策略失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出NAT66策略成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_nat66_policy_tree(self):
        """获取 NAT66 策略总览。

        对应 API 文档中的 ``get_nat66_tree``。

        :return: 成功返回 ``{"status": 2000, "result": [...]}``（dict），失败返回 False
        :rtype: dict or bool
        """
        req_url = f'{self.base_url}/nf/strategy/nat66/tree/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取NAT66策略总览失败: {e}')
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


    def upload_nat66_policy_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入 NAT66 策略。

        对应接口 ``POST /nf/strategy/nat66/upload_nat/``。

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

        url = f'{self.base_url}/nf/strategy/nat66/upload_nat/'
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
            logger.error(f'上传NAT66策略CSV失败: {e}')
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
    def gen_nat66_policy_csv(file_path, policies, encoding="utf-8-sig"):
        """生成 NAT66 策略 CSV。

        :param file_path: CSV保存路径
        :type file_path: str

        :param policies: NAT66 策略列表，例如::

            [
                {
                    "name": "nat66-test",
                    "nat_type": 0,
                    "s_address": "20:3::2/128",
                    "d_address": "40::/48",
                    "nat_object": "20::3/128",
                    "out_interface": "G1/1",
                    "transf_mode": 3,
                    "enabled": "no",
                    "s_safety_zone": "DMZ",
                    "d_safety_zone": "TRUST",
                    "service": "any",
                    "HA": "test"
                },
                {
                    "name": "nat66-test2",
                    "nat_type": 1,
                    "in_interface": "G1/1",
                    "external_address": "30::/64",
                    "internal_address": "20::/48",
                    "transf_mode": 3,
                    "enabled": "no",
                    "HA": "test"
                }
            ]

        :type policies: list[dict]

        :param encoding: 文件编码
        :type encoding: str

        :return: 成功返回策略数量，失败返回 False
        :rtype: int or bool
        """
        import csv

        headers = [
            "策略名称",
            "策略类型(0:源nat 1:目的nat)",
            "源地址",
            "目的地址",
            "源地址转换",
            "出接口",
            "外部接口",
            "外部地址",
            "内部地址",
            "转换模式",
            "是否启用（yes,no）",
            "源安全区",
            "目的安全区",
            "服务",
            "HA",
        ]

        try:
            with open(file_path, "w", encoding=encoding, newline="") as f:

                writer = csv.writer(f)

                # 注释
                f.write("#以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略")
                f.write("#部分版本office、wps无法自动识别wps文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件")
                f.write("#根据NAT66类型不同，字段名根据类型和界面展示而定，同一字段不同类型名使用/隔开")
                f.write("#服务默认为any，启用默认为yes")
                f.write("#如果一个字段下需要输入多个值，值与值之间用逗号作为分隔符")
                f.write('#策略名称,策略类型(0:源nat 1:目的nat),源地址,目的地址,源地址转换,出接口,外部接口,外部地址,内部地址,转换模式,"是否启用（yes,no）",源安全区,目的安全区,服务,HA')
                f.write('#示例1：nat66-test,0,20:3::2/128,40::/48,20::3/128,G1/1,,,,3,no,DMZ,TRUST,any,test')
                f.write('#示例1：nat66-test2,1,,,,,G1/1,30::/64,20::/48,3,no,,,,test')

                # 表头
                writer.writerow(["#" + headers[0], headers[1], headers[2],
                                 headers[3], headers[4], headers[5], headers[6],
                                 headers[7], headers[8], headers[9], headers[10],
                                 headers[11], headers[12], headers[13], headers[14]])

                count = 0

                for p in policies:
                    enabled = p.get("enabled", "yes")
                    if isinstance(enabled, bool):
                        enabled = "yes" if enabled else "no"

                    nat_type = p.get("nat_type", 0)

                    if nat_type == 0:
                        # 源 NAT66:源地址,目的地址,源地址转换,出接口
                        s_address = p.get("s_address", "")
                        d_address = p.get("d_address", "")
                        nat_object = p.get("nat_object", "")
                        out_interface = p.get("out_interface", "")
                        in_interface = ""
                        external_address = ""
                        internal_address = ""
                    else:
                        # 目的 NAT66:外部接口,外部地址,内部地址
                        s_address = ""
                        d_address = ""
                        nat_object = ""
                        out_interface = ""
                        in_interface = p.get("in_interface", "")
                        external_address = p.get("external_address", "")
                        internal_address = p.get("internal_address", "")

                    writer.writerow([
                        p.get("name", ""),
                        nat_type,
                        s_address,
                        d_address,
                        nat_object,
                        out_interface,
                        in_interface,
                        external_address,
                        internal_address,
                        p.get("transf_mode", 2),
                        enabled,
                        p.get("s_safety_zone", ""),
                        p.get("d_safety_zone", ""),
                        p.get("service", "any"),
                        p.get("HA", ""),
                    ])
                    count += 1

            logger.info(f"生成NAT66策略CSV成功：{file_path} ({count} 条)")
            return count

        except Exception as e:
            logger.error(f"生成NAT66策略CSV失败: {e}")
            return False
