from ..access_control import restrict_crud_access

from typing import List, Optional, Union, Any
import pandas as pd
from datetime import datetime

from .base_crud import BaseCRUD
from ..models import MPortfolioFileMapping
from ...enums import SOURCE_TYPES, FILE_TYPES
from ...libs import GLOG, cache_with_expiration


@restrict_crud_access
class PortfolioFileMappingCRUD(BaseCRUD[MPortfolioFileMapping]):
    """
    PortfolioFileMapping CRUD operations.
    """

    def __init__(self):
        super().__init__(MPortfolioFileMapping)

    def _get_field_config(self) -> dict:
        """
        定义 PortfolioFileMapping 数据的字段配置
        
        Returns:
            dict: 字段配置字典
        """
        return {
            'portfolio_id': {'type': 'string', 'min': 1},
            'file_id': {'type': 'string', 'min': 1}
            # mapping_type、is_active、source字段移除验证配置，使用模型支持的字段或默认值
        }

    def _create_from_params(self, **kwargs) -> MPortfolioFileMapping:
        """
        Hook method: Create MPortfolioFileMapping from parameters.
        只使用模型实际支持的字段：portfolio_id, file_id, name, type, source
        """
        return MPortfolioFileMapping(
            portfolio_id=kwargs.get("portfolio_id"),
            file_id=kwargs.get("file_id"),
            name=kwargs.get("name", "ginkgo_bind"),
            type=FILE_TYPES.validate_input(kwargs.get("type", FILE_TYPES.OTHER)),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MPortfolioFileMapping]:
        """
        Hook method: Convert mapping objects to MPortfolioFileMapping.
        只使用模型实际支持的字段：portfolio_id, file_id, name, type, source
        """
        if hasattr(item, 'portfolio_id') and hasattr(item, 'file_id'):
            return MPortfolioFileMapping(
                portfolio_id=getattr(item, 'portfolio_id'),
                file_id=getattr(item, 'file_id'),
                name=getattr(item, 'name', 'ginkgo_bind'),
                type=FILE_TYPES.validate_input(getattr(item, 'type', FILE_TYPES.OTHER)),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _convert_output_items(self, items: List[MPortfolioFileMapping], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MPortfolioFileMapping objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str,
                         as_dataframe: bool = False) -> Union[List[MPortfolioFileMapping], pd.DataFrame]:
        """
        Business helper: Find file mappings by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}
        
        return self.find(filters=filters, order_by="uuid",
                        as_dataframe=as_dataframe, output_type="model")

    def find_by_file(self, file_id: str,
                    as_dataframe: bool = False) -> Union[List[MPortfolioFileMapping], pd.DataFrame]:
        """
        Business helper: Find portfolio mappings by file ID.
        """
        filters = {"file_id": file_id}
        
        return self.find(filters=filters, order_by="uuid",
                        as_dataframe=as_dataframe, output_type="model")

    def get_files_for_portfolio(self, portfolio_id: str) -> List[str]:
        """
        Business helper: Get all file IDs for a portfolio.
        """
        mappings = self.find_by_portfolio(portfolio_id, as_dataframe=False)
        return [m.file_id for m in mappings if m.file_id]

    def get_portfolios_for_file(self, file_id: str) -> List[str]:
        """
        Business helper: Get all portfolio IDs for a file.
        """
        mappings = self.find_by_file(file_id, as_dataframe=False)
        return [m.portfolio_id for m in mappings if m.portfolio_id]


    def delete_mapping(self, portfolio_id: str, file_id: str) -> None:
        """
        Delete a specific mapping.
        """
        GLOG.INFO(f"删除组合-文件映射: {portfolio_id} -> {file_id}")
        return self.remove({"portfolio_id": portfolio_id, "file_id": file_id})
