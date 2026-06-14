"""
Data Mappers — 转换收敛层（ADR-010）

每个 Mapper 类负责 Entity/ORM/DTO 三态互转，五方法矩阵：
from_model / to_model / from_dto / to_dto / model_to_dto。

铁律：不 import CRUD（独立于持久层）；不含 to_dataframe（DF 出口留 CRUD）。
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

__all__ = [
    "dataframe_to_adjustfactor_models",
    "row_to_stockinfo_upsert_dict",
    "dataframe_to_stockinfo_upsert_list",
    "dataframe_to_bar_models",
    "dataframe_to_bar_entities",
    "dataframe_to_tick_entities",
    "dataframe_to_tick_models",
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
]
