"""TradeDayMapper — TradeDay Entity ↔ MTradeDay ORM 转换（ADR-010）。

承接原 TradeDay.to_model / TradeDay.from_model 内嵌逻辑
（entities/tradeday.py:142-175）。无 TradeDayDTO（项目未定义），故只提供
to_model / from_model / from_models 三方法。

VO 动态表：to_model 多 model_class 形参，方法体内 model_class(...) 构造。
to_model 忠实原码：model_class(market=..., is_open=..., timestamp=..., uuid=...)，
market 经 MTradeDay.__init__ validate_input 转 int。
from_model 还原 uuid + market int→enum（原码即如此，无丢失）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MTradeDay
from ginkgo.entities import TradeDay
from ginkgo.enums import MARKET_TYPES


class TradeDayMapper:
    """TradeDay 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: TradeDay, model_class=MTradeDay) -> MTradeDay:
        """Entity → ORM。model_class 形参保留（VO 动态表选择）。

        忠实原码：model_class(...) 直接构造，market enum 经 MTradeDay.__init__
        validate_input 转 int 存储。
        """
        return model_class(
            market=entity.market,
            is_open=entity.is_open,
            timestamp=entity.timestamp,
            uuid=entity.uuid,
        )

    @staticmethod
    def from_model(model: MTradeDay) -> TradeDay:
        """ORM → Entity。market int→enum + 还原 uuid（原码即如此，无丢失）。

        忠实原码：market 三态处理——int 转 enum、已是 enum 直接用、其它兜底
        MARKET_TYPES.OTHER。is_open/timestamp/uuid 经 getattr 兜底默认。
        """
        if not isinstance(model, MTradeDay):
            raise TypeError(f"Expected MTradeDay instance, got {type(model).__name__}")

        # 处理market字段 - 支持整数和枚举类型（忠实原码）
        market_value = getattr(model, 'market', MARKET_TYPES.OTHER)
        if isinstance(market_value, int):
            market = MARKET_TYPES(market_value)
        elif isinstance(market_value, MARKET_TYPES):
            market = market_value
        else:
            market = MARKET_TYPES.OTHER

        return TradeDay(
            market=market,
            is_open=getattr(model, 'is_open', True),
            timestamp=getattr(model, 'timestamp', '1990-01-01'),
            uuid=getattr(model, 'uuid', ''),
        )

    @staticmethod
    def from_models(models) -> List[TradeDay]:
        return [TradeDayMapper.from_model(m) for m in models]
