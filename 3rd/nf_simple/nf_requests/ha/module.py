"""ha 一级模块。"""

from .ha_global import HaGlobalFeature
from .ha_sync import HaSyncFeature
from .vrrp_monitor import VrrpMonitorFeature
from .ha_instance_track import HaInstanceTrackFeature


class HaModule:
    """聚合二级功能对象。"""

    ha_global: HaGlobalFeature
    ha_sync: HaSyncFeature
    vrrp_monitor: VrrpMonitorFeature
    ha_instance_track: HaInstanceTrackFeature

    def __init__(self, context):
        self.ha_global = HaGlobalFeature(context)
        self.ha_sync = HaSyncFeature(context)
        self.vrrp_monitor = VrrpMonitorFeature(context)
        self.ha_instance_track = HaInstanceTrackFeature(context)
