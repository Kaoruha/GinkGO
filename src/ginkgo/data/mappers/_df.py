"""Model 列表 → DataFrame 转换（ADR-029 §Decision 9）。

``models_to_dataframe`` 是 CRUD 直接返 list（ADR-029 §Decision 9）后的独立 DF 出口：
读首个 model 的 ``__table__.columns`` 反射 enum 映射（与 BaseCRUD._get_enum_mappings
同源），原地修正 enum 字段后构造 DataFrame。

铁律（与 mapper 包一致）：不 import CRUD，不经 crud 实例。enum 真值单源是
model 字段 ``info={'enum': XxxTypes}``（ADR c1）。

性能：与原 ``_Conversion._convert_models_to_dataframe`` 等价（enum 映射反射一次，
in-place setattr，dict copy + pd.DataFrame 一次构造）——回测热路径
（``bar_service.get_bars_df`` ~777/784）零回归。
"""

from typing import Any, List
import pandas as pd


def _get_enum_mappings_from_model(model: Any) -> dict:
    """从 model 实例反射 ``__table__.columns`` 取 enum 映射。

    与 ``BaseCRUD._get_enum_mappings`` 同源（ADR c1：真值下沉到字段 info）。
    CH(MClickBase)/MySQL(MMysqlBase) 同属 SA DeclarativeBase，反射通用；
    Mongo(MMongoBase) 走 Pydantic model_dump，不经此路径。
    """
    table = getattr(getattr(model, "__class__", None), "__table__", None)
    if table is None:
        return {}
    mappings: dict = {}
    for col in table.columns:
        enum_cls = (col.info or {}).get("enum")
        if enum_cls is not None:
            mappings[col.name] = enum_cls
    return mappings


def _safe_enum_convert(value: Any, enum_class: Any) -> Any:
    """Safe enum conversion（与 ``_Conversion._safe_enum_convert`` 同语义）。"""
    try:
        if value is None:
            return None
        return enum_class(value)
    except (ValueError, TypeError):
        return value


def models_to_dataframe(models: List[Any]) -> pd.DataFrame:
    """将 Model 列表转为 pandas DataFrame（enum 字段反射转换）。

    Args:
        models: Model 实例列表（CRUD.find/add_batch/replace 等返回的 list）。

    Returns:
        pandas DataFrame；空列表返 ``pd.DataFrame()``。enum 字段经
        ``__table__`` 反射读取的 ``info['enum']`` 转为 enum 实例（与原
        ``BaseCRUD._convert_models_to_dataframe`` 行为对齐）。

    Note:
        enum 转换是 **in-place** setattr（与原实现一致，零额外拷贝）。若调用方
        后续仍持有 model 实例并读取 enum 字段，会拿到 enum 实例而非原始 int——
        这是 ADR c1 之前就成立的行为，本函数保持不动。
    """
    if not models:
        return pd.DataFrame()

    # enum 映射只反射一次（首个 model；同列表内 model 同类）
    enum_mappings = _get_enum_mappings_from_model(models[0])

    # in-place 修正 enum 字段（与 _convert_models_to_dataframe 一致）
    if enum_mappings:
        for model in models:
            for column, enum_class in enum_mappings.items():
                if hasattr(model, column):
                    current = getattr(model, column)
                    converted = _safe_enum_convert(current, enum_class)
                    if converted is not None:
                        try:
                            setattr(model, column, converted)
                        except AttributeError:
                            # 只读属性（部分 entity）跳过
                            pass

    # 构造 DataFrame（与原实现一致：__dict__ copy + pop _sa_instance_state）
    data = []
    for model in models:
        model_dict = model.__dict__.copy()
        model_dict.pop("_sa_instance_state", None)
        data.append(model_dict)

    return pd.DataFrame(data)
