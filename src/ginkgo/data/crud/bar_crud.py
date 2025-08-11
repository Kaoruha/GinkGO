from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MBar
from ...backtest import Bar
from ...enums import FREQUENCY_TYPES, SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration
from ..access_control import restrict_crud_access


@restrict_crud_access
class BarCRUD(BaseCRUD[MBar]):
    """
    Bar CRUD operations with configurable field validation.
    """

    def __init__(self):
        super().__init__(MBar)

    def _get_field_config(self) -> dict:
        """
        定义 Bar 数据的字段配置 - 所有字段都是必填的

        Returns:
            dict: 字段配置字典
        """
        return {
            # 股票代码 - 只要求非空字符串
            "code": {"type": "string", "min": 1},
            # OHLC 价格 - 支持多种数值类型，必须大于0
            "open": {"type": ["decimal", "float", "int"], "min": 0.001},
            "high": {"type": ["decimal", "float", "int"], "min": 0.001},
            "low": {"type": ["decimal", "float", "int"], "min": 0.001},
            "close": {"type": ["decimal", "float", "int"], "min": 0.001},
            # 成交量 - Number，非负数
            "volume": {"type": ["int", "float", "decimal"], "min": 0},
            # 成交额 - 数值类型，非负数
            "amount": {"type": ["decimal", "float", "int"], "min": 0},
            # 时间戳 - datetime 或字符串
            "timestamp": {"type": ["datetime", "string"]},
            # 频率类型 - 枚举值
            "frequency": {
                "type": "enum",
                "choices": [f for f in FREQUENCY_TYPES],
            }
            # source字段已移除 - 使用模型默认值 SOURCE_TYPES.OTHER
        }

    def _create_from_params(self, **kwargs) -> MBar:
        """
        Hook method: Create MBar from parameters.
        """
        return MBar(
            code=kwargs.get("code"),
            open=to_decimal(kwargs.get("open", 0)),
            high=to_decimal(kwargs.get("high", 0)),
            low=to_decimal(kwargs.get("low", 0)),
            close=to_decimal(kwargs.get("close", 0)),
            volume=kwargs.get("volume", 0),
            amount=to_decimal(kwargs.get("amount", 0)),
            frequency=FREQUENCY_TYPES.validate_input(kwargs.get("frequency", FREQUENCY_TYPES.DAY)),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.TUSHARE)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MBar]:
        """
        Hook method: Convert Bar objects to MBar.
        """
        if isinstance(item, Bar):
            return MBar(
                code=item.code,
                open=item.open,
                high=item.high,
                low=item.low,
                close=item.close,
                volume=item.volume,
                amount=item.amount,
                frequency=item.frequency,
                timestamp=item.timestamp,
            )
        return None

    def _convert_output_items(self, items: List[MBar], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MBar objects to Bar objects.
        """
        if output_type == "bar":
            return [
                Bar(
                    code=item.code,
                    open=item.open,
                    high=item.high,
                    low=item.low,
                    close=item.close,
                    volume=item.volume,
                    amount=item.amount,
                    frequency=item.frequency,
                    timestamp=item.timestamp,
                )
                for item in items
            ]
        return items

    # Business Helper Methods
    def find_by_code_and_date_range(
        self,
        code: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        desc_order: bool = False,
        as_dataframe: bool = False,
    ) -> Union[List[Bar], pd.DataFrame]:
        """
        Business helper: Find bars by code with date range.
        """
        filters = {"code": code}

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
            output_type="bar" if not as_dataframe else "model",
        )

    def get_latest_bars(self, code: str, limit: int = 1, as_dataframe: bool = False) -> Union[List[Bar], pd.DataFrame]:
        """
        Business helper: Get latest bars for a code.
        """
        return self.find(
            filters={"code": code},
            page=0,
            page_size=limit,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="bar" if not as_dataframe else "model",
        )

    def remove_by_code_and_date_range(
        self, code: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None
    ) -> None:
        """
        Business helper: Remove bars by code with date range.
        """
        filters = {"code": code}

        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.remove(filters)

    def count_by_code(self, code: str) -> int:
        """
        Business helper: Count bars for a specific stock code.
        """
        return self.count({"code": code})

    def get_date_range_for_code(self, code: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Business helper: Get date range (min and max timestamps) for a stock code.
        """
        conn = self._get_connection()

        try:
            with conn.get_session() as session:
                from sqlalchemy import func

                result = (
                    session.query(
                        func.min(self.model_class.timestamp).label("min_date"),
                        func.max(self.model_class.timestamp).label("max_date"),
                    )
                    .filter(self.model_class.code == code)
                    .first()
                )

                if result and result.min_date is not None and result.max_date is not None:
                    # Check if we got meaningful dates (not epoch time)
                    min_date = result.min_date
                    max_date = result.max_date

                    # If we get epoch time (1970-01-01), it means no records were found
                    if min_date.year == 1970 and max_date.year == 1970:
                        return (None, None)

                    return (min_date, max_date)
                else:
                    return (None, None)

        except Exception as e:
            GLOG.ERROR(f"Failed to get date range for {code}: {e}")
            return (None, None)

    def get_all_codes(self, limit: Optional[int] = None) -> List[str]:
        """
        Business helper: Get list of distinct stock codes.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            return self.find(
                filters=None,
                page=None,
                page_size=limit,
                order_by=None,
                desc_order=False,
                as_dataframe=False,
                output_type="model",
                distinct_field="code",
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to get stock codes: {e}")
            return []
