"""StockInfoMapper — StockInfo Entity ↔ MStockInfo ORM 转换（ADR-010 / ADR-029）。

承接原 StockInfo.to_model / StockInfo.from_model 内嵌逻辑
（entities/stockinfo.py:186-227）+ stock_info_crud._convert_input_item override
字段集（market/source/uuid None-coalesce，本 Task 收敛到 mapper，删 override）。

VO 动态表：entity_to_model 多 model_class 形参，方法体内 model_class(...) 构造。
from_model market/currency int→enum 转换在前（避免 StockInfo.__init__ 严格
校验 enum 报错），还原 uuid。

**ADR-029 Task 3 修复点**：原 mapper 未传 market（自承丢失 bug，
entities/stockinfo.py:215-227）→ roundtrip 非 CHINA entity 的 market 静默回退
到 CHINA。现对齐 stock_info_crud._convert_input_item:159-169 override 字段集，
全字段直传 + source side-channel + uuid 空→None。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MStockInfo
from ginkgo.entities import StockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES, SOURCE_TYPES


class StockInfoMapper:
    """StockInfo 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def entity_to_model(entity: StockInfo, model_class=MStockInfo) -> MStockInfo:
        """Entity → ORM。model_class 形参保留（VO 动态表选择）。

        ADR-029 Task 3：对齐 stock_info_crud._convert_input_item override 字段集，
        全字段直传：
        - **market 修复**：原码漏传，model.market 走 MStockInfo.__init__ 默认
          CHINA.value；现传 entity.market，全枚举 roundtrip 保真。
        - source side-channel：StockInfo 是 ValueObject（无 Base.source property），
          service 经 `entity._source = SOURCE_TYPES.X` side-channel 写入
          （stockinfo_service:166）；mapper 对齐 `getattr(entity, '_source', TUSHARE)`
          读取（原 CRUD override 同款）。
        - uuid None-coalesce：entity 默认 uuid="" → 传 None 让 ORM default 生成
          （原 CRUD override:168 同款）。
        """
        source = getattr(entity, '_source', SOURCE_TYPES.TUSHARE)
        return model_class(
            code=entity.code,
            code_name=entity.code_name,
            industry=entity.industry,
            market=entity.market,
            currency=entity.currency,
            list_date=entity.list_date,
            delist_date=entity.delist_date,
            source=source,
            uuid=entity.uuid if entity.uuid else None,
        )

    @staticmethod
    def model_to_entity(model: MStockInfo) -> StockInfo:
        """ORM → Entity。market/currency int→enum + 还原 uuid。

        market/currency 先做 int/str→enum 转换（避免 StockInfo.__init__ 严格
        enum 校验报错），再传构造器。其余字段经 getattr 兜底默认。
        """
        if not isinstance(model, MStockInfo):
            raise TypeError(f"Expected MStockInfo instance, got {type(model).__name__}")

        # 处理枚举字段的int到enum转换（忠实原码 stockinfo.py:189-200）
        market_value = getattr(model, 'market', MARKET_TYPES.CHINA)
        if isinstance(market_value, (int, str)):
            market = MARKET_TYPES(market_value)
        else:
            market = market_value

        currency_value = getattr(model, 'currency', CURRENCY_TYPES.CNY)
        if isinstance(currency_value, (int, str)):
            currency = CURRENCY_TYPES(currency_value)
        else:
            currency = currency_value

        return StockInfo(
            code=getattr(model, 'code', ''),
            code_name=getattr(model, 'code_name', ''),
            industry=getattr(model, 'industry', ''),
            market=market,
            currency=currency,
            list_date=getattr(model, 'list_date', '1990-01-01'),
            delist_date=getattr(model, 'delist_date', '2099-12-31'),
            uuid=getattr(model, 'uuid', ''),
        )

    @staticmethod
    def models_to_entities(models) -> List[StockInfo]:
        return [StockInfoMapper.model_to_entity(m) for m in models]
