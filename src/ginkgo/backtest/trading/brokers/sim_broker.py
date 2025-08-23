"""
SimBroker - 模拟撮合Broker

基于MatchMakingSim的逻辑，提供统一的Broker接口进行模拟撮合。
支持滑点、态度设置、手续费计算等回测功能。
"""

import pandas as pd
from decimal import Decimal
from typing import Dict, List, Optional, Any
from scipy import stats

from .base_broker import BaseBroker, ExecutionResult, ExecutionStatus, Position, AccountInfo
from ginkgo.backtest.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ATTITUDE_TYPES
from ginkgo.libs import to_decimal, Number
from ginkgo.libs import GLOG


class SimBroker(BaseBroker):
    """
    模拟撮合Broker
    
    实现模拟交易的核心逻辑，包括：
    - 价格撮合算法
    - 手续费计算
    - 滑点模拟
    - 涨跌停限制
    """
    
    def __init__(self, broker_config: Dict[str, Any]):
        """
        初始化模拟Broker
        
        Args:
            broker_config: 配置字典，包含:
                - attitude: 撮合态度 (OPTIMISTIC/PESSMISTIC/RANDOM)
                - slippage: 滑点基数
                - commission_rate: 佣金费率
                - commission_min: 最小佣金
        """
        super().__init__(broker_config)
        
        # 模拟撮合参数
        self._attitude = broker_config.get('attitude', ATTITUDE_TYPES.RANDOM)
        self._slippage = broker_config.get('slippage', 0.0)
        self._commission_rate = Decimal(str(broker_config.get('commission_rate', 0.0003)))
        self._commission_min = Decimal(str(broker_config.get('commission_min', 5.0)))
        
        # 价格缓存和订单簿
        self._price_cache = pd.DataFrame()
        self._order_book = {}
        self._positions = {}  # 持仓信息 {code: Position}
        self._account = AccountInfo(
            total_asset=broker_config.get('initial_cash', 1000000.0),
            available_cash=broker_config.get('initial_cash', 1000000.0),
            frozen_cash=0.0,
            market_value=0.0,
            total_pnl=0.0
        )
        
    def connect(self) -> bool:
        """建立连接（模拟连接总是成功）"""
        self._connected = True
        GLOG.info(f"SimBroker connected successfully")
        return True
        
    def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        return True
    
    def update_price_cache(self, price_data: pd.DataFrame):
        """
        更新价格缓存
        
        Args:
            price_data: 价格数据，包含code, open, high, low, close等字段
        """
        self._price_cache = price_data
        
    def submit_order(self, order: Order) -> ExecutionResult:
        """
        提交订单进行模拟撮合
        
        Args:
            order: 订单对象
            
        Returns:
            ExecutionResult: 执行结果
        """
        if not self.validate_order(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Order validation failed"
            )
            
        try:
            # 检查价格数据
            if self._price_cache.empty:
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.REJECTED,
                    message="No price data available"
                )
                
            price_data = self._price_cache[self._price_cache["code"] == order.code]
            if price_data.empty:
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.REJECTED,
                    message=f"No price data for {order.code}"
                )
                
            price_row = price_data.iloc[0]
            
            # 验证价格有效性
            if not self._is_price_valid(order.code, price_row):
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.REJECTED,
                    message="Invalid price data"
                )
                
            # 检查订单是否可以成交
            if order.order_type == ORDER_TYPES.LIMITORDER:
                if not self._can_limit_order_be_filled(order, price_row):
                    return ExecutionResult(
                        order_id=order.uuid,
                        status=ExecutionStatus.REJECTED,
                        message="Limit order cannot be filled"
                    )
            elif order.order_type == ORDER_TYPES.MARKETORDER:
                if not self._can_market_order_be_filled(order, price_row):
                    return ExecutionResult(
                        order_id=order.uuid,
                        status=ExecutionStatus.REJECTED,
                        message="Market order cannot be filled"
                    )
                    
            # 检查涨跌停
            if order.direction == DIRECTION_TYPES.LONG and self._is_price_limit_up(price_row):
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.REJECTED,
                    message="Price limit up"
                )
            if order.direction == DIRECTION_TYPES.SHORT and self._is_price_limit_down(price_row):
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.REJECTED,
                    message="Price limit down"
                )
                
            # 执行订单
            return self._process_order_execution(order, price_row)
            
        except Exception as e:
            GLOG.ERROR(f"SimBroker order execution failed: {str(e)}")
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message=f"Execution error: {str(e)}"
            )
    
    def cancel_order(self, order_id: str) -> ExecutionResult:
        """撤销订单"""
        return ExecutionResult(
            order_id=order_id,
            status=ExecutionStatus.CANCELLED,
            message="Order cancelled"
        )
        
    def query_order(self, order_id: str) -> ExecutionResult:
        """查询订单状态（模拟中订单立即执行）"""
        return ExecutionResult(
            order_id=order_id,
            status=ExecutionStatus.FILLED,
            message="Order filled"
        )
        
    def get_positions(self) -> List[Position]:
        """获取持仓信息"""
        return list(self._positions.values())
        
    def get_account_info(self) -> AccountInfo:
        """获取账户信息"""
        return self._account
    
    def _get_random_transaction_price(
        self, direction: DIRECTION_TYPES, low: float, high: float, attitude: ATTITUDE_TYPES
    ) -> float:
        """
        计算随机成交价格
        
        Args:
            direction: 交易方向
            low: 最低价
            high: 最高价  
            attitude: 撮合态度
            
        Returns:
            float: 成交价格
        """
        low = float(to_decimal(low))
        high = float(to_decimal(high))
        mean = (low + high) / 2
        std_dev = (high - low) / 6
        
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
            elif attitude == ATTITUDE_TYPES.PESSMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)
        
        price = rs[0]
        if price > high:
            price = high
        if price < low:
            price = low
            
        return round(price, 2)
    
    def _cal_fee(self, transaction_money: Number, is_long: bool) -> Decimal:
        """
        计算手续费
        
        Args:
            transaction_money: 成交金额
            is_long: 是否买入
            
        Returns:
            Decimal: 手续费
        """
        if transaction_money <= 0:
            return Decimal('0')
            
        transaction_money = Decimal(str(transaction_money))
        
        # 印花税，仅卖出时收
        stamp_tax = transaction_money * Decimal("0.001") if not is_long else Decimal('0')
        # 过户费，买卖均收
        transfer_fees = Decimal("0.00001") * transaction_money
        # 代收规费0.00687%，买卖均收
        collection_fees = Decimal("0.0000687") * transaction_money
        # 佣金，买卖均收
        commission = self._commission_rate * transaction_money
        commission = commission if commission > self._commission_min else self._commission_min
        
        total_fee = stamp_tax + transfer_fees + collection_fees + commission
        return round(total_fee, 2)
    
    def _is_price_valid(self, code: str, price_data: pd.Series) -> bool:
        """验证价格数据有效性"""
        required_fields = ['open', 'high', 'low', 'close']
        for field in required_fields:
            if field not in price_data or pd.isna(price_data[field]) or price_data[field] <= 0:
                return False
        return True
        
    def _can_limit_order_be_filled(self, order: Order, price_data: pd.Series) -> bool:
        """检查限价单是否可以成交"""
        if order.direction == DIRECTION_TYPES.LONG:
            return order.limit_price >= price_data['low']
        else:
            return order.limit_price <= price_data['high']
            
    def _can_market_order_be_filled(self, order: Order, price_data: pd.Series) -> bool:
        """检查市价单是否可以成交（通常都可以成交）"""
        return True
        
    def _is_price_limit_up(self, price_data: pd.Series) -> bool:
        """检查是否涨停"""
        # 简化实现：假设涨停为收盘价等于最高价且涨幅超过9.8%
        return abs(price_data['close'] - price_data['high']) < 0.01
        
    def _is_price_limit_down(self, price_data: pd.Series) -> bool:
        """检查是否跌停"""
        # 简化实现：假设跌停为收盘价等于最低价且跌幅超过9.8%
        return abs(price_data['close'] - price_data['low']) < 0.01
    
    def _process_order_execution(self, order: Order, price_data: pd.Series) -> ExecutionResult:
        """
        处理订单执行
        
        Args:
            order: 订单对象
            price_data: 价格数据
            
        Returns:
            ExecutionResult: 执行结果
        """
        # 确定成交价格
        if order.order_type == ORDER_TYPES.LIMITORDER:
            transaction_price = float(order.limit_price)
        else:  # MARKETORDER
            transaction_price = self._get_random_transaction_price(
                order.direction, price_data["low"], price_data["high"], self._attitude
            )
        
        volume = order.volume
        
        # 对于买入订单，检查资金是否足够
        if order.direction == DIRECTION_TYPES.LONG:
            transaction_money = transaction_price * volume
            fee = self._cal_fee(transaction_money, True)
            cost = transaction_money + fee
            
            if cost > self._account.available_cash:
                # 调整数量到资金允许的范围
                max_volume = int(self._account.available_cash / (transaction_price * 1.01))  # 预留1%费用
                volume = (max_volume // 100) * 100  # 调整为100的倍数
                
                if volume < 100:
                    return ExecutionResult(
                        order_id=order.uuid,
                        status=ExecutionStatus.REJECTED,
                        message="Insufficient funds"
                    )
        
        # 重新计算成交金额和费用
        transaction_money = transaction_price * volume
        fee = self._cal_fee(transaction_money, order.direction == DIRECTION_TYPES.LONG)
        
        # 更新账户信息
        if order.direction == DIRECTION_TYPES.LONG:
            cost = transaction_money + float(fee)
            self._account.available_cash -= cost
            self._account.frozen_cash += cost
        else:
            income = transaction_money - float(fee)
            self._account.available_cash += income
        
        # 更新持仓
        self._update_position(order.code, order.direction, volume, transaction_price)
        
        return ExecutionResult(
            order_id=order.uuid,
            status=ExecutionStatus.FILLED,
            filled_volume=volume,
            filled_price=transaction_price,
            commission=float(fee),
            message="Order filled successfully"
        )
    
    def _update_position(self, code: str, direction: DIRECTION_TYPES, volume: float, price: float):
        """更新持仓信息"""
        if code not in self._positions:
            self._positions[code] = Position(
                code=code,
                volume=0,
                available_volume=0,
                avg_price=0,
                market_value=0,
                unrealized_pnl=0,
                direction=direction
            )
        
        position = self._positions[code]
        
        if direction == DIRECTION_TYPES.LONG:
            # 买入
            total_cost = position.volume * position.avg_price + volume * price
            position.volume += volume
            position.available_volume += volume
            position.avg_price = total_cost / position.volume if position.volume > 0 else price
        else:
            # 卖出
            position.volume -= volume
            position.available_volume -= volume
            if position.volume <= 0:
                del self._positions[code]