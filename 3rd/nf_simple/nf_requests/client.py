"""NF API 组合式客户端入口。"""

from __future__ import annotations

from typing import TYPE_CHECKING
try:
    from nf_requests.nflib.Log import logger
except ModuleNotFoundError:
    from .nflib.Log import logger
import requests


if TYPE_CHECKING:
    from .basic import BasicModule
    from .ha import HaModule
    from .log import LogModule
    from .network import NetworkModule
    from .object import ObjectModule
    from .policy import PolicyModule
    from .security import SecurityModule
    from .security_operation import Security_OperationModule
    from .system import SystemModule
    from .vpn import VpnModule


class NFRequests:
    basic: BasicModule
    ha: HaModule
    log: LogModule
    network: NetworkModule
    object: ObjectModule
    security_operation: Security_OperationModule
    policy: PolicyModule
    security: SecurityModule
    system: SystemModule
    vpn: VpnModule
    """NF API 总入口与二级功能类共享基类。"""

    def __init__(self, base_url=None, session=None, mount_modules=True):
        self._parent = None

        if isinstance(base_url, NFRequests):
            self._parent = base_url
            return
        requests.packages.urllib3.disable_warnings()
        self._session = session or requests.Session()
        self._base_url = base_url 
        logger.info(self._base_url)

        if mount_modules:
            self._mount_modules()

    def _mount_modules(self):
        """挂载一级模块，保持 ``nf.xxx.yyy`` 三级调用结构。"""
        from .basic import BasicModule
        from .ha import HaModule
        from .log import LogModule
        from .network import NetworkModule
        from .object import ObjectModule
        from .security_operation import Security_OperationModule
        from .policy import PolicyModule
        from .security import SecurityModule
        from .system import SystemModule
        from .vpn import VpnModule

        self.basic = BasicModule(self)  #weboper的基础模块
        self.ha = HaModule(self)   #HA模块
        self.log = LogModule(self)  #日志模块
        self.network = NetworkModule(self) #网络模块
        self.object = ObjectModule(self)  #对象模块
        self.security_operation = Security_OperationModule(self)  #安全运营模块
        self.policy = PolicyModule(self)
        self.security = SecurityModule(self)
        self.system = SystemModule(self)
        self.vpn = VpnModule(self)


    @property
    def session(self):
        """返回当前对象共享的 requests Session。"""
        if self._parent is not None:
            return self._parent.session
        return self._session

    @session.setter
    def session(self, session):
        if self._parent is not None:
            self._parent.session = session
        else:
            self._session = session

    @property
    def base_url(self):
        """返回当前对象共享的基础 URL。"""
        if self._parent is not None:
            return self._parent.base_url
        return self._base_url

    @base_url.setter
    def base_url(self, base_url):
        if self._parent is not None:
            self._parent.base_url = base_url
        else:
            self._base_url = base_url

    def set_base_url(self, base_url):
        """更新当前客户端基础 URL。"""
        self.base_url = base_url
        return self

    def set_session(self, session):
        """更新当前客户端 requests Session。"""
        self.session = session
        return self
