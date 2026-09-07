"""vpn 一级模块。"""

from .gre import GreFeature
from .ipsec import IpsecFeature
from .ssl_vpn_global import SslVpnGlobalFeature
from .ssl_vpn_link import SslVpnLinkFeature
from .ssl_vpn_status_log import SslVpnStatusLogFeature
from .ssl_vpn_resource import SslVpnResourceFeature
from .ssl_vpn_resource_group import SslVpnResourceGroupFeature
from .ssl_vpn_auth_access import SslVpnAuthAccessFeature
from .global_association import GlobalAssociationFeature


class VpnModule:
    """聚合二级功能对象。"""

    gre: GreFeature
    ipsec: IpsecFeature
    ssl_vpn_global: SslVpnGlobalFeature
    ssl_vpn_link: SslVpnLinkFeature
    ssl_vpn_status_log: SslVpnStatusLogFeature
    ssl_vpn_resource: SslVpnResourceFeature
    ssl_vpn_resource_group: SslVpnResourceGroupFeature
    ssl_vpn_auth_access: SslVpnAuthAccessFeature
    global_association: GlobalAssociationFeature

    def __init__(self, context):
        self.gre = GreFeature(context)
        self.ipsec = IpsecFeature(context)
        self.ssl_vpn_global = SslVpnGlobalFeature(context)
        self.ssl_vpn_link = SslVpnLinkFeature(context)
        self.ssl_vpn_status_log = SslVpnStatusLogFeature(context)
        self.ssl_vpn_resource = SslVpnResourceFeature(context)
        self.ssl_vpn_resource_group = SslVpnResourceGroupFeature(context)
        self.ssl_vpn_auth_access = SslVpnAuthAccessFeature(context)
        self.global_association = GlobalAssociationFeature(context)
