"""security 一级模块。"""

from .ddos_global import DdosGlobalFeature
from .ddos_protect import DdosProtectFeature
from .deformity import DeformityFeature
from .scan import ScanFeature
from .special_packet import SpecialPacketFeature
from .snooping import SnoopingFeature


class SecurityModule:
    """聚合二级功能对象。"""

    ddos_global: DdosGlobalFeature
    ddos_protect: DdosProtectFeature
    deformity: DeformityFeature
    scan: ScanFeature
    special_packet: SpecialPacketFeature
    snooping: SnoopingFeature

    def __init__(self, context):
        self.ddos_global = DdosGlobalFeature(context)
        self.ddos_protect = DdosProtectFeature(context)
        self.deformity = DeformityFeature(context)
        self.scan = ScanFeature(context)
        self.special_packet = SpecialPacketFeature(context)
        self.snooping = SnoopingFeature(context)
