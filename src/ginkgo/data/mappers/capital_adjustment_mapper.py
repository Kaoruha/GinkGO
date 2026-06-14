"""CapitalAdjustmentMapper — CapitalAdjustment Entity ↔ MCapitalAdjustment ORM 转换（ADR-010）。

承接原 CapitalAdjustment.to_model / CapitalAdjustment.from_model 内嵌逻辑
（entities/capital_adjustment.py:187-212）。无 CapitalAdjustmentDTO（项目未
定义），故只提供 to_model / from_model / from_models 三方法。

VO 动态表：to_model 多 model_class 形参，方法体内 model_class(...) 构造。
to_model 忠实原码：model_class(portfolio_id=..., amount=..., timestamp=...,
reason=..., source=..., uuid=...)，source enum 经 MCapitalAdjustment.__init__
validate_input 转 int。
from_model 还原 uuid（原码即如此，无丢失）。

已知问题（留 Task 1.6 统一评估，不擅修）：
- 原码 from_model 把 model.source（int）直接传 CapitalAdjustment 构造器，
  但 CapitalAdjustment.__init__ 严格校验 source 必须 SOURCE_TYPES enum
  （capital_adjustment.py:56-57），故 from_model 对 ORM 标准 int source 必
  TypeError。原 CapitalAdjustment.from_model 从未被 CRUD 调用（CRUD 直
  CapitalAdjustment(...) 构造），属死代码 bug。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MCapitalAdjustment
from ginkgo.entities import CapitalAdjustment
from ginkgo.enums import SOURCE_TYPES


class CapitalAdjustmentMapper:
    """CapitalAdjustment 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: CapitalAdjustment, model_class=MCapitalAdjustment) -> MCapitalAdjustment:
        """Entity → ORM。model_class 形参保留（VO 动态表选择）。

        忠实原码：model_class(...) 直接构造，source enum 经
        MCapitalAdjustment.__init__ validate_input 转 int 存储。
        """
        return model_class(
            portfolio_id=entity.portfolio_id,
            amount=entity.amount,
            timestamp=entity.timestamp,
            reason=entity.reason,
            source=entity.source,
            uuid=entity.uuid,
        )

    @staticmethod
    def from_model(model: MCapitalAdjustment) -> CapitalAdjustment:
        """ORM → Entity。还原 uuid（原码即如此，无丢失）。

        忠实原码：source 经 getattr 兜底 SOURCE_TYPES.SIM（enum），传入
        CapitalAdjustment 构造器；若 model.source 是 int，构造器内
        validate_input 转 enum。其余字段经 getattr 兜底默认。
        """
        if not isinstance(model, MCapitalAdjustment):
            raise TypeError(f"Expected MCapitalAdjustment instance, got {type(model).__name__}")

        return CapitalAdjustment(
            portfolio_id=getattr(model, 'portfolio_id', ''),
            amount=getattr(model, 'amount', 0),
            timestamp=getattr(model, 'timestamp', '1990-01-01'),
            reason=getattr(model, 'reason', ''),
            source=getattr(model, 'source', SOURCE_TYPES.SIM),
            uuid=getattr(model, 'uuid', ''),
        )

    @staticmethod
    def from_models(models) -> List[CapitalAdjustment]:
        return [CapitalAdjustmentMapper.from_model(m) for m in models]
