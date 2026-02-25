<<<<<<< HEAD
# Upstream: BacktestTaskService (回测任务业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MBacktestTask (回测任务MySQL模型)
# Role: BacktestTaskCRUD回测任务CRUD操作提供任务配置和状态管理功能支持交易系统功能和组件集成提供完整业务支持

=======
# Upstream: BacktestTaskService (回测任务业务服务)、BacktestTaskFactory (创建和查询回测任务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MBacktestTask (MySQL回测任务模型)
# Role: BacktestTaskCRUD回测任务CRUD操作继承BaseCRUD提供回测任务管理功能支持交易系统功能和组件集成提供完整业务支持

"""
Backtest Task CRUD Operations

回测任务的增删改查操作，支持回测列表、执行历史等功能。
"""
>>>>>>> 011-quant-research

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime
<<<<<<< HEAD
import json
=======
>>>>>>> 011-quant-research

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MBacktestTask
<<<<<<< HEAD
=======
from ginkgo.enums import SOURCE_TYPES
>>>>>>> 011-quant-research
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access
from sqlalchemy.orm import Session


<<<<<<< HEAD
@restrict_crud_access
class BacktestTaskCRUD(BaseCRUD[MBacktestTask]):
    """
    BacktestTask CRUD operations.

    提供回测任务的完整 CRUD 操作：
    - 创建任务并初始化配置
    - 查询任务（支持状态过滤）
    - 更新任务状态、进度、结果
    - 删除任务
    """

    # 类级别声明，支持自动注册
=======
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

>>>>>>> 011-quant-research
    _model_class = MBacktestTask

    def __init__(self):
        super().__init__(MBacktestTask)

    def _get_field_config(self) -> dict:
        """
<<<<<<< HEAD
        定义 BacktestTask 数据的字段配置 - 必填字段验证
=======
        定义 BacktestTask 数据的字段配置

        注意：_get_field_config() 中的所有字段都会被视为必填字段。
        非必填字段不应添加到此配置中。

        run_id 自动生成，如未指定则自动生成，因此不在此配置中。
>>>>>>> 011-quant-research

        Returns:
            dict: 字段配置字典
        """
<<<<<<< HEAD
        return {
            # 任务名称 - 非空字符串
            "name": {"type": "string", "min": 1, "max": 255},
            # 投资组合 UUID - 非空字符串
            "portfolio_uuid": {"type": "string", "min": 1, "max": 36},
            # 任务状态 - 字符串枚举（有默认值）
            "state": {
                "type": "string",
                "default": "PENDING",
                "allowed_values": ["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
            },
            # 进度 - 浮点数 0-100（有默认值）
            "progress": {"type": "float", "min": 0.0, "max": 100.0, "default": 0.0},
            # 注意：config, result, worker_id, error 等可选字段不需要在此配置
            # 因为它们有默认值 None 或可以通过 Model 的 nullable 处理
        }
=======
        return {}  # run_id 自动生成，无需必填验证
>>>>>>> 011-quant-research

    def _create_from_params(self, **kwargs) -> MBacktestTask:
        """
        Hook method: Create MBacktestTask from parameters.
<<<<<<< HEAD
        """
        # 处理 config 字典转换为 JSON
        config_value = kwargs.get("config")
        if config_value and isinstance(config_value, dict):
            config_value = json.dumps(config_value)
        elif config_value is None:
            config_value = None

        # 处理 result 字典转换为 JSON
        result_value = kwargs.get("result")
        if result_value and isinstance(result_value, dict):
            result_value = json.dumps(result_value)
        elif result_value is None:
            result_value = None

        return MBacktestTask(
            name=kwargs.get("name", "Unnamed Task"),
            portfolio_uuid=kwargs.get("portfolio_uuid", ""),
            portfolio_name=kwargs.get("portfolio_name", "Unknown Portfolio"),
            state=kwargs.get("state", "PENDING"),
            progress=kwargs.get("progress", 0.0),
            config=config_value,
            result=result_value,
            worker_id=kwargs.get("worker_id"),
            error=kwargs.get("error"),
            created_at=kwargs.get("created_at", datetime.utcnow()),
            started_at=kwargs.get("started_at"),
            completed_at=kwargs.get("completed_at"),
        )

    def _convert_input_item(self, item: Any) -> Optional[MBacktestTask]:
        """
        Hook method: Convert objects to MBacktestTask.
        """
        if hasattr(item, "name") or hasattr(item, "portfolio_uuid"):
            return MBacktestTask(
                name=getattr(item, "name", "Unnamed Task"),
                portfolio_uuid=getattr(item, "portfolio_uuid", ""),
                portfolio_name=getattr(item, "portfolio_name", "Unknown Portfolio"),
                state=getattr(item, "state", "PENDING"),
                progress=getattr(item, "progress", 0.0),
                config=getattr(item, "config", None),
                result=getattr(item, "result", None),
                worker_id=getattr(item, "worker_id", None),
                error=getattr(item, "error", None),
                created_at=getattr(item, "created_at", datetime.utcnow()),
                started_at=getattr(item, "started_at", None),
                completed_at=getattr(item, "completed_at", None),
            )
        return None

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        Define field-to-enum mappings (BacktestTask 没有枚举字段).

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {}

    def _convert_output_items(self, items: List[MBacktestTask], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MBacktestTask objects for business layer.
        """
        return items

    # Business Helper Methods
    def find_by_uuid(self, uuid: str, as_dataframe: bool = False) -> Union[List[MBacktestTask], pd.DataFrame]:
        """
        Business helper: Find task by UUID.
        """
        return self.find(filters={"uuid": uuid}, page_size=1, as_dataframe=as_dataframe)

    def find_by_state(
        self, state: str, as_dataframe: bool = False
    ) -> Union[List[MBacktestTask], pd.DataFrame]:
        """
        Business helper: Find tasks by state.

        Args:
            state: Task state (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
            as_dataframe: Return as DataFrame if True

        Returns:
            List of tasks or DataFrame
        """
        return self.find(
            filters={"state": state},
            order_by="created_at",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model",
        )

    def find_by_portfolio(
        self, portfolio_uuid: str, as_dataframe: bool = False
    ) -> Union[List[MBacktestTask], pd.DataFrame]:
        """
        Business helper: Find tasks by portfolio UUID.
        """
        return self.find(
            filters={"portfolio_uuid": portfolio_uuid},
            order_by="created_at",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model",
        )

    def update_state(self, uuid: str, state: str, error: str = None) -> None:
        """
        Update task state.

        Args:
            uuid: Task UUID
            state: New state (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
            error: Error message (optional)
        """
        update_data = {"state": state}

        # 根据状态更新时间字段
        if state == "RUNNING" and not update_data.get("started_at"):
            update_data["started_at"] = datetime.utcnow()
        elif state in ["COMPLETED", "FAILED", "CANCELLED"]:
            update_data["completed_at"] = datetime.utcnow()

        if error:
            update_data["error"] = error

        return self.modify({"uuid": uuid}, update_data)

    def update_progress(self, uuid: str, progress: float) -> None:
        """
        Update task progress.

        Args:
            uuid: Task UUID
            progress: Progress value (0-100)
        """
        return self.modify({"uuid": uuid}, {"progress": progress})

    def update_result(self, uuid: str, result: dict) -> None:
        """
        Update task result.

        Args:
            uuid: Task UUID
            result: Result dictionary
        """
        return self.modify({"uuid": uuid}, {"result": json.dumps(result)})

    def assign_worker(self, uuid: str, worker_id: str) -> None:
        """
        Assign worker to task.

        Args:
            uuid: Task UUID
            worker_id: Worker ID
        """
        return self.modify(
            {"uuid": uuid},
            {"worker_id": worker_id, "state": "RUNNING", "started_at": datetime.utcnow()}
        )

    def get_active_tasks(self, as_dataframe: bool = False) -> Union[List[MBacktestTask], pd.DataFrame]:
        """
        Get all active (PENDING or RUNNING) tasks.

        Returns:
            List of active tasks or DataFrame
        """
        return self.find(
            filters={"state__in": ["PENDING", "RUNNING"]},
            order_by="created_at",
            desc_order=True,
            as_dataframe=as_dataframe,
            output_type="model",
        )

    def delete_by_uuid(self, uuid: str, session=None) -> None:
        """
        Business helper: Delete task by UUID.
        """
        if not uuid:
            raise ValueError("uuid不能为空")

        GLOG.WARN(f"删除回测任务 {uuid}")
        return self.remove({"uuid": uuid}, session)
=======

        设计原则：会话实体的 uuid = run_id（主键就是会话ID）
        """
        from ginkgo.trading.core.identity import IdentityUtils

        source_value = kwargs.get("source", SOURCE_TYPES.SIM)
        if isinstance(source_value, SOURCE_TYPES):
            source_value = source_value.value
        else:
            source_value = SOURCE_TYPES.validate_input(source_value) or -1

        # 生成 run_id（如果未提供），使用与 uuid 相同的规则
        run_id = kwargs.get("run_id") or IdentityUtils.generate_run_id()

        model = MBacktestTask(
            uuid=run_id,  # 会话实体的 uuid = run_id
            run_id=run_id,
            name=kwargs.get("name", ""),  # 用户可指定名称
            engine_id=kwargs.get("engine_id", ""),
            portfolio_id=kwargs.get("portfolio_id", ""),
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
            final_portfolio_value=kwargs.get("final_portfolio_value", "0"),
            total_pnl=kwargs.get("total_pnl", "0"),
            max_drawdown=kwargs.get("max_drawdown", "0"),
            sharpe_ratio=kwargs.get("sharpe_ratio", "0"),
            annual_return=kwargs.get("annual_return", "0"),
            win_rate=kwargs.get("win_rate", "0"),
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

    def get_by_run_id(self, run_id: str) -> Optional[MBacktestTask]:
        """
        通过 run_id 获取任务

        Args:
            run_id: 运行会话ID

        Returns:
            MBacktestTask or None
        """
        results = self.find(filters={"run_id": run_id, "is_del": False})
        if results and len(results) > 0:
            return results[0]
        return None

    # 向后兼容
    def get_task_by_task_id(self, task_id: str) -> Optional[MBacktestTask]:
        """向后兼容方法，调用 get_by_run_id"""
        return self.get_by_run_id(task_id)

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
>>>>>>> 011-quant-research
