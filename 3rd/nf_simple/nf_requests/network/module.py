"""network 一级模块。"""

from .interface import InterfaceFeature
from .zone import ZoneFeature
from .arp import ArpFeature
from .mac import MacFeature
from .dhcp import DhcpFeature
from .dns import DnsFeature
from .route import RouteFeature
from .link_detection import LinkDetectionFeature
from .dynamic_route import DynamicRouteFeature


class NetworkModule:
    """聚合二级功能对象。"""

    interface: InterfaceFeature
    zone: ZoneFeature
    arp: ArpFeature
    mac: MacFeature
    dhcp: DhcpFeature
    dns: DnsFeature
    route: RouteFeature
    link_detection: LinkDetectionFeature
    dynamic_route: DynamicRouteFeature

    def __init__(self, context):
        self.interface = InterfaceFeature(context)
        self.zone = ZoneFeature(context)
        self.arp = ArpFeature(context)
        self.mac = MacFeature(context)
        self.dhcp = DhcpFeature(context)
        self.dns = DnsFeature(context)
        self.route = RouteFeature(context)
        self.link_detection = LinkDetectionFeature(context)
        self.dynamic_route = DynamicRouteFeature(context)
