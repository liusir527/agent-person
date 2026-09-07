"""basic 一级模块。"""

from .session import SessionFeature
from .apply import ApplyFeature
from .auth import AuthFeature
from .account import AccountFeature


class BasicModule:
    """聚合二级功能对象。"""

    session: SessionFeature
    apply: ApplyFeature
    auth: AuthFeature
    account: AccountFeature

    def __init__(self, context):
        self.session = SessionFeature(context)
        self.apply = ApplyFeature(context)
        self.auth = AuthFeature(context)
        self.account = AccountFeature(context)
