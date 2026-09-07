"""object 一级模块。"""

from .network_object import NetworkObjectFeature
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


class ObjectModule:
    """聚合二级功能对象。"""

    network_object: NetworkObjectFeature
    server: ServerObjectFeature
    app: AppObjectFeature
    time: TimeObjectFeature
    user: UserObjectFeature
    cert: CertObjectFeature
    keyword: KeywordObjectFeature
    location: LocationObjectFeature
    antivirus: AntivirusObjectFeature
    ips: IpsObjectFeature
    url: UrlObjectFeature
    scm: ScmObjectFeature
    waf: WafObjectFeature
    vul: VulObjectFeature

    def __init__(self, context):
        # 向后兼容 Facade — 包含所有拆分子模块的方法
        self.network_object = NetworkObjectFeature(context)

        # 独立 Feature 属性，便于按子模块直接访问
        self.server = ServerObjectFeature(context)
        self.app = AppObjectFeature(context)
        self.time = TimeObjectFeature(context)
        self.user = UserObjectFeature(context)
        self.cert = CertObjectFeature(context)
        self.keyword = KeywordObjectFeature(context)
        self.location = LocationObjectFeature(context)
        self.antivirus = AntivirusObjectFeature(context)
        self.ips = IpsObjectFeature(context)
        self.url = UrlObjectFeature(context)
        self.scm = ScmObjectFeature(context)
        self.waf = WafObjectFeature(context)
        self.vul = VulObjectFeature(context)
