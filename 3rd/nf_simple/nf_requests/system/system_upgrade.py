"""系统在线/离线升级。"""

import sys
import requests
import json
import os
import base64
import logging
import time

from requests.adapters import HTTPAdapter

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class SystemUpgradeFeature(NFRequests):
    """系统升级操作集合。"""

    def update_system_online_update_config(self, url='update.nsfocus.com',
                                            update_engine='false',
                                            update_type='all',
                                            download_only='false',
                                            enabled='true', time_val='02:00',
                                            date_type='day', date='0',
                                            update_time_type='false'):
        """
        更新系统在线升级配置
        :param url: 升级地址
        :param update_engine: 升级包含引擎，true-包含，false-不包含
        :param update_type: 升级包类型，eng-仅规则库，all-所有类型
        :param download_only: 是否仅下载升级包
        :param enabled: 是否自动升级，true-开启，false-关闭
        :param time_val: 升级时间
        :param date_type: day-每天升级，week-按星期升级
        :param date: 升级时间，0-每天，1-7代表周一到周日
        :param update_time_type: 升级时间，true-立即，false-定时
        :return: resp_data 成功，False 失败
        """
        body = {"url": url, "update_engine": update_engine,
                "update_type": update_type, "download_only": download_only,
                "enabled": enabled, "time": time_val, "type": date_type,
                "date": date, "update_time_type": update_time_type}
        url_full = f'{self.base_url}/nf/system/update_system_online_config/'
        try:
            result = self.session.post(url_full, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'更新系统在线升级配置失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(body)
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def get_system_update_version(self):
        """
        获取系统升级版本列表
        :return: resp_data 成功，False 失败
        """
        url = f'{self.base_url}/nf/system/system_update_version/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取系统升级版本失败: {e}')
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

    def get_system_restore_info(self):
        """
        获取系统恢复信息
        :return: resp_data 成功，False 失败
        """
        url = f'{self.base_url}/nf/system/restore_info/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取系统恢复信息失败: {e}')
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

    def get_system_online_config(self):
        """
        获取系统在线升级配置
        :return: resp_data 成功，False 失败
        """
        url = f'{self.base_url}/nf/system/get_system_online_config/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取系统在线升级配置失败: {e}')
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

    def download_system_update_version(self, v_type='waf_lib',
                                        v_type_id='name'):
        """
        下载系统升级版本
        :param v_type: 升级类型，如 'waf_lib'
        :param v_type_id: 升级 ID 字段名，如 'name'
        :return: resp_data 成功，False 失败
        """
        body = {'type': v_type, 'id': v_type_id}
        url = f'{self.base_url}/nf/system/system_update_version/'
        try:
            result = self.session.post(url, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'下载系统升级版本失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(body)
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def system_update(self, v_type='waf_lib', v_type_id='name'):
        """
        执行系统更新
        :param v_type: 升级类型，如 'waf_lib'
        :param v_type_id: 升级 ID 字段名，如 'name'
        :return: resp_data 成功，False 失败
        """
        body = {'type': v_type, 'id': v_type_id}
        url = f'{self.base_url}/nf/system/system_update_version/update'
        try:
            result = self.session.post(url, json=body, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'执行系统更新失败: {e}')
            return False
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(body)
                logger.error(message)
                return False
            logger.info(message)
            return resp_data
        logger.error(f'HTTP请求失败，状态码: {result.status_code}')
        return False

    def _get_system_update_property_by_name(self, name, attr):
        """
        按名称获取特征库属性
        :param name: 特征库名称
        :param attr: 特征库属性名
        :return: 属性值或 None
        """
        data = self.get_system_update_version()
        if not data:
            logger.error(f'获取系统更新版本列表失败')
            return None
        for item in data.get('result', {}).get('res', []):
            if item.get('type_name') == name:
                return item.get(attr)
        return None

    def get_system_update_version_by_name(self, name):
        """
        按名称获取特征库版本号
        :param name: 特征库名称
        :return: 版本号字符串成功，False 失败
        """
        try:
            version = self._get_system_update_property_by_name(name, 'version')
        except Exception as e:
            logger.error(f'按名称获取特征库版本失败，未找到名称: {name}，异常: {e}')
            return False
        if version is None:
            logger.error(f'未找到特征库: {name}')
            return False
        return version

    def wait_system_update_finish(self):
        """
        等待系统升级完成
        :return: resp_data 成功，False 失败
        """
        for i in range(200):
            url = f'{self.base_url}/nf/system/is_update_state'
            try:
                result = self.session.get(url, verify=False, timeout=30)
            except Exception as e:
                logger.error(f'获取升级状态失败: {e}')
                return False
            if result.status_code != 200:
                logger.error(f'获取升级状态HTTP请求失败，状态码: {result.status_code}')
                return False
            resp_data = json.loads(result.text)
            if resp_data.get('status') != 2000:
                logger.error(resp_data.get('message'))
                return False
            if resp_data.get('result', [{}])[-1].get('percent') == 100:
                logger.info('系统升级完成')
                time.sleep(10)
                return True
            time.sleep(3)
        logger.error('等待系统升级超时')
        return False

    def upload_system_update_file(self, file_path, file_type='local.eng'):
        """
        上传系统升级文件（流式上传，禁用自动重试避免 SSL 大文件重发）
        :param file_path: 升级文件路径
        :param file_type: 文件类型
        :return: resp_data 成功，False 失败
        """
        if not os.path.isfile(file_path):
            logger.error(f'升级文件未找到: {file_path}')
            return False
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f'正在上传文件：{file_name}，大小：{file_size_mb:.1f} MB')
        # 挂载零重试适配器，禁止 urllib3 对 SSL 写错误自动重试（大文件重发必然失败）
        prev_adapter = self.session.adapters.get('https://')
        self.session.mount('https://', HTTPAdapter(max_retries=0))
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f, 'application/octet-stream')}
                url = f'{self.base_url}/nf/system/system_update/upload_offline_chunk/'
                params = {'type': file_type}
                data = {'file_size': file_size, 'file_name': file_name,
                        'chunk_index': 0, 'total_chunks': 1}
                result = self.session.post(
                    url,
                    params=params,
                    data=data,
                    files=files,
                    verify=False,
                    timeout=900
                )
        except Exception as e:
            logger.error(f'上传系统升级文件失败: {e}')
            return False
        finally:
            # 恢复原始适配器
            if prev_adapter is not None:
                self.session.mount('https://', prev_adapter)
        if result.status_code == 200:
            resp_data = json.loads(result.text)
            status_code = resp_data.get('status')
            message = resp_data.get('message')
            if status_code != 2000:
                logger.error(message)
                return False
            logger.info(message)
            return True
        logger.error(f'上传升级文件HTTP请求失败，状态码: {result.status_code}')
        return False
