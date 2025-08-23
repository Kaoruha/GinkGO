from typing import Optional
from datetime import datetime

from .base_executor import BaseExecutor
from .execution_result import ExecutionResult
from .execution_constraints import ExecutionConstraints
from ....enums import EXECUTION_MODE, EXECUTION_STATUS, ACCOUNT_TYPE
from ....backtest.entities.signal import Signal
from ....libs import GLOG, time_logger


class ManualExecutor(BaseExecutor):
    """
    人工确认执行器
    
    用于模拟盘和实盘的人工确认执行模式，发送通知并等待用户确认
    """
    
    def __init__(self, account_type: ACCOUNT_TYPE, engine_id: Optional[str] = None):
        """
        初始化人工确认执行器
        
        Args:
            account_type: 账户类型（模拟盘或实盘）
            engine_id: 引擎ID
        """
        # 执行模式映射
        if account_type == ACCOUNT_TYPE.PAPER:
            execution_mode = EXECUTION_MODE.PAPER_MANUAL
        elif account_type == ACCOUNT_TYPE.LIVE:
            execution_mode = EXECUTION_MODE.LIVE_MANUAL
        else:
            raise ValueError(f"ManualExecutor does not support account type: {account_type}")
        
        # 调用父类构造函数
        super().__init__(execution_mode)
        
        self.account_type = account_type
        self.engine_id = engine_id or ""
        
        # 延迟加载依赖服务
        self._tracking_service = None
        self._notifier = None
        self._risk_checker = None
    
    @property
    def tracking_service(self):
        """延迟加载信号追踪服务"""
        if self._tracking_service is None:
            from ....libs.ginkgo_container import container
            self._tracking_service = container.services.signal_tracking_service()
        return self._tracking_service
    
    @property
    def notifier(self):
        """延迟加载通知服务"""
        if self._notifier is None:
            from ....libs import GNOTIFIER
            self._notifier = GNOTIFIER
        return self._notifier
    
    @property
    def risk_checker(self):
        """延迟加载风险检查器"""
        if self._risk_checker is None:
            # 这里可以根据需要实现风险检查器
            # from ....risk import RiskChecker
            # self._risk_checker = RiskChecker()
            pass
        return self._risk_checker
    
    @time_logger
    def execute_signal(self, signal: Signal) -> ExecutionResult:
        """
        执行信号 - 发送通知并创建追踪记录
        
        Args:
            signal: 需要执行的交易信号
            
        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 1. 风险检查（如果有风险检查器）
            if self.risk_checker and not self._check_risk(signal):
                return self.create_rejected_result(signal, "Risk check failed")
            
            # 2. 创建追踪记录
            tracking_result = self.tracking_service.create_tracking(
                signal=signal,
                execution_mode=self.execution_mode,
                account_type=self.account_type,
                engine_id=self.engine_id
            )
            
            if not tracking_result.is_success():
                GLOG.ERROR(f"Failed to create tracking record: {tracking_result.message}")
                return self.create_error_result(signal, "Failed to create tracking record")
            
            tracking_record = tracking_result.data
            
            # 3. 发送通知
            try:
                self._send_notification(signal)
                GLOG.INFO(f"Sent notification for signal: {signal.uuid}")
            except Exception as e:
                GLOG.ERROR(f"Failed to send notification: {e}")
                # 通知发送失败不影响追踪记录的创建
            
            # 4. 返回等待确认状态
            return ExecutionResult(
                signal_id=signal.uuid,
                status=EXECUTION_STATUS.PENDING_CONFIRMATION,
                tracking_id=tracking_record.uuid,
                execution_time=datetime.now()
            )
            
        except Exception as e:
            GLOG.ERROR(f"ManualExecutor failed to execute signal: {e}")
            return self.create_error_result(signal, f"Execution error: {e}")
    
    
    def can_auto_execute(self) -> bool:
        """
        是否支持自动执行
        
        Returns:
            bool: False，人工确认执行器不支持自动执行
        """
        return False
    
    def requires_confirmation(self) -> bool:
        """
        是否需要人工确认
        
        Returns:
            bool: True，人工确认执行器需要人工确认
        """
        return True
    
    def _validate_mode_specific(self, signal: Signal) -> bool:
        """
        人工确认模式特定的验证逻辑
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 模式特定验证是否通过
        """
        try:
            # 人工确认模式的特定验证
            # 例如：检查是否在交易时间内等
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Manual mode specific validation error: {e}")
            return False
    
    def _create_execution_constraints(self) -> Optional[ExecutionConstraints]:
        """
        创建人工确认模式的执行约束条件
        
        Returns:
            ExecutionConstraints: 执行约束条件
        """
        # 人工确认模式可以有一些基础约束
        constraints = ExecutionConstraints()
        
        # 设置基础约束
        constraints.auto_execution_enabled = False
        constraints.max_single_order_value = 1000000  # 单笔最大100万
        
        # 实盘比模拟盘更严格的约束
        if self.account_type == ACCOUNT_TYPE.LIVE:
            constraints.max_single_order_value = 100000  # 实盘单笔最大10万
        
        return constraints
    
    def _prepare_mode_specific(self, signal: Signal) -> bool:
        """
        人工确认模式特定的准备工作
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 准备是否成功
        """
        try:
            # 可以在这里做一些准备工作，比如检查市场开放时间等
            GLOG.DEBUG(f"Preparing manual execution for signal: {signal.uuid}")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Manual execution preparation failed: {e}")
            return False
    
    def _cleanup_mode_specific(self, signal: Signal, result: ExecutionResult) -> None:
        """
        人工确认模式特定的清理工作
        
        Args:
            signal: 已执行的信号
            result: 执行结果
        """
        try:
            GLOG.DEBUG(f"Cleaning up manual execution for signal: {signal.uuid}")
            # 可以在这里做一些清理工作
            
        except Exception as e:
            GLOG.ERROR(f"Manual cleanup execution failed: {e}")
    
    def _check_risk(self, signal: Signal) -> bool:
        """
        风险检查
        
        Args:
            signal: 需要检查的信号
            
        Returns:
            bool: 是否通过风险检查
        """
        if not self.risk_checker:
            return True
        
        try:
            # 这里可以实现具体的风险检查逻辑
            return self.risk_checker.check_signal(signal)
        except Exception as e:
            GLOG.ERROR(f"Risk check error: {e}")
            return False
    
    def _send_notification(self, signal: Signal) -> None:
        """
        发送交易信号通知
        
        Args:
            signal: 交易信号
        """
        try:
            from rich.text import Text
            from rich.console import Console
            
            # 准备通知内容
            account_type_name = "模拟盘" if self.account_type == ACCOUNT_TYPE.PAPER else "实盘"
            direction_name = "买入" if signal.direction.value == 1 else "卖出"
            
            # 使用Rich Text构建消息
            console = Console()
            text = Text()
            
            # 标题
            text.append(f"[{account_type_name}交易信号]\n", style="bold red" if self.account_type == ACCOUNT_TYPE.LIVE else "bold blue")
            
            # 信号详情
            text.append("策略: ", style="cyan")
            text.append(f"{getattr(signal, 'strategy_id', 'Unknown')}\n")
            
            text.append("代码: ", style="cyan")
            text.append(f"{signal.code}\n")
            
            text.append("方向: ", style="cyan")
            text.append(f"{direction_name}\n", style="green" if signal.direction.value == 1 else "red")
            
            text.append("价格: ", style="cyan")
            text.append(f"{getattr(signal, 'price', 0):.2f}\n")
            
            text.append("数量: ", style="cyan")
            text.append(f"{getattr(signal, 'volume', 0)}\n")
            
            text.append("时间: ", style="cyan")
            text.append(f"{signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            text.append("信号ID: ", style="cyan")
            text.append(f"{signal.uuid[:8]}\n")
            
            text.append("\n请在30分钟内完成执行并回复确认\n", style="yellow")
            text.append(f"回复格式: /confirm {signal.uuid[:8]} 实际价格 实际数量\n", style="dim")
            
            # 添加风险提示
            if self.account_type == ACCOUNT_TYPE.LIVE:
                text.append("\n这是真实交易，请谨慎操作", style="bold red")
            else:
                text.append("\n这是模拟交易，不涉及真实资金", style="dim")
            
            # 转换为字符串发送
            with console.capture() as capture:
                console.print(text)
            
            message = capture.get()
            
            # 发送通知
            self.notifier.echo_to_telegram(message)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to send notification: {e}")
            # 如果Rich格式化失败，回退到简单文本
            self._send_simple_notification(signal)
    
    def _send_simple_notification(self, signal: Signal) -> None:
        """
        发送简单文本通知（Rich格式化失败时的备选方案）
        
        Args:
            signal: 交易信号
        """
        try:
            account_type_name = "模拟盘" if self.account_type == ACCOUNT_TYPE.PAPER else "实盘"
            direction_name = "买入" if signal.direction.value == 1 else "卖出"
            
            message = f"""
[{account_type_name}交易信号]
策略: {getattr(signal, 'strategy_id', 'Unknown')}
代码: {signal.code}
方向: {direction_name}
价格: {getattr(signal, 'price', 0):.2f}
数量: {getattr(signal, 'volume', 0)}
时间: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
信号ID: {signal.uuid[:8]}

请在30分钟内完成执行并回复确认
回复格式: /confirm {signal.uuid[:8]} 实际价格 实际数量
"""
            
            if self.account_type == ACCOUNT_TYPE.LIVE:
                message += "\n⚠️ 这是真实交易，请谨慎操作"
            else:
                message += "\n📝 这是模拟交易，不涉及真实资金"
            
            # 发送通知
            self.notifier.echo_to_telegram(message)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to send simple notification: {e}")
            raise