"""NAT64 策略 — NAT64 策略的增删查改、移动和导出。

对应 UI 页面「策略 → NAT64」。

对应 API 文档中的 ``create_or_update_nat64``、``get_nat64``、``remove_nat64``、
``move_nat64``、``export_nat64``。
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


class Nat64Feature(NFRequests):
    """NAT64 策略操作集合 — NAT64 策略的增删查改、移动和导出，以及 DNS46 记录管理。"""

    def create_or_update_nat64_policy(self, action='create', id='', name='',
        source_interface='', is_6to4=0, s_address='', d_address='',
        is_prefix=0, prefix_obj='', s_nat_obj='', d_nat_obj='',
        port_map_type=1, protocol='', orig_port='0-65535',
        nat_port='0-65535', load_balance='', HA='', enabled=True,
        priority=0, req_body=None):
        """创建或更新 NAT64/NAT46 策略。

        对应 API 文档中的 ``create_or_update_nat64``。

        通过 **is_6to4** 参数区分两种模式：

        - ``is_6to4=1`` — NAT64：源/目的地址为 IPv6，转换对象为 IPv4
        - ``is_6to4=0`` — NAT46：源/目的地址为 IPv4，转换对象为 IPv6

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 策略 ID，编辑时传入
        :type id: str
        :param name: 策略名称
        :type name: str
        :param source_interface: 源接口，如 ``"G1/1"``
        :type source_interface: str
        :param is_6to4: ``0``=NAT46，``1``=NAT64
        :type is_6to4: int
        :param s_address: 源地址/对象
        :type s_address: str
        :param d_address: 目的地址/对象
        :type d_address: str
        :param is_prefix: 前缀标志，默认 ``0``
        :type is_prefix: int
        :param prefix_obj: 前缀对象
        :type prefix_obj: str
        :param s_nat_obj: 源 NAT 转换对象
        :type s_nat_obj: str
        :param d_nat_obj: 目的 NAT 转换对象
        :type d_nat_obj: str
        :param port_map_type: 端口映射类型，默认 ``1``
        :type port_map_type: int
        :param protocol: 协议类型，如 ``"tcp"`` 或 ``""``
        :type protocol: str
        :param orig_port: 原始端口范围，默认 ``"0-65535"``
        :type orig_port: str
        :param nat_port: NAT 端口范围，默认 ``"0-65535"``
        :type nat_port: str
        :param load_balance: 负载均衡模式，如 ``"random"``
        :type load_balance: str
        :param HA: HA 线路
        :type HA: str
        :param enabled: 是否启用
        :type enabled: bool
        :param priority: 优先级，编辑时生效
        :type priority: int
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            data = {
                'action': action,
                'id': id,
                'name': name,
                'source_interface': source_interface,
                'is_6to4': is_6to4,
                's_address': s_address,
                'd_address': d_address,
                'is_prefix': is_prefix,
                'prefix_obj': prefix_obj,
                's_nat_obj': s_nat_obj,
                'd_nat_obj': d_nat_obj,
                'port_map_type': port_map_type,
                'protocol': protocol,
                'orig_port': orig_port,
                'nat_port': nat_port,
                'load_balance': load_balance,
                'HA': HA,
                'enabled': enabled,
                'priority': priority,
            }
        req_url = f'{self.base_url}/nf/strategy/nat64/'
        try:
            result = self.session.post(req_url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新NAT64策略失败: {e}')
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

    def get_nat64_policy(self, page=1, size=10, search='', method='match',
        req_param=None):
        """获取 NAT64 策略列表。

        对应 API 文档中的 ``get_nat64``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字，默认 ``""``
        :type search: str
        :param method: 匹配方式，默认 ``"match"``
        :type method: str
        :param req_param: 自定义查询参数，传入后覆盖默认参数
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {"total": int, "list": [...]}}``，
            失败返回 False
        :rtype: dict or bool
        """
        params = {'page': page, 'size': size, 'search': search, 'method': method}
        if req_param is not None:
            params = req_param
        req_url = f'{self.base_url}/nf/strategy/nat64/'
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取NAT64策略列表失败: {e}')
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

    def remove_nat64_policy(self, policy_ids, req_body=None):
        """删除 NAT64 策略。

        对应 API 文档中的 ``remove_nat64``。

        :param policy_ids: 策略 ID，支持 ``str`` 或 ``list``
        :type policy_ids: str or list
        :param req_body: 自定义请求体，传入后覆盖默认请求体
        :type req_body: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        if isinstance(policy_ids, list):
            policy_ids = ','.join(map(str, policy_ids))
        data = {'id': str(policy_ids)} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/strategy/nat64/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除NAT64策略失败: {e}')
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

    def move_nat64_policy(self, move_type='move', src_id='1', dst_id='2',
        req_param=None):
        """移动 NAT64 策略。

        对应 API 文档中的 ``move_nat64``。

        :param move_type: 移动类型，``"move"``（移动）或 ``"top"``（置顶）等
        :type move_type: str
        :param src_id: 源策略 ID
        :type src_id: str
        :param dst_id: 目标策略 ID（仅 ``move_type='move'`` 时生效）
        :type dst_id: str
        :param req_param: 自定义请求体，传入后覆盖默认参数
        :type req_param: dict or None
        :return: 成功返回 API 响应 JSON（dict），失败返回 False
        :rtype: dict or bool
        """
        data = {'type': move_type, 'srcId': src_id}
        if move_type == 'move':
            data['dstId'] = dst_id
        if req_param is not None:
            data = req_param
        req_url = f'{self.base_url}/nf/strategy/nat64/move/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'移动NAT64策略失败: {e}')
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

    def export_nat64_policy(self):
        """导出 NAT64 策略。

        对应 API 文档中的 ``export_nat64``。

        :return: 成功返回导出文本内容（str），失败返回 False
        :rtype: str or bool
        """
        req_url = f'{self.base_url}/nf/strategy/nat64/export/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出NAT64策略失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出NAT64策略成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def upload_nat64_policy_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入 NAT64 策略。

        对应接口 ``POST /nf/strategy/nat64/import/``。

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

        url = f'{self.base_url}/nf/strategy/nat64/import/'
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
            logger.error(f'上传NAT64策略CSV失败: {e}')
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
    def gen_nat64_policy_csv(file_path, policies, encoding="utf-8-sig"):
        """生成 NAT64 策略 CSV。

        :param file_path: CSV保存路径
        :type file_path: str

        :param policies: NAT64 策略列表，例如::

            [
                {
                    "name": "nat64",
                    "is_6to4": 1,
                    "is_prefix": 0,
                    "s_address": "1.1.1.1",
                    "d_address": "2.2.2.2",
                    "s_nat_obj": "3.3.3.3",
                    "d_nat_obj": "4.4.4.4",
                    "source_interface": "G1/1",
                    "port_map_type": 1,
                    "orig_port": "0-65535",
                    "nat_port": "0-65535",
                    "protocol": "tcp",
                    "prefix_obj": "127.0.0.1",
                    "load_balance": "random",
                    "HA": "ha",
                    "enabled": "yes"
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
            "nat6to4",
            "前缀映射",
            "源地址对象",
            "目的地址对象",
            "源nat对象",
            "目的nat对象",
            "源接口",
            "端口映射类型",
            "原始目的端口",
            "映射目的端口",
            "协议",
            "前缀对象",
            "负载均衡(random(随机)/round_robin(轮询)/hash(哈希))",
            "HA线路",
            "是否启用（yes/no）",
        ]

        try:
            with open(file_path, "w", encoding=encoding, newline="") as f:

                writer = csv.writer(f)

                # 注释
                f.write("#以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略\n")
                f.write("#部分版本office、wps无法自动识别wps文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件\n")
                f.write("#负载均衡支持随机、轮询和哈希3种算法。\n")
                f.write("#如果一个字段下需要输入多个值，值与值之间用逗号作为分隔符\n")
                f.write("#策略名称,nat6to4,前缀映射,源地址对象,目的地址对象,源nat对象,目的nat对象,源接口,端口映射类型,原始目的端口,映射目的端口,协议,前缀对象,负载均衡(random(随机)/round_robin(轮询)/hash(哈希)),HA线路,是否启用（yes/no）\n")
                f.write("#示例1：nat64,1,0,1.1.1.1,2.2.2.2,3.3.3.3,4.4.4.4,G1/1,1,0-65535,0-65535,tcp,127.0.0.1,random,ha,yes\n")

                # 表头
                writer.writerow(["#" + headers[0], headers[1], headers[2],
                                 headers[3], headers[4], headers[5], headers[6],
                                 headers[7], headers[8], headers[9], headers[10],
                                 headers[11], headers[12], headers[13],
                                 headers[14], headers[15]])

                count = 0

                for p in policies:
                    enabled = p.get("enabled", "yes")
                    if isinstance(enabled, bool):
                        enabled = "yes" if enabled else "no"

                    writer.writerow([
                        p.get("name", ""),
                        p.get("is_6to4", 0),
                        p.get("is_prefix", 0),
                        p.get("s_address", ""),
                        p.get("d_address", ""),
                        p.get("s_nat_obj", ""),
                        p.get("d_nat_obj", ""),
                        p.get("source_interface", ""),
                        p.get("port_map_type", 1),
                        p.get("orig_port", ""),
                        p.get("nat_port", ""),
                        p.get("protocol", ""),
                        p.get("prefix_obj", ""),
                        p.get("load_balance", ""),
                        p.get("HA", ""),
                        enabled,
                    ])
                    count += 1

            logger.info(f"生成NAT64策略CSV成功：{file_path} ({count} 条)")
            return count

        except Exception as e:
            logger.error(f"生成NAT64策略CSV失败: {e}")
            return False

    def create_or_update_dns46_record(self, action='create', domain_name='',
        record_id=0, ipv4='', ipv6='', is_enable=True, comment='',
        req_body=None):
        """创建或更新 DNS46 记录（域名→IPv4+IPv6 双栈映射）。

        对应接口 ``POST /nf/network/dns/dns46/action_dns46/``。

        :param action: 操作类型，``'create'`` 或 ``'edit'``，默认 ``'create'``
        :type action: str
        :param domain_name: 域名，如 ``'test6.com'``
        :type domain_name: str
        :param record_id: 记录 ID，编辑时传入
        :type record_id: int
        :param ipv4: 映射的 IPv4 地址，如 ``'192.168.91.3'``
        :type ipv4: str
        :param ipv6: 映射的 IPv6 地址，如 ``'10:66::251:152'``
        :type ipv6: str
        :param is_enable: 是否启用，默认 ``True``
        :type is_enable: bool
        :param comment: 备注，默认 ``''``
        :type comment: str
        :param req_body: 自定义请求体，传入后忽略其他参数
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            data = {
                'action': action,
                'domain_name': domain_name,
                'id': record_id,
                'ipv4': ipv4,
                'ipv6': ipv6,
                'is_enable': is_enable,
                'comment': comment,
            }
        url = f'{self.base_url}/nf/network/dns/dns46/action_dns46/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新DNS46记录失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns46_record_list(self, page=1, size=10, search='', req_param=None):
        """获取 DNS46 记录列表。

        对应接口 ``GET /nf/network/dns/dns46/info/``。

        :param page: 页码，默认 ``1``
        :type page: int
        :param size: 每页数量，默认 ``10``
        :type size: int
        :param search: 搜索关键字，默认 ``''``
        :type search: str
        :param req_param: 自定义查询参数，传入后优先使用
        :type req_param: dict or None
        :return: 成功返回 ``{"status": 2000, "result": {...}}``，失败返回 ``False``
        :rtype: dict or bool
        """
        params = {'page': page, 'size': size, 'search': search}
        if req_param is not None:
            params = req_param
        url = f'{self.base_url}/nf/network/dns/dns46/info/'
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取DNS46记录列表失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_dns46_record_id(self, search=''):
        """根据域名查询 DNS46 记录 ID。

        :param search: 搜索关键字（域名匹配）
        :type search: str
        :return: 匹配到的 ID (int)，失败返回 ``False``
        :rtype: int or bool
        """
        resp = self.get_dns46_record_list(search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('domain_name') == search:
                return item.get('id')
        return False

    def remove_dns46_record(self, record_ids, req_body=None):
        """删除 DNS46 记录。

        对应接口 ``POST /nf/network/dns/dns46/delete_dns46/``。

        :param record_ids: 记录 ID，支持 ``int`` 或 ``list``
        :type record_ids: int or list
        :param req_body: 自定义请求体，传入后优先使用
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 ``False``
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            if isinstance(record_ids, int):
                record_ids = [record_ids]
            data = {'id': record_ids}
        url = f'{self.base_url}/nf/network/dns/dns46/delete_dns46/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除DNS46记录失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False
