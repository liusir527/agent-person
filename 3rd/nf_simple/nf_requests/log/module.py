"""log 一级模块。"""

from .url_filter_log import UrlFilterLogFeature
from .ddos_log import DdosLogFeature
from .ha_log import HaLogFeature
from .firewall_log import FirewallLogFeature
from .antivirus_log import AntivirusLogFeature
from .ips_log import IpsLogFeature
from .waf_log import WafLogFeature
from .email_security_log import EmailSecurityLogFeature
from .obm_log import ObmLogFeature
from .sdm_log import SdmLogFeature
from .audit_log import AuditLogFeature
from .running_log import RunningLogFeature
from .network_running_log import NetworkRunningLogFeature


class LogModule:
    """聚合二级功能对象。"""

    url_filter_log: UrlFilterLogFeature
    ddos_log: DdosLogFeature
    ha_log: HaLogFeature
    firewall_log: FirewallLogFeature
    antivirus_log: AntivirusLogFeature
    ips_log: IpsLogFeature
    waf_log: WafLogFeature
    email_security_log: EmailSecurityLogFeature
    obm_log: ObmLogFeature
    sdm_log: SdmLogFeature
    audit_log: AuditLogFeature
    running_log: RunningLogFeature
    network_running_log: NetworkRunningLogFeature

    def __init__(self, context):
        self.url_filter_log = UrlFilterLogFeature(context)
        self.ddos_log = DdosLogFeature(context)
        self.ha_log = HaLogFeature(context)
        self.firewall_log = FirewallLogFeature(context)
        self.antivirus_log = AntivirusLogFeature(context)
        self.ips_log = IpsLogFeature(context)
        self.waf_log = WafLogFeature(context)
        self.email_security_log = EmailSecurityLogFeature(context)
        self.obm_log = ObmLogFeature(context)
        self.sdm_log = SdmLogFeature(context)
        self.audit_log = AuditLogFeature(context)
        self.running_log = RunningLogFeature(context)
        self.network_running_log = NetworkRunningLogFeature(context)
