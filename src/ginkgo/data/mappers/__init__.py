"""
Data Mappers — 转换收敛层（ADR-010 + ADR-025 + ADR-029 §Decision 9）

Entity Mapper (ADR-010) 每类负责 Entity/ORM/DTO 三态互转，五方法矩阵：
from_model / to_model / from_dto / to_dto / model_to_dto。

CacheMapper (ADR-025 第④步) 是 Redis IO 边界 wire↔DTO 转换，非 Entity 三态互转，
故独立于上述五方法矩阵（encode/decode + β 运行期校验）。

``models_to_dataframe`` (ADR-029 §Decision 9) 是 CRUD 直接返 list 后的
独立 DF 出口，经 ``__table__`` 反射读 enum，不依赖 crud 实例。

铁律：不 import CRUD（独立于持久层）。
套C（外部数据源 DataFrame→ORM 入站）见本包 _legacy.py。
"""
from ginkgo.data.mappers._legacy import (
    dataframe_to_adjustfactor_models,
    row_to_stockinfo_upsert_dict,
    dataframe_to_stockinfo_upsert_list,
    dataframe_to_bar_models,
    dataframe_to_bar_entities,
    dataframe_to_tick_entities,
    dataframe_to_tick_models,
)
from ginkgo.data.mappers._df import models_to_dataframe
from ginkgo.data.mappers.order_mapper import OrderMapper
from ginkgo.data.mappers.bar_mapper import BarMapper
from ginkgo.data.mappers.position_mapper import PositionMapper
from ginkgo.data.mappers.signal_mapper import SignalMapper
from ginkgo.data.mappers.adjustfactor_mapper import AdjustfactorMapper
from ginkgo.data.mappers.tradeday_mapper import TradeDayMapper
from ginkgo.data.mappers.capital_adjustment_mapper import CapitalAdjustmentMapper
from ginkgo.data.mappers.stockinfo_mapper import StockInfoMapper
from ginkgo.data.mappers.tick_mapper import TickMapper
from ginkgo.data.mappers.mapping_mapper import MappingMapper
from ginkgo.data.mappers.transfer_mapper import TransferMapper
from ginkgo.data.mappers.cache_mapper import CacheMapper, CacheEntry

__all__ = [
    "dataframe_to_adjustfactor_models",
    "row_to_stockinfo_upsert_dict",
    "dataframe_to_stockinfo_upsert_list",
    "dataframe_to_bar_models",
    "dataframe_to_bar_entities",
    "dataframe_to_tick_entities",
    "dataframe_to_tick_models",
    "models_to_dataframe",
    "OrderMapper",
    "BarMapper",
    "PositionMapper",
    "SignalMapper",
    "AdjustfactorMapper",
    "TradeDayMapper",
    "CapitalAdjustmentMapper",
    "StockInfoMapper",
    "TickMapper",
    "MappingMapper",
    "TransferMapper",
    "CacheMapper",
    "CacheEntry",
]
