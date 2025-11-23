"""
IRiskManagement Protocol Interface

This module defines the IRiskManagement Protocol interface for risk management systems,
providing type safety and IDE support for risk control development.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class IRiskManagement(Protocol):
    """风险管理接口协议 (Risk Management Interface Protocol)

    这个Protocol定义了所有风险管理系统必须实现的核心接口，提供类型安全的
    编译时检查和运行时验证能力。

    主要功能：
    1. 被动风控 - 验证和调整订单（cal方法）
    2. 主动风控 - 生成风控信号（generate_risk_signals方法）
    3. 风险监控 - 实时监控风险指标和限额
    4. 参数管理 - 验证和更新风控参数

    使用示例：
        class MyRiskManager(BaseRiskManagement, RiskMixin):
            def validate_order(self, portfolio_info: Dict[str, Any], order: Order) -> Order:
                # 实现订单风控逻辑
                return adjusted_order

            def generate_risk_signals(self, portfolio_info: Dict[str, Any], event: Any) -> List[Signal]:
                # 实现主动风控信号生成
                return risk_signals

    类型检查：
        def validate_risk_manager(risk_mgr: IRiskManagement) -> bool:
            return isinstance(risk_mgr, IRiskManagement)
    """

    def validate_order(self, portfolio_info: Dict[str, Any], order: Any) -> Any:
        """
        验证并调整订单 (Validate and Adjust Order)

        被动风控机制，在订单生成时进行拦截调整。风控系统可以修改订单数量、
        价格等参数，或者直接拒绝订单。

        Args:
            portfolio_info: 投资组合信息，包含持仓、资金、风险指标等
                ```python
                {
                    "positions": {"000001.SZ": 1000, "000002.SZ": 500},
                    "total_value": 1000000.0,
                    "available_cash": 500000.0,
                    "position_costs": {"000001.SZ": 10.0, "000002.SZ": 15.0},
                    "risk_metrics": {"var": 0.02, "max_drawdown": 0.05}
                }
                ```
            order: 待验证的订单
                ```python
                Order(
                    symbol="000001.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    quantity=1000,
                    price=10.50
                )
                ```

        Returns:
            Order: 调整后的订单，可能的调整包括：
                - 保持不变（订单通过风控检查）
                - 数量调整（减少订单量以符合风险限制）
                - 价格调整（调整价格以减少市场冲击）
                - 拒绝订单（数量设为0或其他拒绝标识）

        典型风控检查：
            1. 仓位比例限制
            2. 单日交易量限制
            3. 流动性检查
            4. 价格合理性检查
            5. 集中度风险检查

        Note:
            - 应该尽量调整订单而非直接拒绝，提高交易执行率
            - 调整逻辑应该透明，便于理解和调试
            - 重要决策应该记录日志，便于后续分析
        """
        ...

    def generate_risk_signals(self, portfolio_info: Dict[str, Any], event: Any) -> List[Any]:
        """
        生成风控信号 (Generate Risk Signals)

        主动风控机制，根据市场情况和投资组合状态主动发出风控信号。
        这些信号可以触发止损、止盈、减仓等风险控制操作。

        Args:
            portfolio_info: 投资组合信息
                ```python
                {
                    "positions": {"000001.SZ": 1000, "000002.SZ": 500},
                    "total_value": 1000000.0,
                    "unrealized_pnl": {"000001.SZ": 500.0, "000002.SZ": -200.0},
                    "risk_metrics": {"var": 0.02, "beta": 1.2}
                }
                ```
            event: 触发事件（通常是价格更新事件）
                ```python
                EventPriceUpdate(
                    symbol="000001.SZ",
                    price=9.50,  # 价格下跌，可能触发止损
                    timestamp=datetime.now()
                )
                ```

        Returns:
            List[Signal]: 风控信号列表，包括：
                - 止损信号：当亏损达到阈值时触发
                - 止盈信号：当盈利达到目标时触发
                - 减仓信号：当风险过高时部分平仓
                - 调仓信号：基于风险模型的投资组合再平衡
                空列表表示无需风控操作

        典型风控场景：
            1. 止损检查：检查是否触及止损线
            2. 止盈检查：检查是否达到盈利目标
            3. VaR超限：投资组合风险价值超标
            4. 回撤控制：最大回撤超过限制
            5. 流动性风险：市场流动性不足

        Note:
            - 主动风控信号应该谨慎生成，避免过度交易
            - 信号应该包含明确的理由和建议操作
            - 应该考虑交易成本，避免频繁操作
        """
        ...

    def check_risk_limits(self, portfolio_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查风险限制 (Check Risk Limits)

        检查当前投资组合是否违反预设的风险限制，并生成相应的警报。

        Args:
            portfolio_info: 投资组合信息
                ```python
                {
                    "positions": {"000001.SZ": 1000, "000002.SZ": 500},
                    "total_value": 1000000.0,
                    "sector_exposure": {"科技": 0.4, "金融": 0.3},
                    "leverage": 1.1,
                    "var_95": 0.025
                }
                ```

        Returns:
            List[Dict[str, Any]]: 风险警报列表
                ```python
                [
                    {
                        "limit_type": "position_ratio",
                        "current_value": 0.15,
                        "limit_value": 0.10,
                        "severity": "high",
                        "symbol": "000001.SZ",
                        "message": "单股仓位超限：15% > 10%"
                    },
                    {
                        "limit_type": "sector_concentration",
                        "current_value": 0.4,
                        "limit_value": 0.3,
                        "severity": "medium",
                        "sector": "科技",
                        "message": "行业集中度过高：40% > 30%"
                    }
                ]
                ```

        常见风险限制类型：
            1. 单股仓位比例限制
            2. 行业集中度限制
            3. 总仓位限制
            4. 杠杆率限制
            5. VaR限制
            6. 回撤限制
            7. 换手率限制

        Note:
            - 应该提供多级警报（低、中、高严重程度）
            - 警报信息应该包含具体的数值和建议措施
            - 风险限制应该可配置，适应不同的风险偏好
        """
        ...

    def update_risk_parameters(self, parameters: Dict[str, float]) -> None:
        """
        更新风控参数 (Update Risk Parameters)

        动态更新风控系统的参数，支持运行时调整风险控制策略。

        Args:
            parameters: 新的风控参数
                ```python
                {
                    "max_position_ratio": 0.15,      # 最大单股仓位比例
                    "max_total_position": 0.85,       # 最大总仓位
                    "loss_limit": 0.05,               # 止损比例
                    "profit_target": 0.20,            # 止盈比例
                    "var_limit": 0.025,               # VaR限制
                    "max_drawdown": 0.08,             # 最大回撤
                    "leverage_limit": 1.2             # 杠杆率限制
                }
                ```

        Raises:
            ValueError: 当参数无效时抛出详细错误信息
            RuntimeError: 当参数更新失败时抛出

        参数验证逻辑：
            1. 参数类型检查
            2. 数值范围验证
            3. 参数间一致性检查
            4. 业务规则验证

        Note:
            - 参数更新应该立即生效
            - 应该记录参数变更历史
            - 关键参数变更可能需要重新校准系统
        """
        ...

    def get_risk_metrics(self, portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        获取风险指标 (Get Risk Metrics)

        计算并返回当前投资组合的风险指标，用于风险监控和评估。

        Args:
            portfolio_info: 投资组合信息
                ```python
                {
                    "positions": {"000001.SZ": 1000, "000002.SZ": 500},
                    "total_value": 1000000.0,
                    "cash": 50000.0,
                    "historical_returns": [0.01, -0.02, 0.015, ...]
                }
                ```

        Returns:
            Dict[str, float]: 风险指标字典
                ```python
                {
                    "portfolio_var_95": 0.025,        # 95% VaR
                    "portfolio_var_99": 0.035,        # 99% VaR
                    "cvar_95": 0.03,                  # 95% CVaR
                    "max_drawdown": 0.08,             # 最大回撤
                    "current_drawdown": 0.03,         # 当前回撤
                    "volatility": 0.15,               # 波动率
                    "beta": 1.1,                      # Beta系数
                    "tracking_error": 0.02,           # 跟踪误差
                    "information_ratio": 0.8,         # 信息比率
                    "leverage": 1.0,                  # 杠杆率
                    "position_concentration": 0.25,    # 仓位集中度
                    "sector_concentration": 0.4,      # 行业集中度
                    "liquidity_risk": 0.02,           # 流动性风险
                    "correlation_risk": 0.65           # 相关性风险
                }
                ```

        指标计算方法：
            1. VaR/CVaR：历史模拟法或蒙特卡洛法
            2. 回撤：基于历史高点的最大跌幅
            3. 波动率：收益率的标准差
            4. 集中度：Herfindahl指数或最大仓位比例

        Note:
            - 指标计算应该基于足够的历史数据
            - 应该提供不同时间窗口的风险指标
            - 计算方法应该保持一致性和可重复性
        """
        ...

    @property
    def name(self) -> str:
        """
        风控系统名称 (Risk Management System Name)

        Returns:
            str: 风控系统的唯一名称标识

        Note:
            - 名称应该在系统内保持唯一性
            - 建议使用描述性名称，如"PositionRatioRisk"
        """
        ...

    def get_risk_status(self) -> Dict[str, Any]:
        """
        获取风控状态 (Get Risk Status)

        返回风控系统的当前状态，包括是否激活、最近的操作历史等。

        Returns:
            Dict[str, Any]: 风控状态信息
                ```python
                {
                    "is_active": True,                     # 是否激活
                    "last_action_time": "2023-12-31T14:30:00Z",  # 最后操作时间
                    "total_actions": 150,                  # 总操作次数
                    "order_adjustments": 45,               # 订单调整次数
                    "signals_generated": 105,              # 信号生成次数
                    "current_alerts_count": 2,             # 当前警报数量
                    "risk_limits_violated": 1,            # 违反的风险限制数量
                    "system_health": "healthy",           # 系统健康状态
                    "last_update": "2023-12-31T15:00:00Z"  # 最后更新时间
                }
                ```

        Note:
            - 状态信息应该实时更新
            - 应该提供足够的信息用于系统监控
            - 异常状态应该及时发出警报
        """
        ...