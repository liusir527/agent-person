"""网络对象 Facade — 向后兼容地聚合所有对象子模块。

对应 UI 页面「对象管理 → 网络对象」。
"""

import json
import logging

from nf_requests.nflib.Log import logger
from .server_object import ServerObjectFeature
from .app_object import AppObjectFeature
from .time_object import TimeObjectFeature
from .user_object import UserObjectFeature
from .cert_object import CertObjectFeature
from .keyword_object import KeywordObjectFeature
from .location_object import LocationObjectFeature
from .antivirus_object import AntivirusObjectFeature
from .ips_object import IpsObjectFeature
from .url_object import UrlObjectFeature
from .scm_object import ScmObjectFeature
from .waf_object import WafObjectFeature
from .vul_object import VulObjectFeature
from ..client import NFRequests


class NetworkObjectFeature(NFRequests):
    """网络对象操作集合 — Facade，聚合所有拆分的对象子模块。

    原始 NetworkObjectFeature 的所有方法均可通过本 Facade 直接调用——
    网络对象自身 CRUD 保留在此类中，其余方法通过 ``__getattr__`` 自动委托
    到对应的 Feature 子类（ServerObjectFeature, AppObjectFeature, …）。
    """

    def __init__(self, context):
        super().__init__(context)
        self._sub_features = [
            ServerObjectFeature(context),
            AppObjectFeature(context),
            TimeObjectFeature(context),
            UserObjectFeature(context),
            CertObjectFeature(context),
            KeywordObjectFeature(context),
            LocationObjectFeature(context),
            AntivirusObjectFeature(context),
            IpsObjectFeature(context),
            UrlObjectFeature(context),
            ScmObjectFeature(context),
            WafObjectFeature(context),
            VulObjectFeature(context),
        ]

    # ---- 委托机制 ----

    def __getattr__(self, name):
        # 排除私有属性，避免无限递归
        if name.startswith('_'):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'")
        for sf in self._sub_features:
            if hasattr(sf, name):
                attr = getattr(sf, name)
                if callable(attr):
                    return attr
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'")

    # ================================================================
    #  网络对象自身 CRUD（保留在 Facade 内）
    # ================================================================

    def create_or_update_network_obj(self, action='create', net_type='node',
            name='', description='', net_address='1.1.1.1', mask='',
            start_ip='', end_ip='', group=None, net_id=None, is_addition=0,
            ability='1', auto_fill='0', id=None, type=None, ip_address=None,
            mac='', domain='', contain_object='', note="", is_ipv6=False
            ):
        """创建或编辑网络对象。

        对应 UI 页面「对象管理 → 网络对象」。

        .. note::

            **参数优先级**：``type`` 优先于 ``net_type``。

            * 优先使用 ``type`` 参数指定对象类型
            * 仅当 ``type`` 未传（为 ``None``）时，才回退使用 ``net_type``
            * ``net_type`` 仅为兼容旧调用保留，新代码请统一使用 ``type``

        :param action: 操作类型，``"create"`` = 新建，``"edit"`` = 编辑，默认 ``"create"``。
        :param net_type: （兼容旧调用）网络对象类型，默认 ``"node"``。仅当 ``type`` 为
            ``None`` 时生效，新代码请改用 ``type`` 参数。
        :param type: 网络对象类型，**优先于 ``net_type``**，默认 ``None``（回退到
            ``net_type``）。可选值：

            * ``"node"`` — 节点（IP 地址）
            * ``"segment"`` — 网段
            * ``"pool"`` — IP 地址池
            * ``"group"`` — 地址组
            * ``"mac"`` — MAC 地址
            * ``"domain"`` — 域名

            不同 ``type`` 对应不同的必填/可选字段：
            ``"node"/"segment"/"pool"`` 需要 ``ip_address``；
            ``"mac"`` 需要 ``mac``；
            ``"group"`` 需要 ``contain_object``；
            ``"domain"`` 需要 ``domain``。
        :param name: 网络对象名称，默认 ``"autotest"``。
        :param description: 兼容旧调用的描述，未传 ``note`` 时映射为 ``note``。
        :param note: OpenAPI 备注字段，优先于 ``description``。
        :param net_address: 兼容旧调用的网络地址，默认 ``"1.1.1.1"``。
        :param mask: 兼容旧调用的掩码，非空时拼接到 ``ip_address``。
        :param start_ip: 兼容旧调用的起始 IP，地址池类型时用于生成 ``ip_address``。
        :param end_ip: 兼容旧调用的结束 IP，地址池类型时用于生成 ``ip_address``。
        :param group: 兼容旧调用的地址组内容，未传 ``contain_object`` 时映射。
        :param net_id: 兼容旧调用的对象 ID，映射为 ``id``。
        :param id: OpenAPI 对象 ID 字段，优先于 ``net_id``。
        :param ip_address: OpenAPI IP 地址字段，显式传入时优先使用。
        :param mac: OpenAPI MAC 地址字段，``type='mac'`` 时使用。
        :param domain: OpenAPI 域名字段，``type='domain'`` 时使用。
        :param contain_object: OpenAPI 包含对象字段，``type='group'`` 时使用，优先于 ``group``。
        :param is_ipv6: OpenAPI IPv6 标志字段。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if name == "" and ip_address==None:
            name = ip_address
        obj_type = type if type is not None else net_type
        obj_id = id if id is not None else net_id
        obj_note = note if note is not None else description
        if ip_address is None:
            if start_ip and end_ip:
                ip_address = f'{start_ip}-{end_ip}'
            elif mask:
                ip_address = f'{net_address}/{mask}'
            else:
                ip_address = net_address
        if not contain_object and group is not None:
            contain_object = ','.join(map(str, group)) if isinstance(group, list) else group

        if action=="edit":
            if obj_type=="node" or obj_type =="segment" or obj_type == "pool":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'ip_address': ip_address, "negation":"false","id":id}
            elif obj_type =="mac":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'mac': mac, "negation":"false","id":id}
            elif obj_type == "group":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'contain_object': contain_object, "negation":"false","id":id}
            elif obj_type =="domain":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'domain': domain, "negation":"false","id":id,
                    'is_ipv6': is_ipv6}
        else:
            if obj_type=="node" or obj_type =="segment" or obj_type == "pool":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'ip_address': ip_address, "negation":"false"}
            elif obj_type =="mac":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'mac': mac, "negation":"false"}
            elif obj_type == "group":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'contain_object': contain_object, "negation":"false"}
            elif obj_type =="domain":
                data = {'action': action, 'name': name, 'note':note,
                    'type': obj_type, 'domain': domain, "negation":"false",
                    'is_ipv6': is_ipv6}

        req_url = f'{self.base_url}/nf/object/networkobj/'
        try:
            result = self.session.post(req_url, json=data, verify=False,
                                       timeout=30)
        except Exception as e:
            logger.error(f'创建或修改网络对象失败: {e}')
            return False
        if result.status_code == 200:
            status = json.loads(result.text)['status']

            message = json.loads(result.text)['message']
            if status != 2000:
                logger.error(message)
                return False
            else:
                logger.info(message)
                return json.loads(result.text)
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_network_obj(self, net_type='segment', page=1, size=10, search='',
            name=None, group=None, is_v6=None, type=None):
        """获取网络对象列表。

        对应 UI 页面「对象管理 → 网络对象」。

        :param net_type: 兼容旧调用的网络对象类型，默认 ``"segment"``。
        :param type: OpenAPI 对象类型，优先于 ``net_type``。
            参见 [`create_or_update_network_obj()`](network_object.py) 的 ``type`` 枚举说明。
        :param page: 页码，默认 1。
        :param size: 每页条数，默认 10。
        :param search: 搜索关键字，默认 ``""``。
        :param is_v6: 是否 IPv6，OpenAPI 查询参数，默认不发送。
        :param name: 兼容旧调用的精确名称筛选，仅显式传入时发送。
        :param group: 兼容旧调用的分组筛选，仅显式传入时发送。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        obj_type = type if type is not None else net_type
        req_url = f'{self.base_url}/nf/object/networkobj/'
        params = {'type': obj_type, 'page': page, 'size': size,
                  'search': search}
        if is_v6 is not None:
            params['is_v6'] = is_v6
        if name is not None:
            params['name'] = name
        if group is not None:
            params['group'] = group
        try:
            result = self.session.get(req_url, params=params, verify=False,
                                      timeout=30)
        except Exception as e:
            logger.error(f'查询网络对象失败: {e}')
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

    def get_network_obj_id(self, net_type='segment', page=1, size=10, search='',
            name=None, group=None, is_v6=None, type=None):
        """按名称查询网络对象 ID。

        通过 [`get_network_obj()`](network_object.py) 获取列表后按名称精确匹配。

        :param net_type: 兼容旧调用的网络对象类型，默认 ``"segment"``。
        :param type: OpenAPI 对象类型，优先于 ``net_type``。
        :param page: 页码，默认 1。
        :param size: 每页条数，默认 10。
        :param search: 搜索关键字，默认 ``""``。
        :param name: 精确名称筛选，匹配到则返回对应 ID。
        :param group: 分组筛选。
        :param is_v6: 是否 IPv6。
        :return: 成功返回 ID 值；失败返回 ``False``。
        """
        resp = self.get_network_obj(net_type=net_type, page=page, size=size, search=search,
            name=name, group=group, is_v6=is_v6, type=type)
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

    def remove_network_obj(self, obj_id):
        """删除网络对象。

        对应 UI 页面「对象管理 → 网络对象」。

        :param obj_id: 网络对象 ID，可以是单个值（int/str）或 list，list 会用逗号拼接。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(obj_id, list):
            obj_id = ','.join(map(str, obj_id))
        data = {'id': str(obj_id)}
        req_url = f'{self.base_url}/nf/object/networkobj_delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False,timeout=30)
        except Exception as e:
            logger.error(f'删除网络对象失败: {e}')
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

    def update_domain_obj_global_config(self, max_level=32):
        """更新域名对象全局配置。

        对应 UI 页面「对象管理 → 网络对象 → 域名对象全局配置」。

        :param max_level: 最大域名解析层级，默认 32。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'max_level': max_level}
        req_url = f'{self.base_url}/nf/object/domain/global_config/'
        try:
            result = self.session.post(req_url, json=data, verify=False,
                                       timeout=30)
        except Exception as e:
            logger.error(f'更新域名对象全局配置失败: {e}')
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

    def get_domain_obj_global_config(self):
        """获取域名对象全局配置。

        对应 UI 页面「对象管理 → 网络对象 → 域名对象全局配置」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/object/domain/global_config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取域名对象全局配置失败: {e}')
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

    def get_network_obj_referenced(self):
        """获取网络对象引用信息。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/object/network_obj_referenced/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取网络对象引用信息失败: {e}')
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

    # ---- NAT 策略模板（待迁移，保留兼容） ----

    def get_export_nat_template(self):
        """获取 NAT 策略模板。

        此方法后续将迁移至 policy/nat.py。

        :return: 成功返回模板文本内容（str）；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/strategy/nat/export_nat_template/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取NAT策略模板失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('获取NAT策略模板成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
    def upload_network_object_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入网络对象。
        
        对应接口 ``POST /nf/object/networkobj_upload/``。

        :param file_path: CSV 文件路径
        :type file_path: str
        :param req_body: 自定义 form-data 参数
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 False
        :rtype: dict or bool
        """
        import os
        import json

        if not os.path.exists(file_path):
            logger.error(f'CSV 文件不存在: {file_path}')
            return False

        url = f'{self.base_url}/nf/object/networkobj_upload/'
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as f:
                files = {
                    "file": (filename, f, "text/csv")
                }

                data = {
                    "type": "node"
                }

                result = self.session.post(
                    url,
                    files=files,
                    data=data,
                    verify=False,
                    timeout=300
                )

        except Exception as e:
            logger.error(f'上传网络对象CSV失败: {e}')
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
    def gen_network_object_csv(file_path, objects, encoding="utf-8-sig"):
        """生成网络对象 CSV。

        :param file_path: CSV保存路径
        :type file_path: str

        :param objects: 网络对象列表，例如::

            [
                {
                    "name": "192.168.1.0/24",
                    "value": "192.168.1.0/24",
                    "comment": ""
                },
                {
                    "name": "host1",
                    "value": "192.168.1.1",
                    "comment": "测试"
                }
            ]

        :type objects: list[dict]

        :param encoding: 文件编码
        :type encoding: str

        :return: 成功返回对象数量，失败返回 False
        :rtype: int or bool
        """
        import csv

        headers = [
            "对象名称",
            "对象取值",
            "备注",
        ]

        try:
            with open(file_path, "w", encoding=encoding, newline="") as f:

                writer = csv.writer(f)

                # 注释
                f.write("#以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略\n")
                f.write("#部分版本office、wps无法自动识别wps文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件\n")
                f.write("#地址对象的取值的约定.\n")
                f.write("#网络对象:网段+掩码位数，eg:192.168.1.0/24;\n")
                f.write("#ip池对象:ip之间以-相连，eg:192.168.1.1-192.168.1.10;\n")
                f.write("#mac对象:字节直接以:隔开，eg:11:11:11:11:11:11;\n")
                f.write("#ip节点对象:合法的ip地址，eg:192.168.1.1;\n")

                # 表头
                writer.writerow(["#" + headers[0], headers[1], headers[2]])

                count = 0

                for obj in objects:
                    writer.writerow([
                        obj.get("name", ""),
                        obj.get("value", ""),
                        obj.get("comment", "")
                    ])
                    count += 1

            logger.info(f"生成网络对象CSV成功：{file_path} ({count} 条)")
            return count

        except Exception as e:
            logger.error(f"生成网络对象CSV失败: {e}")
            return False