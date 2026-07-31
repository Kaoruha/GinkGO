# Upstream: All Data Models (MBar/MStockInfo/MTick等继承to_dataframe方法)
# Downstream: None (基础工具类)
# Role: MBase数据模型基类定义to_dataframe()通用方法将模型对象转换为pandas DataFrame遍历公开属性排除私有/方法/枚举

import pandas as pd

from ginkgo.libs.data.dataframe import to_dataframe as _to_dataframe


class MBase:
    def to_dataframe(self, *args, **kwargs) -> pd.DataFrame:
        return _to_dataframe(self)
