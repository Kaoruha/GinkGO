from ginkgo.backtest.selectors.base_selector import BaseSelector
from ginkgo.data.ginkgo_data import GDATA

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
        super(CNAllSelector, self).__init__(name, *args, **kwargs)
        self._interested = []

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        if len(self._interested) > 0:
            return self._interested

        df = GDATA.get_stock_info_df()
        self._interested = df["code"].tolist()
        return self._interested
