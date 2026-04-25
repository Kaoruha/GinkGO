# Upstream: MOrderRecord, MPositionRecord, MSignalTracker, MAnalyzerRecord, MRunRecord, MBacktestTask
# Downstream: SQLAlchemy(String, mapped_column)
# Role: 回测记录Mixin基类，为Order/Position/Signal等模型提供engine_id和task_id字段






"""
回测记录Mixin基类

为需要关联引擎和运行会话的模型提供统一ID支持。
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class MBacktestRecordBase:
    """
    回测记录Mixin基类

    为需要关联引擎和运行会话的模型提供统一ID支持：
    - engine_id: 引擎装配关系标识
    - task_id: 执行会话标识

    使用方式（多重继承）：
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase

        class MOrder(MMysqlBase, MBacktestRecordBase):
            ...

        class MSignal(MClickBase, MBacktestRecordBase):
            ...

    适用于：Order、Position、Signal、AnalyzerRecord等回测相关记录
    不适用于：Bar、Tick等市场原始数据
    """

    engine_id: Mapped[str] = mapped_column(String(32), default="", comment="引擎装配ID")
    task_id: Mapped[str] = mapped_column(String(32), default="", comment="执行会话ID")
