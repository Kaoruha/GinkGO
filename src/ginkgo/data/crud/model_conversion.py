# Upstream: 各CRUD类(作为Mixin混入), 业务实体对象
# Downstream: ModelCRUDMapping, pandas
# Role: Model转换Mixin，提供to_dataframe()方法，通过ModelCRUDMapping将数据库Model转为业务对象






"""
Model转换功能模块

提供Model类的转换能力，通过ModelCRUDMapping找到对应的CRUD类进行转换
"""

import pandas as pd
from typing import List, Optional, Generic, TypeVar
from ginkgo.data.crud.model_crud_mapping import ModelCRUDMapping

T = TypeVar("T")


class ModelConversion:
    """
    Model转换Mixin

    提供to_dataframe()方法，通过ModelCRUDMapping找到对应的CRUD类进行转换。
    注：to_entity() 懒转换路径已在 ADR-010 Phase 4 Task 4.1 删除（斩断
    _convert_to_business_objects hook 的调用方，改走 Mapper 层）。
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

        支持多种模型类型：
        - SQLAlchemy 模型：使用 __dict__ 属性
        - Pydantic 模型：使用 model_dump() 方法

        Returns:
            基础的DataFrame（无enum转换）
        """
        # 检测是否为 Pydantic 模型
        if hasattr(self, 'model_dump'):
            data = [self.model_dump()]
        else:
            data = [self.__dict__]

        df = pd.DataFrame(data)
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

    def first(self) -> Optional[T]:
        """获取第一个Model，空列表返回None。"""
        return self[0] if self else None

    def head(self, n: int = 5) -> 'ModelList[T]':
        """
        获取前n个元素，模拟DataFrame.head()。

        Args:
            n: 返回的元素数量

        Returns:
            ModelList: 包含前n个元素的新ModelList
        """
        return ModelList(self[:n], self._crud_instance)

    def __repr__(self):
        model_type = type(self[0]).__name__ if self else "No models"
        return f"ModelList(count={len(self)}, type={model_type})"