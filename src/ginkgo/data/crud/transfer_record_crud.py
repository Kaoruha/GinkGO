# Upstream: 回测引擎, 资金管理模块, TransferService
# Downstream: BaseCRUD, MTransferRecord模型, Transfer实体
# Role: 资金划转记录CRUD，管理出入金和资金调拨的历史记录，支持多方向和状态筛选






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MTransferRecord
from ginkgo.entities import Transfer
from ginkgo.enums import (
    CAPITALADJUSTMENT_TYPES,
    MARKET_TYPES,
    SOURCE_TYPES,
    TRANSFERDIRECTION_TYPES,
    TRANSFERSTATUS_TYPES,
)
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration


@restrict_crud_access
class TransferRecordCRUD(BaseCRUD[MTransferRecord]):
    """
    TransferRecord CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MTransferRecord

    def __init__(self):
        super().__init__(MTransferRecord)

    def _get_field_config(self) -> dict:
        """
        定义 TransferRecord 数据的字段配置 - 所有字段都是必填的
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合ID - 非空字符串
            'portfolio_id': {
                'type': 'string',
                'min': 1
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
            
            # 转账金额 - 必须大于0
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

    def _create_from_params(self, **kwargs) -> MTransferRecord:
        """
        Hook method: Create MTransferRecord from parameters.
        """
        return MTransferRecord(
            portfolio_id=kwargs.get("portfolio_id"),
            direction=kwargs.get("direction"),
            market=kwargs.get("market"),
            money=to_decimal(kwargs.get("money", 0)),
            status=kwargs.get("status"),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MTransferRecord]:
        """
        Hook method: Convert Transfer objects to MTransferRecord.
        """
        if isinstance(item, Transfer):
            return MTransferRecord(
                portfolio_id=item.portfolio_id,
                direction=item.direction,
                market=item.market,
                money=item.money,
                status=item.status,
                timestamp=item.timestamp,
                source=SOURCE_TYPES.validate_input(getattr(item, "source", SOURCE_TYPES.SIM)),
            )
        return None


    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'capitaladjustment': CAPITALADJUSTMENT_TYPES,
            'market': MARKET_TYPES,
            'source': SOURCE_TYPES,
            'transferdirection': TRANSFERDIRECTION_TYPES,
            'transferstatus': TRANSFERSTATUS_TYPES
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

    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert objects for business layer.
        """
        return items

    def _convert_output_items(
        self, items: List[MTransferRecord], output_type: str = "model"
    ) -> List[Any]:
        """
        Hook method: Convert MTransferRecord objects to Transfer objects.
        """
        if output_type == "transfer":
            return [
                Transfer(
                    portfolio_id=item.portfolio_id,
                    direction=item.direction,
                    market=item.market,
                    money=item.money,
                    status=item.status,
                    timestamp=item.timestamp,
                    uuid=item.uuid,
                )
                for item in items
            ]
        return items

    def find_by_portfolio(
        self,
        portfolio_id: str,
        direction: Optional[TRANSFERDIRECTION_TYPES] = None,
        status: Optional[TRANSFERSTATUS_TYPES] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> List[Transfer]:
        """
        Business helper: Find transfer records by portfolio.
        """
        filters = {"portfolio_id": portfolio_id}
        if direction:
            filters["direction"] = direction
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
            output_type="transfer",
        )

    def get_total_transfer_amount(
        self,
        portfolio_id: str,
        direction: TRANSFERDIRECTION_TYPES,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> float:
        """
        Business helper: Get total transfer amount for a portfolio.
        """
        records = self.find_by_portfolio(
            portfolio_id, direction, TRANSFERSTATUS_TYPES.FILLED, start_date, end_date
        )
        return sum(float(r.money) for r in records if r.money)

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio_ids from transfer_record table.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_ids = self.find(distinct_field="portfolio_id")
            return [pid for pid in portfolio_ids if pid is not None]
        except Exception as e:
            GLOG.ERROR(f"Failed to get portfolio ids from transfer records: {e}")
            return []

