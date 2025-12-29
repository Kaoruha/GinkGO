# Upstream: Portfolio Manager (测试对比使用无风控场景)、RiskBase (继承提供风控基础能力)
# Downstream: 无额外依赖空实现风控接口
# Role: No Risk风控继承BaseRiskManagement实现NoRiskManagement无风险管理






from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement


class NoRiskManagement(BaseRiskManagement):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "norisk", *args, **kwargs):
        super(NoRiskManagement, self).__init__(name, *args, **kwargs)
