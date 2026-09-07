"""policy 一级模块。"""

from .url_filter import UrlFilterFeature
from .firewall import FirewallFeature
from .policy_group import PolicyGroupFeature
from .black_white_list import BlackWhiteListFeature
from .url_black_white_list import UrlBlackWhiteListFeature
from .nat import NatFeature
from .nat64 import Nat64Feature
from .nat66 import Nat66Feature
from .ipmac import IpmacFeature
from .user_auth import UserAuthFeature
from .bandwidth_policy import BandwidthPolicyFeature
from .bandwidth_channel import BandwidthChannelFeature
from .bandwidth_wire import BandwidthWireFeature


class PolicyModule:
    """聚合二级功能对象。"""

    url_filter: UrlFilterFeature
    firewall: FirewallFeature
    policy_group: PolicyGroupFeature
    black_white_list: BlackWhiteListFeature
    url_black_white_list: UrlBlackWhiteListFeature
    nat: NatFeature
    nat64: Nat64Feature
    nat66: Nat66Feature
    ipmac: IpmacFeature
    user_auth: UserAuthFeature
    bandwidth_policy: BandwidthPolicyFeature
    bandwidth_channel: BandwidthChannelFeature
    bandwidth_wire: BandwidthWireFeature

    def __init__(self, context):
        self.url_filter = UrlFilterFeature(context)
        self.firewall = FirewallFeature(context)
        self.policy_group = PolicyGroupFeature(context)
        self.black_white_list = BlackWhiteListFeature(context)
        self.url_black_white_list = UrlBlackWhiteListFeature(context)
        self.nat = NatFeature(context)
        self.nat64 = Nat64Feature(context)
        self.nat66 = Nat66Feature(context)
        self.ipmac = IpmacFeature(context)
        self.user_auth = UserAuthFeature(context)
        self.bandwidth_policy = BandwidthPolicyFeature(context)
        self.bandwidth_channel = BandwidthChannelFeature(context)
        self.bandwidth_wire = BandwidthWireFeature(context)
