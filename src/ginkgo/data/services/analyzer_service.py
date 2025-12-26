"""
Analyzer Service Module

提供分析器记录的数据访问服务，支持添加、查询、更新 analyzer 记录。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
from ginkgo.data.models.model_analyzer_record import MAnalyzerRecord
from ginkgo.libs import GLOG, time_logger, retry
from ginkgo.data.services.base_service import ServiceResult, BaseService


class AnalyzerService(BaseService):
    """
    Analyzer Service Layer

    提供分析器记录的数据访问功能：
    - 添加 analyzer 记录到数据库
    - 查询 analyzer 记录
    - 按 run_id、portfolio_id 等维度查询
    """

    def __init__(self, analyzer_crud: AnalyzerRecordCRUD):
        """
        初始化 AnalyzerService

        Args:
            analyzer_crud: AnalyzerRecord 数据访问对象
        """
        super().__init__(crud_repo=analyzer_crud)
        self._crud_repo = analyzer_crud

    @time_logger
    @retry(max_try=3)
    def add_record(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str,
        timestamp: str,
        value: Any,
        name: str,
        analyzer_id: str = "",
        business_timestamp: Optional[str] = None
    ) -> ServiceResult:
        """
        添加 analyzer 记录到数据库

        Args:
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            run_id: 运行会话ID
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
                run_id=run_id,
                timestamp=timestamp,
                business_timestamp=business_timestamp or timestamp,
                value=value,
                name=name,
                analyzer_id=analyzer_id,
                source=SOURCE_TYPES.OTHER,
            )

            GLOG.DEBUG(f"添加 analyzer 记录成功: {name}, value={value}, timestamp={timestamp}")
            return ServiceResult.success(record)

        except Exception as e:
            GLOG.ERROR(f"添加 analyzer 记录失败: {e}")
            return ServiceResult.error(f"添加 analyzer 记录失败: {e}")

    @time_logger
    @retry(max_try=3)
    def get_by_run_id(
        self,
        run_id: str,
        portfolio_id: Optional[str] = None,
        analyzer_name: Optional[str] = None,
        limit: int = 1000,
        as_dataframe: bool = False
    ) -> ServiceResult:
        """
        按 run_id 查询 analyzer 记录

        Args:
            run_id: 运行会话ID
            portfolio_id: 投资组合ID（可选）
            analyzer_name: 分析器名称（可选）
            limit: 返回数量限制
            as_dataframe: 是否返回 DataFrame 格式

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_by_run_id(
                run_id=run_id,
                portfolio_id=portfolio_id,
                analyzer_name=analyzer_name,
                page_size=limit,
                as_dataframe=as_dataframe
            )

            GLOG.INFO(f"按 run_id 查询成功: run_id={run_id}, count={len(result) if result else 0}")
            return ServiceResult.success(result)

        except Exception as e:
            GLOG.ERROR(f"按 run_id 查询失败: {e}")
            return ServiceResult.error(f"按 run_id 查询失败: {e}")

    @time_logger
    @retry(max_try=3)
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
