"""
SimBroker - 模拟撮合Broker

基于MatchMakingSim的逻辑，提供统一的Broker接口进行模拟撮合。
支持滑点、态度设置、手续费计算等回测功能。
"""

import pandas as pd
import random
from decimal import Decimal
from typing import Dict, List, Optional, Any
from scipy import stats

from ginkgo.trading.brokers.base_broker import (
    BaseBroker,
    ExecutionResult,
    ExecutionStatus,
    AccountInfo,
    BrokerCapabilities,
)
from ginkgo.trading.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ATTITUDE_TYPES
from ginkgo.libs import to_decimal, Number
from ginkgo.libs import GLOG


class SimBroker(BaseBroker):
    """
    模拟撮合Broker

    基于MatchMakingSim的逻辑，提供统一的Broker接口进行模拟撮合。
    支持滑点、态度设置、手续费计算等回测功能。

    核心特点：
    - 同步执行：立即返回最终状态（FILLED/CANCELLED）
    - 模拟撮合：基于随机价格和滑点模型
    - 完整验证：订单验证、资金检查、价格限制
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化SimBroker

        Args:
            config: 配置字典，包含：
                - attitude: 撮合态度 (OPTIMISTIC/PESSIMISTIC/RANDOM)
                - commission_rate: 手续费率 (默认0.0003)
                - commission_min: 最小手续费 (默认5)
                - slip_base: 滑点基数 (默认0.01)
        """
        super().__init__(config)

        # 模拟交易配置
        from ginkgo.enums import ATTITUDE_TYPES

        self._attitude = config.get("attitude", ATTITUDE_TYPES.RANDOM)
        self._commission_rate = Decimal(str(config.get("commission_rate", 0.0003)))
        self._commission_min = config.get("commission_min", 5)
        self._slip_base = config.get("slip_base", 0.01)
        # 回测同步成交流程开关（默认启用）：
        # - True: submit_order 同步返回最终结果
        # - False: 返回ACK并异步产生成交结果
        self._sync_fills: bool = bool(config.get("sync_fills", True))

        # 市场数据缓存
        self._current_market_data: Dict[str, pd.Series] = {}

        # Portfolio信息提供器（延迟绑定）
        self._portfolio_provider = None

    def _init_capabilities(self) -> BrokerCapabilities:
        """初始化SimBroker的能力描述"""
        caps = BrokerCapabilities()
        caps.execution_type = "sync"  # 同步执行
        caps.supports_streaming = False
        caps.supports_batch_ops = True  # 支持批量操作
        caps.supports_market_data = False
        caps.supports_positions = False
        caps.max_orders_per_second = 1000  # 模拟环境无限制
        caps.max_concurrent_orders = 1000
        caps.order_timeout_seconds = 0  # 立即执行
        caps.supported_order_types = ["MARKET", "LIMIT"]
        caps.supported_time_in_force = ["DAY", "GTC"]
        return caps

    def _detect_execution_mode(self) -> str:
        """
        SimBroker专用于回测模式

        Returns:
            str: 'backtest'
        """
        return "backtest"

    def bind_portfolio_provider(self, provider):
        """
        绑定Portfolio信息提供器

        Args:
            provider: Portfolio信息获取函数，通常是portfolio.get_info
        """
        self._portfolio_provider = provider

    # ============= 连接管理 =============
    async def connect(self) -> bool:
        """模拟连接（总是成功）"""
        self._connected = True
        from ginkgo.libs import GLOG
        GLOG.DEBUG(f"SimBroker connected successfully")
        return True

    async def disconnect(self) -> bool:
        """模拟断连"""
        self._connected = False
        from ginkgo.libs import GLOG
        GLOG.DEBUG(f"SimBroker disconnected")
        return True

    # ============= 订单管理 =============
    async def submit_order(self, order: "Order") -> ExecutionResult:
        """
        提交订单（T5语义）：返回ACK并异步产生成交结果

        Args:
            order: 订单对象

        Returns:
            ExecutionResult: 提交ACK结果（SUBMITTED）
        """
        if not self.is_connected:
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message="SimBroker not connected",
                execution_mode=self.execution_mode,
                requires_confirmation=False,
            )

        # 基础验证
        if not self.validate_order(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Order validation failed",
                execution_mode=self.execution_mode,
                requires_confirmation=False,
            )

        broker_order_id = f"SIM_{order.uuid[:8]}"

        # 同步/异步路径
        if self._sync_fills:
            # 直接同步撮合并返回最终状态（可能包含“同步分笔”）
            try:
                results = self._simulate_execution_core(order, broker_order_id)
                last: ExecutionResult = results[-1] if results else ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.FAILED,
                    broker_order_id=broker_order_id,
                    message="No execution result",
                    execution_mode=self.execution_mode,
                )
                for r in results:
                    self._update_order_status(r)
                return last
            except Exception as e:
                err = ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.FAILED,
                    broker_order_id=broker_order_id,
                    message=f"Sync fill error: {e}",
                    execution_mode=self.execution_mode,
                )
                self._update_order_status(err)
                return err
        else:
            # 旧路径：ACK + 异步成交
            ack = ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.SUBMITTED,
                broker_order_id=broker_order_id,
                message="Order accepted by SimBroker",
                execution_mode=self.execution_mode,
                requires_confirmation=False,
            )
            self._update_order_status(ack)

            # 启动异步成交流程
            import asyncio as _asyncio
            _asyncio.create_task(self._process_order_fills(order, broker_order_id))

            return ack

    async def _process_order_fills(self, order: "Order", broker_order_id: str):
        """异步处理成交，支持部分成交"""
        import asyncio as _asyncio
        try:
            await _asyncio.sleep(0.05)
            results = self._simulate_execution_core(order, broker_order_id)
            for idx, r in enumerate(results):
                if idx > 0:
                    await _asyncio.sleep(0.05)
                self._update_order_status(r)

        except Exception as e:
            err = ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                broker_order_id=broker_order_id,
                message=f"Async fill error: {e}",
                execution_mode=self.execution_mode,
            )
            self._update_order_status(err)

    async def cancel_order(self, order_id: str) -> ExecutionResult:
        """
        取消订单（模拟环境中订单立即执行，无法取消）

        Args:
            order_id: 订单ID

        Returns:
            ExecutionResult: 取消结果
        """
        # 检查订单是否存在于缓存中
        cached_result = self.get_cached_order_status(order_id)
        if cached_result and cached_result.is_final_status:
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.REJECTED,
                message="Cannot cancel already executed order in simulation",
            )

        return ExecutionResult(
            order_id=order_id, status=ExecutionStatus.CANCELED, message="Order cancelled in simulation"
        )

    async def query_order(self, order_id: str) -> ExecutionResult:
        """
        查询订单状态（模拟环境返回缓存状态）

        Args:
            order_id: 订单ID

        Returns:
            ExecutionResult: 订单状态
        """
        cached_result = self.get_cached_order_status(order_id)
        if cached_result:
            return cached_result

        return ExecutionResult(
            order_id=order_id, status=ExecutionStatus.FAILED, message="Order not found in simulation cache"
        )

    # ============= 账户管理 =============
    async def get_account_info(self) -> "AccountInfo":
        """
        获取真实Portfolio账户信息

        Returns:
            AccountInfo: 从Portfolio获取的真实账户信息
        """
        # 直接调用portfolio_provider获取真实状态
        portfolio_state = self._portfolio_provider()

        # 正确映射Portfolio字段到AccountInfo字段
        cash = portfolio_state.get("cash", 0.0)
        frozen = portfolio_state.get("frozen", 0.0)
        worth = portfolio_state.get("worth", 0.0)
        profit = portfolio_state.get("profit", 0.0)

        # 计算市值 = 总价值 - 现金 - 冻结资金
        market_value = max(0.0, worth - cash - frozen)

        return AccountInfo(
            total_asset=worth,  # Portfolio的worth对应总资产
            available_cash=cash,  # Portfolio的cash对应可用资金
            frozen_cash=frozen,  # Portfolio的frozen对应冻结资金
            market_value=market_value,  # 计算得出的持仓市值
            total_pnl=profit,  # Portfolio的profit对应总盈亏
        )

    async def get_positions(self) -> List["Position"]:
        """
        获取真实Portfolio持仓信息

        Returns:
            List[Position]: 从Portfolio获取的真实持仓列表
        """
        # 直接调用portfolio_provider获取真实持仓
        portfolio_state = self._portfolio_provider()
        return portfolio_state.get("positions", [])

    # ============= 核心模拟逻辑 =============
    async def _simulate_execution(self, order: "Order", market_data: pd.Series) -> ExecutionResult:
        """
        执行模拟撮合 - 从MatchMakingSim提取的核心逻辑

        Args:
            order: 订单对象
            market_data: 市场数据

        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 1. 价格验证
            if not self._is_price_valid(order.code, market_data):
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    message="Invalid price data",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False,
                )

            # 2. 订单类型检查
            if not self._can_order_be_filled(order, market_data):
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    message="Order cannot be filled at current price",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False,
                )

            # 3. 涨跌停检查
            if self._is_limit_blocked(order, market_data):
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    message="Price limit up/down",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False,
                )

            # 4. 计算成交价格（已包含滑点效应）
            transaction_price = self._calculate_transaction_price(order, market_data)

            # 5. 调整成交数量（资金检查）
            transaction_volume = self._adjust_volume_for_funds(order, transaction_price)
            if transaction_volume == 0:
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    message="Insufficient funds for execution",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False,
                )

            # 6. 计算费用
            transaction_money = transaction_price * transaction_volume
            fees = self._calculate_commission(transaction_money, order.direction == DIRECTION_TYPES.LONG)

            # 7. 创建执行结果
            result = ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FILLED,
                broker_order_id=f"SIM_{order.uuid[:8]}",
                filled_quantity=transaction_volume,
                filled_price=float(transaction_price),
                remaining_quantity=0.0,
                average_price=float(transaction_price),
                fees=float(fees),
                message="Simulated execution completed",
                execution_mode=self.execution_mode,
                requires_confirmation=False,
            )

            # 8. 更新缓存并触发回调
            self._update_order_status(result)

            return result

        except Exception as e:
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"Simulation execution error: {e}")
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message=f"Simulation error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=False,
            )

    # ============= 新增：同步撮合核心（回测同步路径与异步路径共用） =============
    def _simulate_execution_core(self, order: "Order", broker_order_id: str) -> List[ExecutionResult]:
        """
        同步模拟撮合核心逻辑：返回按顺序的 ExecutionResult 列表。
        可能为 [FILLED] 或 [PARTIALLY_FILLED, FILLED]
        """
        results: List[ExecutionResult] = []

        market_data = self._get_market_data(order.code)
        if market_data is None:
            results.append(
                ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.FAILED,
                    broker_order_id=broker_order_id,
                    message=f"No market data available for {order.code}",
                    execution_mode=self.execution_mode,
                )
            )
            return results

        if not self._is_price_valid(order.code, market_data):
            results.append(
                ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    broker_order_id=broker_order_id,
                    message="Invalid price data",
                    execution_mode=self.execution_mode,
                )
            )
            return results

        if not self._can_order_be_filled(order, market_data):
            results.append(
                ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    broker_order_id=broker_order_id,
                    message="Order cannot be filled at current price",
                    execution_mode=self.execution_mode,
                )
            )
            return results

        if self._is_limit_blocked(order, market_data):
            results.append(
                ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    broker_order_id=broker_order_id,
                    message="Price limit up/down",
                    execution_mode=self.execution_mode,
                )
            )
            return results

        price = self._calculate_transaction_price(order, market_data)
        volume = self._adjust_volume_for_funds(order, price)
        if volume == 0:
            results.append(
                ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.CANCELED,
                    broker_order_id=broker_order_id,
                    message="Insufficient funds for execution",
                    execution_mode=self.execution_mode,
                )
            )
            return results

        # 分笔策略（可选同原逻辑）
        do_partial = int(order.volume) >= 200
        if do_partial:
            first = int(min(order.volume // 2, volume))
            second = int(volume - first)
            if first > 0:
                results.append(
                    ExecutionResult(
                        order_id=order.uuid,
                        status=ExecutionStatus.PARTIALLY_FILLED,
                        broker_order_id=broker_order_id,
                        filled_quantity=float(first),
                        filled_price=float(price),
                        remaining_quantity=float(max(0, order.volume - first)),
                        average_price=float(price),
                        fees=float(self._calculate_commission(price * first, order.direction == DIRECTION_TYPES.LONG)),
                        message="Partial fill",
                        execution_mode=self.execution_mode,
                    )
                )
            if second > 0:
                results.append(
                    ExecutionResult(
                        order_id=order.uuid,
                        status=ExecutionStatus.FILLED,
                        broker_order_id=broker_order_id,
                        filled_quantity=float(second),
                        filled_price=float(price),
                        remaining_quantity=0.0,
                        average_price=float(price),
                        fees=float(self._calculate_commission(price * second, order.direction == DIRECTION_TYPES.LONG)),
                        message="Final fill",
                        execution_mode=self.execution_mode,
                    )
                )
        else:
            results.append(
                ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.FILLED,
                    broker_order_id=broker_order_id,
                    filled_quantity=float(volume),
                    filled_price=float(price),
                    remaining_quantity=0.0,
                    average_price=float(price),
                    fees=float(self._calculate_commission(price * volume, order.direction == DIRECTION_TYPES.LONG)),
                    message="Order filled",
                    execution_mode=self.execution_mode,
                )
            )

        return results

    def _calculate_transaction_price(self, order: "Order", market_data: pd.Series) -> Decimal:
        """
        计算成交价格 - 从MatchMakingSim.get_random_transaction_price()提取

        Args:
            order: 订单对象
            market_data: 市场数据

        Returns:
            Decimal: 成交价格
        """
        if hasattr(order, "order_type") and order.order_type == ORDER_TYPES.LIMITORDER:
            return to_decimal(order.limit_price)

        # 市价单使用随机价格模拟滑点
        return self._get_random_transaction_price(
            order.direction, market_data["low"], market_data["high"], self._attitude
        )

    def _get_random_transaction_price(self, direction: DIRECTION_TYPES, low: Number, high: Number, attitude) -> Decimal:
        """
        随机成交价格计算 - 直接从MatchMakingSim提取

        Args:
            direction: 买卖方向
            low: 最低价
            high: 最高价
            attitude: 撮合态度

        Returns:
            Decimal: 随机成交价格
        """
        low = float(to_decimal(low))
        high = float(to_decimal(high))
        mean = (low + high) / 2
        std_dev = (high - low) / 6

        from ginkgo.enums import ATTITUDE_TYPES
        from scipy import stats

        if attitude == ATTITUDE_TYPES.RANDOM:
            rs = stats.norm.rvs(loc=mean, scale=std_dev, size=1)
        else:
            skewness_right = mean
            skewness_left = -mean
            if attitude == ATTITUDE_TYPES.OPTIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
            elif attitude == ATTITUDE_TYPES.PESSIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)

        rs = max(low, min(high, rs[0]))  # 限制在合理范围内
        return to_decimal(round(rs, 2))

    def _calculate_commission(self, transaction_money: Number, is_long: bool) -> Decimal:
        """
        计算手续费（A股标准）

        Args:
            transaction_money: 交易金额
            is_long: 是否为买入

        Returns:
            Decimal: 手续费（包含佣金和印花税）
        """
        # 基础佣金（买卖均收）
        commission = to_decimal(transaction_money) * self._commission_rate
        commission = max(commission, to_decimal(self._commission_min))

        # 印花税（仅卖出收取）
        if not is_long:  # 卖出
            stamp_duty = to_decimal(transaction_money) * Decimal("0.001")  # 0.1%印花税
            commission += stamp_duty

        return commission

    def _adjust_volume_for_funds(self, order: "Order", price: Decimal) -> int:
        """
        根据资金调整成交数量

        Args:
            order: 订单对象
            price: 成交价格

        Returns:
            int: 调整后的成交数量
        """
        if order.direction == DIRECTION_TYPES.SHORT:
            return order.volume  # 卖出不需要资金检查

        # 买入需要检查资金充足性
        volume = order.volume
        while volume >= 100:  # 股票交易最小单位
            transaction_money = price * volume
            fees = self._calculate_commission(transaction_money, True)
            total_cost = transaction_money + fees

            if hasattr(order, "frozen") and total_cost <= order.frozen:
                return volume
            volume -= 100

        return 0  # 资金不足

    # ============= 辅助方法 =============
    def _get_market_data(self, code: str) -> Optional[pd.Series]:
        """
        获取市场数据（需要从外部设置）

        Args:
            code: 股票代码

        Returns:
            Optional[pd.Series]: 市场数据
        """
        return self._current_market_data.get(code)

    def set_market_data(self, code: str, market_data: pd.Series):
        """
        设置当前市场数据

        Args:
            code: 股票代码
            market_data: 市场数据
        """
        self._current_market_data[code] = market_data

    def _is_price_valid(self, code: str, price_data: pd.Series) -> bool:
        """价格有效性检查"""
        required_fields = ["open", "high", "low", "close", "volume"]
        return all(field in price_data.index for field in required_fields)

    def _can_order_be_filled(self, order: "Order", price_data: pd.Series) -> bool:
        """
        订单是否可以成交 - 基于价格位置和态度的概率成交机制

        Args:
            order: 订单对象
            price_data: 价格数据，包含low, high等字段

        Returns:
            bool: 是否可以成交
        """
        # 市价单总是可以成交
        if not (hasattr(order, "order_type") and order.order_type == ORDER_TYPES.LIMITORDER):
            return True

        limit_price = order.limit_price
        low_price = price_data["low"]
        high_price = price_data["high"]

        # 基本可行性检查：限价必须在当日价格区间内
        if order.direction == DIRECTION_TYPES.LONG:
            if limit_price < low_price:
                return False
        else:  # 卖出
            if limit_price > high_price:
                return False

        # 计算价格位置权重（0-1之间）
        price_range = high_price - low_price
        if price_range == 0:  # 防止除零
            position_weight = 0.8  # 无波动时给予较高概率
        else:
            if order.direction == DIRECTION_TYPES.LONG:  # 买单
                # 买单：越接近最低价，成交概率越高
                position_weight = 1.0 - (limit_price - low_price) / price_range
            else:  # 卖单
                # 卖单：越接近最高价，成交概率越高
                position_weight = (limit_price - low_price) / price_range

        # 基础成交概率：30%-85%范围
        base_probability = 0.3 + position_weight * 0.55

        # 态度调整：乐观增加概率，悲观减少概率
        if self._attitude == ATTITUDE_TYPES.OPTIMISTIC:
            final_probability = min(0.95, base_probability * 1.3)  # 乐观增加30%，上限95%
        elif self._attitude == ATTITUDE_TYPES.PESSIMISTIC:
            final_probability = max(0.15, base_probability * 0.7)  # 悲观减少30%，下限15%
        else:  # NEUTRAL
            final_probability = base_probability

        # 随机数决定是否成交
        return random.random() < final_probability  # 临时返回，待实现概率逻辑  # 市价单总是可以成交

    def _is_limit_blocked(self, order: "Order", price_data: pd.Series) -> bool:
        """检查是否因涨跌停无法成交"""
        # 这里可以添加涨跌停逻辑
        # 比如检查价格是否触及涨跌停板
        return False
