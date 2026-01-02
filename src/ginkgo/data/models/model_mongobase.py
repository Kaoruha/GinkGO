# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: MongoDB Collections, CRUD Operations
# Role: MMongoBase MongoDB文档模型基类继承MBase和Pydantic BaseModel提供uuid/meta/desc/create_at/update_at/is_del/source字段


import uuid
import datetime
import pandas as pd
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator
from ginkgo.data.models.model_base import MBase
from ginkgo.enums import SOURCE_TYPES


class MMongoBase(BaseModel, MBase):
    """
    MongoDB 文档模型基类

    继承 Pydantic BaseModel 和 MBase，提供所有 MongoDB 文档共享的字段：
    - uuid: 主键，文档唯一标识
    - 元数据字段：meta, desc, create_at, update_at, is_del, source
    - __collection__: MongoDB 集合名称

    Attributes:
        uuid: 文档唯一标识（32位十六进制字符串）
        meta: 元数据（JSON字符串，默认"{}"）
        desc: 描述信息
        create_at: 创建时间
        update_at: 更新时间
        is_del: 软删除标记
        source: 数据来源枚举值

    Examples:
        >>> class MyDocument(MMongoBase):
        ...     __collection__ = "my_collection"
        ...     name: str
        ...
        >>> doc = MyDocument(name="test")
        >>> doc.uuid  # 自动生成UUID
        """

    # 集合名称（子类必须重写）
    __collection__: str = "mongobase_default"

    # 基础ID字段
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4().hex))

    # 元数据字段
    meta: str = Field(default="{}", description="元数据JSON字符串")
    desc: str = Field(default="This man is lazy, there is no description.", description="描述信息")
    create_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        description="创建时间"
    )
    update_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        description="更新时间"
    )
    is_del: bool = Field(default=False, description="软删除标记")
    source: int = Field(default=-1, description="数据来源枚举值")

    class Config:
        """Pydantic 配置"""
        from_attributes = True  # 支持从 ORM 对象创建
        use_enum_values = True  # 使用枚举值而非枚举对象

    @classmethod
    def get_collection_name(cls) -> str:
        """
        获取集合名称

        Returns:
            str: MongoDB 集合名称

        Raises:
            ValueError: 如果子类未定义 __collection__
        """
        if cls.__collection__ == "mongobase_default" and cls.__name__ != "MMongoBase":
            raise ValueError(f"{cls.__name__} must override __collection__ attribute")
        return cls.__collection__

    def get_source_enum(self) -> SOURCE_TYPES:
        """
        将数据库中的 source 整数值转换为枚举类型

        Returns:
            SOURCE_TYPES: 数据来源枚举
        """
        return SOURCE_TYPES.from_int(self.source)

    def set_source(self, source: Any) -> None:
        """
        设置 source 字段，支持枚举/整数/字符串输入

        Args:
            source: SOURCE_TYPES 枚举、整数或字符串

        Examples:
            >>> doc.set_source(SOURCE_TYPES.TUSHARE)
            >>> doc.set_source(0)  # 整数
            >>> doc.set_source("tushare")  # 字符串
        """
        try:
            # 先尝试 validate_input (处理枚举和整数)
            result = SOURCE_TYPES.validate_input(source)
            if result is not None:
                self.source = result
                return

            # 如果是字符串，尝试 enum_convert
            if isinstance(source, str):
                enum_result = SOURCE_TYPES.enum_convert(source)
                if enum_result is not None:
                    self.source = enum_result.value
                    return

            # 无法转换，设置为默认值 -1
            self.source = -1
        except Exception:
            self.source = -1

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: int) -> int:
        """
        验证 source 字段值

        Args:
            v: source 值

        Returns:
            int: 验证后的 source 值
        """
        if v is None:
            return -1
        # 确保是整数类型
        return int(v)

    def delete(self, **kwargs) -> None:
        """软删除：标记 is_del 为 True"""
        self.is_del = True
        self.update_at = datetime.datetime.now()

    def cancel_delete(self, **kwargs) -> None:
        """取消软删除：标记 is_del 为 False"""
        self.is_del = False
        self.update_at = datetime.datetime.now()

    def update(self, *args, **kwargs) -> None:
        """
        更新模型数据 - 支持 MySQL 一致的接口

        支持三种调用方式：
        1. 仅关键字参数：update(name="New", description="Desc")
        2. 字符串位置参数：update("New Name")
        3. pandas Series 位置参数：update(pd.Series(...))

        Args:
            *args: 位置参数（可选，用于派发）
            **kwargs: 关键字参数

        Raises:
            NotImplementedError: 如果子类未实现对应的更新方法

        Examples:
            >>> # 方式1：仅关键字参数（推荐）
            >>> doc.update(name="New Name", description="New Desc")
            >>>
            >>> # 方式2：字符串参数
            >>> doc.update("New Name")
            >>>
            >>> # 方式3：pandas Series
            >>> doc.update(pd.Series({"name": "New Name"}))
        """
        # 处理仅关键字参数的情况（没有位置参数时）
        if not args and kwargs:
            self._update_from_kwargs(**kwargs)
        elif args:
            # 有位置参数，使用类型派发
            self._update_dispatch(args[0], *args[1:], **kwargs)
        else:
            raise NotImplementedError("Unsupported type for update")

    def _update_dispatch(self, first_arg, *args, **kwargs) -> None:
        """
        内部派发方法 - 根据第一个参数类型分发

        子类可以重写此方法以添加更多类型的支持
        """
        if isinstance(first_arg, str):
            self._update_from_str(first_arg, *args, **kwargs)
        elif isinstance(first_arg, pd.Series):
            self._update_from_series(first_arg, *args, **kwargs)
        else:
            raise NotImplementedError(f"Unsupported type for update: {type(first_arg)}")

    def _update_from_kwargs(self, **kwargs) -> None:
        """
        从关键字参数更新模型

        子类应重写此方法以实现具体的字段更新逻辑
        默认实现：更新所有匹配的属性
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.update_at = datetime.datetime.now()

    def _update_from_str(self, data: str, *args, **kwargs) -> None:
        """
        从字符串参数更新模型

        子类应重写此方法以实现具体的字符串更新逻辑
        """
        raise NotImplementedError("Subclass must implement _update_from_str()")

    def _update_from_series(self, df: pd.Series, *args, **kwargs) -> None:
        """
        从 pandas Series 更新模型

        子类应重写此方法以实现具体的 Series 更新逻辑
        """
        raise NotImplementedError("Subclass must implement _update_from_series()")

    def model_dump_for_mongo(self) -> Dict[str, Any]:
        """
        导出为适合 MongoDB 存储的字典

        类似于 model_dump()，但处理特殊类型：
        - datetime 转换为 ISO 格式字符串
        - 枚举转换为整数值

        Returns:
            Dict[str, Any]: 适合 MongoDB 存储的字典

        Examples:
            >>> doc = MyDocument(name="test")
            >>> mongo_dict = doc.model_dump_for_mongo()
            >>> # mongo_dict['create_at'] 是 ISO 格式字符串
        """
        data = self.model_dump(exclude_none=True, mode='json')
        # 处理 datetime 字段
        for key, value in data.items():
            if isinstance(value, datetime.datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> 'MMongoBase':
        """
        从 MongoDB 文档创建模型实例

        Args:
            data: MongoDB 文档字典

        Returns:
            MMongoBase: 模型实例

        Examples:
            >>> mongo_doc = {"uuid": "abc123", "name": "test", ...}
            >>> model = MyDocument.from_mongo(mongo_doc)
        """
        # 处理 datetime 字段
        if 'create_at' in data and isinstance(data['create_at'], str):
            data['create_at'] = datetime.datetime.fromisoformat(data['create_at'])
        if 'update_at' in data and isinstance(data['update_at'], str):
            data['update_at'] = datetime.datetime.fromisoformat(data['update_at'])

        return cls(**data)

    def __repr__(self) -> str:
        """友好的字符串表示"""
        collection = self.get_collection_name()
        return f"<MMongoBase({collection}) uuid={self.uuid[:8]}... is_del={self.is_del}>"
