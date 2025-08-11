from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MTransfer
from ...enums import SOURCE_TYPES, TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES, MARKET_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration
from ...backtest import Transfer


@restrict_crud_access
class TransferCRUD(BaseCRUD[MTransfer]):
    """
    Transfer CRUD operations.
    """

    def __init__(self):
        super().__init__(MTransfer)

    def _get_field_config(self) -> dict:
        """
        定义 Transfer 数据的字段配置 - 根据MTransfer模型字段
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合ID - 非空字符串，最大32位
            'portfolio_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 引擎ID - 非空字符串，最大32位
            'engine_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 转账方向 - 枚举值
            'direction': {
                'type': 'enum',
                'choices': [d for d in TRANSFERDIRECTION_TYPES]
            },
            
            # 市场类型 - 枚举值
            'market': {
                'type': 'enum',
                'choices': [m for m in MARKET_TYPES]
            },
            
            # 转账金额 - 必须大于等于0.01
            'money': {
                'type': ['decimal', 'float', 'int'],
                'min': 0.01
            },
            
            # 转账状态 - 枚举值
            'status': {
                'type': 'enum',
                'choices': [s for s in TRANSFERSTATUS_TYPES]
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

    def _create_from_params(self, **kwargs) -> MTransfer:
        """
        Hook method: Create MTransfer from parameters.
        """
        return MTransfer(
            portfolio_id=kwargs.get("portfolio_id", ""),
            engine_id=kwargs.get("engine_id", ""),
            direction=TRANSFERDIRECTION_TYPES.validate_input(kwargs.get("direction", TRANSFERDIRECTION_TYPES.IN)),
            market=MARKET_TYPES.validate_input(kwargs.get("market", MARKET_TYPES.CHINA)),
            money=to_decimal(kwargs.get("money", 0)),
            status=TRANSFERSTATUS_TYPES.validate_input(kwargs.get("status", TRANSFERSTATUS_TYPES.PENDING)),
            timestamp=datetime_normalize(kwargs.get("timestamp", datetime.now())),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MTransfer]:
        """
        Hook method: Convert Transfer objects to MTransfer.
        """
        if isinstance(item, Transfer):
            return MTransfer(
                portfolio_id=getattr(item, 'portfolio_id', ''),
                engine_id=getattr(item, 'engine_id', ''),
                direction=TRANSFERDIRECTION_TYPES.validate_input(getattr(item, 'direction', TRANSFERDIRECTION_TYPES.IN)),
                market=MARKET_TYPES.validate_input(getattr(item, 'market', MARKET_TYPES.CHINA)),
                money=to_decimal(getattr(item, 'money', 0)),
                status=TRANSFERSTATUS_TYPES.validate_input(getattr(item, 'status', TRANSFERSTATUS_TYPES.PENDING)),
                timestamp=datetime_normalize(getattr(item, 'timestamp', datetime.now())),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MTransfer], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MTransfer objects to Transfer objects.
        """
        if output_type == "transfer":
            return [
                Transfer(
                    portfolio_id=item.portfolio_id,
                    engine_id=item.engine_id,
                    direction=item.direction,
                    market=item.market,
                    money=item.money,
                    status=item.status,
                    timestamp=item.timestamp,
                    source=item.source,
                )
                for item in items
            ]
        return items

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str, direction: Optional[TRANSFERDIRECTION_TYPES] = None,
                         start_date: Optional[Any] = None, end_date: Optional[Any] = None,
                         as_dataframe: bool = False) -> Union[List[MTransfer], pd.DataFrame]:
        """
        Business helper: Find transfers by portfolio and direction.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if direction is not None:
            filters["direction"] = direction
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)
            
        return self.find(filters=filters, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_status(self, status: TRANSFERSTATUS_TYPES, as_dataframe: bool = False) -> Union[List[MTransfer], pd.DataFrame]:
        """
        Business helper: Find transfers by status.
        """
        return self.find(filters={"status": status}, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_direction(self, direction: TRANSFERDIRECTION_TYPES, as_dataframe: bool = False) -> Union[List[MTransfer], pd.DataFrame]:
        """
        Business helper: Find transfers by direction.
        """
        return self.find(filters={"direction": direction}, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def get_total_transfer_amount(self, portfolio_id: str, direction: TRANSFERDIRECTION_TYPES,
                                 start_date: Optional[Any] = None, end_date: Optional[Any] = None) -> float:
        """
        Business helper: Get total transfer amount for a portfolio and direction.
        """
        transfers = self.find_by_portfolio(portfolio_id, direction, start_date, end_date, as_dataframe=False)
        # Only count filled transfers
        filled_transfers = [t for t in transfers if t.status == TRANSFERSTATUS_TYPES.FILLED]
        return sum(float(t.money) for t in filled_transfers if t.money)

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all unique portfolio IDs.
        """
        # This would require a distinct query, simplified implementation
        all_transfers = self.find(filters={}, as_dataframe=False, output_type="model")
        return list(set(t.portfolio_id for t in all_transfers if t.portfolio_id))

    def update_status(self, portfolio_id: str, status: TRANSFERSTATUS_TYPES) -> None:
        """
        Update transfer status by portfolio ID.
        """
        return self.modify({"portfolio_id": portfolio_id}, {"status": status})
