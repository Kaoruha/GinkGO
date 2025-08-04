from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MPortfolio
from ...enums import SOURCE_TYPES
from ...libs import datetime_normalize, GLOG
from ..access_control import restrict_crud_access


@restrict_crud_access
class PortfolioCRUD(BaseCRUD[MPortfolio]):
    """
    Portfolio CRUD operations - Only overrides hook methods, never template methods.
    
    Features:
    - Inherits ALL decorators (@time_logger, @retry, @cache) from BaseCRUD template methods
    - Only provides Portfolio-specific conversion and creation logic via hook methods
    - Supports portfolio management and tracking
    - Maintains architectural purity of template method pattern
    """

    def __init__(self):
        super().__init__(MPortfolio)

    def _get_field_config(self) -> dict:
        """
        定义 Portfolio 数据的字段配置 - 所有字段都是必填的
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 投资组合名称 - 非空字符串
            'name': {
                'type': 'string',
                'min': 1,
                'max': 64  # 与模型String(64)一致
            },
            
            # 回测开始时间 - datetime 或字符串
            'backtest_start_date': {
                'type': ['datetime', 'string']
            },
            
            # 回测结束时间 - datetime 或字符串
            'backtest_end_date': {
                'type': ['datetime', 'string']
            },
            
            # 是否实盘 - 布尔值
            'is_live': {
                'type': 'bool'
            }
            
            # source字段移除验证配置，使用模型默认值 SOURCE_TYPES.OTHER
        }

    def _create_from_params(self, **kwargs) -> MPortfolio:
        """Hook method: Create MPortfolio from parameters."""
        return MPortfolio(
            name=kwargs.get("name", "test_portfolio"),
            backtest_start_date=datetime_normalize(kwargs.get("backtest_start_date", datetime.now())),
            backtest_end_date=datetime_normalize(kwargs.get("backtest_end_date", datetime.now())),
            is_live=kwargs.get("is_live", False),
            source=kwargs.get("source", SOURCE_TYPES.SIM),
        )

    def _convert_input_item(self, item: Any) -> Optional[MPortfolio]:
        """Hook method: Convert portfolio objects to MPortfolio."""
        if hasattr(item, 'name'):
            return MPortfolio(
                name=getattr(item, 'name', 'test_portfolio'),
                backtest_start_date=datetime_normalize(getattr(item, 'backtest_start_date', datetime.now())),
                backtest_end_date=datetime_normalize(getattr(item, 'backtest_end_date', datetime.now())),
                is_live=getattr(item, 'is_live', False),
                source=getattr(item, 'source', SOURCE_TYPES.SIM),
            )
        return None

    def _convert_output_items(self, items: List[MPortfolio], output_type: str = "model") -> List[Any]:
        """Hook method: Convert MPortfolio objects for business layer."""
        return items

    # Business Helper Methods
    def find_by_uuid(self, uuid: str, as_dataframe: bool = False) -> Union[List[MPortfolio], pd.DataFrame]:
        """Find portfolio by UUID."""
        return self.find(filters={"uuid": uuid}, page_size=1,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_name_pattern(self, name_pattern: str, as_dataframe: bool = False) -> Union[List[MPortfolio], pd.DataFrame]:
        """Find portfolios by name pattern."""
        return self.find(filters={"name__like": name_pattern}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_live_status(self, is_live: bool, as_dataframe: bool = False) -> Union[List[MPortfolio], pd.DataFrame]:
        """Find portfolios by live status."""
        return self.find(filters={"is_live": is_live}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe, output_type="model")

    def get_all_uuids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio UUIDs.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_uuids = self.find(distinct_field="uuid")
            return [puid for puid in portfolio_uuids if puid]
        except Exception as e:
            GLOG.ERROR(f"Failed to get portfolio uuids: {e}")
            return []

    def delete_by_uuid(self, uuid: str) -> None:
        """Delete portfolio by UUID."""
        if not uuid:
            raise ValueError("uuid不能为空")
        
        GLOG.WARN(f"删除组合 {uuid}")
        return self.remove({"uuid": uuid})

    def update_live_status(self, uuid: str, is_live: bool) -> None:
        """Update portfolio live status."""
        return self.modify({"uuid": uuid}, {"is_live": is_live})