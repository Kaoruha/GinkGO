# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, _data_feeder.stockinfo_service
# Role: 全A股选股器，从股票信息服务获取全部A股代码列表






from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.libs import GLOG

import datetime


class CNAllSelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "CNAllSelector",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name, *args, **kwargs)
        self._interested = []

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        if len(self._interested) > 0:
            return self._interested
        if self._data_feeder is None:
            GLOG.WARN(f"CNAllSelector({self.name}): data_feeder 未绑定，跳过选股。")
            return self._interested
        # #4608：走 _data_feeder 显式依赖，不再穿透 container
        result = self._data_feeder.get_stockinfos_df()
        if result.success and not result.data.empty:
            self._interested = result.data["code"].tolist()
        else:
            self._interested = []
        return self._interested
