# Upstream: 数据同步 API (update_data), 数据概览页 (sync/history)
# Downstream: BaseService (继承), DataSyncRecordCRUD (数据访问)
# Role: 数据同步记录业务服务，提供同步开始记录、完成更新、历史查询

"""
Data Sync Record Service

数据同步记录的业务服务层，封装 CRUD 操作并提供业务语义接口。
"""

import time
from typing import Optional, Dict, Any

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG
from ginkgo.enums import TRIGGER_SOURCE_TYPES


class DataSyncRecordService(BaseService):
    """
    数据同步记录服务

    提供：
    - record_start: 记录同步开始
    - record_complete: 更新同步结果
    - record_fail: 更新为失败状态
    - get_history: 分页查询同步历史
    """

    def record_start(
        self,
        sync_type: str,
        code: str,
        trigger_source: str = "manual",
        status: str = "running",
    ) -> ServiceResult:
        """
        记录同步开始

        Args:
            sync_type: 同步类型 (stockinfo/bars/ticks/adjustfactor)
            code: 股票代码，stockinfo 用 "ALL"

        Returns:
            ServiceResult: 包含 uuid 和 status
        """
        try:
            record = self._crud_repo.record_start(
                sync_type=sync_type,
                code=code,
                trigger_source=trigger_source,
                status=status,
            )
            if record:
                return ServiceResult.success(
                    data={"uuid": record.uuid, "status": record.status},
                    message=f"Sync start recorded for {sync_type}/{code}",
                )
            return ServiceResult.error("Failed to record sync start")
        except Exception as e:
            return ServiceResult.error(f"Failed to record sync start: {str(e)}")

    def record_complete(
        self,
        uuid: str,
        status: str,
        duration_ms: int = 0,
        records_processed: int = 0,
        records_added: int = 0,
        records_updated: int = 0,
        records_failed: int = 0,
        error_message: Optional[str] = None,
        sync_strategy: str = "",
    ) -> ServiceResult:
        """
        更新同步记录为完成状态

        Args:
            uuid: 记录 ID
            status: success / partial / failed
            duration_ms: 耗时毫秒
            records_*: 同步统计
            error_message: 失败原因
            sync_strategy: 同步策略

        Returns:
            ServiceResult
        """
        try:
            success = self._crud_repo.record_complete(
                uuid=uuid,
                status=status,
                duration_ms=duration_ms,
                records_processed=records_processed,
                records_added=records_added,
                records_updated=records_updated,
                records_failed=records_failed,
                error_message=error_message,
                sync_strategy=sync_strategy,
            )
            if success:
                return ServiceResult.success(
                    data={"uuid": uuid, "status": status},
                    message=f"Sync record updated to {status}",
                )
            return ServiceResult.error("Failed to complete sync record")
        except Exception as e:
            return ServiceResult.error(f"Failed to complete sync record: {str(e)}")

    # ---- 执行租约(2026-08-18) ----
    # 长任务(tick 单股可跑数小时)不能用固定时长阈值判僵尸;改记录级租约:
    # 执行方(worker/CLI 前台)持租约并周期续期,进程死亡 → 无人续期 → TTL 过期
    # → reap 判僵尸。Redis 不可达时降级为"仅年龄判定"(2 小时兜底)。
    LEASE_TTL_SECONDS = 90
    LEASE_RENEW_INTERVAL = 60
    LEASE_FALLBACK_MINUTES = 120   # Redis 全程不可用时的兜底年龄(保守不误杀)
    QUEUE_IDLE_MINUTES = 30        # 队列静止判定(无任何记录流转即视为队列死)
    QUEUE_RETENTION_HOURS = 24 * 7 # queued 绝对边界,对齐 Kafka 默认 retention 7 天
    # reap 双确认候选(实例内存):uuid → 首次观测到 alive=False 的时间戳。
    # 不入 Redis——Redis 故障场景恰恰是它要防护的
    _reap_candidates: dict = {}

    def _lease_key(self, uuid_: str) -> str:
        return f"ginkgo:sync:lease:{uuid_}"

    def _lease_seed(self, uuid_: str) -> bool:
        """写入/续期租约。返回是否成功(Redis 不可达 → False,调用方降级)。"""
        try:
            from ginkgo.data.drivers import create_redis_connection
            r = create_redis_connection()
            r.set(self._lease_key(uuid_), "1", ex=self.LEASE_TTL_SECONDS)
            return True
        except Exception as e:
            GLOG.WARN(f"sync lease seed failed (degraded): {e}")
            return False

    def _lease_drop(self, uuid_: str) -> None:
        try:
            from ginkgo.data.drivers import create_redis_connection
            create_redis_connection().delete(self._lease_key(uuid_))
        except Exception:
            pass

    def _lease_alive(self, uuid_: str) -> bool | None:
        """租约存活?;None=Redis 不可达(判定降级,不得当僵尸处理)"""
        try:
            from ginkgo.data.drivers import create_redis_connection
            return bool(create_redis_connection().exists(self._lease_key(uuid_)))
        except Exception:
            return None

    def record_dispatch_batch(self, sync_type: str, codes: list, trigger_source: str = "web") -> list:
        """批量建立 queued 记录(2026-08-18 queued 方案,B 选项):codes=all 场景
        一次请求建数千条,逐条 record_start(每条一事务)会把 API 派发拖到数十秒
        ——单事务批量插入,返回 uuid 列表与 codes 顺序对齐。
        status 列为 String,queued 无需迁移。"""
        try:
            return self._crud_repo.record_dispatch_batch(
                sync_type=sync_type, codes=codes, trigger_source=trigger_source,
            )
        except Exception as e:
            GLOG.WARN(f"record_dispatch_batch failed: {e}")
            return []

    def recorded(self, sync_type: str, code: str, trigger_source: str = "web", existing_uuid: str = None):
        """同步执行落记录的统一包裹(2026-08-18):worker handler 与 CLI 进程内模式共用。

        with svc.recorded("bars", code, trigger_source="cli") as (rec_uuid, started):
            result = bar_service.sync_smart(code)
            svc.record_result(rec_uuid, result, started)

        租约:进入时写 key(TTL 90s)+后台线程 60s 续期——长任务(tick 数小时)
        只要进程活着就持续持租;进程死亡 key 自灭,reap 据此收敛僵尸。
        """
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            # 消费端复活(queued 方案):消息带 _record 时该记录已在派发时建立
            # (status=queued/lost/任何态)——无条件拉回 running 重置计时,不再 INSERT;
            # 无 _record(tasktimer 老命令/裸命令)走原 record_start 路径
            if existing_uuid:
                import datetime as _dt
                self._crud_repo.modify(
                    filters={"uuid": existing_uuid},
                    updates={"status": "running", "started_at": _dt.datetime.now(), "error_message": None},
                )
                uuid_ = existing_uuid
            else:
                rec = self.record_start(sync_type=sync_type, code=code, trigger_source=trigger_source)
                uuid_ = rec.data.get("uuid") if rec.is_success() and rec.data else None
            started = time.time()
            lease_thread = None
            if uuid_:
                self._lease_seed(uuid_)
                import threading

                def _renew_loop(u):
                    # 续租永不放弃(2026-08-18 修订):曾在断供超 TTL 时 break 弃租
                    # ——线程一死,Redis 恢复后无人补写 key,长挂恢复场景下正在执行
                    # 的任务会被 reap 误杀(存活必须可恢复,而非一次性判定)。改为
                    # 无限重试:Redis 恢复后下一轮 60s seed 成功,租约自动复活。
                    # Redis 长挂期间 reap 走 degraded fail-open,不会杀记录。
                    fail_streak = 0
                    while not stop_evt.is_set():
                        stop_evt.wait(self.LEASE_RENEW_INTERVAL)
                        if stop_evt.is_set():
                            break
                        if self._lease_seed(u):
                            if fail_streak >= 2:
                                GLOG.INFO(f"sync lease recovered after {fail_streak} failures: {u[:8]}")
                            fail_streak = 0
                        else:
                            fail_streak += 1
                stop_evt = threading.Event()
                lease_thread = threading.Thread(target=_renew_loop, args=(uuid_,), daemon=True)
                lease_thread.start()
            try:
                yield uuid_, started
            except Exception as e:
                if uuid_: self.record_fail(uuid=uuid_, error_message=str(e))
                raise
            finally:
                if uuid_:
                    stop_evt.set()
                    self._lease_drop(uuid_)
        return _ctx()

    def record_result(self, uuid_, result, started: float) -> None:
        """按 ServiceResult 落同步结果(success → 计数回写 / 失败 → record_fail)。"""
        if not uuid_: return
        duration_ms = int((time.time() - started) * 1000)
        if getattr(result, "success", False) or (hasattr(result, "is_success") and result.is_success()):
            data = getattr(result, "data", None)
            processed = getattr(data, "records_processed", None)
            added = getattr(data, "records_added", None)
            updated = getattr(data, "records_updated", None)
            failed = getattr(data, "records_failed", None)
            self.record_complete(
                uuid=uuid_, status="success", duration_ms=duration_ms,
                records_processed=processed or 0, records_added=added or 0,
                records_updated=updated or 0, records_failed=failed or 0,
            )
        else:
            self.record_fail(uuid=uuid_, error_message=str(getattr(result, "error", "") or getattr(result, "message", ""))[:500])

    def record_fail(
        self,
        uuid: str,
        error_message: str,
    ) -> ServiceResult:
        """
        更新同步记录为失败状态

        Args:
            uuid: 记录 ID
            error_message: 失败原因

        Returns:
            ServiceResult
        """
        return self.record_complete(
            uuid=uuid,
            status="failed",
            error_message=error_message,
        )

    def reap_stale_running(self) -> int:
        """清理僵尸 running 记录(2026-08-18,租约判定版;CRUD 原语实现,无裸 SQL)。

        判据(替代固定时长阈值——tick 单股可跑数小时,15min 会误杀):
        - 租约死亡:status=running 且 Redis 租约不存在(执行进程已死,TTL 90s 自灭)
          且过双确认(两轮 reap 间隔 ≥ 续租周期仍 False——防 Redis 重启清 key 的
          补写窗口误杀)
        - 降级路径:Redis 全程不可达 → 按 LEASE_FALLBACK_MINUTES 年龄兜底(保守)
        触发:get_history 惰性(历史页每次查询)。
        """
        import datetime
        try:
            running = self._crud_repo.find(filters={"status": "running"})
            if not running:
                self._reap_candidates.clear()
                return 0
            uuids = [r.uuid for r in running]

            # Redis 探测:任一失败即整体降级(fail-open,不基于租约杀)
            alive_map = {}
            degraded = False
            for u in uuids:
                a = self._lease_alive(u)
                if a is None:
                    degraded = True
                    break
                alive_map[u] = a

            if degraded:
                cutoff = datetime.datetime.now() - datetime.timedelta(minutes=self.LEASE_FALLBACK_MINUTES)
                stale = [r.uuid for r in running if r.started_at and r.started_at < cutoff]
                self._crud_repo.modify(
                    filters={"uuid__in": stale},
                    updates={
                        "status": "failed",
                        "completed_at": datetime.datetime.now(),
                        "error_message": "interrupted: executor lease unknown (redis degraded, age fallback)",
                    },
                )
                return len(stale)

            dead = [u for u in uuids if not alive_map.get(u)]
            if not dead:
                self._reap_candidates.clear()
                return 0

            # 双确认:alive=False 首轮只记候选;两轮间隔 ≥ 续租周期仍 False 才真死
            now = time.time()
            confirmed = [u for u in dead
                         if u in self._reap_candidates
                         and now - self._reap_candidates[u] >= self.LEASE_RENEW_INTERVAL]
            self._reap_candidates = {u: now for u in dead}
            if not confirmed:
                return 0
            self._crud_repo.modify(
                filters={"uuid__in": confirmed},
                updates={
                    "status": "failed",
                    "completed_at": datetime.datetime.now(),
                    "error_message": "interrupted: executor died (lease expired, double-confirmed)",
                },
            )
            return len(confirmed)
        except Exception as e:
            GLOG.WARN(f"reap_stale_running failed (non-blocking): {e}")
            return 0

    def reap_stale_queued(self) -> int:
        """queued 僵尸清理(2026-08-18,三层判定)。

        queued 的活性主体是 Kafka 里那条消息(无执行体,租约不适用):
        a. 队列活性(主判据):最近 QUEUE_IDLE_MINUTES 内存在任何记录流转
           (update_at 变化,worker 每消费一条必产生) → 队列在动,
           queued 全部保留——首次全量(codes=all)排几天也不误杀;
        b. 队列静止:无任何流转超 QUEUE_IDLE_MINUTES → 滞留 queued 标 lost;
        c. 绝对边界:age > QUEUE_RETENTION_HOURS(对齐 Kafka retention 7天)
           → 消息物理不存在,直接 lost(不依赖队列状态)。
        误杀兜底:消费端复活(existing_uuid 无条件拉回 running)。
        """
        import datetime
        try:
            latest = self._crud_repo.find(order_by="update_at", desc_order=True, page_size=1)
            queue_active = bool(latest) and latest[0].update_at and (
                datetime.datetime.now() - latest[0].update_at
            < datetime.timedelta(minutes=self.QUEUE_IDLE_MINUTES)
            )
            cutoff_retention = datetime.datetime.now() - datetime.timedelta(hours=self.QUEUE_RETENTION_HOURS)
            if queue_active:
                # 队列在动:只清超过 retention 的绝对死信(消息物理已不存在)
                doomed = self._crud_repo.find(
                    filters={"status": "queued", "started_at__lt": cutoff_retention})
            else:
                # 队列静止:滞留超 idle 窗口的全部清算
                cutoff_idle = datetime.datetime.now() - datetime.timedelta(minutes=self.QUEUE_IDLE_MINUTES)
                doomed = self._crud_repo.find(
                    filters={"status": "queued", "started_at__lt": cutoff_idle})
            if not doomed:
                return 0
            self._crud_repo.modify(
                filters={"uuid__in": [r.uuid for r in doomed]},
                updates={
                    "status": "lost",
                    "completed_at": datetime.datetime.now(),
                    "error_message": "dispatched but never consumed (queue idle/retention)",
                },
            )
            return len(doomed)
        except Exception as e:
            GLOG.WARN(f"reap_stale_queued failed (non-blocking): {e}")
            return 0

    def get_history(
        self,
        sync_type: Optional[str] = None,
        trigger_source: Optional[str] = None,
        page: int = 0,
        page_size: int = 20,
    ) -> ServiceResult:
        """
        分页查询同步历史(查询前惰性清理僵尸 running——见 reap_stale_running)

        Args:
            sync_type: 按类型筛选 (可选)
            page: 页码（从 0 开始）
            page_size: 每页数量

        Returns:
            ServiceResult: {"items": [...], "total": N}
        """
        try:
            self.reap_stale_running()
            self.reap_stale_queued()
            items = self._crud_repo.find_recent(
                sync_type=sync_type,
                trigger_source=trigger_source,
                page=page,
                page_size=page_size,
            )
            count_filters: Dict[str, Any] = {}
            if sync_type:
                count_filters["sync_type"] = sync_type
            if trigger_source:
                enum_val = TRIGGER_SOURCE_TYPES.enum_convert(str(trigger_source))
                if enum_val is not None:
                    count_filters["trigger_source"] = enum_val.value
            total = self._crud_repo.count(filters=count_filters)

            data = []
            for item in items:
                data.append({
                    "uuid": item.uuid,
                    "sync_type": item.sync_type,
                    "code": item.code,
                    "trigger_source": TRIGGER_SOURCE_TYPES.from_int(item.trigger_source).name.lower()
                        if item.trigger_source is not None else "manual",
                    "status": item.status,
                    "started_at": item.started_at.isoformat() if item.started_at else None,
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "duration_ms": item.duration_ms,
                    "records_processed": item.records_processed,
                    "records_added": item.records_added,
                    "records_updated": item.records_updated,
                    "records_failed": item.records_failed,
                    "error_message": item.error_message,
                    "sync_strategy": item.sync_strategy,
                })

            return ServiceResult.success(
                data={"items": data, "total": total},
                message=f"Found {total} sync records",
            )
        except Exception as e:
            return ServiceResult.error(f"Failed to get sync history: {str(e)}")
