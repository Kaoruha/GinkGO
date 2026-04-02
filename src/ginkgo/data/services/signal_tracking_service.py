# Upstream: Strategy Signal Tracking (信号执行追踪)、EventExecutionConfirmed (执行确认事件)
# Downstream: BaseService (继承提供服务基础能力)、SignalTrackerCRUD (信号追踪CRUD操作)、MSignalTracker (信号追踪模型)、EXECUTION_MODE/TRACKINGSTATUS_TYPES/ACCOUNT_TYPE (执行模式/追踪状态/账户类型枚举)
# Role: SignalTrackingService信号追踪服务提供信号执行追踪和统计功能支持交易系统功能和组件集成提供完整业务支持






from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.data.crud.signal_tracker_crud import SignalTrackerCRUD
from ginkgo.data.models.model_signal_tracker import MSignalTracker
from ginkgo.entities import Signal
from ginkgo.enums import EXECUTION_MODE, TRACKINGSTATUS_TYPES, ACCOUNT_TYPE
from ginkgo.libs import GLOG, retry, to_decimal, datetime_normalize
from ginkgo.data.services.base_service import ServiceResult, BaseService


class SignalTrackingService(BaseService):
    """
    Signal Tracking Service Layer

    Provides complete business logic for signal execution tracking, including creating tracking records,
    confirming execution, statistical analysis, etc., following flat architecture design
    """

    def __init__(self, tracker_crud: SignalTrackerCRUD):
        """
        Initialize signal tracking service

        Args:
            tracker_crud: Signal tracking data access object
        """
        # Call parent constructor, following flat architecture pattern
        super().__init__(crud_repo=tracker_crud)
        self._crud_repo = tracker_crud

    @retry(max_try=3)
    def create(
        self,
        signal: Signal,
        execution_mode: EXECUTION_MODE,
        account_type: ACCOUNT_TYPE,
        engine_id: Optional[str] = None
    ) -> ServiceResult:
        """
        Create tracking record for signal

        Args:
            signal: Trading signal
            execution_mode: Execution mode
            account_type: Account type
            engine_id: Engine ID

        Returns:
            ServiceResult[MSignalTracker]: Service result
        """
        try:
            # Get signal business time (key field)
            signal_business_time = signal.business_timestamp or signal.timestamp

            # Create MSignalTracker object directly
            from ginkgo.data.models.model_signal_tracker import MSignalTracker

            tracker = MSignalTracker(
                signal_id=signal.uuid,
                strategy_id=getattr(signal, 'strategy_id', ''),
                portfolio_id=signal.portfolio_id,
                engine_id=engine_id or "",
                execution_mode=execution_mode,
                account_type=account_type,
                expected_code=signal.code,
                expected_direction=signal.direction,
                expected_price=float(getattr(signal, 'price', 0)),
                expected_volume=getattr(signal, 'volume', 0),

                # Time fields - simplified approach
                timestamp=datetime.now(),                    # System creation time
                business_timestamp=signal_business_time,     # Signal business time
                expected_timestamp=signal_business_time,     # Expected execution time (simplified)
                notification_sent_at=datetime.now(),         # Notification sent time
                tracking_status=TRACKINGSTATUS_TYPES.NOTIFIED,
                time_delay_seconds=None,                     # Calculated when execution is confirmed
            )

            tracker = self._crud_repo.add(tracker)

            if tracker is None:
                return ServiceResult.error("Failed to create signal tracking: database insertion returned None")

            GLOG.INFO(f"Created signal tracking for signal_id: {signal.uuid}")
            return ServiceResult.success(tracker)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to create signal tracking: {e}")
            return ServiceResult.error(f"Failed to create signal tracking: {e}")

    @retry(max_try=3)
    def set_confirmed(
        self,
        signal_id: str,
        actual_price: float,
        actual_volume: int,
        execution_timestamp: Optional[datetime] = None
    ) -> ServiceResult:
        """
        Confirm signal execution

        Args:
            signal_id: Signal ID
            actual_price: Actual price
            actual_volume: Actual volume
            execution_timestamp: Execution time

        Returns:
            ServiceResult[MSignalTracker]: Service result
        """
        try:
            tracker = self._crud_repo.find_by_signal_id(signal_id)
            if not tracker:
                return ServiceResult.error(f"Signal tracking record not found: {signal_id}")
            
            if tracker.is_executed():
                return ServiceResult.error(f"Signal already confirmed execution: {signal_id}")
            
            # 🎯 Actual execution time: prefer passed business time, otherwise use signal business time
            actual_execution_time = execution_timestamp or tracker.business_timestamp

            # 🎯 Calculate execution delay (based on business time)
            time_delay_seconds = None
            if tracker.expected_timestamp and actual_execution_time:
                time_delay_seconds = (actual_execution_time - tracker.expected_timestamp).total_seconds()

            # Update tracking record
            update_data = {
                "actual_price": actual_price,
                "actual_volume": actual_volume,
                "actual_timestamp": actual_execution_time,          # Actual execution time (business time)
                "tracking_status": TRACKINGSTATUS_TYPES.EXECUTED,
                "execution_confirmed_at": datetime.now(),           # Execution confirmation system time
                "time_delay_seconds": time_delay_seconds
            }
            
            result = self._crud_repo.modify(filters={"uuid": tracker.uuid}, updates=update_data)

            if result.is_success():
                updated_tracker = self._crud_repo.get_by_uuid(tracker.uuid)
                GLOG.INFO(f"Confirmed execution for signal_id: {signal_id}")
                return ServiceResult.success(updated_tracker)
            else:
                return ServiceResult.error("Failed to update tracking record")

        except Exception as e:
            GLOG.ERROR(f"Failed to confirm execution: {e}")
            return ServiceResult.error(f"Failed to confirm execution: {e}")

    @retry(max_try=3)
    def set_timeout(
        self,
        signal_id: str,
        reason: str = "Execution timeout"
    ) -> ServiceResult:
        """
        Mark signal as timeout status

        Args:
            signal_id: Signal ID
            reason: Timeout reason

        Returns:
            ServiceResult[bool]: Service result
        """
        try:
            self._crud_repo.modify(
                filters={"signal_id": signal_id},
                updates={
                    "tracking_status": TRACKINGSTATUS_TYPES.TIMEOUT,
                    "reject_reason": reason
                }
            )

            GLOG.INFO(f"Marked signal as timeout: {signal_id}")
            return ServiceResult.success(True)

        except Exception as e:
            GLOG.ERROR(f"Failed to mark timeout: {e}")
            return ServiceResult.error(f"Timeout marking failed: {e}")

    def get_pending(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        timeout_minutes: int = 30
    ) -> ServiceResult:
        """
        Get pending signals for confirmation

        Args:
            engine_id: Engine ID filter
            portfolio_id: Portfolio ID filter
            strategy_id: Strategy ID filter
            timeout_minutes: Timeout period (minutes)

        Returns:
            ServiceResult[List[MSignalTracker]]: Service result
        """
        try:
            # 使用SignalTrackerCRUD的特定方法
            pending_signals = self._crud_repo.find_by_tracking_status(
                tracking_status=TRACKINGSTATUS_TYPES.NOTIFIED.value
            )

            return ServiceResult.success(pending_signals)

        except Exception as e:
            GLOG.ERROR(f"Failed to get pending signals: {e}")
            return ServiceResult.error(f"获取待确认信号失败: {e}")

    def get_timeouts(
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
                "tracking_status": TRACKINGSTATUS_TYPES.NOTIFIED,
                "notification_sent_at__lt": timeout_threshold
            }
            
            if engine_id:
                filters["engine_id"] = engine_id
            
            timeout_signals = self._crud_repo.get_items_filtered(**filters)
            
            return ServiceResult.success(timeout_signals)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get timeout signals: {e}")
            return ServiceResult.error(f"获取超时信号失败: {e}")
    
        
    @retry(max_try=3)
    def set_status(
        self,
        tracking_uuid: str,
        new_status: TRACKINGSTATUS_TYPES,
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
            # 获取现有记录 (tracking_uuid实际上是signal_id)
            tracking_records = self._crud_repo.find(filters={"signal_id": tracking_uuid})
            if not tracking_records or len(tracking_records) == 0:
                return ServiceResult.error(f"未找到追踪记录: {tracking_uuid}")

            tracking_record = tracking_records[0]
            
            # 更新状态
            update_data = {
                "tracking_status": new_status,
                "update_at": datetime.now()
            }
            
            if notes:
                update_data["notes"] = notes
            
            # 根据状态设置相应的时间戳
            if new_status == TRACKINGSTATUS_TYPES.EXECUTED:
                update_data["executed_at"] = datetime.now()
            elif new_status == TRACKINGSTATUS_TYPES.TIMEOUT:
                update_data["timeout_at"] = datetime.now()
            elif new_status == TRACKINGSTATUS_TYPES.CANCELED:
                update_data["canceled_at"] = datetime.now()
            
            # 执行更新
            self._crud_repo.modify(filters={"signal_id": tracking_uuid}, updates=update_data)
            updated_record = tracking_record  # modify方法不返回值，使用原来的记录
            
            GLOG.INFO(f"Updated tracking status for {tracking_uuid}: {new_status}")
            return ServiceResult.success(updated_record)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to update tracking status: {e}")
            return ServiceResult.error(f"更新追踪状态失败: {e}")

    @retry(max_try=3)
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
                return ServiceResult.error("获取超时信号失败")
            
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
            return ServiceResult.error(f"批量标记超时失败: {e}")

    def get_statistics_summary(
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
            
            records = self._crud_repo.get_items_filtered(**filters)
            
            total_count = len(records)
            executed_count = len([r for r in records if r.is_executed()])
            pending_count = len([r for r in records if r.is_pending()])
            timeout_count = len([r for r in records if r.is_timeout()])
            
            # 计算平均延迟
            executed_records = [r for r in records if r.is_executed()]
            avg_time_delay = 0

            if executed_records:
                time_delays = [r.time_delay_seconds for r in executed_records if r.time_delay_seconds]
                if time_delays:
                    avg_time_delay = sum(time_delays) / len(time_delays)
            
            statistics = {
                "total_signals": total_count,
                "executed_signals": executed_count,
                "pending_signals": pending_count,
                "timeout_signals": timeout_count,
                "execution_rate": executed_count / total_count if total_count > 0 else 0,
                "timeout_rate": timeout_count / total_count if total_count > 0 else 0,
                "avg_time_delay_seconds": avg_time_delay
            }
            
            return ServiceResult.success(statistics)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get execution statistics: {e}")
            return ServiceResult.error(f"获取执行统计失败: {e}")

    
    @retry(max_try=3)
    def cleanup(self, days_to_keep: int = 30) -> ServiceResult:
        """
        清理旧的追踪记录

        Args:
            days_to_keep: 保留天数

        Returns:
            ServiceResult[int]: 删除的记录数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            # 查询需要删除的旧记录
            old_records = self._crud_repo.find(page_size=10000)

            # 筛选出需要删除的记录
            to_delete = []
            for record in old_records:
                if record.create_at and record.create_at < cutoff_date:
                    to_delete.append(record)

            # 逐条删除
            deleted_count = 0
            for record in to_delete:
                try:
                    self._crud_repo.delete_by_uuid(record.uuid)
                    deleted_count += 1
                except Exception as e:
                    GLOG.WARN(f"Failed to delete signal tracking record {record.uuid}: {e}")

            if deleted_count > 0:
                GLOG.INFO(f"Cleaned up {deleted_count} old signal tracking records")
            else:
                GLOG.DEBUG("No old signal tracking records to clean up")

            return ServiceResult.success(deleted_count)

        except Exception as e:
            GLOG.ERROR(f"Failed to cleanup old records: {e}")
            return ServiceResult.error(f"清理旧记录失败: {e}")

    # ==================== 标准接口方法 ====================

    def get(self, **filters) -> ServiceResult:
        """
        标准获取方法 - 根据过滤条件获取信号追踪记录

        Args:
            **filters: 过滤条件，支持：
                - uuid: 记录UUID
                - signal_id: 信号ID
                - portfolio_id: 投资组合ID
                - engine_id: 引擎ID
                - strategy_id: 策略ID
                - tracking_status: 追踪状态
                - account_type: 账户类型
                - limit: 限制数量
                - offset: 偏移量

        Returns:
            ServiceResult[List[MSignalTracker]]: 服务结果
        """
        try:
            if not filters:
                return ServiceResult.error("获取记录时必须提供过滤条件")

            # 使用CRUD的获取方法
            records = self._crud_repo.find(filters=filters)

            GLOG.DEBUG(f"Retrieved {len(records)} signal tracking records")
            return ServiceResult.success(records)

        except Exception as e:
            GLOG.ERROR(f"Failed to get signal tracking records: {e}")
            return ServiceResult.error(f"获取信号追踪记录失败: {str(e)}")

    def count(self, **filters) -> ServiceResult:
        """
        标准计数方法 - 根据过滤条件统计记录数量

        Args:
            **filters: 过滤条件，支持：
                - signal_id: 信号ID
                - portfolio_id: 投资组合ID
                - engine_id: 引擎ID
                - strategy_id: 策略ID
                - tracking_status: 追踪状态
                - account_type: 账户类型

        Returns:
            ServiceResult[int]: 记录数量
        """
        try:
            # 使用CRUD的计数方法
            count = self._crud_repo.count(**filters)

            GLOG.DEBUG(f"Counted {count} signal tracking records")
            return ServiceResult.success({"count": count})

        except Exception as e:
            GLOG.ERROR(f"Failed to count signal tracking records: {e}")
            return ServiceResult.error(f"统计信号追踪记录失败: {str(e)}")

    def validate(self, data: Dict[str, Any]) -> ServiceResult:
        """
        标准验证方法 - 验证信号追踪数据的有效性

        Args:
            data: 待验证的数据字典

        Returns:
            ServiceResult[bool]: 验证结果
        """
        try:
            if not isinstance(data, dict):
                return ServiceResult.error("数据必须是字典格式")

            # 必填字段验证
            required_fields = [
                'signal_id', 'portfolio_id', 'execution_mode',
                'account_type', 'expected_code', 'expected_direction'
            ]

            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None or data[field] == '':
                    missing_fields.append(field)

            if missing_fields:
                return ServiceResult.error(
                    data={
                        "valid": False,
                        "missing_fields": missing_fields,
                        "message": f"缺少必填字段: {', '.join(missing_fields)}"
                    },
                    error=f"缺少必填字段: {', '.join(missing_fields)}"
                )

            # 数据类型验证
            if 'expected_price' in data and not isinstance(data['expected_price'], (int, float, Decimal)):
                try:
                    data['expected_price'] = float(data['expected_price'])
                except (ValueError, TypeError):
                    return ServiceResult.error("expected_price必须是数值类型")

            if 'expected_volume' in data and not isinstance(data['expected_volume'], int):
                try:
                    data['expected_volume'] = int(data['expected_volume'])
                except (ValueError, TypeError):
                    return ServiceResult.error("expected_volume必须是整数类型")

            # 枚举值验证
            valid_execution_modes = [mode.value for mode in EXECUTION_MODE]
            if 'execution_mode' in data and data['execution_mode'] not in valid_execution_modes:
                return ServiceResult.error(f"无效的执行模式: {data['execution_mode']}")

            valid_account_types = [atype.value for atype in ACCOUNT_TYPE]
            if 'account_type' in data and data['account_type'] not in valid_account_types:
                return ServiceResult.error(f"无效的账户类型: {data['account_type']}")

            GLOG.DEBUG("Signal tracking data validation passed")
            return ServiceResult.success(
                data={
                    "valid": True,
                    "message": "数据验证通过"
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to validate signal tracking data: {e}")
            return ServiceResult.error(f"数据验证失败: {str(e)}")

    def check_integrity(self, **filters) -> ServiceResult:
        """
        标准完整性检查方法 - 检查信号追踪数据的完整性

        Args:
            **filters: 检查范围过滤条件

        Returns:
            ServiceResult[Dict[str, Any]]: 完整性检查结果
        """
        try:
            # 获取检查范围内的记录
            records = self._crud_repo.get_items_filtered(**filters)

            total_records = len(records)
            issues = []
            warnings = []

            # 检查项目
            for record in records:
                record_issues = []

                # 检查关键字段完整性
                if not record.signal_id:
                    record_issues.append("缺少signal_id")
                if not record.portfolio_id:
                    record_issues.append("缺少portfolio_id")
                if not record.expected_code:
                    record_issues.append("缺少expected_code")
                if not record.expected_direction:
                    record_issues.append("缺少expected_direction")

                # 检查已执行记录的字段完整性
                if record.is_executed():
                    if not record.actual_price:
                        record_issues.append("已执行记录缺少actual_price")
                    if not record.actual_timestamp:
                        record_issues.append("已执行记录缺少actual_timestamp")

                # 检查时间戳合理性
                if record.expected_timestamp and record.actual_timestamp:
                    time_diff = (record.actual_timestamp - record.expected_timestamp).total_seconds()
                    if time_diff < 0:
                        warnings.append(f"记录{record.uuid}: 实际时间早于预期时间")
                    elif time_diff > 3600:  # 超过1小时
                        warnings.append(f"记录{record.uuid}: 执行延迟超过1小时")

                if record_issues:
                    issues.append({
                        "record_uuid": record.uuid,
                        "signal_id": record.signal_id,
                        "issues": record_issues
                    })

            # 计算完整性指标
            integrity_score = 1.0
            if total_records > 0:
                integrity_score = (total_records - len(issues)) / total_records

            result = {
                "total_records": total_records,
                "records_with_issues": len(issues),
                "integrity_score": integrity_score,
                "issues": issues,
                "warnings": warnings,
                "recommendations": []
            }

            # 生成建议
            if len(issues) > total_records * 0.1:  # 超过10%的记录有问题
                result["recommendations"].append("建议检查数据输入流程，提高数据质量")

            if len(warnings) > total_records * 0.05:  # 超过5%的记录有警告
                result["recommendations"].append("建议优化执行时间，减少执行延迟")

            GLOG.DEBUG(f"Integrity check completed: {len(issues)} issues found")
            return ServiceResult.success(result)

        except Exception as e:
            GLOG.ERROR(f"Failed to check signal tracking integrity: {e}")
            return ServiceResult.error(f"完整性检查失败: {str(e)}")

    # 从CRUD层移动过来的业务逻辑方法

    def find_pending(
        self,
        account_type: Optional[ACCOUNT_TYPE] = None,
        execution_mode: Optional[EXECUTION_MODE] = None
    ) -> ServiceResult:
        """
        查找待执行的信号追踪记录

        Args:
            account_type: 账户类型筛选
            execution_mode: 执行模式筛选

        Returns:
            ServiceResult: 待执行记录列表
        """
        try:
            # 使用CRUD基础方法查找待执行信号
            filters = {"tracking_status": TRACKINGSTATUS_TYPES.NOTIFIED}
            if account_type is not None:
                filters["account_type"] = account_type
            if execution_mode is not None:
                filters["execution_mode"] = execution_mode

            trackers = self._crud_repo.find(filters=filters, limit=1000)
            return ServiceResult.success(trackers)
        except Exception as e:
            return ServiceResult.error(f"查找待执行信号失败: {str(e)}")

    def get_timeouts_by_account(
        self,
        timeout_hours: int = 24,
        account_type: Optional[ACCOUNT_TYPE] = None
    ) -> ServiceResult:
        """
        查找超时的信号追踪记录

        Args:
            timeout_hours: 超时小时数
            account_type: 账户类型筛选

        Returns:
            ServiceResult: 超时记录列表
        """
        try:
            # 计算超时时间点
            timeout_time = datetime.now() - timedelta(hours=timeout_hours)

            filters = {
                "tracking_status": TRACKINGSTATUS_TYPES.NOTIFIED,
                "notification_sent_at__lt": timeout_time
            }
            if account_type is not None:
                filters["account_type"] = account_type

            trackers = self._crud_repo.find(filters=filters, limit=1000)
            return ServiceResult.success(trackers)
        except Exception as e:
            return ServiceResult.error(f"查找超时信号失败: {str(e)}")

    def get_statistics(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        run_id: Optional[str] = None,
        account_type: Optional[ACCOUNT_TYPE] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        获取信号执行统计信息

        Args:
            portfolio_id: 投资组合ID筛选
            engine_id: 引擎ID筛选
            run_id: 运行会话ID筛选
            account_type: 账户类型筛选
            start_time: 开始时间筛选
            end_time: 结束时间筛选

        Returns:
            ServiceResult: 统计信息
        """
        try:
            # 构建过滤条件
            filters = {}
            if portfolio_id is not None:
                filters["portfolio_id"] = portfolio_id
            if engine_id is not None:
                filters["engine_id"] = engine_id
            if run_id is not None:
                filters["run_id"] = run_id
            if account_type is not None:
                filters["account_type"] = account_type
            if start_time is not None:
                filters["business_timestamp__gte"] = start_time
            if end_time is not None:
                filters["business_timestamp__lte"] = end_time

            # 查询所有相关记录
            all_records = self._crud_repo.find(filters=filters, limit=10000)

            if not all_records:
                stats = {
                    "total_count": 0,
                    "executed_count": 0,
                    "pending_count": 0,
                    "timeout_count": 0,
                    "rejected_count": 0,
                    "execution_rate": 0.0
                }
            else:
                total_count = len(all_records)
                executed_count = len([r for r in all_records if r.tracking_status == TRACKINGSTATUS_TYPES.EXECUTED.value])
                pending_count = len([r for r in all_records if r.tracking_status == TRACKINGSTATUS_TYPES.NOTIFIED.value])
                timeout_count = len([r for r in all_records if r.tracking_status == TRACKINGSTATUS_TYPES.TIMEOUT.value])
                rejected_count = len([r for r in all_records if r.tracking_status == TRACKINGSTATUS_TYPES.REJECTED.value])

                execution_rate = (executed_count / total_count) if total_count > 0 else 0.0

                stats = {
                    "total_count": total_count,
                    "executed_count": executed_count,
                    "pending_count": pending_count,
                    "timeout_count": timeout_count,
                    "rejected_count": rejected_count,
                    "execution_rate": execution_rate
                }

            return ServiceResult.success(stats)
        except Exception as e:
            return ServiceResult.error(f"获取执行统计失败: {str(e)}")

    @retry(max_try=3)
    def batch_update_execution_status(
        self,
        signal_ids: List[str],
        tracking_status: TRACKINGSTATUS_TYPES,
        actual_price: Optional[float] = None,
        actual_volume: Optional[int] = None,
        actual_timestamp: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> ServiceResult:
        """
        批量更新信号执行状态

        Args:
            signal_ids: 信号ID列表 (建议 < 100条)
            tracking_status: 新的追踪状态
            actual_price: 实际价格
            actual_volume: 实际数量
            actual_timestamp: 实际执行时间
            notes: 备注信息

        Returns:
            ServiceResult: 更新成功的记录数量
        """
        try:
            updated_count = 0

            for signal_id in signal_ids:
                tracker = self._crud_repo.find_by_signal_id(signal_id)
                if tracker:
                    # 更新状态信息
                    tracker.tracking_status = tracking_status.value
                    tracker.execution_confirmed_at = datetime.now()

                    if actual_price is not None:
                        tracker.actual_price = to_decimal(actual_price)
                    if actual_volume is not None:
                        tracker.actual_volume = actual_volume
                    if actual_timestamp is not None:
                        tracker.actual_timestamp = datetime_normalize(actual_timestamp)
                    if notes is not None:
                        tracker.notes = notes

                    # 保存更新
                    success = self._crud_repo.update(tracker)
                    if success:
                        updated_count += 1

            return ServiceResult.success({"updated_count": updated_count})
        except Exception as e:
            return ServiceResult.error(f"批量更新执行状态失败: {str(e)}")

    
    @retry(max_try=3)
    def batch_update_paper_trade_execution(
        self,
        executions: List[dict]
    ) -> ServiceResult:
        """
        批量更新PaperTrade执行结果

        Args:
            executions: 执行结果列表，每个dict包含:
                - signal_id: 信号ID
                - actual_price: 实际价格
                - actual_volume: 实际数量
                - actual_timestamp: 执行时间
                - notes: 可选备注

        Returns:
            ServiceResult: 处理结果统计
        """
        try:
            if not executions:
                return ServiceResult.success({"total": 0, "success": 0, "failed": 0})

            signal_ids = [exec_data["signal_id"] for exec_data in executions]

            # 批量查询所有相关信号
            trackers = self._crud_repo.find(filters={"signal_id__in": signal_ids})
            tracker_map = {tracker.signal_id: tracker for tracker in trackers}

            success_count = 0
            failed_count = 0

            for exec_data in executions:
                signal_id = exec_data["signal_id"]
                tracker = tracker_map.get(signal_id)

                if not tracker:
                    GLOG.WARN(f"未找到信号记录: {signal_id}")
                    failed_count += 1
                    continue

                try:
                    # 更新执行信息
                    tracker.tracking_status = TRACKINGSTATUS_TYPES.EXECUTED.value
                    tracker.execution_confirmed_at = datetime.now()
                    tracker.actual_price = to_decimal(exec_data["actual_price"])
                    tracker.actual_volume = exec_data["actual_volume"]
                    tracker.actual_timestamp = datetime_normalize(exec_data.get("actual_timestamp"))
                    tracker.notes = exec_data.get("notes", "PaperTrade模拟成交")

                    success = self._crud_repo.update(tracker)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    GLOG.ERROR(f"更新PaperTrade执行结果失败 {signal_id}: {e}")
                    failed_count += 1

            result = {
                "total": len(executions),
                "success": success_count,
                "failed": failed_count
            }

            GLOG.INFO(f"PaperTrade批量更新完成: {result}")
            return ServiceResult.success(result)
        except Exception as e:
            return ServiceResult.error(f"批量更新PaperTrade执行结果失败: {str(e)}")

    def get_all_signal_ids(self) -> ServiceResult:
        """
        获取所有信号ID

        Returns:
            ServiceResult: 信号ID列表
        """
        try:
            all_records = self._crud_repo.find(limit=10000)
            signal_ids = list(set(item.signal_id for item in all_records if item.signal_id))
            return ServiceResult.success(signal_ids)
        except Exception as e:
            return ServiceResult.error(f"获取信号ID列表失败: {str(e)}")

    def get_portfolio_ids(self) -> ServiceResult:
        """
        获取所有投资组合ID

        Returns:
            ServiceResult: 投资组合ID列表
        """
        try:
            all_records = self._crud_repo.find(limit=10000)
            portfolio_ids = list(set(item.portfolio_id for item in all_records if item.portfolio_id))
            return ServiceResult.success(portfolio_ids)
        except Exception as e:
            return ServiceResult.error(f"获取投资组合ID列表失败: {str(e)}")

    def find_by_business_time(
        self,
        portfolio_id: str,
        start_business_time: Optional[Any] = None,
        end_business_time: Optional[Any] = None,
        account_type: Optional[ACCOUNT_TYPE] = None,
        tracking_status: Optional[TRACKINGSTATUS_TYPES] = None
    ) -> ServiceResult:
        """
        根据业务时间范围查找信号追踪记录

        Args:
            portfolio_id: 投资组合ID
            start_business_time: 开始业务时间
            end_business_time: 结束业务时间
            account_type: 账户类型筛选
            tracking_status: 追踪状态筛选

        Returns:
            ServiceResult: 追踪记录列表
        """
        try:
            filters = {"portfolio_id": portfolio_id}

            if start_business_time:
                filters["business_timestamp__gte"] = datetime_normalize(start_business_time)
            if end_business_time:
                filters["business_timestamp__lte"] = datetime_normalize(end_business_time)
            if account_type is not None:
                filters["account_type"] = account_type
            if tracking_status is not None:
                filters["tracking_status"] = tracking_status

            trackers = self._crud_repo.find(filters=filters, limit=1000)
            return ServiceResult.success(trackers)
        except Exception as e:
            return ServiceResult.error(f"根据业务时间查找信号失败: {str(e)}")

    
    def exists(self, **filters) -> ServiceResult:
        """
        标准存在性检查方法 - 检查信号追踪记录是否存在

        Args:
            **filters: 检查条件，支持：
                - signal_id: 信号ID
                - uuid: 记录UUID
                - portfolio_id: 投资组合ID
                - engine_id: 引擎ID
                - tracking_status: 追踪状态

        Returns:
            ServiceResult[bool]: 存在性检查结果
        """
        try:
            if not filters:
                return ServiceResult.error("存在性检查时必须提供过滤条件")

            # 使用count方法进行存在性检查
            count_result = self.count(**filters)
            if not count_result.is_success():
                return ServiceResult.error("存在性检查时查询失败")

            count = count_result.data.get("count", 0)
            exists = count > 0

            GLOG.DEBUG(f"Existence check result: {exists}")
            return ServiceResult.success({"exists": exists})

        except Exception as e:
            GLOG.ERROR(f"Failed to check signal tracking existence: {e}")
            return ServiceResult.error(f"存在性检查失败: {str(e)}")

    def health_check(self) -> ServiceResult:
        """
        服务健康检查方法 - 检查SignalTrackingService运行状态

        Returns:
            ServiceResult[Dict[str, Any]]: 健康检查结果
        """
        try:
            health_info = {
                "service_name": "SignalTrackingService",
                "status": "healthy",
                "checks": {}
            }

            # 检查CRUD依赖
            if self._crud_repo is None:
                health_info["status"] = "unhealthy"
                health_info["checks"]["crud_dependency"] = {
                    "status": "failed",
                    "error": "SignalTrackerCRUD依赖未初始化"
                }
                return ServiceResult.success(health_info)

            health_info["checks"]["crud_dependency"] = {
                "status": "passed",
                "message": "SignalTrackerCRUD依赖正常"
            }

            # 检查数据库连接 - 尝试执行一个简单查询
            try:
                self._crud_repo.find(limit=1)
                health_info["checks"]["database_connection"] = {
                    "status": "passed",
                    "message": "数据库连接正常"
                }
            except Exception as db_error:
                health_info["status"] = "unhealthy"
                health_info["checks"]["database_connection"] = {
                    "status": "failed",
                    "error": f"数据库连接失败: {str(db_error)}"
                }
                return ServiceResult.success(health_info)

            # 检查服务功能 - 尝试统计记录数量
            try:
                count_result = self.count()
                if count_result.is_success():
                    total_count = count_result.data.get("count", 0)
                    health_info["checks"]["service_functionality"] = {
                        "status": "passed",
                        "message": f"服务功能正常，共{total_count}条记录"
                    }
                    health_info["total_records"] = total_count
                else:
                    health_info["status"] = "degraded"
                    health_info["checks"]["service_functionality"] = {
                        "status": "warning",
                        "error": count_result.error
                    }
            except Exception as func_error:
                health_info["status"] = "unhealthy"
                health_info["checks"]["service_functionality"] = {
                    "status": "failed",
                    "error": f"服务功能检查失败: {str(func_error)}"
                }

            # 检查内存使用情况
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                health_info["checks"]["memory_usage"] = {
                    "status": "passed",
                    "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "message": f"内存使用正常: {round(memory_info.rss / 1024 / 1024, 2)}MB"
                }
            except ImportError:
                health_info["checks"]["memory_usage"] = {
                    "status": "skipped",
                    "message": "psutil未安装，跳过内存检查"
                }
            except Exception as mem_error:
                health_info["checks"]["memory_usage"] = {
                    "status": "warning",
                    "error": f"内存检查失败: {str(mem_error)}"
                }

            # 生成最终健康状态消息
            if health_info["status"] == "healthy":
                message = f"SignalTrackingService运行正常，共{health_info.get('total_records', 0)}条信号追踪记录"
            elif health_info["status"] == "degraded":
                message = "SignalTrackingService部分功能异常，但基本可用"
            else:
                message = "SignalTrackingService运行异常，需要立即处理"

            GLOG.DEBUG(f"Health check completed: {health_info['status']}")
            return ServiceResult.success(health_info, message)

        except Exception as e:
            GLOG.ERROR(f"Failed to perform health check: {e}")
            return ServiceResult.error(f"健康检查失败: {str(e)}")