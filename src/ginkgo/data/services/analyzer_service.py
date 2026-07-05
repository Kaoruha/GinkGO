# Upstream: BaseAnalyzer (分析器基类调用add_record写入数据)
# Downstream: AnalyzerRecordCRUD (数据访问层)、ClickHouse (持久化存储)
# Role: 分析器记录服务层，封装add_record并传递source_type参数






"""
Analyzer Service Module

提供分析器记录的数据访问服务，支持添加、查询、更新 analyzer 记录。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

import pandas as pd

from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
from ginkgo.data.models import MAnalyzerRecord
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult, BaseService


class AnalyzerService(BaseService):
    """
    Analyzer Service Layer

    提供分析器记录的数据访问功能：
    - 添加 analyzer 记录到数据库
    - 查询 analyzer 记录
    - 按 task_id、portfolio_id 等维度查询
    """

    def __init__(self, analyzer_crud: AnalyzerRecordCRUD):
        """
        初始化 AnalyzerService

        Args:
            analyzer_crud: AnalyzerRecord 数据访问对象
        """
        super().__init__(crud_repo=analyzer_crud)
        self._crud_repo = analyzer_crud

    def add_record(
        self,
        portfolio_id: str,
        engine_id: str,
        task_id: str,
        timestamp: str,
        value: Any,
        name: str,
        analyzer_id: str = "",
        business_timestamp: Optional[str] = None,
        source: Any = None,
    ) -> ServiceResult:
        """
        添加 analyzer 记录到数据库

        Args:
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            task_id: 运行会话ID
            timestamp: 时间戳
            value: 分析器数值
            name: 分析器名称
            analyzer_id: 分析器ID（可选）
            business_timestamp: 业务时间戳（可选）

        Returns:
            ServiceResult: 操作结果，包含创建的记录
        """
        try:
            from ginkgo.enums import SOURCE_TYPES

            # 使用 CRUD 的 create 方法
            record = self._crud_repo.create(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                task_id=task_id,
                timestamp=timestamp,
                business_timestamp=business_timestamp or timestamp,
                value=value,
                name=name,
                analyzer_id=analyzer_id,
                source=source if source is not None else SOURCE_TYPES.OTHER,
            )

            GLOG.DEBUG(f"添加 analyzer 记录成功: {name}, value={value}, timestamp={timestamp}")
            return ServiceResult.success(record)

        except Exception as e:
            GLOG.ERROR(f"添加 analyzer 记录失败: {e}")
            return ServiceResult.error(f"添加 analyzer 记录失败: {e}")

    def get_by_task_id(
        self,
        task_id: str,
        portfolio_id: Optional[str] = None,
        analyzer_name: Optional[str] = None,
        limit: int = 1000,
    ) -> ServiceResult:
        """
        按 task_id 查询 analyzer 记录

        Args:
            task_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）
            analyzer_name: 分析器名称（可选）
            limit: 返回数量限制

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_by_task_id(
                task_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=analyzer_name,
                page_size=limit,
            )

            GLOG.INFO(f"按 task_id 查询成功: task_id={task_id}, count={len(result) if result else 0}")
            return ServiceResult.success(result)

        except Exception as e:
            GLOG.ERROR(f"按 task_id 查询失败: {e}")
            return ServiceResult.error(f"按 task_id 查询失败: {e}")

    # fix(#4582): 封装 find_by_portfolio，避免 API 层直调 CRUD
    def find_by_portfolio(
        self,
        portfolio_id: str,
        analyzer_name: Optional[str] = None,
        task_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ServiceResult:
        """按 portfolio 查询 analyzer 记录

        Args:
            portfolio_id: 投资组合ID
            analyzer_name: 分析器名称（可选）
            task_id: 运行会话ID（可选）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            ServiceResult: 查询结果
        """
        try:
            records = self._crud_repo.find_by_portfolio(
                portfolio_id=portfolio_id,
                analyzer_name=analyzer_name,
                task_id=task_id,
                start_date=start_date,
                end_date=end_date,
            )
            GLOG.INFO(f"按 portfolio 查询成功: portfolio_id={portfolio_id}, count={len(records) if records else 0}")
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"按 portfolio 查询失败: {e}")
            return ServiceResult.error(f"按 portfolio 查询失败: {e}")

    def find_latest_before(
        self,
        portfolio_id: str,
        end_time: Any,
        analyzer_name: Optional[str] = None,
        use_business_time: bool = True,
    ) -> ServiceResult:
        """查询 ``end_time`` 之前最近的 analyzer 记录（按时间倒序，records[0] 为最近）。

        #6048: 封装 ``crud.find_by_time_range``，供 API 层查询上一日净资产基准，
        避免 API 层直访 CRUD 违反分层（API → Service → CRUD）。
        """
        try:
            records = self._crud_repo.find_by_time_range(
                portfolio_id=portfolio_id,
                start_time=None,
                end_time=end_time,
                use_business_time=use_business_time,
                analyzer_name=analyzer_name,
            )
            GLOG.INFO(f"按时间范围查询成功: portfolio_id={portfolio_id}, count={len(records) if records else 0}")
            return ServiceResult.success(records)
        except Exception as e:
            GLOG.ERROR(f"按时间范围查询失败: {e}")
            return ServiceResult.error(f"按时间范围查询失败: {e}")

    def get_records(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """
        通用查询 analyzer 记录（支持可选 portfolio/engine 过滤）。

        Args:
            portfolio_id: 组合 ID（可选）
            engine_id: 引擎 ID（可选）
            page_size: 返回数量限制，0 表示全部

        Returns:
            ServiceResult.data: ModelList
        """
        try:
            filters = {"is_del": False}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id
            if engine_id:
                filters["engine_id"] = engine_id

            results = self._crud_repo.find(
                filters=filters,
                page_size=page_size if page_size > 0 else None,
            )
            return ServiceResult.success(data=results)
        except Exception as e:
            GLOG.ERROR(f"查询 analyzer 记录失败: {e}")
            return ServiceResult.error(f"查询 analyzer 记录失败: {e}")

    def _build_analyzer_record_filters(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
    ) -> dict:
        """从业务参数构造 AnalyzerRecord CRUD filters。get_records_df 独立使用（DRY）。

        filter 域与现有 get_records() 一致（portfolio_id / engine_id），
        固定排除 is_del=True。未抽改 get_records()，保持纯增量。
        """
        filters = {"is_del": False}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if engine_id:
            filters["engine_id"] = engine_id
        return filters

    def get_records_df(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """出口①：data 是 pandas.DataFrame（类型即契约）。

        ADR-010：API/CLI 消费 DataFrame 语义时走此出口，不接触 ORM ModelList、
        不再绕 ``result.data.to_dataframe()``。内部 find 返 ModelList 后调
        ``to_dataframe()``；空结果返空 ``pd.DataFrame()``。
        """
        try:
            filters = self._build_analyzer_record_filters(
                portfolio_id=portfolio_id, engine_id=engine_id,
            )
            model_list = self._crud_repo.find(
                filters=filters,
                page_size=page_size if page_size > 0 else None,
            )
            df = model_list.to_dataframe() if model_list else pd.DataFrame()
            return ServiceResult.success(
                data=df,
                message=f"Retrieved {len(df)} analyzer records (DataFrame)",
            )
        except Exception as e:
            GLOG.ERROR(f"查询 analyzer 记录(df)失败: {e}")
            return ServiceResult.error(f"查询 analyzer 记录(df)失败: {e}")

    def get_latest_by_portfolio(
        self,
        portfolio_id: str,
        analyzer_name: Optional[str] = None,
        limit: int = 10
    ) -> ServiceResult:
        """
        获取指定 portfolio 的最新 analyzer 记录

        Args:
            portfolio_id: 投资组合ID
            analyzer_name: 分析器名称（可选）
            limit: 返回数量限制

        Returns:
            ServiceResult: 查询结果
        """
        try:
            filters = {"portfolio_id": portfolio_id}
            if analyzer_name:
                filters["name"] = analyzer_name

            records = self._crud_repo.find(
                filters=filters,
                page_size=limit,
                order_by="timestamp",
                desc_order=True
            )

            GLOG.INFO(f"获取最新记录成功: portfolio_id={portfolio_id}, count={len(records)}")
            return ServiceResult.success(records)

        except Exception as e:
            GLOG.ERROR(f"获取最新记录失败: {e}")
            return ServiceResult.error(f"获取最新记录失败: {e}")
