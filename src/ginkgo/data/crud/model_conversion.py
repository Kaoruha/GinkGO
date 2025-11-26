"""
Model转换功能模块

提供Model类的转换能力，通过ModelCRUDMapping找到对应的CRUD类进行转换
"""

import pandas as pd
from typing import Any, List, Optional, Callable, Generic, TypeVar
from ginkgo.libs import GLOG
from ginkgo.data.crud.model_crud_mapping import ModelCRUDMapping

T = TypeVar("T")


class ModelConversion:
    """
    Model转换Mixin

    提供to_dataframe()和to_business_object()方法
    通过ModelCRUDMapping找到对应的CRUD类进行转换
    """

    def to_dataframe(self) -> pd.DataFrame:
        """
        将单个Model转换为DataFrame

        Returns:
            pandas DataFrame with enum conversions applied
        """
        crud_instance = self.get_crud_instance()
        if crud_instance:
            return crud_instance._convert_models_to_dataframe([self])
        else:
            # 降级处理：基础的DataFrame转换
            return self._fallback_to_dataframe()

    def to_entity(self) -> Any:
        """
        将单个Model转换为业务实体对象

        Returns:
            Business entity instance with enum fields converted
        """
        crud_instance = self.get_crud_instance()
        if crud_instance:
            business_objs = crud_instance._convert_to_business_objects([self])
            return business_objs[0] if business_objs else None
        else:
            raise ValueError(f"No CRUD class registered for {type(self).__name__}")

    @classmethod
    def get_crud_instance(cls):
        """
        获取对应的CRUD实例

        Returns:
            CRUD实例或None
        """
        crud_class = ModelCRUDMapping.get_crud_class(cls)
        return crud_class() if crud_class else None

    def _fallback_to_dataframe(self) -> pd.DataFrame:
        """
        降级处理：当没有找到CRUD类时的基础DataFrame转换

        Returns:
            基础的DataFrame（无enum转换）
        """
        df = pd.DataFrame([self.__dict__])
        # 移除非数据列
        for col in ['_sa_instance_state']:
            if col in df.columns:
                df = df.drop(col, axis=1)
        return df


class ModelList(list, Generic[T]):
    """
    带转换功能的Model列表

    继承自list，支持所有列表操作，同时提供转换方法
    """

    def __init__(self, models: List[T], crud_instance):
        super().__init__(models)
        self._crud_instance = crud_instance
        self._cache = {}

    def to_dataframe(self) -> pd.DataFrame:
        """
        将Model列表转换为DataFrame

        Returns:
            pandas DataFrame with enum conversions applied
        """
        cache_key = 'dataframe'
        if cache_key not in self._cache:
            self._cache[cache_key] = self._crud_instance._convert_models_to_dataframe(self)
        return self._cache[cache_key]

    def to_entities(self) -> List[Any]:
        """
        将Model列表转换为业务实体对象

        Returns:
            List of business entity objects with enum fields converted
        """
        cache_key = 'entities'
        if cache_key not in self._cache:
            self._cache[cache_key] = self._crud_instance._convert_to_business_objects(self)
        return self._cache[cache_key]

    def first(self) -> Optional[T]:
        """获取第一个Model"""
        return self[0] if self else None

    def count(self) -> int:
        """获取Model数量"""
        return len(self)

    def filter(self, predicate: Callable[[T], bool]) -> 'ModelList[T]':
        """
        过滤Model列表

        Args:
            predicate: 过滤函数

        Returns:
            新的ModelList
        """
        filtered_models = [model for model in self if predicate(model)]
        return ModelList(filtered_models, self._crud_instance)

    def empty(self) -> bool:
        """
        检查ModelList是否为空

        提供与pandas DataFrame.empty()相同的接口

        Returns:
            bool: 如果列表为空返回True，否则返回False
        """
        return len(self) == 0

    def shape(self) -> tuple[int, int]:
        """
        获取ModelList的形状，模拟DataFrame.shape()

        Returns:
            tuple: (行数, 1) 格式的形状，与DataFrame兼容
        """
        return (len(self), 1)

    def head(self, n: int = 5) -> 'ModelList[T]':
        """
        获取前n个元素，模拟DataFrame.head()

        Args:
            n: 返回的元素数量

        Returns:
            ModelList: 包含前n个元素的新ModelList
        """
        return ModelList(self[:n], self._crud_instance)

    def tail(self, n: int = 5) -> 'ModelList[T]':
        """
        获取后n个元素，模拟DataFrame.tail()

        Args:
            n: 返回的元素数量

        Returns:
            ModelList: 包含后n个元素的新ModelList
        """
        return ModelList(self[-n:] if n > 0 else [], self._crud_instance)

    def __repr__(self):
        model_type = type(self[0]).__name__ if self else "No models"
        return f"ModelList(count={len(self)}, type={model_type})"