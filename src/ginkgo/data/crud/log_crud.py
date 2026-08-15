# Upstream: LogService（delete_logs_by_task_id 经此操作 CH 日志三表）
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MBacktestLog/MComponentLog/MPerformanceLog (ClickHouse 日志三表)
# Role: CH 日志三表 CRUD——日志域数据操作统一走 CRUD 层（分层 Service → CRUD → DB）；
#       写入仍由 vector 直写 CH，查询在 LogService 保留独立 engine（历史路径）






from ginkgo.data.access_control import restrict_crud_access

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MBacktestLog, MComponentLog, MPerformanceLog


@restrict_crud_access
class BacktestLogCRUD(BaseCRUD[MBacktestLog]):
    """ginkgo_logs_backtest 表 CRUD（重跑清理用，查询仍走 LogService）。"""

    _model_class = MBacktestLog

    def __init__(self):
        super().__init__(MBacktestLog)

    def _get_field_config(self) -> dict:
        return {}


@restrict_crud_access
class ComponentLogCRUD(BaseCRUD[MComponentLog]):
    """ginkgo_logs_component 表 CRUD（重跑清理用，查询仍走 LogService）。"""

    _model_class = MComponentLog

    def __init__(self):
        super().__init__(MComponentLog)

    def _get_field_config(self) -> dict:
        return {}


@restrict_crud_access
class PerformanceLogCRUD(BaseCRUD[MPerformanceLog]):
    """ginkgo_logs_performance 表 CRUD（重跑清理用，查询仍走 LogService）。"""

    _model_class = MPerformanceLog

    def __init__(self):
        super().__init__(MPerformanceLog)

    def _get_field_config(self) -> dict:
        return {}
