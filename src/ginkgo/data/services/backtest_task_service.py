# Upstream: CLI Commands (ginkgo backtest list/run/delete)、API Server (回测任务API)
# Downstream: BaseService (继承提供服务基础能力)、BacktestTaskCRUD (回测任务CRUD)、AnalyzerService (分析服务)
# Role: BacktestTaskService回测任务服务提供回测任务管理功能

"""
Backtest Task Service

回测任务业务服务，提供：
- 回测任务 CRUD
- 任务状态管理
- 任务结果查询
- 与引擎、投资组合的关联管理
"""

import time
import json
from typing import List, Union, Any, Optional, Dict
import pandas as pd
from datetime import datetime, timedelta, timezone

from ginkgo.libs import cache_with_expiration, retry, GLOG
from ginkgo.libs.data.number import convert_to_float
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.interfaces.kafka_topics import KafkaTopics


class BacktestTaskService(BaseService):
    """
    回测任务服务

    管理回测任务的完整生命周期：
    - 创建任务
    - 执行任务
    - 查询结果
    - 删除任务
    """

    def __init__(self, crud_repo, analyzer_service=None, engine_service=None,
                 portfolio_service=None,
                 signal_crud=None, order_crud=None, position_crud=None,
                 position_record_crud=None, analyzer_record_crud=None,
                 order_record_crud=None, transfer_record_crud=None,
                 transfer_crud=None, signal_tracker_crud=None):
        """
        初始化服务

        Args:
            crud_repo: BacktestTaskCRUD 实例
            analyzer_service: 分析服务（可选，用于获取净值数据等）
            engine_service: 引擎服务（可选，用于关联引擎）
            portfolio_service: 投资组合服务（可选，用于关联投资组合）
            signal_crud ~ signal_tracker_crud: 重跑清理用的 CRUD（可选，由容器注入）
        """
        super().__init__(
            crud_repo=crud_repo,
            analyzer_service=analyzer_service,
            engine_service=engine_service,
            portfolio_service=portfolio_service,
            signal_crud=signal_crud,
            order_crud=order_crud,
            position_crud=position_crud,
            position_record_crud=position_record_crud,
            analyzer_record_crud=analyzer_record_crud,
            order_record_crud=order_record_crud,
            transfer_record_crud=transfer_record_crud,
            transfer_crud=transfer_crud,
            signal_tracker_crud=signal_tracker_crud,
        )
        GLOG.set_log_category("component")

    def get(self, task_id: str = None, engine_id: str = None, portfolio_id: str = None,
            status: str = None) -> ServiceResult:
        """
        获取回测任务

        Args:
            task_id: 任务ID
            engine_id: 引擎ID
            portfolio_id: 投资组合ID
            status: 任务状态

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_tasks_page_filtered(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                status=status,
                page=0,
                page_size=1000,
            )

            return ServiceResult.success(result, f"Successfully retrieved backtest tasks")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest tasks: {str(e)}")

    def get_by_id(self, backtest_id: str) -> ServiceResult:
        """
        通过 ID 获取单个任务（支持 uuid 或 task_id）

        Args:
            backtest_id: 任务标识（可以是 uuid 或 task_id）

        Returns:
            ServiceResult: 查询结果
        """
        try:
            # 先尝试用 uuid 精确匹配
            result = self._crud_repo.get_by_uuid(backtest_id)
            if result is None:
                # 如果 uuid 查不到，尝试用 task_id 查询
                result = self._crud_repo.get_by_task_id(backtest_id)
            if result is None:
                return ServiceResult.error(f"Backtest task not found: {backtest_id}")
            return ServiceResult.success(result, f"Successfully retrieved backtest task")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest task: {str(e)}")

    def fuzzy_search(
        self,
        query: str,
        fields: Optional[List[str]] = None
    ) -> ServiceResult:
        """
        模糊搜索回测任务，支持 UUID 部分匹配、名称匹配等。

        Args:
            query: 搜索字符串
            fields: 搜索字段列表。默认: ['uuid', 'name', 'task_id']

        Returns:
            ServiceResult: 查询结果
        """
        try:
            if not query or not query.strip():
                return ServiceResult.success(ModelList([], self._crud_repo))

            results = self._crud_repo.fuzzy_search(query, fields)
            return ServiceResult.success(results)

        except Exception as e:
            return ServiceResult.error(f"Backtest task fuzzy search failed: {str(e)}")

    def get_by_task_id(self, task_id: str) -> ServiceResult:
        """
        通过 task_id 获取单个任务

        Args:
            task_id: 任务ID

        Returns:
            ServiceResult: 查询结果
        """
        try:
            result = self._crud_repo.get_by_task_id(task_id)
            if result is None:
                return ServiceResult.error(f"Backtest task not found: {task_id}")
            return ServiceResult.success(result, f"Successfully retrieved backtest task")

        except Exception as e:
            return ServiceResult.error(f"Failed to get backtest task: {str(e)}")

    def list(self, page: int = 0, page_size: int = 20, engine_id: str = None,
             portfolio_id: str = None, status: str = None) -> ServiceResult:
        """
        获取回测任务列表

        Args:
            page: 页码
            page_size: 每页数量
            engine_id: 引擎ID筛选
            portfolio_id: 投资组合ID筛选
            status: 状态筛选

        Returns:
            ServiceResult: 列表结果
        """
        try:
            result = self._crud_repo.get_tasks_page_filtered(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                status=status,
                page=page,
                page_size=page_size
            )

            # 获取总数（应用相同的筛选条件）
            count_filters = {"is_del": False}
            if status:
                count_filters["status"] = status
            if engine_id:
                count_filters["engine_id"] = engine_id
            if portfolio_id:
                count_filters["portfolio_id"] = portfolio_id

            total = self._crud_repo.count(filters=count_filters)

            return ServiceResult.success({
                "data": result,
                "total": total,
                "page": page,
                "page_size": page_size
            }, f"Successfully retrieved backtest task list")

        except Exception as e:
            return ServiceResult.error(f"Failed to list backtest tasks: {str(e)}")

    @retry(max_try=3)
    def create(self, name: str = "", engine_id: str = "", portfolio_id: str = "",
               config_snapshot: dict = None, **kwargs) -> ServiceResult:
        """
        创建回测任务

        Args:
            name: 任务名称（可选，用户可读标识）
            engine_id: 所属引擎ID
            portfolio_id: 关联投资组合ID
            config_snapshot: 配置快照
            **kwargs: 其他参数

        Returns:
            ServiceResult: 创建结果
        """
        try:
            # 创建任务 (task_id 自动等于 uuid)
            task_data = {
                "name": name,
                "engine_id": engine_id,
                "portfolio_id": portfolio_id,
                "config_snapshot": json.dumps(config_snapshot or {}),
                **kwargs
            }

            task = self._crud_repo.create(**task_data)

            GLOG.INFO(f"Created backtest task: {task.uuid[:8]}...")

            return ServiceResult.success(task, f"Backtest task created successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to create backtest task: {e}")
            return ServiceResult.error(f"Failed to create backtest task: {str(e)}")

    @retry(max_try=3)
    def update(self, uuid: str, **updates) -> ServiceResult:
        """
        更新回测任务

        Args:
            uuid: 任务 UUID
            **updates: 更新字段

        Returns:
            ServiceResult: 更新结果
        """
        try:
            # 检查任务是否存在
            existing = self._crud_repo.get_by_uuid(uuid)
            if not existing:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 执行更新
            updated_count = self._crud_repo.modify(filters={"uuid": uuid}, updates=updates)

            if updated_count == 0:
                return ServiceResult.error(f"Failed to update backtest task: {uuid}")

            GLOG.INFO(f"Updated backtest task: {uuid[:8]}...")

            return ServiceResult.success({"uuid": uuid, "updated_fields": list(updates.keys())},
                                         f"Backtest task updated successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to update backtest task {uuid[:8]}...: {e}")
            return ServiceResult.error(f"Failed to update backtest task: {str(e)}")

    @retry(max_try=3)
    def update_status(self, uuid: str, status: str, error_message: str = "",
                      **result_fields) -> ServiceResult:
        """
        更新任务状态

        Args:
            uuid: 任务标识（可以是 uuid 或 task_id）
            status: 新状态 (created/pending/running/completed/failed/stopped)
            error_message: 错误信息
            **result_fields: 结果字段

        Returns:
            ServiceResult: 更新结果
        """
        try:
            valid_statuses = ["created", "pending", "running", "completed", "failed", "stopped"]
            if status not in valid_statuses:
                return ServiceResult.error(f"Invalid status: {status}")

            # 查找任务，支持 uuid 或 task_id
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_task_id(uuid)
            if not task:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 使用真实的 uuid 更新
            real_uuid = task.uuid
            updated_count = self._crud_repo.update_task_status(
                uuid=real_uuid,
                status=status,
                error_message=error_message,
                **result_fields
            )

            if updated_count == 0:
                return ServiceResult.error(f"Backtest task not found: {real_uuid}")

            GLOG.INFO(f"Updated task {real_uuid[:8]}... status to: {status}")

            return ServiceResult.success({"uuid": real_uuid, "task_id": task.task_id, "status": status},
                                         f"Task status updated to {status}")

        except Exception as e:
            GLOG.ERROR(f"Failed to update task status: {e}")
            return ServiceResult.error(f"Failed to update task status: {str(e)}")

    @retry(max_try=3)
    def delete(self, uuid: str) -> ServiceResult:
        """
        删除回测任务（软删除）

        Args:
            uuid: 任务 UUID

        Returns:
            ServiceResult: 删除结果
        """
        try:
            # 检查任务是否存在
            existing = self._crud_repo.get_by_uuid(uuid)
            if not existing:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 执行软删除
            self._crud_repo.soft_remove(filters={"uuid": uuid})

            GLOG.INFO(f"Deleted backtest task: {uuid[:8]}...")

            return ServiceResult.success({"uuid": uuid}, f"Backtest task deleted successfully")

        except Exception as e:
            GLOG.ERROR(f"Failed to delete backtest task {uuid[:8]}...: {e}")
            return ServiceResult.error(f"Failed to delete backtest task: {str(e)}")

    def cleanup_orphan_tasks(self, timeout_minutes: int = 30) -> ServiceResult:
        """
        清理孤儿回测任务（#4853）。

        扫描 status=running 但 start_time 早于 timeout_minutes 的任务，标记为 failed。
        处理两类孤儿：
        - Worker 重启期间 Kafka 消息丢失（派发成功但 Worker 未消费）
        - 派发期未被 send 返回值检查拦截的历史残留（本方法上线前的存量）

        与 portfolio_service.reset_stale_running() 同构：状态机兜底，防永久 running。

        Args:
            timeout_minutes: running 状态超时阈值（分钟），默认 30。

        Returns:
            ServiceResult: data 含 cleaned（标记 failed 数量）与 total_running（扫描时 running 总数）。
        """
        try:
            running = self._crud_repo.get_running_tasks()
            # 阈值语态绑死 worker 写入端：progress_tracker.py:218 写 naive local
            # datetime.now()（宿主 Asia/Shanghai UTC+8）。两端必须同语态比较，
            # 否则 naive 北京时间被 replace(tzinfo=utc) 当 UTC 解释会看起来年轻 8h，
            # 30min timeout 实际变 ~8h30min（#4853 PR #6565 review 抓的 bug）。
            # 治本（worker 改 aware UTC）属全仓 naive→UTC 迁移，超出本 PR 范围，
            # 迁移完成时同步此行回 datetime.now(timezone.utc)。
            threshold = datetime.now() - timedelta(minutes=timeout_minutes)
            cleaned = 0

            for task in running:
                st = task.start_time
                if st is None:
                    # start_time 残缺无法判定，跳过（不崩，留给下次或人工）。
                    continue

                if st < threshold:
                    self.update_status(
                        task.uuid, status="failed",
                        error_message=(
                            f"Orphan task: running > {timeout_minutes}min without progress "
                            "(worker lost Kafka message or crashed)"
                        ),
                    )
                    cleaned += 1
                    GLOG.INFO(f"Marked orphan backtest task {task.uuid[:8]}... as failed")

            if cleaned > 0:
                GLOG.INFO(f"Cleaned {cleaned}/{len(running)} orphan running backtest tasks")

            return ServiceResult.success(
                {"cleaned": cleaned, "total_running": len(running)},
                f"清理 {cleaned} 个孤儿 running 任务",
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to cleanup orphan backtest tasks: {e}")
            return ServiceResult.error(f"Failed to cleanup orphan backtest tasks: {str(e)}")

    def get_statistics(self) -> ServiceResult:
        """
        获取回测任务统计信息

        Returns:
            ServiceResult: 统计结果
        """
        try:
            total = self._crud_repo.count(filters={"is_del": False})
            created = self._crud_repo.count(filters={"status": "created", "is_del": False})
            pending = self._crud_repo.count(filters={"status": "pending", "is_del": False})
            running = self._crud_repo.count(filters={"status": "running", "is_del": False})
            completed = self._crud_repo.count(filters={"status": "completed", "is_del": False})
            failed = self._crud_repo.count(filters={"status": "failed", "is_del": False})
            stopped = self._crud_repo.count(filters={"status": "stopped", "is_del": False})

            return ServiceResult.success({
                "total": total,
                "created": created,
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "stopped": stopped
            }, f"Statistics retrieved successfully")

        except Exception as e:
            return ServiceResult.error(f"Failed to get statistics: {str(e)}")

    def get_netvalue_data(self, task_id: str, portfolio_id: str = "") -> ServiceResult:
        """
        获取任务的净值曲线数据

        Args:
            task_id: 任务ID
            portfolio_id: 投资组合ID（可选）

        Returns:
            ServiceResult: 净值数据
        """
        try:
            from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

            # 使用汇总器获取净值数据
            aggregator = BacktestResultAggregator(
                analyzer_service=self._analyzer_service
            )

            result = aggregator.get_net_value_data(task_id, portfolio_id)
            return ServiceResult.success(result, "Net value data retrieved")

        except Exception as e:
            return ServiceResult.error(f"Failed to get net value data: {str(e)}")

    def compare(self, task_ids: List[str]) -> ServiceResult:
        """
        对比多个回测任务

        Args:
            task_ids: 任务ID列表

        Returns:
            ServiceResult: 对比结果
        """
        try:
            if not task_ids or len(task_ids) < 2:
                return ServiceResult.error("At least 2 tasks required for comparison")

            tasks = []
            for task_id in task_ids:
                task = self._crud_repo.get_by_uuid(task_id)
                if task:
                    tasks.append(task)

            if len(tasks) < 2:
                return ServiceResult.error("Not enough valid tasks found")

            # 构建对比数据
            comparison = {
                "task_ids": task_ids,
                "metrics": {}
            }

            # 提取指标
            metric_fields = ["total_pnl", "max_drawdown", "sharpe_ratio", "annual_return", "win_rate"]
            for field in metric_fields:
                comparison["metrics"][field] = {}
                for task in tasks:
                    value = getattr(task, field, "0")
                    comparison["metrics"][field][task.uuid] = value

            return ServiceResult.success(comparison, "Comparison completed")

        except Exception as e:
            GLOG.ERROR(f"Failed to compare tasks: {e}")
            return ServiceResult.error(f"Failed to compare tasks: {str(e)}")

    def exists(self, task_id: str = None, uuid: str = None) -> ServiceResult:
        """
        检查任务是否存在

        Args:
            task_id: 任务ID
            uuid: 任务 UUID

        Returns:
            ServiceResult: 存在性检查结果
        """
        try:
            if uuid:
                exists = self._crud_repo.exists(filters={"uuid": uuid, "is_del": False})
            elif task_id:
                exists = self._crud_repo.exists(filters={"task_id": task_id, "is_del": False})
            else:
                return ServiceResult.error("task_id or uuid is required")

            return ServiceResult.success({"exists": exists}, "Existence check completed")

        except Exception as e:
            return ServiceResult.error(f"Failed to check existence: {str(e)}")

    def update_progress(self, uuid: str, progress: float = None,
                        current_stage: str = None, current_date: str = None) -> ServiceResult:
        """
        更新任务进度（用于SSE实时推送）

        Args:
            uuid: 任务标识（可以是 uuid 或 task_id）
            progress: 进度百分比 0-100
            current_stage: 当前阶段 (DATA_PREPARING/ENGINE_BUILDING/RUNNING/FINALIZING)
            current_date: 当前处理的业务日期

        Returns:
            ServiceResult: 更新结果
        """
        try:
            updates = {}
            if progress is not None:
                updates["progress"] = int(min(100, max(0, progress)))
            if current_stage is not None:
                updates["current_stage"] = current_stage
            if current_date is not None:
                updates["current_date"] = current_date

            if not updates:
                return ServiceResult.error("No progress fields to update")

            # 查找任务，支持 uuid 或 task_id
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_task_id(uuid)
            if not task:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 使用真实的 uuid 更新
            real_uuid = task.uuid
            updated_count = self._crud_repo.modify(
                filters={"uuid": real_uuid},
                updates=updates
            )

            if updated_count is None or updated_count == 0:
                return ServiceResult.error(f"Backtest task not found: {real_uuid}")

            return ServiceResult.success({
                "uuid": real_uuid,
                "task_id": task.task_id,
                "progress": updates.get("progress"),
                "current_stage": updates.get("current_stage"),
                "current_date": updates.get("current_date")
            }, f"Task progress updated")

        except Exception as e:
            GLOG.ERROR(f"Failed to update task progress: {e}")
            return ServiceResult.error(f"Failed to update task progress: {str(e)}")

    def health_check(self) -> ServiceResult:
        """
        服务健康检查

        Returns:
            ServiceResult: 健康状态
        """
        try:
            total = self._crud_repo.count()

            return ServiceResult.success({
                "status": "healthy",
                "total_tasks": total
            }, "BacktestTaskService is healthy")

        except Exception as e:
            return ServiceResult.error(f"Health check failed: {str(e)}")

    # ===== 任务控制方法 =====

    def start_task(self, uuid: str, portfolio_uuid: str = None, name: str = None,
                   start_date: str = "", end_date: str = "",
                   initial_cash: float = 100000.0,
                   analyzers: list = None) -> ServiceResult:
        """
        启动回测任务（发送到Kafka队列）

        状态机规则：只能启动 completed/stopped/failed 状态的任务

        重新运行时：
        1. 删除该 task_id 的所有旧数据：
           - signals (信号)
           - orders (订单)
           - positions (持仓)
           - position_records (持仓记录)
           - analyzer_records (分析器记录)
           - order_records (订单状态变更历史)
           - transfer_records (转账记录 - ClickHouse)
           - transfers (转账 - MySQL)
           - signal_trackers (信号追踪器)
        2. task_id 保持不变
        3. 发送启动命令到 Kafka

        Args:
            uuid: 任务标识（可以是 uuid 或 task_id）
            portfolio_uuid: 投资组合UUID
            name: 任务名称
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            analyzers: 分析器列表

        Returns:
            ServiceResult: 启动结果
        """
        try:
            # 获取任务信息（支持 uuid 或 task_id）
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_task_id(uuid)
            if not task:
                return ServiceResult.error("Backtest task not found")

            # 状态机检查：新任务(created/pending)可直接启动，旧任务(completed/stopped/failed)可重新运行
            startable_states = ["created", "pending", "completed", "stopped", "failed"]
            if task.status not in startable_states:
                return ServiceResult.error(
                    f"Cannot start task with status '{task.status}'. "
                    f"Task must be in one of: {', '.join(startable_states)}"
                )

            # 解析派发输入（snapshot_config / dates）：必须在守卫与清理块之前完成，
            # 下方 portfolio/dates 守卫据此判定有效性——空字段同样要在删数据前即拒。
            try:
                snapshot_config = json.loads(task.config_snapshot) if task.config_snapshot else {}
            except (json.JSONDecodeError, TypeError):
                snapshot_config = {}

            # 优先级：显式参数 > 数据库列 backtest_start/end_date > config_snapshot > ""
            if not start_date and task.backtest_start_date:
                start_date = task.backtest_start_date.strftime("%Y-%m-%d")
            elif not start_date:
                start_date = snapshot_config.get("start_date", "")

            if not end_date and task.backtest_end_date:
                end_date = task.backtest_end_date.strftime("%Y-%m-%d")
            elif not end_date:
                end_date = snapshot_config.get("end_date", "")

            # 校验 portfolio 关联：派发前确认 portfolio_uuid 可解析，否则 worker
            # 消费空值时会报误导性的 'portfolio_uuid is required'（#5646）
            # 时序不变式：必须在清理块（删 9 表，CH 不可逆）之前——孤儿任务在删数据前即拒，
            # 否则历史 order/position/signal/analyzer 被永久删除后才在 DTO 处拒绝（#6461 回归）
            if not (portfolio_uuid or task.portfolio_id):
                return ServiceResult.error(
                    f"Backtest task '{task.uuid[:8]}' has no portfolio associated. "
                    f"Recreate the backtest with a valid --portfolio binding so the "
                    f"worker receives a non-empty portfolio_uuid."
                )

            # 校验日期范围：空 dates 同样需在清理块之前拒——否则重跑先删光 9 表历史
            # 数据（CH 5 表异步 mutation 不可逆）后才在 DTO 构造期拒绝，数据永久丢失。
            # （#6461 round-4 finding 的 dates 维度：与 portfolio 守卫同一时序不变式）
            if not start_date or not end_date:
                return ServiceResult.error(
                    f"Backtest task '{task.uuid[:8]}' has no valid date range "
                    f"(start_date={start_date!r}, end_date={end_date!r}). "
                    f"Recreate the backtest with valid --start/--end bindings so the "
                    f"worker receives a non-empty date range."
                )

            # ========== 重新运行：删除旧数据 ==========
            task_id = task.task_id

            GLOG.INFO(f"Cleaning old data for task_id: {task_id[:8]}...")

            # 库归属分组（_is_clickhouse 运行时属性为裁判，非 CRUD 注释）：
            #   MySQL 4 个：共享单事务，任一失败全 rollback，cleanup 失败则不启动回测
            #   ClickHouse 5 个：CH 无事务（ALTER DELETE 异步 mutation），best-effort 删除+告警，不阻断
            # 设计变更见 #5562：原逐表 try-except 半清理仍启动 → 新回测用残留数据致结果污染。
            # driver 经 get_db_connection 单例返回，4 个 MySQL CRUD 共享同一 session_factory。
            _mysql_cleanups = [
                ("order",           self._order_crud),
                ("position",        self._position_crud),
                ("transfer",        self._transfer_crud),
                ("signal_tracker",  self._signal_tracker_crud),
            ]
            _click_cleanups = [
                ("signal",          self._signal_crud),
                ("position_record", self._position_record_crud),
                ("analyzer_record", self._analyzer_record_crud),
                ("order_record",    self._order_record_crud),
                ("transfer_record", self._transfer_record_crud),
            ]

            # ClickHouse 无事务：尽力删除，失败告警不阻断（CH 固有限制，无回滚能力）
            for name, crud in _click_cleanups:
                try:
                    crud.remove(filters={"task_id": task_id})
                    GLOG.DEBUG(f"Deleted old {name} (clickhouse)")
                except Exception as e:
                    GLOG.WARN(f"Failed to delete {name} (clickhouse, no rollback): {e}")

            # MySQL 4 个：None 告警跳过，其余共享单事务（任一失败全 rollback）
            # （清理路径缺注必须大声告警，否则旧数据残留致回测静默污染）
            _mysql_present = []
            for name, crud in _mysql_cleanups:
                if crud is None:
                    GLOG.WARN(f"Failed to delete {name}: CRUD not injected")
                else:
                    _mysql_present.append((name, crud))

            if _mysql_present:
                try:
                    # 4 个 MySQL CRUD 共享同一 driver 单例 → 同一 session_factory → 单事务
                    _mysql_driver = _mysql_present[0][1]._get_connection()
                    with _mysql_driver.get_session() as _cleanup_session:
                        for name, crud in _mysql_present:
                            crud.remove(filters={"task_id": task_id}, session=_cleanup_session)
                            GLOG.DEBUG(f"Deleted old {name} (mysql, in transaction)")
                except Exception as e:
                    GLOG.ERROR(f"MySQL cleanup transaction failed (rolled back): {e}")
                    return ServiceResult.error(f"Cleanup failed and rolled back: {str(e)}")

            # 发送启动命令到Kafka（task_id 保持不变）
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            real_uuid = task.uuid  # 用于更新状态

            # snapshot_config / start_date / end_date 已在守卫前解析完成（见上方），
            # 此处直接用于组装 Kafka config 与状态更新。

            # 先更新状态为 pending，确保 Worker 查询时能看到正确的状态
            status_result = self.update_status(real_uuid, status="pending")
            if not status_result.is_success():
                return ServiceResult.error(f"Failed to update task status to pending: {status_result.error}")

            GLOG.DEBUG(f"Updated task {real_uuid} status to pending")

            # 构建 Kafka config：从 config_snapshot 恢复，显式参数覆盖
            kafka_config = {}
            # 从 snapshot 恢复所有字段作为基础
            # ADR-018：死字段 broker_type/broker_attitude/commission_min 不进 wire spec（消费端 BacktestConfig 不读）
            for key in ("initial_cash", "commission_rate", "slippage_rate", "frequency",
                        "benchmark_return", "max_position_ratio",
                        "stop_loss_ratio", "take_profit_ratio"):
                if key in snapshot_config:
                    kafka_config[key] = snapshot_config[key]

            # 显式参数覆盖（start_date/end_date 已在上面处理）
            kafka_config.update({
                "start_date": start_date,
                "end_date": end_date,
                "analyzers": analyzers or [],
            })
            # initial_cash: snapshot 中的值优先，仅当调用方显式指定非默认值时覆盖
            if initial_cash != 100000.0 or "initial_cash" not in kafka_config:
                kafka_config["initial_cash"] = initial_cash

            # DTO 构造期校验作为二次门：缺 portfolio_uuid / 空 dates 等已由上方
            # 早返回守卫在不可逆清理块之前拦截（时序不变式，#6461 round-4 finding）；
            # 此处 DTO Field(min_length=1) 再兜底校验 wire spec，构造失败则不派发 Kafka（#5646）。
            # 两层并存是有意为之：守卫保时序（先于删数据），DTO 保契约（派发本体）。
            from pydantic import ValidationError
            from ginkgo.interfaces.dtos.backtest_assignment_dto import (
                BacktestAssignmentConfig, StartAssignment,
            )
            producer = GinkgoProducer()
            try:
                assignment = StartAssignment(
                    task_uuid=task_id,  # task_id 保持不变
                    portfolio_uuid=portfolio_uuid or task.portfolio_id,
                    name=name or task.name or f"backtest_{task_id[:8]}",
                    config=BacktestAssignmentConfig(**kafka_config),
                ).to_payload()
            except ValidationError as e:
                return ServiceResult.error(f"Invalid backtest assignment config: {e}")

            # #4853：检查 send 返回值，失败即标 failed，避免永久 running 孤儿。
            # GinkgoProducer.send 已装饰 @retry(max_try=3)，此处 False 表示重试耗尽仍未送达。
            send_ok = producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment)
            producer.flush(timeout=2.0)
            producer.close()

            if not send_ok:
                self.update_status(
                    real_uuid, status="failed",
                    error_message="Kafka dispatch failed: message not delivered after retries",
                )
                GLOG.ERROR(f"Failed to dispatch backtest task {task_id}: Kafka send returned False")
                return ServiceResult.error(
                    f"Failed to dispatch backtest task to Kafka (task {task_id}): "
                    "message not delivered. Task marked as failed."
                )

            GLOG.INFO(f"Started backtest task with task_id: {task_id}")
            return ServiceResult.success({"uuid": real_uuid, "task_id": task_id}, "Backtest task started")

        except Exception as e:
            GLOG.ERROR(f"Failed to start backtest task {uuid}: {e}")
            return ServiceResult.error(f"Failed to start backtest task: {str(e)}")

    def stop_task(self, uuid: str) -> ServiceResult:
        """
        停止回测任务（发送停止命令到Kafka）

        状态机规则：只能停止 running 状态的任务

        Args:
            uuid: 任务标识（可以是 uuid 或 task_id）

        Returns:
            ServiceResult: 停止结果
        """
        try:
            # 获取任务信息（支持 uuid 或 task_id）
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_task_id(uuid)
            if not task:
                return ServiceResult.error("Backtest task not found")

            # 状态机检查：只能停止运行中的任务
            if task.status != "running":
                return ServiceResult.error(
                    f"Cannot stop task with status '{task.status}'. "
                    f"Only running tasks can be stopped."
                )

            # 发送停止命令到Kafka（使用 task_id 作为任务标识）
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            real_uuid = task.uuid  # 用于更新状态
            task_id = task.task_id   # 任务标识
            # ADR-018：StopAssignment.to_payload() —— 判别联合，command 是类型标记非手写字段
            from ginkgo.interfaces.dtos.backtest_assignment_dto import StopAssignment
            producer = GinkgoProducer()
            assignment = StopAssignment(task_uuid=task_id).to_payload()  # 使用 task_id

            producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment)
            producer.flush(timeout=2.0)
            producer.close()

            # 更新任务状态为stopped
            self.update_status(real_uuid, status="stopped")

            GLOG.INFO(f"Stopped backtest task: {task_id[:8]}...")
            return ServiceResult.success({"uuid": real_uuid, "task_id": task_id}, "Backtest task stopped")

        except Exception as e:
            GLOG.ERROR(f"Failed to stop backtest task: {e}")
            return ServiceResult.error(f"Failed to stop backtest task: {str(e)}")

    def cancel_task(self, uuid: str) -> ServiceResult:
        """
        取消回测任务（发送取消命令到Kafka）

        状态机规则：只能取消 created/pending 状态的任务（尚未开始执行的任务）

        Args:
            uuid: 任务标识（可以是 uuid 或 task_id）

        Returns:
            ServiceResult: 取消结果
        """
        try:
            # 获取任务信息（支持 uuid 或 task_id）
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_task_id(uuid)
            if not task:
                return ServiceResult.error("Backtest task not found")

            # 状态机检查：只能取消待调度或排队中的任务
            cancelable_states = ["created", "pending"]
            if task.status not in cancelable_states:
                return ServiceResult.error(
                    f"Cannot cancel task with status '{task.status}'. "
                    f"Only tasks in {', '.join(cancelable_states)} can be cancelled."
                )

            # 发送取消命令到Kafka（使用 task_id 作为任务标识）
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            real_uuid = task.uuid  # 用于更新状态
            task_id = task.task_id   # 任务标识
            # ADR-018：CancelAssignment.to_payload() —— 判别联合
            from ginkgo.interfaces.dtos.backtest_assignment_dto import CancelAssignment
            producer = GinkgoProducer()
            assignment = CancelAssignment(task_uuid=task_id).to_payload()  # 使用 task_id

            producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment)
            producer.flush(timeout=2.0)
            producer.close()

            # 更新任务状态为stopped
            self.update_status(real_uuid, status="stopped")

            GLOG.INFO(f"Cancelled backtest task: {task_id[:8]}...")
            return ServiceResult.success({"uuid": real_uuid, "task_id": task_id}, "Backtest task cancelled")

        except Exception as e:
            GLOG.ERROR(f"Failed to cancel backtest task: {e}")
            return ServiceResult.error(f"Failed to cancel backtest task: {str(e)}")

    # #3867: API 层不再直调 CRUD，通过 Service 封装

    def get_latest_completed(self, portfolio_id: str) -> ServiceResult:
        """获取 portfolio 最新已完成回测的绩效指标"""
        try:
            tasks = self._crud_repo.find(
                filters={"portfolio_id": portfolio_id, "status": "completed", "is_del": False},
                order_by="create_at",
                desc_order=True,
                page_size=1,
            )
            if not tasks:
                return ServiceResult.success(data={})
            t = tasks[0]
            return ServiceResult.success(data={
                "annual_return": float(getattr(t, "annual_return", 0) or 0),
                "sharpe_ratio": float(getattr(t, "sharpe_ratio", 0) or 0),
                "max_drawdown": float(getattr(t, "max_drawdown", 0) or 0),
                "win_rate": float(getattr(t, "win_rate", 0) or 0),
                "last_backtest_date": t.create_at.isoformat() if hasattr(t, "create_at") and t.create_at else None,
            })
        except Exception as e:
            return ServiceResult.error(f"Failed to get latest backtest metrics: {str(e)}")

    def count_by_portfolio(self, portfolio_id: str) -> ServiceResult:
        """统计 portfolio 的回测次数"""
        try:
            count = self._crud_repo.count(
                filters={"portfolio_id": portfolio_id, "is_del": False}
            )
            return ServiceResult.success(data=count or 0)
        except Exception as e:
            return ServiceResult.error(f"Failed to count backtests: {str(e)}")

    # ==================== Schema 方法（返回 Pydantic 对象） ====================

    def _format_dt(self, dt) -> Optional[str]:
        """datetime → ISO 字符串"""
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

    def _task_to_summary(self, task, portfolio_names: dict = None) -> "BacktestTaskSummary":
        """ORM task → BacktestTaskSummary"""
        from ginkgo.data.services.backtest_task_schemas import BacktestTaskSummary
        pid = getattr(task, "portfolio_id", "") or ""
        return BacktestTaskSummary(
            uuid=getattr(task, "uuid", ""),
            name=getattr(task, "name", ""),
            portfolio_id=pid,
            portfolio_name=(portfolio_names or {}).get(pid, ""),
            status=getattr(task, "status", "created") or "created",
            progress=getattr(task, "progress", 0) or 0,
            total_pnl=float(getattr(task, "total_pnl", 0) or 0),
            total_orders=int(getattr(task, "total_orders", 0) or 0),
            total_signals=int(getattr(task, "total_signals", 0) or 0),
            total_positions=int(getattr(task, "total_positions", 0) or 0),
            max_drawdown=float(getattr(task, "max_drawdown", 0) or 0),
            sharpe_ratio=float(getattr(task, "sharpe_ratio", 0) or 0),
            annual_return=float(getattr(task, "annual_return", 0) or 0),
            win_rate=float(getattr(task, "win_rate", 0) or 0),
            final_portfolio_value=float(getattr(task, "final_portfolio_value", 0) or 0),
            created_at=self._format_dt(getattr(task, "create_at", None)) or "",
            started_at=self._format_dt(getattr(task, "start_time", None)),
            completed_at=self._format_dt(getattr(task, "end_time", None)),
            backtest_start_date=self._format_dt(getattr(task, "backtest_start_date", None)),
            backtest_end_date=self._format_dt(getattr(task, "backtest_end_date", None)),
            error_message=getattr(task, "error_message", "") or "",
        )

    def list_summaries(
        self,
        page: int = 0,
        page_size: int = 20,
        portfolio_id: str = None,
        status: str = None,
        sort_by: str = None,
        sort_order: str = "desc",
    ) -> "ServiceResult":
        """
        分页获取回测摘要列表，返回 BacktestTaskSummary 列表。

        内部完成：CRUD 查询 → portfolio 名称解析 → ORM→Schema 转换 → 排序。
        """
        from ginkgo.data.services.backtest_task_schemas import BacktestTaskSummary

        try:
            result = self.list(
                page=page, page_size=page_size,
                portfolio_id=portfolio_id, status=status,
            )
            if not result.is_success():
                return result

            result_data = result.data or {}
            tasks = result_data.get("data", [])
            total = result_data.get("total", 0)

            # 批量获取 portfolio 名称
            portfolio_ids = set()
            for t in tasks:
                pid = t.get("portfolio_id") if isinstance(t, dict) else getattr(t, "portfolio_id", "")
                if pid:
                    portfolio_ids.add(pid)

            portfolio_names = {}
            if portfolio_ids and self._portfolio_service:
                try:
                    portfolio_names = self._portfolio_service.get_names_by_ids(list(portfolio_ids))
                except Exception as e:
                    GLOG.WARN(f"failed to fetch portfolio names for task list summary: {e}")

            summaries: list[BacktestTaskSummary] = []
            for t in tasks:
                summaries.append(self._task_to_summary(t, portfolio_names))

            # 当前页内排序
            sortable = {"annual_return", "sharpe_ratio", "max_drawdown", "win_rate", "created_at", "total_pnl"}
            if sort_by in sortable:
                reverse = sort_order != "asc"
                summaries.sort(key=lambda s: getattr(s, sort_by, 0) or 0, reverse=reverse)

            sr = ServiceResult.success(data=summaries, message="Backtest summaries retrieved")
            sr.set_metadata("total", total)
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_summaries failed: {e}")
            return ServiceResult.error(f"Failed to list summaries: {e}")

    def get_detail(self, uuid: str) -> "ServiceResult":
        """
        获取回测任务详情，返回 BacktestTaskDetail。
        """
        from ginkgo.data.services.backtest_task_schemas import BacktestTaskDetail

        try:
            result = self.get_by_id(uuid)
            if not result.is_success() or not result.data:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            task = result.data
            if isinstance(task, list):
                task = task[0] if task else None
            if task is None:
                return ServiceResult.error(f"Backtest task not found: {uuid}")

            # 解析 config JSON
            config_str = getattr(task, "config_snapshot", "{}") or "{}"
            config = json.loads(config_str) if isinstance(config_str, str) else (config_str or {})

            detail = BacktestTaskDetail(
                uuid=getattr(task, "uuid", uuid),
                name=getattr(task, "name", ""),
                portfolio_id=getattr(task, "portfolio_id", ""),
                status=getattr(task, "status", "created") or "created",
                progress=getattr(task, "progress", 0) or 0,
                total_pnl=float(getattr(task, "total_pnl", 0) or 0),
                total_orders=int(getattr(task, "total_orders", 0) or 0),
                total_signals=int(getattr(task, "total_signals", 0) or 0),
                total_positions=int(getattr(task, "total_positions", 0) or 0),
                total_events=int(getattr(task, "total_events", 0) or 0),
                max_drawdown=float(getattr(task, "max_drawdown", 0) or 0),
                sharpe_ratio=float(getattr(task, "sharpe_ratio", 0) or 0),
                annual_return=float(getattr(task, "annual_return", 0) or 0),
                win_rate=float(getattr(task, "win_rate", 0) or 0),
                final_portfolio_value=float(getattr(task, "final_portfolio_value", 0) or 0),
                backtest_start_date=self._format_dt(getattr(task, "backtest_start_date", None)),
                backtest_end_date=self._format_dt(getattr(task, "backtest_end_date", None)),
                engine_uuid=config.get("engine_uuid"),
                created_at=self._format_dt(getattr(task, "create_at", None)) or "",
                started_at=self._format_dt(getattr(task, "start_time", None)),
                completed_at=self._format_dt(getattr(task, "end_time", None)),
                config=config,
                error_message=getattr(task, "error_message", "") or "",
            )

            return ServiceResult.success(data=detail, message="Backtest detail retrieved")
        except Exception as e:
            GLOG.ERROR(f"get_detail failed: {e}")
            return ServiceResult.error(f"Failed to get detail: {e}")

    def _resolve_task_id(self, uuid: str) -> "tuple[Optional[str], Optional[str], ServiceResult | None]":
        """解析 uuid → (task_id, portfolio_id, error_result)"""
        result = self.get_by_id(uuid)
        if not result.is_success() or not result.data:
            return None, None, ServiceResult.error(f"Backtest task not found: {uuid}")
        task = result.data
        if isinstance(task, list):
            task = task[0] if task else None
        if task is None:
            return None, None, ServiceResult.error(f"Backtest task not found: {uuid}")
        task_id = getattr(task, "task_id", uuid)
        portfolio_id = getattr(task, "portfolio_id", "")
        return task_id, portfolio_id, None

    def list_signals(self, uuid: str, page: int = 1, page_size: int = 100) -> "ServiceResult":
        """获取回测信号列表，返回 list[BacktestSignalItem]"""
        from ginkgo.data.services.backtest_task_schemas import BacktestSignalItem

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_signals(task_id=task_id, page=page, page_size=page_size)
            if not result.is_success():
                return ServiceResult.success(data=[], message=result.error)

            signals = result.data.get("data", [])
            total = result.data.get("total", 0)

            items = []
            for s in signals:
                items.append(BacktestSignalItem(
                    uuid=getattr(s, "uuid", ""),
                    portfolio_id=getattr(s, "portfolio_id", ""),
                    engine_id=getattr(s, "engine_id", ""),
                    task_id=getattr(s, "task_id", ""),
                    code=getattr(s, "code", ""),
                    direction=str(getattr(s, "direction", "")) if getattr(s, "direction", None) is not None else None,
                    reason=getattr(s, "reason", ""),
                    timestamp=self._format_dt(getattr(s, "timestamp", None)),
                    source=str(getattr(s, "source", "")) if getattr(s, "source", None) is not None else None,
                ))

            sr = ServiceResult.success(data=items, message="Signals retrieved")
            sr.set_metadata("total", total)
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_signals failed: {e}")
            return ServiceResult.error(f"Failed to list signals: {e}")

    def list_orders(self, uuid: str, page: int = 1, page_size: int = 0) -> "ServiceResult":
        """获取回测订单列表，返回 list[BacktestOrderItem]

        page_size 默认 0=全量(向后兼容 CLI/分析引擎等内部全量调用方);
        端点层(Query 默认 50)显式传入时分页。
        """
        from ginkgo.data.services.backtest_task_schemas import BacktestOrderItem

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_orders(task_id=task_id, page=page, page_size=page_size)
            if not result.is_success():
                return ServiceResult.success(data=[], message=result.error)

            orders = result.data.get("data", [])
            total = result.data.get("total", 0)

            items = []
            for o in orders:
                items.append(BacktestOrderItem(
                    uuid=getattr(o, "uuid", ""),
                    portfolio_id=getattr(o, "portfolio_id", ""),
                    engine_id=getattr(o, "engine_id", ""),
                    task_id=getattr(o, "task_id", ""),
                    code=getattr(o, "code", ""),
                    direction=str(getattr(o, "direction", "")) if getattr(o, "direction", None) is not None else None,
                    order_type=str(getattr(o, "order_type", "")) if getattr(o, "order_type", None) is not None else None,
                    status=str(getattr(o, "status", "")) if getattr(o, "status", None) is not None else None,
                    volume=int(getattr(o, "volume", 0) or 0),
                    limit_price=convert_to_float(getattr(o, "limit_price", 0)) or None,
                    transaction_price=convert_to_float(getattr(o, "transaction_price", 0)),
                    transaction_volume=int(getattr(o, "transaction_volume", 0) or 0),
                    fee=convert_to_float(getattr(o, "fee", 0)),
                    timestamp=self._format_dt(getattr(o, "timestamp", None)),
                ))

            sr = ServiceResult.success(data=items, message="Orders retrieved")
            sr.set_metadata("total", total)
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_orders failed: {e}")
            return ServiceResult.error(f"Failed to list orders: {e}")

    def list_fills(self, uuid: str) -> "ServiceResult":
        """获取回测已成交订单（fills），返回 list[BacktestOrderItem]。

        fills = status==FILLED 的订单子集（订单被成交的填充语义）。
        与 list_orders 同源（result_service.get_orders 去重订单），仅过滤成交态；
        在 raw record 层过滤（status 字段未 str 化），兼容 int 值与 enum 实例。
        """
        from ginkgo.data.services.backtest_task_schemas import BacktestOrderItem
        from ginkgo.enums import ORDERSTATUS_TYPES

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_orders(task_id=task_id)
            if not result.is_success():
                return ServiceResult.success(data=[], message=result.error)

            orders = result.data.get("data", [])
            filled_value = ORDERSTATUS_TYPES.FILLED.value
            filled = [o for o in orders
                      if getattr(o, "status", None) == ORDERSTATUS_TYPES.FILLED
                      or getattr(o, "status", None) == filled_value]

            items = []
            for o in filled:
                items.append(BacktestOrderItem(
                    uuid=getattr(o, "uuid", ""),
                    portfolio_id=getattr(o, "portfolio_id", ""),
                    engine_id=getattr(o, "engine_id", ""),
                    task_id=getattr(o, "task_id", ""),
                    code=getattr(o, "code", ""),
                    direction=str(getattr(o, "direction", "")) if getattr(o, "direction", None) is not None else None,
                    order_type=str(getattr(o, "order_type", "")) if getattr(o, "order_type", None) is not None else None,
                    status=str(getattr(o, "status", "")) if getattr(o, "status", None) is not None else None,
                    volume=int(getattr(o, "volume", 0) or 0),
                    limit_price=str(getattr(o, "limit_price", 0)),
                    transaction_price=str(getattr(o, "transaction_price", 0)),
                    transaction_volume=int(getattr(o, "transaction_volume", 0) or 0),
                    fee=str(getattr(o, "fee", 0)),
                    timestamp=self._format_dt(getattr(o, "timestamp", None)),
                ))

            sr = ServiceResult.success(data=items, message="Fills retrieved")
            sr.set_metadata("total", len(items))
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_fills failed: {e}")
            return ServiceResult.error(f"Failed to list fills: {e}")

    def get_results(self, uuid: str) -> "ServiceResult":
        """获取回测运行结果摘要（portfolios/analyzers/time_range/total_records）。

        透传 result_service.get_run_summary(task_id)；uuid 经 _resolve_task_id 解析。
        """
        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            return result_service.get_run_summary(task_id)
        except Exception as e:
            GLOG.ERROR(f"get_results failed: {e}")
            return ServiceResult.error(f"Failed to get results: {e}")

    def list_order_records(self, uuid: str) -> "ServiceResult":
        """获取回测订单记录流水(完整状态流转, 不去重), 返回 list[BacktestOrderItem]。

        与 list_orders 区分: list_orders 返回去重后的订单(每个 order_id 最终态一条),
        本方法返回同一 order_id 的全部状态变更记录(NEW/SUBMITTED/FILLED/CANCELED 等)。
        """
        from ginkgo.data.services.backtest_task_schemas import BacktestOrderItem

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_order_records(task_id=task_id)
            if not result.is_success():
                return ServiceResult.success(data=[], message=result.error)

            records = result.data.get("data", [])
            total = result.data.get("total", 0)

            items = []
            for o in records:
                items.append(BacktestOrderItem(
                    uuid=getattr(o, "uuid", ""),
                    portfolio_id=getattr(o, "portfolio_id", ""),
                    engine_id=getattr(o, "engine_id", ""),
                    task_id=getattr(o, "task_id", ""),
                    code=getattr(o, "code", ""),
                    direction=str(getattr(o, "direction", "")) if getattr(o, "direction", None) is not None else None,
                    order_type=str(getattr(o, "order_type", "")) if getattr(o, "order_type", None) is not None else None,
                    status=str(getattr(o, "status", "")) if getattr(o, "status", None) is not None else None,
                    volume=int(getattr(o, "volume", 0) or 0),
                    limit_price=convert_to_float(getattr(o, "limit_price", 0)) or None,
                    transaction_price=convert_to_float(getattr(o, "transaction_price", 0)),
                    transaction_volume=int(getattr(o, "transaction_volume", 0) or 0),
                    fee=convert_to_float(getattr(o, "fee", 0)),
                    timestamp=self._format_dt(getattr(o, "timestamp", None)),
                ))

            sr = ServiceResult.success(data=items, message="Order records retrieved")
            sr.set_metadata("total", total)
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_order_records failed: {e}")
            return ServiceResult.error(f"Failed to list order records: {e}")

    def list_positions(self, uuid: str) -> "ServiceResult":
        """获取回测持仓列表，返回 list[BacktestPositionItem]"""
        from ginkgo.data.services.backtest_task_schemas import BacktestPositionItem

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_positions(task_id=task_id)
            if not result.is_success():
                return ServiceResult.success(data=[], message=result.error)

            positions = result.data.get("data", [])
            total = result.data.get("total", 0)

            items = []
            for p in positions:
                items.append(BacktestPositionItem(
                    uuid=getattr(p, "uuid", ""),
                    portfolio_id=getattr(p, "portfolio_id", ""),
                    engine_id=getattr(p, "engine_id", ""),
                    task_id=getattr(p, "task_id", ""),
                    code=getattr(p, "code", ""),
                    cost=convert_to_float(getattr(p, "cost", 0)),
                    volume=int(getattr(p, "volume", 0) or 0),
                    frozen_volume=int(getattr(p, "frozen_volume", 0) or 0),
                    price=convert_to_float(getattr(p, "price", 0)),
                    fee=convert_to_float(getattr(p, "fee", 0)),
                ))

            sr = ServiceResult.success(data=items, message="Positions retrieved")
            sr.set_metadata("total", total)
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_positions failed: {e}")
            return ServiceResult.error(f"Failed to list positions: {e}")

    def list_analyzer_groups(self, uuid: str) -> "ServiceResult":
        """
        获取分析器聚合列表，返回 list[BacktestAnalyzerGroup]。
        包含分组聚合逻辑（latest, count, change）。
        """
        from collections import OrderedDict
        from ginkgo.data.services.backtest_task_schemas import BacktestAnalyzerGroup

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            analyzer_service = container.analyzer_service()
            # #5403: task_id 是主查询键(ADR-012); portfolio_id 仅在非空时作为可选过滤。
            # 原走 find_by_portfolio 无条件按 portfolio_id 过滤, 当 portfolio_id 为空时
            # filter {"portfolio_id": ""} 匹配不到记录, 导致 analyzers 端点返回空数组。
            # review #6205: find_by_portfolio 原无上限, 而 get_by_task_id 默认 limit=1000,
            # 长周期回测(>1000 条)会被截断, 使分组 change(首尾差)/count 失真。
            # 显式传大 limit(对齐 result_service 的 page_size=10000)消除回归。
            result = analyzer_service.get_by_task_id(
                task_id=task_id, portfolio_id=portfolio_id or None, limit=10000)
            if not getattr(result, "success", False):
                return ServiceResult.error(getattr(result, "error", "查询分析器失败"))
            records = result.data

            grouped = OrderedDict()
            for r in records:
                name = getattr(r, "name", None)
                if name is None:
                    continue
                if name not in grouped:
                    grouped[name] = []
                val = float(r.value) if r.value is not None else None
                if val is not None:
                    grouped[name].append(val)

            groups = []
            for name, values in grouped.items():
                latest = values[0] if values else None
                count = len(values)
                change = (values[0] - values[-1]) if len(values) > 1 else 0
                groups.append(BacktestAnalyzerGroup(
                    name=name,
                    latest_value=latest,
                    record_count=count,
                    stats={"count": count, "latest": latest, "change": change},
                ))

            return ServiceResult.success(data=groups, message="Analyzer groups retrieved")
        except Exception as e:
            GLOG.ERROR(f"list_analyzer_groups failed: {e}")
            return ServiceResult.error(f"Failed to list analyzer groups: {e}")

    def get_netvalue(self, uuid: str) -> "ServiceResult":
        """获取净值数据，返回 BacktestNetValueData"""
        from ginkgo.data.services.backtest_task_schemas import (
            BacktestAnalyzerDataPoint, BacktestNetValueData,
        )

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_analyzer_values(
                task_id=task_id, portfolio_id=portfolio_id, analyzer_name="net_value",
            )
            if not result.is_success() or not result.data:
                return ServiceResult.success(
                    data=BacktestNetValueData(),
                    message="No net value data",
                )

            # #5848: get_by_task_id 硬编码 desc_order=True（aggregator 依赖它取最新累计值），
            # 净值曲线需要正序（最早在前），组装前反转，不动共享 CRUD。
            records = list(reversed(result.data))
            strategy = []
            for r in records:
                ts = r.business_timestamp.isoformat() if r.business_timestamp else (
                    r.timestamp.isoformat() if r.timestamp else ""
                )
                strategy.append(BacktestAnalyzerDataPoint(
                    time=ts,
                    value=float(r.value) if r.value is not None else None,
                ))

            return ServiceResult.success(
                data=BacktestNetValueData(strategy=strategy),
                message="Net value retrieved",
            )
        except Exception as e:
            GLOG.ERROR(f"get_netvalue failed: {e}")
            return ServiceResult.error(f"Failed to get netvalue: {e}")

    def get_analyzer_data(self, uuid: str, analyzer_name: str) -> "ServiceResult":
        """获取单个分析器的完整时序数据，返回 BacktestAnalyzerDetail"""
        from ginkgo.data.services.backtest_task_schemas import (
            BacktestAnalyzerDataPoint, BacktestAnalyzerDetail,
        )

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_analyzer_values(
                task_id=task_id, portfolio_id=portfolio_id, analyzer_name=analyzer_name,
            )
            if not result.is_success() or not result.data:
                return ServiceResult.success(
                    data=BacktestAnalyzerDetail(),
                    message="No analyzer data found",
                )

            records = result.data
            data_points = []
            values = []
            for r in records:
                ts = r.business_timestamp.isoformat() if r.business_timestamp else r.timestamp.isoformat()
                val = float(r.value) if r.value is not None else None
                data_points.append(BacktestAnalyzerDataPoint(time=ts, value=val))
                if val is not None:
                    values.append(val)

            stats = None
            if values:
                stats = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "first": values[0],
                    "latest": values[-1],
                    "change": (values[-1] - values[0]) if len(values) > 1 else 0,
                }

            return ServiceResult.success(
                data=BacktestAnalyzerDetail(data=data_points, stats=stats),
                message="Analyzer data retrieved",
            )
        except Exception as e:
            GLOG.ERROR(f"get_analyzer_data failed: {e}")
            return ServiceResult.error(f"Failed to get analyzer data: {e}")


# 向后兼容别名
RunRecordService = BacktestTaskService

