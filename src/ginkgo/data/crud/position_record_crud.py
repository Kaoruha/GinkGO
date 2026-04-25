# Upstream: 回测引擎, 分析器, PositionService
# Downstream: BaseCRUD, MPositionRecord模型
# Role: 持仓记录CRUD，管理历史持仓快照(成本、数量、冻结量等)，用于回测分析和偏差检测






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MPositionRecord
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration


@restrict_crud_access
class PositionRecordCRUD(BaseCRUD[MPositionRecord]):
    """
    PositionRecord CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MPositionRecord

    def __init__(self):
        super().__init__(MPositionRecord)

    def _get_field_config(self) -> dict:
        """
        定义 PositionRecord 数据的字段配置 - 核心字段必填，其他字段可选
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 组合ID - 必填字符串，最大32字符
            "portfolio_id": {"type": "string", "min": 1, "max": 32},
            # 引擎ID - 必填字符串，最大32字符  
            "engine_id": {"type": "string", "min": 1, "max": 32},
            # 股票代码 - 必填字符串，最大32字符
            "code": {"type": "string", "min": 1, "max": 32},
            # 成本 - 非负数值
            "cost": {"type": ["decimal", "float", "int"], "min": 0},
            # 持仓量 - 非负整数
            "volume": {"type": ["int", "float"], "min": 0},
            # 冻结量 - 非负整数
            "frozen_volume": {"type": ["int", "float"], "min": 0},
            # 冻结资金 - 非负数值
            "frozen_money": {"type": ["decimal", "float", "int"], "min": 0},
            # 价格 - 非负数值
            "price": {"type": ["decimal", "float", "int"], "min": 0},
            # 费用 - 非负数值
            "fee": {"type": ["decimal", "float", "int"], "min": 0},
            # 时间戳 - datetime 或字符串
            "timestamp": {"type": ["datetime", "string"]},

            # 业务时间戳 - datetime 或字符串，可选
            "business_timestamp": {"type": ["datetime", "string", "none"]},
        }

    def _create_from_params(self, **kwargs) -> MPositionRecord:
        """
        Hook method: Create MPositionRecord from parameters.
        """
        return MPositionRecord(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            task_id=kwargs.get("task_id", ""),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            code=kwargs.get("code"),
            cost=to_decimal(kwargs.get("cost", 0)),
            volume=kwargs.get("volume", 0),
            frozen_volume=kwargs.get("frozen_volume", 0),
            frozen_money=to_decimal(kwargs.get("frozen_money", 0)),
            price=to_decimal(kwargs.get("price", 0)),
            fee=to_decimal(kwargs.get("fee", 0)),
            business_timestamp=datetime_normalize(kwargs.get("business_timestamp")),
        )

    def _convert_input_item(self, item: Any) -> Optional[MPositionRecord]:
        """
        Hook method: Convert position record objects to MPositionRecord.
        """
        # Assuming 'item' could be a dictionary or an object with attributes
        if isinstance(item, dict):
            return MPositionRecord(
                portfolio_id=item.get('portfolio_id'),
                engine_id=item.get('engine_id', ''),
                timestamp=datetime_normalize(item.get('timestamp', datetime.now())),
                code=item.get('code', ''),
                cost=to_decimal(item.get('cost', 0)),
                volume=item.get('volume', 0),
                frozen_volume=item.get('frozen_volume', 0),
                frozen_money=to_decimal(item.get('frozen_money', 0)),
                price=to_decimal(item.get('price', 0)),
                fee=to_decimal(item.get('fee', 0)),
                business_timestamp=datetime_normalize(item.get('business_timestamp', None)),
            )
        elif hasattr(item, 'portfolio_id') and hasattr(item, 'code') and hasattr(item, 'volume'):
            return MPositionRecord(
                portfolio_id=getattr(item, 'portfolio_id', ''),
                engine_id=getattr(item, 'engine_id', ''),
                timestamp=datetime_normalize(getattr(item, 'timestamp', datetime.now())),
                code=getattr(item, 'code', ''),
                cost=to_decimal(getattr(item, 'cost', 0)),
                volume=getattr(item, 'volume', 0),
                frozen_volume=getattr(item, 'frozen_volume', 0),
                frozen_money=to_decimal(getattr(item, 'frozen_money', 0)),
                price=to_decimal(getattr(item, 'price', 0)),
                fee=to_decimal(getattr(item, 'fee', 0)),
                business_timestamp=datetime_normalize(getattr(item, 'business_timestamp', None)),
            )
        return None


    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES
        }

    def _convert_models_to_business_objects(self, models: List) -> List:
        """
        🎯 Convert models to business objects.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of models (business object doesn't exist yet)
        """
        # For now, return models as-is since business object doesn't exist yet
        return models

    def _convert_output_items(self, items: List[MPositionRecord], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MPositionRecord objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(
        self,
        portfolio_id: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        code: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        desc_order: bool = True,
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Find position records by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)
        if code:
            filters["code"] = code

        return self.find(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="timestamp",
            desc_order=desc_order,
        )

    def find_by_code(
        self,
        code: str,
        portfolio_id: Optional[str] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Find position records by stock code.
        """
        filters = {"code": code}
        
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
        )

    def find_current_positions(
        self,
        portfolio_id: str,
        min_volume: Optional[int] = None,
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Find current positions (latest for each code).
        """
        filters = {"portfolio_id": portfolio_id}
        
        if min_volume is not None:
            filters["volume__gte"] = min_volume

        return self.find(
            filters=filters,
            order_by="timestamp",
            desc_order=True,
        )

    def find_positions_with_volume(
        self,
        portfolio_id: str,
        min_volume: int = 1,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Find position records with volume greater than threshold.
        """
        filters = {"portfolio_id": portfolio_id, "volume__gte": min_volume}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(
            filters=filters,
            order_by="volume",
            desc_order=True,  # Largest positions first
        )

    def find_frozen_positions(
        self,
        portfolio_id: str,
        min_frozen_volume: int = 1,
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Find positions with frozen volume.
        """
        filters = {"portfolio_id": portfolio_id, "frozen_volume__gte": min_frozen_volume}

        return self.find(
            filters=filters,
            order_by="frozen_volume",
            desc_order=True,
        )

    def get_latest_position(
        self, portfolio_id: str, code: str
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Get latest position record for a specific code.
        """
        return self.find(
            filters={"portfolio_id": portfolio_id, "code": code},
            page_size=1,
            order_by="timestamp",
            desc_order=True,
        )

    def delete_by_portfolio(self, portfolio_id: str) -> None:
        """
        Business helper: Delete all position records for a portfolio.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id不能为空")
        
        GLOG.WARN(f"删除组合 {portfolio_id} 的所有position_record记录")
        return self.remove({"portfolio_id": portfolio_id})

    def delete_by_portfolio_and_date_range(
        self, 
        portfolio_id: str, 
        start_date: Optional[Any] = None, 
        end_date: Optional[Any] = None
    ) -> None:
        """
        Business helper: Delete position records by portfolio and date range.
        """
        if not portfolio_id:
            raise ValueError("portfolio_id不能为空")
        
        filters = {"portfolio_id": portfolio_id}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.remove(filters)

    def delete_zero_positions(self, portfolio_id: str) -> None:
        """
        Business helper: Delete position records with zero volume.
        """
        GLOG.INFO(f"删除组合 {portfolio_id} 的零持仓记录")
        return self.remove({"portfolio_id": portfolio_id, "volume": 0})

    def count_by_portfolio(self, portfolio_id: str) -> int:
        """
        Business helper: Count position records for a specific portfolio.
        """
        return self.count({"portfolio_id": portfolio_id})

    def count_active_positions(self, portfolio_id: str, min_volume: int = 1) -> int:
        """
        Business helper: Count active positions (volume > 0).
        """
        return self.count({"portfolio_id": portfolio_id, "volume__gte": min_volume})

    def get_portfolio_summary(self, portfolio_id: str, as_of_date: Optional[Any] = None) -> dict:
        """
        Business helper: Get portfolio position summary.
        """
        filters = {"portfolio_id": portfolio_id}
        
        if as_of_date:
            filters["timestamp__lte"] = datetime_normalize(as_of_date)
        
        
        if not positions:
            return {
                "total_positions": 0,
                "active_positions": 0,
                "total_cost": 0,
                "total_market_value": 0,
                "total_frozen_volume": 0,
                "total_frozen_money": 0,
                "codes": [],
            }
        
        active_positions = [p for p in positions if p.volume > 0]
        
        summary = {
            "total_positions": len(positions),
            "active_positions": len(active_positions),
            "total_cost": sum(float(p.cost) for p in positions if p.cost),
            "total_market_value": sum(float(p.price) * p.volume for p in active_positions if p.price and p.volume),
            "total_frozen_volume": sum(p.frozen_volume for p in positions if p.frozen_volume),
            "total_frozen_money": sum(float(p.frozen_money) for p in positions if p.frozen_money),
            "codes": list(set(p.code for p in active_positions)),
        }
        
        return summary

    def get_position_pnl(
        self, 
        portfolio_id: str, 
        code: str, 
        start_date: Optional[Any] = None, 
        end_date: Optional[Any] = None
    ) -> dict:
        """
        Business helper: Calculate position P&L for a specific code.
        """
        filters = {"portfolio_id": portfolio_id, "code": code}
        
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)
        
        
        if not positions:
            return {
                "code": code,
                "total_cost": 0,
                "current_market_value": 0,
                "unrealized_pnl": 0,
                "total_fees": 0,
                "position_count": 0,
            }
        
        # Sort by timestamp to get chronological order
        positions.sort(key=lambda x: x.timestamp)
        
        latest_position = positions[-1]
        total_cost = sum(float(p.cost) for p in positions if p.cost)
        total_fees = sum(float(p.fee) for p in positions if p.fee)
        current_market_value = float(latest_position.price) * latest_position.volume if latest_position.price else 0
        
        return {
            "code": code,
            "total_cost": total_cost,
            "current_market_value": current_market_value,
            "unrealized_pnl": current_market_value - total_cost,
            "total_fees": total_fees,
            "position_count": len(positions),
        }

    def get_all_codes(self) -> List[str]:
        """
        Business helper: Get all distinct stock codes with position records.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            codes = self.find(distinct_field="code")
            return [code for code in codes if code]
        except Exception as e:
            GLOG.ERROR(f"Failed to get position record codes: {e}")
            return []

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio IDs with position records.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_ids = self.find(distinct_field="portfolio_id")
            return [pid for pid in portfolio_ids if pid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get position record portfolio ids: {e}")
            return []

    def find_by_business_time(
        self,
        portfolio_id: str,
        start_business_time: Optional[Any] = None,
        end_business_time: Optional[Any] = None,
        code: Optional[str] = None,
        min_volume: Optional[int] = None,
    ) -> ModelList[MPositionRecord]:
        """
        Business helper: Find position records by business time range.

        Args:
            portfolio_id: Portfolio ID to query
            start_business_time: Start of business time range (optional)
            end_business_time: End of business time range (optional)
            code: Stock code filter (optional)
            min_volume: Minimum volume filter (optional)

        Returns:
            List of MPositionRecord models or DataFrame
        """
        filters = {"portfolio_id": portfolio_id}

        if start_business_time:
            filters["business_timestamp__gte"] = datetime_normalize(start_business_time)
        if end_business_time:
            filters["business_timestamp__lte"] = datetime_normalize(end_business_time)
        if code:
            filters["code"] = code
        if min_volume is not None:
            filters["volume__gte"] = min_volume

        return self.find(
            filters=filters,
            order_by="business_timestamp",
            desc_order=True,
        )
