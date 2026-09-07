"""会话与报文过滤。"""

import sys
import requests
import json
import os
import base64
import logging

from ..nflib.Log import logger
from ..nflib.comm import *
from ..client import NFRequests


class SessionPacketFilterFeature(NFRequests):
    """会话与报文过滤操作集合。"""

    def update_session_manager_config(self, udp_timeout=60, icmp_timeout=30,
        tcp_est_timeout=1800, tcp_fin_timeout=1, tcp_init_timeout=1,
        is_status_check_tcp=0, is_status_check_icmp=0, ha_sync_wait=0, req_body
        =None):
        """
        更新会话管理配置
        :param session: requests Session对象
        :param req_body: 自定义请求体，传入后优先使用
        :return:
        """
        data = {'udp_timeout': udp_timeout, 'icmp_timeout': icmp_timeout,
            'tcp_est_timeout': tcp_est_timeout, 'tcp_fin_timeout':
            tcp_fin_timeout, 'tcp_init_timeout': tcp_init_timeout,
            'is_status_check_tcp': is_status_check_tcp, 'is_status_check_icmp':
            is_status_check_icmp, 'ha_sync_wait': ha_sync_wait}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/session/config/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'更新会话管理配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_session_manager_config(self):
        """
        获取会话管理配置
        :param session: requests Session对象
        :return:
        """
        req_url = f'{self.base_url}/nf/system/session/config/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            msg = f'获取会话管理配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def update_fast_sync_session_config(self, fast_session_sync=True, sync_type
        ='fastsessionsync', req_body=None):
        """
        更新快速会话同步配置
        :param session: requests Session对象
        :param fast_session_sync: True启用，False禁用
        :param sync_type: 同步类型，默认 'fastsessionsync'
        :param req_body: 自定义请求体，传入后优先使用
        :return:
        """
        data = {'type': str(sync_type).lower(), 'fast_session_sync': str(
            fast_session_sync).lower()}
        if req_body is not None:
            data = req_body
        url = f'{self.base_url}/nf/ha/fast_session_sync/'
        try:
            result = self.session.post(url, json=data, verify=False, timeout=30)
        except Exception as e:
            msg = f'更新快速会话同步配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def update_filter_config(self, sif='', src_net='0.0.0.0/0', dst_net=
        '0.0.0.0/0', s_port=0, d_port=0, proto=0, req_body=None):
        """
        更新丢包统计过滤配置
        :param session: requests Session对象
        :param req_body: 自定义请求体，传入后优先使用
        :return:
        """
        data = {'sif': sif, 'srcnet': src_net, 'dstnet': dst_net, 'sport':
            s_port, 'dport': d_port, 'proto': proto}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/packet_loss_counter/update_filter/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'更新丢包统计过滤配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            if status_code != 2000 and status_code != 'success':
                logger.error(resp_data)
                return {"success": False, "message": resp_data}
            return resp_data
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def action_counter_status(self, enable, req_body=None):
        """
        启用或禁用丢包统计
        :param session: requests Session对象
        :param enable: true or false
        :param req_body: 自定义请求体，传入后优先使用
        :return:
        """
        data = {'enable': enable}
        if req_body is not None:
            data = req_body
        req_url = (
            f'{self.base_url}/nf/system/packet_loss_counter/action_counter_status/'
            )
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'操作丢包统计状态失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def clear_counter_result(self):
        """
        清除丢包统计结果
        :param session: requests Session对象
        :return:
        """
        req_url = (
            f'{self.base_url}/nf/system/packet_loss_counter/clear_counter_result/')
        try:
            result = self.session.post(req_url, data=json.dumps({}), verify=
                False, timeout=30)
        except Exception as e:
            msg = f'清除丢包统计结果失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_filter_info(self):
        """
        获取丢包统计配置
        :param session: requests Session对象
        :return:
        """
        req_url = f'{self.base_url}/nf/system/packet_loss_counter/filter_info/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            msg = f'获取丢包统计配置失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_counter_status(self):
        """
        获取丢包统计状态
        :param session: requests Session对象
        :return:
        """
        req_url = (
            f'{self.base_url}/nf/system/packet_loss_counter/get_counter_status/')
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            msg = f'获取丢包统计状态失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_counter_result(self):
        """
        获取丢包统计结果
        :param session: requests Session对象
        :return:
        """
        req_url = f'{self.base_url}/nf/system/packet_loss_counter/counter_result/'
        try:
            result = self.session.get(req_url, verify=False, timeout=30)
        except Exception as e:
            msg = f'获取丢包统计结果失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def get_session_table(self, src_addr=None, dst_addr=None, src_mac=None,
        dst_mac=None, s2d_rx_if=None, d2s_rx_if=None, server_id=None,
        comp_flags=None, src_port=None, dst_port=None, protocol=None, src_zone=
        None, dst_zone=None, action=0, appid=None, size=20, page=1, vsys_id='',
        req_body=None):
        """
        获取会话表
        :param session: requests Session对象
        :param req_body: 自定义请求体，传入后优先使用
        :return:
        """
        data = {'size': size, 'page': page, 'vsysId': vsys_id, 'src_addr':
            src_addr, 'dst_addr': dst_addr, 'src_mac': src_mac, 'dst_mac':
            dst_mac, 's2d_rx_if': s2d_rx_if, 'd2s_rx_if': d2s_rx_if,
            'server_id': server_id, 'comp_flags': comp_flags, 'protocol':
            protocol, 'src_port': src_port, 'dst_port': dst_port, 'src_zone':
            src_zone, 'dst_zone': dst_zone, 'action': action, 'appid': appid}
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/session/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'获取会话表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def remove_session_table(self, src_addr, dst_addr, src_port, dst_port,
        protocol, req_body=None):
        """
        删除会话表项
        :param session: requests Session对象
        :param req_body: 自定义请求体，传入后优先使用
        :return:
        """
        if isinstance(src_addr, str):
            src_addr = [src_addr]
        if isinstance(dst_addr, str):
            dst_addr = [dst_addr]
        if isinstance(src_port, int):
            src_port = [src_port]
        if isinstance(dst_port, int):
            dst_port = [dst_port]
        if isinstance(protocol, int):
            protocol = [protocol]
        data = [{'src_addr': a, 'dst_addr': b, 'src_port': c, 'dst_port': d,
            'protocol': e} for a, b, c, d, e in zip(src_addr, dst_addr,
            src_port, dst_port, protocol)]
        if req_body is not None:
            data = req_body
        req_url = f'{self.base_url}/nf/system/session/SessioninfoDelete/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            msg = f'删除会话表项失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}

    def clear_session_table(self):
        """
        清空会话表
        :param session: requests Session对象
        :return:
        """
        req_url = f'{self.base_url}/nf/system/session/SessioninfoDelete/'
        try:
            result = self.session.post(req_url, data=json.dumps([]), verify=
                False, timeout=30)
        except Exception as e:
            msg = f'清空会话表失败: {e}'
            logger.error(msg)
            return {"success": False, "message": msg}
        if result.status_code == 200:
            status = json.loads(result.text).get('status')
            message = json.loads(result.text).get('message')
            if status != 2000:
                logger.error(message)
                return {"success": False, "message": message}
            else:
                logger.info(message)
                return json.loads(result.text)
        msg = f'HTTP请求失败，状态码: {result.status_code}'
        logger.error(msg)
        return {"success": False, "message": msg}
