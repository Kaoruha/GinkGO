# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, container.stockinfo_service, ensure_list
# Role: 全A股选股器，默认从股票信息服务获取全部A股代码列表；
#       调用方可经 codes 形参（portfolio bind-component --param '1:[...]'）限定子集。






from typing import List, Union

from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.libs.utils import ensure_list

import datetime


class CNAllSelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "CNAllSelector",
        codes: Union[str, List[str]] = "",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(name, *args, **kwargs)
        # #4893: 尊重调用方传入的 codes（component_loader 按 index 排序后位置绑定：
        # index0=name, index1=codes）。codes 非空 → pick() 早返该子集，不查全库；
        # codes 空（默认 ""）→ pick() 回退查全 A 股（cn_all 本意，无参 fallback 实例化
        # 如 component_loader.py:337 / engine_assembly_service.py:311 依赖此行为）。
        # 区别于 FixedSelector：此处空 codes 是合法默认（=全市场），不发空告警。
        self._interested = ensure_list(codes)

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        if len(self._interested) > 0:
            return self._interested
        # 使用服务容器避免导入时的循环依赖问题
        from ginkgo.data.containers import container
        result = container.stockinfo_service().get_stockinfos_df()
        if result.success and not result.data.empty:
            self._interested = result.data["code"].tolist()
        else:
            self._interested = []
        return self._interested
