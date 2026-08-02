# Upstream: SignalTrackingService (信号追踪业务服务)、Strategy Signal Tracking (信号执行追踪)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MSignalTracker (MySQL信号追踪模型)、EXECUTION_MODE/TRACKINGSTATUS_TYPES/ACCOUNT_TYPE/DIRECTION_TYPES (执行模式/追踪状态/账户类型/方向枚举)
# Role: SignalTrackerCRUD信号追踪CRUD继承BaseCRUD提供追踪记录管理和查询功能






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime, timedelta

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MSignalTracker
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EXECUTION_MODE, TRACKINGSTATUS_TYPES, ACCOUNT_TYPE
from ginkgo.libs import datetime_normalize, GLOG, to_decimal, cache_with_expiration


@restrict_crud_access
class SignalTrackerCRUD(BaseCRUD[MSignalTracker]):
    """
    信号追踪 CRUD 操作
    
    提供基础的数据库访问接口
    """

    # 类级别声明，支持自动注册

    _model_class = MSignalTracker

    def __init__(self):
        super().__init__(MSignalTracker)

    def _get_field_config(self) -> dict:
        """
        定义 SignalTracker 数据的字段配置
        基于业务场景分析，只包含真正的必填字段

        Returns:
            dict: 字段配置字典
        """
        return {
            # 核心关联信息 - 业务必填
            "signal_id": {"type": str},
            "strategy_id": {"type": str},
            "portfolio_id": {"type": str},

            # 执行预期参数 - 业务必填
            "expected_code": {"type": str},
            "expected_direction": {
                "type": "enum",
                "choices": [d for d in DIRECTION_TYPES]
            },
            "expected_price": {"type": ["decimal", "float", "int"]},
            "expected_volume": {"type": int},
            "expected_timestamp": {"type": ["datetime", "string"]},

            # 业务时间 - 核心字段，所有时间计算的基础
            "business_timestamp": {"type": ["datetime", "string"]},

            # 场景相关字段 - 根据具体业务场景必填
            "engine_id": {"type": str},  # 回测场景必填
            "task_id": {"type": str},     # 回测场景必填，区分多次执行
            "account_type": {
                "type": "enum",
                "choices": [a for a in ACCOUNT_TYPE]
            },  # 区分回测/模拟盘/实盘
            "execution_mode": {
                "type": "enum",
                "choices": [e for e in EXECUTION_MODE]
            },  # 自动执行还是人工确认
        }

    def _create_from_params(self, **kwargs) -> MSignalTracker:
        """
        Hook method: Create MSignalTracker from parameters.
        """
        return MSignalTracker(
            # 核心关联信息 - 业务必填
            signal_id=kwargs.get("signal_id"),
            strategy_id=kwargs.get("strategy_id", ""),  # 提供默认值
            portfolio_id=kwargs.get("portfolio_id"),

            # 执行预期参数 - 业务必填
            expected_code=kwargs.get("expected_code"),
            expected_direction=DIRECTION_TYPES.validate_input(kwargs.get("expected_direction")),
            expected_price=to_decimal(kwargs.get("expected_price")),
            expected_volume=int(kwargs.get("expected_volume")),
            expected_timestamp=datetime_normalize(kwargs.get("expected_timestamp")),

            # 业务时间 - 核心字段
            business_timestamp=datetime_normalize(kwargs.get("business_timestamp")),

            # 场景相关字段
            engine_id=kwargs.get("engine_id", ""),
            task_id=kwargs.get("task_id", ""),
            account_type=ACCOUNT_TYPE.validate_input(kwargs.get("account_type", ACCOUNT_TYPE.PAPER)),
            execution_mode=EXECUTION_MODE.validate_input(kwargs.get("execution_mode", EXECUTION_MODE.PAPER)),
        )

    # ADR-029 §Decision 1：转换钩子 override 已退役（4 路多态：Model/Signal/dict/Series）。
    # 调用方 signal_tracking_service.add:89 经 MSignalTracker(...) 直接构造后传入；
    # Signal/dict/Series 三分支无生产调用方。

    def find_by_signal_id(self, signal_id: str) -> Optional[MSignalTracker]:
        """
        根据信号ID查找追踪记录

        Args:
            signal_id: 信号ID

        Returns:
            Optional[MSignalTracker]: 追踪记录
        """
        results = self.get_items_filtered(signal_id=signal_id, limit=1)
        return results[0] if results else None

    def find_by_portfolio(
        self,
        portfolio_id: str,
        account_type: Optional[ACCOUNT_TYPE] = None,
        execution_mode: Optional[EXECUTION_MODE] = None
    ) -> list:
        """
        根据投资组合查找追踪记录

        Args:
            portfolio_id: 投资组合ID
            account_type: 账户类型筛选
            execution_mode: 执行模式筛选

        Returns:
            list[MSignalTracker]: 追踪记录列表
        """
        filters = {"portfolio_id": portfolio_id}

        if account_type is not None:
            filters["account_type"] = account_type
        if execution_mode is not None:
            filters["execution_mode"] = execution_mode

        return self.find(filters=filters)

    def find_by_engine(
        self,
        engine_id: str,
        task_id: Optional[str] = None,
        account_type: Optional[ACCOUNT_TYPE] = None
    ) -> list:
        """
        根据引擎查找追踪记录

        Args:
            engine_id: 引擎ID
            task_id: 任务ID筛选
            account_type: 账户类型筛选

        Returns:
            list[MSignalTracker]: 追踪记录列表
        """
        filters = {"engine_id": engine_id}

        if task_id is not None:
            filters["task_id"] = task_id
        if account_type is not None:
            filters["account_type"] = account_type

        return self.find(filters=filters)

    def find_by_tracking_status(
        self,
        tracking_status: TRACKINGSTATUS_TYPES,
        account_type: Optional[ACCOUNT_TYPE] = None
    ) -> list:
        """
        根据追踪状态查找记录

        Args:
            tracking_status: 追踪状态
            account_type: 账户类型筛选

        Returns:
            list[MSignalTracker]: 追踪记录列表
        """
        filters = {"tracking_status": tracking_status}

        if account_type is not None:
            filters["account_type"] = account_type

        return self.find(filters=filters)

    def delete_by_portfolio(self, portfolio_id: str) -> None:
        """
        删除指定投资组合的所有追踪记录

        Args:
            portfolio_id: 投资组合ID
        """
        self.delete_by_filters(portfolio_id=portfolio_id)

    def delete_by_engine(self, engine_id: str) -> None:
        """
        删除指定引擎的所有追踪记录

        Args:
            engine_id: 引擎ID
        """
        self.delete_by_filters(engine_id=engine_id)

    def delete_by_uuid(self, uuid: str) -> None:
        """
        根据UUID删除信号追踪记录

        Args:
            uuid: 记录UUID
        """
        if not uuid:
            raise ValueError("uuid不能为空")
        self.remove({"uuid": uuid})
