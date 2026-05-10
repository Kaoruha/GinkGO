# Upstream: EngineAssemblyService, PortfolioBase
# Downstream: BaseSelector, ensure_list, GLOG
# Role: 固定选股器，通过ensure_list支持列表/JSON/逗号分隔格式的固定股票池配置
# 注意: 固定选股依赖后视选股（已知哪只股票表现好），仅适用于回测验证，
#       实盘策略应使用动态选股器（如 MomentumSelector、MultiParamsSelector）。

import json
from typing import List, Union
from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.libs import GLOG
from ginkgo.libs.utils import ensure_list


class FixedSelector(BaseSelector):
    """固定选股器 - 锁定指定股票代码，一般仅在回测测试时使用。

    注意: 使用 FixedSelector 意味着你已经知道哪只股票会涨（后视偏差），
    不适用于实盘交易。实盘请使用动态选股器。
    """

    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "FixedSelector", codes: Union[str, List[str]] = "", *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)
        self._interested = ensure_list(codes)

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        r = self._interested
        GLOG.DEBUG(f"Selector:{self.name} pick {r}.")
        return r
