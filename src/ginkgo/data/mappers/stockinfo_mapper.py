"""StockInfoMapper — StockInfo Entity ↔ MStockInfo ORM 转换（ADR-010）。

承接原 StockInfo.to_model / StockInfo.from_model 内嵌逻辑
（entities/stockinfo.py:186-227）。无 StockInfoDTO（项目未定义），故只提供
to_model / from_model / from_models 三方法。

VO 动态表：to_model 多 model_class 形参，方法体内 model_class(...) 构造。
from_model market/currency int→enum 转换在前（避免 StockInfo.__init__ 严格
校验 enum 报错），还原 uuid（原码即如此，无丢失）。

已知问题（留 Task 1.6 统一评估，不擅修）：
- 原码 to_model 未传 market（stockinfo.py:215-227），model.market 走
  MStockInfo.__init__ 默认 CHINA.value 而非 entity.market。roundtrip 时
  非 CHINA entity 的 market 会丢失（from_model 转回 CHINA）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MStockInfo
from ginkgo.entities import StockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES


class StockInfoMapper:
    """StockInfo 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: StockInfo, model_class=MStockInfo) -> MStockInfo:
        """Entity → ORM。model_class 形参保留（VO 动态表选择）。

        忠实原码：model_class(...) 直接构造。**未传 market**（原码即如此，
        stockinfo.py:215-227）——model.market 走 MStockInfo.__init__ 默认
        CHINA.value。已知 bug，留 Task 1.6。
        """
        return model_class(
            code=entity.code,
            code_name=entity.code_name,
            industry=entity.industry,
            currency=entity.currency,
            list_date=entity.list_date,
            delist_date=entity.delist_date,
            uuid=entity.uuid,
        )

    @staticmethod
    def from_model(model: MStockInfo) -> StockInfo:
        """ORM → Entity。market/currency int→enum + 还原 uuid（原码即如此，无丢失）。

        忠实原码：market/currency 先做 int/str→enum 转换（避免 StockInfo.__init__
        严格 enum 校验报错），再传构造器。其余字段经 getattr 兜底默认。
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
    def from_models(models) -> List[StockInfo]:
        return [StockInfoMapper.from_model(m) for m in models]
