from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MOrder
from ...backtest import Order
from ...enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration


@restrict_crud_access
class OrderCRUD(BaseCRUD[MOrder]):
    """
    Order CRUD operations.
    """

    def __init__(self):
        super().__init__(MOrder)

    def _get_field_config(self) -> dict:
        """
        定义 Order 数据的字段配置 - 所有字段都是必填的
        
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
            
            # 订单类型 - 枚举值
            'order_type': {
                'type': 'enum',
                'choices': [o for o in ORDER_TYPES]
            },
            
            # 订单状态 - 枚举值
            'status': {
                'type': 'enum',
                'choices': [s for s in ORDERSTATUS_TYPES]
            },
            
            # 订单数量 - 正数
            'volume': {
                'type': ['int', 'float'],
                'min': 1
            },
            
            # 限价 - 非负数值
            'limit_price': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 冻结资金 - 非负数
            'frozen': {
                'type': ['int', 'float', 'decimal'],
                'min': 0
            },
            
            # 成交价格 - 非负数值
            'transaction_price': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 成交数量 - 非负数
            'transaction_volume': {
                'type': ['int', 'float'],
                'min': 0
            },
            
            # 剩余数量 - 非负数
            'remain': {
                'type': ['float', 'int'],
                'min': 0
            },
            
            # 手续费 - 非负数
            'fee': {
                'type': ['float', 'decimal'],
                'min': 0
            },
            
            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [s for s in SOURCE_TYPES]
            }
        }

    def _create_from_params(self, **kwargs) -> MOrder:
        """
        Hook method: Create MOrder from parameters.
        """
        return MOrder(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            code=kwargs.get("code"),
            direction=kwargs.get("direction"),
            order_type=kwargs.get("order_type"),
            status=kwargs.get("status", ORDERSTATUS_TYPES.NEW),
            volume=kwargs.get("volume"),
            limit_price=to_decimal(kwargs.get("limit_price", 0)),
            frozen=kwargs.get("frozen", 0),
            transaction_price=to_decimal(kwargs.get("transaction_price", 0)),
            transaction_volume=kwargs.get("transaction_volume", 0),
            remain=kwargs.get("remain", 0.0),
            fee=kwargs.get("fee", 0.0),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            source=kwargs.get("source", SOURCE_TYPES.SIM),
        )

    def _convert_input_item(self, item: Any) -> Optional[MOrder]:
        """
        Hook method: Convert Order objects to MOrder.
        """
        if isinstance(item, Order) or hasattr(item, 'portfolio_id'):
            return MOrder(
                portfolio_id=getattr(item, 'portfolio_id', ""),
                engine_id=getattr(item, 'engine_id', ""),
                code=getattr(item, 'code', ""),
                direction=getattr(item, 'direction', DIRECTION_TYPES.LONG),
                order_type=getattr(item, 'order_type', ORDER_TYPES.OTHER),
                status=getattr(item, 'status', ORDERSTATUS_TYPES.NEW),
                volume=getattr(item, 'volume', 0),
                limit_price=to_decimal(getattr(item, 'limit_price', 0)),
                frozen=to_decimal(getattr(item, 'frozen', 0)),
                transaction_price=to_decimal(getattr(item, 'transaction_price', 0)),
                transaction_volume=getattr(item, 'transaction_volume', 0),
                remain=to_decimal(getattr(item, 'remain', 0)),
                fee=to_decimal(getattr(item, 'fee', 0)),
                timestamp=datetime_normalize(getattr(item, 'timestamp')),
                source=getattr(item, 'source', SOURCE_TYPES.SIM),
            )
        return None

    def _convert_output_items(self, items: List[MOrder], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MOrder objects to Order objects.
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
        status: Optional[ORDERSTATUS_TYPES] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        desc_order: bool = True,
        as_dataframe: bool = False,
    ) -> Union[List[Order], pd.DataFrame]:
        """
        Business helper: Find orders by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if status:
            filters["status"] = status
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
            output_type="order" if not as_dataframe else "model"
        )

    def find_by_code(
        self,
        code: str,
        portfolio_id: Optional[str] = None,
        status: Optional[ORDERSTATUS_TYPES] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Order], pd.DataFrame]:
        """
        Business helper: Find orders by stock code.
        """
        filters = {"code": code}
        
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if status:
            filters["status"] = status
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="order" if not as_dataframe else "model"
        )

    def find_pending_orders(
        self,
        portfolio_id: Optional[str] = None,
        code: Optional[str] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Order], pd.DataFrame]:
        """
        Business helper: Find pending orders.
        """
        filters = {"status": ORDERSTATUS_TYPES.NEW}
        
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if code:
            filters["code"] = code

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=False,  # Pending orders by creation time
            as_dataframe=as_dataframe,
            output_type="order" if not as_dataframe else "model"
        )

    def find_filled_orders(
        self,
        portfolio_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Order], pd.DataFrame]:
        """
        Business helper: Find filled orders.
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
            output_type="order" if not as_dataframe else "model"
        )

    def find_by_direction(
        self,
        direction: DIRECTION_TYPES,
        portfolio_id: Optional[str] = None,
        status: Optional[ORDERSTATUS_TYPES] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Order], pd.DataFrame]:
        """
        Business helper: Find orders by direction (LONG/SHORT).
        """
        filters = {"direction": direction}
        
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if status:
            filters["status"] = status
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="order" if not as_dataframe else "model"
        )

    def find_large_orders(
        self,
        min_volume: int,
        portfolio_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        limit: Optional[int] = None,
        as_dataframe: bool = False,
    ) -> Union[List[Order], pd.DataFrame]:
        """
        Business helper: Find large volume orders.
        """
        filters = {"volume__gte": min_volume}
        
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            page_size=limit,
            order_by="volume",
            desc_order=True,  # Largest volume first
            as_dataframe=as_dataframe,
            output_type="order" if not as_dataframe else "model"
        )

    def delete_by_portfolio(self, portfolio_id: str) -> None:
        """
        Business helper: Delete all orders for a portfolio.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id不能为空")
        
        GLOG.WARN(f"删除组合 {portfolio_id} 的所有order记录")
        return self.remove({"portfolio_id": portfolio_id})

    def delete_by_status(self, status: ORDERSTATUS_TYPES, portfolio_id: Optional[str] = None) -> None:
        """
        Business helper: Delete orders by status.
        """
        filters = {"status": status}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        
        GLOG.WARN(f"删除状态为 {status} 的order记录")
        return self.remove(filters)

    def cancel_pending_orders(self, portfolio_id: Optional[str] = None, code: Optional[str] = None) -> int:
        """
        Business helper: Cancel (delete) pending orders.
        Returns count of cancelled orders.
        """
        filters = {"status": ORDERSTATUS_TYPES.NEW}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if code:
            filters["code"] = code
        
        # Count before deletion
        count = self.count(filters)
        
        if count > 0:
            GLOG.INFO(f"取消 {count} 个pending订单")
            self.remove(filters)
        
        return count

    def count_by_portfolio(self, portfolio_id: str) -> int:
        """
        Business helper: Count orders for a specific portfolio.
        """
        return self.count({"portfolio_id": portfolio_id})

    def count_by_status(self, status: ORDERSTATUS_TYPES, portfolio_id: Optional[str] = None) -> int:
        """
        Business helper: Count orders by status.
        """
        filters = {"status": status}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        return self.count(filters)

    def count_by_direction(self, direction: DIRECTION_TYPES, portfolio_id: Optional[str] = None) -> int:
        """
        Business helper: Count orders by direction.
        """
        filters = {"direction": direction}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        return self.count(filters)

    def get_order_summary(self, portfolio_id: str, start_date: Optional[Any] = None, end_date: Optional[Any] = None) -> dict:
        """
        Business helper: Get order summary statistics for a portfolio.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)
        
        orders = self.find(filters=filters, as_dataframe=False, output_type="model")
        
        if not orders:
            return {
                "total_orders": 0,
                "pending_orders": 0,
                "filled_orders": 0,
                "cancelled_orders": 0,
                "total_volume": 0,
                "avg_price": 0,
                "total_fees": 0,
            }
        
        summary = {
            "total_orders": len(orders),
            "pending_orders": sum(1 for o in orders if o.status == ORDERSTATUS_TYPES.NEW),
            "filled_orders": sum(1 for o in orders if o.status == ORDERSTATUS_TYPES.FILLED),
            "cancelled_orders": sum(1 for o in orders if o.status == ORDERSTATUS_TYPES.CANCELED),
            "total_volume": sum(o.volume for o in orders if o.volume),
            "total_fees": sum(float(o.fee) for o in orders if o.fee),
        }
        
        filled_orders = [o for o in orders if o.status == ORDERSTATUS_TYPES.FILLED and o.transaction_price]
        if filled_orders:
            total_amount = sum(float(o.transaction_price) * o.volume for o in filled_orders)
            total_volume = sum(o.volume for o in filled_orders)
            summary["avg_price"] = total_amount / total_volume if total_volume > 0 else 0
        else:
            summary["avg_price"] = 0
        
        return summary

    def get_all_codes(self) -> List[str]:
        """
        Business helper: Get all distinct stock codes with orders.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            codes = self.find(distinct_field="code")
            return [code for code in codes if code]
        except Exception as e:
            GLOG.ERROR(f"Failed to get order codes: {e}")
            return []

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio IDs with orders.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_ids = self.find(distinct_field="portfolio_id")
            return [pid for pid in portfolio_ids if pid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get order portfolio ids: {e}")
            return []
