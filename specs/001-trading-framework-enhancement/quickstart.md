# Quick Start Guide: Trading Framework Enhancement

**Branch**: 001-trading-framework-enhancement | **Date**: 2025-01-18
**Purpose**: 快速开始指南 - 基于Protocol + Mixin架构的现代化量化交易框架

## Overview

本指南将帮助您快速上手基于Protocol + Mixin架构的现代化量化交易框架。通过清晰的业务语义和最优的架构设计，您可以快速构建功能强大的交易策略。

### 环境准备

#### 1. 安装依赖

```bash
# 激活虚拟环境
conda activate ginkgo
# 或
source venv/bin/activate

# 安装项目依赖
python ./install.py

# 启用调试模式（数据库操作必需）
ginkgo system config set --debug on
ginkgo status  # 确认DEBUG已启用
```

#### 2. 初始化数据库

```bash
# 初始化数据库表
ginkgo data init

# 更新股票信息
ginkgo data update --stockinfo

# 准备测试数据
ginkgo data update day --code 000001.SZ --start 20230101 --end 20231231
```

### 第一个交易策略

#### 1. 创建简单移动平均策略

```python
# examples/my_first_strategy.py
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd

from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES
from ginkgo.libs.core.logger import GLOG

class MovingAverageStrategy(BaseStrategy):
    """简单移动平均策略"""

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__()
        self.short_period = short_period
        self.long_period = long_period
        self.name = "MovingAverage"

    def cal(self, portfolio_info: Dict[str, Any], event: Any) -> List[Signal]:
        """
        计算交易信号

        Args:
            portfolio_info: 投资组合信息
            event: 价格更新事件

        Returns:
            List[Signal]: 交易信号列表
        """
        signals = []

        try:
            # 获取当前价格数据
            symbol = event.symbol
            current_price = event.price

            # 获取历史数据
            bars = self.get_bars(
                symbol=symbol,
                count=self.long_period + 5,  # 多获取一些确保数据充足
                frequency='1d'
            )

            if len(bars) < self.long_period:
                GLOG.debug(f"数据不足，跳过 {symbol}")
                return signals

            # 计算移动平均
            df = pd.DataFrame([bar.__dict__ for bar in bars])
            df['ma_short'] = df['close'].rolling(self.short_period).mean()
            df['ma_long'] = df['close'].rolling(self.long_period).mean()

            # 获取最新指标
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # 生成信号
            current_position = portfolio_info.get('positions', {}).get(symbol, 0)

            # 金叉买入信号
            if (prev['ma_short'] <= prev['ma_long'] and
                latest['ma_short'] > latest['ma_long'] and
                current_position <= 0):

                signal = Signal(
                    symbol=symbol,
                    direction=DIRECTION_TYPES.LONG,
                    quantity=1000,  # 固定数量
                    price=current_price,
                    timestamp=datetime.now()
                )
                signals.append(signal)
                GLOG.info(f"生成买入信号: {symbol} @ {current_price}")

            # 死叉卖出信号
            elif (prev['ma_short'] >= prev['ma_long'] and
                  latest['ma_short'] < latest['ma_long'] and
                  current_position > 0):

                signal = Signal(
                    symbol=symbol,
                    direction=DIRECTION_TYPES.SHORT,
                    quantity=current_position,  # 清仓
                    price=current_price,
                    timestamp=datetime.now()
                )
                signals.append(signal)
                GLOG.info(f"生成卖出信号: {symbol} @ {current_price}")

        except Exception as e:
            GLOG.ERROR(f"策略计算错误: {e}")

        return signals

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': self.name,
            'short_period': self.short_period,
            'long_period': self.long_period,
            'description': f'简单移动平均策略 (短期{self.short_period}日, 长期{self.long_period}日)'
        }

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        try:
            short_period = params.get('short_period', self.short_period)
            long_period = params.get('long_period', self.long_period)

            if not (1 < short_period < long_period < 500):
                raise ValueError("参数范围错误: 1 < short_period < long_period < 500")

            return True
        except Exception as e:
            GLOG.ERROR(f"参数验证失败: {e}")
            return False
```

#### 2. 创建风险管理器

```python
# examples/my_risk_manager.py
from typing import Dict, Any, List
from datetime import datetime

from ginkgo.trading.strategy.risk_managements.base_risk import BaseRiskManagement
from ginkgo.trading.entities import Signal, Order
from ginkgo.trading.enums import DIRECTION_TYPES
from ginkgo.libs.core.logger import GLOG

class SimpleRiskManager(BaseRiskManagement):
    """简单风险管理器"""

    def __init__(self, max_position_ratio: float = 0.3, loss_limit: float = 0.05):
        super().__init__()
        self.max_position_ratio = max_position_ratio
        self.loss_limit = loss_limit
        self.name = "SimpleRiskManager"

    def cal(self, portfolio_info: Dict[str, Any], order: Order) -> Order:
        """
        验证并调整订单

        Args:
            portfolio_info: 投资组合信息
            order: 原始订单

        Returns:
            Order: 调整后的订单
        """
        try:
            total_value = portfolio_info.get('total_value', 0)
            current_position = portfolio_info.get('positions', {}).get(order.symbol, 0)

            # 计算订单金额
            order_value = order.quantity * order.price if order.price else 0

            # 检查仓位限制
            max_position_value = total_value * self.max_position_ratio
            current_position_value = abs(current_position) * (order.price or 0)

            if current_position_value + order_value > max_position_value:
                # 调整订单数量
                max_quantity = (max_position_value - current_position_value) / (order.price or 1)
                adjusted_quantity = min(order.quantity, max_quantity)

                if adjusted_quantity <= 0:
                    GLOG.warn(f"订单被拒绝: 超出仓位限制 {order.symbol}")
                    order.quantity = 0
                else:
                    GLOG.info(f"订单数量调整: {order.symbol} {order.quantity} -> {adjusted_quantity}")
                    order.quantity = adjusted_quantity

            return order

        except Exception as e:
            GLOG.ERROR(f"风控处理错误: {e}")
            return order

    def generate_signals(self, portfolio_info: Dict[str, Any], event: Any) -> List[Signal]:
        """
        生成风控信号

        Args:
            portfolio_info: 投资组合信息
            event: 触发事件

        Returns:
            List[Signal]: 风控信号
        """
        signals = []

        try:
            positions = portfolio_info.get('positions', {})

            for symbol, position in positions.items():
                if position == 0:
                    continue

                # 获取当前价格
                current_price = event.price if event.symbol == symbol else self.get_current_price(symbol)
                if current_price is None:
                    continue

                # 计算盈亏
                # 注意: 这里简化处理，实际需要获取开仓价格
                # 假设我们可以在portfolio_info中获取持仓成本信息
                position_cost = portfolio_info.get('position_costs', {}).get(symbol, current_price)

                if position > 0:  # 多头持仓
                    pnl_ratio = (current_price - position_cost) / position_cost

                    # 止损检查
                    if pnl_ratio <= -self.loss_limit:
                        signal = Signal(
                            symbol=symbol,
                            direction=DIRECTION_TYPES.SHORT,
                            quantity=position,
                            price=current_price,
                            timestamp=datetime.now(),
                            reason=f"止损: 亏损比例{pnl_ratio:.2%}"
                        )
                        signals.append(signal)
                        GLOG.warn(f"触发止损: {symbol} 亏损{pnl_ratio:.2%}")

                elif position < 0:  # 空头持仓
                    pnl_ratio = (position_cost - current_price) / position_cost

                    # 止损检查
                    if pnl_ratio <= -self.loss_limit:
                        signal = Signal(
                            symbol=symbol,
                            direction=DIRECTION_TYPES.LONG,
                            quantity=abs(position),
                            price=current_price,
                            timestamp=datetime.now(),
                            reason=f"止损: 亏损比例{pnl_ratio:.2%}"
                        )
                        signals.append(signal)
                        GLOG.warn(f"触发止损: {symbol} 亏损{pnl_ratio:.2%}")

        except Exception as e:
            GLOG.ERROR(f"风控信号生成错误: {e}")

        return signals

    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        try:
            # 这里应该从数据服务获取最新价格
            # 简化实现，实际应该调用相应的数据接口
            bars = self.get_bars(symbol=symbol, count=1, frequency='1d')
            return bars[0].close if bars else None
        except:
            return None
```

### 运行回测

#### 1. 创建回测脚本

```python
# examples/run_backtest.py
from datetime import datetime
from ginkgo.trading.engines.historic_engine import EngineHistoric
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator

from my_first_strategy import MovingAverageStrategy
from my_risk_manager import SimpleRiskManager

def run_backtest():
    """运行回测"""

    # 1. 创建策略
    strategy = MovingAverageStrategy(short_period=5, long_period=20)

    # 2. 创建风控管理器
    risk_manager = SimpleRiskManager(max_position_ratio=0.3, loss_limit=0.05)

    # 3. 创建投资组合
    portfolio = PortfolioT1Backtest(
        name="MA_5_20_Backtest",
        initial_capital=1000000.0,  # 100万初始资金
        commission_rate=0.001,      # 0.1%手续费
        slippage_rate=0.001         # 0.1%滑点
    )

    # 4. 添加组件到投资组合
    portfolio.add_strategy(strategy)
    portfolio.add_risk_manager(risk_manager)

    # 5. 设置交易标的
    symbols = ["000001.SZ"]  # 平安银行

    # 6. 创建回测引擎
    engine = EngineHistoric(
        name="Backtest_2023",
        portfolio=portfolio,
        symbols=symbols,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        frequency="1d"
    )

    # 7. 运行回测
    print("开始回测...")
    result = engine.run()

    # 8. 分析结果
    evaluator = BacktestEvaluator()
    analysis = evaluator.evaluate(result)

    # 9. 输出结果
    print("\n=== 回测结果 ===")
    print(f"总收益率: {analysis['total_return']:.2%}")
    print(f"年化收益率: {analysis['annual_return']:.2%}")
    print(f"夏普比率: {analysis['sharpe_ratio']:.2f}")
    print(f"最大回撤: {analysis['max_drawdown']:.2%}")
    print(f"胜率: {analysis['win_rate']:.2%}")
    print(f"总交易次数: {analysis['total_trades']}")

    # 10. 保存结果
    engine.save_results("backtest_results_2023.json")

    return result

if __name__ == "__main__":
    run_backtest()
```

#### 2. 运行回测

```bash
# 确保在正确的目录下
cd /home/kaoru/Applications/Ginkgo

# 运行回测
python examples/run_backtest.py

# 预期输出:
# 开始回测...
# === 回测结果 ===
# 总收益率: 12.34%
# 年化收益率: 12.34%
# 夏普比率: 0.87
# 最大回撤: -8.45%
# 胜率: 58.23%
# 总交易次数: 24
```

### TDD开发流程

#### 1. 编写测试（Red阶段）

```python
# test/test_moving_average_strategy.py
import pytest
from unittest.mock import Mock
from datetime import datetime

from my_first_strategy import MovingAverageStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES

class TestMovingAverageStrategy:
    """移动平均策略测试"""

    def setup_method(self):
        """测试前准备"""
        self.strategy = MovingAverageStrategy(short_period=5, long_period=20)

    def test_strategy_initialization(self):
        """测试策略初始化"""
        assert self.strategy.short_period == 5
        assert self.strategy.long_period == 20
        assert self.strategy.name == "MovingAverage"

    def test_calculate_signals_with_insufficient_data(self):
        """测试数据不足时的信号计算"""
        # 模拟数据不足的情况
        portfolio_info = {}
        event = Mock()
        event.symbol = "000001.SZ"

        # Mock get_bars返回不足的数据
        self.strategy.get_bars = Mock(return_value=[])

        signals = self.strategy.cal(portfolio_info, event)

        assert len(signals) == 0

    def test_golden_cross_buy_signal(self):
        """测试金叉买入信号"""
        # 准备测试数据
        portfolio_info = {"positions": {"000001.SZ": 0}}
        event = Mock()
        event.symbol = "000001.SZ"
        event.price = 10.5

        # Mock历史数据，模拟金叉
        mock_bars = self._create_mock_bars_with_golden_cross()
        self.strategy.get_bars = Mock(return_value=mock_bars)

        signals = self.strategy.cal(portfolio_info, event)

        assert len(signals) == 1
        assert signals[0].direction == DIRECTION_TYPES.LONG
        assert signals[0].symbol == "000001.SZ"

    def test_death_cross_sell_signal(self):
        """测试死叉卖出信号"""
        # 准备测试数据
        portfolio_info = {"positions": {"000001.SZ": 1000}}
        event = Mock()
        event.symbol = "000001.SZ"
        event.price = 9.8

        # Mock历史数据，模拟死叉
        mock_bars = self._create_mock_bars_with_death_cross()
        self.strategy.get_bars = Mock(return_value=mock_bars)

        signals = self.strategy.cal(portfolio_info, event)

        assert len(signals) == 1
        assert signals[0].direction == DIRECTION_TYPES.SHORT
        assert signals[0].symbol == "000001.SZ"

    def test_parameter_validation(self):
        """测试参数验证"""
        # 有效参数
        valid_params = {"short_period": 10, "long_period": 30}
        assert self.strategy.validate_parameters(valid_params) == True

        # 无效参数：短期大于长期
        invalid_params = {"short_period": 30, "long_period": 10}
        assert self.strategy.validate_parameters(invalid_params) == False

        # 无效参数：超出范围
        invalid_params = {"short_period": 0, "long_period": 600}
        assert self.strategy.validate_parameters(invalid_params) == False

    def _create_mock_bars_with_golden_cross(self):
        """创建金叉的模拟数据"""
        # 这里需要创建25个模拟K线数据，最后两天形成金叉
        # 实际实现中应该使用更精确的数据构造
        pass

    def _create_mock_bars_with_death_cross(self):
        """创建死叉的模拟数据"""
        # 这里需要创建25个模拟K线数据，最后两天形成死叉
        # 实际实现中应该使用更精确的数据构造
        pass
```

#### 2. 运行测试（确认失败）

```bash
# 运行测试，确认失败（Red阶段）
pytest test/test_moving_average_strategy.py -v

# 预期输出: 测试失败，因为策略还未实现或存在bug
```

#### 3. 实现功能（Green阶段）

根据测试失败的原因，修改策略实现，使测试通过。

#### 4. 重构优化（Refactor阶段）

在测试保护下，优化代码结构和性能。

### 实盘交易

#### 1. 配置实盘环境

```python
# examples/live_trading.py
from datetime import datetime
from ginkgo.trading.engines.live_engine import EngineLive
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive

from my_first_strategy import MovingAverageStrategy
from my_risk_manager import SimpleRiskManager

def setup_live_trading():
    """设置实盘交易"""

    # 创建策略（参数可能需要调整）
    strategy = MovingAverageStrategy(short_period=10, long_period=30)

    # 创建风控管理器（实盘风控更严格）
    risk_manager = SimpleRiskManager(
        max_position_ratio=0.2,  # 更小的仓位
        loss_limit=0.03          # 更严格的止损
    )

    # 创建实盘投资组合
    portfolio = PortfolioLive(
        name="Live_MA_Portfolio",
        broker_id="sim_broker",  # 使用模拟券商进行测试
        initial_capital=100000.0
    )

    # 添加组件
    portfolio.add_strategy(strategy)
    portfolio.add_risk_manager(risk_manager)

    # 设置交易标的
    symbols = ["000001.SZ"]

    # 创建实盘引擎
    engine = EngineLive(
        name="Live_Trading_Engine",
        portfolio=portfolio,
        symbols=symbols,
        data_source="real_time"  # 实时数据源
    )

    return engine

def run_live_trading():
    """运行实盘交易"""

    engine = setup_live_trading()

    try:
        print("启动实盘交易...")
        print("按 Ctrl+C 停止交易")

        # 启动引擎
        engine.start()

        # 保持运行
        engine.run_forever()

    except KeyboardInterrupt:
        print("\n停止交易...")
        engine.stop()
    except Exception as e:
        print(f"交易异常: {e}")
        engine.stop()

if __name__ == "__main__":
    # 注意: 实盘交易前请充分测试
    # 建议先在模拟环境中运行
    run_live_trading()
```

#### 2. 运行实盘交易

```bash
# 确保已正确配置券商接口和数据源
# 建议先使用模拟环境进行测试

# 运行实盘交易
python examples/live_trading.py
```

### 监控和调试

#### 1. 启用详细日志

```python
import logging
from ginkgo.libs import GLOG

# 设置日志级别
GLOG.set_level("DEBUG")

# 启用文件日志
GLOG.add_file_handler("trading.log")

# 运行策略
# ...
```

#### 2. 监控系统状态

```bash
# 查看系统状态
ginkgo status

# 查看worker状态
ginkgo worker status

# 查看数据同步状态
ginkgo data list stockinfo --page 10
```

#### 3. 性能分析

```python
# 添加性能监控装饰器
from ginkgo.libs.decorators import time_logger, performance_monitor

class PerformanceMonitoredStrategy(MovingAverageStrategy):
    """带性能监控的策略"""

    @time_logger
    @performance_monitor
    def cal(self, portfolio_info, event):
        return super().cal(portfolio_info, event)
```

## 常见问题

### Q1: 数据库连接失败
```bash
# 确保已启用调试模式
ginkgo system config set --debug on

# 检查数据库配置
cat ~/.ginkgo/config.yaml
```

### Q2: 策略无信号输出
- 检查数据是否充足
- 验证策略参数设置
- 启用DEBUG日志查看详细信息

### Q3: 回测结果异常
- 检查手续费和滑点设置
- 验证数据完整性
- 确认策略逻辑正确性

### Q4: 实盘交易风险
- 务必先在模拟环境充分测试
- 设置严格的风控参数
- 实时监控系统运行状态

## 下一步

1. **学习高级策略开发**: 了解多因子策略、机器学习策略等
2. **深入研究风控系统**: 学习动态风控、组合风控等
3. **性能优化**: 掌握向量化计算、并行处理等技巧
4. **监控系统**: 建立完善的监控和告警体系

## 支持与帮助

- **文档**: 查看项目docs目录
- **示例**: 参考examples目录
- **测试**: 学习test目录的测试用例
- **社区**: 提交Issue获取帮助

祝您使用愉快！