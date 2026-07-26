"""TransferMapper — Transfer Entity ↔ MTransfer ORM 转换（ADR-010）。

承接原 Transfer.from_model 内嵌逻辑（entities/transfer.py:218-239，含 task_id）。
to_model 按 from_model 反向实现（原 entity 无 to_model，CRUD
_convert_input_item 提供构造手法旁证——注：CRUD 该 hook 漏传 task_id，
Mapper.to_model 已补全，比 CRUD 更正确）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from datetime import datetime
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
        """Entity → ORM。ADR-029 阶段1:逐字段对齐 TransferCRUD._convert_input_item(strict mirror)。

        去 task_id + 去 uuid(镜像 CRUD 不塞:task_id 留 from_model 出路口,uuid 走 MClickBase default);
        去 ' or -1' 兜底(镜像 CRUD enum 无兜底);timestamp default datetime.now()(镜像 CRUD)。
        改直构 MTransfer(镜像 CRUD 直构),替代原逐属性赋值。enum 经 validate_input 转 int。
        """
        return MTransfer(
            portfolio_id=getattr(entity, 'portfolio_id', ''),
            engine_id=getattr(entity, 'engine_id', ''),
            direction=TRANSFERDIRECTION_TYPES.validate_input(getattr(entity, 'direction', TRANSFERDIRECTION_TYPES.IN)),
            market=MARKET_TYPES.validate_input(getattr(entity, 'market', MARKET_TYPES.CHINA)),
            money=to_decimal(getattr(entity, 'money', 0)),
            status=TRANSFERSTATUS_TYPES.validate_input(getattr(entity, 'status', TRANSFERSTATUS_TYPES.PENDING)),
            timestamp=datetime_normalize(getattr(entity, 'timestamp', datetime.now())),
            source=SOURCE_TYPES.validate_input(getattr(entity, 'source', SOURCE_TYPES.SIM)),
        )

    # ------------------------------------------------------------------
    # ORM → Entity（忠实原码 transfer.py:218-239，含 task_id）
    # ------------------------------------------------------------------
    @staticmethod
    def from_model(model: MTransfer) -> Transfer:
        """ORM → Entity。

        忠实原码（transfer.py:218-239，含 task_id）：direction/market/status
        注释为 "此时已经是枚举对象"（ORM __init__ 已转），uuid 直接传。
        """
        return Transfer(
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            task_id=model.task_id,
            direction=model.direction,  # 此时已经是枚举对象
            market=model.market,       # 此时已经是枚举对象
            money=model.money,
            status=model.status,      # 此时已经是枚举对象
            timestamp=model.timestamp,
            uuid=model.uuid
        )

    @staticmethod
    def from_models(models) -> List[Transfer]:
        return [TransferMapper.from_model(m) for m in models]
