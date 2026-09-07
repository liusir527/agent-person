"""会话创建。"""

import sys
import requests
import json
import os
import base64
import logging

from nf_requests.nflib.Log import logger
from nf_requests.nflib.comm  import *
from ..client import NFRequests


class SessionFeature(NFRequests):
    """会话创建操作集合。"""

    def create_session(self, url):
        """创建并绑定新的共享 session，同时更新基础访问地址。"""
        self.session = requests.Session()
        self.base_url = url
        logger.info(f"base_url_config:{self.base_url}")
        return self.session
