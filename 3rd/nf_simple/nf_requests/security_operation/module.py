"""operation 一级模块。"""

from .soc import SocFeature
from .threat_defense import ThreatDefenseFeature




class Security_OperationModule:
    """安全运营模块。"""

    soc: SocFeature
    threat_defense: ThreatDefenseFeature

    def __init__(self, context):
        self.soc = SocFeature(context)
        self.threat_defense = ThreatDefenseFeature(context)
        
        
