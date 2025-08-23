"""
ConfirmationHandler 确认处理器

该模块实现信号执行确认的核心逻辑，负责：
1. 解析用户确认命令
2. 更新信号追踪状态
3. 发布执行确认事件
4. 支持确认、拒绝、超时、取消等操作
"""

import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from ....libs import GLOG
from ....data.services.base_service import ServiceResult
from ....enums import EXECUTION_STATUS, TRACKING_STATUS, DIRECTION_TYPES
from ..events.execution_confirmation import (
    EventExecutionConfirmed,
    EventExecutionRejected,
    EventExecutionTimeout,
    EventExecutionCanceled
)


class ConfirmationHandler:
    """
    信号执行确认处理器
    
    处理用户的执行确认命令，更新追踪状态，并发布相应事件
    """
    
    def __init__(self):
        """初始化确认处理器"""
        self._tracking_service = None
        self._event_publisher = None
        
        # 确认命令正则模式
        self._confirm_pattern = re.compile(
            r'^/confirm\s+(\w{8})\s+([\d.]+)\s+(\d+)(?:\s+(.*))?$',
            re.IGNORECASE
        )
        self._reject_pattern = re.compile(
            r'^/reject\s+(\w{8})(?:\s+(.*))?$',
            re.IGNORECASE
        )
        self._timeout_pattern = re.compile(
            r'^/timeout\s+(\w{8})(?:\s+(.*))?$',
            re.IGNORECASE
        )
        
        # 超时配置（分钟）
        self._default_timeout_minutes = 30
        
    @property
    def tracking_service(self):
        """延迟加载信号追踪服务"""
        if self._tracking_service is None:
            from ....data.containers import container
            self._tracking_service = container.signal_tracking_service()
        return self._tracking_service
    
    @property
    def event_publisher(self):
        """延迟加载事件发布器"""
        if self._event_publisher is None:
            # TODO: 实现事件发布器
            # from ....core.event_publisher import EventPublisher
            # self._event_publisher = EventPublisher()
            pass
        return self._event_publisher
    
    def parse_confirm_command(self, command: str) -> Optional[Dict[str, Any]]:
        """
        解析确认命令
        
        Args:
            command: 用户输入的命令，格式: /confirm signal_id price volume [notes]
            
        Returns:
            解析结果字典或None（如果解析失败）
        """
        try:
            command = command.strip()
            match = self._confirm_pattern.match(command)
            
            if not match:
                GLOG.WARN(f"Invalid confirm command format: {command}")
                return None
            
            signal_id = match.group(1)
            actual_price = Decimal(match.group(2))
            actual_volume = int(match.group(3))
            notes = match.group(4) or ""
            
            # 验证参数
            if actual_price <= 0:
                GLOG.WARN(f"Invalid price: {actual_price}")
                return None
            
            if actual_volume <= 0:
                GLOG.WARN(f"Invalid volume: {actual_volume}")
                return None
            
            return {
                "signal_id": signal_id,
                "actual_price": actual_price,
                "actual_volume": actual_volume,
                "notes": notes,
                "execution_time": datetime.now()
            }
            
        except (ValueError, AttributeError) as e:
            GLOG.ERROR(f"Failed to parse confirm command: {command}, error: {e}")
            return None
    
    def parse_reject_command(self, command: str) -> Optional[Dict[str, Any]]:
        """
        解析拒绝命令
        
        Args:
            command: 用户输入的命令，格式: /reject signal_id [reason]
            
        Returns:
            解析结果字典或None（如果解析失败）
        """
        try:
            command = command.strip()
            match = self._reject_pattern.match(command)
            
            if not match:
                GLOG.WARN(f"Invalid reject command format: {command}")
                return None
            
            signal_id = match.group(1)
            reason = match.group(2) or "User rejected"
            
            return {
                "signal_id": signal_id,
                "reject_reason": reason,
                "reject_time": datetime.now()
            }
            
        except (AttributeError,) as e:
            GLOG.ERROR(f"Failed to parse reject command: {command}, error: {e}")
            return None
    
    def parse_timeout_command(self, command: str) -> Optional[Dict[str, Any]]:
        """
        解析超时命令
        
        Args:
            command: 用户输入的命令，格式: /timeout signal_id [reason]
            
        Returns:
            解析结果字典或None（如果解析失败）
        """
        try:
            command = command.strip()
            match = self._timeout_pattern.match(command)
            
            if not match:
                GLOG.WARN(f"Invalid timeout command format: {command}")
                return None
            
            signal_id = match.group(1)
            reason = match.group(2) or "Manual timeout"
            
            return {
                "signal_id": signal_id,
                "timeout_reason": reason,
                "timeout_time": datetime.now()
            }
            
        except (AttributeError,) as e:
            GLOG.ERROR(f"Failed to parse timeout command: {command}, error: {e}")
            return None
    
    def confirm_execution(
        self,
        signal_id: str,
        actual_price: Decimal,
        actual_volume: int,
        execution_time: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> ServiceResult:
        """
        确认信号执行
        
        Args:
            signal_id: 信号ID（支持短ID，前8位）
            actual_price: 实际执行价格
            actual_volume: 实际执行数量
            execution_time: 执行时间（可选，默认当前时间）
            notes: 备注（可选）
            
        Returns:
            ServiceResult: 操作结果
        """
        try:
            execution_time = execution_time or datetime.now()
            
            # 1. 查找信号追踪记录（支持短ID）
            tracking_result = self._find_tracking_by_signal_id(signal_id)
            if not tracking_result.is_success():
                return tracking_result
            
            tracking_record = tracking_result.data
            
            # 2. 验证状态
            if tracking_record.tracking_status != TRACKING_STATUS.PENDING:
                return ServiceResult.error(
                    f"Signal {signal_id} is not in pending status: {tracking_record.tracking_status}"
                )
            
            # 3. 计算偏差指标
            slippage = self._calculate_slippage(
                tracking_record.expected_price,
                actual_price,
                tracking_record.direction
            )
            
            delay_seconds = int((execution_time - tracking_record.created_at).total_seconds())
            
            # 4. 更新追踪记录
            update_result = self.tracking_service.confirm_execution(
                tracking_record.uuid,
                actual_price=actual_price,
                actual_volume=actual_volume,
                execution_time=execution_time,
                slippage=slippage,
                delay_seconds=delay_seconds,
                notes=notes
            )
            
            if not update_result.is_success():
                return update_result
            
            # 5. 发布执行确认事件
            event = EventExecutionConfirmed(
                signal_id=tracking_record.signal_id,
                tracking_id=tracking_record.uuid,
                code=tracking_record.code,
                direction=tracking_record.direction,
                expected_price=tracking_record.expected_price,
                actual_price=actual_price,
                expected_volume=tracking_record.expected_volume,
                actual_volume=actual_volume,
                execution_time=execution_time,
                slippage=slippage,
                delay_seconds=delay_seconds,
                commission=Decimal('0'),  # TODO: 从配置获取手续费
                engine_id=tracking_record.engine_id,
                portfolio_id=tracking_record.portfolio_id
            )
            
            self._publish_event(event)
            
            GLOG.INFO(f"Signal {signal_id} execution confirmed successfully")
            return ServiceResult.success(
                tracking_record,
                f"Signal {signal_id} execution confirmed"
            )
            
        except Exception as e:
            GLOG.ERROR(f"Failed to confirm execution: {e}")
            return ServiceResult.error(f"Execution confirmation failed: {e}")
    
    def reject_execution(
        self,
        signal_id: str,
        reason: str,
        reject_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        拒绝信号执行
        
        Args:
            signal_id: 信号ID（支持短ID）
            reason: 拒绝原因
            reject_time: 拒绝时间（可选，默认当前时间）
            
        Returns:
            ServiceResult: 操作结果
        """
        try:
            reject_time = reject_time or datetime.now()
            
            # 1. 查找信号追踪记录
            tracking_result = self._find_tracking_by_signal_id(signal_id)
            if not tracking_result.is_success():
                return tracking_result
            
            tracking_record = tracking_result.data
            
            # 2. 验证状态
            if tracking_record.tracking_status != TRACKING_STATUS.PENDING:
                return ServiceResult.error(
                    f"Signal {signal_id} is not in pending status: {tracking_record.tracking_status}"
                )
            
            # 3. 更新追踪记录状态
            update_result = self.tracking_service.update_tracking_status(
                tracking_record.uuid,
                TRACKING_STATUS.REJECTED,
                reason
            )
            
            if not update_result.is_success():
                return update_result
            
            # 4. 发布执行拒绝事件
            event = EventExecutionRejected(
                signal_id=tracking_record.signal_id,
                tracking_id=tracking_record.uuid,
                code=tracking_record.code,
                direction=tracking_record.direction,
                reject_reason=reason,
                reject_time=reject_time,
                engine_id=tracking_record.engine_id,
                portfolio_id=tracking_record.portfolio_id
            )
            
            self._publish_event(event)
            
            GLOG.INFO(f"Signal {signal_id} execution rejected: {reason}")
            return ServiceResult.success(
                tracking_record,
                f"Signal {signal_id} execution rejected"
            )
            
        except Exception as e:
            GLOG.ERROR(f"Failed to reject execution: {e}")
            return ServiceResult.error(f"Execution rejection failed: {e}")
    
    def timeout_execution(
        self,
        signal_id: str,
        timeout_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        标记信号执行超时
        
        Args:
            signal_id: 信号ID（支持短ID）
            timeout_time: 超时时间（可选，默认当前时间）
            
        Returns:
            ServiceResult: 操作结果
        """
        try:
            timeout_time = timeout_time or datetime.now()
            
            # 1. 查找信号追踪记录
            tracking_result = self._find_tracking_by_signal_id(signal_id)
            if not tracking_result.is_success():
                return tracking_result
            
            tracking_record = tracking_result.data
            
            # 2. 验证状态
            if tracking_record.tracking_status != TRACKING_STATUS.PENDING:
                return ServiceResult.error(
                    f"Signal {signal_id} is not in pending status: {tracking_record.tracking_status}"
                )
            
            # 3. 计算超时时长
            timeout_duration = int((timeout_time - tracking_record.created_at).total_seconds())
            
            # 4. 更新追踪记录状态
            update_result = self.tracking_service.mark_timeout(
                tracking_record.uuid,
                timeout_duration
            )
            
            if not update_result.is_success():
                return update_result
            
            # 5. 发布执行超时事件
            event = EventExecutionTimeout(
                signal_id=tracking_record.signal_id,
                tracking_id=tracking_record.uuid,
                code=tracking_record.code,
                direction=tracking_record.direction,
                timeout_duration=timeout_duration,
                timeout_time=timeout_time,
                engine_id=tracking_record.engine_id,
                portfolio_id=tracking_record.portfolio_id
            )
            
            self._publish_event(event)
            
            GLOG.INFO(f"Signal {signal_id} execution timed out after {timeout_duration}s")
            return ServiceResult.success(
                tracking_record,
                f"Signal {signal_id} execution timed out"
            )
            
        except Exception as e:
            GLOG.ERROR(f"Failed to timeout execution: {e}")
            return ServiceResult.error(f"Execution timeout failed: {e}")
    
    def cancel_execution(
        self,
        signal_id: str,
        reason: str,
        cancel_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        取消信号执行（系统调用）
        
        Args:
            signal_id: 信号ID（支持短ID）
            reason: 取消原因
            cancel_time: 取消时间（可选，默认当前时间）
            
        Returns:
            ServiceResult: 操作结果
        """
        try:
            cancel_time = cancel_time or datetime.now()
            
            # 1. 查找信号追踪记录
            tracking_result = self._find_tracking_by_signal_id(signal_id)
            if not tracking_result.is_success():
                return tracking_result
            
            tracking_record = tracking_result.data
            
            # 2. 更新追踪记录状态
            update_result = self.tracking_service.update_tracking_status(
                tracking_record.uuid,
                TRACKING_STATUS.CANCELED,
                reason
            )
            
            if not update_result.is_success():
                return update_result
            
            # 3. 发布执行取消事件
            event = EventExecutionCanceled(
                signal_id=tracking_record.signal_id,
                tracking_id=tracking_record.uuid,
                code=tracking_record.code,
                direction=tracking_record.direction,
                cancel_reason=reason,
                cancel_time=cancel_time,
                engine_id=tracking_record.engine_id,
                portfolio_id=tracking_record.portfolio_id
            )
            
            self._publish_event(event)
            
            GLOG.INFO(f"Signal {signal_id} execution canceled: {reason}")
            return ServiceResult.success(
                tracking_record,
                f"Signal {signal_id} execution canceled"
            )
            
        except Exception as e:
            GLOG.ERROR(f"Failed to cancel execution: {e}")
            return ServiceResult.error(f"Execution cancellation failed: {e}")
    
    def check_timeout_signals(self) -> ServiceResult:
        """
        检查并处理超时的信号
        
        Returns:
            ServiceResult: 操作结果，包含处理的超时信号数量
        """
        try:
            # 获取待确认的信号
            pending_result = self.tracking_service.get_pending_signals()
            if not pending_result.is_success():
                return pending_result
            
            pending_signals = pending_result.data
            timeout_count = 0
            
            # 检查每个信号是否超时
            for signal in pending_signals:
                time_elapsed = datetime.now() - signal.created_at
                if time_elapsed > timedelta(minutes=self._default_timeout_minutes):
                    timeout_result = self.timeout_execution(signal.signal_id)
                    if timeout_result.is_success():
                        timeout_count += 1
            
            GLOG.INFO(f"Processed {timeout_count} timeout signals")
            return ServiceResult.success(
                timeout_count,
                f"Processed {timeout_count} timeout signals"
            )
            
        except Exception as e:
            GLOG.ERROR(f"Failed to check timeout signals: {e}")
            return ServiceResult.error(f"Timeout check failed: {e}")
    
    def handle_command(self, command: str) -> ServiceResult:
        """
        处理用户命令（统一入口）
        
        Args:
            command: 用户命令
            
        Returns:
            ServiceResult: 操作结果
        """
        try:
            command = command.strip()
            
            # 确认命令
            if command.lower().startswith('/confirm'):
                parsed = self.parse_confirm_command(command)
                if not parsed:
                    return ServiceResult.error("Invalid confirm command format")
                
                return self.confirm_execution(
                    signal_id=parsed["signal_id"],
                    actual_price=parsed["actual_price"],
                    actual_volume=parsed["actual_volume"],
                    execution_time=parsed["execution_time"],
                    notes=parsed["notes"]
                )
            
            # 拒绝命令
            elif command.lower().startswith('/reject'):
                parsed = self.parse_reject_command(command)
                if not parsed:
                    return ServiceResult.error("Invalid reject command format")
                
                return self.reject_execution(
                    signal_id=parsed["signal_id"],
                    reason=parsed["reject_reason"],
                    reject_time=parsed["reject_time"]
                )
            
            # 超时命令
            elif command.lower().startswith('/timeout'):
                parsed = self.parse_timeout_command(command)
                if not parsed:
                    return ServiceResult.error("Invalid timeout command format")
                
                return self.timeout_execution(
                    signal_id=parsed["signal_id"],
                    timeout_time=parsed["timeout_time"]
                )
            
            else:
                return ServiceResult.error(f"Unknown command: {command}")
                
        except Exception as e:
            GLOG.ERROR(f"Failed to handle command: {command}, error: {e}")
            return ServiceResult.error(f"Command handling failed: {e}")
    
    def _find_tracking_by_signal_id(self, signal_id: str) -> ServiceResult:
        """
        根据信号ID查找追踪记录（支持短ID）
        
        Args:
            signal_id: 信号ID，支持短ID（前8位）
            
        Returns:
            ServiceResult: 查找结果
        """
        try:
            # 如果是短ID（8位），通过模糊查询
            if len(signal_id) == 8:
                result = self.tracking_service.find_by_signal_id_prefix(signal_id)
            else:
                # 完整ID，精确查询
                result = self.tracking_service.get_by_signal_id(signal_id)
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to find tracking record: {e}")
            return ServiceResult.error(f"Failed to find signal: {e}")
    
    def _calculate_slippage(
        self,
        expected_price: Decimal,
        actual_price: Decimal,
        direction: DIRECTION_TYPES
    ) -> Decimal:
        """
        计算滑点
        
        Args:
            expected_price: 预期价格
            actual_price: 实际价格
            direction: 交易方向
            
        Returns:
            滑点（百分比）
        """
        if expected_price == 0:
            return Decimal('0')
        
        # 计算价格偏差
        price_diff = actual_price - expected_price
        slippage_pct = price_diff / expected_price * 100
        
        return slippage_pct
    
    def _publish_event(self, event) -> None:
        """
        发布事件
        
        Args:
            event: 要发布的事件
        """
        try:
            if self.event_publisher:
                self.event_publisher.publish(event)
            else:
                # 临时方案：直接记录日志
                GLOG.INFO(f"Event published: {event}")
                
        except Exception as e:
            GLOG.ERROR(f"Failed to publish event: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取确认处理器统计信息
        
        Returns:
            统计信息字典
        """
        try:
            stats_result = self.tracking_service.get_execution_statistics()
            if stats_result.is_success():
                return stats_result.data
            else:
                return {"error": stats_result.message}
                
        except Exception as e:
            GLOG.ERROR(f"Failed to get statistics: {e}")
            return {"error": f"Failed to get statistics: {e}"}