from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MSignal
from ...backtest import Signal
from ...enums import DIRECTION_TYPES, SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, cache_with_expiration


@restrict_crud_access
class SignalCRUD(BaseCRUD[MSignal]):
    """
    Signal CRUD operations.
    """

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
            
            # 股票代码 - 非空字符串
            'code': {
                'type': 'string',
                'min': 1
            },
            
            # 交易方向 - 枚举值
            'direction': {
                'type': 'enum',
                'choices': [d for d in DIRECTION_TYPES]
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
                'type': 'enum',
                'choices': [s for s in SOURCE_TYPES]
            }
        }

    def _create_from_params(self, **kwargs) -> MSignal:
        """
        Hook method: Create MSignal from parameters.
        """
        return MSignal(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            code=kwargs.get("code"),
            direction=kwargs.get("direction"),
            reason=kwargs.get("reason"),
            source=kwargs.get("source", SOURCE_TYPES.SIM),
        )

    def _convert_input_item(self, item: Any) -> Optional[MSignal]:
        """
        Hook method: Convert Signal objects to MSignal.
        """
        if isinstance(item, Signal):
            return MSignal(
                portfolio_id=item.portfolio_id,
                engine_id=item.engine_id,
                timestamp=item.timestamp,
                code=item.code,
                direction=item.direction,
                reason=item.reason,
                source=item.source if hasattr(item, 'source') else SOURCE_TYPES.SIM,
            )
        return None

    def _convert_output_items(self, items: List[MSignal], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MSignal objects to Signal objects.
        """
        if output_type == "signal":
            return [
                Signal(
                    portfolio_id=item.portfolio_id,
                    engine_id=item.engine_id,
                    timestamp=item.timestamp,
                    code=item.code,
                    direction=item.direction,
                    reason=item.reason,
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
        self, portfolio_id: str, limit: int = 10, as_dataframe: bool = False
    ) -> Union[List[Signal], pd.DataFrame]:
        """
        Business helper: Get latest signals for a portfolio.
        """
        return self.find_by_portfolio(
            portfolio_id=portfolio_id, 
            page=0,  # Add page=0 to enable pagination
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
