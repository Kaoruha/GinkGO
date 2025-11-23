from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.data.crud.signal_tracker_crud import SignalTrackerCRUD
from ginkgo.data.models.model_signal_tracker import MSignalTracker
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import EXECUTION_MODE, TRACKING_STATUS, ACCOUNT_TYPE
from ginkgo.libs import GLOG, time_logger
from ginkgo.data.services.base_service import ServiceResult, BusinessService


class SignalTrackingService(BusinessService):
    """
    信号追踪服务层
    
    提供信号执行追踪的完整业务逻辑，包括创建追踪记录、确认执行、
    统计分析等功能，遵循DI设计原则
    """

    def __init__(self, tracker_crud: SignalTrackerCRUD):
        """
        初始化信号追踪服务
        
        Args:
            tracker_crud: 信号追踪数据访问对象
        """
        # 调用父类构造函数，遵循BusinessService模式
        super().__init__(tracker_crud=tracker_crud)
        self.tracker_crud = tracker_crud

    @time_logger
    def create_tracking(
        self,
        signal: Signal,
        execution_mode: EXECUTION_MODE,
        account_type: ACCOUNT_TYPE,
        engine_id: Optional[str] = None
    ) -> ServiceResult:
        """
        为信号创建追踪记录
        
        Args:
            signal: 交易信号
            execution_mode: 执行模式
            account_type: 账户类型
            engine_id: 引擎ID
            
        Returns:
            ServiceResult[MSignalTracker]: 服务结果
        """
        try:
            tracking_data = {
                "signal_id": signal.uuid,
                "strategy_id": getattr(signal, 'strategy_id', ''),
                "portfolio_id": signal.portfolio_id,
                "engine_id": engine_id or "",
                "execution_mode": execution_mode,
                "account_type": account_type,
                "expected_code": signal.code,
                "expected_direction": signal.direction,
                "expected_price": float(getattr(signal, 'price', 0)),
                "expected_volume": getattr(signal, 'volume', 0),
                "expected_timestamp": signal.timestamp,
                "tracking_status": TRACKING_STATUS.NOTIFIED,
                "notification_sent_at": datetime.now(),
            }
            
            tracker = self.tracker_crud.add(tracking_data)
            
            GLOG.INFO(f"Created signal tracking for signal_id: {signal.uuid}")
            return ServiceResult.success(tracker)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to create signal tracking: {e}")
            return ServiceResult.failure(f"创建信号追踪失败: {e}")

    @time_logger
    def confirm_execution(
        self,
        signal_id: str,
        actual_price: float,
        actual_volume: int,
        execution_timestamp: Optional[datetime] = None
    ) -> ServiceResult:
        """
        确认信号执行
        
        Args:
            signal_id: 信号ID
            actual_price: 实际价格
            actual_volume: 实际数量
            execution_timestamp: 执行时间
            
        Returns:
            ServiceResult[MSignalTracker]: 服务结果
        """
        try:
            tracker = self.tracker_crud.find_by_signal_id(signal_id)
            if not tracker:
                return ServiceResult.failure(f"信号追踪记录不存在: {signal_id}")
            
            if tracker.is_executed():
                return ServiceResult.failure(f"信号已经确认执行: {signal_id}")
            
            execution_time = execution_timestamp or datetime.now()
            
            # 计算偏差指标
            price_deviation = None
            volume_deviation = None
            time_delay_seconds = None
            
            if tracker.expected_price and tracker.expected_volume:
                price_deviation = (actual_price - float(tracker.expected_price)) / float(tracker.expected_price)
                volume_deviation = (actual_volume - tracker.expected_volume) / tracker.expected_volume
                time_delay_seconds = (execution_time - tracker.expected_timestamp).total_seconds()
            
            # 更新追踪记录
            update_data = {
                "actual_price": actual_price,
                "actual_volume": actual_volume,
                "actual_timestamp": execution_time,
                "tracking_status": TRACKING_STATUS.EXECUTED,
                "execution_confirmed_at": datetime.now(),
                "price_deviation": price_deviation,
                "volume_deviation": volume_deviation,
                "time_delay_seconds": time_delay_seconds
            }
            
            result = self.tracker_crud.update(filters={"uuid": tracker.uuid}, **update_data)
            
            if result.is_success():
                updated_tracker = self.tracker_crud.get_by_uuid(tracker.uuid)
                GLOG.INFO(f"Confirmed execution for signal_id: {signal_id}")
                return ServiceResult.success(updated_tracker)
            else:
                return ServiceResult.failure("更新追踪记录失败")
                
        except Exception as e:
            GLOG.ERROR(f"Failed to confirm execution: {e}")
            return ServiceResult.failure(f"确认执行失败: {e}")

    def mark_timeout(
        self,
        signal_id: str,
        reason: str = "Execution timeout"
    ) -> ServiceResult:
        """
        标记信号为超时状态
        
        Args:
            signal_id: 信号ID
            reason: 超时原因
            
        Returns:
            ServiceResult[bool]: 服务结果
        """
        try:
            result = self.tracker_crud.update(
                filters={"signal_id": signal_id},
                tracking_status=TRACKING_STATUS.TIMEOUT,
                reject_reason=reason
            )
            
            if result.is_success():
                GLOG.INFO(f"Marked signal as timeout: {signal_id}")
                return ServiceResult.success(True)
            else:
                return ServiceResult.failure("标记超时失败")
                
        except Exception as e:
            GLOG.ERROR(f"Failed to mark timeout: {e}")
            return ServiceResult.failure(f"标记超时失败: {e}")

    def get_pending_signals(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        timeout_minutes: int = 30
    ) -> ServiceResult:
        """
        获取待确认的信号
        
        Args:
            engine_id: 引擎ID筛选
            portfolio_id: 投资组合ID筛选
            strategy_id: 策略ID筛选
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            ServiceResult[List[MSignalTracker]]: 服务结果
        """
        try:
            timeout_threshold = datetime.now() - timedelta(minutes=timeout_minutes)
            
            filters = {
                "tracking_status": TRACKING_STATUS.NOTIFIED,
                "notification_sent_at__gte": timeout_threshold
            }
            
            if engine_id:
                filters["engine_id"] = engine_id
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id
            if strategy_id:
                filters["strategy_id"] = strategy_id
            
            pending_signals = self.tracker_crud.get_items_filtered(**filters)
            
            return ServiceResult.success(pending_signals)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get pending signals: {e}")
            return ServiceResult.failure(f"获取待确认信号失败: {e}")

    def get_timeout_signals(
        self,
        engine_id: Optional[str] = None,
        timeout_minutes: int = 30
    ) -> ServiceResult:
        """
        获取超时的信号
        
        Args:
            engine_id: 引擎ID筛选
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            ServiceResult[List[MSignalTracker]]: 服务结果
        """
        try:
            timeout_threshold = datetime.now() - timedelta(minutes=timeout_minutes)
            
            filters = {
                "tracking_status": TRACKING_STATUS.NOTIFIED,
                "notification_sent_at__lt": timeout_threshold
            }
            
            if engine_id:
                filters["engine_id"] = engine_id
            
            timeout_signals = self.tracker_crud.get_items_filtered(**filters)
            
            return ServiceResult.success(timeout_signals)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get timeout signals: {e}")
            return ServiceResult.failure(f"获取超时信号失败: {e}")
    
    def get_by_signal_id(self, signal_id: str) -> ServiceResult:
        """
        根据完整信号ID获取追踪记录
        
        Args:
            signal_id: 完整信号ID
            
        Returns:
            ServiceResult[MSignalTracker]: 服务结果
        """
        try:
            tracking_records = self.tracker_crud.get_items_filtered(signal_id=signal_id)
            
            if not tracking_records:
                return ServiceResult.failure(f"未找到信号: {signal_id}")
            
            if len(tracking_records) > 1:
                GLOG.WARN(f"Found multiple tracking records for signal_id: {signal_id}")
            
            return ServiceResult.success(tracking_records[0])
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get tracking by signal_id: {e}")
            return ServiceResult.failure(f"获取信号追踪记录失败: {e}")
    
    def find_by_signal_id_prefix(self, signal_id_prefix: str) -> ServiceResult:
        """
        根据信号ID前缀查找追踪记录（支持短ID）
        
        Args:
            signal_id_prefix: 信号ID前缀（通常是前8位）
            
        Returns:
            ServiceResult[MSignalTracker]: 服务结果
        """
        try:
            # 使用SQL LIKE查询匹配前缀
            tracking_records = self.tracker_crud.get_items_filtered(
                signal_id__startswith=signal_id_prefix
            )
            
            if not tracking_records:
                return ServiceResult.failure(f"未找到信号: {signal_id_prefix}*")
            
            if len(tracking_records) > 1:
                # 如果有多个匹配，返回最近创建的
                tracking_records.sort(key=lambda x: x.created_at, reverse=True)
                GLOG.WARN(f"Found multiple tracking records for prefix: {signal_id_prefix}, using latest")
            
            return ServiceResult.success(tracking_records[0])
            
        except Exception as e:
            GLOG.ERROR(f"Failed to find tracking by signal_id prefix: {e}")
            return ServiceResult.failure(f"查找信号追踪记录失败: {e}")
    
    def update_tracking_status(
        self,
        tracking_uuid: str,
        new_status: TRACKING_STATUS,
        notes: Optional[str] = None
    ) -> ServiceResult:
        """
        更新追踪记录状态
        
        Args:
            tracking_uuid: 追踪记录UUID
            new_status: 新状态
            notes: 备注信息
            
        Returns:
            ServiceResult[MSignalTracker]: 服务结果
        """
        try:
            # 获取现有记录
            tracking_record = self.tracker_crud.get_by_uuid(tracking_uuid)
            if not tracking_record:
                return ServiceResult.failure(f"未找到追踪记录: {tracking_uuid}")
            
            # 更新状态
            update_data = {
                "tracking_status": new_status,
                "updated_at": datetime.now()
            }
            
            if notes:
                update_data["notes"] = notes
            
            # 根据状态设置相应的时间戳
            if new_status == TRACKING_STATUS.EXECUTED:
                update_data["executed_at"] = datetime.now()
            elif new_status == TRACKING_STATUS.REJECTED:
                update_data["rejected_at"] = datetime.now()
            elif new_status == TRACKING_STATUS.TIMEOUT:
                update_data["timeout_at"] = datetime.now()
            elif new_status == TRACKING_STATUS.CANCELED:
                update_data["canceled_at"] = datetime.now()
            
            # 执行更新
            updated_record = self.tracker_crud.update(tracking_uuid, **update_data)
            
            GLOG.INFO(f"Updated tracking status for {tracking_uuid}: {new_status}")
            return ServiceResult.success(updated_record)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to update tracking status: {e}")
            return ServiceResult.failure(f"更新追踪状态失败: {e}")

    def batch_mark_timeout(
        self,
        engine_id: Optional[str] = None,
        timeout_minutes: int = 30
    ) -> ServiceResult:
        """
        批量标记超时信号
        
        Args:
            engine_id: 引擎ID筛选
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            ServiceResult[int]: 标记为超时的信号数量
        """
        try:
            timeout_signals_result = self.get_timeout_signals(engine_id, timeout_minutes)
            
            if not timeout_signals_result.is_success():
                return ServiceResult.failure("获取超时信号失败")
            
            timeout_signals = timeout_signals_result.data
            count = 0
            
            for signal in timeout_signals:
                result = self.mark_timeout(signal.signal_id, "Batch timeout")
                if result.is_success():
                    count += 1
            
            GLOG.INFO(f"Batch marked {count} timeout signals")
            return ServiceResult.success(count)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to batch mark timeout: {e}")
            return ServiceResult.failure(f"批量标记超时失败: {e}")

    def get_execution_statistics(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        account_type: Optional[ACCOUNT_TYPE] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ServiceResult:
        """
        获取执行统计信息
        
        Args:
            engine_id: 引擎ID筛选
            portfolio_id: 投资组合ID筛选
            strategy_id: 策略ID筛选
            account_type: 账户类型筛选
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            ServiceResult[Dict[str, Any]]: 统计信息
        """
        try:
            filters = {}
            
            if engine_id:
                filters["engine_id"] = engine_id
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id
            if strategy_id:
                filters["strategy_id"] = strategy_id
            if account_type is not None:
                filters["account_type"] = account_type
            if start_date:
                filters["expected_timestamp__gte"] = start_date
            if end_date:
                filters["expected_timestamp__lte"] = end_date
            
            records = self.tracker_crud.get_items_filtered(**filters)
            
            total_count = len(records)
            executed_count = len([r for r in records if r.is_executed()])
            pending_count = len([r for r in records if r.is_pending()])
            timeout_count = len([r for r in records if r.is_timeout()])
            
            # 计算平均偏差
            executed_records = [r for r in records if r.is_executed()]
            avg_price_deviation = 0
            avg_time_delay = 0
            
            if executed_records:
                price_deviations = [float(r.price_deviation) for r in executed_records if r.price_deviation]
                time_delays = [r.time_delay_seconds for r in executed_records if r.time_delay_seconds]
                
                if price_deviations:
                    avg_price_deviation = sum(price_deviations) / len(price_deviations)
                if time_delays:
                    avg_time_delay = sum(time_delays) / len(time_delays)
            
            statistics = {
                "total_signals": total_count,
                "executed_signals": executed_count,
                "pending_signals": pending_count,
                "timeout_signals": timeout_count,
                "execution_rate": executed_count / total_count if total_count > 0 else 0,
                "timeout_rate": timeout_count / total_count if total_count > 0 else 0,
                "avg_price_deviation": avg_price_deviation,
                "avg_time_delay_seconds": avg_time_delay
            }
            
            return ServiceResult.success(statistics)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get execution statistics: {e}")
            return ServiceResult.failure(f"获取执行统计失败: {e}")

    def get_strategy_performance_by_engine(
        self,
        engine_id: str,
        account_type: Optional[ACCOUNT_TYPE] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ServiceResult:
        """
        获取指定引擎下各策略的执行表现
        
        Args:
            engine_id: 引擎ID
            account_type: 账户类型筛选
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            ServiceResult[Dict[str, Dict[str, Any]]]: 按策略分组的性能统计
        """
        try:
            filters = {"engine_id": engine_id}
            
            if account_type is not None:
                filters["account_type"] = account_type
            if start_date:
                filters["expected_timestamp__gte"] = start_date
            if end_date:
                filters["expected_timestamp__lte"] = end_date
            
            records = self.tracker_crud.get_items_filtered(**filters)
            
            # 按策略分组统计
            strategy_stats = {}
            
            for record in records:
                strategy_id = record.strategy_id
                if strategy_id not in strategy_stats:
                    strategy_stats[strategy_id] = {
                        "total": 0,
                        "executed": 0,
                        "pending": 0,
                        "timeout": 0,
                        "price_deviations": [],
                        "time_delays": []
                    }
                
                stats = strategy_stats[strategy_id]
                stats["total"] += 1
                
                if record.is_executed():
                    stats["executed"] += 1
                    if record.price_deviation:
                        stats["price_deviations"].append(float(record.price_deviation))
                    if record.time_delay_seconds:
                        stats["time_delays"].append(record.time_delay_seconds)
                elif record.is_pending():
                    stats["pending"] += 1
                elif record.is_timeout():
                    stats["timeout"] += 1
            
            # 计算汇总指标
            for strategy_id, stats in strategy_stats.items():
                stats["execution_rate"] = stats["executed"] / stats["total"] if stats["total"] > 0 else 0
                stats["timeout_rate"] = stats["timeout"] / stats["total"] if stats["total"] > 0 else 0
                
                if stats["price_deviations"]:
                    stats["avg_price_deviation"] = sum(stats["price_deviations"]) / len(stats["price_deviations"])
                else:
                    stats["avg_price_deviation"] = 0
                
                if stats["time_delays"]:
                    stats["avg_time_delay"] = sum(stats["time_delays"]) / len(stats["time_delays"])
                else:
                    stats["avg_time_delay"] = 0
                
                # 删除原始列表，只保留汇总数据
                del stats["price_deviations"]
                del stats["time_delays"]
            
            return ServiceResult.success(strategy_stats)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get strategy performance: {e}")
            return ServiceResult.failure(f"获取策略性能失败: {e}")

    def cleanup_old_records(self, days_to_keep: int = 30) -> ServiceResult:
        """
        清理旧的追踪记录
        
        Args:
            days_to_keep: 保留天数
            
        Returns:
            ServiceResult[int]: 删除的记录数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = self.tracker_crud.delete_by_date_range(end_date=cutoff_date)
            
            GLOG.INFO(f"Cleaned up {deleted_count} old signal tracking records")
            return ServiceResult.success(deleted_count)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to cleanup old records: {e}")
            return ServiceResult.failure(f"清理旧记录失败: {e}")