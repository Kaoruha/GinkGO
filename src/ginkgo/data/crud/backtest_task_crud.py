# Upstream: BacktestTaskService (回测任务业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器)、MBacktestTask (回测任务MySQL模型)
# Role: BacktestTaskCRUD回测任务CRUD操作提供任务配置和状态管理功能支持交易系统功能和组件集成提供完整业务支持


from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime
import json

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.models import MBacktestTask
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.data.access_control import restrict_crud_access
from sqlalchemy.orm import Session


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
    _model_class = MBacktestTask

    def __init__(self):
        super().__init__(MBacktestTask)

    def _get_field_config(self) -> dict:
        """
        定义 BacktestTask 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
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

    def _create_from_params(self, **kwargs) -> MBacktestTask:
        """
        Hook method: Create MBacktestTask from parameters.
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
