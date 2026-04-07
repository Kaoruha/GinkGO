# Upstream: AnalyzerService (分析器服务层)、BaseCRUD (抽象基类)
# Downstream: MAnalyzerRecord (ClickHouse分析器记录模型)、SOURCE_TYPES (枚举映射)
# Role: 分析器记录CRUD，支持SOURCE_TYPES枚举字段映射和多维度查询






from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MAnalyzerRecord
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, Number, to_decimal, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class AnalyzerRecordCRUD(BaseCRUD[MAnalyzerRecord]):
    """
    AnalyzerRecord CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MAnalyzerRecord

    def __init__(self):
        super().__init__(MAnalyzerRecord)

    def _get_field_config(self) -> dict:
        """
        定义 AnalyzerRecord 数据的字段配置 - 所有字段都是必填的

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

            # 运行会话ID - 非空字符串
            'run_id': {
                'type': 'string',
                'min': 1
            },

            # 分析器名称 - 非空字符串
            'name': {
                'type': 'string',
                'min': 1,
                'max': 50
            },

            # 分析器ID - 可选
            'analyzer_id': {
                'type': 'string',
                'min': 0
            },

            # 时间戳 - datetime 或字符串
            'timestamp': {
                'type': ['datetime', 'string']
            },

            # 业务时间戳 - datetime 或字符串，可选
            'business_timestamp': {
                'type': ['datetime', 'string', 'none']
            },

            # 分析结果值 - 数值
            'value': {
                'type': ['decimal', 'float', 'int']
            },

            # 数据源 - 枚举值
            'source': {
                'type': 'enum',
                'choices': [
                    SOURCE_TYPES.SIM,
                    SOURCE_TYPES.LIVE,
                    SOURCE_TYPES.BACKTEST,
                    SOURCE_TYPES.PAPER_REPLAY,
                    SOURCE_TYPES.PAPER_LIVE,
                    SOURCE_TYPES.OTHER
                ]
            }
        }

    def _create_from_params(self, **kwargs) -> MAnalyzerRecord:
        """
        Hook method: Create MAnalyzerRecord from parameters.
        """
        return MAnalyzerRecord(
            portfolio_id=kwargs.get("portfolio_id"),
            engine_id=kwargs.get("engine_id"),
            run_id=kwargs.get("run_id", ""),
            name=kwargs.get("name", kwargs.get("analyzer_name", "")),
            analyzer_id=kwargs.get("analyzer_id", ""),
            timestamp=datetime_normalize(kwargs.get("timestamp")),
            business_timestamp=datetime_normalize(kwargs.get("business_timestamp")),
            value=to_decimal(kwargs.get("value", 0)),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
        )

    def _convert_input_item(self, item: Any) -> Optional[MAnalyzerRecord]:
        """
        Hook method: Convert analyzer record objects to MAnalyzerRecord.
        """
        if hasattr(item, 'portfolio_id') and (hasattr(item, 'name') or hasattr(item, 'analyzer_name')):
            return MAnalyzerRecord(
                portfolio_id=getattr(item, 'portfolio_id'),
                engine_id=getattr(item, 'engine_id', ''),
                name=getattr(item, 'name', getattr(item, 'analyzer_name', '')),
                analyzer_id=getattr(item, 'analyzer_id', ''),
                timestamp=datetime_normalize(getattr(item, 'timestamp', datetime.now())),
                business_timestamp=datetime_normalize(getattr(item, 'business_timestamp', None)),
                value=to_decimal(getattr(item, 'value', 0)),
                source=SOURCE_TYPES.validate_input(getattr(item, 'source', SOURCE_TYPES.SIM)),
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for AnalyzerRecord.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'source': SOURCE_TYPES  # 数据源字段映射
        }

    def _convert_models_to_business_objects(self, models: List[MAnalyzerRecord]) -> List[MAnalyzerRecord]:
        """
        🎯 Convert MAnalyzerRecord models to business objects.

        Args:
            models: List of MAnalyzerRecord models with enum fields already fixed

        Returns:
            List of MAnalyzerRecord models (AnalyzerRecord business object doesn't exist yet)
        """
        # For now, return models as-is since AnalyzerRecord business object doesn't exist yet
        return models

    def _convert_output_items(self, items: List[MAnalyzerRecord], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MAnalyzerRecord objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_portfolio(self, portfolio_id: str, analyzer_name: Optional[str] = None,
                         start_date: Optional[Any] = None, end_date: Optional[Any] = None,
                         as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Find analyzer records by portfolio.
        """
        filters = {"portfolio_id": portfolio_id}

        if analyzer_name:
            filters["name"] = analyzer_name
        if start_date:
            filters["timestamp__gte"] = datetime_normalize(start_date)
        if end_date:
            filters["timestamp__lte"] = datetime_normalize(end_date)

        return self.find(filters=filters, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe)

    def find_by_analyzer(self, analyzer_name: str, portfolio_id: Optional[str] = None,
                        as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Find records by analyzer name.
        """
        filters = {"name": analyzer_name}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id

        return self.find(filters=filters, order_by="timestamp", desc_order=True,
                        as_dataframe=as_dataframe)

    def get_latest_values(self, portfolio_id: str, as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Get latest analyzer values for a portfolio.
        """
        return self.find_by_portfolio(portfolio_id, page_size=10, as_dataframe=as_dataframe)

    def get_portfolio_ids(self) -> List[str]:
        """
        Business helper: Get all distinct portfolio_ids from analyzer_record table.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            portfolio_ids = self.find(distinct_field="portfolio_id")
            return [pid for pid in portfolio_ids if pid is not None]
        except Exception as e:
            GLOG.ERROR(f"Failed to get portfolio ids from analyzer records: {e}")
            return []

    def get_engine_ids(self) -> List[str]:
        """
        Business helper: Get all distinct engine_ids from analyzer_record table.
        Uses base CRUD's DISTINCT support for consistent null byte handling.
        """
        try:
            engine_ids = self.find(distinct_field="engine_id")
            return [eid for eid in engine_ids if eid is not None]
        except Exception as e:
            GLOG.ERROR(f"Failed to get engine ids from analyzer records: {e}")
            return []

    def find_by_business_time(self, portfolio_id: str, start_business_time: Optional[Any] = None,
                             end_business_time: Optional[Any] = None, analyzer_name: Optional[str] = None,
                             as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Find analyzer records by business timestamp range.
        """
        filters = {"portfolio_id": portfolio_id}

        if analyzer_name:
            filters["name"] = analyzer_name
        if start_business_time:
            filters["business_timestamp__gte"] = datetime_normalize(start_business_time)
        if end_business_time:
            filters["business_timestamp__lte"] = datetime_normalize(end_business_time)

        return self.find(filters=filters, order_by="business_timestamp", desc_order=True,
                        as_dataframe=as_dataframe)

    def find_by_time_range(self, portfolio_id: str, start_time: Optional[Any] = None,
                          end_time: Optional[Any] = None, use_business_time: bool = True,
                          analyzer_name: Optional[str] = None, as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        Business helper: Find analyzer records by time range (can use either timestamp or business_timestamp).

        Args:
            portfolio_id: Portfolio ID to filter
            start_time: Start time of the range
            end_time: End time of the range
            use_business_time: If True, use business_timestamp; if False, use timestamp
            analyzer_name: Optional analyzer name filter
            as_dataframe: Return results as DataFrame if True
        """
        filters = {"portfolio_id": portfolio_id}

        if analyzer_name:
            filters["name"] = analyzer_name

        time_field = "business_timestamp" if use_business_time else "timestamp"
        if start_time:
            filters[f"{time_field}__gte"] = datetime_normalize(start_time)
        if end_time:
            filters[f"{time_field}__lte"] = datetime_normalize(end_time)

        return self.find(filters=filters, order_by=time_field, desc_order=True,
                        as_dataframe=as_dataframe)

    def get_by_run_id(self, run_id: str, portfolio_id: Optional[str] = None,
                      analyzer_name: Optional[str] = None, page_size: int = 1000,
                      as_dataframe: bool = False) -> Union[List[MAnalyzerRecord], pd.DataFrame]:
        """
        按 run_id 查询 analyzer 记录（支持 result 命令）

        Args:
            run_id: 运行会话ID（必需）
            portfolio_id: 投资组合ID（可选，为空则查询所有portfolio）
            analyzer_name: 分析器名称（可选，为空则查询所有analyzer）
            page_size: 分页大小（限制返回条数）
            as_dataframe: 返回 pandas DataFrame

        Returns:
            List[MAnalyzerRecord] 或 pd.DataFrame

        Examples:
            # 查询某次运行的所有 analyzer 记录
            records = crud.get_by_run_id("a3b5c7d9e2f1a4b6c8d0e2f4a6b8c0d2")

            # 查询某次运行的特定 portfolio 和 analyzer
            records = crud.get_by_run_id(
                run_id="a3b5c7d9e2f1a4b6c8d0e2f4a6b8c0d2",
                portfolio_id="present_portfolio_uuid",
                analyzer_name="net_value"
            )
        """
        filters = {"run_id": run_id}

        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if analyzer_name:
            filters["name"] = analyzer_name

        return self.find(filters=filters, order_by="timestamp", desc_order=True,
                        page_size=page_size, as_dataframe=as_dataframe)
