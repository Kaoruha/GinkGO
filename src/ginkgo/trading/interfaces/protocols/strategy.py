"""
IStrategy Protocol Interface

This module defines the IStrategy Protocol interface for trading strategies,
providing type safety and IDE support for strategy development.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class IStrategy(Protocol):
    """交易策略接口协议 (Trading Strategy Interface Protocol)

    这个Protocol定义了所有交易策略必须实现的核心接口，提供类型安全的
    编译时检查和运行时验证能力。

    主要功能：
    1. 信号计算 - 基于市场数据生成交易信号
    2. 生命周期管理 - 初始化和清理方法
    3. 信息提供 - 获取策略元信息和状态
    4. 数据更新 - 响应数据更新事件

    使用示例：
        class MyStrategy(BaseStrategy):
            def cal(self, portfolio_info: Dict[str, Any], event: Any) -> List[Signal]:
                # 实现策略逻辑
                return signals

            def get_strategy_info(self) -> Dict[str, Any]:
                return {"name": "MyStrategy", "version": "1.0"}

    类型检查：
        def validate_strategy(strategy: IStrategy) -> bool:
            return isinstance(strategy, IStrategy)

    注意事项：
        - 使用Python动态类型特性，参数通过kwargs直接设置
        - 不再包含运行时参数验证方法，简化架构设计
    """

    def cal(self, portfolio_info: Dict[str, Any], event: Any) -> List[Any]:
        """
        计算交易信号 (Calculate Trading Signals)

        策略的核心方法，根据投资组合信息和市场事件计算交易信号。

        Args:
            portfolio_info: 投资组合信息，包含持仓、资金、风险指标等
                ```python
                {
                    "positions": {"000001.SZ": 1000, "000002.SZ": 500},
                    "total_value": 1000000.0,
                    "available_cash": 500000.0,
                    "risk_metrics": {"var": 0.02, "max_drawdown": 0.05}
                }
                ```
            event: 市场事件，通常是价格更新事件
                ```python
                EventPriceUpdate(
                    symbol="000001.SZ",
                    price=10.50,
                    volume=1000000,
                    timestamp=datetime.now()
                )
                ```

        Returns:
            List[Signal]: 交易信号列表，如果没有信号返回空列表
                ```python
                [
                    Signal(
                        code="000001.SZ",
                        direction=DIRECTION_TYPES.LONG,
                        reason="金叉买入信号",
                        confidence=0.85
                    )
                ]
                ```

        Raises:
            ValueError: 当输入参数无效时抛出
            RuntimeError: 当策略计算过程中发生错误时抛出
            DataError: 当数据访问失败时抛出

        Note:
            - 此方法应该为纯函数，相同的输入应该产生相同的输出
            - 建议在方法内部进行异常处理，避免影响整个系统
            - 返回的信号应该经过充分验证，确保符合风控要求
        """
        ...

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息 (Get Strategy Information)

        返回策略的元信息，用于系统管理和监控。

        Returns:
            Dict[str, Any]: 策略信息字典，包含以下字段：
                ```python
                {
                    "name": "MovingAverageStrategy",           # 策略名称
                    "version": "1.0.0",                       # 策略版本
                    "description": "基于移动平均的趋势跟踪策略",  # 策略描述
                    "parameters": {                           # 策略参数
                        "short_period": 5,
                        "long_period": 20
                    },
                    "performance_metrics": {                 # 性能指标
                        "total_return": 0.15,
                        "sharpe_ratio": 1.2,
                        "max_drawdown": 0.08
                    },
                    "risk_metrics": {                        # 风险指标
                        "var_95": 0.02,
                        "volatility": 0.15
                    },
                    "last_updated": "2023-12-31T15:00:00Z"   # 最后更新时间
                }
                ```

        Note:
            - 返回的信息应该及时更新，反映策略的最新状态
            - 性能指标应该在回测或实盘运行后计算
            - 此方法用于展示和监控，不应包含敏感信息
        """
        ...

  
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        初始化策略 (Initialize Strategy)

        在策略开始执行前进行初始化工作，如数据预加载、指标计算等。

        Args:
            context: 初始化上下文，包含必要的环境信息
                ```python
                {
                    "data_source": "tushare",           # 数据源
                    "start_date": "2023-01-01",        # 开始日期
                    "end_date": "2023-12-31",          # 结束日期
                    "universe": ["000001.SZ", "000002.SZ"],  # 股票池
                    "frequency": "1d",                  # 数据频率
                    "benchmark": "000300.SH"            # 基准指数
                }
                ```

        Raises:
            ValueError: 当上下文参数无效时抛出
            RuntimeError: 当初始化过程中发生错误时抛出
            DataError: 当数据预加载失败时抛出

        典型初始化步骤：
            1. 验证上下文参数
            2. 预加载历史数据
            3. 计算技术指标
            4. 设置内部状态
            5. 验证初始化结果

        Note:
            - 此方法在策略开始前只调用一次
            - 初始化失败将阻止策略执行
            - 应该记录初始化过程，便于调试
        """
        ...

    def finalize(self) -> Dict[str, Any]:
        """
        策略结束清理 (Finalize Strategy)

        在策略执行结束后进行清理工作，返回执行结果和统计信息。

        Returns:
            Dict[str, Any]: 策略执行结果
                ```python
                {
                    "execution_summary": {
                        "total_signals": 150,
                        "successful_trades": 85,
                        "failed_trades": 10,
                        "execution_time": 300.5
                    },
                    "final_portfolio": {
                        "total_value": 1150000.0,
                        "cash": 45000.0,
                        "positions": {"000001.SZ": {"quantity": 1000, "value": 10500.0}}
                    },
                    "performance_attribution": {
                        "strategy_return": 0.15,
                        "market_return": 0.08,
                        "alpha": 0.07
                    },
                    "recommendations": [
                        "建议优化止损策略",
                        "考虑添加市场状态过滤器"
                    ]
                }
                ```

        典型清理步骤：
            1. 计算最终绩效指标
            2. 生成执行报告
            3. 清理临时数据
            4. 保存重要状态
            5. 提供改进建议

        Note:
            - 此方法在策略结束后自动调用
            - 返回的信息用于策略评估和优化
            - 确保所有资源都被正确释放
        """
        ...

    @property
    def name(self) -> str:
        """
        策略名称 (Strategy Name)

        Returns:
            str: 策略的唯一名称标识

        Note:
            - 名称应该在系统内保持唯一性
            - 建议使用描述性名称，便于识别
        """
        ...

    def on_data_updated(self, symbols: List[str]) -> None:
        """
        数据更新回调 (Data Update Callback)

        当有新数据可用时调用，用于策略的数据预处理和缓存更新。

        Args:
            symbols: 更新的标的代码列表
                ```python
                ["000001.SZ", "000002.SZ", "600000.SH"]
                ```

        典型处理步骤：
            1. 更新技术指标
            2. 刷新缓存数据
            3. 检查数据完整性
            4. 更新内部状态

        Note:
            - 此方法为可选实现，默认为空操作
            - 应该快速执行，避免阻塞主流程
            - 异常不应该向上传播，应该内部处理
        """
        ...