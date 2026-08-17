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

from ginkgo.libs import cache_with_expiration, retry, GLOG, datetime_normalize
from ginkgo.libs.data.number import convert_to_float
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.interfaces.kafka_topics import KafkaTopics


class BacktestTaskService(BaseService):
    # 孤儿判定宽限期(秒):容忍心跳快照对"刚启动任务"的滞后(见 cleanup_orphan_tasks)
    ORPHAN_GRACE_SECONDS = 60

    # 状态正向迁移白名单(状态机守卫,见 update_status):键=目标状态,值=合法来源集。
    # 语义:created 仅由创建产生(无来源);pending=start/重跑;running=worker 认领;
    # 终态仅可来自活跃态;终态不可互转(重跑走 pending 复活,非直接覆盖)。
    STATUS_TRANSITIONS = {
        "created": set(),                                    # 初始态,只建不迁
        "pending": {"created", "failed", "completed", "stopped"},  # start/重跑
        "running": {"pending", "created"},                   # worker 认领启动
        "completed": {"running", "pending"},                  # 正常完成(容忍竞态快)
        "failed": {"running", "pending", "created"},          # 失败/孤儿清理/派发失败
        "stopped": {"running", "pending"},                    # 用户停止
    }

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
                return ServiceResult.success([])

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
             portfolio_id: str = None, status: str = None,
             sort_by: str = None, sort_order: str = "desc") -> ServiceResult:
        """
        获取回测任务列表

        Args:
            page: 页码
            page_size: 每页数量
            engine_id: 引擎ID筛选
            portfolio_id: 投资组合ID筛选
            status: 状态筛选
            sort_by: DB 级排序字段（白名单 create_at/update_at，其余忽略走默认）
            sort_order: 排序方向 asc/desc

        Returns:
            ServiceResult: 列表结果
        """
        try:
            # order_by 直拼列名，白名单防注入；非法值一律回退默认 create_at
            if sort_by not in ("create_at", "update_at"):
                sort_by = "create_at"
            # None 守卫：0=全量下推 None（与 signal/engine/portfolio service 一致），
            # 裸 page_size=0 触发 BaseCRUD.find LIMIT 0 返空，破坏 ADR-021 "0=all" 契约（#6652 review R4）。
            result = self._crud_repo.get_tasks_page_filtered(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                status=status,
                page=page,
                page_size=page_size if page_size and page_size > 0 else None,
                sort_by=sort_by,
                sort_order=sort_order,
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
            # #6640: 创建预检——校验 portfolio 必需组件（清单单点定义于装配层 requirements）
            # 缺必需组件时拒绝创建并返回具体组件名 + 绑定命令，避免用户跑到 run
            # 阶段才看到笼统的 'No portfolios bound to engine'。校验在 service 层
            # （API/CLI 共享）；portfolio_service 未注入或查询失败时保守放行，
            # 由装配层 component_loader 兜底（错误经 #6640 透传机制回传具体缺失组件）。
            portfolio_service = getattr(self, "_portfolio_service", None)
            if portfolio_id and portfolio_service is not None:
                # 延迟 import 规避 data → trading 的模块加载期循环
                from ginkgo.trading.services._assembly.requirements import (
                    find_missing_required_components,
                    format_missing_components_message,
                )
                comp_result = portfolio_service.get_components(portfolio_id=portfolio_id)
                # 注意用 `is not None` 而非 truthiness：空 portfolio（0 绑定）的合法
                # 返回是空 list []（falsy），但语义=「该 portfolio 无绑定」=缺全部必需组件，
                # 是预检最该拦截的场景。truthiness 会把 [] 当「查询失败」放行，让 fast-feedback
                # 对最常见的配置不全场景失效（用户须跑到 run 阶段才见错误）。None 才是
                # 「无 payload / 查询异常」信号，交装配层兜底。
                if comp_result.is_success() and comp_result.data is not None:
                    bound_types = {
                        c.get("component_type")
                        for c in comp_result.data
                        if c.get("component_type")
                    }
                    missing = find_missing_required_components(bound_types)
                    if missing:
                        return ServiceResult.error(
                            format_missing_components_message(portfolio_id, missing)
                        )

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
                return ServiceResult.error(f"Invalid status: {status}", code="INVALID_STATUS")

            # 查找任务，支持 uuid 或 task_id
            task = self._crud_repo.get_by_uuid(uuid)
            if not task:
                task = self._crud_repo.get_by_task_id(uuid)
            if not task:
                return ServiceResult.error(f"Backtest task not found: {uuid}", code="NOT_FOUND")

            # 正向迁移白名单（状态机守卫,2026-08-16 竞态实证：API 置 pending 与
            # worker 置 running 并发提交、序不可控,running 曾被 pending 反向覆盖
            # ——任务卡"排队中"但进度在走。守卫拒绝一切非法回退；同值写放行
            # （重试幂等）。这是状态机重设计（ADR 待做）的第一块守卫件,
            # 迁移表即未来 ADR 的形式化基础。
            current = getattr(task, "status", None)
            if current != status and current not in self.STATUS_TRANSITIONS.get(status, set()):
                return ServiceResult.error(
                    f"Illegal status transition: {current} -> {status} "
                    f"(allowed origins: {sorted(self.STATUS_TRANSITIONS.get(status, set())) or 'none'})",
                    code="ILLEGAL_TRANSITION",
                )

            # 使用真实的 uuid 更新
            real_uuid = task.uuid
            updated_count = self._crud_repo.update_task_status(
                uuid=real_uuid,
                status=status,
                error_message=error_message,
                **result_fields
            )

            if updated_count == 0:
                return ServiceResult.error(f"Backtest task not found: {real_uuid}", code="NOT_FOUND")

            GLOG.INFO(f"Updated task {real_uuid[:8]}... status to: {status}")

            return ServiceResult.success({"uuid": real_uuid, "task_id": task.task_id, "status": status},
                                         f"Task status updated to {status}")

        except Exception as e:
            GLOG.ERROR(f"Failed to update task status: {e}")
            return ServiceResult.error(f"Failed to update task status: {str(e)}", code="UPDATE_FAILED")

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

    def cleanup_orphan_backtests(self, dry_run: bool = True) -> ServiceResult:
        """
        清理引用断裂的孤儿回测数据（2026-08-16,对齐 cleanup_orphaned_mappings 风格）。

        两类目标:
        1. MySQL 孤儿任务:portfolio_id 引用不存在的 portfolio(组合被删,实例:
           765e5a30 被删后遗留 6 个任务)——连任务带 CH 流水 + MySQL 四表级联清理;
        2. CH 全局孤儿流水:task_id 为空或指向不存在任务——历史删除不级联留下
           的尸体(实测 ~14.4 万 signal + ~1 万空 id)。

        与 cleanup_orphan_tasks(运行态孤儿:running 不被 worker 持有)互补,
        本方法管引用完整性。dry_run=True 仅统计不删(默认,清理不可逆)。

        Returns:
            ServiceResult: data 含 mysql_tasks(CH 级联前任务数)/ch_global(CH 全局
            孤儿流水分表计数)/details;MySQL CRUD 未注入时跳过对应级联并告警。
        """
        try:
            from sqlalchemy import text

            details: List[str] = []

            # ---------- 1. MySQL 孤儿任务(引用断) ----------
            with self._crud_repo.get_session() as session:
                orphan_tasks = session.execute(text(
                    "SELECT task_id FROM backtest_task "
                    "WHERE portfolio_id IS NOT NULL AND portfolio_id != '' "
                    "AND portfolio_id NOT IN (SELECT uuid FROM portfolio WHERE is_del = 0)"
                )).scalars().all()

            mysql_task_count = len(orphan_tasks)
            if mysql_task_count > 0:
                details.append(f"MySQL 孤儿任务(portfolio 引用断): {mysql_task_count} 个")

            if not dry_run and orphan_tasks:
                # 级联清理与重跑清理同构:CH 五表(尽力) + 日志 + MySQL 四表(单事务) + 任务行
                _click_cleanups = [
                    ("signal",          self._signal_crud),
                    ("position_record", self._position_record_crud),
                    ("analyzer_record", self._analyzer_record_crud),
                    ("order_record",    self._order_record_crud),
                    ("transfer_record", self._transfer_record_crud),
                ]
                for task_id in orphan_tasks:
                    for name, crud in _click_cleanups:
                        if crud is None:
                            GLOG.WARN(f"[orphan-cleanup] {name} CRUD not injected, skipped")
                        else:
                            try:
                                crud.remove(filters={"task_id": task_id})
                            except Exception as e:
                                GLOG.WARN(f"[orphan-cleanup] CH {name} delete failed for {task_id[:8]}: {e}")
                    try:
                        from ginkgo.services.logging import LogService
                        LogService().delete_logs_by_task_id(task_id)
                    except Exception as e:
                        GLOG.WARN(f"[orphan-cleanup] logs delete failed for {task_id[:8]}: {e}")
                    for name, crud in [
                        ("order", self._order_crud), ("position", self._position_crud),
                        ("transfer", self._transfer_crud), ("signal_tracker", self._signal_tracker_crud),
                    ]:
                        if crud is not None:
                            try:
                                crud.remove(filters={"task_id": task_id})
                            except Exception as e:
                                GLOG.WARN(f"[orphan-cleanup] mysql {name} failed for {task_id[:8]}: {e}")
                    self._crud_repo.remove(filters={"task_id": task_id})
                    GLOG.INFO(f"[orphan-cleanup] removed orphan backtest task {task_id[:8]} (+cascades)")

            # ---------- 2. CH 全局孤儿流水(task_id 空或指向不存在的任务) ----------
            with self._crud_repo.get_session() as session:
                valid_ids = session.execute(text(
                    "SELECT task_id FROM backtest_task"
                )).scalars().all()
            in_clause = ",".join(f"'{tid}'" for tid in valid_ids) or "''"
            ch_global: Dict[str, int] = {}

            # CH 侧直 SQL(跨库 NOT IN 只能拉清单下推)。任一 CH crud 拿连接。
            ch_crud = next((c for c in [self._signal_crud, self._position_record_crud,
                                        self._analyzer_record_crud, self._order_record_crud] if c is not None), None)
            if ch_crud is None:
                GLOG.WARN("[orphan-cleanup] no CH crud injected, global sweep skipped")
            else:
                ch_tables = ["signal", "order_record", "position_record", "analyzer_record"]
                ch_session_factory = ch_crud._get_connection()
                with ch_session_factory.get_session() as ch_session:
                    for table in ch_tables:
                        where = f"task_id = '' OR task_id NOT IN ({in_clause})"
                        cnt = ch_session.execute(text(
                            f"SELECT count() FROM {table} WHERE {where}"
                        )).scalar() or 0
                        if cnt > 0:
                            ch_global[table] = int(cnt)
                            details.append(f"CH {table} 孤儿流水: {cnt} 行")
                            if not dry_run:
                                ch_session.execute(text(f"ALTER TABLE {table} DELETE WHERE {where}"))
                # 回测日志表(仅 ginkgo_logs_backtest 有 task_id 语义)
                try:
                    from ginkgo.services.logging import LogService
                    log_svc = LogService()
                    log_where = f"task_id = '' OR task_id NOT IN ({in_clause})"
                    with log_svc._engine.get_session() as ls:
                        cnt = ls.execute(text(
                            f"SELECT count() FROM ginkgo_logs_backtest WHERE {log_where}"
                        )).scalar() or 0
                        if cnt > 0:
                            ch_global["ginkgo_logs_backtest"] = int(cnt)
                            details.append(f"CH 回测日志孤儿: {cnt} 行")
                            if not dry_run:
                                ls.execute(text(f"ALTER TABLE ginkgo_logs_backtest DELETE WHERE {log_where}"))
                except Exception as e:
                    GLOG.WARN(f"[orphan-cleanup] log sweep failed: {e}")

            action = "将清理" if dry_run else "清理了"
            if details:
                for d in details:
                    GLOG.INFO(f"[orphan-cleanup] {action}: {d}")

            return ServiceResult.success({
                "dry_run": dry_run,
                "mysql_orphan_tasks": mysql_task_count,
                "ch_global": ch_global,
                "details": details,
            }, f"孤儿回测清理{'预览' if dry_run else '执行'}完成")

        except Exception as e:
            GLOG.ERROR(f"cleanup_orphan_backtests failed: {e}")
            return ServiceResult.error(f"cleanup_orphan_backtests failed: {e}")

    def cleanup_orphan_tasks(self) -> ServiceResult:
        """
        清理孤儿回测任务（#6846）。

        判定：running 任务不被任何活跃 worker 心跳持有 → 孤儿 → 标 failed。
        心跳 TTL 30s，worker crash / 丢 Kafka 消息后心跳过期即不再声明持有该 task，
        遂被判定孤儿，兜底状态机防永久 running。

        宽限期（ORPHAN_GRACE_SECONDS）：心跳是 10s 周期快照，任务登记后最长 10s
        才进持有集；刚置 running（start_time 距今 < 60s）的任务即使缺席快照也跳过，
        防启动窗口竞态误杀（真孤儿最多晚一个宽限期被标，代价可忽略）。

        相比 #4853 旧的 start_time 超时判定，心跳持有集才是"有 worker 在管这事"
        的真实信号：worker 正常在跑 → 心跳声明持有 → 不动；worker 死了 → 心跳过期
        → 持有集不含该 task → 标 failed。start_time 无法区分"真在跑"与"已丢"，
        且 naive/UTC 语态漂移让 30min 阈值形同虚设。

        告警消息含 business_timestamp（worker 上报 current_date 时同步写入，①），
        便于运维定位最后业务推进点。

        Returns:
            ServiceResult: data 含 cleaned（标记 failed 数量）、total_running（扫描时
            running 总数）；Redis 不可达时 skipped=True 且 cleaned=0（防基础设施抖动误杀全量）。
        """
        try:
            import datetime

            running = self._crud_repo.get_running_tasks()
            if not running:
                return ServiceResult.success(
                    {"cleaned": 0, "total_running": 0},
                    "无 running 任务",
                )

            held = self._get_held_task_uuids()
            # Redis 不可达：无法区分"真孤儿"与"基础设施抖动"，本轮跳过防误杀全量。
            if held is None:
                GLOG.WARN("跳过本轮孤儿清理：无法读取活跃 worker 心跳（Redis 不可达）")
                return ServiceResult.success(
                    {"cleaned": 0, "total_running": len(running), "skipped": True},
                    "Redis 不可达，跳过孤儿清理",
                )

            cleaned = 0
            for task in running:
                if task.uuid in held:
                    continue
                # 宽限期:worker 心跳是 10s 周期快照,任务登记进 self.tasks 后最长
                # 10s 才随下一次心跳写进持有集。刚置 running(start_time 距今 <
                # ORPHAN_GRACE_SECONDS)的任务天然可能缺席快照,跳过防误杀——
                # 实例:2026-08-16 24ec2a63 重跑 10s 内被 Reaper 误标 failed,引擎
                # 不知情跑完才被 completed 覆盖,期间用户看到"失败但进行中"。
                # start_time 缺失(None)不宽限:保证兜底使命不受数据缺失影响。
                # 消费方适配快照滞后语义,而非要求生产方(心跳)堵漏。
                st = getattr(task, "start_time", None)
                if st is not None:
                    if st.tzinfo is not None:
                        st = st.astimezone().replace(tzinfo=None)  # 归一 naive-local(#4853 语态漂移教训)
                    if 0 <= (datetime.datetime.now() - st).total_seconds() < self.ORPHAN_GRACE_SECONDS:
                        continue
                bt = getattr(task, "business_timestamp", None)
                bt_str = bt.strftime("%Y-%m-%d %H:%M:%S") if bt else "N/A"
                self.update_status(
                    task.uuid, status="failed",
                    error_message=(
                        f"Orphan task: no active worker holds it "
                        f"(worker crashed or lost Kafka message). "
                        f"last business_timestamp={bt_str}"
                    ),
                )
                cleaned += 1
                GLOG.INFO(
                    f"Marked orphan backtest task {task.uuid[:8]}... as failed "
                    f"(not held by any active worker)"
                )

            if cleaned > 0:
                GLOG.INFO(
                    f"Cleaned {cleaned}/{len(running)} orphan running backtest tasks "
                    f"(held by active workers: {len(held)})"
                )

            return ServiceResult.success(
                {"cleaned": cleaned, "total_running": len(running)},
                f"清理 {cleaned} 个孤儿 running 任务",
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to cleanup orphan backtest tasks: {e}")
            return ServiceResult.error(f"Failed to cleanup orphan backtest tasks: {str(e)}")

    def _get_held_task_uuids(self):
        """
        读取所有活跃 backtest worker 心跳，union 出被持有的 task_uuid 集合（#6846）。

        SCAN 枚举 backtest:worker:* 心跳键（TTL 30s，过期即视为该 worker 已死），
        解析每条心跳的 task_uuids 字段取并集。

        Returns:
            set: 被持有的 task_uuid 集合（无活跃 worker 时为空集）。
            None: Redis 不可达 / 读取异常，无法判定。调用方据此跳过本轮，防误杀全量。
        """
        try:
            from ginkgo.data.redis_schema import (
                RedisKeyPrefix, BacktestWorkerHeartbeat,
            )
            from ginkgo.data.drivers import create_redis_connection

            redis = create_redis_connection()
            held = set()
            pattern = f"{RedisKeyPrefix.BACKTEST_WORKER_HEARTBEAT}:*"
            for key in redis.scan_iter(match=pattern, count=100):
                raw = redis.get(key)
                if not raw:
                    continue
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="ignore")
                try:
                    hb = BacktestWorkerHeartbeat.from_json(raw)
                    held.update(hb.task_uuids)
                except Exception:
                    # 单条心跳解析失败不拖垮整轮；坏数据留给下次或人工。
                    continue
            return held
        except Exception as e:
            GLOG.WARN(f"读取 worker 心跳失败，跳过本轮孤儿清理: {e}")
            return None

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
                # #6846: business_timestamp 此前恒 None——worker 每次上报 current_date
                # （回测当前处理的业务日期）却未落库，使其无法作"业务推进"信号。
                # 同步写入，供孤儿判定告警与运维定位（与 current_date 同源同值）。
                updates["business_timestamp"] = datetime_normalize(current_date)

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

            # 状态机检查：新任务 created 可直接启动，旧任务(completed/stopped/failed)可重新运行。
            # pending 不可再 start：pending 意味着上一轮重跑已通过守卫、清理块已执行、Kafka
            # 已派发——此时若再次通过守卫会重复执行清理块，删掉第一轮正在写入的数据并发出
            # 第二条派发消息（双引擎同 task_id 并发写入）。
            startable_states = ["created", "completed", "stopped", "failed"]
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

            # ClickHouse 无事务：尽力删除，失败告警不阻断（CH 固有限制，无回滚能力）。
            # None（未注入）显式告警跳过——与 MySQL 侧同纪律，静默跳过会掩盖清理缺口。
            for name, crud in _click_cleanups:
                if crud is None:
                    GLOG.WARN(f"Failed to delete {name} (clickhouse): CRUD not injected")
                    continue
                try:
                    crud.remove(filters={"task_id": task_id})
                    GLOG.DEBUG(f"Deleted old {name} (clickhouse)")
                except Exception as e:
                    GLOG.WARN(f"Failed to delete {name} (clickhouse, no rollback): {e}")

            # CH 日志三表（ginkgo_logs_backtest/component/performance）：日志域数据
            # 统一走 LogService（查询与删除同入口），不经 CRUD 层。worker 经 vector
            # 写入这三张表，重跑不清理会致同 task_id 新旧 run 日志混排（"日志混乱"
            # 主因）。best-effort：失败告警不阻断，与上方 CH 组同纪律。
            try:
                from ginkgo.services.logging import LogService
                _log_del = LogService().delete_logs_by_task_id(task_id)
                for _table, _ok in _log_del.items():
                    if not _ok:
                        GLOG.WARN(f"Failed to delete {_table} logs (clickhouse, no rollback)")
            except Exception as e:
                GLOG.WARN(f"Failed to delete ginkgo_logs_* (clickhouse, no rollback): {e}")

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

            # 先更新状态为 pending，确保 Worker 查询时能看到正确的状态。
            # 重跑摘要归零：上方清理块只删 9 表记录，backtest_task 行自身的摘要列
            # （pnl/sharpe/回撤等）不在删除范围——须同步重置，否则重跑运行中/
            # 失败期间详情页仍展示上一次运行的成功数值（曲线已清空、摘要残留）。
            _run_summary_reset = {
                "progress": 0,
                "total_orders": 0,
                "total_signals": 0,
                "total_positions": 0,
                "total_events": 0,
                "duration_seconds": None,
                "start_time": None,
                "end_time": None,
                "final_portfolio_value": 0.0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "annual_return": 0.0,
                "win_rate": 0.0,
            }
            status_result = self.update_status(
                real_uuid, status="pending", error_message="", **_run_summary_reset
            )
            if not status_result.is_success():
                # 入口 startable 守卫是 check-then-act,非原子:并发双击的第二个
                # start 可能在守卫通过后、此处写 pending 前,被第一个 start 的
                # worker 认领抢先置成 running。状态机守卫拦下(2026-08-17 实例:
                # running→pending 被拒报 400)——这恰是守卫的价值:旧版无守卫时
                # 此处会静默打回 pending,重复清理+双引擎并发写入。转化为友好语义。
                if getattr(status_result, "code", None) == "ILLEGAL_TRANSITION":
                    return ServiceResult.error(
                        f"Task is already being started (concurrent start detected). "
                        f"Current status: {status_result.error}"
                    )
                return ServiceResult.error(f"Failed to update task status to pending: {status_result.error}")

            GLOG.DEBUG(f"Updated task {real_uuid} status to pending")

            # portfolio.performance 同步归零：任务行摘要已重置，但 portfolio 表的
            # 绩效快照（annual_return/sharpe 等）不在其中——不重置则列表页在重跑
            # 期间仍展示上一次运行的成绩。尽力而为，失败告警不阻断启动。
            if self._portfolio_service is not None:
                try:
                    self._portfolio_service.update_performance(
                        task.portfolio_id,
                        annual_return=0.0, sharpe_ratio=0.0, max_drawdown=0.0,
                        win_rate=0.0, total_trades=0, winning_trades=0,
                    )
                except Exception as e:
                    GLOG.WARN(f"Failed to reset portfolio performance: {e}")

            # 构建 Kafka config：从 config_snapshot 恢复，显式参数覆盖
            kafka_config = {}
            # 从 snapshot 恢复所有字段作为基础
            # ADR-018：死字段 broker_type/broker_attitude/commission_min 不进 wire spec（消费端 BacktestConfig 不读）
            # ADR-037 方案B：fill_price_policy 与 slippage_rate 同列透传——消费端 BacktestConfig 读此字段
            # 决定成交价模型；漏传则 DTO 回退默认 attitude，--fill-price-policy slippage 在 API/WebUI→Kafka→worker 路径静默失效
            for key in ("initial_cash", "commission_rate", "slippage_rate", "frequency",
                        "benchmark_return", "max_position_ratio",
                        "stop_loss_ratio", "take_profit_ratio", "fill_price_policy"):
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
            # #6786：trace_id 经 Kafka header 跨进程传播（与 api 层 send_task_to_kafka 对称），
            # POST /{uuid}/start 入口同进程继承 #6784 TraceIdMiddleware 注入的 GLOG contextvars。
            # None 时等价不传，向后兼容（既有 start_task 测试断言位置参数不受影响）。
            trace_id = GLOG.get_trace_id()
            headers = [("trace_id", trace_id.encode())] if trace_id else None
            send_ok = producer.send(KafkaTopics.BACKTEST_ASSIGNMENTS, assignment, headers=headers)
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

        状态机规则：可停止 created/pending/running 状态的任务（#5421）
        - created/pending：委托 cancel_task（走 CancelAssignment，worker _cancel_task
          真实清理 in-memory task；StopAssignment 在 worker 端是 no-op 死信）
        - running：发 StopAssignment（worker 正在执行，发 stop 信号）
        - 终态（completed/failed/stopped）拒绝

        review #6543：原扩白名单后对 created/pending 一并发 StopAssignment，但 worker
        端该 handler 是显式 no-op（DTO A1 未实现），与 CancelAssignment 走 _cancel_task
        真实清理不对称——卡住场景未真正修复。故 created/pending 改走 cancel 路径。

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

            # 状态机检查：created/pending/running 均可停（#5421）；终态拒绝
            stoppable_states = ("running", "created", "pending")
            if task.status not in stoppable_states:
                return ServiceResult.error(
                    f"Cannot stop task with status '{task.status}'. "
                    f"Only tasks in {', '.join(stoppable_states)} can be stopped."
                )

            # created/pending：尚未执行或刚被 worker 接收，委托 cancel_task 走真实清理
            # （CancelAssignment → worker _cancel_task → processor.cancel()）。
            # review #6543：StopAssignment 在 worker 端是 no-op（DTO A1 未实现），
            # created/pending 走它对 worker 卡住场景无效，须走 CancelAssignment。
            if task.status in ("created", "pending"):
                return self.cancel_task(uuid)

            # running：worker 正在执行，发 StopAssignment（graceful-stop A1 实现后生效）
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

    def get_latest_completed_task_id(self, portfolio_id: str) -> ServiceResult:
        """获取 portfolio 最新已完成回测的 task_id (#5196: 供 deploy 自动溯源回测→部署链路).

        复用 get_latest_completed 的 find 查询模式 (portfolio_id + status=completed,
        order_by create_at desc, limit 1)。无记录时返回 success+data=None，由调用方决定留空。
        """
        try:
            tasks = self._crud_repo.find(
                filters={"portfolio_id": portfolio_id, "status": "completed", "is_del": False},
                order_by="create_at",
                desc_order=True,
                page_size=1,
            )
            if not tasks:
                return ServiceResult.success(data=None)
            # task_id 是回测任务主标识(≡uuid, ADR-016)，deploy 写入 MDeployment.source_task_id
            return ServiceResult.success(data=getattr(tasks[0], "task_id", None))
        except Exception as e:
            return ServiceResult.error(f"Failed to get latest completed task_id: {str(e)}")

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
            # 列表默认按 update_at 排序/展示;旧行 update_at 可能缺省,回退 create_at
            update_at=self._format_dt(getattr(task, "update_at", None) or getattr(task, "create_at", None)) or "",
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
            # 时间字段下推 DB 级排序(分页前全局有序);指标字段仍走页内排序
            db_sortable = ("create_at", "update_at")
            result = self.list(
                page=page, page_size=page_size,
                portfolio_id=portfolio_id, status=status,
                sort_by=sort_by if sort_by in db_sortable else None,
                sort_order=sort_order,
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

            # 当前页内排序(仅指标字段;时间字段已在 DB 级排序,页内重排会破坏分页全局有序)
            sortable = {"annual_return", "sharpe_ratio", "max_drawdown", "win_rate", "total_pnl"}
            if sort_by in sortable:
                reverse = sort_order != "asc"
                summaries.sort(key=lambda s: getattr(s, sort_by, 0) or 0, reverse=reverse)

            sr = ServiceResult.success(data=summaries, message="Backtest summaries retrieved")
            sr.set_metadata("total", total)
            return sr
        except Exception as e:
            GLOG.ERROR(f"list_summaries failed: {e}")
            return ServiceResult.error(f"Failed to list summaries: {e}")

    def get_portfolio_stats(self, portfolio_id: str) -> ServiceResult:
        """
        聚合某 Portfolio 全部已完成回测的统计指标。

        指标列直接取自 MBacktestTask（回测完成时写入），无需逐任务拉 analyzer。
        净值 = final_portfolio_value / config_snapshot.initial_cash（缺初始资金时跳过该样本）。
        """
        try:
            # page_size=0 → 全量（ADR-021 "0=all"）
            result = self.list(page=0, page_size=0, portfolio_id=portfolio_id)
            if not result.is_success():
                return result

            tasks = (result.data or {}).get("data", []) or []
            total = len(tasks)

            navs: list[float] = []
            drawdowns: list[float] = []
            sharpes: list[float] = []
            annual_returns: list[float] = []
            win_rates: list[float] = []
            latest_completed = None  # create_at 最近的已完成任务摘要
            # 比较用 raw datetime（存储时才 _format_dt 成 str）：
            # 若拿 datetime 与已格式化的 str 比较会 TypeError（多任务时必触发）
            latest_created_raw = None

            for t in tasks:
                if (getattr(t, "status", "") or "") != "completed":
                    continue
                final_value = float(getattr(t, "final_portfolio_value", 0) or 0)
                config_str = getattr(t, "config_snapshot", "{}") or "{}"
                config = json.loads(config_str) if isinstance(config_str, str) else (config_str or {})
                initial_cash = float(config.get("initial_cash") or 0)
                if initial_cash > 0 and final_value > 0:
                    navs.append(final_value / initial_cash)

                drawdowns.append(float(getattr(t, "max_drawdown", 0) or 0))
                sharpes.append(float(getattr(t, "sharpe_ratio", 0) or 0))
                annual_returns.append(float(getattr(t, "annual_return", 0) or 0))
                win_rates.append(float(getattr(t, "win_rate", 0) or 0))

                created = getattr(t, "create_at", None)
                if latest_completed is None or (
                    created is not None
                    and (latest_created_raw is None or created > latest_created_raw)
                ):
                    latest_created_raw = created
                    latest_completed = {
                        "uuid": getattr(t, "uuid", ""),
                        "name": getattr(t, "name", ""),
                        "created_at": self._format_dt(created) or "",
                        "nav": navs[-1] if (initial_cash > 0 and final_value > 0) else None,
                        "max_drawdown": drawdowns[-1],
                        "sharpe_ratio": sharpes[-1],
                        "annual_return": annual_returns[-1],
                        "win_rate": win_rates[-1],
                    }

            def _avg(vals: list[float]) -> Optional[float]:
                return round(sum(vals) / len(vals), 6) if vals else None

            stats = {
                "portfolio_id": portfolio_id,
                "total_backtests": total,
                "completed_backtests": len(drawdowns),
                "avg_nav": _avg(navs),
                "best_nav": round(max(navs), 6) if navs else None,
                "worst_nav": round(min(navs), 6) if navs else None,
                "avg_max_drawdown": _avg(drawdowns),
                "worst_max_drawdown": round(max(drawdowns), 6) if drawdowns else None,
                "best_max_drawdown": round(min(drawdowns), 6) if drawdowns else None,
                "avg_sharpe_ratio": _avg(sharpes),
                "best_sharpe_ratio": round(max(sharpes), 6) if sharpes else None,
                "avg_annual_return": _avg(annual_returns),
                "avg_win_rate": _avg(win_rates),
                "latest_completed": latest_completed,
            }
            return ServiceResult.success(stats, "Portfolio backtest stats retrieved")
        except Exception as e:
            GLOG.ERROR(f"get_portfolio_stats failed: {e}")
            return ServiceResult.error(f"Failed to get portfolio stats: {e}")

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
        """获取回测信号列表，返回 list[BacktestSignalItem]

        page 对外 1-based（与 API Query(1, ge=1) 对齐）；result_service.get_signals
        是 0-based（page 直通 crud find 作 offset 基数），此处下推前转换。
        原样透传时 page=1 → offset=page_size，跳过前 page_size 条——总量不足一页的
        回测（如仅 4 条信号）直接返回空列表，前端信号 tab 显示"暂无信号记录"。
        """
        from ginkgo.data.services.backtest_task_schemas import BacktestSignalItem

        try:
            task_id, portfolio_id, err = self._resolve_task_id(uuid)
            if err:
                return err

            from ginkgo.data.containers import container
            result_service = container.result_service()
            result = result_service.get_signals(
                task_id=task_id,
                page=max(page - 1, 0),
                page_size=page_size,
            )
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
                    weight=convert_to_float(getattr(s, "weight", 0)) or 0.0,
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
                    order_id=getattr(o, "order_id", "") or "",
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
                    signal_id=getattr(o, "signal_id", "") or "",
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
                    order_id=getattr(o, "order_id", "") or "",
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
                    order_id=getattr(o, "order_id", "") or "",
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
                    signal_id=getattr(o, "signal_id", "") or "",
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
                cost = convert_to_float(getattr(p, "cost", 0))
                volume = int(getattr(p, "volume", 0) or 0)
                price = convert_to_float(getattr(p, "price", 0))
                fee = convert_to_float(getattr(p, "fee", 0))
                # 记录是持仓变更流水（volume 为带符号 delta：卖出为负），
                # cost 为每股加权均价（Position._cost 口径）。
                # 市值按该笔变更的规模（|volume|）计，方向由 direction 表达；
                # 盈亏仅卖出行有意义（2026-08-17 定稿）：
                #   SELL 行 profit = (卖价-剩余均价)*|vol|-fee = 已实现盈亏
                #     （与 Position._sold 的 realized_gain 同口径，仅多扣 fee）
                #   BUY  行 profit = None —— cost 是成交后加权均价（先 deal 再记
                #     流水），(price-cost)*vol 是均价漂移残差：首仓恒=-fee（纯
                #     手续费）、加仓为本笔价相对新均价的偏离（无金融语义）。
                abs_volume = abs(volume)
                # 变动方向:优先记录中的显式枚举,缺失/非法时按 volume 符号派生兜底
                # （int() 对 None/Mock 抛 TypeError，须捕获后走派生）
                try:
                    direction = int(getattr(p, "direction", 0)) or (1 if volume >= 0 else 2)
                except (TypeError, ValueError):
                    direction = 1 if volume >= 0 else 2
                market_value = price * abs_volume
                if direction == 2:  # SELL:已实现盈亏
                    profit = (price - cost) * abs_volume - fee
                    cost_basis = cost * abs_volume
                    profit_pct = (profit / cost_basis) if cost_basis > 0 else None
                else:               # BUY:无盈亏语义
                    profit = None
                    profit_pct = None
                # timestamp 主显事件时间（business_timestamp）；CH 记录的 timestamp
                # 是写入时刻（回测结束落库时间），非行情时间
                event_ts = getattr(p, "business_timestamp", None) or getattr(p, "timestamp", None)
                items.append(BacktestPositionItem(
                    uuid=getattr(p, "uuid", ""),
                    portfolio_id=getattr(p, "portfolio_id", ""),
                    engine_id=getattr(p, "engine_id", ""),
                    task_id=getattr(p, "task_id", ""),
                    code=getattr(p, "code", ""),
                    cost=cost,
                    volume=volume,
                    frozen_volume=int(getattr(p, "frozen_volume", 0) or 0),
                    price=price,
                    fee=fee,
                    timestamp=self._format_dt(event_ts) or "",
                    business_timestamp=self._format_dt(getattr(p, "business_timestamp", None)) or "",
                    direction=direction,
                    market_value=market_value,
                    profit=profit,
                    profit_pct=profit_pct,
                    # 血缘:引发本次持仓变动的订单。漏传会断 Signal→Order→Position
                    # 追溯链(前端 order_id 恒空→持仓列无法关联,2026-08-17 实证)
                    order_id=getattr(p, "order_id", "") or "",
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
        from ginkgo.trading.analysis.analyzers import ANALYZER_DESCRIPTIONS

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
                    description=ANALYZER_DESCRIPTIONS.get(name, ""),
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

