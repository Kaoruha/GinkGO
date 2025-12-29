# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Portfolio PortfolioProtocol组合协议定义组合接口标准提供相关功能和接口实现






"""
IPortfolio Protocol Interface

This module defines the IPortfolio Protocol interface for portfolio management systems,
providing type safety and IDE support for portfolio development.
"""

from typing import Protocol, Dict, Any, List, Optional, runtime_checkable
from decimal import Decimal


@runtime_checkable
class IPortfolio(Protocol):
    """投资组合接口协议 (Portfolio Interface Protocol)

    这个Protocol定义了所有投资组合管理系统必须实现的核心接口，提供类型安全的
    编译时检查和运行时验证能力。

    主要功能：
    1. 组件管理 - 管理策略、风控、分析器、选股器、仓位管理器等组件
    2. 事件处理 - 处理价格更新、信号生成、订单生命周期等事件
    3. 信号处理 - 将策略信号转换为订单并执行
    4. 持仓管理 - 维护投资组合的持仓和资金状态
    5. 风险控制 - 应用风控规则和限制
    6. 性能跟踪 - 计算和记录投资组合表现
    7. 批处理支持 - 支持信号批处理和优化执行
    8. 时间管理 - T+1机制和时间推进

    使用示例：
        class MyPortfolio(BasePortfolio, PortfolioMixin):
            def process_signals(self, signals: List[Signal]) -> List[Order]:
                # 实现信号处理逻辑
                return orders

            def get_portfolio_info(self) -> Dict[str, Any]:
                # 返回投资组合信息
                return info

    类型检查：
        def validate_portfolio(portfolio: IPortfolio) -> bool:
            return isinstance(portfolio, IPortfolio)
    """

    # ========== 基础属性 ==========

    @property
    def name(self) -> str:
        """
        投资组合名称 (Portfolio Name)

        Returns:
            str: 投资组合的唯一名称标识

        Note:
            - 名称应该在系统内保持唯一性
            - 建议使用描述性名称，便于识别管理
        """
        ...

    @name.setter
    def name(self, value: str) -> None:
        ...

    @property
    def portfolio_id(self) -> str:
        """
        投资组合ID (Portfolio ID)

        Returns:
            str: 投资组合的唯一标识符

        Note:
            - ID应该全局唯一
            - 用于数据库存储和检索
            - 不应随意更改
        """
        ...

    def set_portfolio_id(self, value: str) -> str:
        """
        设置投资组合ID (Set Portfolio ID)

        Args:
            value: 新的投资组合ID

        Returns:
            str: 设置后的投资组合ID
        """
        ...

    @property
    def cash(self) -> Decimal:
        """
        现金余额 (Cash Balance)

        Returns:
            Decimal: 当前现金余额

        Note:
            - 表示可用的现金总额
            - 不包括冻结资金
            - 使用Decimal保证精度
        """
        ...

    @property
    def frozen(self) -> Decimal:
        """
        冻结资金 (Frozen Cash)

        Returns:
            Decimal: 当前冻结的资金总额

        Note:
            - 包括订单冻结的资金
            - 不能用于其他交易
            - 使用Decimal保证精度
        """
        ...

    @property
    def worth(self) -> Decimal:
        """
        投资组合总价值 (Total Worth)

        Returns:
            Decimal: 投资组合总价值

        Note:
            - 现金 + 冻结资金 + 持仓市值
            - 使用Decimal保证精度
            - 应该实时更新
        """
        ...

    def update_worth(self) -> None:
        """
        更新投资组合总价值 (Update Total Worth)

        计算投资组合的总价值（现金 + 冻结资金 + 持仓市值）。

        计算公式：
            总价值 = 现金余额 + 冻结资金 + Σ(持仓数量 × 当前价格)

        Note:
            - 价格应该使用最新市场价
            - 计算应该实时更新
            - 应该考虑价格数据的时效性
        """
        ...

    @property
    def profit(self) -> Decimal:
        """
        投资组合盈亏 (Portfolio Profit)

        Returns:
            Decimal: 当前总盈亏

        Note:
            - 计算所有持仓的未实现盈亏
            - 不包括已实现盈亏
            - 使用Decimal保证精度
        """
        ...

    def update_profit(self) -> None:
        """
        更新投资组合盈亏 (Update Portfolio Profit)

        计算并更新投资组合的总盈亏。

        Note:
            - 遍历所有持仓计算盈亏
            - 应该实时更新
            - 使用标准盈亏计算方法
        """
        ...

    @property
    def fee(self) -> Decimal:
        """
        累计手续费 (Accumulated Fees)

        Returns:
            Decimal: 累计手续费总额

        Note:
            - 包括所有交易的费用
            - 使用Decimal保证精度
        """
        ...

    def add_fee(self, fee: Any) -> Decimal:
        """
        添加手续费 (Add Fee)

        记录新的交易手续费。

        Args:
            fee: 手续费金额

        Returns:
            Decimal: 更新后的累计手续费

        Note:
            - 手续费应该为正数
            - 使用Decimal保证精度
        """
        ...

    # ========== 组件管理 ==========

    @property
    def strategies(self) -> List[Any]:
        """
        策略列表 (Strategies List)

        Returns:
            List[BaseStrategy]: 策略列表

        Note:
            - 返回所有策略的引用
            - 策略顺序可能影响信号生成
            - 支持动态添加和移除策略
        """
        ...

    def add_strategy(self, strategy: Any) -> None:
        """
        添加策略 (Add Strategy)

        向投资组合添加交易策略，策略将生成交易信号。

        Args:
            strategy: 交易策略实例，必须实现IStrategy接口

        Note:
            - 策略名称应该在投资组合内保持唯一
            - 添加策略后应该触发相关初始化流程
            - 避免重复添加相同策略
        """
        ...

    @property
    def risk_managers(self) -> List[Any]:
        """
        风控管理器列表 (Risk Managers List)

        Returns:
            List[BaseRiskManagement]: 风控管理器列表

        Note:
            - 风控管理器按添加顺序执行
            - 支持多个风控管理器协同工作
            - 应该覆盖不同类型的风险
        """
        ...

    def add_risk_manager(self, risk_manager: Any) -> None:
        """
        添加风控管理器 (Add Risk Manager)

        向投资组合添加风险管理器，用于订单和风险控制。

        Args:
            risk_manager: 风控管理器实例，必须实现IRiskManagement接口

        Note:
            - 风控管理器按添加顺序执行
            - 可以添加多个不同类型的风控管理器
            - 风控管理器应该支持动态参数调整
        """
        ...

    @property
    def selector(self) -> Optional[Any]:
        """
        选股器 (Selector)

        Returns:
            Optional[BaseSelector]: 选股器实例，未设置时返回None

        Note:
            - 选股器负责筛选交易标的
            - 应该支持动态更新股票池
            - 选股结果影响策略执行范围
        """
        ...

    def bind_selector(self, selector: Any) -> None:
        """
        绑定选股器 (Bind Selector)

        向投资组合绑定选股器，用于选择交易标的。

        Args:
            selector: 选股器实例，必须实现BaseSelector接口

        Note:
            - 选股器负责筛选可交易的标的
            - 应该支持动态更新股票池
            - 选股结果应该考虑流动性等因素
        """
        ...

    @property
    def sizer(self) -> Optional[Any]:
        """
        仓位管理器 (Sizer)

        Returns:
            Optional[BaseSizer]: 仓位管理器实例，未设置时返回None

        Note:
            - 仓位管理器负责计算订单数量
            - 应该考虑风险和资金约束
            - 支持多种仓位管理策略
        """
        ...

    def bind_sizer(self, sizer: Any) -> None:
        """
        绑定仓位管理器 (Bind Sizer)

        向投资组合绑定仓位管理器，用于计算订单数量。

        Args:
            sizer: 仓位管理器实例，必须实现BaseSizer接口

        Note:
            - 仓位管理器负责将信号转换为具体订单数量
            - 应该考虑风险限制和资金约束
            - 支持多种仓位管理策略
        """
        ...

    @property
    def analyzers(self) -> Dict[str, Any]:
        """
        分析器字典 (Analyzers Dictionary)

        Returns:
            Dict[str, BaseAnalyzer]: 分析器字典，键为分析器名称

        Note:
            - 返回所有分析器的引用
            - 分析器通过钩子机制参与回测过程
            - 支持动态添加和移除分析器
        """
        ...

    def add_analyzer(self, analyzer: Any) -> None:
        """
        添加分析器 (Add Analyzer)

        向投资组合添加性能分析器，用于计算和记录各种指标。

        Args:
            analyzer: 分析器实例，必须实现BaseAnalyzer接口

        Note:
            - 分析器通过钩子机制参与回测过程
            - 支持多阶段分析器激活和记录
            - 分析器结果用于性能评估和优化
        """
        ...

    def analyzer(self, key: str) -> Any:
        """
        获取分析器 (Get Analyzer)

        根据名称获取指定的分析器。

        Args:
            key: 分析器名称

        Returns:
            BaseAnalyzer: 分析器实例，不存在时返回None

        Note:
            - 用于访问特定分析器
            - 应该检查分析器是否存在
        """
        ...

    # ========== 持仓管理 ==========

    @property
    def positions(self) -> Dict[str, Any]:
        """
        持仓字典 (Positions Dictionary)

        Returns:
            Dict[str, Position]: 持仓字典，键为股票代码

        Note:
            - 返回所有持仓的引用
            - 修改持仓会影响投资组合状态
            - 应该谨慎处理持仓数据
        """
        ...

    def get_position(self, code: str) -> Optional[Any]:
        """
        获取指定标的的持仓 (Get Position)

        查询指定标的的当前持仓情况。

        Args:
            code: 交易标的代码

        Returns:
            Optional[Position]: 持仓信息，无持仓时返回None

        Note:
            - 应该区分无持仓和零持仓的情况
            - 持仓信息应该包含完整的成本和收益数据
            - 查询性能应该考虑投资组合规模
        """
        ...

    def add_position(self, position: Any) -> None:
        """
        添加持仓 (Add Position)

        向投资组合添加新的持仓或更新现有持仓。

        Args:
            position: 持仓对象

        Note:
            - 如果持仓已存在，会增加数量
            - 如果持仓不存在，会创建新持仓
            - 应该验证持仓数据的有效性
        """
        ...

    def update_position(self, symbol: str, quantity: float, price: float) -> None:
        """
        更新持仓 (Update Position)

        根据交易执行结果更新投资组合持仓。

        Args:
            symbol: 交易标的代码
            quantity: 数量变化（正数为买入，负数为卖出）
            price: 成交价格

        典型操作：
            1. 验证参数有效性
            2. 更新或创建持仓记录
            3. 调整现金余额
            4. 计算盈亏
            5. 更新相关指标
            6. 触发分析器钩子

        Note:
            - 价格更新应该实时反映到持仓价值
            - 现金调整应该考虑交易费用
            - 持仓变化应该触发相关风险检查
        """
        ...

    def clean_positions(self) -> None:
        """
        清理空持仓 (Clean Empty Positions)

        移除数量和冻结量都为0的持仓记录。

        Note:
            - 定期清理可以提高性能
            - 避免空持仓占用内存
            - 应该在交易后定期调用
        """
        ...

    # ========== 资金管理 ==========

    def add_cash(self, money: Any) -> Decimal:
        """
        添加资金 (Add Cash)

        向投资组合添加资金。

        Args:
            money: 要添加的金额

        Returns:
            Decimal: 添加后的现金余额

        Note:
            - 金额应该为正数
            - 使用Decimal保证精度
            - 应该更新总价值
        """
        ...

    def freeze(self, money: Any) -> bool:
        """
        冻结资金 (Freeze Cash)

        冻结指定金额的现金，用于订单保证金。

        Args:
            money: 冻结金额

        Returns:
            bool: 冻结成功返回True，资金不足返回False

        典型操作：
            1. 检查可用资金是否充足
            2. 从可用资金中扣除冻结金额
            3. 增加冻结资金余额
            4. 更新投资组合状态

        Note:
            - 冻结资金不能用于其他交易
            - 应该防止重复冻结
            - 冻结操作应该原子化
        """
        ...

    def unfreeze(self, money: Any) -> Decimal:
        """
        解冻资金 (Unfreeze Cash)

        解冻指定金额的现金，恢复可用性。

        Args:
            money: 解冻金额

        Returns:
            Decimal: 实际解冻的金额

        典型操作：
            1. 检查冻结资金余额
            2. 从冻结资金中扣除解冻金额
            3. 增加可用现金余额
            4. 更新投资组合状态

        Note:
            - 解冻金额不应超过冻结余额
            - 应该支持部分解冻
            - 解冻后资金立即可用
        """
        ...

    # ========== 事件处理 ==========

    def on_price_received(self, event: Any) -> None:
        """
        处理价格更新事件 (Handle Price Update Event)

        当收到新的价格数据时调用，更新持仓价值并生成交易信号。

        Args:
            event: 价格更新事件

        典型处理流程：
            1. 验证事件有效性和时间顺序
            2. 更新相关持仓的市场价格
            3. 重新计算投资组合总价值
            4. 调用策略生成交易信号
            5. 调用风控生成风控信号
            6. 投递信号事件到引擎

        Note:
            - 这是事件驱动架构的核心入口点
            - 应该处理未来数据的防护
            - 价格更新应该实时反映到持仓价值
        """
        ...

    def process_price_update(self, event: Any) -> None:
        """
        处理价格更新（通用方法） (Process Price Update - Generic)

        价格事件通用处理：更新持仓价格与组合指标，生成策略/风控信号。

        Args:
            event: 价格更新事件

        Note:
            - T+1 组合可继续使用自有 on_price_received 逻辑
            - 本方法主要给 Live/通用场景复用
            - 包含完整的信号生成流程
        """
        ...

    def on_signal(self, event: Any) -> Optional[Any]:
        """
        处理信号生成事件 (Handle Signal Generation Event)

        当收到交易信号时调用，将信号转换为订单并执行。

        Args:
            event: 信号生成事件

        Returns:
            Optional[Order]: 生成的订单，如果信号被拒绝则返回None

        典型处理流程：
            1. 验证信号有效性和时间顺序
            2. 通过仓位管理器计算订单数量
            3. 依次通过风控管理器调整订单
            4. 冻结相应资金或持仓
            5. 提交订单到执行引擎

        Note:
            - T+1组合需要延迟处理信号
            - 应该支持批处理模式优化
            - 订单生成需要考虑资金和仓位限制
        """
        ...

    def generate_strategy_signals(self, event: Any) -> List[Any]:
        """
        生成策略信号 (Generate Strategy Signals)

        遍历所有策略，调用策略的cal方法，返回信号列表。

        Args:
            event: 市场事件

        Returns:
            List[Signal]: 策略生成的信号列表

        Note:
            - 包含防御性处理，确保返回列表
            - 自动包装单个Signal对象
            - 记录策略执行错误
        """
        ...

    def generate_risk_signals(self, event: Any) -> List[Any]:
        """
        生成风控信号 (Generate Risk Signals)

        遍历所有风控管理器，调用generate_signals方法，返回信号列表。

        Args:
            event: 市场事件

        Returns:
            List[Signal]: 风控生成的信号列表

        Note:
            - 包含防御性处理，确保返回列表
            - 自动包装单个Signal对象
            - 记录风控执行错误
        """
        ...

    def on_order_ack(self, event: Any) -> None:
        """
        处理订单确认事件 (Handle Order Acknowledgment Event)

        当订单被券商确认时调用，更新订单状态。

        Args:
            event: 订单确认事件

        典型处理流程：
            1. 验证订单确认信息
            2. 更新订单状态为已确认
            3. 激活分析器钩子
            4. 记录订单确认日志

        Note:
            - 订单确认表示券商已接受订单
            - 此时订单已进入执行队列
            - 应该跟踪订单生命周期
        """
        ...

    def on_order_partially_filled(self, event: Any) -> None:
        """
        处理订单部分成交事件 (Handle Order Partially Filled Event)

        当订单部分成交时调用，更新持仓和资金状态。

        Args:
            event: 订单部分成交事件

        典型处理流程：
            1. 验证成交信息有效性
            2. 更新或创建持仓记录
            3. 调整冻结资金/持仓
            4. 计算和扣除手续费
            5. 更新投资组合价值
            6. 激活分析器钩子

        Note:
            - 部分成交可能发生多次
            - 应该正确处理买入和卖出的区别
            - 需要精确计算成本和费用
        """
        ...

    def on_order_rejected(self, event: Any) -> None:
        """
        处理订单拒绝事件 (Handle Order Rejected Event)

        当订单被券商拒绝时调用，处理拒绝原因。

        Args:
            event: 订单拒绝事件

        典型处理流程：
            1. 记录订单拒绝信息
            2. 分析拒绝原因
            3. 释放冻结资金/持仓
            4. 激活分析器钩子
            5. 更新订单状态

        Note:
            - 订单拒绝通常表示交易失败
            - 应该记录详细的拒绝原因
            - 可能需要调整后续交易策略
        """
        ...

    def on_order_expired(self, event: Any) -> None:
        """
        处理订单过期事件 (Handle Order Expired Event)

        当订单因超时而过期时调用，清理相关状态。

        Args:
            event: 订单过期事件

        典型处理流程：
            1. 验证订单过期信息
            2. 释放过期部分的冻结资源
            3. 激活分析器钩子
            4. 更新订单状态

        Note:
            - 订单过期通常发生在有效期末
            - 可能部分已成交，部分过期
            - 应该区别于主动取消
        """
        ...

    def on_order_cancel_ack(self, event: Any) -> None:
        """
        处理订单取消确认事件 (Handle Order Cancel Acknowledgment Event)

        当订单取消被确认时调用，释放冻结资源。

        Args:
            event: 订单取消确认事件

        典型处理流程：
            1. 验证取消确认信息
            2. 释放冻结资金/持仓
            3. 更新订单状态
            4. 激活分析器钩子
            5. 记录取消操作日志

        Note:
            - 取消确认表示券商已成功取消订单
            - 应该完整释放冻结的资源
            - 可能需要调整投资组合状态
        """
        ...

    # ========== 时间管理 ==========

    def advance_time(self, time: Any) -> bool:
        """
        时间推进 (Advance Time)

        推进投资组合的时间状态，用于T+1处理和时间序列分析。

        Args:
            time: 新的时间点

        Returns:
            bool: 时间推进成功返回True

        典型操作：
            1. 更新投资组合当前时间
            2. 推进所有组件的时间状态
            3. 处理T+1延迟的信号
            4. 更新选股器感兴趣的标的
            5. 触发时间相关的事件

        Note:
            - T+1组合在此处理延迟信号
            - 应该同步所有组件的时间状态
            - 时间推进应该保持一致性
        """
        ...

    def is_event_from_future(self, event: Any) -> bool:
        """
        检查事件是否来自未来 (Check if Event is from Future)

        防止处理未来时间的价格数据。

        Args:
            event: 待检查的事件

        Returns:
            bool: 事件来自未来返回True

        Note:
            - 这是防止未来数据污染的重要机制
            - 应该记录未来数据事件
            - 可以用于数据质量监控
        """
        ...

    # ========== 批处理支持 ==========

    def enable_batch_processing(self, batch_processor: Any) -> None:
        """
        启用批处理模式 (Enable Batch Processing)

        启用信号批处理模式，优化交易执行效率。

        Args:
            batch_processor: 批处理器实例

        典型操作：
            1. 验证批处理器接口
            2. 保存原始信号处理方法
            3. 配置批处理器参数
            4. 启用批处理模式

        Note:
            - 批处理可以提高执行效率
            - 应该支持不同的时间窗口
            - 批处理应该保持交易逻辑一致性
        """
        ...

    def disable_batch_processing(self) -> None:
        """
        禁用批处理模式 (Disable Batch Processing)

        禁用批处理模式，恢复到逐个信号处理。

        典型操作：
            1. 停用批处理器
            2. 恢复原始信号处理方法
            3. 清理批处理状态

        Note:
            - 禁用后立即使用传统模式
            - 应该清理所有批处理相关状态
            - 不影响已处理的信号
        """
        ...

    def force_process_pending_batches(self) -> List[Any]:
        """
        强制处理待处理批次 (Force Process Pending Batches)

        强制处理所有待处理的批次，通常用于回测结束。

        Returns:
            List[Order]: 生成的订单列表

        典型操作：
            1. 检查待处理批次
            2. 强制处理所有批次
            3. 提交生成的订单
            4. 清理批处理状态

        Note:
            - 主要用于回测结束时清理
            - 应该处理所有剩余信号
            - 生成的订单应该经过完整的风控流程
        """
        ...

    def get_batch_processing_stats(self) -> Dict[str, Any]:
        """
        获取批处理统计信息 (Get Batch Processing Statistics)

        返回批处理系统的统计信息。

        Returns:
            Dict[str, Any]: 批处理统计信息

        Note:
            - 用于监控批处理性能
            - 应该包含关键指标
            - 可以用于调试和优化
        """
        ...

    # ========== 工具方法 ==========

    def is_all_set(self) -> bool:
        """
        检查组件是否完整配置 (Check if All Components are Set)

        验证投资组合的所有必要组件是否已正确配置。

        Returns:
            bool: 所有组件配置完整返回True

        检查项目：
            - 策略组件是否存在
            - 选股器是否已绑定
            - 仓位管理器是否已绑定
            - 风控管理器是否已配置（可选）

        Note:
            - 应该在交易开始前检查
            - 缺少必要组件应该记录警告
            - 检查结果应该影响交易执行
        """
        ...

    def get_info(self) -> Dict[str, Any]:
        """
        获取投资组合信息 (Get Portfolio Information)

        返回投资组合的完整状态信息，用于监控和分析。

        Returns:
            Dict[str, Any]: 投资组合信息字典

        Note:
            - 信息应该实时更新
            - 计算指标应该使用标准方法
            - 返回数据应该适合序列化
        """
        ...

    @property
    def interested(self) -> List[str]:
        """
        感兴趣的标的列表 (Interested Symbols List)

        Returns:
            List[str]: 投资组合感兴趣的标的代码列表

        Note:
            - 由选股器生成
            - 用于数据订阅和过滤
            - 应该定期更新
        """
        ...

    # ========== 事件发布 ==========

    def put(self, event: Any) -> None:
        """
        发布事件 (Publish Event)

        将事件发布到事件引擎。

        Args:
            event: 要发布的事件

        Note:
            - 用于向引擎回传事件
            - 应该检查事件发布器是否已绑定
            - 是事件驱动架构的重要组成部分
        """
        ...

    def set_event_publisher(self, publisher: Any) -> None:
        """
        设置事件发布器 (Set Event Publisher)

        注入事件发布器（通常是engine.put），用于将事件回传到引擎。

        Args:
            publisher: 事件发布器

        Note:
            - 通常在组合初始化时设置
            - 应该验证发布器的有效性
            - 是组合与引擎通信的桥梁
        """
        ...

    def bind_data_feeder(self, feeder: Any) -> None:
        """
        绑定数据源 (Bind Data Feeder)

        为组合的所有组件绑定数据源。

        Args:
            feeder: 数据源实例

        Note:
            - 策略、选股器、仓位管理器都需要数据
            - 应该统一数据源接口
            - 避免重复绑定
        """
        ...

    def bind_engine(self, engine: Any) -> None:
        """
        绑定引擎 (Bind Engine)

        将投资组合绑定到交易引擎。

        Args:
            engine: 交易引擎实例

        Note:
            - 引擎是组合的执行环境
            - 应该同步所有组件的引擎绑定
            - 确保组件间的协调工作
        """
        ...