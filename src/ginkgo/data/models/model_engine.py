# Upstream: EngineCRUD (引擎配置持久化)、EngineFactory (创建和查询引擎)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、ModelConversion (提供实体转换能力)、ENGINESTATUS_TYPES/ATTITUDE_TYPES (枚举类型验证)
# Role: MEngine引擎配置MySQL模型继承MMysqlBase定义核心字段提供引擎配置管理支持交易系统功能和组件集成提供完整业务支持






import datetime
import pandas as pd

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Boolean, Enum, Integer, Text, DateTime
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, ENGINESTATUS_TYPES, ATTITUDE_TYPES
from ginkgo.libs import base_repr


class MEngine(MMysqlBase, ModelConversion):
    """
    Enhanced Engine Model with Configuration and Run Management
    
    增强的引擎模型，支持：
    - 配置哈希验证
    - 运行统计跟踪
    - 当前会话管理
    """
    __abstract__ = False
    __tablename__ = "engine"

    name: Mapped[str] = mapped_column(String(64), default="ginkgo_test_engine")
    status: Mapped[int] = mapped_column(TINYINT, default=-1)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 新增：配置和运行管理字段
    config_hash: Mapped[str] = mapped_column(String(64), default="", comment="配置哈希值")
    current_run_id: Mapped[str] = mapped_column(String(128), default="", comment="当前运行会话ID")
    run_count: Mapped[int] = mapped_column(Integer, default=0, comment="运行次数计数")
    config_snapshot: Mapped[Optional[str]] = mapped_column(Text, default="{}", comment="配置快照JSON")

    # 时间范围配置字段
    backtest_start_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="回测开始时间")
    backtest_end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="回测结束时间")

    # Broker配置字段
    broker_attitude: Mapped[int] = mapped_column(TINYINT, default=2, comment="Broker态度: 1=PESSIMISTIC, 2=OPTIMISTIC, 3=RANDOM")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        engine_id: str = "",
        config_hash: str = "",
        current_run_id: str = "",
        run_count: int = 0,  # 新增run_count参数
        config_snapshot: str = "{}",  # 新增config_snapshot参数
        backtest_start_date: Optional[datetime.datetime] = None,  # 新增时间范围参数
        backtest_end_date: Optional[datetime.datetime] = None,    # 新增时间范围参数
        broker_attitude: Optional[ATTITUDE_TYPES] = None,        # 新增broker_attitude参数
        status: Optional[ENGINESTATUS_TYPES] = None,
        is_live: Optional[bool] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        self.engine_id = engine_id
        self.config_hash = config_hash
        self.current_run_id = current_run_id
        self.run_count = run_count  # 新增run_count字段赋值
        self.config_snapshot = config_snapshot  # 新增config_snapshot字段赋值
        self.backtest_start_date = backtest_start_date  # 新增时间范围字段赋值
        self.backtest_end_date = backtest_end_date      # 新增时间范围字段赋值
        if broker_attitude is not None:
            self.broker_attitude = ATTITUDE_TYPES.validate_input(broker_attitude) or 2  # 默认OPTIMISTIC
        if status is not None:
            self.status = ENGINESTATUS_TYPES.validate_input(status) or -1
        if is_live is not None:
            self.is_live = is_live
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.name = df["name"]
        self.status = ENGINESTATUS_TYPES.validate_input(df["status"]) or -1
        self.is_live = df["is_live"]
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __init__(self, **kwargs):
        """初始化MEngine实例，自动处理枚举字段转换"""
        super().__init__()
        # 处理枚举字段转换
        if 'status' in kwargs:
            self.status = ENGINESTATUS_TYPES.validate_input(kwargs['status']) or -1
            del kwargs['status']
        if 'source' in kwargs:
            self.source = SOURCE_TYPES.validate_input(kwargs['source']) or -1
            del kwargs['source']
        if 'broker_attitude' in kwargs:
            self.broker_attitude = ATTITUDE_TYPES.validate_input(kwargs['broker_attitude']) or 2
            del kwargs['broker_attitude']
        # 设置其他字段，包括run_count
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
