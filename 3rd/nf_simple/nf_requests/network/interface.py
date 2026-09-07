"""接口配置。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests



class InterfaceFeature(NFRequests):
    """接口配置操作集合。"""

    def create_l3_physical_interface(self, name='G1/1', zone='TRUST', manage="default",
        ipv4='1.2.3.4/24', sub_ipv4='', status='up', ipv6='', ipv6_method=
        'manual', mac='', ipv4_mtu=1500, tcp_mss=None, ipv6_mtu=1500, linkspeed
        ='auto', linkmode='auto', multicast='', label='', ip4_method='static',
        userName='', passWord='', isGenerateRoute='true', HandShakeInterval=20,
        Reconnects=5, onlineMethod='true', ipGetMethod='true', reverse_route=[{
        'protocol': 'IPv4', 'next_hop': '', 'status': '0'}]):
        """编辑三层物理接口。

        对应 UI 页面「网络管理 → 接口 → 编辑（三层物理接口）」。

        接口 ID 和 MAC 地址通过 ``search_interface_id_by_name`` / ``search_interface_mac_addr_by_name``
        自动查询，无需手动传入。可管理属性 ID 通过 ``get_mgt_attr_id`` 自动查询。

        :param name:         接口名称，如 ``"G1/1"``，默认 ``"G1/1"``。
        :param zone:         安全区名称，默认 ``"TRUST"``。
        :param manage:       可管理属性名称，默认 ``"default"``，自动转换为 ID。
        :param ipv4:         IPv4 地址，如 ``"1.2.3.4/24"``。
        :param sub_ipv4:     辅助 IPv4 地址，默认 ``""``。
        :param status:       接口状态。``"up"`` = 启用，``"down"`` = 禁用。
        :param ipv6:         IPv6 地址，默认 ``""``。
        :param ipv6_method:  IPv6 获取方式。``"manual"`` = 手动，``"auto"`` = 自动。
        :param mac:          MAC 地址，留空则自动查询。
        :param ipv4_mtu:     IPv4 MTU，默认 ``1500``。
        :param tcp_mss:      TCP MSS，默认 ``None``。
        :param ipv6_mtu:     IPv6 MTU，默认 ``1500``。
        :param linkspeed:    链路速率，默认 ``"auto"``。
        :param linkmode:     链路模式，默认 ``"auto"``。
        :param multicast:    多播配置，默认 ``""``。
        :param label:        标签，默认 ``""``。
        :param ip4_method:   IPv4 获取方式。``"static"`` = 静态，``"pppoe"`` = PPPoE。
        :param userName:     PPPoE 用户名，默认 ``""``。
        :param passWord:     PPPoE 密码，默认 ``""``。
        :param isGenerateRoute: 是否生成路由。``"true"`` = 是，``"false"`` = 否。
        :param HandShakeInterval: PPPoE 握手间隔（秒），默认 ``20``。
        :param Reconnects:   PPPoE 重连次数，默认 ``5``。
        :param onlineMethod: PPPoE 在线方式。``"true"`` = 永远在线，``"false"`` = 按需连接。
        :param ipGetMethod:  PPPoE IP 获取方式。``"true"`` = 自动获取，``"false"`` = 手动。
        :param reverse_route: 反向路由配置列表，默认为 IPv4 单条记录。
        :return: 成功时返回 ``None``（日志输出创建成功），失败时返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/interfacedetail/edit/'
        id = self.search_interface_id_by_name(name)
        if mac == '':
            mac = self.search_interface_mac_addr_by_name(name)
        manage = self.get_mgt_attr_id(name=manage)
        data = {'id': id, 'type': 'L3_INTERFACE', 'name': name, 'zone': zone,
            'attribute': 'physical', 'manage': manage, 'ipv4': ipv4, 'sub_ipv4':
            sub_ipv4, 'status': status, 'ipv6': ipv6, 'ipv6_method':
            ipv6_method, 'router_message': 0, 'mac': mac, 'ipv4_mtu': ipv4_mtu,
            'tcp_mss': tcp_mss, 'ipv6_mtu': ipv6_mtu, 'linkspeed': linkspeed,
            'linkmode': linkmode, 'multicast': multicast, 'label': label,
            'ip4_method': ip4_method, 'userName': userName, 'passWord':
            passWord, 'isGenerateRoute': isGenerateRoute, 'HandShakeInterval':
            HandShakeInterval, 'Reconnects': Reconnects, 'onlineMethod':
            onlineMethod, 'ipGetMethod': ipGetMethod, 'reverse_route':
            reverse_route}
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
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
                logger.info(f'创建接口 {name} {message}')
        else:
            logger.error("创建接口失败")

    def create_l3_pppoe_interface(self, name='G1/1', zone='TRUST', manage=1,
        ipv4='', sub_ipv4='', status='up', ipv6='', ipv6_method='manual', mac=
        '', ipv4_mtu=1500, tcp_mss=None, ipv6_mtu=1500, linkspeed='auto',
        linkmode='auto', multicast='', label='', ip4_method='pppoe', userName=
        'test', passWord='qwert12345', isGenerateRoute='true',
        HandShakeInterval=20, Reconnects=5, onlineMethod='true', ipGetMethod=
        'true', reverse_route=[{'protocol': 'IPv4', 'next_hop': '', 'status': '0'}]
        ):
        """编辑三层 PPPoE 接口。

        对应 UI 页面「网络管理 → 接口 → 编辑（PPPoE 模式）」。

        与 ``create_l3_physical_interface`` 共用同一编辑端点，但 ``ip4_method`` 固定为 ``"pppoe"``，
        且用户名和密码会经过加密处理。接口 ID 和 MAC 地址自动查询。

        :param name:         接口名称，如 ``"G1/1"``，默认 ``"G1/1"``。
        :param zone:         安全区名称，默认 ``"TRUST"``。
        :param manage:       可管理属性 ID，默认 ``1``。
        :param ipv4:         IPv4 地址，PPPoE 模式下通常留空。
        :param sub_ipv4:     辅助 IPv4 地址，默认 ``""``。
        :param status:       接口状态。``"up"`` = 启用，``"down"`` = 禁用。
        :param ipv6:         IPv6 地址，默认 ``""``。
        :param ipv6_method:  IPv6 获取方式。``"manual"`` = 手动，``"auto"`` = 自动。
        :param mac:          MAC 地址，留空则自动查询。
        :param ipv4_mtu:     IPv4 MTU，默认 ``1500``。
        :param tcp_mss:      TCP MSS，默认 ``None``。
        :param ipv6_mtu:     IPv6 MTU，默认 ``1500``。
        :param linkspeed:    链路速率，默认 ``"auto"``。
        :param linkmode:     链路模式，默认 ``"auto"``。
        :param multicast:    多播配置，默认 ``""``。
        :param label:        标签，默认 ``""``。
        :param ip4_method:   IPv4 获取方式，PPPoE 模式下固定 ``"pppoe"``。
        :param userName:     PPPoE 用户名，默认 ``"test"``，会加密传输。
        :param passWord:     PPPoE 密码，默认 ``"qwert12345"``，会加密传输。
        :param isGenerateRoute: 是否生成路由。``"true"`` = 是，``"false"`` = 否。
        :param HandShakeInterval: PPPoE 握手间隔（秒），默认 ``20``。
        :param Reconnects:   PPPoE 重连次数，默认 ``5``。
        :param onlineMethod: PPPoE 在线方式。``"true"`` = 永远在线，``"false"`` = 按需连接。
        :param ipGetMethod:  PPPoE IP 获取方式。``"true"`` = 自动获取，``"false"`` = 手动。
        :param reverse_route: 反向路由配置列表，默认为 IPv4 单条记录。
        :return: 成功时返回 ``None``（日志输出创建成功），失败时返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/interfacedetail/edit/'
        id = self.search_interface_id_by_name(name)
        if mac == '':
            mac = self.search_interface_mac_addr_by_name(name)
        data = {'id': id, 'type': 'L3_INTERFACE', 'name': name, 'zone': zone,
            'attribute': 'physical', 'manage': manage, 'ipv4': ipv4, 'sub_ipv4':
            sub_ipv4, 'status': status, 'ipv6': ipv6, 'ipv6_method':
            ipv6_method, 'router_message': 0, 'mac': mac, 'ipv4_mtu': ipv4_mtu,
            'tcp_mss': tcp_mss, 'ipv6_mtu': ipv6_mtu, 'linkspeed': linkspeed,
            'linkmode': linkmode, 'multicast': multicast, 'label': label,
            'ip4_method': ip4_method, 'userName': encrypt_msg(userName),
            'passWord': encrypt_msg(passWord), 'isGenerateRoute':
            isGenerateRoute, 'HandShakeInterval': HandShakeInterval,
            'Reconnects': Reconnects, 'onlineMethod': onlineMethod,
            'ipGetMethod': ipGetMethod, 'reverse_route': reverse_route}
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
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
                logger.info(f'创建接口 {name} {message}')
        else:
            logger.error(result)

    def search_interface_mac_addr_by_name(self, interface_name):
        """根据接口名称查询 MAC 地址。

        对应 UI 页面「网络管理 → 接口」。

        通过 ``search_interface_list`` 模糊搜索后，只返回精确匹配 ``name`` 的接口 MAC 地址。

        :param interface_name: 接口名称，如 ``"G1/1"``。
        :return: 精确匹配时返回 MAC 地址字符串；无匹配时返回 ``False``。
        """
        result = self.search_interface_list(search=interface_name)
        if not result:
            return False
        result_data = result.get('result', {})
        if result_data.get('total') == 1:
            mac = result_data.get('list', {}).get('physical', [{}])[0].get('mac')
            logger.info(f'获取接口：{interface_name} 的mac地址 {mac}')
            return mac
        else:
            info = result_data.get('list', {}).get('physical', [])
            for i in info:
                if i['name'] == interface_name:
                    logger.info(f"获取接口：{interface_name} 的mac地址 {i['mac']}")
                    return i['mac']
            logger.info(f'获取接口：{interface_name} 失败')
            return False

    def search_interface_list(self, search='', size=10, page=1, type=''):
        """搜索接口列表。

        对应 UI 页面「网络管理 → 接口」。

        ``type`` 取值：
            - ``"L3_INTERFACE"`` = 三层接口
            - ``"L2_INTERFACE"`` = 二层接口
            - ``"NO_ALLOCATION_INTERFACE"`` = 未配置接口
            - ``"IPSEC_INTERFACE"`` = IPSec 逻辑接口

        :param search: 搜索关键字，默认 ``""``。
        :param size:   每页数量，默认 ``10``。
        :param page:   页码，默认 ``1``。
        :param type:   接口类型过滤，默认 ``""``（全部）。
        :return: 成功返回完整响应 dict，结构为 ``{"status": 2000, "result": {"total": ..., "list": {"physical": [...], "logic": [...]}}, ...}``；
                 失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/interface/'
        params = {'size': size, 'page': page, 'search': search, 'type': type}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(e)
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status = resp_data.get('status')
            message = resp_data.get('message')
            if status != 2000:
                logger.error(message)
                return False
            logger.info(message)
            return json.loads(result.text)
        logger.error(result)
        return False

    def search_interface_id_by_name(self, interface_name):
        """根据接口名称查询接口 ID。

        对应 UI 页面「网络管理 → 接口」。

        通过 ``search_interface_list`` 模糊搜索后，只返回精确匹配 ``name`` 的接口 ID。
        通常作为 ``create_l3_physical_interface`` 等编辑操作的前置查询步骤。

        :param interface_name: 接口名称，如 ``"G1/1"``。
        :return: 精确匹配时返回接口 ID (int)；无匹配时返回 ``False``。
        """
        result = self.search_interface_list(search=interface_name)
        if not result:
            return False
        result_data = result.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        physical_list = result_data.get('list', {}).get('physical', [])
        if len(physical_list) == 0:
            return False
        if result_data.get('total') == 1:
            id_ = physical_list[0]['id']
            logger.info(f'获取接口：{interface_name} 的ID值 {id_}')
            return id_
        for i in physical_list:
            if i.get('name') == interface_name:
                logger.info(f"获取接口：{interface_name} 的ID值 {i['id']}")
                return i['id']
        logger.info(f'获取接口：{interface_name} 失败')
        return False

    def update_interface(self, if_type='L3_INTERFACE', id=None, name='',
        zone='TRUST', attribute='physical', manage=1, ipv4='', sub_ipv4='',
        status='down', ipv6='', ipv6_method='manual', router_message=0,
        mac='', ipv4_mtu=1500, tcp_mss=None, ipv6_mtu=1500,
        linkspeed='auto', linkmode='auto', multicast='', label='',
        ip4_method='static', userName='', passWord='',
        isGenerateRoute='true', HandShakeInterval=20, Reconnects=5,
        onlineMethod='true', ipGetMethod='true',
        reverse_route=None, vlan_id=None, stp=None, models='access',
        support_vlan_id='', aggre_model='BOND_API_MODE_ROUND_ROBIN',
        dispense_policy='', bond_interfaces=None,
        l3_interface=None, l2_interface=None,
        inter_connection=None, useCustomMac=True, req_body=None):
        """更新接口（通用编辑，支持六种接口类型）。

        对应 UI 页面「网络管理 → 接口 → 编辑」。

        对应 API 文档中的 ``update_interface``。

        通过 **if_type** 选择接口类型：
        - ``"NO_ALLOCATION_INTERFACE"`` — 取消接口分配（仅需 id + type）
        - ``"L3_INTERFACE"`` — 三层接口（物理/静态IP/PPPoE）
        - ``"L2_INTERFACE"`` — 二层接口（access/trunk/PVID + VLAN）
        - ``"BOND_L3_INTERFACE"`` — 聚合三层接口（Bond 聚合 + L3 层配置）
        - ``"BOND_L2_INTERFACE"`` — 聚合二层接口（Bond 聚合 + L2 层配置）
        - ``"BOND_INTER_CONNECTION_INTERFACE"`` — 聚合接口互联

        L3_INTERFACE 参数（共 28 个字段）：
        :param if_type: 接口类型，``"NO_ALLOCATION_INTERFACE"`` / ``"L3_INTERFACE"`` /
            ``"L2_INTERFACE"``
        :type if_type: str
        :param id: 接口 ID，默认 ``None``（为 ``None`` 时通过 name 自动查询）
        :type id: int or None
        :param name: 接口名称，如 ``"G1/8"``，默认 ``""``
        :type name: str
        :param zone: 安全区名称，默认 ``"TRUST"``
        :type zone: str
        :param attribute: 接口属性，默认 ``"physical"``
        :type attribute: str
        :param manage: 可管理属性 ID，默认 ``1``
        :type manage: int
        :param ipv4: IPv4 地址，如 ``"1.1.1.1/24"``
        :type ipv4: str
        :param sub_ipv4: 辅助 IPv4 地址
        :type sub_ipv4: str
        :param status: 接口状态，``"up"`` / ``"down"``
        :type status: str
        :param ipv6: IPv6 地址，如 ``"666::1/64"``
        :type ipv6: str
        :param ipv6_method: IPv6 获取方式，``"manual"`` / ``"auto"``
        :type ipv6_method: str
        :param router_message: 路由通告，默认 ``0``
        :type router_message: int
        :param mac: MAC 地址，留空自动查询
        :type mac: str
        :param ipv4_mtu: IPv4 MTU，默认 ``1500``
        :type ipv4_mtu: int
        :param tcp_mss: TCP MSS，默认 ``None``
        :type tcp_mss: int or None
        :param ipv6_mtu: IPv6 MTU，默认 ``1500``
        :type ipv6_mtu: int
        :param linkspeed: 链路速率，默认 ``"auto"``
        :type linkspeed: str
        :param linkmode: 链路模式，默认 ``"auto"``
        :type linkmode: str
        :param multicast: 多播配置，默认 ``""``
        :type multicast: str
        :param label: 标签
        :type label: str
        :param ip4_method: IPv4 方式，``"static"`` / ``"pppoe"``
        :type ip4_method: str
        :param userName: PPPoE 用户名（ip4_method="pppoe" 时生效，自动加密）
        :type userName: str
        :param passWord: PPPoE 密码（ip4_method="pppoe" 时生效，自动加密）
        :type passWord: str
        :param isGenerateRoute: 是否生成路由，``"true"`` / ``"false"``
        :type isGenerateRoute: str
        :param HandShakeInterval: PPPoE 握手间隔（秒），默认 ``20``
        :type HandShakeInterval: int
        :param Reconnects: PPPoE 重连次数，默认 ``5``
        :type Reconnects: int
        :param onlineMethod: PPPoE 在线方式，``"true"``=永远在线
        :type onlineMethod: str
        :param ipGetMethod: PPPoE IP 获取方式，``"true"``=自动获取
        :type ipGetMethod: str
        :param reverse_route: 反向路由列表，默认 ``None``（转为默认 IPv4 单条）
        :type reverse_route: list or None

        L2_INTERFACE 额外参数：
        :param vlan_id: VLAN ID，默认 ``None``（不传入）
        :type vlan_id: int or None
        :param stp: STP 配置，默认 ``None``
        :type stp: any or None
        :param models: 二层模式，``"access"`` / ``"trunk"``
        :type models: str
        :param support_vlan_id: 支持 VLAN ID 列表（trunk 模式），如 ``"1,2,3"``
        :type support_vlan_id: str

        BOND_L3_INTERFACE / BOND_L2_INTERFACE / BOND_INTER_CONNECTION_INTERFACE 共享参数：
        :param aggre_model: 聚合模式，默认 ``"BOND_API_MODE_ROUND_ROBIN"``
        :type aggre_model: str
        :param dispense_policy: 分发策略，默认 ``""``
        :type dispense_policy: str
        :param bond_interfaces: 子接口列表，每项为 ``{"sub_interface": "T2/1", "work_model": "initiative", "level": 1, "id": 0}``
        :type bond_interfaces: list or None
        :param useCustomMac: 是否使用自定义 MAC，默认 ``True``
        :type useCustomMac: bool

        BOND_L3_INTERFACE 额外参数（通过 l3_interface 嵌套）：
        :param l3_interface: L3 层配置 dict，若不传则自动由其他参数构造
        :type l3_interface: dict or None

        BOND_L2_INTERFACE 额外参数（通过 l2_interface 嵌套）：
        :param l2_interface: L2 层配置 dict，若不传则自动由其他参数构造
        :type l2_interface: dict or None

        BOND_INTER_CONNECTION_INTERFACE 额外参数（通过 inter_connection 嵌套）：
        :param inter_connection: 互联配置 dict，若不传则自动由其他参数构造
        :type inter_connection: dict or None

        通用参数：
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            if id is None and name != '':
                id = self.search_interface_id_by_name(name)
            if if_type == 'NO_ALLOCATION_INTERFACE':
                data = {
                    'id': id,
                    'type': if_type,
                }
            elif if_type == 'L2_INTERFACE':
                l2_data = {
                    'id': id,
                    'type': if_type,
                    'label': label,
                    'name': name,
                    'zone': zone,
                    'attribute': attribute,
                    'stp': stp,
                    'models': models,
                    'status': status,
                    'ipv4_mtu': ipv4_mtu,
                    'linkspeed': linkspeed,
                    'linkmode': linkmode,
                    'support_vlan_id': support_vlan_id,
                }
                if vlan_id is not None:
                    l2_data['vlan_id'] = vlan_id
                data = l2_data
            elif if_type == 'L3_INTERFACE':
                if mac == '' and name != '':
                    mac = self.search_interface_mac_addr_by_name(name)
                rr = reverse_route if reverse_route is not None else [
                    {'protocol': 'IPv4', 'next_hop': '', 'status': '0'}]
                data = {
                    'id': id,
                    'type': if_type,
                    'name': name,
                    'zone': zone,
                    'attribute': attribute,
                    'manage': manage,
                    'ipv4': ipv4,
                    'sub_ipv4': sub_ipv4,
                    'status': status,
                    'ipv6': ipv6,
                    'ipv6_method': ipv6_method,
                    'router_message': router_message,
                    'mac': mac,
                    'ipv4_mtu': ipv4_mtu,
                    'tcp_mss': tcp_mss,
                    'ipv6_mtu': ipv6_mtu,
                    'linkspeed': linkspeed,
                    'linkmode': linkmode,
                    'multicast': multicast,
                    'label': label,
                    'ip4_method': ip4_method,
                    'isGenerateRoute': isGenerateRoute,
                    'HandShakeInterval': HandShakeInterval,
                    'Reconnects': Reconnects,
                    'onlineMethod': onlineMethod,
                    'ipGetMethod': ipGetMethod,
                    'reverse_route': rr,
                }
                if ip4_method == 'pppoe':
                    data['userName'] = encrypt_msg(userName)
                    data['passWord'] = encrypt_msg(passWord)
                else:
                    data['userName'] = userName
                    data['passWord'] = passWord
            elif if_type == 'BOND_L3_INTERFACE':
                bi = bond_interfaces if bond_interfaces is not None else []
                li = l3_interface if l3_interface is not None else {
                    'useCustomMac': useCustomMac,
                    'zone': zone,
                    'mac': mac,
                    'manage': manage,
                    'ipv4': ipv4,
                    'sub_ipv4': sub_ipv4,
                    'status': status,
                    'ipv6': ipv6,
                    'ipv6_method': ipv6_method,
                    'router_message': router_message,
                    'ipv4_mtu': ipv4_mtu,
                    'tcp_mss': tcp_mss,
                    'ipv6_mtu': ipv6_mtu,
                    'linkspeed': linkspeed,
                    'linkmode': linkmode,
                    'multicast': multicast,
                    'reverse_route': reverse_route,
                }
                data = {
                    'type': if_type,
                    'id': id,
                    'name': name,
                    'aggre_model': aggre_model,
                    'dispense_policy': dispense_policy,
                    'interface': bi,
                    'label': label,
                    'l3_interface': li,
                    'useCustomMac': useCustomMac,
                }
            elif if_type == 'BOND_L2_INTERFACE':
                bi = bond_interfaces if bond_interfaces is not None else []
                li = l2_interface if l2_interface is not None else {
                    'vlan_id': vlan_id,
                    'mac': mac,
                    'zone': zone,
                    'stp': stp,
                    'models': models,
                    'status': status,
                    'ipv4_mtu': ipv4_mtu,
                    'linkspeed': linkspeed,
                    'linkmode': linkmode,
                    'support_vlan_id': support_vlan_id,
                }
                data = {
                    'type': if_type,
                    'id': id,
                    'name': name,
                    'aggre_model': aggre_model,
                    'dispense_policy': dispense_policy,
                    'interface': bi,
                    'label': label,
                    'l2_interface': li,
                }
            elif if_type == 'BOND_INTER_CONNECTION_INTERFACE':
                bi = bond_interfaces if bond_interfaces is not None else []
                ic = inter_connection if inter_connection is not None else {
                    'status': status,
                    'ipv4_mtu': ipv4_mtu,
                    'linkspeed': linkspeed,
                    'linkmode': linkmode,
                }
                data = {
                    'type': if_type,
                    'id': id,
                    'name': name,
                    'aggre_model': aggre_model,
                    'dispense_policy': dispense_policy,
                    'interface': bi,
                    'label': label,
                    'inter_connection': ic,
                }
        url = f'{self.base_url}/nf/network/interfacedetail/edit/'
        #logger.info(data)
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新接口失败: {e}')
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

    def create_or_update_xconnect_interface(self, action='create', id='',
        name='', vm_first_id=None, vm_second_id=None,
        vwire_first_zone='TRUST', vwire_second_zone='TRUST',
        linkmode1='auto', linkmode2='auto',
        linkspeed1='auto', linkspeed2='auto',
        ipv4_mtu1='1500', ipv4_mtu2='1500',
        linkstatus=True, label='', req_body=None):
        """创建或更新交叉连接（XConnect/VWire）接口。

        对应 UI 页面「网络管理 → 接口 → 交叉连接」。

        对应 API 文档中的 ``create_or_update_xconnect``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 接口 ID，编辑时传入
        :type id: str
        :param name: 接口名称，如 ``"test333"``
        :type name: str
        :param vm_first_id: 第一端 VM 端口 ID
        :type vm_first_id: int or None
        :param vm_second_id: 第二端 VM 端口 ID
        :type vm_second_id: int or None
        :param vwire_first_zone: 第一端虚接线安全区，默认 ``"TRUST"``
        :type vwire_first_zone: str
        :param vwire_second_zone: 第二端虚接线安全区，默认 ``"TRUST"``
        :type vwire_second_zone: str
        :param linkmode1: 第一端链路模式，默认 ``"auto"``
        :type linkmode1: str
        :param linkmode2: 第二端链路模式，默认 ``"auto"``
        :type linkmode2: str
        :param linkspeed1: 第一端链路速率，默认 ``"auto"``
        :type linkspeed1: str
        :param linkspeed2: 第二端链路速率，默认 ``"auto"``
        :type linkspeed2: str
        :param ipv4_mtu1: 第一端 MTU，默认 ``"1500"``
        :type ipv4_mtu1: str
        :param ipv4_mtu2: 第二端 MTU，默认 ``"1500"``
        :type ipv4_mtu2: str
        :param linkstatus: 链路状态，默认 ``True``
        :type linkstatus: bool
        :param label: 标签
        :type label: str
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            data = {
                'type': 'XCONNECT_INTERFACE',
                'id': id,
                'name': name,
                'vm_first_id': vm_first_id,
                'vm_second_id': vm_second_id,
                'vwire_first_zone': vwire_first_zone,
                'vwire_second_zone': vwire_second_zone,
                'linkmode1': linkmode1,
                'linkmode2': linkmode2,
                'linkspeed1': linkspeed1,
                'linkspeed2': linkspeed2,
                'ipv4_mtu1': ipv4_mtu1,
                'ipv4_mtu2': ipv4_mtu2,
                'linkstatus': linkstatus,
                'label': label,
            }
        url = f'{self.base_url}/nf/network/interfacedetail/'
        try:
            result = self.session.post(url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新XConnect接口失败: {e}')
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

    def create_or_update_sub_interface(self, action='create', id='',
        parent_name='', name='', vlan_id=100, zone='TRUST',
        attribute='logic', manage=1, ipv4='', sub_ipv4='',
        status='down', ipv6='', ipv6_method='manual',
        router_message=0, ipv4_mtu=1500, tcp_mss=None,
        ipv6_mtu=1500, label='', reverse_route=None, req_body=None):
        """创建或更新子接口（SUB_INTERFACE）。

        对应 UI 页面「网络管理 → 接口 → 子接口」。

        对应 API 端点 ``/nf/network/interfacedetail/``，``type`` 固定为
        ``"SUB_INTERFACE"``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 接口 ID，编辑时传入，默认 ``""``
        :type id: str
        :param parent_name: 父接口名称，如 ``"G1/2"``
        :type parent_name: str
        :param name: 子接口名称，如 ``"G1/2.100"``
        :type name: str
        :param vlan_id: VLAN ID，默认 ``100``
        :type vlan_id: int
        :param zone: 安全区，默认 ``"TRUST"``
        :type zone: str
        :param attribute: 接口属性，默认 ``"logic"``
        :type attribute: str
        :param manage: 管理访问，``1``=启用  ``0``=禁用，默认 ``1``
        :type manage: int
        :param ipv4: IPv4 地址/掩码，如 ``"2.2.3.4/24"``
        :type ipv4: str
        :param sub_ipv4: 辅助 IPv4 地址/掩码，如 ``"2.3.5.1/24"``
        :type sub_ipv4: str
        :param status: 接口状态，``"up"`` 或 ``"down"``，默认 ``"down"``
        :type status: str
        :param ipv6: IPv6 地址/前缀，如 ``"66::1/64"``
        :type ipv6: str
        :param ipv6_method: IPv6 获取方式，``"manual"`` 或 ``"auto"``，默认 ``"manual"``
        :type ipv6_method: str
        :param router_message: 路由器通告，``0``=禁用  ``1``=启用，默认 ``0``
        :type router_message: int
        :param ipv4_mtu: IPv4 MTU，默认 ``1500``
        :type ipv4_mtu: int
        :param tcp_mss: TCP MSS 值，默认 ``None``
        :type tcp_mss: int or None
        :param ipv6_mtu: IPv6 MTU，默认 ``1500``
        :type ipv6_mtu: int
        :param label: 标签，默认 ``""``
        :type label: str
        :param reverse_route: 反向路由列表，每个元素为 ``{"protocol": "IPv4", "next_hop": "", "status": "0"}``
        :type reverse_route: list or None
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            rr = reverse_route if reverse_route is not None else [
                {'protocol': 'IPv4', 'next_hop': '', 'status': '0'}]
            data = {
                'type': 'SUB_INTERFACE',
                'id': id,
                'parent_name': parent_name,
                'name': name,
                'vlan_id': vlan_id,
                'zone': zone,
                'attribute': attribute,
                'manage': manage,
                'ipv4': ipv4,
                'sub_ipv4': sub_ipv4,
                'status': status,
                'ipv6': ipv6,
                'ipv6_method': ipv6_method,
                'router_message': router_message,
                'ipv4_mtu': ipv4_mtu,
                'tcp_mss': tcp_mss,
                'ipv6_mtu': ipv6_mtu,
                'label': label,
                'reverse_route': rr,
            }
        url = f'{self.base_url}/nf/network/interfacedetail/'
        try:
            result = self.session.post(url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新子接口失败: {e}')
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

    def create_or_update_vlan_interface(self, action='create', id='',
        name='', vlan_id=100, zone='TRUST', attribute='logic',
        manage=1, ipv4='', sub_ipv4='', status='down', ipv6='',
        ipv6_method='manual', router_message=0, mac='',
        ipv4_mtu=1500, tcp_mss=None, ipv6_mtu=1500,
        label='', reverse_route=None, req_body=None):
        """创建或更新 VLAN 接口（VLAN_INTERFACE）。

        对应 UI 页面「网络管理 → 接口 → VLAN 接口」。

        对应 API 端点 ``/nf/network/interfacedetail/``，``type`` 固定为
        ``"VLAN_INTERFACE"``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 接口 ID，编辑时传入，默认 ``""``
        :type id: str
        :param name: 接口名称，如 ``"vlan100"``
        :type name: str
        :param vlan_id: VLAN ID，默认 ``100``
        :type vlan_id: int
        :param zone: 安全区，默认 ``"TRUST"``
        :type zone: str
        :param attribute: 接口属性，默认 ``"logic"``
        :type attribute: str
        :param manage: 管理访问，``1``=启用  ``0``=禁用，默认 ``1``
        :type manage: int
        :param ipv4: IPv4 地址/掩码，如 ``"11.2.3.4/24"``
        :type ipv4: str
        :param sub_ipv4: 辅助 IPv4 地址/掩码，默认 ``""``
        :type sub_ipv4: str
        :param status: 接口状态，``"up"`` 或 ``"down"``，默认 ``"down"``
        :type status: str
        :param ipv6: IPv6 地址/前缀，默认 ``""``
        :type ipv6: str
        :param ipv6_method: IPv6 获取方式，``"manual"`` 或 ``"auto"``，默认 ``"manual"``
        :type ipv6_method: str
        :param router_message: 路由器通告，``0``=禁用  ``1``=启用，默认 ``0``
        :type router_message: int
        :param mac: MAC 地址，默认 ``""``
        :type mac: str
        :param ipv4_mtu: IPv4 MTU，默认 ``1500``
        :type ipv4_mtu: int
        :param tcp_mss: TCP MSS 值，默认 ``None``
        :type tcp_mss: int or None
        :param ipv6_mtu: IPv6 MTU，默认 ``1500``
        :type ipv6_mtu: int
        :param label: 标签，默认 ``""``
        :type label: str
        :param reverse_route: 反向路由列表
        :type reverse_route: list or None
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            rr = reverse_route if reverse_route is not None else [
                {'protocol': 'IPv4', 'next_hop': '', 'status': '0'}]
            data = {
                'type': 'VLAN_INTERFACE',
                'id': id,
                'name': name,
                'vlan_id': vlan_id,
                'zone': zone,
                'attribute': attribute,
                'manage': manage,
                'ipv4': ipv4,
                'sub_ipv4': sub_ipv4,
                'status': status,
                'ipv6': ipv6,
                'ipv6_method': ipv6_method,
                'router_message': router_message,
                'mac': mac,
                'ipv4_mtu': ipv4_mtu,
                'tcp_mss': tcp_mss,
                'ipv6_mtu': ipv6_mtu,
                'label': label,
                'reverse_route': rr,
            }
        url = f'{self.base_url}/nf/network/interfacedetail/'
        try:
            result = self.session.post(url, json=data,
                verify=False, timeout=30)
        
        except Exception as e:
            logger.error(f'创建或更新VLAN接口失败: {e}')
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

    def create_or_update_loopback_interface(self, action='create', id='',
        name='', zone='TRUST', attribute='logic', manage=1,
        ipv4='', sub_ipv4='', status='down', ipv6='',
        ipv6_method='manual', router_message=0, mac='',
        ipv4_mtu=1500, tcp_mss=None, ipv6_mtu=1500,
        label='', req_body=None):
        """创建或更新回环接口（LOOPBACK_INTERFACE）。

        对应 UI 页面「网络管理 → 接口 → 回环接口」。

        对应 API 端点 ``/nf/network/interfacedetail/``，``type`` 固定为
        ``"LOOPBACK_INTERFACE"``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 接口 ID，编辑时传入，默认 ``""``
        :type id: str
        :param name: 接口名称，如 ``"loop22"``
        :type name: str
        :param zone: 安全区，默认 ``"TRUST"``
        :type zone: str
        :param attribute: 接口属性，默认 ``"logic"``
        :type attribute: str
        :param manage: 管理访问，``1``=启用  ``0``=禁用，默认 ``1``
        :type manage: int
        :param ipv4: IPv4 地址/掩码，如 ``"66.2.2.1/24"``
        :type ipv4: str
        :param sub_ipv4: 辅助 IPv4 地址/掩码，默认 ``""``
        :type sub_ipv4: str
        :param status: 接口状态，``"up"`` 或 ``"down"``，默认 ``"down"``
        :type status: str
        :param ipv6: IPv6 地址/前缀，默认 ``""``
        :type ipv6: str
        :param ipv6_method: IPv6 获取方式，``"manual"`` 或 ``"auto"``，默认 ``"manual"``
        :type ipv6_method: str
        :param router_message: 路由器通告，``0``=禁用  ``1``=启用，默认 ``0``
        :type router_message: int
        :param mac: MAC 地址，默认 ``""``
        :type mac: str
        :param ipv4_mtu: IPv4 MTU，默认 ``1500``
        :type ipv4_mtu: int
        :param tcp_mss: TCP MSS 值，默认 ``None``
        :type tcp_mss: int or None
        :param ipv6_mtu: IPv6 MTU，默认 ``1500``
        :type ipv6_mtu: int
        :param label: 标签，默认 ``""``
        :type label: str
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            data = {
                'type': 'LOOPBACK_INTERFACE',
                'id': id,
                'name': name,
                'zone': zone,
                'attribute': attribute,
                'manage': manage,
                'ipv4': ipv4,
                'sub_ipv4': sub_ipv4,
                'status': status,
                'ipv6': ipv6,
                'ipv6_method': ipv6_method,
                'router_message': router_message,
                'mac': mac,
                'ipv4_mtu': ipv4_mtu,
                'tcp_mss': tcp_mss,
                'ipv6_mtu': ipv6_mtu,
                'label': label,
            }
        url = f'{self.base_url}/nf/network/interfacedetail/'
        try:
            result = self.session.post(url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新回环接口失败: {e}')
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

    def create_or_update_ipsec_interface(self, action='create', id='',
        name='', zone='TRUST', attribute='logic', status='up',
        ipv4='', ipv4_mtu=1400, mac='', sub_type='ipsec',
        tcp_mss=1360, req_body=None):
        """创建或更新 IPSec 逻辑接口（IPSEC_INTERFACE）。

        对应 UI 页面「网络管理 → 接口 → IPSec 接口」。

        对应 API 端点 ``/nf/network/interfacedetail/``，``type`` 固定为
        ``"IPSEC_INTERFACE"``。

        .. note::

            ``ipv4`` 必须为网段地址（如 ``"1.2.3.0/24"``），不可填写主机地址。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 接口 ID，编辑时传入，默认 ``""``
        :type id: str
        :param name: 接口名称，如 ``"ipsec"``
        :type name: str
        :param zone: 安全区，默认 ``"TRUST"``
        :type zone: str
        :param attribute: 接口属性，默认 ``"logic"``
        :type attribute: str
        :param status: 接口状态，``"up"`` 或 ``"down"``，默认 ``"up"``
        :type status: str
        :param ipv4: IPv4 网段地址/掩码，如 ``"1.2.3.0/24"``（必须是网段）
        :type ipv4: str
        :param ipv4_mtu: IPv4 MTU，默认 ``1400``
        :type ipv4_mtu: int
        :param mac: MAC 地址，默认 ``""``
        :type mac: str
        :param sub_type: 子类型，固定 ``"ipsec"``
        :type sub_type: str
        :param tcp_mss: TCP MSS 值，默认 ``1360``
        :type tcp_mss: int
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            data = {
                'type': 'IPSEC_INTERFACE',
                'id': id,
                'name': name,
                'zone': zone,
                'attribute': attribute,
                'status': status,
                'ipv4': ipv4,
                'ipv4_mtu': ipv4_mtu,
                'mac': mac,
                'sub_type': sub_type,
                'tcp_mss': tcp_mss,
            }
        url = f'{self.base_url}/nf/network/interfacedetail/'
        try:
            result = self.session.post(url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新IPSec接口失败: {e}')
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

    def create_or_update_bond_interface(self, action='create', id='',
        name='', aggre_model='BOND_API_MODE_ROUND_ROBIN',
        dispense_policy='', interface=None, label='', req_body=None):
        """创建或更新聚合接口（BOND_INTERFACE）。

        对应 UI 页面「网络管理 → 接口 → 聚合接口」。

        对应 API 端点 ``/nf/network/interfacedetail/``，``type`` 固定为
        ``"BOND_INTERFACE"``。

        :param action: 操作类型，``"create"`` 或 ``"edit"``
        :type action: str
        :param id: 接口 ID，编辑时传入，默认 ``""``
        :type id: str
        :param name: 接口名称，如 ``"test333"``
        :type name: str
        :param aggre_model: 聚合模式，默认 ``"BOND_API_MODE_ROUND_ROBIN"``
        :type aggre_model: str
        :param dispense_policy: 分发策略，默认 ``""``
        :type dispense_policy: str
        :param interface: 子接口列表，每项为 ``{"id": 0, "sub_interface": "T2/1", "level": 1, "work_model": "initiative"}``
        :type interface: list or None
        :param label: 标签，默认 ``""``
        :type label: str
        :param req_body: 自定义请求体，传入后忽略所有关键字参数
        :type req_body: dict or None
        :return: 成功返回 API 响应 dict，失败返回 False
        :rtype: dict or bool
        """
        if req_body is not None:
            data = req_body
        else:
            iface = interface if interface is not None else []
            data = {
                'type': 'BOND_INTERFACE',
                'id': id,
                'name': name,
                'aggre_model': aggre_model,
                'dispense_policy': dispense_policy,
                'interface': iface,
                'label': label,
            }
        url = f'{self.base_url}/nf/network/interfacedetail/'
        try:
            result = self.session.post(url, json=data,
                verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新聚合接口失败: {e}')
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

    def get_interfaces(self, page=1, size=10, search='', if_type=''):
        """获取接口列表。

        对应 UI 页面「网络管理 → 接口」。

        与 ``search_interface_list`` 功能相同，均为 GET 请求获取接口概览列表。

        ``if_type`` 取值：
            - ``"L3_INTERFACE"`` = 三层接口
            - ``"L2_INTERFACE"`` = 二层接口
            - ``"NO_ALLOCATION_INTERFACE"`` = 未配置接口
            - ``"IPSEC_INTERFACE"`` = IPSec 逻辑接口

        :param page:    页码，默认 ``1``。
        :param size:    每页数量，默认 ``10``。
        :param search:  搜索关键字，默认 ``""``。
        :param if_type: 接口类型过滤，默认 ``""``（全部）。
        :return: 成功返回完整响应 dict，结构为 ``{"status": 2000, "result": {"total": ..., "list": {"physical": [...], "logic": [...]}}, ...}``；
                 失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/interface/'
        params = {'size': size, 'page': page, 'search': search, 'type': if_type}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取接口列表失败: {e}')
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

    def get_interfaces_id(self, page=1, size=10, search='', if_type=''):
        """根据名称查询接口 ID。

        对应 UI 页面「网络管理 → 接口」。

        调用 ``get_interfaces`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:    页码，默认 ``1``。
        :param size:    每页数量，默认 ``10``。
        :param search:  接口名称关键字，用于匹配。
        :param if_type: 接口类型过滤，默认 ``""``。
        :return: 匹配到时返回接口 ID (int)；失败返回 ``False``。
        """
        resp = self.get_interfaces(page=page, size=size, search=search,
                                   if_type=if_type)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def get_interface_detail(self, if_id=1, if_type="L3_INTERFACE"):
        """获取接口详情。

        对应 UI 页面「网络管理 → 接口 → 详情」。

        ``if_type`` 取值：
            - ``"L3_INTERFACE"`` = 三层接口
            - ``"L2_INTERFACE"`` = 二层接口
            - ``"NO_ALLOCATION_INTERFACE"`` = 未配置接口

        :param if_id:   接口 ID，默认 ``1``。
        :param if_type: 接口类型，默认 ``"L3_INTERFACE"``。
        :return: 成功返回完整响应 dict，``result`` 中包含接口完整配置；
                 失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/interfacedetail/'
        params = {'id': if_id, 'type': if_type}
        try:
            result = self.session.get(url, params=params, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取接口详情失败: {e}')
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

    def remove_interface(self, interface_id, if_type, req_body=None):
        """删除接口。

        对应 UI 页面「网络管理 → 接口 → 删除」。

        :param interface_id: 接口 ID。
        :param if_type:      接口类型，如 ``"L3_INTERFACE"``。
        :param req_body:     自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': str(interface_id), 'type': if_type}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/interfacedetail/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除接口失败: {e}')
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

    def update_interface_status(self, if_id, if_type, action='up', req_body=None):
        """更新接口状态（启用/禁用）。

        对应 UI 页面「网络管理 → 接口 → 启用/禁用」。

        :param if_id:    接口 ID。
        :param if_type:  接口类型，如 ``"L3_INTERFACE"``。
        :param action:   操作动作。``"up"`` = 启用（默认），``"down"`` = 禁用。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'id': if_id, 'action': action, 'type': if_type}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/interface/interfacestatus/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新接口状态失败: {e}')
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

    def create_or_update_mgt_attr(self, action='create', name='mgt_1',
        mgt_attr_id=-1, https=True, icmp=True, ssh=True, req_body=None):
        """创建或更新可管理属性。

        对应 UI 页面「网络管理 → 接口 → 可管理属性 → 新建/编辑」。

        可管理属性用于控制接口上允许的管理协议（HTTPS、ICMP、SSH）。

        :param action:      操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param name:        属性名称，默认 ``"mgt_1"``。
        :param mgt_attr_id: 属性 ID。创建时传 ``-1``（默认），编辑时传实际 ID。
        :param https:       是否启用 HTTPS 管理。``True`` = 启用（默认），``False`` = 禁用。
        :param icmp:        是否启用 ICMP（Ping）。``True`` = 启用（默认），``False`` = 禁用。
        :param ssh:         是否启用 SSH 管理。``True`` = 启用（默认），``False`` = 禁用。
        :param req_body:    自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'action': action, 'id': mgt_attr_id, 'name': name, 'https': str
            (https), 'ssh': str(ssh), 'icmp': str(icmp)}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/mgt/configuration/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建或更新可管理属性失败: {e}')
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

    def get_mgt_attr(self, name='default', page=1, size=10, https='', icmp='',
        ssh='', where='OR'):
        """获取可管理属性列表。

        对应 UI 页面「网络管理 → 接口 → 可管理属性」。

        ``where`` 取值：
            - ``"OR"`` = 满足任一条件（默认）
            - ``"AND"`` = 满足全部条件

        :param name:  名称过滤，默认 ``"default"``。传 ``""`` 不过滤。
        :param page:  页码，默认 ``1``。
        :param size:  每页数量，默认 ``10``。
        :param https: HTTPS 过滤。``"True"`` / ``"False"`` / ``""``（不过滤）。
        :param icmp:  ICMP 过滤。``"True"`` / ``"False"`` / ``""``（不过滤）。
        :param ssh:   SSH 过滤。``"True"`` / ``"False"`` / ``""``（不过滤）。
        :param where: 条件组合方式，默认 ``"OR"``。
        :return: 成功返回完整响应 dict，``result.list`` 为属性列表；
                 失败返回 ``False``。
        """
        data = {'page': page, 'size': size, 'name': name, 'https': https,
            'icmp': icmp, 'ssh': ssh, 'where': where}
        url = f'{self.base_url}/nf/network/mgt/info/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取可管理属性列表失败: {e}')
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
        logger.info(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_mgt_attr_id(self, name='default', page=1, size=10, https='', icmp='',
        ssh='', where='OR'):
        """根据名称获取可管理属性 ID。

        对应 UI 页面「网络管理 → 接口 → 可管理属性」。

        调用 ``get_mgt_attr`` 后在返回列表中按 ``name`` 精确匹配。

        :param name:  属性名称，用于匹配。
        :param page:  页码，默认 ``1``。
        :param size:  每页数量，默认 ``10``。
        :param https: HTTPS 过滤，默认 ``""``。
        :param icmp:  ICMP 过滤，默认 ``""``。
        :param ssh:   SSH 过滤，默认 ``""``。
        :param where: 条件组合方式，默认 ``"OR"``。
        :return: 匹配到时返回属性 ID (int)；失败返回 ``False``。
        """
        resp = self.get_mgt_attr(name=name, page=page, size=size, https=https,
                                 icmp=icmp, ssh=ssh, where=where)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == name:
                return item.get('id')
        return False


    def remove_mgt_attr(self, mgt_id, req_body=None):
        """删除可管理属性。

        对应 UI 页面「网络管理 → 接口 → 可管理属性 → 删除」。

        ``mgt_id`` 支持 ``int``、``str`` 或 ``list[int/str]``，传入单个值时自动包装为列表。

        :param mgt_id:   可管理属性 ID，支持 int（如 ``1``）、str 或 list（如 ``[1, 2]``）。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(mgt_id, (int, str)):
            mgt_id = [int(mgt_id)]
        data = {'id': mgt_id}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/network/mgt/delete/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'删除可管理属性失败: {e}')
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

    def interface_route_console(self, inband_enable=False, reverse_route_enable
        =False, secondary_routing_enable=False):
        """配置接口路由控制台（带内/反向路由/辅助路由）。

        对应 UI 页面「网络管理 → 路由 → 接口路由控制」。

        :param inband_enable:            是否启用带内管理路由，默认 ``False``。
        :param reverse_route_enable:     是否启用反向路由，默认 ``False``。
        :param secondary_routing_enable: 是否启用辅助路由，默认 ``False``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        data = {'inband_enable': inband_enable, 'reverse_route_enable':
            reverse_route_enable, 'secondary_routing_enable':
            secondary_routing_enable}
        url = f'{self.base_url}/nf/network/route/interface_route_console/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'接口路由控制配置失败: {e}')
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

    def create_or_update_ospf_interface(self, if_conf_id='', action='create',
        name='G1/1', metric=1, priority=1, hello_int=10, dead_count=40,
        retransmit_int=5, transmit_delay=1, intf_net_type='broadcast',
        auth_type='none', password=None, key_id=None, req_body=None):
        """创建或更新 OSPF 接口配置。

        对应 UI 页面「网络管理 → 路由 → OSPF → 接口配置」。

        ``auth_type`` 取值：
            - ``"none"`` = 无认证（默认），password/key_id 自动置空
            - ``"md5"`` = MD5 认证，password 默认 ``"123456"``，key_id 默认 ``"1"``
            - ``"key"`` = 简单密码认证，password 默认 ``"123456"``，key_id 自动置空

        ``intf_net_type`` 取值：
            - ``"broadcast"`` = 广播网络（默认）
            - ``"p2p"`` = 点对点网络

        :param if_conf_id:      接口配置 ID。创建时传 ``""``（默认），编辑时传实际 ID。
        :param action:          操作类型。``"create"`` = 新建（默认），``"edit"`` = 编辑。
        :param name:            接口名称，如 ``"G1/1"``，默认 ``"G1/1"``。
        :param metric:          OSPF 度量值，默认 ``1``。
        :param priority:        OSPF 优先级，默认 ``1``。
        :param hello_int:       Hello 间隔（秒），默认 ``10``。
        :param dead_count:      邻居失效计数（个），默认 ``40``。
        :param retransmit_int:  重传间隔（秒），默认 ``5``。
        :param transmit_delay:  传输延迟（秒），默认 ``1``。
        :param intf_net_type:   接口网络类型，默认 ``"broadcast"``。
        :param auth_type:       认证类型，默认 ``"none"``。
        :param password:        认证密码，默认根据 ``auth_type`` 自动填充。
        :param key_id:          认证 Key ID，默认根据 ``auth_type`` 自动填充。
        :param req_body:        自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if auth_type == 'md5':
            password = '123456' if password is None else password
            key_id = '1' if key_id is None else key_id
        elif auth_type == 'key':
            password = '123456' if password is None else password
            key_id = '' if key_id is None else key_id
        else:
            password = '' if password is None else password
            key_id = '' if key_id is None else key_id
        data = {'id': if_conf_id, 'action': action, 'name': name, 'metric':
            metric, 'priority': priority, 'hello_int': hello_int, 'dead_count':
            dead_count, 'retransmit_int': retransmit_int, 'transmit_delay':
            transmit_delay, 'intf_net_type': intf_net_type, 'auth_type':
            auth_type, 'password': password, 'key_id': key_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/interface/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'创建或更新OSPF接口配置失败: {e}')
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

    def get_ospf_interface(self, page=1, size=10, search='', if_type=''):
        """获取 OSPF 接口配置列表。

        对应 UI 页面「网络管理 → 路由 → OSPF → 接口配置」。

        :param page:    页码，默认 ``1``。
        :param size:    每页数量，默认 ``10``。
        :param search:  搜索关键字，默认 ``""``。
        :param if_type: 接口类型过滤，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        req_url = f'{self.base_url}/nf/network/route/ospf/interface/'
        params = {'size': size, 'page': page, 'search': search, 'type': if_type}
        try:
            result = self.session.get(req_url, params=params, verify=False,
                timeout=30)
        except Exception as e:
            logger.error(f'获取OSPF接口配置失败: {e}')
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

    def get_ospf_interface_id(self, page=1, size=10, search='', if_type=''):
        """根据名称查询 OSPF 接口配置 ID。

        对应 UI 页面「网络管理 → 路由 → OSPF → 接口配置」。

        调用 ``get_ospf_interface`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:    页码，默认 ``1``。
        :param size:    每页数量，默认 ``10``。
        :param search:  接口名称关键字，用于匹配。
        :param if_type: 接口类型过滤，默认 ``""``。
        :return: 匹配到时返回接口配置 ID (int)；失败返回 ``False``。
        """
        resp = self.get_ospf_interface(page=page, size=size, search=search,
                                       if_type=if_type)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def remove_ospf_interface(self, if_conf_id, req_body=None):
        """删除 OSPF 接口配置。

        对应 UI 页面「网络管理 → 路由 → OSPF → 接口配置 → 删除」。

        ``if_conf_id`` 支持单个 ID（int/str）或多个 ID（list/tuple），多个时自动以逗号拼接。

        :param if_conf_id: 接口配置 ID，支持 int、str 或 list/tuple（如 ``[1, 2]``）。
        :param req_body:   自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(if_conf_id, (list, tuple)):
            if_conf_id = ','.join(map(str, if_conf_id))
        else:
            if_conf_id = str(if_conf_id)
        data = {'id': if_conf_id}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/route/ospf/area/delete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'删除OSPF接口配置失败: {e}')
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

    def get_snooping_interface_action(self, page=1, size=20, search=''):
        """获取 DHCP Snooping 接口动作配置列表。

        对应 UI 页面「网络管理 → DHCP Snooping → 接口动作」。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``20``。
        :param search: 搜索关键字，默认 ``""``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        query_params = {'page': page, 'size': size, 'search': search}
        req_url = f'{self.base_url}/nf/network/snooping/interface/'
        try:
            result = self.session.get(req_url, params=query_params, verify=
                False, timeout=30)
        except Exception as e:
            logger.error(f'获取DHCP Snooping接口动作配置失败: {e}')
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

    def get_snooping_interface_action_id(self, page=1, size=20, search=''):
        """根据名称查询 DHCP Snooping 接口动作配置 ID。

        对应 UI 页面「网络管理 → DHCP Snooping → 接口动作」。

        调用 ``get_snooping_interface_action`` 后在返回列表中按 ``name`` 精确匹配。

        :param page:   页码，默认 ``1``。
        :param size:   每页数量，默认 ``20``。
        :param search: 接口名称关键字，用于匹配。
        :return: 匹配到时返回配置 ID (int)；失败返回 ``False``。
        """
        resp = self.get_snooping_interface_action(page=page, size=size,
                                                   search=search)
        if resp is False:
            return False
        result_data = resp.get('result', {})
        if result_data.get('total', 0) == 0:
            return False
        for item in result_data.get('list', []):
            if item.get('name') == search:
                return item.get('id')
        return False

    def update_snooping_interface_action(self, if_name=None, enable=None,
        action=None, req_body=None):
        """更新 DHCP Snooping 接口动作配置。

        对应 UI 页面「网络管理 → DHCP Snooping → 接口动作 → 编辑」。

        ``if_name`` 和 ``enable`` 支持单个值或列表，传入单个时自动包装为列表。
        列表长度需一致，以一一对应组装 ``interface_data``。

        :param if_name:  接口名称，str 或 list[str]。默认 ``["G1/1"]``。
        :param enable:   是否启用，bool 或 list[bool]。默认 ``[True]``。
        :param action:   操作动作字符串，可选。传入时附加到请求体 ``action`` 字段。
        :param req_body: 自定义请求体 dict，传入后优先使用，覆盖默认构造的请求体。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        if isinstance(if_name, str):
            if_name = [if_name]
        elif if_name is None:
            if_name = ['G1/1']
        if isinstance(enable, bool):
            enable = [enable]
        elif enable is None:
            enable = [True]
        data = {'interface_data': [{'interface': if_name[i], 'enable': enable[i
            ]} for i in range(len(if_name))]}
        if action is not None:
            data['action'] = action
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/network/snooping/interface/action/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'更新DHCP Snooping接口动作配置失败: {e}')
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

    def create_logic_ipsec(self, ipv4='192.168.0.0/24', ipv4_mtu='1400', name=
        'ipsec', tcp_mss='1360', zone='ipsec'):
        """创建 IPSec 逻辑接口。

        对应 UI 页面「网络管理 → 接口 → 新建（IPSec 逻辑接口）」。

        :param ipv4:     IPv4 地址，如 ``"192.168.0.0/24"``。
        :param ipv4_mtu: IPv4 MTU，默认 ``"1400"``。
        :param name:     接口名称，默认 ``"ipsec"``。
        :param tcp_mss:  TCP MSS，默认 ``"1360"``。
        :param zone:     安全区名称，默认 ``"ipsec"``。
        :return: 成功返回完整响应 dict；失败返回 ``False``。
        """
        url = f'{self.base_url}/nf/network/interfacedetail/'
        data = {'attribute': 'logic', 'id': '', 'ipv4': ipv4, 'ipv4_mtu':
            ipv4_mtu, 'mac': '', 'name': name, 'status': 'up', 'sub_type':
            'ipsec', 'tcp_mss': tcp_mss, 'type': 'IPSEC_INTERFACE', 'zone': zone}
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'创建接口失败: {e}')
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
