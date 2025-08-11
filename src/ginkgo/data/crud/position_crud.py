from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MPosition
from ...enums import SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration


@restrict_crud_access
class PositionCRUD(BaseCRUD[MPosition]):
    """
    Position CRUD operations.
    """

    def __init__(self):
        super().__init__(MPosition)

    def _get_field_config(self) -> dict:
        """
        定义 Position 数据的字段配置 - 基于 MPosition 模型字段
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合ID - 非空字符串 (长度32)
            'portfolio_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 引擎ID - 非空字符串 (长度32)
            'engine_id': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 股票代码 - 非空字符串 (长度32)
            'code': {
                'type': 'string',
                'min': 1,
                'max': 32
            },
            
            # 成本 - 非负十进制数
            'cost': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 持仓数量 - 整数
            'volume': {
                'type': 'int',
                'min': 0
            },
            
            # 冻结数量 - 整数
            'frozen_volume': {
                'type': 'int',
                'min': 0
            },
            
            # 冻结资金 - 非负十进制数
            'frozen_money': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 价格 - 非负十进制数
            'price': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 手续费 - 非负十进制数
            'fee': {
                'type': ['decimal', 'float', 'int'],
                'min': 0
            },
            
            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [s for s in SOURCE_TYPES]
            }
        }

    def _create_from_params(self, **kwargs) -> MPosition:
        """
        Hook method: Create MPosition from parameters.
        """
        return MPosition(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            code=kwargs.get("code"),
            cost=to_decimal(kwargs.get("cost", 0)),
            volume=kwargs.get("volume", 0),
            frozen_volume=kwargs.get("frozen_volume", 0),
            frozen_money=to_decimal(kwargs.get("frozen_money", 0)),
            price=to_decimal(kwargs.get("price", 0)),
            fee=to_decimal(kwargs.get("fee", 0)),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MPosition]:
        """
        Hook method: Convert position objects to MPosition.
        """
        if hasattr(item, 'portfolio_id') and hasattr(item, 'code'):
            return MPosition(
                portfolio_id=getattr(item, 'portfolio_id'),
                engine_id=getattr(item, 'engine_id', ''),
                code=getattr(item, 'code'),
                cost=to_decimal(getattr(item, 'cost', 0)),
                volume=getattr(item, 'volume', 0),
                frozen_volume=getattr(item, 'frozen_volume', 0),
                frozen_money=to_decimal(getattr(item, 'frozen_money', 0)),
                price=to_decimal(getattr(item, 'price', 0)),
                fee=to_decimal(getattr(item, 'fee', 0)),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MPosition], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MPosition objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str, min_volume: int = 0,
                         as_dataframe: bool = False) -> Union[List[MPosition], pd.DataFrame]:
        """
        Business helper: Find positions by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        if min_volume > 0:
            filters["volume__gte"] = min_volume
            
        return self.find(filters=filters, order_by="cost", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_code(self, code: str, portfolio_id: Optional[str] = None,
                    as_dataframe: bool = False) -> Union[List[MPosition], pd.DataFrame]:
        """
        Business helper: Find positions by stock code.
        """
        filters = {"code": code}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
            
        return self.find(filters=filters, order_by="volume", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def get_position(self, portfolio_id: str, code: str) -> Optional[MPosition]:
        """
        Business helper: Get specific position.
        """
        result = self.find(filters={"portfolio_id": portfolio_id, "code": code},
                          page_size=1, as_dataframe=False, output_type="model")
        return result[0] if result else None

    def get_active_positions(self, portfolio_id: str, min_volume: int = 1,
                           as_dataframe: bool = False) -> Union[List[MPosition], pd.DataFrame]:
        """
        Business helper: Get active positions (volume > 0).
        """
        return self.find_by_portfolio(portfolio_id, min_volume, as_dataframe)

    def get_portfolio_value(self, portfolio_id: str) -> dict:
        """
        Business helper: Get portfolio total value.
        """
        positions = self.find_by_portfolio(portfolio_id, as_dataframe=False)
        
        total_cost = sum(float(pos.cost) for pos in positions if pos.cost)
        # Calculate market value as price * volume for positions with volume > 0
        total_market_value = sum(float(pos.price) * pos.volume for pos in positions if pos.volume > 0 and pos.price)
        total_volume = sum(pos.volume for pos in positions if pos.volume)
        active_positions = len([pos for pos in positions if pos.volume > 0])
        
        return {
            "portfolio_id": portfolio_id,
            "total_positions": len(positions),
            "active_positions": active_positions,
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "total_pnl": total_market_value - total_cost,
            "total_volume": total_volume,
        }

    def update_position(self, portfolio_id: str, code: str, **updates) -> None:
        """
        Update position data.
        """
        return self.modify({"portfolio_id": portfolio_id, "code": code}, updates)

    def close_position(self, portfolio_id: str, code: str) -> None:
        """
        Close a position (set volume to 0).
        """
        return self.update_position(portfolio_id, code, 
                                   volume=0, frozen_volume=0)
