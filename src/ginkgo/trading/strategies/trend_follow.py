import datetime
from decimal import Decimal
import pandas as pd
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class StrategyTrendFollow(BaseStrategy):
    """
    趋势跟踪策略
    
    基于移动平均线和价格动量的趋势跟踪策略。
    使用快慢均线交叉和价格动量确认来产生交易信号。
    """
    
    __abstract__ = False

    def __init__(
        self,
        name: str = "TrendFollow",
        fast_ma_period: int = 10,
        slow_ma_period: int = 30,
        momentum_period: int = 5,
        loss_limit: float = 8.0,
        profit_target: float = 20.0,
        *args,
        **kwargs,
    ):
        super(StrategyTrendFollow, self).__init__(name, *args, **kwargs)
        self._fast_ma_period = fast_ma_period
        self._slow_ma_period = slow_ma_period
        self._momentum_period = momentum_period
        self._loss_limit = Decimal(str(loss_limit / 100))  # 转换为小数
        self._profit_target = Decimal(str(profit_target / 100))

    def _calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算移动平均线
        """
        df = df.copy()
        df['fast_ma'] = df['close'].rolling(window=self._fast_ma_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self._slow_ma_period).mean()
        df['momentum'] = df['close'].pct_change(periods=self._momentum_period)
        return df

    def _generate_signal(
        self, portfolio_info, code: str, direction: DIRECTION_TYPES, reason: str
    ) -> Signal:
        """
        生成交易信号
        """
        self.log("INFO", f"Generate {direction.value} signal for {code} from {self.name}")
        return Signal(
            portfolio_id=portfolio_info["uuid"],
            engine_id=self.engine_id,
            timestamp=portfolio_info["now"],
            code=code,
            direction=direction,
            reason=reason,
            source=SOURCE_TYPES.STRATEGY,
        )

    def _check_position_risk(self, portfolio_info, code: str, current_price: float) -> bool:
        """
        检查持仓风险，决定是否止损
        """
        if code not in portfolio_info["positions"]:
            return False
            
        position = portfolio_info["positions"][code]
        cost = position.cost
        price = position.price
        ratio = Decimal(str(price)) / Decimal(str(cost))
        
        # 止损检查
        if ratio <= (Decimal('1') - self._loss_limit):
            self.log("INFO", f"Stop loss triggered for {code}: cost={cost}, price={price}, ratio={ratio}")
            return True
            
        # 止盈检查
        if ratio >= (Decimal('1') + self._profit_target):
            self.log("INFO", f"Take profit triggered for {code}: cost={cost}, price={price}, ratio={ratio}")
            return True
            
        return False

    def cal(self, portfolio_info, event, *args, **kwargs):
        super(StrategyTrendFollow, self).cal(portfolio_info, event)
        
        # 获取历史数据
        date_start = self.business_timestamp - datetime.timedelta(days=(self._slow_ma_period + 10))
        df = get_bars(event.code, date_start, self.business_timestamp, as_dataframe=True)

        if df.shape[0] < self._slow_ma_period + 5:
            return []

        # 计算技术指标
        df = self._calculate_moving_averages(df)
        
        # 获取最新的指标值
        current_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        current_price = float(current_row['close'])
        
        # 检查止损
        if self._check_position_risk(portfolio_info, event.code, current_price):
            return [self._generate_signal(
                portfolio_info, event.code, DIRECTION_TYPES.SHORT, "Stop Loss/Take Profit"
            )]
        
        has_position = event.code in portfolio_info["positions"]
        
        # 交易信号逻辑
        signals = []
        
        # 金叉买入信号
        if (prev_row['fast_ma'] <= prev_row['slow_ma'] and 
            current_row['fast_ma'] > current_row['slow_ma'] and
            current_row['momentum'] > 0 and
            not has_position):
            
            signals.append(self._generate_signal(
                portfolio_info, event.code, DIRECTION_TYPES.LONG, "Golden Cross"
            ))
        
        # 死叉卖出信号
        elif (prev_row['fast_ma'] >= prev_row['slow_ma'] and 
              current_row['fast_ma'] < current_row['slow_ma'] and
              has_position):
            
            signals.append(self._generate_signal(
                portfolio_info, event.code, DIRECTION_TYPES.SHORT, "Death Cross"
            ))
        
        # 趋势强度确认
        elif not has_position and current_row['momentum'] > 0.05:  # 5%动量
            # 检查是否处于上升趋势
            if (current_row['fast_ma'] > current_row['slow_ma'] and
                current_row['close'] > current_row['fast_ma']):
                
                signals.append(self._generate_signal(
                    portfolio_info, event.code, DIRECTION_TYPES.LONG, "Momentum Confirmation"
                ))
        
        return signals
