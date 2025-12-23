from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector

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
        # 使用服务容器避免导入时的循环依赖问题
        from ginkgo.data.containers import container
        result = container.stockinfo_service().get()
        if result.success and hasattr(result.data, 'to_dataframe'):
            df = result.data.to_dataframe()
            self._interested = df["code"].tolist()
        else:
            self._interested = []
        return self._interested
