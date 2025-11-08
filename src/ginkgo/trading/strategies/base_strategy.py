import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin


class BaseStrategy(ContextMixin, TimeMixin, BacktestBase):
    def __init__(self, name: str = "Strategy", **kwargs):
        # 显式初始化各个Mixin和基类，确保正确的初始化顺序
        ContextMixin.__init__(self, **kwargs)
        TimeMixin.__init__(self, **kwargs)
        BacktestBase.__init__(self, name=name, **kwargs)
        self._raw = {}
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    @property
    def data_feeder(self):
        return self._data_feeder

    
    def cal(self, portfolio_info, event, *args, **kwargs) -> List[Signal]:
        """
        策略计算方法
        Args:
            portfolio_info(Dict): 投资组合信息
            event(EventBase): 事件
        Returns:
            List[Signal]: 信号列表，如果没有信号返回空列表
        """
        return []

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息

        Returns:
            Dict[str, Any]: 包含策略名称、版本、描述等信息的字典
        """
        return {
            "name": self.name,
            "version": "1.0.0",
            "description": f"{self.name} - 基础策略类",
            "parameters": {k: v for k, v in self.__dict__.items() if not k.startswith('_')},
            "last_updated": datetime.now().isoformat()
        }

    
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        初始化策略

        Args:
            context: 初始化上下文，包含数据源、时间范围等信息
        """
        try:
            # 验证上下文基本结构
            if not isinstance(context, dict):
                raise ValueError("Context must be a dictionary")

            # 存储初始化上下文
            self._initialization_context = context.copy()

            # 记录初始化时间
            self._initialization_time = datetime.now()

            # 初始化完成
            pass

        except Exception as e:
            # 初始化失败，记录错误并重新抛出
            raise

    def finalize(self) -> Dict[str, Any]:
        """
        策略结束清理

        Returns:
            Dict[str, Any]: 策略执行结果和统计信息
        """
        try:
            # 计算执行时间
            init_time = getattr(self, '_initialization_time', datetime.now())
            execution_time = (datetime.now() - init_time).total_seconds()

            # 构建返回结果
            result = {
                "execution_summary": {
                    "strategy_name": self.name,
                    "execution_time": execution_time,
                    "initialization_time": init_time.isoformat() if init_time else None,
                    "finalization_time": datetime.now().isoformat()
                },
                "final_portfolio": {
                    "strategy_status": "completed"
                },
                "performance_attribution": {
                    "strategy_return": 0.0,
                    "market_return": 0.0,
                    "alpha": 0.0
                },
                "recommendations": [
                    "考虑实现具体的策略逻辑",
                    "添加性能监控指标"
                ]
            }

            # 策略结束清理完成
            pass

            return result

        except Exception as e:
            # 策略结束清理失败，返回基本结果
            return {
                "execution_summary": {"strategy_name": self.name, "status": "error"},
                "error": str(e)
            }

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        验证参数有效性 (简化实现)

        基于Python动态类型的简单参数验证。由于使用Python动态特性，
        这里只做基本的存在性检查，复杂的参数验证已被移除。

        Args:
            params: 待验证的参数字典

        Returns:
            bool: 总是返回True，表示接受所有参数

        Note:
            - 简化实现：依赖Python动态类型特性
            - 参数通过setattr直接设置到实例上
            - 不再进行复杂的类型转换和范围检查
        """
        # 简化实现：接受所有参数
        return True

    def on_data_updated(self, symbols: List[str]) -> None:
        """
        数据更新回调

        Args:
            symbols: 更新的标的代码列表
        """
        try:
            # 验证输入参数
            if not isinstance(symbols, list):
                raise ValueError("Symbols must be a list")

            # 记录更新的符号
            if hasattr(self, '_updated_symbols'):
                self._updated_symbols.extend(symbols)
            else:
                self._updated_symbols = symbols.copy()

            # 去重处理
            if hasattr(self, '_updated_symbols'):
                self._updated_symbols = list(set(self._updated_symbols))

        except Exception as e:
            # 数据更新回调处理失败，但不抛出异常避免影响主流程
            pass

# Backward compatibility: some tests import StrategyBase
StrategyBase = BaseStrategy
