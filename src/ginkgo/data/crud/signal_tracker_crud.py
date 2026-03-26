# Upstream: SignalTrackingService (信号追踪业务服务)、Strategy Signal Tracking (信号执行追踪)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MSignalTracker (MySQL信号追踪模型)、EXECUTION_MODE/TRACKINGSTATUS_TYPES/ACCOUNT_TYPE/DIRECTION_TYPES (执行模式/追踪状态/账户类型/方向枚举)
# Role: SignalTrackerCRUD信号追踪CRUD继承BaseCRUD提供追踪记录管理和查询功能支持交易系统功能和组件集成提供完整业务支持






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime, timedelta

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models.model_signal_tracker import MSignalTracker
from ginkgo.trading.entities.signal import Signal
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
            "run_id": {"type": str},     # 回测场景必填，区分多次执行
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
            run_id=kwargs.get("run_id", ""),
            account_type=ACCOUNT_TYPE.validate_input(kwargs.get("account_type", ACCOUNT_TYPE.PAPER)),
            execution_mode=EXECUTION_MODE.validate_input(kwargs.get("execution_mode", EXECUTION_MODE.PAPER)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MSignalTracker]:
        """
        转换输入项为 MSignalTracker 对象

        Args:
            item: 输入项 (Signal, dict, pd.Series 等)

        Returns:
            Optional[MSignalTracker]: 转换后的对象
        """
        if isinstance(item, MSignalTracker):
            return item
        elif isinstance(item, Signal):
            # 从Signal对象创建追踪记录
            return MSignalTracker(
                signal_id=item.uuid,
                portfolio_id=item.portfolio_id,
                expected_code=item.code,
                expected_direction=DIRECTION_TYPES.validate_input(getattr(item, 'direction', DIRECTION_TYPES.LONG)),
                expected_price=float(getattr(item, 'price', 0)),
                expected_volume=getattr(item, 'volume', 0),
                expected_timestamp=datetime_normalize(getattr(item, 'timestamp')),
                business_timestamp=datetime_normalize(getattr(item, 'business_timestamp')),
                engine_id=getattr(item, 'engine_id', ''),
                run_id=getattr(item, 'run_id', ''),
                account_type=ACCOUNT_TYPE.validate_input(getattr(item, 'account_type', ACCOUNT_TYPE.PAPER)),
                execution_mode=EXECUTION_MODE.validate_input(getattr(item, 'execution_mode', EXECUTION_MODE.PAPER)),
            )
        elif isinstance(item, dict):
            # 从字典创建追踪记录，使用模型构造函数
            return MSignalTracker(
                signal_id=item.get('signal_id'),
                strategy_id=item.get('strategy_id', ''),
                portfolio_id=item.get('portfolio_id'),
                expected_code=item.get('expected_code'),
                expected_direction=DIRECTION_TYPES.validate_input(item.get('expected_direction')),
                expected_price=to_decimal(item.get('expected_price')),
                expected_volume=item.get('expected_volume'),
                expected_timestamp=datetime_normalize(item.get('expected_timestamp')),
                business_timestamp=datetime_normalize(item.get('business_timestamp')),
                engine_id=item.get('engine_id', ''),
                run_id=item.get('run_id', ''),
                account_type=ACCOUNT_TYPE.validate_input(item.get('account_type')),
                execution_mode=EXECUTION_MODE.validate_input(item.get('execution_mode')),
            )
        elif isinstance(item, pd.Series):
            # 从pandas Series创建追踪记录
            return MSignalTracker(
                signal_id=item.get("signal_id"),
                portfolio_id=item.get("portfolio_id"),
                expected_code=item.get("expected_code"),
                expected_direction=DIRECTION_TYPES.validate_input(item.get("expected_direction")),
                expected_price=to_decimal(item.get("expected_price")),
                expected_volume=item.get("expected_volume"),
                expected_timestamp=datetime_normalize(item.get("expected_timestamp")),
                business_timestamp=datetime_normalize(item.get("business_timestamp")),
                engine_id=item.get("engine_id", ""),
                run_id=item.get("run_id", ""),
                account_type=ACCOUNT_TYPE.validate_input(item.get("account_type")),
                execution_mode=EXECUTION_MODE.validate_input(item.get("execution_mode")),
            )
        else:
            GLOG.WARN(f"Unsupported input type: {type(item)}")
            return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for SignalTracker.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'execution_mode': EXECUTION_MODE,    # 执行模式字段映射
            'account_type': ACCOUNT_TYPE,        # 账户类型字段映射
            'expected_direction': DIRECTION_TYPES,  # 预期方向字段映射
            'tracking_status': TRACKINGSTATUS_TYPES,     # 追踪状态字段映射
            'source': SOURCE_TYPES                # 数据源字段映射
        }

    def _convert_models_to_business_objects(self, models: List[MSignalTracker]) -> List[Any]:
        """
        🎯 Convert MSignalTracker models to business objects.

        Args:
            models: List of MSignalTracker models with enum fields already fixed

        Returns:
            List of business objects (keeping as MSignalTracker for now)
        """
        # For now, return models as-is since SignalTracker doesn't have a direct business object
        return models

    def _convert_output_items(self, items: List[MSignalTracker], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MSignalTracker objects for business layer.
        """
        return items

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
    ) -> ModelList[MSignalTracker]:
        """
        根据投资组合查找追踪记录

        Args:
            portfolio_id: 投资组合ID
            account_type: 账户类型筛选
            execution_mode: 执行模式筛选

        Returns:
            ModelList[MSignalTracker]: 追踪记录列表，支持to_dataframe()和to_entities()方法
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
        run_id: Optional[str] = None,
        account_type: Optional[ACCOUNT_TYPE] = None
    ) -> ModelList[MSignalTracker]:
        """
        根据引擎查找追踪记录

        Args:
            engine_id: 引擎ID
            run_id: 运行会话ID筛选
            account_type: 账户类型筛选

        Returns:
            ModelList[MSignalTracker]: 追踪记录列表，支持to_dataframe()和to_entities()方法
        """
        filters = {"engine_id": engine_id}

        if run_id is not None:
            filters["run_id"] = run_id
        if account_type is not None:
            filters["account_type"] = account_type

        return self.find(filters=filters)

    def find_by_tracking_status(
        self,
        tracking_status: TRACKINGSTATUS_TYPES,
        account_type: Optional[ACCOUNT_TYPE] = None
    ) -> ModelList[MSignalTracker]:
        """
        根据追踪状态查找记录

        Args:
            tracking_status: 追踪状态
            account_type: 账户类型筛选

        Returns:
            ModelList[MSignalTracker]: 追踪记录列表，支持to_dataframe()和to_entities()方法
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