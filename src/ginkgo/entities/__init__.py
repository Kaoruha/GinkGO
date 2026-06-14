"""
Ginkgo Entities - 领域对象包（Entity 与 ValueObject，ADR-010）

数据对象三层角色分离的逻辑层（详见 ADR-010）：
- **Entity**（本包，如 Signal/Order/Position）：有 uuid 的状态主体，跨层流通的规范形态。
- **ValueObject**（本包，如 Adjustfactor/Tick）：无身份的领域值载体。
- ORM（data/models/）：SQLAlchemy 持久化模型，仅 CRUD 层可见。
- DTO（interfaces/dtos/）：API / 跨进程传输对象。
- Mapper（data/mappers/）：Entity ↔ ORM ↔ DTO 转换的唯一通道。

本包对象供 data 与 trading 层共同使用，但**不应**被当作 DTO 或 ORM 直接持久化。
"""

from ginkgo.entities.base import Base
from ginkgo.entities.value_object import ValueObject
from ginkgo.entities.bar import Bar
from ginkgo.entities.order import Order
from ginkgo.entities.position import Position
from ginkgo.entities.signal import Signal
from ginkgo.entities.stockinfo import StockInfo
from ginkgo.entities.tick import Tick
from ginkgo.entities.tradeday import TradeDay
from ginkgo.entities.transfer import Transfer
from ginkgo.entities.adjustfactor import Adjustfactor
from ginkgo.entities.capital_adjustment import CapitalAdjustment
from ginkgo.entities.mapping import Mapping
from ginkgo.entities.file_info import FileInfo
from ginkgo.entities.identity import IdentityUtils
from ginkgo.entities.mixins import TimeMixin, ContextMixin, NamedMixin, EngineBindableMixin

__all__ = [
    "Base", "ValueObject",
    "Bar", "Order", "Position", "Signal", "StockInfo", "Tick",
    "TradeDay", "Transfer", "Adjustfactor", "CapitalAdjustment",
    "Mapping", "FileInfo", "IdentityUtils",
    "TimeMixin", "ContextMixin", "NamedMixin", "EngineBindableMixin",
]
