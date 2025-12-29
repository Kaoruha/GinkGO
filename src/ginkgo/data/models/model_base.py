# Upstream: All Data Models (MBar/MStockInfo/MTick等继承to_dataframe方法)
# Downstream: None (基础工具类)
# Role: MBase数据模型基类定义to_dataframe()通用方法将模型对象转换为pandas DataFrame遍历公开属性排除私有/方法/枚举






import pandas as pd
from types import FunctionType, MethodType
from sqlalchemy import Enum


class MBase:
    def to_dataframe(self, *args, **kwargs) -> pd.DataFrame:
        item = {}
        methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
        for param in self.__dir__():
            if param in methods:
                continue
            if param.startswith("_"):
                continue
            if isinstance(self.__getattribute__(param), MethodType):
                continue
            if isinstance(self.__getattribute__(param), FunctionType):
                continue

            if isinstance(self.__getattribute__(param), Enum):
                item[param] = self.__getattribute__(param).value
            else:
                item[param] = self.__getattribute__(param)

        df = pd.DataFrame.from_dict(item, orient="index").transpose()
        return df
