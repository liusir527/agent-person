"""system 一级模块。"""

from .backup_restore import BackupRestoreFeature
from .system_upgrade import SystemUpgradeFeature
from .snmp import SnmpFeature
from .north_api import NorthApiFeature
from .system_config import SystemConfig
from .sd_wan import SdWanFeature
from .init_login_admin_cert_import import InitLoginCertImportFeature
from .session_packet_filter import SessionPacketFilterFeature
from .connectivity import ConnectivityFeature


class SystemModule:
    """weboper系统"""

    backup_restore: BackupRestoreFeature
    snmp: SnmpFeature
    north_api: NorthApiFeature
    sysconfig: SystemConfig
    sd_wan: SdWanFeature
    init_login_cert_import: InitLoginCertImportFeature
    system_upgrade: SystemUpgradeFeature
    session_packet_filter: SessionPacketFilterFeature
    connectivity: ConnectivityFeature

    def __init__(self, context):
        self.backup_restore = BackupRestoreFeature(context)
        self.snmp = SnmpFeature(context)
        self.north_api = NorthApiFeature(context)
        self.sysconfig = SystemConfig(context)
        self.sd_wan = SdWanFeature(context)
        self.init_login_cert_import = InitLoginCertImportFeature(context)
        self.system_upgrade = SystemUpgradeFeature(context)
        self.session_packet_filter = SessionPacketFilterFeature(context)
        self.connectivity = ConnectivityFeature(context)
