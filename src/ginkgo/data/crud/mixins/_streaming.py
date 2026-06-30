"""BaseCRUD 内部实现：流式查询、检查点和监控。

此模块是 BaseCRUD 的文件拆分部分，不是独立的 Mixin。
仅通过 BaseCRUD 使用，不对外导出。
"""

import time
from typing import Any, Dict, Optional, List, Callable, Tuple

from ginkgo.libs import GLOG, time_logger


class _Streaming:
    """BaseCRUD 的流式查询能力实现。

    依赖 CoreCRUD.__init__ 设置的实例属性：
    - self._streaming_enabled
    - self._streaming_engine
    - self._streaming_config
    - self._streaming_initialized
    - self._is_clickhouse
    - self._is_mysql
    - self.model_class

    And methods from CoreCRUD:
    - self.find()
    - self.count()
    """

    # ============================================================================
    # 流式查询功能 - 新增功能，完全向后兼容
    # ============================================================================


    def _initialize_streaming(self) -> None:
        """延迟初始化流式查询功能"""
        if self._streaming_initialized:
            return

        try:
            # 导入流式查询模块（延迟导入避免循环依赖）
            from ginkgo.data.streaming.config import get_config
            from ginkgo.data.streaming.engines import BaseStreamingEngine

            # 加载配置
            self._streaming_config = get_config()
            self._streaming_enabled = self._streaming_config.enabled

            if self._streaming_enabled:
                GLOG.DEBUG(f"Streaming functionality enabled for {self.model_class.__name__}")
            else:
                GLOG.DEBUG(f"Streaming functionality disabled for {self.model_class.__name__}")

            self._streaming_initialized = True

        except Exception as e:
            GLOG.WARN(f"Failed to initialize streaming for {self.model_class.__name__}: {e}")
            self._streaming_enabled = False
            self._streaming_initialized = True

    def _get_streaming_engine(self):
        """获取流式查询引擎"""
        if not self._streaming_initialized:
            self._initialize_streaming()

        if not self._streaming_enabled:
            raise RuntimeError(
                "Streaming functionality is disabled. "
                "Enable it in config: streaming.enabled = true"
            )

        if self._streaming_engine is None:
            try:
                # 延迟导入和创建引擎
                if self._is_mysql:
                    from ginkgo.data.streaming.engines.mysql_streaming_engine import MySQLStreamingEngine
                    self._streaming_engine = MySQLStreamingEngine(
                        self._get_connection(),
                        self._streaming_config
                    )
                elif self._is_clickhouse:
                    from ginkgo.data.streaming.engines.clickhouse_streaming_engine import ClickHouseStreamingEngine
                    self._streaming_engine = ClickHouseStreamingEngine(
                        self._get_connection(),
                        self._streaming_config
                    )
                else:
                    raise RuntimeError(f"No streaming engine available for {self.model_class}")

                GLOG.DEBUG(f"Created streaming engine for {self.model_class.__name__}")

            except ImportError as e:
                # 如果引擎尚未实现，提供友好的错误信息
                raise RuntimeError(
                    f"Streaming engine not available for {self.model_class}. "
                    f"This feature is still under development: {e}"
                )

        return self._streaming_engine

    @time_logger
    def stream_find(self,
                   filters: Optional[Dict[str, Any]] = None,
                   batch_size: Optional[int] = None,
                   order_by: Optional[str] = None,
                   desc_order: bool = False) -> Any:
        """
        🆕 流式查询接口 - 新增功能，不影响现有find()方法

        提供高性能的流式查询，适用于大数据集处理。
        内存占用稳定，支持断点续传和进度监控。

        Args:
            filters: 查询过滤条件（支持操作符，如field__gte）
            batch_size: 批次大小，默认使用配置值
            order_by: 排序字段
            desc_order: 是否降序

        Yields:
            Iterator[List[T]]: 批次数据迭代器

        Example:
            >>> # 流式查询500万条K线数据
            >>> for batch in bar_crud.stream_find(
            ...     filters={'timestamp__gte': '2020-01-01'},
            ...     batch_size=1000
            ... ):
            ...     process_batch(batch)  # 处理1000条数据
        """
        try:
            # 获取流式查询引擎
            engine = self._get_streaming_engine()

            # 构建基础查询（参数化，防 SQL 注入 #3859）
            base_query, params = self._build_streaming_query(filters, order_by, desc_order)

            # 执行流式查询（params 绑定 value）
            return engine.execute_stream(
                query=base_query,
                params=params,
                filters=filters or {},
                batch_size=batch_size
            )

        except Exception as e:
            GLOG.ERROR(f"Stream find failed for {self.model_class.__name__}: {e}")

            # 自动降级到传统查询（如果启用了降级）
            if self._streaming_config and self._streaming_config.recovery.enable_fallback:
                GLOG.WARN(f"Falling back to traditional query for {self.model_class.__name__}")
                return self._fallback_to_traditional_query(filters, batch_size, order_by, desc_order)
            else:
                raise

    def stream_find_with_progress(self,
                                 filters: Optional[Dict[str, Any]] = None,
                                 batch_size: Optional[int] = None,
                                 progress_callback: Optional[Any] = None,
                                 **kwargs) -> Any:
        """
        🆕 带进度回调的流式查询

        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            progress_callback: 进度回调函数 callback(progress_info)
            **kwargs: 其他参数

        Yields:
            Iterator[List[T]]: 批次数据迭代器
        """
        # 获取引擎并添加进度观察者
        engine = self._get_streaming_engine()

        if progress_callback:
            # 创建进度观察者
            from ginkgo.data.streaming.engines.base_streaming_engine import ProgressObserver

            class CallbackObserver(ProgressObserver):
                def __init__(self, callback):
                    self.callback = callback

                def on_progress_update(self, progress):
                    self.callback(progress)

                def on_batch_processed(self, batch_index, batch_size):
                    pass

                def on_error(self, error):
                    pass

            observer = CallbackObserver(progress_callback)
            engine.add_observer(observer)

        try:
            yield from self.stream_find(filters, batch_size, **kwargs)
        finally:
            # 清理观察者
            if progress_callback:
                engine.remove_observer(observer)

    def is_streaming_enabled(self) -> bool:
        """检查流式查询是否已启用"""
        if not self._streaming_initialized:
            self._initialize_streaming()
        return self._streaming_enabled

    def enable_streaming(self) -> None:
        """运行时启用流式查询"""
        if not self._streaming_initialized:
            self._initialize_streaming()
        self._streaming_enabled = True
        GLOG.INFO(f"Streaming enabled for {self.model_class.__name__}")

    def disable_streaming(self) -> None:
        """运行时禁用流式查询"""
        self._streaming_enabled = False
        self._streaming_engine = None
        GLOG.INFO(f"Streaming disabled for {self.model_class.__name__}")

    def get_streaming_metrics(self) -> Optional[Any]:
        """获取流式查询性能指标"""
        if self._streaming_engine:
            return self._streaming_engine.get_metrics()
        return None

    # ==================== 内部辅助方法 ====================

    def _build_streaming_query(self,
                              filters: Optional[Dict[str, Any]] = None,
                              order_by: Optional[str] = None,
                              desc_order: bool = False) -> Tuple[str, Dict[str, Any]]:
        """构建流式查询SQL语句（value 参数化绑定，防 SQL 注入 #3859）。

        列名经 ``hasattr`` 白名单保护（不可注入）；value 经 ``%(name)s`` 命名占位符
        绑定（MySQL PyMySQL/mysqlclient 与 ClickHouse clickhouse-driver 均支持
        named paramstyle + dict params）。

        Returns:
            (query, params): query 含占位符模板，params 为绑定值字典。
        """
        # 基础SELECT语句
        table_name = self.model_class.__tablename__
        query = f"SELECT * FROM {table_name}"
        params: Dict[str, Any] = {}

        # 添加WHERE条件（value 参数化，len(params) 作索引保证占位符 key 唯一）
        if filters:
            where_conditions = []
            for key, value in filters.items():
                if "__" in key:
                    field, operator = key.split("__", 1)
                    if hasattr(self.model_class, field):
                        if operator == "gte":
                            pk = f"flt_{field}_gte_{len(params)}"
                            where_conditions.append(f"{field} >= %({pk})s")
                            params[pk] = value
                        elif operator == "lte":
                            pk = f"flt_{field}_lte_{len(params)}"
                            where_conditions.append(f"{field} <= %({pk})s")
                            params[pk] = value
                        elif operator == "gt":
                            pk = f"flt_{field}_gt_{len(params)}"
                            where_conditions.append(f"{field} > %({pk})s")
                            params[pk] = value
                        elif operator == "lt":
                            pk = f"flt_{field}_lt_{len(params)}"
                            where_conditions.append(f"{field} < %({pk})s")
                            params[pk] = value
                        elif operator == "in":
                            if isinstance(value, (list, tuple)):
                                placeholders = []
                                for v in value:
                                    pk = f"flt_{field}_in_{len(params)}"
                                    placeholders.append(f"%({pk})s")
                                    params[pk] = v
                                where_conditions.append(
                                    f"{field} IN ({', '.join(placeholders)})"
                                )
                        elif operator == "like":
                            pk = f"flt_{field}_like_{len(params)}"
                            where_conditions.append(f"{field} LIKE %({pk})s")
                            # % 放 Python 值侧，SQL 模板不留裸 %（PyMySQL
                            # string-formatting 会把裸 % 误当占位符）
                            params[pk] = f"%{value}%"
                else:
                    if hasattr(self.model_class, key):
                        pk = f"flt_{key}_eq_{len(params)}"
                        where_conditions.append(f"{key} = %({pk})s")
                        params[pk] = value

            if where_conditions:
                query += f" WHERE {' AND '.join(where_conditions)}"

        # 添加ORDER BY（列名白名单保护，非用户 value）
        if order_by and hasattr(self.model_class, order_by):
            query += f" ORDER BY {order_by}"
            if desc_order:
                query += " DESC"

        return query, params

    def _fallback_to_traditional_query(self,
                                     filters: Optional[Dict[str, Any]] = None,
                                     batch_size: Optional[int] = None,
                                     order_by: Optional[str] = None,
                                     desc_order: bool = False) -> Any:
        """降级到传统查询的实现"""
        GLOG.INFO(f"Using traditional query fallback for {self.model_class.__name__}")

        # 使用现有的find方法，分页返回
        batch_size = batch_size or 1000
        page = 0

        while True:
            batch = self.find(
                filters=filters,
                page=page,
                page_size=batch_size,
                order_by=order_by,
                desc_order=desc_order
            )

            if not batch:
                break

            yield batch
            page += 1

            # 避免无限循环
            if len(batch) < batch_size:
                break

    # ==================== 🆕 断点续传流式查询方法 ====================

    def stream_find_resumable(self,
                             filters: Optional[Dict[str, Any]] = None,
                             batch_size: Optional[int] = None,
                             order_by: Optional[str] = "timestamp",
                             desc_order: bool = False,
                             checkpoint_id: Optional[str] = None,
                             auto_checkpoint: bool = True,
                             checkpoint_interval: int = 1000) -> Any:
        """
        🆕 支持断点续传的流式查询

        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            order_by: 排序字段（用于断点续传）
            desc_order: 是否降序
            checkpoint_id: 现有断点ID（用于恢复）
            auto_checkpoint: 是否自动创建断点
            checkpoint_interval: 自动断点间隔

        Yields:
            查询结果批次
        """
        if not self._streaming_enabled:
            GLOG.WARN("Streaming not enabled, falling back to traditional query")
            yield from self._fallback_to_traditional_query(filters, batch_size, order_by, desc_order)
            return

        try:
            # 导入断点管理器（延迟导入避免循环依赖）
            from ginkgo.data.streaming.checkpoint import checkpoint_manager, progress_tracking_manager
            from ginkgo.data.streaming import StreamingState, CheckpointError

            # 恢复或创建断点
            checkpoint = None
            if checkpoint_id:
                checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
                if not checkpoint:
                    raise CheckpointError(f"Checkpoint not found: {checkpoint_id}")
                GLOG.INFO(f"Resuming from checkpoint: {checkpoint_id}")
            elif auto_checkpoint:
                # 创建新断点
                # query_text 带占位符模板；params 不存——执行路径 resumable→stream_find
                # 重建查询，checkpoint.query_text 仅参与 hash + 人类可读（#3859）
                query_text, _params = self._build_streaming_query(filters, order_by, desc_order)
                checkpoint_id = checkpoint_manager.create_checkpoint(
                    query=query_text,
                    filters=filters or {},
                    batch_size=batch_size or 1000,
                    database_type=getattr(self.driver, '_db_type', 'unknown'),
                    engine_type='streaming',
                    estimated_total=self._estimate_total_records(filters)
                )
                checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
                GLOG.INFO(f"Created checkpoint: {checkpoint_id}")

            # 调整过滤条件支持断点续传
            adjusted_filters = self._adjust_filters_for_resume(filters, checkpoint, order_by)

            # 创建进度跟踪器
            tracker_id = None
            if checkpoint:
                from ginkgo.data.streaming.checkpoint import checkpoint_manager
                query_hash = checkpoint_manager._generate_query_hash(
                    checkpoint.query_text,
                    adjusted_filters
                )
                tracker_id = progress_tracking_manager.create_tracker(
                    query_hash=query_hash,
                    estimated_total=checkpoint.estimated_total
                )

            # 执行流式查询
            processed_in_session = 0
            total_processed = checkpoint.processed_count if checkpoint else 0

            try:
                # 更新断点状态为运行中
                if checkpoint:
                    checkpoint_manager.update_checkpoint(
                        checkpoint.checkpoint_id,
                        state=StreamingState.RUNNING
                    )

                for batch in self.stream_find(
                    filters=adjusted_filters,
                    batch_size=batch_size,
                    order_by=order_by,
                    desc_order=desc_order
                ):
                    # 更新处理计数
                    batch_size_actual = len(batch)
                    processed_in_session += batch_size_actual
                    total_processed += batch_size_actual

                    # 更新进度跟踪
                    if tracker_id:
                        progress_tracking_manager.update_progress(
                            tracker_id=tracker_id,
                            processed_count=total_processed,
                            batch_size=batch_size_actual
                        )

                    # 自动保存断点
                    if checkpoint and auto_checkpoint and processed_in_session >= checkpoint_interval:
                        self._save_checkpoint_progress(
                            checkpoint, batch, total_processed, order_by
                        )
                        processed_in_session = 0

                    yield batch

                # 查询完成，更新断点状态
                if checkpoint:
                    checkpoint_manager.update_checkpoint(
                        checkpoint.checkpoint_id,
                        state=StreamingState.COMPLETED,
                        processed_count=total_processed,
                        progress_percentage=100.0
                    )
                    GLOG.INFO(f"Streaming query completed. Checkpoint: {checkpoint.checkpoint_id}")

            except Exception as e:
                # 查询失败，保存当前进度
                if checkpoint:
                    checkpoint_manager.update_checkpoint(
                        checkpoint.checkpoint_id,
                        state=StreamingState.FAILED,
                        processed_count=total_processed
                    )
                    GLOG.ERROR(f"Streaming query failed. Checkpoint saved: {checkpoint.checkpoint_id}")
                raise
            finally:
                # 清理进度跟踪器
                if tracker_id:
                    progress_tracking_manager.remove_tracker(tracker_id)

        except Exception as e:
            GLOG.ERROR(f"Resumable streaming query failed: {e}")
            # 降级到普通流式查询
            GLOG.INFO("Falling back to regular streaming query")
            yield from self.stream_find(filters, batch_size, order_by, desc_order)

    def stream_find_with_detailed_progress(self,
                                         filters: Optional[Dict[str, Any]] = None,
                                         batch_size: Optional[int] = None,
                                         progress_callback: Optional[Callable] = None,
                                         checkpoint_id: Optional[str] = None) -> Any:
        """
        🆕 带详细进度监控的流式查询

        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            progress_callback: 进度回调函数
            checkpoint_id: 断点ID（用于恢复）

        Yields:
            查询结果批次
        """
        # 添加默认进度回调
        def default_progress_callback(progress_info):
            from ginkgo.data.streaming import ProgressInfo
            GLOG.INFO(
                f"Streaming progress: {progress_info.processed} processed, "
                f"rate: {progress_info.rate:.1f} records/sec, "
                f"elapsed: {progress_info.elapsed:.1f}s"
                + (f", progress: {progress_info.progress_percentage:.1f}%"
                   if progress_info.progress_percentage else "")
            )

        actual_callback = progress_callback or default_progress_callback

        # 使用断点续传功能
        for batch in self.stream_find_resumable(
            filters=filters,
            batch_size=batch_size,
            checkpoint_id=checkpoint_id,
            auto_checkpoint=True
        ):
            # 执行进度回调
            if actual_callback:
                try:
                    # 这里需要构造ProgressInfo，实际实现中会从跟踪器获取
                    from ginkgo.data.streaming import ProgressInfo
                    progress_info = ProgressInfo(
                        processed=len(batch),  # 简化实现
                        rate=0.0,
                        elapsed=0.0
                    )
                    actual_callback(progress_info)
                except Exception as e:
                    GLOG.WARN(f"Progress callback failed: {e}")

            yield batch

    def get_checkpoint_status(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        🆕 获取断点状态信息

        Args:
            checkpoint_id: 断点ID

        Returns:
            断点状态信息
        """
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager

            checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
            if not checkpoint:
                return None

            return {
                "checkpoint_id": checkpoint.checkpoint_id,
                "state": checkpoint.state.value,
                "processed_count": checkpoint.processed_count,
                "progress_percentage": checkpoint.progress_percentage,
                "processing_rate": checkpoint.processing_rate,
                "elapsed_time": checkpoint.elapsed_time,
                "created_at": checkpoint.created_at,
                "updated_at": checkpoint.updated_at,
                "database_type": checkpoint.database_type,
                "engine_type": checkpoint.engine_type
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to get checkpoint status: {e}")
            return None

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        🆕 列出所有相关断点

        Returns:
            断点列表
        """
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager

            checkpoints = checkpoint_manager.list_checkpoints()
            return [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "state": cp.state.value,
                    "processed_count": cp.processed_count,
                    "progress_percentage": cp.progress_percentage,
                    "created_at": cp.created_at,
                    "database_type": cp.database_type
                }
                for cp in checkpoints
            ]

        except Exception as e:
            GLOG.ERROR(f"Failed to list checkpoints: {e}")
            return []

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        🆕 删除断点

        Args:
            checkpoint_id: 断点ID

        Returns:
            是否删除成功
        """
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager
            return checkpoint_manager.delete_checkpoint(checkpoint_id)
        except Exception as e:
            GLOG.ERROR(f"Failed to delete checkpoint: {e}")
            return False

    def _adjust_filters_for_resume(self,
                                  filters: Optional[Dict[str, Any]],
                                  checkpoint: Optional[Any],
                                  order_by: str) -> Dict[str, Any]:
        """调整过滤条件以支持断点续传"""
        adjusted_filters = dict(filters) if filters else {}

        if checkpoint and checkpoint.last_timestamp:
            # 使用时间戳断点续传
            timestamp_filter = f"{order_by}__gt"
            adjusted_filters[timestamp_filter] = checkpoint.last_timestamp
            GLOG.DEBUG(f"Resuming from timestamp: {checkpoint.last_timestamp}")
        elif checkpoint and checkpoint.last_offset > 0:
            # 使用偏移量断点续传（不太精确，但总比没有好）
            GLOG.DEBUG(f"Resuming from offset: {checkpoint.last_offset}")

        return adjusted_filters

    def _save_checkpoint_progress(self,
                                checkpoint: Any,
                                batch: List[Any],
                                total_processed: int,
                                order_by: str):
        """保存断点进度"""
        try:
            from ginkgo.data.streaming.checkpoint import checkpoint_manager

            updates = {
                "processed_count": total_processed,
                "last_offset": total_processed
            }

            # 尝试从批次数据中提取时间戳
            if batch and hasattr(batch[0], order_by):
                last_timestamp = getattr(batch[-1], order_by)
                if last_timestamp:
                    updates["last_timestamp"] = str(last_timestamp)

            checkpoint_manager.update_checkpoint(
                checkpoint.checkpoint_id,
                **updates
            )

            GLOG.DEBUG(f"Saved checkpoint progress: {total_processed} records processed")

        except Exception as e:
            GLOG.WARN(f"Failed to save checkpoint progress: {e}")

    def _estimate_total_records(self, filters: Optional[Dict[str, Any]]) -> Optional[int]:
        """估算总记录数（用于进度计算）"""
        try:
            # 简单的估算方法：执行COUNT查询
            # 实际生产环境可以使用更复杂的估算逻辑
            count_result = self.count(filters=filters)
            return count_result if isinstance(count_result, int) else None
        except Exception as e:
            GLOG.DEBUG(f"Failed to estimate total records: {e}")
            return None

    # ==================== 🆕 内存监控和会话管理集成 ====================

    def stream_find_with_monitoring(self,
                                   filters: Optional[Dict[str, Any]] = None,
                                   batch_size: Optional[int] = None,
                                   order_by: Optional[str] = None,
                                   desc_order: bool = False,
                                   memory_limit_mb: Optional[float] = None,
                                   auto_optimize: bool = True) -> Any:
        """
        🆕 带内存监控的流式查询

        Args:
            filters: 查询过滤条件
            batch_size: 批次大小
            order_by: 排序字段
            desc_order: 是否降序
            memory_limit_mb: 内存限制（MB）
            auto_optimize: 是否启用自动优化

        Yields:
            查询结果批次
        """
        if not self._streaming_enabled:
            GLOG.WARN("Streaming not enabled, falling back to traditional query")
            yield from self._fallback_to_traditional_query(filters, batch_size, order_by, desc_order)
            return

        try:
            # 导入监控模块
            from ginkgo.data.streaming.session_context import streaming_session
            from ginkgo.data.streaming.monitoring import memory_monitor

            database_type = getattr(self.driver, '_db_type', 'unknown') if hasattr(self, 'driver') else 'unknown'

            # 使用会话上下文管理器
            with streaming_session(
                database_type=database_type,
                auto_optimize=auto_optimize
            ) as session_context:

                batch_count = 0
                current_batch_size = batch_size or 1000

                # 内存限制检查
                if memory_limit_mb:
                    initial_snapshot = memory_monitor.get_current_snapshot()
                    if initial_snapshot.process_mb > memory_limit_mb:
                        GLOG.WARN(
                            f"Current memory usage ({initial_snapshot.process_mb:.1f}MB) "
                            f"exceeds limit ({memory_limit_mb}MB), reducing batch size"
                        )
                        current_batch_size = max(current_batch_size // 2, 100)

                for batch in self.stream_find(
                    filters=filters,
                    batch_size=current_batch_size,
                    order_by=order_by,
                    desc_order=desc_order
                ):
                    batch_count += 1

                    # 更新会话进度
                    from ginkgo.data.streaming.session_context import streaming_session_manager

                    current_memory = memory_monitor.get_current_snapshot().process_mb
                    streaming_session_manager.update_session_progress(
                        session_context.session_id,
                        len(batch),
                        current_memory
                    )

                    # 内存优化检查
                    if auto_optimize and memory_limit_mb and current_memory > memory_limit_mb:
                        # 动态调整批次大小
                        new_batch_size = max(current_batch_size // 2, 100)
                        if new_batch_size != current_batch_size:
                            GLOG.WARN(
                                f"Memory limit exceeded ({current_memory:.1f}MB > {memory_limit_mb}MB), "
                                f"reducing batch size: {current_batch_size} -> {new_batch_size}"
                            )
                            current_batch_size = new_batch_size

                        # 强制垃圾回收
                        memory_monitor.force_garbage_collection()

                    yield batch

                # 记录最终统计
                final_metrics = streaming_session_manager.get_session_metrics(session_context.session_id)
                if final_metrics:
                    GLOG.INFO(
                        f"Streaming query completed: {final_metrics['records_processed']} records, "
                        f"{final_metrics['processing_rate']:.1f} records/sec, "
                        f"peak memory: {final_metrics['memory_peak_mb']:.1f}MB"
                    )

        except Exception as e:
            GLOG.ERROR(f"Monitored streaming query failed: {e}")
            # 降级到常规流式查询
            yield from self.stream_find(filters, batch_size, order_by, desc_order)

    def get_streaming_session_metrics(self) -> List[Dict[str, Any]]:
        """
        🆕 获取流式查询会话指标

        Returns:
            活跃会话指标列表
        """
        try:
            from ginkgo.data.streaming.session_context import streaming_session_manager
            return streaming_session_manager.list_active_sessions()
        except Exception as e:
            GLOG.ERROR(f"Failed to get streaming session metrics: {e}")
            return []

    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        🆕 获取内存统计信息

        Returns:
            内存统计字典
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager

            memory_stats = memory_monitor.get_memory_statistics()
            session_stats = session_manager.get_session_statistics()

            return {
                "memory": memory_stats,
                "sessions": session_stats,
                "timestamp": time.time()
            }
        except Exception as e:
            GLOG.ERROR(f"Failed to get memory statistics: {e}")
            return {"error": str(e)}

    def optimize_streaming_resources(self) -> Dict[str, Any]:
        """
        🆕 手动优化流式查询资源

        Returns:
            优化结果报告
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager

            optimization_report = {
                "timestamp": time.time(),
                "actions_taken": [],
                "before": {},
                "after": {}
            }

            # 记录优化前状态
            optimization_report["before"] = {
                "memory_percent": memory_monitor.get_current_snapshot().percent,
                "active_sessions": len(session_manager.list_sessions(state=SessionState.ACTIVE)),
                "idle_sessions": len(session_manager.list_sessions(state=SessionState.IDLE))
            }

            # 1. 强制垃圾回收
            gc_result = memory_monitor.force_garbage_collection()
            if gc_result.get("collected", 0) > 0:
                optimization_report["actions_taken"].append(
                    f"Garbage collection: freed {gc_result.get('freed_objects', 0)} objects"
                )

            # 2. 清理过期会话
            from ginkgo.data.streaming.monitoring import SessionState
            idle_sessions = session_manager.list_sessions(state=SessionState.IDLE)
            cleaned_sessions = 0

            for session in idle_sessions:
                if session.idle_seconds > 300:  # 5分钟空闲
                    session_manager.close_session(session.session_id)
                    cleaned_sessions += 1

            if cleaned_sessions > 0:
                optimization_report["actions_taken"].append(
                    f"Cleaned {cleaned_sessions} idle sessions"
                )

            # 记录优化后状态
            optimization_report["after"] = {
                "memory_percent": memory_monitor.get_current_snapshot().percent,
                "active_sessions": len(session_manager.list_sessions(state=SessionState.ACTIVE)),
                "idle_sessions": len(session_manager.list_sessions(state=SessionState.IDLE))
            }

            # 计算优化效果
            memory_improvement = (
                optimization_report["before"]["memory_percent"] -
                optimization_report["after"]["memory_percent"]
            )
            optimization_report["memory_improvement_percent"] = memory_improvement

            GLOG.INFO(f"Resource optimization completed: {optimization_report}")
            return optimization_report

        except Exception as e:
            GLOG.ERROR(f"Failed to optimize streaming resources: {e}")
            return {"error": str(e)}

    def enable_memory_monitoring(self) -> bool:
        """
        🆕 启用内存监控

        Returns:
            是否成功启用
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager

            if not memory_monitor._monitoring:
                memory_monitor.start_monitoring()
                GLOG.INFO("Memory monitoring started")

            if not session_manager._cleanup_enabled:
                session_manager.start_cleanup()
                GLOG.INFO("Session cleanup started")

            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to enable memory monitoring: {e}")
            return False

    def disable_memory_monitoring(self) -> bool:
        """
        🆕 禁用内存监控

        Returns:
            是否成功禁用
        """
        try:
            from ginkgo.data.streaming.monitoring import memory_monitor, session_manager

            memory_monitor.stop_monitoring()
            session_manager.stop_cleanup()

            GLOG.INFO("Memory monitoring and session cleanup stopped")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to disable memory monitoring: {e}")
            return False
