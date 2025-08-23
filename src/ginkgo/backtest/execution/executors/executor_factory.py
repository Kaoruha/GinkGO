from typing import Optional, Dict, Any

from .base_executor import BaseExecutor
from .backtest_executor import BacktestExecutor
from .manual_executor import ManualExecutor
from ....enums import EXECUTION_MODE, ACCOUNT_TYPE
from ....libs import GLOG


class ExecutorFactory:
    """
    执行器工厂类
    
    根据执行模式创建对应的执行器实例，支持当前和未来的所有执行模式
    """
    
    @staticmethod
    def create_executor(
        execution_mode: EXECUTION_MODE,
        engine_id: Optional[str] = None,
        **kwargs
    ) -> BaseExecutor:
        """
        根据执行模式创建执行器
        
        Args:
            execution_mode: 执行模式
            engine_id: 引擎ID
            **kwargs: 额外的配置参数
            
        Returns:
            BaseExecutor: 执行器实例
            
        Raises:
            ValueError: 不支持的执行模式
        """
        try:
            if execution_mode == EXECUTION_MODE.BACKTEST:
                return ExecutorFactory._create_backtest_executor(**kwargs)
            
            elif execution_mode == EXECUTION_MODE.PAPER_MANUAL:
                return ExecutorFactory._create_paper_manual_executor(engine_id, **kwargs)
            
            elif execution_mode == EXECUTION_MODE.LIVE_MANUAL:
                return ExecutorFactory._create_live_manual_executor(engine_id, **kwargs)
            
            elif execution_mode == EXECUTION_MODE.PAPER_AUTO:
                # 未来实现自动化模拟盘执行器
                raise NotImplementedError(f"Auto execution mode not implemented yet: {execution_mode}")
            
            elif execution_mode == EXECUTION_MODE.LIVE_AUTO:
                # 未来实现自动化实盘执行器
                raise NotImplementedError(f"Auto execution mode not implemented yet: {execution_mode}")
            
            elif execution_mode == EXECUTION_MODE.SEMI_AUTO:
                # 未来实现半自动执行器
                raise NotImplementedError(f"Semi-auto execution mode not implemented yet: {execution_mode}")
            
            else:
                raise ValueError(f"Unsupported execution mode: {execution_mode}")
                
        except Exception as e:
            GLOG.ERROR(f"Failed to create executor for mode {execution_mode}: {e}")
            raise
    
    @staticmethod
    def _create_backtest_executor(**kwargs) -> BacktestExecutor:
        """
        创建回测执行器
        
        Args:
            **kwargs: 配置参数
                - slippage: 滑点率
                - commission_rate: 手续费率
                
        Returns:
            BacktestExecutor: 回测执行器
        """
        slippage = kwargs.get('slippage', 0.0)
        commission_rate = kwargs.get('commission_rate', 0.0)
        
        executor = BacktestExecutor(
            slippage=slippage,
            commission_rate=commission_rate
        )
        
        GLOG.DEBUG(f"Created BacktestExecutor with slippage={slippage}, commission_rate={commission_rate}")
        return executor
    
    @staticmethod
    def _create_paper_manual_executor(engine_id: Optional[str], **kwargs) -> ManualExecutor:
        """
        创建模拟盘人工确认执行器
        
        Args:
            engine_id: 引擎ID
            **kwargs: 配置参数
                
        Returns:
            ManualExecutor: 模拟盘人工确认执行器
        """
        executor = ManualExecutor(
            account_type=ACCOUNT_TYPE.PAPER,
            engine_id=engine_id
        )
        
        GLOG.DEBUG(f"Created PaperManualExecutor for engine_id={engine_id}")
        return executor
    
    @staticmethod
    def _create_live_manual_executor(engine_id: Optional[str], **kwargs) -> ManualExecutor:
        """
        创建实盘人工确认执行器
        
        Args:
            engine_id: 引擎ID
            **kwargs: 配置参数
                
        Returns:
            ManualExecutor: 实盘人工确认执行器
        """
        executor = ManualExecutor(
            account_type=ACCOUNT_TYPE.LIVE,
            engine_id=engine_id
        )
        
        GLOG.DEBUG(f"Created LiveManualExecutor for engine_id={engine_id}")
        return executor
    
    @staticmethod
    def get_supported_modes() -> list[EXECUTION_MODE]:
        """
        获取当前支持的执行模式列表
        
        Returns:
            list[EXECUTION_MODE]: 支持的执行模式列表
        """
        return [
            EXECUTION_MODE.BACKTEST,
            EXECUTION_MODE.PAPER_MANUAL,
            EXECUTION_MODE.LIVE_MANUAL
        ]
    
    @staticmethod
    def get_future_modes() -> list[EXECUTION_MODE]:
        """
        获取未来计划支持的执行模式列表
        
        Returns:
            list[EXECUTION_MODE]: 未来计划支持的执行模式列表
        """
        return [
            EXECUTION_MODE.PAPER_AUTO,
            EXECUTION_MODE.LIVE_AUTO,
            EXECUTION_MODE.SEMI_AUTO
        ]
    
    @staticmethod
    def is_mode_supported(execution_mode: EXECUTION_MODE) -> bool:
        """
        检查执行模式是否当前支持
        
        Args:
            execution_mode: 执行模式
            
        Returns:
            bool: 是否支持
        """
        return execution_mode in ExecutorFactory.get_supported_modes()
    
    @staticmethod
    def get_mode_info(execution_mode: EXECUTION_MODE) -> Dict[str, Any]:
        """
        获取执行模式的详细信息
        
        Args:
            execution_mode: 执行模式
            
        Returns:
            Dict[str, Any]: 模式信息
        """
        mode_info = {
            EXECUTION_MODE.BACKTEST: {
                "name": "历史回测",
                "description": "使用历史数据进行自动化回测",
                "auto_execute": True,
                "requires_confirmation": False,
                "real_money": False,
                "supported": True
            },
            EXECUTION_MODE.PAPER_MANUAL: {
                "name": "模拟盘-人工确认",
                "description": "模拟盘实时交易，需要人工确认执行",
                "auto_execute": False,
                "requires_confirmation": True,
                "real_money": False,
                "supported": True
            },
            EXECUTION_MODE.LIVE_MANUAL: {
                "name": "实盘-人工确认",
                "description": "实盘实时交易，需要人工确认执行",
                "auto_execute": False,
                "requires_confirmation": True,
                "real_money": True,
                "supported": True
            },
            EXECUTION_MODE.PAPER_AUTO: {
                "name": "模拟盘-自动执行",
                "description": "模拟盘实时交易，自动执行（未来功能）",
                "auto_execute": True,
                "requires_confirmation": False,
                "real_money": False,
                "supported": False
            },
            EXECUTION_MODE.LIVE_AUTO: {
                "name": "实盘-自动执行",
                "description": "实盘实时交易，自动执行（未来功能）",
                "auto_execute": True,
                "requires_confirmation": False,
                "real_money": True,
                "supported": False
            },
            EXECUTION_MODE.SEMI_AUTO: {
                "name": "半自动模式",
                "description": "根据规则自动执行部分信号，其他需要确认（未来功能）",
                "auto_execute": True,
                "requires_confirmation": True,
                "real_money": True,
                "supported": False
            }
        }
        
        return mode_info.get(execution_mode, {
            "name": "未知模式",
            "description": "未知的执行模式",
            "auto_execute": False,
            "requires_confirmation": True,
            "real_money": False,
            "supported": False
        })
    
    @staticmethod
    def validate_config(execution_mode: EXECUTION_MODE, config: Dict[str, Any]) -> bool:
        """
        验证执行器配置是否有效
        
        Args:
            execution_mode: 执行模式
            config: 配置参数
            
        Returns:
            bool: 配置是否有效
        """
        try:
            if execution_mode == EXECUTION_MODE.BACKTEST:
                # 验证回测配置
                slippage = config.get('slippage', 0.0)
                commission_rate = config.get('commission_rate', 0.0)
                
                if not isinstance(slippage, (int, float)) or slippage < 0:
                    GLOG.WARN(f"Invalid slippage: {slippage}")
                    return False
                
                if not isinstance(commission_rate, (int, float)) or commission_rate < 0:
                    GLOG.WARN(f"Invalid commission_rate: {commission_rate}")
                    return False
                
                return True
            
            elif execution_mode in [EXECUTION_MODE.PAPER_MANUAL, EXECUTION_MODE.LIVE_MANUAL]:
                # 人工确认模式通常不需要特殊配置验证
                return True
            
            else:
                # 未来模式的配置验证
                GLOG.WARN(f"Configuration validation not implemented for mode: {execution_mode}")
                return True
                
        except Exception as e:
            GLOG.ERROR(f"Configuration validation error: {e}")
            return False