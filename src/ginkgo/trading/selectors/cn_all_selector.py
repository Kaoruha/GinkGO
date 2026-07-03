# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, container.stockinfo_service, container.bar_service
# Role: 全A股选股器，从股票信息服务获取全部A股代码列表，剔除 DB 无 bar 数据的 code（#5163）




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
        # 使用服务容器避免导入时的循环依赖问题
        from ginkgo.data.containers import container
        result = container.stockinfo_service().get_stockinfos_df()
        if result.success and not result.data.empty:
            market_codes = result.data["code"].tolist()
        else:
            market_codes = []

        # #5163: 批量预过滤——剔除 DB 中无 bar 数据的 code，避免 feeder 每日
        # 对全市场逐股 N+1 查询 + 逐日刷屏 WARN。get_available_codes 一次 distinct
        # 查询返回所有有 bar 的 code。
        if market_codes:
            market_set = set(market_codes)
            try:
                bar_result = container.bar_service().get_available_codes()
            except Exception as e:
                GLOG.WARN(
                    f"CNAllSelector: bar_service.get_available_codes failed ({e}), "
                    f"skip prefilter (fail-open, return all {len(market_set)} codes)"
                )
                bar_result = None

            if bar_result is not None and bar_result.success and bar_result.data:
                available = set(bar_result.data)
                filtered = [c for c in market_codes if c in available]
                dropped = len(market_set) - len(filtered)
                if dropped > 0:
                    GLOG.INFO(
                        f"CNAllSelector: prefilter dropped {dropped}/{len(market_set)} "
                        f"codes without bar data, {len(filtered)} remaining"
                    )
                self._interested = filtered
            else:
                # 预过滤失败/空 → fail-open，返回全市场（不阻断回测）
                self._interested = market_codes
        else:
            self._interested = []
        return self._interested
