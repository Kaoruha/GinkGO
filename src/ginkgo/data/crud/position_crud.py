# Upstream: PortfolioService (状态持久化时全量替换/加载持仓快照)、PositionService (持仓查询业务服务)
# Downstream: BaseCRUD (继承标准CRUD能力)、MPosition (MySQL持仓模型)、Position (业务持仓实体)
# Role: 持仓记录 CRUD，提供按组合/代码/业务时间查询、持仓快照批量创建与删除，支持状态持久化






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MPosition
from ginkgo.entities import Position
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration


@restrict_crud_access
class PositionCRUD(BaseCRUD[MPosition]):
    """
    Position CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MPosition

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
            },

            # 业务时间戳 - datetime 或字符串，可选
            'business_timestamp': {
                'type': ['datetime', 'string', 'none']
            }
        }

    def _create_from_params(self, **kwargs) -> MPosition:
        """
        Hook method: Create MPosition from parameters.
        """
        return MPosition(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            run_id=kwargs.get("run_id", ""),  # 添加 run_id 字段
            code=kwargs.get("code"),
            cost=to_decimal(kwargs.get("cost", 0)),
            volume=kwargs.get("volume", 0),
            frozen_volume=kwargs.get("frozen_volume", 0),
            frozen_money=to_decimal(kwargs.get("frozen_money", 0)),
            price=to_decimal(kwargs.get("price", 0)),
            fee=to_decimal(kwargs.get("fee", 0)),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
            business_timestamp=datetime_normalize(kwargs.get("business_timestamp")),
        )

    def _convert_input_item(self, item: Any) -> Optional[MPosition]:
        """
        Hook method: Convert position objects to MPosition.
        """
        if hasattr(item, 'portfolio_id') and hasattr(item, 'code'):
            return MPosition(
                portfolio_id=getattr(item, 'portfolio_id'),
                engine_id=getattr(item, 'engine_id', ''),
                run_id=getattr(item, 'run_id', ""),  # 添加 run_id 字段
                code=getattr(item, 'code'),
                cost=to_decimal(getattr(item, 'cost', 0)),
                volume=getattr(item, 'volume', 0),
                frozen_volume=getattr(item, 'frozen_volume', 0),
                frozen_money=to_decimal(getattr(item, 'frozen_money', 0)),
                price=to_decimal(getattr(item, 'price', 0)),
                fee=to_decimal(getattr(item, 'fee', 0)),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
                business_timestamp=datetime_normalize(getattr(item, 'business_timestamp', None)),
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for Position.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES  # 数据源字段映射
        }

    def _convert_models_to_business_objects(self, models: List[MPosition]) -> List[Position]:
        """
        🎯 Convert MPosition models to Position business objects.

        Args:
            models: List of MPosition models with enum fields already fixed

        Returns:
            List of Position business objects
        """
        business_objects = []
        for model in models:
            # 转换为业务对象 (此时枚举字段已经是正确的枚举对象)
            position = Position.from_model(model)
            business_objects.append(position)

        return business_objects

    def _convert_output_items(self, items: List[MPosition], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MPosition objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str, min_volume: int = 0) -> ModelList[MPosition]:
        """
        Business helper: Find positions by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        if min_volume > 0:
            filters["volume__gte"] = min_volume
            
        return self.find(filters=filters, order_by="cost", desc_order=True)

    def find_by_code(self, code: str, portfolio_id: Optional[str] = None) -> ModelList[MPosition]:
        """
        Business helper: Find positions by stock code.
        """
        filters = {"code": code}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
            
        return self.find(filters=filters, order_by="volume", desc_order=True)

    def get_position(self, portfolio_id: str, code: str) -> Optional[MPosition]:
        """
        Business helper: Get specific position.
        """
        result = self.find(filters={"portfolio_id": portfolio_id, "code": code}, page_size=1)
        return result[0] if result else None

    def get_active_positions(self, portfolio_id: str, min_volume: int = 1) -> ModelList[MPosition]:
        """
        Business helper: Get active positions (volume > 0).
        """
        return self.find_by_portfolio(portfolio_id, min_volume)

    def get_portfolio_value(self, portfolio_id: str) -> dict:
        """
        Business helper: Get portfolio total value.
        """
        positions = self.find_by_portfolio(portfolio_id)
        
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

    def find_by_business_time(
        self,
        portfolio_id: str,
        start_business_time: Optional[Any] = None,
        end_business_time: Optional[Any] = None,
        min_volume: int = 0,
    ) -> List[MPosition]:
        """
        Business helper: Find positions by business time range.

        Args:
            portfolio_id: Portfolio ID to query
            start_business_time: Start of business time range (optional)
            end_business_time: End of business time range (optional)
            min_volume: Minimum volume filter (default: 0)

        Returns:
            List of MPosition models
        """
        filters = {"portfolio_id": portfolio_id}

        if min_volume > 0:
            filters["volume__gte"] = min_volume
        if start_business_time:
            filters["business_timestamp__gte"] = datetime_normalize(start_business_time)
        if end_business_time:
            filters["business_timestamp__lte"] = datetime_normalize(end_business_time)

        return self.find(
            filters=filters,
            order_by="business_timestamp",
            desc_order=True,
            output_type="model"
        )

    def delete_by_portfolio(self, portfolio_id: str) -> int:
        """
        删除指定 portfolio 的所有持仓快照（用于状态持久化时全量替换）

        Args:
            portfolio_id: 投资组合UUID

        Returns:
            int: 删除的记录数
        """
        try:
            self.delete(filters={"portfolio_id": portfolio_id})
            GLOG.DEBUG(f"Deleted all position snapshots for portfolio {portfolio_id[:8]}")
            return 1
        except Exception as e:
            GLOG.ERROR(f"Failed to delete positions for portfolio {portfolio_id[:8]}: {e}")
            return 0

    def batch_create(self, positions: list) -> int:
        """
        批量创建持仓快照（用于状态持久化时全量写入）

        Args:
            positions: MPosition 模型列表

        Returns:
            int: 创建的记录数
        """
        try:
            for pos in positions:
                self.create(pos)
            return len(positions)
        except Exception as e:
            GLOG.ERROR(f"Failed to batch create positions: {e}")
            return 0
