from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MSignal
from ginkgo.trading import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration


@restrict_crud_access
class SignalCRUD(BaseCRUD[MSignal]):
    """
    Signal CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MSignal

    def __init__(self):
        super().__init__(MSignal)

    def _get_field_config(self) -> dict:
        """
        定义 Signal 数据的字段配置 - 所有字段都是必填的

        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合ID - 非空字符串
            'portfolio_id': {
                'type': 'string',
                'min': 1
            },

            # 引擎ID - 非空字符串
            'engine_id': {
                'type': 'string',
                'min': 1
            },

            # 运行会话ID - 非空字符串
            'run_id': {
                'type': 'string',
                'min': 1
            },

            # 股票代码 - 非空字符串
            'code': {
                'type': 'string',
                'min': 1
            },

            # 交易方向 - 枚举值
            'direction': {
                'type': 'DIRECTION_TYPES',  # 使用枚举类型名称
            },

            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },

            # 原因 - 可选字符串
            'reason': {
                'type': 'string',
                'min': 0  # 允许空字符串
            },

            # 数据源 - 枚举值
            'source': {
                'type': 'SOURCE_TYPES',  # 使用枚举类型名称
            },

            # 业务时间戳 - datetime 或字符串，可选
            'business_timestamp': {
                'type': ['datetime', 'string', 'none'],
                'required': False
            }
        }

    def _create_from_params(self, **kwargs) -> MSignal:
        """
        Hook method: Create MSignal from parameters.
        """
        # 处理枚举字段，确保插入数据库的是数值
        direction_value = kwargs.get("direction")
        if isinstance(direction_value, DIRECTION_TYPES):
            direction_value = direction_value.value
        else:
            direction_value = DIRECTION_TYPES.validate_input(direction_value)

        source_value = kwargs.get("source", SOURCE_TYPES.SIM)
        if isinstance(source_value, SOURCE_TYPES):
            source_value = source_value.value
        else:
            source_value = SOURCE_TYPES.validate_input(source_value)

        # 确保business_timestamp有默认值，避免验证失败
        business_timestamp = kwargs.get("business_timestamp")
        if business_timestamp is None:
            business_timestamp = kwargs.get("timestamp")  # 回退到timestamp

        return MSignal(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            run_id=kwargs.get("run_id", ""),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            code=kwargs.get("code"),
            direction=direction_value,
            reason=kwargs.get("reason"),
            source=source_value,
            business_timestamp=datetime_normalize(business_timestamp),
        )

    def _convert_input_item(self, item: Any) -> Optional[MSignal]:
        """
        Hook method: Convert Signal objects to MSignal.
        """
        if isinstance(item, Signal):
            return MSignal(
                portfolio_id=item.portfolio_id,
                engine_id=item.engine_id,
                run_id=item.run_id,
                timestamp=item.timestamp,
                code=item.code,
                direction=DIRECTION_TYPES.validate_input(item.direction),
                reason=item.reason,
                source=SOURCE_TYPES.validate_input(item.source if hasattr(item, 'source') else SOURCE_TYPES.SIM),
                business_timestamp=datetime_normalize(getattr(item, 'business_timestamp', None)),
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for Signal.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'direction': DIRECTION_TYPES,  # 交易方向字段映射
            'source': SOURCE_TYPES        # 数据源字段映射
        }

    def _convert_models_to_business_objects(self, models: List[MSignal]) -> List[Signal]:
        """
        🎯 Convert MSignal models to Signal business objects.

        Args:
            models: List of MSignal models with enum fields already fixed

        Returns:
            List of Signal business objects
        """
        business_objects = []
        for model in models:
            # 转换为业务对象 (此时枚举字段已经是正确的枚举对象)
            signal = Signal(
                portfolio_id=model.portfolio_id,
                engine_id=model.engine_id,
                run_id=model.run_id,  # 添加run_id字段
                timestamp=model.timestamp,
                code=model.code,
                direction=model.direction,
                reason=model.reason,
                source=model.source,  # 添加source字段
                strength=model.strength,  # 添加strength字段
                confidence=model.confidence,  # 添加confidence字段
            )
            business_objects.append(signal)

        return business_objects

    def _convert_output_items(self, items: List[MSignal], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MSignal objects to Signal objects.
        """
        if output_type == "signal":
            return [
                Signal(
                    portfolio_id=item.portfolio_id,
                    engine_id=item.engine_id,
                    run_id=item.run_id,  # 添加run_id字段
                    timestamp=item.timestamp,
                    code=item.code,
                    direction=item.direction,
                    reason=item.reason,
                    source=item.source,  # 添加source字段
                    strength=item.strength,  # 添加strength字段
                    confidence=item.confidence,  # 添加confidence字段
                )
                for item in items
            ]
        return items

    # Business Helper Methods
    def find_by_portfolio(
        self,
        portfolio_id: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        desc_order: bool = False,
        as_dataframe: bool = False,
    ) -> Union[List[Signal], pd.DataFrame]:
        """
        Business helper: Find signals by portfolio ID with date range.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="timestamp",
            desc_order=desc_order,
            as_dataframe=as_dataframe,
            output_type="signal" if not as_dataframe else "model"
        )

    def find_by_engine(
        self,
        engine_id: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Signal], pd.DataFrame]:
        """
        Business helper: Find signals by engine ID.
        """
        filters = {"engine_id": engine_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="signal" if not as_dataframe else "model"
        )

    def find_by_code_and_direction(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        portfolio_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Signal], pd.DataFrame]:
        """
        Business helper: Find signals by code and direction.
        """
        filters = {"code": code, "direction": direction}
        
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="signal" if not as_dataframe else "model"
        )

    def get_latest_signals(
        self, portfolio_id: str, limit: int = 10, page: Optional[int] = None, as_dataframe: bool = False
    ) -> Union[List[Signal], pd.DataFrame]:
        """
        Business helper: Get latest signals for a portfolio with pagination support.

        Args:
            portfolio_id: Portfolio ID to query
            limit: Number of signals to return (default: 10)
            page: Page number (0-based, None means start from page 0)
            as_dataframe: Return as DataFrame if True
        """
        return self.find_by_portfolio(
            portfolio_id=portfolio_id,
            page=page,  # Use dynamic page parameter
            page_size=limit,
            desc_order=True,
            as_dataframe=as_dataframe
        )

    def delete_by_portfolio(self, portfolio_id: str) -> None:
        """
        Business helper: Delete all signals for a portfolio.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id不能为空")
        
        GLOG.WARN(f"删除组合 {portfolio_id} 的所有signal记录")
        return self.remove({"portfolio_id": portfolio_id})

    def delete_by_portfolio_and_date_range(
        self, 
        portfolio_id: str, 
        start_date: Optional[Any] = None, 
        end_date: Optional[Any] = None
    ) -> None:
        """
        Business helper: Delete signals by portfolio and date range.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id不能为空")
        
        filters = {"portfolio_id": portfolio_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.remove(filters)

    def count_by_portfolio(self, portfolio_id: str) -> int:
        """
        Business helper: Count signals for a specific portfolio.
        """
        return self.count({"portfolio_id": portfolio_id})

    def count_by_code_and_direction(self, code: str, direction: DIRECTION_TYPES) -> int:
        """
        Business helper: Count signals by code and direction.
        """
        return self.count({"code": code, "direction": direction})

    def get_all_codes(self) -> List[str]:
        """
        Business helper: Get all distinct stock codes with signals.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            codes = self.find(distinct_field="code")
            return [code for code in codes if code]
        except Exception as e:
            GLOG.ERROR(f"Failed to get signal codes: {e}")
            return []

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio IDs with signals.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_ids = self.find(distinct_field="portfolio_id")
            return [pid for pid in portfolio_ids if pid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get signal portfolio ids: {e}")
            return []

    def find_by_business_time(
        self,
        portfolio_id: str,
        start_business_time: Optional[Any] = None,
        end_business_time: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[MSignal], pd.DataFrame]:
        """
        Business helper: Find signals by business time range.

        Args:
            portfolio_id: Portfolio ID to query
            start_business_time: Start of business time range (optional)
            end_business_time: End of business time range (optional)
            as_dataframe: Return as DataFrame if True

        Returns:
            List of MSignal models or DataFrame
        """
        filters = {"portfolio_id": portfolio_id}

        if start_business_time:
            filters["business_timestamp__gte"] = datetime_normalize(start_business_time)
        if end_business_time:
            filters["business_timestamp__lte"] = datetime_normalize(end_business_time)

        return self.find(
            filters=filters,
            order_by="business_timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model"
        )
