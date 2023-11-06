from ginkgo.backtest.risk_managements.base_risk import BaseRiskManagement


class NoRiskManagement(BaseRiskManagement):
    __abstract__ = False

    def __init__(self, name: str = "norisk", *args, **kwargs):
        super(NoRiskManagement, self).__init__(name, *args, **kwargs)
