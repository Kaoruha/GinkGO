# Upstream: BacktestTaskService (回测任务业务服务)、BacktestTaskFactory (创建和查询回测任务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MBacktestTask (MySQL回测任务模型)
# Role: BacktestTaskCRUD回测任务CRUD操作继承BaseCRUD提供回测任务管理功能

"""
Backtest Task CRUD Operations

回测任务的增删改查操作，支持回测列表、执行历史等功能。
"""

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MBacktestTask
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access
from sqlalchemy.orm import Session


# 向后兼容别名
RunRecordCRUD = None  # 将在类定义后设置


@restrict_crud_access
class BacktestTaskCRUD(BaseCRUD[MBacktestTask]):
    """
    Backtest Task CRUD operations.

    回测任务的增删改查操作，包括：
    - 任务列表查询（按引擎、按投资组合筛选）
    - 任务状态管理
    - 任务结果记录
    """

    _model_class = MBacktestTask

    def __init__(self):
        super().__init__(MBacktestTask)

    def _get_field_config(self) -> dict:
        """
        定义 BacktestTask 数据的字段配置

        注意：_get_field_config() 中的所有字段都会被视为必填字段。
        非必填字段不应添加到此配置中。

        task_id 自动生成，如未指定则自动生成，因此不在此配置中。

        Returns:
            dict: 字段配置字典
        """
        return {}  # task_id 自动生成，无需必填验证

    def _create_from_params(self, **kwargs) -> MBacktestTask:
        """
        Hook method: Create MBacktestTask from parameters.

        设计原则：会话实体的 uuid = task_id（主键就是会话ID）
        """
        from ginkgo.entities import IdentityUtils

        source_value = kwargs.get("source", SOURCE_TYPES.SIM)
        if isinstance(source_value, SOURCE_TYPES):
            source_value = source_value.value
        else:
            source_value = SOURCE_TYPES.validate_input(source_value) or -1

        # 生成 task_id（如果未提供），使用与 uuid 相同的规则
        task_id = kwargs.get("task_id") or IdentityUtils.generate_task_id()

        # #5577 #5443: 日期字段从字符串转为 datetime
        raw_start = kwargs.get("backtest_start_date")
        raw_end = kwargs.get("backtest_end_date")
        backtest_start_date = datetime_normalize(raw_start) if raw_start else None
        backtest_end_date = datetime_normalize(raw_end) if raw_end else None

        model = MBacktestTask(
            uuid=task_id,  # 会话实体的 uuid = task_id
            task_id=task_id,
            name=kwargs.get("name", ""),  # 用户可指定名称
            engine_id=kwargs.get("engine_id", ""),
            portfolio_id=kwargs.get("portfolio_id", ""),
            backtest_start_date=backtest_start_date,
            backtest_end_date=backtest_end_date,
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            status=kwargs.get("status", "created"),
            error_message=kwargs.get("error_message", ""),
            total_orders=kwargs.get("total_orders", 0),
            total_signals=kwargs.get("total_signals", 0),
            total_positions=kwargs.get("total_positions", 0),
            total_events=kwargs.get("total_events", 0),
            config_snapshot=kwargs.get("config_snapshot", "{}"),
            environment_info=kwargs.get("environment_info", "{}"),
            final_portfolio_value=kwargs.get("final_portfolio_value", 0.0),
            total_pnl=kwargs.get("total_pnl", 0.0),
            max_drawdown=kwargs.get("max_drawdown", 0.0),
            sharpe_ratio=kwargs.get("sharpe_ratio", 0.0),
            annual_return=kwargs.get("annual_return", 0.0),
            win_rate=kwargs.get("win_rate", 0.0),
            source=source_value,
        )

        return model

    def get_tasks_by_engine(self, engine_id: str, page: int = 0, page_size: int = 20) -> ModelList:
        """
        获取指定引擎的所有回测任务

        Args:
            engine_id: 引擎UUID
            page: 页码
            page_size: 每页数量

        Returns:
            ModelList: 任务列表
        """
        return self.find(
            filters={"engine_id": engine_id, "is_del": False},
            order_by="create_at", desc_order=True,
            page=page,
            page_size=page_size
        )

    def get_tasks_by_portfolio(self, portfolio_id: str, page: int = 0, page_size: int = 20) -> ModelList:
        """
        获取指定投资组合的所有回测任务

        Args:
            portfolio_id: 投资组合UUID
            page: 页码
            page_size: 每页数量

        Returns:
            ModelList: 任务列表
        """
        return self.find(
            filters={"portfolio_id": portfolio_id, "is_del": False},
            order_by="create_at", desc_order=True,
            page=page,
            page_size=page_size
        )

    def get_running_tasks(self) -> ModelList:
        """
        获取所有运行中的任务

        Returns:
            ModelList: 运行中的任务列表
        """
        return self.find(
            filters={"status": "running", "is_del": False},
            order_by="create_at", desc_order=True
        )

    def get_completed_tasks(self, page: int = 0, page_size: int = 20) -> ModelList:
        """
        获取已完成的任务列表

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            ModelList: 已完成任务列表
        """
        return self.find(
            filters={"status": "completed", "is_del": False},
            order_by="-end_time",
            page=page,
            page_size=page_size
        )

    def count_by_status(self, status: str) -> int:
        """
        统计指定状态的任务数量

        Args:
            status: 任务状态

        Returns:
            int: 数量
        """
        return self.count(filters={"status": status, "is_del": False})

    def get_by_task_id(self, task_id: str) -> Optional[MBacktestTask]:
        """
        通过 task_id 获取任务

        Args:
            task_id: 任务ID

        Returns:
            MBacktestTask or None
        """
        results = self.find(filters={"task_id": task_id, "is_del": False})
        if results and len(results) > 0:
            return results[0]
        return None

    def get_by_uuid(self, uuid: str) -> Optional[MBacktestTask]:
        """
        通过 UUID 获取任务

        Args:
            uuid: 任务 UUID

        Returns:
            MBacktestTask or None
        """
        results = self.find(filters={"uuid": uuid, "is_del": False})
        if results and len(results) > 0:
            return results[0]
        return None

    def fuzzy_search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> ModelList[MBacktestTask]:
        """
        模糊搜索回测任务，支持 UUID、名称、task_id 的部分匹配。

        Args:
            query: 搜索字符串
            fields: 搜索字段列表。默认: ['uuid', 'name', 'task_id']

        Returns:
            ModelList of matching tasks
        """
        if not query or not query.strip():
            return ModelList([], self)

        query_lower = query.lower().strip()

        if fields is None:
            fields = ['uuid', 'name', 'task_id']

        all_results = []
        seen_uuids = set()

        if 'uuid' in fields:
            try:
                results = self.find(filters={"uuid__like": f"%{query_lower}%", "is_del": False}, page_size=limit)
                for item in results:
                    if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                        all_results.append(item)
                        seen_uuids.add(item.uuid)
            except Exception as e:
                GLOG.WARN(f"UUID fuzzy search failed: {e}")

        if 'name' in fields:
            try:
                results = self.find(filters={"name__like": f"%{query_lower}%", "is_del": False}, page_size=limit)
                for item in results:
                    if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                        all_results.append(item)
                        seen_uuids.add(item.uuid)
            except Exception as e:
                GLOG.WARN(f"Name fuzzy search failed: {e}")

        if 'task_id' in fields:
            try:
                results = self.find(filters={"task_id__like": f"%{query_lower}%", "is_del": False}, page_size=limit)
                for item in results:
                    if hasattr(item, 'uuid') and item.uuid not in seen_uuids:
                        all_results.append(item)
                        seen_uuids.add(item.uuid)
            except Exception as e:
                GLOG.WARN(f"Task ID fuzzy search failed: {e}")

        # #6572: 多字段合并去重后按 limit 截断
        if limit is not None:
            all_results = all_results[:limit]

        return ModelList(all_results, self)

    def update_task_status(
        self,
        uuid: str,
        status: str,
        error_message: str = "",
        **result_fields
    ) -> int:
        """
        更新任务状态

        Args:
            uuid: 任务 UUID（与 task_id 等价）
            status: 新状态
            error_message: 错误信息
            **result_fields: 结果字段 (final_portfolio_value, total_pnl, etc.)

        Returns:
            int: 更新的记录数
        """
        updates = {"status": status, "error_message": error_message}
        updates.update(result_fields)

        # #5424: running 时补 start_time，与 end_time 对称。调用方（如 progress_tracker）
        # 显式传入时尊重其值；CLI 同步路径漏传时由数据层兜底，避免 start_time 恒 NULL。
        if status == "running" and "start_time" not in updates:
            updates["start_time"] = datetime.now()

        if status in ["completed", "failed", "stopped"]:
            updates["end_time"] = datetime.now()

        # 统一按 uuid 查找（task_id 与 uuid 等价）
        count = self.modify(filters={"uuid": uuid}, updates=updates)
        return count if count is not None else 0

    def get_tasks_page_filtered(
        self,
        engine_id: str = None,
        portfolio_id: str = None,
        status: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = 0,
        page_size: int = 20
    ) -> ModelList:
        """
        分页获取筛选后的任务列表

        Args:
            engine_id: 引擎ID筛选
            portfolio_id: 投资组合ID筛选
            status: 状态筛选
            start_date: 开始日期筛选
            end_date: 结束日期筛选
            page: 页码
            page_size: 每页数量

        Returns:
            ModelList: 任务列表
        """
        filters = {"is_del": False}

        if engine_id:
            filters["engine_id"] = engine_id
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if status:
            filters["status"] = status

        # TODO: 日期范围筛选需要在 BaseCRUD 中支持

        return self.find(
            filters=filters,
            order_by="create_at", desc_order=True,
            page=page,
            page_size=page_size
        )


# 向后兼容别名
RunRecordCRUD = BacktestTaskCRUD

