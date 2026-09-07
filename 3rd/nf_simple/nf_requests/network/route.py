"""路由配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class RouteFeature(NFRequests):
    """路由配置操作集合。

    涵盖静态路由、ISP 路由、策略路由、反向路由的增删改查及导入导出。

    .. note::
        所需账号：``webpolicy``（静态路由/ISP 路由/策略路由），``weboper``（反向路由）。
    """

    def create_or_update_isp_route(self, isp_name='china_telecom', enable=True,
        interface=None, gw=None, ad=None, weight=None, link_detect_id=None,
        route_id=None, req_body=None):
        """创建或更新 ISP 路由。

        对应 UI 页面「网络管理 → ISP 路由 → 新建/编辑」。

        各列表参数支持单个值（自动广播到所有路径）或列表（按索引一一对应）。
        ``interface`` 长度决定路径数量。

        :param isp_name:        ISP 名称，如 ``"china_telecom"``。
        :param enable:          是否启用，默认 ``True``。
        :param interface:       出接口名称，str 或 list[str]。默认 ``["G1/1"]``。
        :param gw:              网关地址，str 或 list[str]。默认 ``["0.0.0.0"]``。
        :param ad:              管理距离（AD），int 或 list[int]。默认 ``[1]``。
        :param weight:          权重，int 或 list[int]。默认 ``[1]``。
        :param link_detect_id:  链路探测 ID，int 或 list[int]。默认 ``[-1]``（无）。
        :param route_id:        编辑时必填，路由 ID。传入后 ``action`` 自动切换为 ``"edit"``。
        :param req_body:        自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'action': 'create', 'isp_name': isp_name, 'enable': enable}
        if route_id is not None:
            data['action'] = 'edit'
            data['route_id'] = str(route_id)
        if interface is None:
            interface = ['G1/1']
        elif isinstance(interface, str):
            interface = [interface]
        if_len = len(interface)
        if gw is None:
            gw = ['0.0.0.0'] * if_len
        elif isinstance(gw, str):
            gw = [gw] * if_len
        if ad is None:
            ad = [1] * if_len
        elif isinstance(ad, (int, str)):
            ad = [int(ad)] * if_len
        elif isinstance(ad, list):
            ad = list(map(int, ad))
        if weight is None:
            weight = [1] * if_len
        elif isinstance(weight, (str, int)):
            weight = [int(weight)] * if_len
        elif isinstance(weight, list):
            weight = list(map(int, weight))
        if link_detect_id is None:
            link_detect_id = [-1] * if_len
        elif isinstance(link_detect_id, (str, int)):
            link_detect_id = [int(link_detect_id)] * if_len
        elif isinstance(link_detect_id, list):
            link_detect_id = list(map(int, link_detect_id))
        data['via'] = [{'interface': interface[index], 'gw': gw[index], 'ad':
            ad[index], 'weight': weight[index], 'linkdetectid': link_detect_id[
            index]} for index in range(if_len)]
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/isp_route/action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新ISP路由失败: {e}')
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

    def get_isp_route(self, page=1, size=10, search=''):
        """获取 ISP 路由列表。

        对应 UI 页面「网络管理 → ISP 路由」。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/isp_route/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取ISP路由列表失败: {e}')
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

    def get_isp_route_id(self, page=1, size=10, search=''):
        """根据名称查询 ISP 路由 ID。

        对应 UI 页面「网络管理 → ISP 路由」。

        调用 ``get_isp_route`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: ISP 路由名称关键字，用于匹配。
        :return: 匹配到时返回路由 ID (int)；失败返回 ``False``。
        """
        resp = self.get_isp_route(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_isp_route(self, route_id='all', req_body=None):
        """删除 ISP 路由。

        对应 UI 页面「网络管理 → ISP 路由 → 删除」。

        :param route_id: 路由 ID（单个值）或 ``"all"`` = 删除全部（默认）。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': str(route_id)}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/isp_route/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除ISP路由失败: {e}')
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

    def create_or_update_isp_info(self, name='auto', ip='0.0.0.0/24', info_id=
        None, req_body=None):
        """创建或更新 ISP 信息（IP 网段条目）。

        对应 UI 页面「网络管理 → ISP 路由 → ISP 信息」。

        :param name:     ISP 信息名称，默认 ``"auto"``。
        :param ip:       IP 网段，如 ``"0.0.0.0/24"``。
        :param info_id:  编辑时必填，信息 ID。传入后 ``action`` 自动切换为 ``"edit"``。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'action': 'create', 'name': name, 'ip': ip}
        if info_id is not None:
            data['action'] = 'edit'
            data['id'] = info_id
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/isp_info/action/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新ISP信息失败: {e}')
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

    def get_isp_info(self, page=1, size=10, search=''):
        """获取 ISP 信息列表。

        对应 UI 页面「网络管理 → ISP 路由 → ISP 信息」。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/isp_info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取ISP信息列表失败: {e}')
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

    def get_isp_info_id(self, page=1, size=10, search=''):
        """根据名称查询 ISP 信息 ID。

        对应 UI 页面「网络管理 → ISP 路由 → ISP 信息」。

        调用 ``get_isp_info`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: ISP 信息名称关键字，用于匹配。
        :return: 匹配到时返回信息 ID (int)；失败返回 ``False``。
        """
        resp = self.get_isp_info(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_isp_info(self, info_id='all', req_body=None):
        """删除 ISP 信息。

        对应 UI 页面「网络管理 → ISP 路由 → ISP 信息 → 删除」。

        :param info_id:  信息 ID（单个值）或 ``"all"`` = 删除全部（默认）。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': str(info_id)}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/isp_info/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除ISP信息失败: {e}')
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

    def create_or_update_policy_route(self, action='create', name='policy1',
        enabled=True, source_ip='1.1.1.0/24', dst_ip='2.2.2.0/24', is_app_route
        =False, service=None, application=None, src_interface='G1/1',
        export_type='single', load_balance_mode=None, dst_domain_obj='',
        dst_obj_type='ip', dst_interface=None, link_detection=None, gateway=
        None, preference=None, weight=None, fib_id=None, pbrs_id=None, req_body
        =None):
        """创建或更新策略路由。

        对应 UI 页面「网络管理 → 策略路由 → 新建/编辑」。

        ``export_type`` 取值：
            - ``"single"`` = 单路径（默认），``load_balance_mode`` 自动设为 ``0``
            - ``"multi"`` = 多路径，``load_balance_mode`` 自动设为 ``1``

        ``dst_obj_type`` 取值：
            - ``"ip"`` = IP 地址对象（默认）
            - ``"domain"`` = 域名对象

        各路径参数（``dst_interface``、``gateway`` 等）支持单个值或列表，列表长度决定路径数量。

        :param action:            操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param name:              策略路由名称，默认 ``"policy1"``。
        :param enabled:           是否启用，默认 ``True``。
        :param source_ip:         源 IP 地址，默认 ``"1.1.1.0/24"``。
        :param dst_ip:            目的 IP 地址，默认 ``"2.2.2.0/24"``。
        :param is_app_route:      是否为应用路由，默认 ``False``。
        :param service:           服务对象 ID，str 或 list。默认 ``"any"``。
        :param application:       应用对象 ID，str 或 list。默认 ``"any"``。
        :param src_interface:     源接口名称，str 或 list。默认 ``"G1/1"``。
        :param export_type:       导出类型，默认 ``"single和many"``。
        :param load_balance_mode: 负载均衡模式。``0`` = 主备，``1`` = 负载均衡。根据 ``export_type`` 自动设置。
        :param dst_domain_obj:    目的域名对象，默认 ``"any"``。
        :param dst_obj_type:      目的对象类型，默认 ``"ip"``。
        :param dst_interface:     目的接口名称，str 或 list[str]。默认 ``["G1/2"]``。
        :param link_detection:    链路探测 ID，int 或 list[int]。默认 ``[""]``。
        :param gateway:           网关地址，str 或 list[str]。默认 ``["2.2.2.2"]``。
        :param preference:        优先级，int 或 list[int]。默认 ``[1]``。
        :param weight:            权重，int 或 list[int]。默认 ``[1]``。
        :param fib_id:            FIB 路径 ID，int 或 list[int]。默认 ``[1, 2, ...]``。
        :param pbrs_id:           编辑时必填，策略路由 ID。新建时传 ``None``。
        :param req_body:          自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if dst_domain_obj is None:
            dst_domain_obj = 'any'
        elif isinstance(dst_domain_obj, list):
            dst_domain_obj = ','.join(str(item) for item in dst_domain_obj)
        elif isinstance(dst_domain_obj, (str, int)):
            dst_domain_obj = str(dst_domain_obj)
        if service is None:
            service = 'any'
        elif isinstance(service, list):
            service = ','.join(service)
        if application is None:
            application = 'any'
        elif isinstance(application, list):
            application = ','.join(application)
        if isinstance(src_interface, list):
            src_interface = ','.join(src_interface)
        if export_type == 'single':
            load_balance_mode = (0 if load_balance_mode is None else
                load_balance_mode)
        else:
            load_balance_mode = (1 if load_balance_mode is None else
                load_balance_mode)
        if dst_interface is None:
            dst_interface = ['G1/2']
        elif isinstance(dst_interface, str):
            dst_interface = [dst_interface]
        fib_count = len(dst_interface)
        if link_detection is None:
            link_detection = [''] * fib_count
        elif isinstance(link_detection, int):
            link_detection = [link_detection] * fib_count
        if gateway is None:
            gateway = ['2.2.2.2'] * fib_count
        elif isinstance(gateway, str):
            gateway = [gateway] * fib_count
        if preference is None:
            preference = [1] * fib_count
        elif isinstance(preference, int):
            preference = [preference] * fib_count
        if weight is None:
            weight = [1] * fib_count
        elif isinstance(weight, int):
            weight = [weight] * fib_count
        if fib_id is None:
            fib_id = [x for x in range(1, fib_count + 1)]
        elif isinstance(fib_id, int):
            fib_id = [x for x in range(fib_id, fib_count + fib_id)]
        fib_path = []
        for di, gw_item, p, ld, we, fi in zip(dst_interface, gateway,
            preference, link_detection, weight, fib_id):
            fib_path.append({'dst_interface': di, 'gateway': gw_item,
                'preference': p, 'linkdection': ld, 'weight': we})
        if action == 'create':
            pbrs_id = '' if pbrs_id is None else pbrs_id
        else:
            pbrs_id = 1 if pbrs_id is None else pbrs_id
        data = {'name': name, 'action': action, 'id': pbrs_id, 'source_ip':
            source_ip, 'dst_ip': dst_ip, 'dst_domain_obj': dst_domain_obj,
            'dst_obj_type': dst_obj_type, 'linkdection': '', 'is_app_route':
            is_app_route, 'service': service, 'application': application,
            'fib_path': fib_path, 'src_interface': src_interface, 'enabled':
            enabled, 'export_type': export_type, 'loadbalanceMode':
            load_balance_mode}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/policy/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新策略路由失败: {e}')
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

    def upload_policy_route_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入策略路由。

        对应接口 ``POST /nf/network/route/policy/import/``。

        :param file_path: CSV 文件路径
        :type file_path: str
        :param req_body: 自定义 form-data 参数，传入后与默认参数合并
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 False
        :rtype: dict or bool
        """
        import os
        import json

        if not os.path.exists(file_path):
            logger.error(f'CSV 文件不存在: {file_path}')
            return False

        url = f'{self.base_url}/nf/network/route/policy/import/'
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
            logger.error(f'上传策略路由CSV失败: {e}')
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
    def gen_policy_route_csv(file_path, routes, encoding="utf-8-sig"):
        """生成策略路由 CSV。

        :param file_path: CSV保存路径
        :type file_path: str

        :param routes: 策略路由列表，例如::

            [
                {
                    "name": "route1",
                    "source_ip": "192.168.1.0/24",
                    "dst_ip": "192.168.2.0/24",
                    "dst_domain_obj": "domain1",
                    "dst_obj_type": "ip",
                    "service": "any",
                    "src_interface": "G1/1",
                    "export_type": "many",
                    "dst_interface": "G1/2,G1/3",
                    "gateway": "192.168.2.2,1.1.1.1",
                    "preference": "1,2",
                    "weight": "1,2",
                    "enabled": "yes",
                    "link_detection": "test,test2",
                    "load_balance_mode": 1,
                    "is_app_route": "TRUE",
                    "application": "any"
                }
            ]

        :type routes: list[dict]

        :param encoding: 文件编码
        :type encoding: str

        :return: 成功返回路由数量，失败返回 False
        :rtype: int or bool
        """
        import csv

        headers = [
            "名称",
            "源ip",
            "目的网段",
            "目的域名对象",
            "目的对象类型",
            "服务",
            "源接口",
            "目的接口类型(single:单接口 many：多接口)",
            "目的接口",
            "网关",
            "管理距离",
            "权值",
            "启用(yes/no)",
            "链路探测名称(逗号分隔,最多32个)",
            "负载方式：单接口默认为0",
            "是否基于应用",
            "应用",
        ]

        try:
            with open(file_path, "w", encoding=encoding, newline="") as f:

                writer = csv.writer(f)

                # 注释
                f.write("#以#开始的行表示注释. 策略名称不能以#开始，否则导入时会忽略这条策略\n")
                f.write("#部分版本office、wps无法自动识别csv文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件\n")
                f.write("#启用默认为yes\n")
                f.write("#源IP与目的网段以ip+掩码位数的方式表示，例如192.168.1.0/24或2001:abcd:123:1::/64.\n")
                f.write("#源接口与目的接口都不能选择any.\n")
                f.write("#管理距离的取值范围为1-255.多接口中的权重模式下，权值范围为1-255，其余模式的权值均为1.\n")
                f.write("#目的接口类型有单接口和多接口，多接口时：至少选择两个接口，且接口、网关、管理距离、权值有多个时需要其数量一致，且位置一一对应\n")
                f.write("#多接口中的负载方式取值可为1、2、3、4，分别对应源&目的IP模式、逐包模式、用户模式和权重模式，0对应单接口模式\n")
                f.write("#当基于应用为TRUE时，服务需要选择any；当基于应用为FALSE时，应用需要选择any\n")
                f.write('"#当目的接口类型为多接口类型时（many）:|表示不配置链路探测，例如：|,link1,|,link2"\n')
                f.write("#目的对象类型为ip|domain_object，类型为domain_object则目的域名对象是域名组，类型为ip则目的网段是ip网段\n")
                f.write('#名称,源ip,目的网段,目的域名对象,目的对象类型,服务,源接口,目的接口类型(single:单接口 many：多接口),目的接口,网关,管理距离,权值,启用(yes/no),"链路探测名称(逗号分隔,最多32个)",负载方式：单接口默认为0,是否基于应用,应用\n')
                f.write('#示例1：route1,192.168.1.0/24,192.168.2.0/24,domain1,ip,any,G1/1,many,"G1/2,G1/3","192.168.2.2,1.1.1.1","1,2","1,2",yes,"test,test2",1,TRUE,any\n')

                # 表头
                writer.writerow(["#" + headers[0], headers[1], headers[2],
                                 headers[3], headers[4], headers[5], headers[6],
                                 headers[7], headers[8], headers[9], headers[10],
                                 headers[11], headers[12], headers[13],
                                 headers[14], headers[15], headers[16]])

                count = 0

                for r in routes:
                    enabled = r.get("enabled", "yes")
                    if isinstance(enabled, bool):
                        enabled = "yes" if enabled else "no"

                    is_app = r.get("is_app_route", "FALSE")
                    if isinstance(is_app, bool):
                        is_app = "TRUE" if is_app else "FALSE"

                    # 列表型字段：逗号拼接
                    def _join(v):
                        if isinstance(v, list):
                            return ",".join(str(x) for x in v)
                        return "" if v is None else str(v)

                    writer.writerow([
                        r.get("name", ""),
                        r.get("source_ip", ""),
                        r.get("dst_ip", ""),
                        r.get("dst_domain_obj", ""),
                        r.get("dst_obj_type", "ip"),
                        r.get("service", "any"),
                        _join(r.get("src_interface", "")),
                        r.get("export_type", "single"),
                        _join(r.get("dst_interface", "")),
                        _join(r.get("gateway", "")),
                        _join(r.get("preference", 1)),
                        _join(r.get("weight", 1)),
                        enabled,
                        _join(r.get("link_detection", "")),
                        r.get("load_balance_mode", 0),
                        is_app,
                        r.get("application", "any"),
                    ])
                    count += 1

            logger.info(f"生成策略路由CSV成功：{file_path} ({count} 条)")
            return count

        except Exception as e:
            logger.error(f"生成策略路由CSV失败: {e}")
            return False

    def get_policy_route(self, page=1, size=10, search=''):
        """获取策略路由列表。

        对应 UI 页面「网络管理 → 策略路由」。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/policy/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取策略路由列表失败: {e}')
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

    def get_policy_route_id(self, page=1, size=10, search=''):
        """根据名称查询策略路由 ID。

        对应 UI 页面「网络管理 → 策略路由」。

        调用 ``get_policy_route`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 策略路由名称关键字，用于匹配。
        :return: 匹配到时返回策略路由 ID (int)；失败返回 ``False``。
        """
        resp = self.get_policy_route(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def enable_policy_route(self, pbrs_id=1, enabled=True, req_body=None):
        """启用或禁用策略路由。

        对应 UI 页面「网络管理 → 策略路由 → 启用/禁用」。

        :param pbrs_id:  策略路由 ID，默认 ``1``。
        :param enabled:  是否启用。``True`` = 启用（默认），``False`` = 禁用。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': pbrs_id, 'enabled': enabled}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/policy/status/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'启用或禁用策略路由失败: {e}')
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

    def remove_policy_route(self, pbrs_id, req_body=None):
        """删除策略路由。

        对应 UI 页面「网络管理 → 策略路由 → 删除」。

        :param pbrs_id:  策略路由 ID，支持 int、str 或 list（如 ``[1, 2]``）。多个时以逗号拼接。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(pbrs_id, (int, str)):
            pbrs_id = [str(pbrs_id)]
        elif isinstance(pbrs_id, list):
            pbrs_id = [str(x) for x in pbrs_id]
        data = {'id': ','.join(pbrs_id)}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/policy/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除策略路由失败: {e}')
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

    def export_policy_route(self):
        """导出策略路由为 CSV/文本格式。

        对应 UI 页面「网络管理 → 策略路由 → 导出」。

        :return: 成功返回 CSV/文本字符串内容；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/policy/export/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出策略路由失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出策略路由成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def update_reverse_route(self, ipv4_enable=False, in_band_enable=False,
        req_body=None):
        """更新反向路由配置。

        对应 UI 页面「网络管理 → 路由 → 反向路由」。

        所需账号：``weboper``。

        :param ipv4_enable:    是否启用 IPv4 反向路由，默认 ``False``。
        :param in_band_enable: 是否启用带内反向路由，默认 ``False``。
        :param req_body:       自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'ipv4_enable': ipv4_enable, 'inband_enable': in_band_enable}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/reverse/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新反向路由配置失败: {e}')
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

    def get_reverse_route(self):
        """获取反向路由配置。

        对应 UI 页面「网络管理 → 路由 → 反向路由」。

        所需账号：``weboper``。

        :return: 成功返回完整响应 dict，``result`` 包含 ``ipv4_enable`` 和 ``inband_enable``；
                 失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/reverse/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取反向路由配置失败: {e}')
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

    def create_static_route(self, name='route_name', interface='G1/1', dst_net=
        '172.30.2.0/24', gateway='172.30.1.2', metric=1, weight=1, enabled=True,
        link_detection='', sta_route_id=None, req_body=None):
        """创建静态路由。

        对应 UI 页面「网络管理 → 静态路由 → 新建」。

        .. note::
            传入 ``sta_route_id`` 时，会同时写入 ``id`` 和 ``backend_id`` 字段（编辑场景）。

        :param name:           路由名称，默认 ``"route_name"``。
        :param interface:      出接口名称，如 ``"G1/1"``。
        :param dst_net:        目的网段，如 ``"172.30.2.0/24"``。
        :param gateway:        网关地址，如 ``"172.30.1.2"``。
        :param metric:         度量值，默认 ``1``。
        :param weight:         权重，默认 ``1``。
        :param enabled:        是否启用，默认 ``True``。
        :param link_detection: 链路探测名称，默认 ``""``。
        :param sta_route_id:   静态路由 ID。传入则附加 ``id`` / ``backend_id``。
        :param req_body:       自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'name': name, 'dstNet': dst_net, 'gateway': gateway, 'metric':
            metric, 'weight': weight, 'interface': interface, 'enabled':
            enabled, 'linkdection': link_detection}
        if sta_route_id is not None:
            data.update({'id': sta_route_id, 'backend_id': sta_route_id})
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/static/create/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建静态路由失败: {e}')
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

    def upload_static_route_csv(self, file_path, req_body=None):
        """通过上传 CSV 文件批量导入静态路由。

        对应接口 ``POST /nf/network/route/static/import/``。

        :param file_path: CSV 文件路径
        :type file_path: str
        :param req_body: 自定义 form-data 参数，传入后与默认参数合并
        :type req_body: dict or None
        :return: 成功返回响应 dict，失败返回 False
        :rtype: dict or bool
        """
        import os
        import json

        if not os.path.exists(file_path):
            logger.error(f'CSV 文件不存在: {file_path}')
            return False

        url = f'{self.base_url}/nf/network/route/static/import/'
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
            logger.error(f'上传静态路由CSV失败: {e}')
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
    def gen_static_route_csv(file_path, routes, encoding="utf-8-sig"):
        """生成静态路由 CSV。

        :param file_path: CSV保存路径
        :type file_path: str

        :param routes: 静态路由列表，例如::

            [
                {
                    "name": "route1",
                    "dst_net": "192.168.1.0/24",
                    "gateway": "192.168.2.2",
                    "interface": "G1/1",
                    "priority": 1,
                    "weight": 1,
                    "link_detection": "link1",
                    "enabled": "yes"
                }
            ]

        :type routes: list[dict]

        :param encoding: 文件编码
        :type encoding: str

        :return: 成功返回路由数量，失败返回 False
        :rtype: int or bool
        """
        import csv

        headers = [
            "名称",
            "目的网段",
            "网关",
            "接口",
            "优先级",
            "权值",
            "链路探测",
            "启用(yes/no)",
        ]

        try:
            with open(file_path, "w", encoding=encoding, newline="") as f:

                writer = csv.writer(f)

                # 注释
                f.write("#以#开始的行表示注释.策略名称不能以#开始，否则导入时会忽略这条策略\n")
                f.write("#部分版本office、wps无法自动识别csv文件，存在保存时出现格式乱码问题；解决方法-编辑完成后选择另存为csv文件\n")
                f.write("#启用默认为yes\n")
                f.write("#目的网段以ip+掩码位数的方式表示，例如192.168.1.0/24，如果自动需要出接口，则接口填any，也可以指定具体接口.\n")
                f.write("#优先级的取值范围为1-255，度量值的取值范围为1-65535.\n")
                f.write("#名称,目的网段,网关,接口,优先级,权值,链路探测,启用(yes/no)\n")
                f.write("#示例1：route1,192.168.1.0/24,192.168.2.2,G1/1,1,1,link1,yes\n")

                # 表头
                writer.writerow(["#" + headers[0], headers[1], headers[2],
                                 headers[3], headers[4], headers[5], headers[6],
                                 headers[7]])

                count = 0

                for r in routes:
                    enabled = r.get("enabled", "yes")
                    if isinstance(enabled, bool):
                        enabled = "yes" if enabled else "no"

                    writer.writerow([
                        r.get("name", ""),
                        r.get("dst_net", ""),
                        r.get("gateway", ""),
                        r.get("interface", ""),
                        r.get("priority", 1),
                        r.get("weight", 1),
                        r.get("link_detection", ""),
                        enabled
                    ])
                    count += 1

            logger.info(f"生成静态路由CSV成功：{file_path} ({count} 条)")
            return count

        except Exception as e:
            logger.error(f"生成静态路由CSV失败: {e}")
            return False

    def update_static_route(self, name='route_name', interface='G1/1', dst_net=
        '172.30.2.0/24', gateway='172.30.1.2', metric=1, weight=1, enabled=True,
        link_detection='', sta_route_id=None, req_body=None):
        """更新静态路由。

        对应 UI 页面「网络管理 → 静态路由 → 编辑」。

        与 ``create_static_route`` 参数相同，但调用编辑端点。需要传入 ``sta_route_id``。

        :param name:           路由名称。
        :param interface:      出接口名称。
        :param dst_net:        目的网段。
        :param gateway:        网关地址。
        :param metric:         度量值，默认 ``1``。
        :param weight:         权重，默认 ``1``。
        :param enabled:        是否启用，默认 ``True``。
        :param link_detection: 链路探测名称，默认 ``""``。
        :param sta_route_id:   编辑时必填，路由 ID（同时作为 ``backend_id``）。
        :param req_body:       自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'name': name, 'dstNet': dst_net, 'gateway': gateway, 'metric':
            metric, 'weight': weight, 'interface': interface, 'enabled':
            enabled, 'linkdection': link_detection}
        if sta_route_id is not None:
            data.update({'id': sta_route_id, 'backend_id': sta_route_id})
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/static/edit/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新静态路由失败: {e}')
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

    def get_static_route(self, page=1, size=10, search=''):
        """获取静态路由列表。

        对应 UI 页面「网络管理 → 静态路由」。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/static/info/'
        params = {'page': page, 'size': size, 'search': search}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取静态路由列表失败: {e}')
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

    def get_static_route_id(self, page=1, size=10, search=''):
        """根据名称查询静态路由 ID。

        对应 UI 页面「网络管理 → 静态路由」。

        调用 ``get_static_route`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``10``。
        :param search: 静态路由名称关键字，用于匹配。
        :return: 匹配到时返回路由 ID (int)；失败返回 ``False``。
        """
        resp = self.get_static_route(page=page, size=size, search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_static_route(self, sta_route_id, req_body=None):
        """删除静态路由。

        对应 UI 页面「网络管理 → 静态路由 → 删除」。

        :param sta_route_id: 路由 ID，支持 int、str 或 list/tuple（如 ``[1, 2]``）。多个时以逗号拼接。
        :param req_body:     自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(sta_route_id, (list, tuple)):
            sta_route_ids = ','.join(map(str, sta_route_id))
        else:
            sta_route_ids = str(sta_route_id)
        data = {'id': sta_route_ids}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/route/static/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除静态路由失败: {e}')
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

    def clear_static_route(self):
        """清空全部静态路由。

        对应 UI 页面「网络管理 → 静态路由 → 清空」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/static/clear/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'清空静态路由失败: {e}')
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

    def export_static_route(self):
        """导出静态路由为 CSV/文本格式。

        对应 UI 页面「网络管理 → 静态路由 → 导出」。

        :return: 成功返回 CSV/文本字符串内容；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/route/static/export/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'导出静态路由失败: {e}')
            return False
        if result.status_code == 200:
            logger.info('导出静态路由成功')
            return result.text
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False
