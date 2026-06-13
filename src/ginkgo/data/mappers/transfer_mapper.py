"""TransferMapper — Transfer Entity ↔ MTransfer ORM 转换（ADR-010）。

承接原 Transfer.from_model 内嵌逻辑（entities/transfer.py:218-239）。
to_model 按 from_model 反向实现（原 entity 无 to_model，但 CRUD
_convert_input_item 提供了完整 entity→ORM 构造逻辑作为旁证）。

已知问题（#6125，留后续 issue 不擅修）：
- 原码 from_model 构造不传 task_id（transfer.py:229-238），但 Transfer.__init__
  强制 task_id 非空 str（transfer.py:30/52-55）→ from_model 必触发 TypeError。
  忠实搬运保留此 bug。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MTransfer
from ginkgo.entities import Transfer
from ginkgo.enums import (
    SOURCE_TYPES,
    MARKET_TYPES,
    TRANSFERDIRECTION_TYPES,
    TRANSFERSTATUS_TYPES,
)
from ginkgo.libs import to_decimal, datetime_normalize


class TransferMapper:
    """Transfer 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity → ORM（按 from_model 反向实现，CRUD _convert_input_item 旁证）
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Transfer) -> MTransfer:
        """Entity → ORM。

        按 from_model 反向 + CRUD _convert_input_item（transfer_crud.py:113-123）
        构造逻辑。enum 经 validate_input 转 int（ORM 存 int）。uuid 还原（原码惯例）。
        """
        model = MTransfer()
        model.portfolio_id = getattr(entity, 'portfolio_id', '')
        model.engine_id = getattr(entity, 'engine_id', '')
        model.task_id = getattr(entity, 'task_id', '')
        model.direction = TRANSFERDIRECTION_TYPES.validate_input(
            getattr(entity, 'direction', TRANSFERDIRECTION_TYPES.IN)
        ) or -1
        model.market = MARKET_TYPES.validate_input(
            getattr(entity, 'market', MARKET_TYPES.CHINA)
        ) or -1
        model.money = to_decimal(getattr(entity, 'money', 0))
        model.status = TRANSFERSTATUS_TYPES.validate_input(
            getattr(entity, 'status', TRANSFERSTATUS_TYPES.PENDING)
        ) or -1
        model.timestamp = datetime_normalize(getattr(entity, 'timestamp', None))
        model.source = SOURCE_TYPES.validate_input(
            getattr(entity, 'source', SOURCE_TYPES.SIM)
        ) or -1
        model.uuid = getattr(entity, 'uuid', '')
        return model

    # ------------------------------------------------------------------
    # ORM → Entity（忠实原码 transfer.py:218-239，含 task_id bug）
    # ------------------------------------------------------------------
    @staticmethod
    def from_model(model: MTransfer) -> Transfer:
        """ORM → Entity。

        忠实原码（transfer.py:218-239）：direction/market/status 注释为
        "此时已经是枚举对象"（ORM __init__ 已转），uuid 直接传。
        **原码不传 task_id** → 触发 Transfer.__init__ TypeError（已知 bug）。
        """
        return Transfer(
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            direction=model.direction,  # 此时已经是枚举对象
            market=model.market,       # 此时已经是枚举对象
            money=model.money,
            status=model.status,      # 此时已经是枚举对象
            timestamp=model.timestamp,
            uuid=model.uuid,
        )

    @staticmethod
    def from_models(models) -> List[Transfer]:
        return [TransferMapper.from_model(m) for m in models]
