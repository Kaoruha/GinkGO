from ginkgo.backtest.strategy.risk_managements.base_risk import BaseRiskManagement


class NoRiskManagement(BaseRiskManagement):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "norisk", *args, **kwargs):
        super(NoRiskManagement, self).__init__(name, *args, **kwargs)
