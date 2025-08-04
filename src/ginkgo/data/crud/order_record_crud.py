from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from .validation import ValidationError
from ..models import MOrderRecord
from ...enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration
from ...backtest import Order


@restrict_crud_access
class OrderRecordCRUD(BaseCRUD[MOrderRecord]):
    """
    OrderRecord CRUD operations.
    """

    def __init__(self):
        super().__init__(MOrderRecord)

    def _get_field_config(self) -> dict:
        """
        定义 OrderRecord 数据的字段配置
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 订单ID - 非空字符串，最大32字符
            'order_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 投资组合ID - 非空字符串，最大32字符  
            'portfolio_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 引擎ID - 非空字符串，最大32字符
            'engine_id': {
                'type': 'string', 
                'min': 1,
                'max': 32
            },
            
            # 股票代码 - 非空字符串，最大32字符
            'code': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 交易方向 - 枚举值
            'direction': {
                'type': 'enum',
                'choices': [d for d in DIRECTION_TYPES]
            },
            
            # 订单类型 - 枚举值
            'order_type': {
                'type': 'enum',
                'choices': [ot for ot in ORDER_TYPES]
            },
            
            # 订单状态 - 枚举值
            'status': {
                'type': 'enum',
                'choices': [s for s in ORDERSTATUS_TYPES]
            },
            
            # 交易量 - 正整数
            'volume': {
                'type': ['int', 'float'],
                'min': 1
            },
            
            # 限价 - 非负数值 (可选)
            'limit_price': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            }
        }


    def _normalize_enum_value(self, value, enum_class):
        """
        智能转换枚举值：支持数值和枚举对象两种格式
        """
        if value is None:
            return None
        
        # 如果已经是枚举对象，直接返回
        if isinstance(value, enum_class):
            return value
        
        # 如果是数值，尝试通过value匹配
        if isinstance(value, (int, float)):
            for enum_item in enum_class:
                if enum_item.value == value:
                    return enum_item
        
        # 如果是字符串，尝试通过名称匹配
        if isinstance(value, str):
            try:
                return enum_class[value]
            except KeyError:
                pass
        
        # 如果都不匹配，返回原值（让后续验证处理）
        return value

    def _create_from_params(self, **kwargs) -> MOrderRecord:
        """
        Hook method: Create MOrderRecord from parameters.
        """
        return MOrderRecord(
            order_id=kwargs.get("order_id"),
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            code=kwargs.get("code"),
            direction=self._normalize_enum_value(kwargs.get("direction"), DIRECTION_TYPES),
            order_type=self._normalize_enum_value(kwargs.get("order_type"), ORDER_TYPES),
            status=self._normalize_enum_value(kwargs.get("status"), ORDERSTATUS_TYPES),
            volume=kwargs.get("volume"),
            limit_price=to_decimal(kwargs.get("limit_price", 0)),
            frozen=to_decimal(kwargs.get("frozen", 0)),
            transaction_price=to_decimal(kwargs.get("transaction_price", 0)),
            remain=to_decimal(kwargs.get("remain", 0)),
            fee=to_decimal(kwargs.get("fee", 0)),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
        )

    def _convert_input_item(self, item: Any) -> Optional[MOrderRecord]:
        """
        Hook method: Convert Order objects to MOrderRecord.
        """
        if isinstance(item, Order):
            return MOrderRecord(
                order_id=item.uuid if hasattr(item, 'uuid') else str(item.order_id),
                portfolio_id=item.portfolio_id if hasattr(item, 'portfolio_id') else "",
                engine_id=item.engine_id if hasattr(item, 'engine_id') else "",
                code=item.code,
                direction=item.direction,
                order_type=item.order_type,
                status=item.status,
                volume=item.volume,
                limit_price=item.limit_price,
                frozen=item.frozen if hasattr(item, 'frozen') else 0,
                transaction_price=item.transaction_price if hasattr(item, 'transaction_price') else 0,
                remain=item.remain if hasattr(item, 'remain') else 0,
                fee=item.fee if hasattr(item, 'fee') else 0,
                timestamp=item.timestamp,
            )
        return None

    def _convert_output_items(self, items: List[MOrderRecord], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MOrderRecord objects to Order objects.
        """
        if output_type == "order":
            return [
                Order(
                    code=item.code,
                    direction=item.direction,
                    order_type=item.order_type,
                    volume=item.volume,
                    limit_price=item.limit_price,
                    timestamp=item.timestamp,
                    status=item.status,
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
        status: Optional[ORDERSTATUS_TYPES] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        desc_order: bool = True,
        as_dataframe: bool = False,
    ) -> Union[List[MOrderRecord], pd.DataFrame]:
        """
        Business helper: Find order records by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)
        if status:
            filters["status"] = status

        return self.find(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="timestamp",
            desc_order=desc_order,
            as_dataframe=as_dataframe,
            output_type="model"
        )

    def find_by_order_id(self, order_id: str, as_dataframe: bool = False) -> Union[List[MOrderRecord], pd.DataFrame]:
        """
        Business helper: Find order records by order ID.
        """
        return self.find(
            filters={"order_id": order_id},
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model"
        )

    def find_by_code_and_status(
        self,
        code: str,
        status: ORDERSTATUS_TYPES,
        portfolio_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[MOrderRecord], pd.DataFrame]:
        """
        Business helper: Find order records by code and status.
        """
        filters = {"code": code, "status": status}
        
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
            output_type="model"
        )

    def find_pending_orders(
        self,
        portfolio_id: Optional[str] = None,
        code: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[List[MOrderRecord], pd.DataFrame]:
        """
        Business helper: Find pending order records.
        """
        filters = {"status": ORDERSTATUS_TYPES.SUBMITTED}
        
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if code:
            filters["code"] = code

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model"
        )

    def find_filled_orders(
        self,
        portfolio_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[MOrderRecord], pd.DataFrame]:
        """
        Business helper: Find filled order records.
        """
        filters = {"status": ORDERSTATUS_TYPES.FILLED}
        
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
            output_type="model"
        )

    def delete_by_portfolio(self, portfolio_id: str) -> None:
        """
        Business helper: Delete all order records for a portfolio.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id不能为空")
        
        GLOG.WARN(f"删除组合 {portfolio_id} 的所有order_record记录")
        return self.remove({"portfolio_id": portfolio_id})

    def delete_by_order_id(self, order_id: str) -> None:
        """
        Business helper: Delete order records by order ID.
        """
        if not order_id:
            raise ValueError("order_id不能为空")
        
        return self.remove({"order_id": order_id})

    def delete_by_status(self, status: ORDERSTATUS_TYPES, portfolio_id: Optional[str] = None) -> None:
        """
        Business helper: Delete order records by status.
        """
        filters = {"status": status}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        
        GLOG.WARN(f"删除状态为 {status} 的order_record记录")
        return self.remove(filters)

    def count_by_portfolio(self, portfolio_id: str) -> int:
        """
        Business helper: Count order records for a specific portfolio.
        """
        return self.count({"portfolio_id": portfolio_id})

    def count_by_status(self, status: ORDERSTATUS_TYPES, portfolio_id: Optional[str] = None) -> int:
        """
        Business helper: Count order records by status.
        """
        filters = {"status": status}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        return self.count(filters)

    def get_total_transaction_amount(self, portfolio_id: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None) -> float:
        """
        Business helper: Calculate total transaction amount for a portfolio.
        """
        filters = {"portfolio_id": portfolio_id, "status": ORDERSTATUS_TYPES.FILLED}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)
        
        records = self.find(filters=filters, as_dataframe=False, output_type="model")
        
        total_amount = sum(
            float(record.transaction_price) * record.volume + float(record.fee)
            for record in records
            if record.transaction_price and record.volume
        )
        
        return total_amount
