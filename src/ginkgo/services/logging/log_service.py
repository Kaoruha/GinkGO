# Upstream: ServiceHub (通过 services.logging.log_service 访问)
# Downstream: ClickHouse (ginkgo_logs_backtest/组件/性能表), MBacktestLog/MComponentLog/MPerformanceLog
# Role: LogService 日志查询服务 - 封装 ClickHouse 查询 API，提供业务日志查询功能

from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy import and_, or_, select, func, text
from sqlalchemy.orm import Session

from ginkgo.data.drivers import get_db_connection
from ginkgo.data.models.model_logs import MBacktestLog, MComponentLog, MPerformanceLog
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG, time_logger, cache_with_expiration
from ginkgo.enums import LEVEL_TYPES


class LogService(BaseService):
    """
    日志查询服务 - 封装 ClickHouse 查询

    提供业务日志查询功能，支持按组合、策略、链路追踪 ID、日志级别等条件过滤。

    Attributes:
        engine: ClickHouse 数据库引擎
    """

    def __init__(self, engine=None):
        """
        初始化 LogService

        Args:
            engine: ClickHouse 引擎实例（可选，默认使用 get_db_connection）
        """
        # 使用依赖注入模式初始化 BaseService
        super().__init__(engine=engine)

        # 存储 ClickHouse 引擎
        if engine is None:
            self._engine = get_db_connection(MBacktestLog)
        else:
            self._engine = engine

    @time_logger
    def query_backtest_logs(
        self,
        portfolio_id: Optional[str] = None,
        task_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        event_type: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询回测日志（支持多条件过滤）

        Args:
            portfolio_id: 组合 ID 过滤
            task_id: 运行会话 ID 过滤
            strategy_id: 策略 ID 过滤
            level: 日志级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            start_time: 开始时间
            end_time: 结束时间
            trace_id: 链路追踪 ID 过滤
            event_type: 事件类型过滤
            symbol: 交易标的过滤
            limit: 最大返回结果数
            offset: 偏移量（用于分页）

        Returns:
            List[Dict]: 日志条目列表（字典格式）
        """
        self._log_operation_start(
            "query_backtest_logs",
            portfolio_id=portfolio_id,
            task_id=task_id,
            strategy_id=strategy_id,
            level=level,
            limit=limit
        )

        try:
            with self._engine.get_session() as session:
                # 构建查询
                query = select(MBacktestLog)

                # 应用过滤条件
                conditions = []
                if portfolio_id:
                    conditions.append(MBacktestLog.portfolio_id == portfolio_id)
                if task_id:
                    conditions.append(MBacktestLog.task_id == task_id)
                if strategy_id:
                    conditions.append(MBacktestLog.strategy_id == strategy_id)
                if level:
                    conditions.append(MBacktestLog.level == level.upper())
                if trace_id:
                    conditions.append(MBacktestLog.trace_id == trace_id)
                if event_type:
                    conditions.append(MBacktestLog.event_type == event_type)
                if symbol:
                    conditions.append(MBacktestLog.symbol == symbol)
                if start_time:
                    conditions.append(MBacktestLog.timestamp >= start_time)
                if end_time:
                    conditions.append(MBacktestLog.timestamp <= end_time)

                if conditions:
                    query = query.where(and_(*conditions))

                # 排序：按时间戳倒序
                query = query.order_by(MBacktestLog.timestamp.desc())

                # 分页
                query = query.limit(limit).offset(offset)

                # 执行查询
                result = session.execute(query)
                logs = result.scalars().all()

                # 转换为字典列表
                log_dicts = [self._model_to_dict(log) for log in logs]

                self._log_operation_end("query_backtest_logs", success=True)
                return log_dicts

        except Exception as e:
            self._logger.ERROR(f"查询回测日志失败: {e}")
            self._log_operation_end("query_backtest_logs", success=False)
            return []

    @time_logger
    def query_component_logs(
        self,
        component_name: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询组件日志

        Args:
            component_name: 组件名称过滤
            level: 日志级别过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回结果数
            offset: 偏移量

        Returns:
            List[Dict]: 日志条目列表
        """
        try:
            with self._engine.get_session() as session:
                query = select(MComponentLog)

                conditions = []
                if component_name:
                    conditions.append(MComponentLog.component_name == component_name)
                if level:
                    conditions.append(MComponentLog.level == level.upper())
                if start_time:
                    conditions.append(MComponentLog.timestamp >= start_time)
                if end_time:
                    conditions.append(MComponentLog.timestamp <= end_time)

                if conditions:
                    query = query.where(and_(*conditions))

                query = query.order_by(MComponentLog.timestamp.desc())
                query = query.limit(limit).offset(offset)

                result = session.execute(query)
                logs = result.scalars().all()

                return [self._model_to_dict(log) for log in logs]

        except Exception as e:
            self._logger.ERROR(f"查询组件日志失败: {e}")
            return []

    @time_logger
    def query_performance_logs(
        self,
        function_name: Optional[str] = None,
        module_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_duration_ms: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询性能日志

        Args:
            function_name: 函数名过滤
            module_name: 模块名过滤
            start_time: 开始时间
            end_time: 结束时间
            min_duration_ms: 最小执行时间（毫秒）
            limit: 最大返回结果数
            offset: 偏移量

        Returns:
            List[Dict]: 日志条目列表
        """
        try:
            with self._engine.get_session() as session:
                query = select(MPerformanceLog)

                conditions = []
                if function_name:
                    conditions.append(MPerformanceLog.function_name == function_name)
                if module_name:
                    conditions.append(MPerformanceLog.module_name == module_name)
                if start_time:
                    conditions.append(MPerformanceLog.timestamp >= start_time)
                if end_time:
                    conditions.append(MPerformanceLog.timestamp <= end_time)
                if min_duration_ms is not None:
                    conditions.append(MPerformanceLog.duration_ms >= min_duration_ms)

                if conditions:
                    query = query.where(and_(*conditions))

                query = query.order_by(MPerformanceLog.timestamp.desc())
                query = query.limit(limit).offset(offset)

                result = session.execute(query)
                logs = result.scalars().all()

                return [self._model_to_dict(log) for log in logs]

        except Exception as e:
            self._logger.ERROR(f"查询性能日志失败: {e}")
            return []

    @time_logger
    def query_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        按追踪 ID 查询完整链路日志（跨三张表）

        Args:
            trace_id: 链路追踪 ID

        Returns:
            List[Dict]: 该链路的所有日志条目（按时间排序）
        """
        all_logs = []

        try:
            with self._engine.get_session() as session:
                # 查询回测日志
                backtest_result = session.execute(
                    select(MBacktestLog)
                    .where(MBacktestLog.trace_id == trace_id)
                )
                all_logs.extend([self._model_to_dict(log) for log in backtest_result.scalars()])

                # 查询组件日志
                component_result = session.execute(
                    select(MComponentLog)
                    .where(MComponentLog.trace_id == trace_id)
                )
                all_logs.extend([self._model_to_dict(log) for log in component_result.scalars()])

                # 查询性能日志
                perf_result = session.execute(
                    select(MPerformanceLog)
                    .where(MPerformanceLog.trace_id == trace_id)
                )
                all_logs.extend([self._model_to_dict(log) for log in perf_result.scalars()])

            # 按时间戳排序
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return all_logs

        except Exception as e:
            self._logger.ERROR(f"按 trace_id 查询日志失败: {e}")
            return []

    @time_logger
    @cache_with_expiration(expiration_seconds=60)  # T115: 缓存60秒
    def get_log_count(
        self,
        log_type: str = "backtest",
        **filters
    ) -> int:
        """
        获取日志数量统计

        Args:
            log_type: 日志类型 ("backtest", "component", "performance")
            **filters: 过滤条件

        Returns:
            int: 日志数量
        """
        try:
            with self._engine.get_session() as session:
                if log_type == "backtest":
                    model = MBacktestLog
                elif log_type == "component":
                    model = MComponentLog
                elif log_type == "performance":
                    model = MPerformanceLog
                else:
                    return 0

                query = select(func.count()).select_from(model)

                # 应用过滤条件
                conditions = []
                for key, value in filters.items():
                    if value is not None and hasattr(model, key):
                        conditions.append(getattr(model, key) == value)

                if conditions:
                    query = query.where(and_(*conditions))

                result = session.execute(query)
                return result.scalar() or 0

        except Exception as e:
            self._logger.ERROR(f"统计日志数量失败: {e}")
            return 0

    @time_logger
    def search_logs(
        self,
        keyword: str,
        log_type: str = "backtest",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        关键词全文搜索

        Args:
            keyword: 搜索关键词
            log_type: 日志类型
            limit: 最大返回结果数
            offset: 偏移量

        Returns:
            List[Dict]: 匹配的日志条目列表
        """
        try:
            with self._engine.get_session() as session:
                if log_type == "backtest":
                    model = MBacktestLog
                elif log_type == "component":
                    model = MComponentLog
                elif log_type == "performance":
                    model = MPerformanceLog
                else:
                    return []

                # ClickHouse 使用 LIKE 进行全文搜索
                query = select(model).where(
                    or_(
                        model.message.like(f"%{keyword}%"),
                        model.logger_name.like(f"%{keyword}%")
                    )
                )

                query = query.order_by(model.timestamp.desc())
                query = query.limit(limit).offset(offset)

                result = session.execute(query)
                logs = result.scalars().all()

                return [self._model_to_dict(log) for log in logs]

        except Exception as e:
            self._logger.ERROR(f"关键词搜索失败: {e}")
            return []

    def _model_to_dict(self, model: Any) -> Dict[str, Any]:
        """
        将 SQLAlchemy 模型转换为字典

        Args:
            model: SQLAlchemy 模型实例

        Returns:
            Dict: 模型数据的字典表示
        """
        if hasattr(model, '__table__'):
            # SQLAlchemy 模型
            result = {}
            for column in model.__table__.columns:
                value = getattr(model, column.name)
                # 转换 datetime 对象为字符串
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value
            return result
        else:
            # 其他类型，尝试使用 __dict__
            return model.__dict__

    @time_logger
    @cache_with_expiration(expiration_seconds=30)  # T115: 错误统计缓存30秒
    def get_error_stats(
        self,
        portfolio_id: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取错误统计信息

        Args:
            portfolio_id: 组合 ID（可选）
            hours: 统计时间范围（小时）

        Returns:
            Dict: 错误统计信息
        """
        try:
            from datetime import timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            with self._engine.get_session() as session:
                # 查询 ERROR 和 CRITICAL 级别的日志
                conditions = [
                    MBacktestLog.timestamp >= start_time,
                    MBacktestLog.level.in_(['ERROR', 'CRITICAL'])
                ]

                if portfolio_id:
                    conditions.append(MBacktestLog.portfolio_id == portfolio_id)

                query = select(MBacktestLog).where(and_(*conditions))
                result = session.execute(query)
                error_logs = result.scalars().all()

                # 统计错误模式
                error_patterns = {}
                for log in error_logs:
                    # 使用消息的前100个字符作为模式
                    pattern = log.message[:100] if log.message else ""
                    if pattern not in error_patterns:
                        error_patterns[pattern] = 0
                    error_patterns[pattern] += 1

                # 排序获取最常见的错误
                top_errors = sorted(
                    error_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]

                return {
                    "total_errors": len(error_logs),
                    "time_range_hours": hours,
                    "top_error_patterns": [
                        {"pattern": pattern, "count": count}
                        for pattern, count in top_errors
                    ]
                }

        except Exception as e:
            self._logger.ERROR(f"获取错误统计失败: {e}")
            return {
                "total_errors": 0,
                "time_range_hours": hours,
                "top_error_patterns": []
            }

    @time_logger
    def join_with_backtest_results(
        self,
        portfolio_id: str,
        backtest_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        关联回测日志与回测结果（T067）

        将日志记录与回测结果表进行 JOIN 操作，提供完整的回测执行视图。

        Args:
            portfolio_id: 组合 ID
            backtest_id: 回测任务 ID（可选）
            limit: 最大返回结果数

        Returns:
            List[Dict]: 关联后的日志和结果数据
        """
        try:
            # 导入回测结果 Model
            from ginkgo.data.models.model_backtest import MBacktest

            with self._engine.get_session() as session:
                # 构建查询：回测日志 + 回测任务信息
                # 注意：ClickHouse 不支持传统 JOIN，使用子查询方式

                # 1. 先获取回测任务信息
                backtest_filters = [MBacktest.portfolio_id == portfolio_id]
                if backtest_id:
                    backtest_filters.append(MBacktest.uuid == backtest_id)

                backtest_query = select(MBacktest).where(and_(*backtest_filters))
                backtest_result = session.execute(backtest_query)
                backtests = backtest_result.scalars().all()

                if not backtests:
                    return []

                # 2. 获取相关日志并关联
                result = []
                for backtest in backtests:
                    # 查询该回测任务相关的日志
                    logs = self.query_backtest_logs(
                        portfolio_id=portfolio_id,
                        strategy_id=backtest.strategy_id if hasattr(backtest, 'strategy_id') else None,
                        limit=limit
                    )

                    # 组合数据
                    for log in logs:
                        result.append({
                            **log,
                            "backtest_info": {
                                "backtest_id": backtest.uuid,
                                "backtest_name": backtest.name if hasattr(backtest, 'name') else None,
                                "strategy_id": backtest.strategy_id if hasattr(backtest, 'strategy_id') else None,
                                "status": backtest.status if hasattr(backtest, 'status') else None,
                                "start_time": backtest.timestamp.isoformat() if backtest.timestamp else None,
                            }
                        })

                return result

        except ImportError:
            # MBacktest 模型不存在时，返回仅日志数据
            self._logger.WARNING("MBacktest 模型不可用，返回仅日志数据")
            return self.query_backtest_logs(portfolio_id=portfolio_id, limit=limit)

        except Exception as e:
            self._logger.ERROR(f"关联回测结果失败: {e}")
            return []
