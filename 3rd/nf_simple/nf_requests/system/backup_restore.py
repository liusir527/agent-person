"""系统备份恢复。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm import *
from ..client import NFRequests


class BackupRestoreFeature(NFRequests):
    """系统备份恢复操作集合。"""

    def download_backup_file(self, file_type='all'):
        """下载备份文件。

        对应 UI 页面「系统 → 备份恢复 → 备份」。

        :param file_type: 备份类型，默认 ``"all"``
        :return: 成功返回备份文件的二进制内容（``bytes``）；失败返回 ``False``
        """
        url = f'{self.base_url}/nf/system/backup/'
        params = {'type': file_type}
        try:
            result = self.session.get(url, params=params, verify=False, timeout
                =30, stream=True)
        except Exception as e:
            logger.error(f'下载备份文件失败: {e}')
            return False
        if result.status_code == 200:
            logger.info(f'下载备份文件成功')
            return result.content
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def get_recover_progress(self):
        """获取恢复进度。

        对应 UI 页面「系统 → 备份恢复 → 恢复」。

        :return: 成功返回完整响应 dict；失败返回 ``False``。

            ``result.status`` 说明：

            - ``0`` = 空闲（无恢复任务）
            - ``1`` = 恢复中
            - ``2`` = 恢复完成
        """
        url = f'{self.base_url}/nf/system/recover_progress/'
        try:
            result = self.session.get(url, verify=False, timeout=30)
        except Exception as e:
            logger.error(f'获取恢复进度失败: {e}')
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
        else:
            logger.error(f'HTTP请求失败，状态码: {result.status_code}')
            return False

    def recover_url_wblist_from_recycle(self, url_id, list_type='black_list'):
        """从回收站恢复 URL 黑/白名单。

        .. note:: 该函数属于 URL 回收站功能，非备份恢复核心接口。

        :param url_id: 要恢复的 URL ID，支持单个 int/str 或 list/tuple
        :param list_type: 列表类型，``"black_list"`` = 黑名单，``"white_list"`` =
            白名单，默认 ``"black_list"``
        :return: 成功返回完整响应 dict；失败返回 ``False``
        """
        if isinstance(url_id, (list, tuple)):
            url_id = ','.join(map(str, url_id))
        else:
            url_id = str(url_id)
        data = {'id': url_id, 'type': list_type}
        req_url = f'{self.base_url}/nf/object/url/recycle/'
        try:
            result = self.session.post(req_url, json=data, verify=False, timeout=30
                )
        except Exception as e:
            logger.error(f'恢复URL黑白名单失败: {e}')
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
