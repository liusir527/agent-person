"""NAT 策略。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class NatFeature(NFRequests):
    """NAT 策略操作集合。"""

    def create_or_update_nat_policy(self, name='test', nat_type=0, enabled=True,
        action='create', id='', s_safety_zone='GLOBAL', d_safety_zone='GLOBAL',
        s_address='any', d_address='any', service='any',
        s_address_translation=1, nat_object='interface_ip',
        in_interface='G1/1',out_interface="G1/1",
        interface_type="normal",internal_address="1.1.1.1",
        port_map_type="2",protocol="tcp",
        external_address="2.2.2.2", load_balance="random",
        health_check="",HA='',external_port="0-65535",internal_port="0-65535",
        src_ip_hold='1'):
        """创建或更新 NAT 策略。

        对应 UI 页面「安全策略 → NAT 策略 → 新建/编辑」。
        根据 ``nat_type`` 的不同，发送不同结构的请求体：

        - ``nat_type=0``：SNAT（源 NAT），使用源/目的安全区、地址、服务、出接口等字段。
        - ``nat_type=1``：DNAT（目的 NAT），使用入接口、内外部地址/端口映射等字段。
        - ``nat_type=2``：双向 NAT，同时包含 SNAT 和 DNAT 相关字段。

        .. note::
            源/目的地址、服务对象需先创建，传入对象名称（字符串），多个以逗号分隔。

        :param name:                 策略名称，默认 ``"test"``。
        :param nat_type:             NAT 类型。``0`` = SNAT（默认），``1`` = DNAT，``2`` = 双向 NAT。
        :param enabled:              是否启用，默认 ``True``。
        :param action:               操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param id:                   策略 ID，新建时传 ``""``，编辑时传对应策略 ID。
        :param s_safety_zone:        源安全区名称，字符串或列表，默认 ``"GLOBAL"``。（SNAT/双向 NAT）
        :param d_safety_zone:        目的安全区名称，字符串或列表，默认 ``"GLOBAL"``。（SNAT）
        :param s_address:            源地址对象名称，支持子网/节点/地址池/地址组，默认 ``"any"``。（SNAT/双向 NAT）
        :param d_address:            目的地址对象名称，默认 ``"any"``。（SNAT）
        :param service:              服务对象名称，多个以逗号分隔，默认 ``"any"``。（SNAT）
        :param s_address_translation: 源地址转换方式。``1`` = 使用出接口主 IP（默认），``2`` = 使用网络对象地址。（SNAT/双向 NAT）
        :param nat_object:           转换地址对象名称。``s_address_translation=1`` 时填 ``"interface_ip"``；
                                     ``s_address_translation=2`` 时填网络对象名称。（SNAT/双向 NAT）
        :param in_interface:         入接口名称，默认 ``"G1/1"``。（DNAT/双向 NAT）
        :param out_interface:        出接口名称（映射到请求体 ``dst_port`` 字段），默认 ``"G1/1"``。（SNAT/双向 NAT）
        :param interface_type:       接口类型。``"normal"`` = 普通接口（默认），``"pppoe"`` = PPPoE 接口。（DNAT/双向 NAT）
        :param internal_address:     内部映射地址，仅支持节点或不超过 32 个地址的地址池，默认 ``"1.1.1.1"``。（DNAT/双向 NAT）
        :param port_map_type:        端口映射类型。``"1"`` = 多对多（外内端口数量一致），``"2"`` = 全端口映射（默认）。（DNAT/双向 NAT）
        :param protocol:             转换协议。``"tcp"``（默认）、``"udp"``、``"icmp"``。（DNAT/双向 NAT）
        :param external_address:     外部映射地址，仅支持节点或不超过 32 个地址的地址池，默认 ``"2.2.2.2"``。（DNAT/双向 NAT）pppoe接口时为空
        :param load_balance:         负载分担模式。``"random"``（默认）、``"round_robin"``、``"hash"``。（DNAT/双向 NAT）
        :param health_check:         内部地址健康检查，使用链路探测名称，默认 ``""``。
        :param HA:                   HA 线路名称，默认 ``""``。
        :param external_port:        外部端口范围，默认 ``"0-65535"``。（DNAT/双向 NAT）
        :param internal_port:        内部端口范围，默认 ``"0-65535"``。（DNAT/双向 NAT）
        :param src_ip_hold:          源接口地址保持。``"0"`` = 开启，``"1"`` = 关闭（默认）。（SNAT）
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if nat_type==0:
            data = {'name': name, 'nat_type': nat_type, 'action': action, 'id': id,
                's_safety_zone': s_safety_zone, 'd_safety_zone': d_safety_zone,
                's_address': s_address, 'd_address': d_address, 'service': service,
                'dst_port': out_interface, 's_address_translation':
                s_address_translation, 'nat_object': nat_object, 'enabled': enabled,
                'HA': HA, 'src_ip_hold': src_ip_hold}
        elif nat_type==1:
            data = {'name': name, 'nat_type': nat_type, 'action': action, 'id': id,
                    "interface":in_interface,"interface_type":interface_type,
                    "port_map_type":port_map_type,"protocol":protocol,
                    "external_address":external_address,"external_port":external_port,
                    "internal_address":internal_address,"internal_port":internal_port,
                    "load_balance":load_balance,'HA':HA,"enabled":enabled}
        elif nat_type ==2:
            data = {'name': name, 'nat_type': nat_type, 'action': action, 'id': id,
                    "dst_port":in_interface,"interface_type":interface_type,
                    "port_map_type":port_map_type,"protocol":protocol,
                    "external_address":external_address,"external_port":external_port,
                    "internal_address":internal_address,"internal_port":internal_port,'interface': out_interface,
                    "load_balance":load_balance,'HA':HA,"nat_object":nat_object,"s_address":s_address,
                    "s_address_translation":s_address_translation,"s_safety_zone":s_safety_zone,"enabled":enabled}

        # print(data)
        req_url = f'{self.base_url}/nf/strategy/nat/nat_action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新NAT策略失败: {e}')
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

    def get_nat_policy(self, page=1, size=10, sort_type='priority', where='OR',
        reload="false",name=None):
        """获取 NAT 策略列表。

        对应 UI 页面「安全策略 → NAT 策略」。

        :param page:      页码，从 ``1`` 开始，默认 ``1``。
        :param size:      每页返回条数，默认 ``10``。
        :param sort_type: 排序类型，默认 ``"priority"``（按优先级）。
        :param where:     查询条件，默认 ``"OR"``。
        :param reload:    是否强制重新加载，``"false"``（默认）或 ``"true"``。
        :param name:      策略名称过滤，默认 ``None``（不过滤）。
        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": {"total": N, "list": [...], "haModels": "1"}, ...}``；
                 其中 ``list`` 每条记录包含 ``id``、``name``、``nat_type``、``enabled``、
                 ``s_safety_zone``、``d_safety_zone``、``s_address``、``d_address``、
                 ``service``、``dst_port``（出接口）等字段。
                 ``nat_type``：``0`` = SNAT，``1`` = DNAT，``2`` = 双向 NAT。
                 失败时返回 ``False``。
        """
        data = {'page': page, 'size': size, 'type': sort_type, 'where': where,"reload":reload,"name":name}


        req_url = f'{self.base_url}/nf/strategy/nat/info/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'获取NAT策略列表失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
    
    def get_nat_policy_id(self,name,page=1, size=10):
        """根据名称查询 NAT 策略 ID。

        调用 :meth:`get_nat_policy` 查询后，按 ``name`` 精确匹配返回策略 ID。

        :param name: 策略名称，用于精确匹配，必填。
        :param page: 页码，默认 ``1``。
        :param size: 每页条数，默认 ``10``。
        :return: 成功时返回策略 ID（整数）；未找到或失败时返回 ``False``。
        """
        resp=self.get_nat_policy(name=name,size=size,page=page)

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
        

    def remove_nat_policy(self, ids, req_body=None):
        """删除 NAT 策略。

        对应 UI 页面「安全策略 → NAT 策略 → 删除」操作。

        :param ids:      策略 ID，字符串、整数或列表。多个 ID 传列表，例如 ``[1, 2, 3]``。
        :param req_body: 自定义请求体 dict，传入后忽略 ``ids`` 参数，直接作为
                         POST body 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if isinstance(ids, list):
            ids = ','.join(map(str, ids))
        elif isinstance(ids, str):
            ids = str(ids)
        data = {'ids': str(ids)} if req_body is None else req_body
        req_url = f'{self.base_url}/nf/strategy/nat/delete_nat/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除NAT策略失败: {e}')
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

    def clear_nat_policy(self):
        """清空所有 NAT 策略。

        对应 UI 页面「安全策略 → NAT 策略 → 清空」操作，删除设备上全部 NAT 策略。

        .. warning::
            此操作不可逆，生产环境请谨慎使用。

        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/strategy/nat/clear_nat/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空NAT策略失败: {e}')
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

    def enable_nat_policy(self, ids, enabled=None, req_param=None):
        """启用或禁用 NAT 策略。

        对应 UI 页面「安全策略 → NAT 策略」列表中的启用/禁用开关。

        :param ids:       策略 ID，字符串、整数或列表。多个 ID 传列表，例如 ``[1, 2]``。
        :param enabled:   目标状态。``True`` = 启用，``False`` = 禁用。
        :param req_param: 自定义请求体 dict，传入后忽略 ``ids`` 和 ``enabled`` 参数，
                          直接作为 POST body 发送。用于特殊场景或调试。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        if isinstance(ids, list):
            ids = ','.join(map(str, ids))
        data = {'ids': ids, 'enabled': enabled} if req_param is None else req_param
        req_url = f'{self.base_url}/nf/strategy/nat/enable_nat/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'启用或禁用NAT策略失败: {e}')
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

    def move_nat_policy(self, req_param):
        """移动 NAT 策略位置。

        对应 UI 页面「安全策略 → NAT 策略 → 移动」操作。

        :param req_param: 原生请求体 dict，直接作为 POST body 发送。
                          移动到顶部/底部时格式为 ``{"type": "top"/"bottom", "srcRuleId": "1"}``；
                          移动到指定位置时格式为 ``{"srcRuleId": "1", "dstRuleId": "2"}``。
        :return: 成功时返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败时返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/strategy/nat/move/'
        try:
            result = self.session.post(req_url, data=json.dumps(req_param),
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'移动NAT策略失败: {e}')
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

    def export_nat_policy(self, query_order='priority'):
        """导出 NAT 策略为文本/CSV 格式。

        对应 UI 页面「安全策略 → NAT 策略 → 导出」操作。

        :param query_order: 导出排序方式，默认 ``"priority"``（按优先级）。
        :return: 成功时返回导出内容字符串（CSV/文本格式）；失败时返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/strategy/nat/export_nat/'
        try:
            result = self.session.get(req_url, params={'query_order':
                query_order}, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出NAT策略失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出NAT策略成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_nat_policy_tree(self):
        """获取 NAT 策略总览（树形列表）。

        返回所有 NAT 策略的简要信息，常用于下拉选择或策略概览展示。

        :return: 成功时返回完整响应 dict，结构为
                 ``{"status": 2000, "result": [{"id": 1, "name": "...", "nat_type": 0}, ...], ...}``；
                 ``nat_type``：``0`` = SNAT，``1`` = DNAT，``2`` = 双向 NAT。
                 失败时返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/strategy/nat/tree/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取NAT策略总览失败: {e}')
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
    def upload_nat_policy_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入 NAT 策略。

        对应接口 ``POST /nf/strategy/nat/upload_nat/``，``multipart/form-data`` 上传。

        当策略数量较多（如 500+ 条）时，建议用本接口替代逐条
        :meth:`create_or_update_nat_policy`，避免大量 HTTP 请求开销。
        CSV 文件可由 :meth:`gen_nat_policy_csv` 生成，格式与 NAT 策略导出一致。

        :param file_path: CSV 文件路径。文件格式参考 NAT 导出的策略 CSV，
            第 1-5 行为注释，第 6 行为表头，第 7 行为示例，其后为数据行。
            字段顺序见 :meth:`gen_nat_policy_csv`。
        :type file_path: str
        :param req_body: 自定义请求体字段，传入后会合并到上传请求的 form data 中。
            一般场景无需传入。
        :type req_body: dict or None
        :return: 成功返回完整响应 dict，结构为 ``{"status": 2000, "message": "...", ...}``；
                 失败返回 ``False``。
        :rtype: dict or bool
        """
        import os
        if not os.path.exists(file_path):
            logger.error(f'CSV 文件不存在: {file_path}')
            return False
        url = f'{self.base_url}/nf/strategy/nat/upload_nat/'
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'text/csv')}
                data = req_body if req_body is not None else {}
                result = self.session.post(url, files=files, data=data,
                    verify=False, timeout=300)
        except Exception as e:
            logger.error(f'上传NAT策略CSV失败: {e}')
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

    @staticmethod
    def gen_nat_policy_csv(file_path, policies, encoding='utf-8-sig'):
        """生成 NAT 策略 CSV 文件（标准格式，可直接上传）。

        生成的 CSV 格式与 NAT 策略导出格式一致，可直接通过
        :meth:`upload_nat_policy_csv` 上传导入。配合上传接口，可实现大批量
        策略的快速导入（替代逐条 :meth:`create_or_update_nat_policy`）。

        :param file_path: 输出 CSV 文件路径
        :type file_path: str
        :param policies: 策略列表，每个元素为 dict，支持以下字段（均可选，
            未提供的字段留空）：

            * ``name`` — 策略名称（必填）
            * ``nat_type`` — NAT 类型。``0`` = 源 NAT，``1`` = 目的 NAT，``2`` = 双向 NAT（默认 ``0``）
            * ``s_address`` — 源地址，str（默认 ``"any"``）
            * ``d_address`` — 目的地址/外部地址
            * ``nat_object`` — 源地址转换/NAT 对象，NAT 对象为目的接口主 ip 时填 ``"interface_ip"``（默认 ``"interface_ip"``）
            * ``internal_address`` — 目的地址转换/内部地址
            * ``enabled`` — 是否启用，``"yes"`` / ``"no"``（默认 ``"yes"``）
            * ``s_safety_zone`` — 源安全区，str 或 list[str]（默认 ``"GLOBAL"``）
            * ``d_safety_zone`` — 目的安全区，str 或 list[str]（默认 ``"GLOBAL"``）
            * ``service`` — 服务，str（默认 ``"any"``）
            * ``in_interface`` — 入接口
            * ``port_map_type`` — 端口映射类型，``1`` = 映射部分端口，``2`` = 映射全部端口
            * ``internal_port`` — 内部端口
            * ``external_port`` — 外部端口
            * ``s_address_translation`` — 地址转换，``1`` = 接口地址，``2`` = 网络对象
            * ``d_address_object`` — 目的地址对象
            * ``interface_type`` — 接口类型，``"normal"`` = 普通接口，``"pppoe"`` = PPPoE 接口
            * ``out_interface`` — 出接口，双向 NAT 支持多选（list 自动逗号拼接）
            * ``protocol`` — 协议，``"tcp"`` / ``"udp"``
            * ``health_check`` — 服务器健康检查，str 或 list[str]
            * ``load_balance`` — 负载均衡，``"random"`` / ``"round_robin"`` / ``"hash"``
            * ``HA`` — HA 线路
            * ``src_ip_hold`` — 源地址保持，``0`` = 开启，``1`` = 关闭（默认 ``1``）
        :type policies: list[dict]
        :param encoding: 文件编码，默认 ``"utf-8-sig"``（带 BOM，兼容 Excel/WPS）
        :type encoding: str
        :return: 成功返回写入的策略条数，失败返回 ``False``
        :rtype: int or bool

        使用示例::

            policies = [
                {"name": "电信出口", "nat_type": "0", "out_interface": "G1/2"},
                {"name": "双向NAT_web", "nat_type": "2", "d_address": "1.24.246.90",
                 "internal_address": "192.168.92.3", "in_interface": "G1/3",
                 "internal_port": "80", "external_port": "74", "out_interface": ["G1/5","G1/6","G1/7"]},
                ["name":"PPPOE_DNAT","nat_type": "1","interface_type","pppoe",
                "in_interface":"G1/4","port_map_type":"1","external_port":"74",
                "internal_port":"80","internal_address":"192.168.92.3"]
            ]
            NatFeature.gen_nat_policy_csv("nat_policy.csv", policies)
            nf.policy.nat.upload_nat_policy_csv("nat_policy.csv")
        """
        import csv
        headers = [
            '策略名称',
            '策略类型(0:源nat 1:目的nat 2:双向nat)',
            '源地址',
            '目的地址/外部地址',
            '源地址转换/NAT对象((NAT对象为目的接口主ip时填 interface_ip))',
            '目的地址转换/内部地址',
            '是否启用（yes,no）',
            '源安全区',
            '目的安全区',
            '服务',
            '入接口',
            '端口映射类型（1:映射部分端口 2:映射全部端口）',
            '内部端口',
            '外部端口',
            '地址转换(1:接口地址 2: 网络对象)',
            '目的地址对象',
            '接口类型normal(普通接口)',
            '出接口(双向nat出接口支持多选,用","隔开)',
            '协议(tcp/udp)',
            '服务器健康检查(可选多个，逗号分隔)',
            '负载均衡(random(随机)/round_robin(轮询)/hash(哈希))',
            'HA线路',
            '源地址保持',
        ]

        def _join(val):
            """list 自动逗号拼接，None 返回空字符串。"""
            if val is None:
                return ''
            if isinstance(val, list):
                return ','.join(str(v) for v in val)
            return str(val)

        try:
            with open(file_path, 'w', encoding=encoding, newline='') as f:
                w = csv.writer(f)
                # 注释行（与 NAT 导出格式一致），按原始文本写入，保持与设备导出逐字节一致
                f.write('#以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略\n')
                f.write('#部分版本office、wps无法自动识别wps文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件\n')
                f.write('#根据NAT类型不同，字段名根据类型和界面展示而定，同一字段不同类型名使用/隔开\n')
                f.write('#服务默认为any，启用默认为yes\n')
                f.write('#如果一个字段下需要输入多个值，值与值之间用逗号作为分隔符\n')
                # 表头行：首字段前缀 #，其余按 CSV 规则逐字段引用（含逗号的字段自动加引号）
                w.writerow(['#' + headers[0]] + headers[1:])
                # 示例行：按原始文本写入（与设备导出示例一致）
                f.write('#示例1：nat1,2,10.10.0.0/16,2.2.2.2,100.0.0.1,1.1.1.1,yes,Intranet,,,G1/1,1,4486,5529,1,,,"G2/2,G2/3",tcp,0,random,,0\n')
                # 数据行
                count = 0
                for p in policies:
                    row = [
                        p.get('name', ''),
                        _join(p.get('nat_type', '0')),
                        p.get('s_address', 'any'),
                        _join(p.get('d_address')),
                        p.get('nat_object', 'interface_ip'),
                        _join(p.get('internal_address')),
                        p.get('enabled', 'yes'),
                        _join(p.get('s_safety_zone', 'GLOBAL')),
                        _join(p.get('d_safety_zone')),
                        p.get('service', 'any'),
                        _join(p.get('in_interface')),
                        _join(p.get('port_map_type', '2')),
                        _join(p.get('internal_port')),
                        _join(p.get('external_port')),
                        _join(p.get('s_address_translation', '1')),
                        _join(p.get('d_address_object', 'any')),
                        p.get('interface_type', 'normal'),
                        _join(p.get('out_interface')),
                        p.get('protocol', ''),
                        _join(p.get('health_check')),
                        p.get('load_balance', ''),
                        _join(p.get('HA')),
                        p.get('src_ip_hold', '1'),
                    ]
                    w.writerow(row)
                    count += 1
            logger.info(f'生成NAT策略 CSV: {file_path} ({count} 条)')
            return count
        except Exception as e:
            logger.error(f'生成NAT策略 CSV 失败: {e}')
            return False