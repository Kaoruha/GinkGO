# Upstream: FileCRUD, PortfolioCRUD, 文件管理服务
# Downstream: BaseCRUD, MPortfolioFileMapping模型, FILE_TYPES枚举
# Role: 投资组合-文件映射CRUD，管理Portfolio与文件(策略脚本等)的绑定关系






from ginkgo.data.access_control import restrict_crud_access

from typing import List, Optional, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MPortfolioFileMapping
from ginkgo.enums import SOURCE_TYPES, FILE_TYPES
from ginkgo.libs import GLOG, cache_with_expiration


@restrict_crud_access
class PortfolioFileMappingCRUD(BaseCRUD[MPortfolioFileMapping]):
    """
    PortfolioFileMapping CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MPortfolioFileMapping

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

    # ADR-029 §Decision 1：转换钩子 override 已退役。
    # 调用方 mapping_service.add_batch:413 传 MPortfolioFileMapping 实例。

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str) -> list:
        """
        Business helper: Find file mappings by portfolio ID.
        """
        filters = {"portfolio_id": portfolio_id}

        return self.find(filters=filters, order_by="uuid")

    def count_portfolios_by_files(self, file_ids: List[str]) -> Dict[str, int]:
        """
        Business helper: 每个组件被多少个不同 Portfolio 持有（SQL 层聚合）。

        GROUP BY + COUNT(DISTINCT) 在库内完成，只返回每组件一行计数，
        不把绑定行拉回应用层——成本随页组件数而非表行数增长
        （配合 file_id 索引为 B+ 树定位，见 model 的 index=True）。

        Returns:
            Dict[str, int]: {file_id: distinct portfolio 数}，未绑定的组件不在 map 中
        """
        if not file_ids:
            return {}

        conn = self._get_connection()
        try:
            with conn.get_session() as session:
                from sqlalchemy import func

                rows = (
                    session.query(
                        self.model_class.file_id.label("file_id"),
                        func.count(func.distinct(self.model_class.portfolio_id)).label("cnt"),
                    )
                    .filter(self.model_class.file_id.in_(list(file_ids)))
                    .group_by(self.model_class.file_id)
                    .all()
                )
                return {r.file_id: int(r.cnt) for r in rows if r.file_id}
        except Exception as e:
            GLOG.ERROR(f"count_portfolios_by_files failed: {e}")
            return {}

    def find_by_file(self, file_id: str) -> list:
        """
        Business helper: Find portfolio mappings by file ID.
        """
        filters = {"file_id": file_id}
        
        return self.find(filters=filters, order_by="uuid")

    def get_files_for_portfolio(self, portfolio_id: str) -> List[str]:
        """
        Business helper: Get all file IDs for a portfolio.
        """
        mappings = self.find_by_portfolio(portfolio_id)
        return [m.file_id for m in mappings if m.file_id]

    def get_portfolios_for_file(self, file_id: str) -> List[str]:
        """
        Business helper: Get all portfolio IDs for a file.
        """
        mappings = self.find_by_file(file_id)
        return [m.portfolio_id for m in mappings if m.portfolio_id]


    def delete_mapping(self, portfolio_id: str, file_id: str) -> None:
        """
        Delete a specific mapping.
        """
        GLOG.DEBUG(f"删除组合-文件映射: {portfolio_id} -> {file_id}")
        return self.remove({"portfolio_id": portfolio_id, "file_id": file_id})
