from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models.model_signal_tracker import MSignalTracker
from ...backtest.entities.signal import Signal
from ...enums import DIRECTION_TYPES, SOURCE_TYPES, EXECUTION_MODE, TRACKING_STATUS, ACCOUNT_TYPE
from ...libs import datetime_normalize, GLOG, to_decimal, cache_with_expiration


@restrict_crud_access
class SignalTrackerCRUD(BaseCRUD[MSignalTracker]):
    """
    信号追踪 CRUD 操作
    
    提供基础的数据库访问接口
    """

    def __init__(self):
        super().__init__(MSignalTracker)

    def _get_field_config(self) -> dict:
        """
        定义 SignalTracker 数据的字段配置
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 必填字段
            "signal_id": {"required": True, "type": str},
            "strategy_id": {"required": True, "type": str},
            "portfolio_id": {"required": True, "type": str},
            "execution_mode": {"required": True, "type": int},
            "account_type": {"required": True, "type": int},
            "expected_code": {"required": True, "type": str},
            "expected_direction": {"required": True, "type": int},
            "expected_price": {"required": True, "type": float},
            "expected_volume": {"required": True, "type": int},
            "expected_timestamp": {"required": True, "type": datetime},
            
            # 可选字段
            "engine_id": {"required": False, "type": str, "default": ""},
            "actual_price": {"required": False, "type": float},
            "actual_volume": {"required": False, "type": int},
            "actual_timestamp": {"required": False, "type": datetime},
            "tracking_status": {"required": False, "type": int, "default": 0},
            "notification_sent_at": {"required": False, "type": datetime},
            "execution_confirmed_at": {"required": False, "type": datetime},
            "price_deviation": {"required": False, "type": float},
            "volume_deviation": {"required": False, "type": float},
            "time_delay_seconds": {"required": False, "type": int},
            "reject_reason": {"required": False, "type": str},
            "notes": {"required": False, "type": str},
            "source": {"required": False, "type": int, "default": -1},
        }

    def _create_from_params(self, **kwargs) -> MSignalTracker:
        """
        从参数创建 SignalTracker 对象
        
        Returns:
            MSignalTracker: 创建的 SignalTracker 对象
        """
        tracker = MSignalTracker()
        
        # 处理必填字段
        tracker.update(
            signal_id=kwargs.get("signal_id"),
            strategy_id=kwargs.get("strategy_id"),
            portfolio_id=kwargs.get("portfolio_id"),
            execution_mode=EXECUTION_MODE.from_int(kwargs.get("execution_mode")),
            account_type=ACCOUNT_TYPE.from_int(kwargs.get("account_type")),
            expected_code=kwargs.get("expected_code"),
            expected_direction=DIRECTION_TYPES.from_int(kwargs.get("expected_direction")),
            expected_price=kwargs.get("expected_price"),
            expected_volume=kwargs.get("expected_volume"),
            expected_timestamp=kwargs.get("expected_timestamp"),
            engine_id=kwargs.get("engine_id", ""),
            actual_price=kwargs.get("actual_price"),
            actual_volume=kwargs.get("actual_volume"),
            actual_timestamp=kwargs.get("actual_timestamp"),
            tracking_status=TRACKING_STATUS.from_int(kwargs.get("tracking_status", 0)),
            notification_sent_at=kwargs.get("notification_sent_at"),
            execution_confirmed_at=kwargs.get("execution_confirmed_at"),
            price_deviation=kwargs.get("price_deviation"),
            volume_deviation=kwargs.get("volume_deviation"),
            time_delay_seconds=kwargs.get("time_delay_seconds"),
            reject_reason=kwargs.get("reject_reason"),
            notes=kwargs.get("notes"),
            source=SOURCE_TYPES.from_int(kwargs.get("source", -1))
        )
        
        return tracker

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
            tracker = MSignalTracker()
            tracker.update(
                signal_id=item.uuid,
                strategy_id=getattr(item, 'strategy_id', ''),
                portfolio_id=item.portfolio_id,
                expected_code=item.code,
                expected_direction=item.direction,
                expected_price=float(getattr(item, 'price', 0)),
                expected_volume=getattr(item, 'volume', 0),
                expected_timestamp=item.timestamp,
                source=SOURCE_TYPES.STRATEGY
            )
            return tracker
        elif isinstance(item, dict):
            # 从字典创建追踪记录
            tracker = MSignalTracker()
            # 设置枚举字段的值
            if 'execution_mode' in item:
                item['execution_mode'] = item['execution_mode'].value if hasattr(item['execution_mode'], 'value') else item['execution_mode']
            if 'account_type' in item:
                item['account_type'] = item['account_type'].value if hasattr(item['account_type'], 'value') else item['account_type']
            if 'expected_direction' in item:
                item['expected_direction'] = item['expected_direction'].value if hasattr(item['expected_direction'], 'value') else item['expected_direction']
            if 'tracking_status' in item:
                item['tracking_status'] = item['tracking_status'].value if hasattr(item['tracking_status'], 'value') else item['tracking_status']
            
            tracker.update(**item)
            return tracker
        elif isinstance(item, pd.Series):
            tracker = MSignalTracker()
            tracker.update(item)
            return tracker
        else:
            GLOG.WARN(f"Unsupported input type: {type(item)}")
            return None

    def _convert_output_items(self, items: List[MSignalTracker], output_type: str = "model") -> List[Any]:
        """
        转换输出项
        
        Args:
            items: MSignalTracker 对象列表
            output_type: 输出类型 ("model", "dict", "dataframe")
            
        Returns:
            List[Any]: 转换后的对象列表
        """
        if output_type == "model":
            return items
        elif output_type == "dict":
            return [item.__dict__ for item in items]
        elif output_type == "dataframe":
            if not items:
                return pd.DataFrame()
            data = []
            for item in items:
                data.append({
                    'uuid': item.uuid,
                    'signal_id': item.signal_id,
                    'strategy_id': item.strategy_id,
                    'portfolio_id': item.portfolio_id,
                    'engine_id': item.engine_id,
                    'execution_mode': item.execution_mode,
                    'account_type': item.account_type,
                    'expected_code': item.expected_code,
                    'expected_direction': item.expected_direction,
                    'expected_price': item.expected_price,
                    'expected_volume': item.expected_volume,
                    'expected_timestamp': item.expected_timestamp,
                    'actual_price': item.actual_price,
                    'actual_volume': item.actual_volume,
                    'actual_timestamp': item.actual_timestamp,
                    'tracking_status': item.tracking_status,
                    'notification_sent_at': item.notification_sent_at,
                    'execution_confirmed_at': item.execution_confirmed_at,
                    'price_deviation': item.price_deviation,
                    'volume_deviation': item.volume_deviation,
                    'time_delay_seconds': item.time_delay_seconds,
                    'reject_reason': item.reject_reason,
                    'notes': item.notes,
                    'source': item.source,
                    'timestamp': item.timestamp,
                    'update_at': item.update_at
                })
            return pd.DataFrame(data)
        else:
            GLOG.WARN(f"Unsupported output type: {output_type}")
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
        tracking_status: Optional[TRACKING_STATUS] = None,
        limit: int = 1000
    ) -> List[MSignalTracker]:
        """
        根据投资组合查找追踪记录
        
        Args:
            portfolio_id: 投资组合ID
            account_type: 账户类型筛选
            tracking_status: 追踪状态筛选
            limit: 返回记录数限制
            
        Returns:
            List[MSignalTracker]: 追踪记录列表
        """
        filters = {"portfolio_id": portfolio_id}
        
        if account_type is not None:
            filters["account_type"] = account_type
        if tracking_status is not None:
            filters["tracking_status"] = tracking_status
        
        return self.get_items_filtered(**filters, limit=limit)

    def find_by_engine(
        self,
        engine_id: str,
        account_type: Optional[ACCOUNT_TYPE] = None,
        tracking_status: Optional[TRACKING_STATUS] = None,
        limit: int = 1000
    ) -> List[MSignalTracker]:
        """
        根据引擎查找追踪记录
        
        Args:
            engine_id: 引擎ID
            account_type: 账户类型筛选
            tracking_status: 追踪状态筛选
            limit: 返回记录数限制
            
        Returns:
            List[MSignalTracker]: 追踪记录列表
        """
        filters = {"engine_id": engine_id}
        
        if account_type is not None:
            filters["account_type"] = account_type
        if tracking_status is not None:
            filters["tracking_status"] = tracking_status
        
        return self.get_items_filtered(**filters, limit=limit)

    def find_by_strategy(
        self,
        strategy_id: str,
        account_type: Optional[ACCOUNT_TYPE] = None,
        tracking_status: Optional[TRACKING_STATUS] = None,
        limit: int = 1000
    ) -> List[MSignalTracker]:
        """
        根据策略查找追踪记录
        
        Args:
            strategy_id: 策略ID
            account_type: 账户类型筛选
            tracking_status: 追踪状态筛选
            limit: 返回记录数限制
            
        Returns:
            List[MSignalTracker]: 追踪记录列表
        """
        filters = {"strategy_id": strategy_id}
        
        if account_type is not None:
            filters["account_type"] = account_type
        if tracking_status is not None:
            filters["tracking_status"] = tracking_status
        
        return self.get_items_filtered(**filters, limit=limit)

    def find_by_tracking_status(self, tracking_status: TRACKING_STATUS, limit: int = 1000) -> List[MSignalTracker]:
        """
        根据追踪状态查找记录
        
        Args:
            tracking_status: 追踪状态
            limit: 返回记录数限制
            
        Returns:
            List[MSignalTracker]: 追踪记录列表
        """
        return self.get_items_filtered(tracking_status=tracking_status, limit=limit)

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

    def count_by_portfolio(self, portfolio_id: str) -> int:
        """
        统计投资组合的追踪记录数量
        
        Args:
            portfolio_id: 投资组合ID
            
        Returns:
            int: 记录数量
        """
        return self.count_filtered(portfolio_id=portfolio_id)

    def count_by_tracking_status(self, tracking_status: TRACKING_STATUS) -> int:
        """
        统计指定状态的追踪记录数量
        
        Args:
            tracking_status: 追踪状态
            
        Returns:
            int: 记录数量
        """
        return self.count_filtered(tracking_status=tracking_status)

    def get_all_signal_ids(self) -> List[str]:
        """
        获取所有信号ID
        
        Returns:
            List[str]: 信号ID列表
        """
        items = self.get_items_filtered()
        return list(set(item.signal_id for item in items if item.signal_id))

    def get_portfolio_ids(self) -> List[str]:
        """
        获取所有投资组合ID
        
        Returns:
            List[str]: 投资组合ID列表
        """
        items = self.get_items_filtered()
        return list(set(item.portfolio_id for item in items if item.portfolio_id))