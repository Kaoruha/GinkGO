# 实盘交易系统场景清单

**Purpose**: 系统性梳理实盘交易运行中会遇到的所有情况/场景
**Created**: 2026-01-04
**Feature**: 007-live-trading-architecture

> **架构说明**: 本文档中的伪代码主要用于说明业务逻辑，实际架构实现使用**双队列模式**：
> - Portfolio通过`put()`发布订单事件到output_queue
> - ExecutionNode监听output_queue，序列化订单并发送到Kafka
> - 伪代码中的`submit_order()`等简洁表示对应实际的双队列通信机制
> - 详见 [information-flow.md](./information-flow.md) 和 [plan.md](./plan.md)

## 场景分类概览

| 类别 | 场景数量 | 优先级 | 说明 |
|------|---------|-------|------|
| 1. 正常业务流程 | 15 | P0 | 日常交易核心流程（含信号产生） |
| 2. Portfolio生命周期 | 10 | P0 | Portfolio管理操作 |
| 3. Node生命周期 | 8 | P0 | ExecutionNode管理 |
| 4. 系统组件管理 | 6 | P1 | LiveCore组件控制 |
| 5. 数据源和连接 | 10 | P0 | 外部依赖异常 |
| 6. 交易异常情况 | 12 | P0 | 订单和风控异常 |
| 7. 系统异常情况 | 9 | P1 | 系统级故障 |
| 8. 运维操作 | 8 | P2 | 人工干预操作 |
| 9. 边缘情况 | 10 | P1 | 极端场景 |
| **总计** | **88** | - | **覆盖所有运行情况** |

**新增信号产生场景（11个）**:
- 1.5 策略信号正常生成
- 1.6 买入信号（LONG）产生
- 1.7 卖出/平仓信号（SHORT）产生
- 1.8 多策略信号冲突
- 1.9 无信号产生（市场观望）
- 1.10 信号被风控拦截
- 1.11 信号被风控调整（订单量修改）
- 1.12 风控信号覆盖策略信号
- 1.13 异常数据过滤（不产生信号）
- 1.14 数据延迟导致信号过期
- 1.15 信号频率限制（防止信号抖动）

---

## 1. 正常业务流程 (15个场景)

### 1.1 市场数据正常推送
**场景描述**: Data模块从外部数据源获取实时行情，推送到Kafka market.data.{market} topic

**触发条件**: 交易时间内，外部数据源持续推送行情

**系统行为**:
```
外部数据源 → LiveCore.Data → Kafka(market.data.cn)
                          ↓
                  ExecutionNode订阅消费
                          ↓
              根据interest_map路由到Portfolio Queue
                          ↓
                  Portfolio.on_event(PriceUpdate)
                          ↓
                  策略计算 → 生成Signal
```

**验证点**:
- ✅ 价格数据延迟 < 100ms (SC-002)
- ✅ 数据不丢失、不重复
- ✅ 兴趣集外股票不推送

---

### 1.2 策略信号正常生成
**场景描述**: Portfolio收到PriceUpdate事件，策略计算后生成交易信号

**触发条件**: PriceUpdate事件触发策略逻辑（如均线金叉）

**系统行为**:
```python
# Portfolio内部
def on_price_update(event: EventPriceUpdate):
    # 1. 更新本地价格缓存
    self.price_cache.update(event.code, event.price)

    # 2. 调用策略计算
    signals = self.strategy.cal(self.portfolio_info, event)

    # 3. 信号通过风控
    for signal in signals:
        signal = self.apply_risk_managements(signal)

    # 4. 通过Sizer计算订单量
    for signal in signals:
        order = self.sizer.cal(self.portfolio_info, signal)

    # 5. 订单提交到Kafka
    self.submit_order(order)
```

**验证点**:
- ✅ 信号生成延迟 < 200ms (SC-014)
- ✅ 信号通过风控检查
- ✅ Sizer正确计算订单量

---

### 1.3 订单正常提交
**场景描述**: Portfolio生成订单，提交到Kafka orders.{market} topic

**触发条件**: 策略生成交易信号

**系统行为**:
```
Portfolio → Kafka(orders.cn)
          ↓
    LiveEngine订阅消费
          ↓
    TradeGateway执行订单
          ↓
    真实交易所（券商API）
```

**验证点**:
- ✅ 订单提交延迟 < 100ms (SC-016)
- ✅ 订单格式正确（code, direction, volume, price）
- ✅ Kafka消息幂等性（enable.idempotence=true）

---

### 1.4 订单部分成交
**场景描述**: TradeGateway提交订单到交易所，订单部分成交

**触发条件**: 交易所返回部分成交回报

**系统行为**:
```python
# LiveEngine处理
def on_order_partially_filled(event: EventOrderPartiallyFilled):
    # 1. 查找对应Portfolio
    portfolio = self.get_portfolio(event.portfolio_id)

    # 2. 发送事件到ExecutionNode → Portfolio
    self.send_to_portfolio(portfolio.id, event)

    # 3. Portfolio更新持仓和资金
    portfolio.on_event(event)
    # position.volume += event.filled_volume
    # position.cost = 更新成本价
    # portfolio.cash -= event.filled_volume * event.filled_price
```

**验证点**:
- ✅ 持仓数量正确更新
- ✅ 资金正确扣减
- ✅ 订单状态正确（PARTIALLY_FILLED）

---

### 1.5 订单全部成交
**场景描述**: 订单最终全部成交

**触发条件**: 交易所返回订单全部完成回报

**系统行为**:
```python
def on_order_filled(event: EventOrderFilled):
    portfolio = self.get_portfolio(event.portfolio_id)
    self.send_to_portfolio(portfolio.id, event)

    # Portfolio更新为FILLED状态
    order.status = ORDER_STATUS.FILLED
    order.filled_volume = order.original_volume
```

**验证点**:
- ✅ 订单状态更新为FILLED
- ✅ 持仓和资金最终状态正确
- ✅ 触发后续策略逻辑

---

### 1.6 订单被拒绝
**场景描述**: TradeGateway提交订单到交易所，交易所拒绝订单

**触发条件**: 资金不足、持仓不足、价格偏离过大、交易时间错误

**系统行为**:
```python
def on_order_rejected(event: EventOrderRejected):
    portfolio = self.get_portfolio(event.portfolio_id)
    self.send_to_portfolio(portfolio.id, event)

    # Portfolio记录拒绝原因
    order.status = ORDER_STATUS.REJECTED
    order.reject_reason = event.reason  # "资金不足"
    GLOG.ERROR(f"Order rejected: {event.reason}")
```

**验证点**:
- ✅ 订单状态更新为REJECTED
- ✅ 记录拒绝原因
- ✅ 不影响持仓和资金

---

### 1.7 订单取消
**场景描述**: Portfolio主动发起订单取消请求

**触发条件**: 策略发出撤单信号

**系统行为**:
```
Portfolio → 取消订单请求
          ↓
    Kafka(orders.cn)
          ↓
    LiveEngine → TradeGateway
          ↓
    交易所撤单API
          ↓
    EventOrderCancelAck返回
```

**验证点**:
- ✅ 撤单请求成功发送
- ✅ 订单状态更新为CANCELLED
- ✅ 部分成交的订单正确处理

---

### 1.8 日终结算
**场景描述**: 交易结束后，系统执行日终结算流程

**触发条件**: 收盘时间（如15:00）

**系统行为**:
```python
def on_settlement():
    # 1. 停止策略计算
    self.stop_strategies()

    # 2. 计算当日盈亏
    daily_pnl = self.calculate_daily_pnl()

    # 3. 更新持仓成本（T+1交割）
    self.update_positions_cost()

    # 4. 持久化到数据库
    self.save_portfolio_state()

    # 5. 发送结算报告
    self.send_settlement_report()
```

**验证点**:
- ✅ 当日盈亏计算正确
- ✅ 持仓状态持久化
- ✅ 结算报告发送成功

---

### 1.5 策略信号正常生成
**场景描述**: Portfolio收到PriceUpdate事件，策略计算后生成交易信号

**触发条件**: PriceUpdate事件触发策略逻辑（如均线金叉）

**系统行为**:
```python
# Portfolio内部
def on_price_update(event: EventPriceUpdate):
    # 1. 更新本地价格缓存
    self.price_cache.update(event.code, event.price)

    # 2. 调用策略计算
    signals = self.strategy.cal(self.portfolio_info, event)

    # 3. 信号通过风控
    for signal in signals:
        signal = self.apply_risk_managements(signal)

    # 4. 通过Sizer计算订单量
    for signal in signals:
        order = self.sizer.cal(self.portfolio_info, signal)

    # 5. 订单提交到Kafka
    self.submit_order(order)
```

**验证点**:
- ✅ 信号生成延迟 < 200ms (SC-014)
- ✅ 信号通过风控检查
- ✅ Sizer正确计算订单量

---

### 1.6 买入信号（LONG）产生
**场景描述**: 策略产生买入信号

**触发条件**:
- 金叉（短期均线上穿长期均线）
- 突破阻力位
- RSI超卖（< 30）
- 其他多头信号

**系统行为**:
```python
Signal(
    code="000001.SZ",
    direction=DIRECTION_TYPES.LONG,
    volume=1000,  # 目标数量（或由Sizer计算）
    price=current_price,  # 限价（市价则不填）
    reason="Golden Cross: MA10 > MA20"
)
```

**验证点**:
- ✅ direction = LONG
- ✅ 订单提交后预期增加持仓
- ✅ 信号理由清晰

---

### 1.7 卖出/平仓信号（SHORT）产生
**场景描述**: 策略产生卖出或平仓信号

**触发条件**:
- 死叉（短期均线下穿长期均线）
- 跌破支撑位
- RSI超买（> 70）
- 止损/止盈触发

**系统行为**:
```python
Signal(
    code="000001.SZ",
    direction=DIRECTION_TYPES.SHORT,
    volume=portfolio.get_position("000001.SZ").volume,  # 平仓全部
    reason="Death Cross: MA10 < MA20"
)
```

**注意**: A股市场无做空机制，SHORT实际为**平仓信号**

**验证点**:
- ✅ direction = SHORT
- ✅ 仅在有持仓时产生订单
- ✅ 订单量 ≤ 当前持仓量

---

### 1.8 多策略信号冲突
**场景描述**: 同一股票同时产生买入和卖出信号

**触发条件**:
- 多个策略逻辑冲突（如趋势策略做多，均值回归策略做空）
- 风控信号与策略信号冲突

**系统行为**:
```python
# Portfolio 处理冲突信号
def resolve_conflicting_signals(signals: List[Signal]) -> List[Signal]:
    # 按股票分组
    signals_by_code = group_by_code(signals)

    resolved_signals = []
    for code, code_signals in signals_by_code.items():
        directions = [s.direction for s in code_signals]

        # 检查冲突
        if DIRECTION_TYPES.LONG in directions and DIRECTION_TYPES.SHORT in directions:
            GLOG.WARN(f"Conflicting signals for {code}: LONG and SHORT")

            # 冲突解决策略：
            # 1. 优先级：风控信号 > 策略信号
            risk_signals = [s for s in code_signals if s.reason.startswith("Risk")]
            if risk_signals:
                resolved_signals.extend(risk_signals)
            else:
                # 2. 忽略所有冲突信号
                GLOG.WARN(f"Ignoring all conflicting signals for {code}")
        else:
            resolved_signals.extend(code_signals)

    return resolved_signals
```

**验证点**:
- ✅ 冲突检测
- ✅ 风控信号优先
- ✅ 日志记录冲突

---

### 1.9 无信号产生（市场观望）
**场景描述**: 策略运行后不产生任何信号

**触发条件**:
- 市场盘整（无明显趋势）
- 技术指标未触发（如RSI在30-70之间）
- 数据不足无法判断

**系统行为**:
```python
def cal(self, portfolio_info: Dict, event: EventPriceUpdate) -> List[Signal]:
    # 策略逻辑计算后，不满足任何条件
    if not self.is_signal_triggered():
        GLOG.DEBUG(f"No signal generated for {event.code}, market in consolidation")
        return []  # 返回空列表

    # 满足条件才产生信号
    return [Signal(...)]
```

**验证点**:
- ✅ 返回空列表 []
- ✅ 不生成任何订单
- ✅ Portfolio状态不变
- ✅ 日志记录无信号原因

---

### 1.10 信号被风控拦截
**场景描述**: 策略产生的信号被风控模块拦截

**触发条件**:
- 持仓超限（单股仓位 > 20%）
- 资金不足
- 违禁交易时间

**系统行为**:
```python
# Portfolio 应用风控
def apply_risk_managements(self, signal: Signal) -> Optional[Signal]:
    for risk_mgmt in self.risk_managements:
        # 风控检查
        signal = risk_mgmt.check(self.portfolio_info, signal)

        # 如果风控拦截，返回None
        if signal is None:
            GLOG.WARN(f"Signal blocked by {risk_mgmt.name}: {signal.reason}")
            return None  # 拦截信号

    # 所有无控通过
    return signal

# PositionRatioRisk 风控拦截示例
class PositionRatioRisk(BaseRiskManagement):
    def check(self, portfolio_info: Dict, signal: Signal) -> Optional[Signal]:
        if signal.direction == DIRECTION_TYPES.LONG:
            new_ratio = calculate_new_position_ratio(portfolio_info, signal)

            if new_ratio > self.max_position_ratio:
                GLOG.WARN(f"Position ratio {new_ratio:.2%} exceeds limit {self.max_position_ratio:.2%}")
                return None  # 完全拦截

        return signal
```

**验证点**:
- ✅ 风控拦截返回None
- ✅ 不生成订单
- ✅ 日志记录拦截原因

---

### 1.11 信号被风控调整（订单量修改）
**场景描述**: 风控调整信号的订单量而非完全拦截

**触发条件**:
- 持仓超限但部分允许
- 资金不足但部分允许

**系统行为**:
```python
# PositionRatioRisk 调整订单量
class PositionRatioRisk(BaseRiskManagement):
    def check(self, portfolio_info: Dict, signal: Signal) -> Optional[Signal]:
        if signal.direction == DIRECTION_TYPES.LONG:
            current_position = portfolio_info["positions"].get(signal.code, 0)
            total_value = portfolio_info["total_value"]

            # 计算新持仓比例
            new_position_value = (current_position + signal.volume) * signal.price
            new_ratio = new_position_value / total_value

            # 超过限制，调整订单量
            if new_ratio > self.max_position_ratio:
                GLOG.WARN(f"Position ratio {new_ratio:.2%} exceeds limit, adjusting volume")

                # 计算允许的最大订单量
                max_volume = int((self.max_position_ratio * total_value) / signal.price) - current_position

                if max_volume <= 0:
                    return None  # 完全拦截

                # 调整信号
                original_volume = signal.volume
                signal.volume = max_volume
                GLOG.INFO(f"Adjusted signal volume from {original_volume} to {max_volume}")

        return signal
```

**验证点**:
- ✅ 信号volume被调整
- ✅ 调整后仍满足风控要求
- ✅ 日志记录调整过程

---

### 1.12 风控信号覆盖策略信号
**场景描述**: 风控生成的信号（如止损）优先级高于策略信号

**触发条件**:
- 止损触发（持仓亏损 > 10%）
- 止盈触发（持仓盈利 > 20%）
- 紧急平仓

**系统行为**:
```python
# Portfolio 处理事件时，先执行风控信号生成
def on_price_update(self, event: EventPriceUpdate):
    # 1. 先让风控生成信号（主动风控）
    risk_signals = []
    for risk_mgmt in self.risk_managements:
        risk_signals.extend(risk_mgmt.generate_signals(self.portfolio_info, event))

    # 2. 如果风控有信号，优先处理
    if risk_signals:
        GLOG.INFO(f"Risk signals generated: {len(risk_signals)}, overriding strategy signals")
        signals = risk_signals  # 使用风控信号，忽略策略信号

    # 3. 如果没有风控信号，让策略生成信号
    else:
        signals = self.strategy.cal(self.portfolio_info, event)

    # 4. 继续处理信号
    for signal in signals:
        # ...
```

**验证点**:
- ✅ 风控信号优先
- ✅ 策略信号被覆盖
- ✅ 日志记录风控触发

---

### 1.13 异常数据过滤（不产生信号）
**场景描述**: 异常价格数据被过滤，不触发策略信号

**触发条件**:
- 价格跳变过大（如单日涨跌 > 10%）
- 价格为负数或零
- 时间戳异常（未来时间）

**系统行为**:
```python
def validate_event(self, event: EventPriceUpdate) -> bool:
    # 1. 价格合理性检查
    last_price = self.price_cache.get(event.code)
    if last_price:
        change_ratio = abs(event.price - last_price) / last_price
        if change_ratio > 0.1:  # 超过10%认为异常
            GLOG.WARN(f"Abnormal price change for {event.code}: {change_ratio:.2%}")
            return False  # 过滤异常数据

    # 2. 价格范围检查
    if event.price <= 0:
        GLOG.WARN(f"Invalid price for {event.code}: {event.price}")
        return False

    # 3. 时间戳检查
    if event.timestamp > datetime.now() + timedelta(seconds=5):
        GLOG.WARN(f"Future timestamp for {event.code}: {event.timestamp}")
        return False

    # 数据正常
    return True

# Portfolio 使用
def on_price_update(self, event: EventPriceUpdate):
    if not self.validate_event(event):
        return  # 过滤异常数据，不产生信号

    # 正常处理
    signals = self.strategy.cal(self.portfolio_info, event)
```

**验证点**:
- ✅ 异常数据被过滤
- ✅ 不产生信号
- ✅ 日志记录异常

---

### 1.14 数据延迟导致信号过期
**场景描述**: 因数据延迟，信号产生后失效

**触发条件**:
- 网络延迟导致价格数据到达时间 > 5秒
- 信号产生后市场条件已变化

**系统行为**:
```python
# Portfolio 处理信号前检查时效性
def on_signal(self, signal: Signal):
    # 检查信号时效
    signal_age = datetime.now() - signal.timestamp

    if signal_age > timedelta(seconds=5):
        GLOG.WARN(f"Signal expired: {signal.code}, age: {signal_age}")
        # 丢弃过期信号
        return

    # 信号有效，继续处理
    # ...
```

**验证点**:
- ✅ 信号时效检查（5秒阈值）
- ✅ 过期信号丢弃
- ✅ 日志记录

---

### 1.15 信号频率限制（防止信号抖动）
**场景描述**: 策略短时间内产生大量信号，需要限制频率

**触发条件**:
- 市场剧烈波动
- 策略参数不当（如周期过短）
- 高频数据流

**系统行为**:
```python
# 信号频率限制
class BaseStrategy:
    def __init__(self):
        self.last_signal_time = {}  # {code: last_time}
        self.min_signal_interval = timedelta(seconds=60)  # 最小信号间隔

    def cal(self, portfolio_info: Dict, event: EventPriceUpdate) -> List[Signal]:
        signals = self.generate_signals(event)  # 生成信号

        # 过滤频繁信号
        filtered_signals = []
        for signal in signals:
            last_time = self.last_signal_time.get(signal.code)

            if last_time is None or datetime.now() - last_time > self.min_signal_interval:
                filtered_signals.append(signal)
                self.last_signal_time[signal.code] = datetime.now()
            else:
                GLOG.DEBUG(f"Signal rate limit for {signal.code}, skipped (last: {last_time})")

        return filtered_signals
```

**验证点**:
- ✅ 信号频率限制（如60秒最小间隔）
- ✅ 频繁信号被过滤
- ✅ 日志记录

---

## 2. Portfolio生命周期 (10个场景)

### 2.1 Portfolio创建
**场景描述**: 用户通过API创建新Portfolio

**触发条件**: POST /api/portfolio with config

**系统行为**:
```json
// API请求
POST /api/portfolio
{
  "name": "test_portfolio",
  "strategy_id": "ma_crossover",
  "strategy_params": {"short_period": 10, "long_period": 20},
  "risk_managements": [
    {"type": "PositionRatioRisk", "max_ratio": 0.2},
    {"type": "LossLimitRisk", "loss_limit": 0.1}
  ],
  "initial_cash": 1000000,
  "interested_codes": ["000001.SZ", "000002.SZ"]
}

// 系统响应
1. API Gateway验证请求
2. 写入数据库 portfolios 表（status = "created"）
3. 发送 Kafka 消息到 portfolio.lifecycle topic
4. Scheduler 下次调度循环发现新 Portfolio
5. Scheduler 分配到某个 ExecutionNode
6. 发送 schedule.updates 消息到 Node
7. ExecutionNode 从数据库加载配置
8. 创建 Portfolio 实例和 PortfolioProcessor 线程
9. 更新 Redis 状态 portfolio:portfolio_001:status = "running"
```

**验证点**:
- ✅ Portfolio ID 唯一
- ✅ 数据库记录创建成功
- ✅ Kafka 消息发送成功
- ✅ ExecutionNode 成功启动 Portfolio

---

### 2.2 Portfolio启动
**场景描述**: ExecutionNode 启动 Portfolio 实例

**触发条件**: Scheduler 分配 Portfolio 到 Node

**系统行为**:
```python
# ExecutionNode
def start_portfolio(portfolio_id: str):
    # 1. 从数据库加载配置
    config = db.get_portfolio_config(portfolio_id)

    # 2. 创建 Portfolio 实例
    portfolio = Portfolio(
        name=config.name,
        initial_cash=config.initial_cash
    )

    # 3. 添加策略
    strategy = create_strategy(config.strategy_id, config.strategy_params)
    portfolio.add_strategy(strategy)

    # 4. 添加风控
    for rm_config in config.risk_managements:
        rm = create_risk_management(rm_config)
        portfolio.add_risk_management(rm)

    # 5. 创建 PortfolioProcessor 线程
    processor = PortfolioProcessor(
        portfolio_id=portfolio_id,
        portfolio=portfolio,
        node=self
    )
    processor.start()

    # 6. 更新 interest_map
    for code in config.interested_codes:
        self.interest_map[code].append(portfolio_id)

    # 7. 上报兴趣集到 LiveEngine
    self.send_interest_update()
```

**验证点**:
- ✅ Portfolio 实例创建成功
- ✅ 策略和风控正确初始化
- ✅ PortfolioProcessor 线程启动
- ✅ interest_map 更新
- ✅ 兴趣集上报到 LiveEngine

---

### 2.3 Portfolio配置变更（策略参数）
**场景描述**: 用户更新 Portfolio 的策略参数

**触发条件**: PUT /api/portfolio/{portfolio_id} with new params

**系统行为**:
```
1. API Gateway 接收请求
2. 更新数据库 portfolios 表
   UPDATE portfolios SET strategy_params = {...}, version = version + 1
3. 发送 Kafka 消息到 portfolio.config.updates topic
   {
     "portfolio_id": "portfolio_001",
     "version": "v2",
     "reason": "parameter_update"
   }
4. ExecutionNode 消费消息
5. 执行优雅重启流程（见 spec.md 第162-219行）
   ├─ 设置状态为 STOPPING
   ├─ 缓存消息到 buffer
   ├─ 等待 Queue 清空
   ├─ 停止 Portfolio 实例
   ├─ 加载新配置（v2）
   ├─ 重新初始化 Portfolio
   ├─ 重放缓存消息
   └─ 设置状态为 RUNNING
6. Portfolio 使用新策略参数运行
```

**验证点**:
- ✅ 配置版本号递增
- ✅ 无事件丢失（消息缓存机制）
- ✅ 切换时间 < 30秒 (SC-009)
- ✅ 新参数生效

---

### 2.4 Portfolio配置变更（风控参数）
**场景描述**: 用户更新 Portfolio 的风控参数

**触发条件**: PUT /api/portfolio/{portfolio_id}/risk

**系统行为**: 同2.3（优雅重启流程）

**验证点**:
- ✅ 新风控参数生效
- ✅ 风控实例重新初始化
- ✅ 切换过程无交易风险

---

### 2.5 Portfolio配置变更（兴趣集）
**场景描述**: Portfolio 更新订阅的股票代码列表

**触发条件**: PUT /api/portfolio/{portfolio_id}/interest

**系统行为**:
```python
# ExecutionNode
def update_portfolio_interest(portfolio_id: str, new_codes: List[str]):
    old_codes = self.portfolios[portfolio_id].interested_codes

    # 1. 更新 Portfolio 实例
    self.portfolios[portfolio_id].interested_codes = new_codes

    # 2. 更新 interest_map
    for code in old_codes:
        if code not in new_codes:
            self.interest_map[code].remove(portfolio_id)

    for code in new_codes:
        if code not in old_codes:
            self.interest_map[code].append(portfolio_id)

    # 3. 上报新的兴趣集到 LiveEngine
    self.send_interest_update()

    # 4. DataFeeder 更新订阅
    # LiveCore.Data 收到 interest.updates 消息
    # 更新 Kafka Topic 订阅
```

**验证点**:
- ✅ interest_map 正确更新
- ✅ 兴趣集上报到 LiveEngine
- ✅ DataFeeder 订阅更新

---

### 2.6 Portfolio停止（手动）
**场景描述**: 用户主动停止 Portfolio

**触发条件**: POST /api/portfolio/{portfolio_id}/stop

**系统行为**:
```python
# ExecutionNode
def stop_portfolio(portfolio_id: str):
    # 1. 设置状态为 STOPPING
    redis.hset(f"portfolio:{portfolio_id}:status", "status", "stopping")

    # 2. EventEngine 停止推送消息，开始缓存
    # （自动由 send_event_to_portfolio 处理）

    # 3. 等待 Queue 清空（最多30秒）
    processor = self.processors[portfolio_id]
    timeout = 30
    start = time.time()
    while processor.queue.qsize() > 0 and (time.time() - start) < timeout:
        time.sleep(0.1)

    # 4. 优雅停止线程
    processor.graceful_stop()

    # 5. 保存状态到数据库
    self.save_portfolio_state(portfolio_id)

    # 6. 清理资源
    del self.processors[portfolio_id]
    del self.portfolios[portfolio_id]

    # 7. 更新 Redis 状态
    redis.hset(f"portfolio:{portfolio_id}:status", "status", "stopped")
```

**验证点**:
- ✅ Queue 中消息处理完成
- ✅ 状态持久化到数据库
- ✅ 线程优雅停止（不强制杀死）
- ✅ interest_map 清理

---

### 2.7 Portfolio删除
**场景描述**: 用户删除 Portfolio

**触发条件**: DELETE /api/portfolio/{portfolio_id}

**系统行为**:
```
1. API Gateway 接收请求
2. 检查 Portfolio 状态（必须是 stopped）
3. 更新数据库 portfolios.status = "deleted"
4. 发送 Kafka 消息到 portfolio.lifecycle topic
   {"action": "delete", "portfolio_id": "portfolio_001"}
5. ExecutionNode 消费消息
6. 删除 Portfolio 实例和线程
7. 清理 interest_map
8. 从 Scheduler 调度计划中移除
9. 清理 Redis 状态
```

**验证点**:
- ✅ 运行中的 Portfolio 不能删除（返回错误）
- ✅ 数据库标记为 deleted
- ✅ 资源完全清理

---

### 2.8 Portfolio迁移（负载均衡）
**场景描述**: Scheduler 将 Portfolio 从 Node-A 迁移到 Node-B

**触发条件**: Scheduler 检测到负载不均衡

**系统行为**:
```
T1: Scheduler 计算负载分布
    Node-A: 5个Portfolio（负载过高）
    Node-B: 2个Portfolio（负载较低）

T2: Scheduler 决定迁移 portfolio_003 从 A → B

T3: 发送迁移命令
    Kafka(schedule.updates) → Node-A: 迁移出
    Kafka(schedule.updates) → Node-B: 迁移入

T4: Node-A 执行停止流程（同2.6）
    ├─ 设置状态 STOPPING
    ├─ 缓存消息
    ├─ 等待 Queue 清空
    ├─ 保存状态到数据库
    └─ 停止线程

T5: Node-B 执行启动流程（同2.2）
    ├─ 从数据库加载状态
    ├─ 创建 Portfolio 实例
    ├─ 启动线程
    ├─ 更新 interest_map
    └─ 上报兴趣集

T6: Kafka 中暂存的消息被 Node-B 消费

总耗时: < 30秒 (SC-009)
```

**验证点**:
- ✅ 迁移过程消息不丢失
- ✅ Portfolio 状态完整迁移
- ✅ 迁移时间 < 30秒
- ✅ 新 Node 正常工作

---

### 2.9 Portfolio迁移（故障恢复）
**场景描述**: Node-A 故障，Scheduler 将 Portfolio 迁移到 Node-B

**触发条件**: Scheduler 检测到 Node-A 心跳超时（>30秒）

**系统行为**:
```
T1: Scheduler 定时检查心跳
    redis.get("heartbeat:node:node_a") → nil (过期)

T2: Scheduler 标记 Node-A 为故障状态
    redis.srem("nodes:active", "node_a")

T3: Scheduler 查找 Node-A 上的 Portfolio
    redis.smembers("schedule:plan:node_a")
    → {portfolio_001, portfolio_002, portfolio_003}

T4: Scheduler 计算新分配方案
    portfolio_001 → node_b
    portfolio_002 → node_c
    portfolio_003 → node_b

T5: 更新 Redis 调度计划
    redis.del("schedule:plan:node_a")
    redis.sadd("schedule:plan:node_b", "portfolio_001", "portfolio_003")
    redis.sadd("schedule:plan:node_c", "portfolio_002")

T6: 发送 Kafka 通知 schedule.updates

T7: Node-B 和 Node-C 从数据库加载 Portfolio 状态并启动

T8: Kafka 中暂存的消息被新 Node 消费

总耗时: < 60秒 (SC-010)
```

**验证点**:
- ✅ 故障检测时间 < 30秒
- ✅ 故障恢复时间 < 60秒
- ✅ Portfolio 状态从数据库恢复
- ✅ Kafka 消息不丢失

---

### 2.10 Portfolio异常恢复
**场景描述**: Portfolio 运行时发生异常（如策略计算错误），需要恢复

**触发条件**: Portfolio 线程抛出未捕获异常

**系统行为**:
```python
# PortfolioProcessor 线程
def run(self):
    while True:
        try:
            event = self.queue.get(timeout=0.1)
            self.portfolio.on_event(event)
        except Exception as e:
            GLOG.ERROR(f"Portfolio {self.portfolio_id} error: {e}")
            # 1. 记录异常到数据库
            self.save_error_log(e)

            # 2. 更新 Redis 状态
            redis.hset(f"portfolio:{self.portfolio_id}:status", {
                "status": "error",
                "error": str(e),
                "error_time": datetime.now().isoformat()
            })

            # 3. 发送告警通知
            self.send_alert(f"Portfolio {self.portfolio_id} crashed")

            # 4. 停止线程
            break

            # 5. 等待 Scheduler 重新分配
```

**验证点**:
- ✅ 异常记录到数据库
- ✅ Redis 状态更新为 ERROR
- ✅ 告警通知发送
- ✅ Scheduler 检测到异常并重新分配

---

## 3. Node生命周期 (8个场景)

### 3.1 Node启动
**场景描述**: ExecutionNode 进程启动

**触发条件**: Docker 容器启动 / 手动启动进程

**系统行为**:
```python
# ExecutionNode 启动流程
def main():
    # 1. 初始化 Redis 连接
    redis_client = redis.Redis(host=REDIS_HOST)

    # 2. 初始化 Kafka Consumer
    kafka_consumer = KafkaConsumer(
        topics=["market.data.cn", "schedule.updates", "portfolio.config.updates"],
        group_id="execution_nodes"
    )

    # 3. 生成 Node ID
    node_id = f"node_{uuid.uuid4().hex[:8]}"

    # 4. 注册到 Redis
    redis.sadd("nodes:active", node_id)

    # 5. 启动心跳线程（每10秒刷新）
    def heartbeat_thread():
        while True:
            redis.set(f"heartbeat:node:{node_id}", "alive", ex=30)
            time.sleep(10)

    # 6. 从 Redis 获取计划状态
    planned_portfolios = redis.smembers(f"schedule:plan:{node_id}")

    # 7. 加载并启动 Portfolio
    for portfolio_id in planned_portfolios:
        start_portfolio(portfolio_id)

    # 8. 开始消费 Kafka 消息
    kafka_consumer_loop()
```

**验证点**:
- ✅ Node ID 唯一
- ✅ 注册到 Redis nodes:active
- ✅ 心跳正常发送
- ✅ 计划的 Portfolio 成功启动

---

### 3.2 Node正常停止
**场景描述**: 优雅停止 ExecutionNode

**触发条件**: docker stop / kill -TERM

**系统行为**:
```python
# 信号处理
def signal_handler(signum, frame):
    GLOG.INFO(f"Node {node_id} shutting down...")

    # 1. 设置状态为 STOPPING
    redis.hset(f"node:{node_id}:status", "status", "stopping")

    # 2. 停止所有 Portfolio（并发）
    with ThreadPoolExecutor() as executor:
        for portfolio_id in self.portfolios.keys():
            executor.submit(stop_portfolio, portfolio_id)

    # 3. 等待所有 Portfolio 停止完成
    wait_for_all_portfolios_stopped(timeout=60)

    # 4. 从活跃节点集合移除
    redis.srem("nodes:active", node_id)

    # 5. 保存最终状态
    save_all_portfolio_states()

    # 6. 关闭 Kafka Consumer
    kafka_consumer.close()

    # 7. 退出进程
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
```

**验证点**:
- ✅ 所有 Portfolio 优雅停止
- ✅ 状态持久化到数据库
- ✅ Kafka Consumer 正常关闭
- ✅ 从 Redis nodes:active 移除

---

### 3.3 Node故障（崩溃）
**场景描述**: ExecutionNode 进程崩溃

**触发条件**: 程序异常 / OOM / 系统故障

**系统行为**:
```
T1: Node 进程崩溃
    进程突然终止，无优雅停止

T2: 心跳停止
    redis.get("heartbeat:node:node_a") → TTL 过期

T3: Scheduler 检测到故障（30秒后）
    SMEMBERS nodes:active → 发现 node_a 不在活跃列表

T4: Scheduler 触发故障恢复流程（见2.9）
    ├─ 查找 Node-A 上的 Portfolio
    ├─ 计算新分配方案
    ├─ 更新 Redis 调度计划
    └─ 发送 Kafka 通知

T5: 其他 Node 从数据库加载 Portfolio 状态并恢复

总耗时: < 60秒 (SC-010)
```

**验证点**:
- ✅ 心跳超时检测
- ✅ Portfolio 自动迁移
- ✅ 恢复时间 < 60秒

---

### 3.4 Node故障（网络断开）
**场景描述**: ExecutionNode 与 Redis/Kafka 网络断开

**触发条件**: 网络分区 / 网络故障

**系统行为**:
```python
# 心跳线程捕获异常
def heartbeat_thread():
    while True:
        try:
            redis.set(f"heartbeat:node:{node_id}", "alive", ex=30)
            time.sleep(10)
        except redis.ConnectionError:
            GLOG.ERROR("Redis连接失败，停止心跳")
            # Node 进入本地隔离状态
            # 继续处理 Kafka 消息（如果连接正常）
            # 或完全停止（取决于策略）
            break

# Kafka 消费线程捕获异常
def kafka_consumer_loop():
    while True:
        try:
            messages = kafka_consumer.poll(timeout_ms=1000)
            # 处理消息
        except KafkaConnectionError:
            GLOG.ERROR("Kafka连接失败")
            # 重试或停止
            time.sleep(5)
```

**验证点**:
- ✅ 连接异常被捕获
- ✅ 错误日志记录
- ✅ 自动重试机制
- ✅ Scheduler 最终检测并迁移 Portfolio

---

### 3.5 Node增加（扩容）
**场景描述**: 新增 ExecutionNode 实例

**触发条件**: docker-compose up --scale execution-node=4

**系统行为**:
```
T1: 新 Node 启动（见3.1）
    node_d 启动，注册到 Redis
    redis.sadd("nodes:active", "node_d")

T2: Scheduler 定时调度发现新 Node
    SMEMBERS nodes:active → {node_a, node_b, node_c, node_d}

T3: Scheduler 计算负载分布
    重新平衡 Portfolio 分配

T4: 发送迁移命令到相关 Node
    Kafka(schedule.updates)

T5: 部分 Portfolio 迁移到 node_d

验证点: 负载更均衡
```

**验证点**:
- ✅ 新 Node 自动注册
- ✅ Scheduler 发现新 Node
- ✅ 负载自动均衡
- ✅ 无服务中断

---

### 3.6 Node移除（缩容）
**场景描述**: 移除 ExecutionNode 实例

**触发条件**: docker stop / docker-compose down

**系统行为**:
```
T1: 发送停止信号到 Node
    docker stop node_c

T2: Node 优雅停止（见3.2）
    ├─ 停止所有 Portfolio
    ├─ 保存状态
    └─ 从 nodes:active 移除

T3: Scheduler 检测到 Node 离线
    心跳过期

T4: Scheduler 迁移 Portfolio（见2.9）
    分配到其他健康 Node

T5: 验证: Node 移除，Portfolio 迁移完成
```

**验证点**:
- ✅ Node 优雅停止
- ✅ Portfolio 自动迁移
- ✅ 消息不丢失

---

### 3.7 Node资源不足
**场景描述**: ExecutionNode CPU/内存资源不足

**触发条件**: 消息积压 / Queue 满载

**系统行为**:
```python
# 监控线程
def monitor_resources():
    while True:
        # 检查 CPU
        cpu_usage = psutil.cpu_percent()
        if cpu_usage > 90:
            GLOG.WARN(f"CPU usage high: {cpu_usage}%")
            # 触发告警

        # 检查内存
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            GLOG.WARN(f"Memory usage high: {memory.percent}%")
            # 触发告警

        # 检查 Queue 积压
        for pid, processor in self.processors.items():
            queue_size = processor.queue.qsize()
            if queue_size > 800:
                GLOG.WARN(f"Portfolio {pid} queue size: {queue_size}")
                # 触发告警

        # 上报指标到 Redis
        redis.hset(f"node:{node_id}:metrics", {
            "cpu": cpu_usage,
            "memory": memory.percent,
            "queue_sizes": json.dumps(queue_sizes)
        })

        time.sleep(5)
```

**验证点**:
- ✅ 资源监控
- ✅ 告警触发
- ✅ Scheduler 检测并迁移 Portfolio

---

### 3.8 Node时钟同步
**场景描述**: 多 Node 环境下时钟偏差

**触发条件**: NTP 不同步 / 系统时钟漂移

**系统行为**:
```python
# 使用 NTP 同步
# Docker 容器配置
services:
  execution-node:
    image: ginkgo-execution-node
    volumes:
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=Asia/Shanghai

# 或者使用 chrony
```

**验证点**:
- ✅ 所有 Node 时钟同步（误差 < 1秒）
- ✅ 事件时间戳一致

---

## 4. 系统组件管理 (6个场景)

### 4.1 LiveEngine启动
**场景描述**: LiveCore 中的 LiveEngine 启动

**触发条件**: docker-compose up / API 启动命令

**系统行为**:
```python
# LiveEngine 启动流程
def start():
    # 1. 初始化 Kafka Consumer（订阅 orders.*）
    kafka_consumer = KafkaConsumer(
        topics=["orders.cn", "orders.hk", "orders.us", "orders.futures"]
    )

    # 2. 初始化 TradeGateway
    trade_gateway = TradeGateway(brokers=[broker_cn, broker_hk, ...])

    # 3. 绑定事件处理器
    self.bind_router(trade_gateway)

    # 4. 订阅 Kafka 控制命令
    control_consumer = KafkaConsumer(topics=["livecore.control"])

    # 5. 启动控制线程
    def control_loop():
        for msg in control_consumer:
            if msg.type == "start":
                self.start()
            elif msg.type == "stop":
                self.stop()

    # 6. 启动订单处理线程
    def order_loop():
        for msg in kafka_consumer:
            # 路由到 TradeGateway 执行
            self.on_event(msg)

    # 7. 更新 Redis 状态
    redis.hset("engine:live_001:status", "status", "running")
```

**验证点**:
- ✅ Kafka Consumer 启动
- ✅ TradeGateway 初始化
- ✅ 控制命令订阅

---

### 4.2 LiveEngine停止
**场景描述**: LiveEngine 正常停止

**触发条件**: API 停止命令 / docker stop

**系统行为**:
```python
def stop():
    # 1. 停止接收新订单
    kafka_consumer.unsubscribe()

    # 2. 等待现有订单处理完成
    wait_for_orders_completed(timeout=30)

    # 3. 关闭 TradeGateway 连接
    trade_gateway.close()

    # 4. 更新 Redis 状态
    redis.hset("engine:live_001:status", "status", "stopped")
```

**验证点**:
- ✅ 现有订单处理完成
- ✅ 资源正确释放

---

### 4.3 Scheduler启动
**场景描述**: Scheduler 启动并开始调度

**触发条件**: LiveCore 启动

**系统行为**:
```python
# Scheduler 启动流程
def start():
    # 1. 初始化 Redis 连接
    redis_client = redis.Redis(host=REDIS_HOST)

    # 2. 启动调度循环线程（每30秒）
    def schedule_loop():
        while True:
            try:
                # 执行调度算法
                self.schedule()

            except Exception as e:
                GLOG.ERROR(f"Scheduler error: {e}")

            time.sleep(30)

    # 3. 启动线程
    schedule_thread = threading.Thread(target=schedule_loop, daemon=True)
    schedule_thread.start()

    # 4. 更新 Redis 状态
    redis.hset("scheduler:status", "status", "running")
```

**验证点**:
- ✅ 调度循环正常启动
- ✅ 异常自动恢复

---

### 4.4 Data模块启动
**场景描述**: LiveCore.Data 启动并开始推送行情

**触发条件**: LiveCore 启动

**系统行为**:
```python
# Data 模块启动流程
def start():
    # 1. 初始化数据源连接（Tushare/AKShare/...）
    data_source = TushareDataSource()

    # 2. 初始化 Kafka Producer
    kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BROKERS)

    # 3. 订阅 interest.updates topic
    interest_consumer = KafkaConsumer(topics=["interest.updates"])

    # 4. 启动兴趣集监听线程
    def interest_loop():
        for msg in interest_consumer:
            # 更新兴趣集
            self.update_interest_set(msg.interest_set)

    # 5. 启动行情推送线程
    def market_data_loop():
        while True:
            # 获取实时行情
            quotes = data_source.get_quotes(self.interested_codes)

            # 推送到 Kafka
            for code, price in quotes.items():
                event = EventPriceUpdate(code=code, price=price)
                kafka_producer.send(f"market.data.{get_market(code)}", event)

            time.sleep(1)  # 每秒推送

    # 6. 启动线程
    threading.Thread(target=interest_loop, daemon=True).start()
    threading.Thread(target=market_data_loop, daemon=True).start()
```

**验证点**:
- ✅ 数据源连接成功
- ✅ Kafka Producer 启动
- ✅ 兴趣集动态更新

---

### 4.5 API Gateway启动
**场景描述**: API Gateway 启动并提供 HTTP API

**触发条件**: docker-compose up

**系统行为**:
```python
# API Gateway 启动流程
def start():
    # 1. 初始化 FastAPI 应用
    app = FastAPI()

    # 2. 注册路由
    @app.post("/api/portfolio")
    def create_portfolio(config: PortfolioConfig):
        # 创建 Portfolio
        pass

    # 3. 初始化 Redis 客户端（状态查询）
    redis_client = redis.Redis(host=REDIS_HOST)

    # 4. 初始化 Kafka Producer（控制命令）
    kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_BROKERS)

    # 5. 启动 HTTP 服务
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**验证点**:
- ✅ HTTP 服务启动（端口8000）
- ✅ API 路由正确
- ✅ Redis/Kafka 连接成功

---

### 4.6 组件间通信异常
**场景描述**: API Gateway 与 LiveCore 通信失败

**触发条件**: Redis/Kafka 连接失败

**系统行为**:
```python
# API Gateway 错误处理
@app.post("/api/engine/start")
def start_engine(engine_id: str):
    try:
        # 发送 Kafka 命令
        kafka_producer.send("livecore.control", {
            "type": "start",
            "engine_id": engine_id
        })
        return {"status": "success"}

    except KafkaError as e:
        GLOG.ERROR(f"Kafka error: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/engine/status")
def get_engine_status(engine_id: str):
    try:
        # 从 Redis 查询状态
        status = redis_client.hget(f"engine:{engine_id}:status", "status")
        return {"status": status}

    except RedisError:
        GLOG.ERROR("Redis error")
        raise HTTPException(status_code=503, detail="Service unavailable")
```

**验证点**:
- ✅ 异常被捕获
- ✅ 返回 503 错误
- ✅ 错误日志记录

---

## 5. 数据源和连接 (10个场景)

### 5.1 Kafka连接失败
**场景描述**: ExecutionNode 无法连接到 Kafka

**触发条件**: Kafka 服务未启动 / 网络故障

**系统行为**:
```python
# Kafka Consumer 初始化
def create_kafka_consumer():
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKERS,
            group_id="execution_nodes"
        )
        return consumer

    except KafkaConnectionError as e:
        GLOG.ERROR(f"Failed to connect to Kafka: {e}")
        # 重试逻辑
        retry_with_backoff(create_kafka_consumer, max_retries=5)

# 消费循环中的错误处理
def kafka_consumer_loop():
    while True:
        try:
            messages = kafka_consumer.poll(timeout_ms=1000)
            # 处理消息

        except KafkaConnectionError:
            GLOG.WARN("Kafka connection lost, reconnecting...")
            time.sleep(5)
            # 自动重连
```

**验证点**:
- ✅ 连接失败被捕获
- ✅ 自动重试（指数退避）
- ✅ 告警通知

---

### 5.2 Redis连接失败
**场景描述**: ExecutionNode 无法连接到 Redis

**触发条件**: Redis 服务未启动 / 网络故障

**系统行为**:
```python
# Redis 连接池配置
redis_pool = redis.ConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    retry_on_timeout=True,  # 自动重试
    socket_connect_timeout=5
)

# 心跳线程捕获异常
def heartbeat_thread():
    while True:
        try:
            redis.set(f"heartbeat:node:{node_id}", "alive", ex=30)
            time.sleep(10)

        except redis.ConnectionError:
            GLOG.ERROR("Redis connection lost")
            # Node 进入降级模式
            # 继续处理 Kafka 消息，但心跳停止
            time.sleep(10)
```

**验证点**:
- ✅ 连接失败被捕获
- ✅ 自动重试
- ✅ 降级模式运行

---

### 5.3 数据库连接失败
**场景描述**: 无法连接到 MySQL 数据库

**触发条件**: 数据库服务未启动 / 网络故障

**系统行为**:
```python
# 数据库操作使用 @retry 装饰器
@retry(max_try=3, delay=1)
def save_portfolio_state(portfolio_id: str):
    try:
        db.execute(
            "UPDATE portfolios SET state = ? WHERE portfolio_id = ?",
            (state, portfolio_id)
        )
    except DatabaseError as e:
        GLOG.ERROR(f"Database error: {e}")
        raise  # 触发重试

# 如果重试失败
if save_portfolio_state.failed:
    GLOG.CRITICAL("Failed to save portfolio state after 3 retries")
    # 缓存到本地，稍后重试
    local_cache.append(portfolio_state)
```

**验证点**:
- ✅ 连接失败自动重试
- ✅ 重试失败后本地缓存
- ✅ 告警通知

---

### 5.4 外部数据源断连
**场景描述**: Data 模块无法连接到外部数据源（Tushare/券商API）

**触发条件**: 外部API故障 / 网络问题

**系统行为**:
```python
# Data 模块
def get_quotes_from_source(codes: List[str]):
    try:
        quotes = tushare_api.get_quotes(codes)
        return quotes

    except TushareError as e:
        GLOG.ERROR(f"Tushare API error: {e}")

        # 尝试备用数据源
        quotes = akshare_api.get_quotes(codes)
        return quotes

    except Exception as e:
        GLOG.CRITICAL(f"All data sources failed: {e}")
        # 返回空数据，触发告警
        return []

# 监控数据源健康
def monitor_data_source_health():
    if len(quotes) == 0:
        GLOG.WARN("No quotes received, data source may be down")
        send_alert("Data source down")
```

**验证点**:
- ✅ 主数据源失败自动切换
- ✅ 告警通知
- ✅ 不推送无效数据

---

### 5.5 TradeGateway连接失败
**场景描述**: TradeGateway 无法连接到券商API

**触发条件**: 券商交易接口故障 / 网络问题

**系统行为**:
```python
# TradeGateway
def submit_order_to_broker(order: Order, broker: IBroker):
    try:
        result = broker.submit_order(order)
        return result

    except BrokerConnectionError as e:
        GLOG.ERROR(f"Broker connection failed: {e}")

        # 标记订单为提交失败
        order.status = ORDER_STATUS.SUBMIT_FAILED
        order.error = str(e)

        # 发送 EventOrderSubmitFailed 到 Portfolio
        self.send_to_portfolio(order.portfolio_id, EventOrderSubmitFailed(...))

        # 重试逻辑
        retry_later(order)

# Portfolio 处理提交失败
def on_order_submit_failed(event: EventOrderSubmitFailed):
    GLOG.ERROR(f"Order submit failed: {event.error}")
    # 记录失败日志
    # 等待手动干预或自动重试
```

**验证点**:
- ✅ 连接失败被捕获
- ✅ 订单状态更新
- ✅ Portfolio 收到失败通知

---

### 5.6 Kafka消息积压
**场景描述**: ExecutionNode 消费速度 < 生产速度，消息积压

**触发条件**: Portfolio 处理慢 / 消息量大

**系统行为**:
```python
# 监控 Kafka Lag
def monitor_kafka_lag():
    consumer = KafkaConsumer()
    topics = ["market.data.cn"]

    while True:
        # 获取 consumer lag
        partitions = consumer.end_offsets(consumer.assignment())
        for tp, offset in partitions.items():
            lag = offset - consumer.position(tp)
            if lag > 1000:
                GLOG.WARN(f"Kafka lag high: {lag} messages")
                # 触发告警
                send_alert(f"Kafka lag: {lag}")
                # 考虑扩容 Node

        time.sleep(10)
```

**验证点**:
- ✅ Lag 监控
- ✅ 告警触发
- ✅ 自动扩容建议

---

### 5.7 Redis内存不足
**场景描述**: Redis 内存使用率过高

**触发条件**: 缓存数据过多 / 未设置过期时间

**系统行为**:
```python
# 监控 Redis 内存
def monitor_redis_memory():
    info = redis.info("memory")
    used_memory = info["used_memory"]
    max_memory = info["maxmemory"]

    usage_pct = (used_memory / max_memory) * 100
    if usage_pct > 80:
        GLOG.WARN(f"Redis memory usage: {usage_pct}%")
        # 触发告警
        send_alert(f"Redis memory high: {usage_pct}%")
        # 清理过期缓存
        redis.delete_expired_keys()
```

**验证点**:
- ✅ 内存监控
- ✅ 告警触发
- ✅ 自动清理

---

### 5.8 数据库连接池耗尽
**场景描述**: 数据库连接池全部占用

**触发条件**: 高并发写入 / 连接泄漏

**系统行为**:
```python
# 数据库连接池配置
db_pool = sqlalchemy.create_engine(
    DATABASE_URL,
    pool_size=20,        # 最大连接数
    max_overflow=10,     # 额外连接数
    pool_timeout=30,     # 获取连接超时
    pool_recycle=3600    # 连接回收时间
)

# 连接超时处理
try:
    with db_pool.connect() as conn:
        result = conn.execute(query)
except TimeoutError:
    GLOG.ERROR("Database connection pool exhausted")
    # 等待或降级
    time.sleep(1)
```

**验证点**:
- ✅ 连接超时被捕获
- ✅ 错误日志记录
- ✅ 自动重试

---

### 5.9 网络分区
**场景描述**: ExecutionNode 与 Kafka/Redis 网络分区

**触发条件**: 网络故障 / 路由问题

**系统行为**:
```python
# 检测网络分区
def detect_network_partition():
    # 检查 Kafka 连接
    try:
        kafka.consumer.position()
    except KafkaError:
        GLOG.ERROR("Cannot reach Kafka")
        kafka_available = False

    # 检查 Redis 连接
    try:
        redis.ping()
    except RedisError:
        GLOG.ERROR("Cannot reach Redis")
        redis_available = False

    # 网络分区判断
    if not kafka_available and not redis_available:
        GLOG.CRITICAL("Network partition detected!")
        # Node 进入隔离模式
        # 停止处理新消息
        # 保存本地状态
        # 等待网络恢复
```

**验证点**:
- ✅ 网络分区检测
- ✅ 隔离模式运行
- ✅ 网络恢复后自动重连

---

### 5.10 时钟同步失败
**场景描述**: Node 时钟与标准时间偏差过大

**触发条件**: NTP 服务故障

**系统行为**:
```python
# 监控时钟偏差
def monitor_clock_skew():
    # 使用 NTP 查询当前时间
    ntp_time = ntp_client.request()
    local_time = time.time()

    skew = abs(ntp_time - local_time)
    if skew > 5:  # 偏差超过5秒
        GLOG.WARN(f"Clock skew detected: {skew}s")
        # 触发告警
        send_alert(f"Clock skew: {skew}s")
        # 尝试同步时钟
        os.system("ntpdate pool.ntp.org")
```

**验证点**:
- ✅ 时钟偏差监控
- ✅ 自动同步
- ✅ 告警通知

---

## 6. 交易异常情况 (12个场景)

### 6.1 资金不足
**场景描述**: Portfolio 提交订单时资金不足

**触发条件**: 订单金额 > 可用资金

**系统行为**:
```python
# Portfolio 提交订单前检查
def submit_order(self, signal: Signal):
    # 计算需要的资金
    required_cash = signal.volume * signal.price * (1 + commission_rate)

    # 检查可用资金
    if required_cash > self.cash:
        GLOG.WARN(f"Insufficient funds: need {required_cash}, have {self.cash}")
        # 订单被拒绝
        return None

    # 提交订单
    order = self.create_order(signal)
    return order

# 或在 Sizer 中检查
class FixedSizer(BaseSizer):
    def cal(self, portfolio_info: Dict, signal: Signal) -> Order:
        available_cash = portfolio_info["cash"]
        max_volume = int(available_cash / signal.price)

        if signal.volume > max_volume:
            signal.volume = max_volume  # 调整订单量

        return Order(..., volume=signal.volume)
```

**验证点**:
- ✅ 订单提交前检查
- ✅ 订单量调整或拒绝
- ✅ 日志记录

---

### 6.2 持仓超限
**场景描述**: 单股持仓超过风控限制

**触发条件**: PositionRatioRisk 风控触发

**系统行为**:
```python
# PositionRatioRisk 风控处理
class PositionRatioRisk(BaseRiskManagement):
    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        current_position = portfolio_info["positions"].get(order.code, 0)
        total_value = portfolio_info["total_value"]

        # 计算新持仓比例
        new_position_value = (current_position + order.volume) * order.price
        new_ratio = new_position_value / total_value

        # 检查是否超过限制
        if new_ratio > self.max_position_ratio:
            GLOG.WARN(f"Position ratio {new_ratio} exceeds limit {self.max_position_ratio}")

            # 调整订单量
            max_volume = int((self.max_position_ratio * total_value) / order.price) - current_position
            order.volume = max_volume

        return order
```

**验证点**:
- ✅ 风控检查
- ✅ 订单量调整
- ✅ 日志记录

---

### 6.3 止损触发
**场景描述**: LossLimitRisk 风控触发，生成平仓信号

**触发条件**: 持仓亏损超过止损线

**系统行为**:
```python
# LossLimitRisk 主动风控
class LossLimitRisk(BaseRiskManagement):
    def generate_signals(self, portfolio_info: Dict, event: EventPriceUpdate) -> List[Signal]:
        signals = []

        for code, position in portfolio_info["positions"].items():
            # 计算当前盈亏
            current_price = event.price
            cost_price = position.cost
            pnl_ratio = (current_price - cost_price) / cost_price

            # 检查止损
            if pnl_ratio < -self.loss_limit:
                GLOG.WARN(f"Stop loss triggered for {code}: PnL {pnl_ratio}")

                # 生成平仓信号
                signal = Signal(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,  # 平仓
                    volume=position.volume,
                    reason=f"Stop loss: {pnl_ratio:.2%}"
                )
                signals.append(signal)

        return signals
```

**验证点**:
- ✅ 实时监控盈亏
- ✅ 触发平仓信号
- ✅ 策略信号被风控信号覆盖

---

### 6.4 止盈触发
**场景描述**: ProfitLimitRisk 风控触发，生成平仓信号

**触发条件**: 持仓盈利超过止盈线

**系统行为**: 同6.3（LossLimitRisk）

**验证点**:
- ✅ 盈利监控
- ✅ 止盈信号生成

---

### 6.5 订单超时
**场景描述**: 订单提交后长时间未成交

**触发条件**: 交易所未返回成交回报

**系统行为**:
```python
# Portfolio 监控未成交订单
def check_pending_orders():
    for order in self.pending_orders:
        # 检查订单超时（如30秒）
        if datetime.now() - order.submit_time > timedelta(seconds=30):
            GLOG.WARN(f"Order {order.order_id} timeout")

            # 撤单
            cancel_order_result = self.cancel_order(order.order_id)

            if cancel_order_result.success:
                order.status = ORDER_STATUS.CANCELLED
            else:
                GLOG.ERROR(f"Failed to cancel order {order.order_id}")
```

**验证点**:
- ✅ 超时检测
- ✅ 自动撤单
- ✅ 日志记录

---

### 6.6 价格异常
**场景描述**: 收到异常价格数据（如价格跳变过大）

**触发条件**: 数据源错误 / 闪崩

**系统行为**:
```python
# Portfolio 处理价格更新
def on_price_update(self, event: EventPriceUpdate):
    # 检查价格合理性
    last_price = self.price_cache.get(event.code)
    if last_price:
        change_ratio = abs(event.price - last_price) / last_price

        # 价格变化超过10%认为异常
        if change_ratio > 0.1:
            GLOG.WARN(f"Abnormal price change for {event.code}: {change_ratio:.2%}")
            # 丢弃该价格数据
            return

    # 正常处理
    self.price_cache[event.code] = event.price
    self.strategy.cal(self.portfolio_info, event)
```

**验证点**:
- ✅ 价格合理性检查
- ✅ 异常数据丢弃
- ✅ 告警通知

---

### 6.7 数据缺失
**场景描述**: 某只股票的价格数据长时间未更新

**触发条件**: 数据源故障 / 股票停牌

**系统行为**:
```python
# Portfolio 监控数据更新
def check_data_freshness():
    for code in self.interested_codes:
        last_update = self.price_cache.get_timestamp(code)

        # 超过5分钟未更新
        if datetime.now() - last_update > timedelta(minutes=5):
            GLOG.WARN(f"No data for {code} for 5 minutes")

            # 生成空信号或跳过策略计算
            # 或触发告警
            send_alert(f"No data for {code}")
```

**验证点**:
- ✅ 数据新鲜度监控
- ✅ 告警通知
- ✅ 策略跳过

---

### 6.8 重复消息
**场景描述**: Kafka 投递重复消息

**触发条件**: Kafka 幂等性配置不当

**系统行为**:
```python
# Portfolio 处理事件时检查重复
def on_event(self, event: EventBase):
    # 检查事件是否已处理（通过事件ID）
    if event.event_id in self.processed_events:
        GLOG.WARN(f"Duplicate event {event.event_id}, skipping")
        return

    # 标记为已处理
    self.processed_events.add(event.event_id)

    # 处理事件
    # ...
```

**验证点**:
- ✅ 重复检测
- ✅ 幂等处理
- ✅ 日志记录

---

### 6.9 消息乱序
**场景描述**: 同一股票的价格事件乱序到达

**触发条件**: 网络延迟 / Kafka 分区问题

**系统行为**:
```python
# Portfolio 处理价格更新时检查时间戳
def on_price_update(self, event: EventPriceUpdate):
    last_timestamp = self.price_cache.get_timestamp(event.code)

    # 检查时间戳
    if event.timestamp < last_timestamp:
        GLOG.WARN(f"Out-of-order price for {event.code}: {event.timestamp} < {last_timestamp}")
        # 丢弃旧数据
        return

    # 正常处理
    self.price_cache[event.code] = event.price
```

**验证点**:
- ✅ 时间戳检查
- ✅ 乱序检测
- ✅ 旧数据丢弃

---

### 6.10 订单部分成交后撤单
**场景描述**: 订单部分成交后用户撤单

**触发条件**: Portfolio 发起撤单

**系统行为**:
```python
# Portfolio 处理撤单确认
def on_order_cancel_ack(self, event: EventOrderCancelAck):
    order = self.get_order(event.order_id)

    if event.status == CANCEL_STATUS.PARTIALLY_FILLED:
        # 部分成交后撤单
        filled_volume = event.filled_volume
        remaining_volume = order.original_volume - filled_volume

        # 更新持仓（已成交部分）
        self.position[event.code].volume += filled_volume

        # 标记订单为已撤单
        order.status = ORDER_STATUS.CANCELLED
        order.filled_volume = filled_volume

        GLOG.INFO(f"Order {order.order_id} partially filled and cancelled: {filled_volume}/{order.original_volume}")
```

**验证点**:
- ✅ 部分成交正确处理
- ✅ 持仓正确更新
- ✅ 订单状态正确

---

### 6.11 手动干预订单
**场景描述**: 运维人员手动干预订单（如强制撤单）

**触发条件**: API 调用 / 运维操作

**系统行为**:
```python
# API Gateway 提供
@app.post("/api/orders/{order_id}/cancel")
def cancel_order(order_id: str, force: bool = False):
    if force:
        # 强制撤单（绕过 Portfolio）
        kafka.send("orders.cn", {
            "action": "force_cancel",
            "order_id": order_id
        })
    else:
        # 正常撤单流程（通过 Portfolio）
        kafka.send("portfolio.control", {
            "action": "cancel_order",
            "portfolio_id": "...",
            "order_id": order_id
        })

    return {"status": "success"}
```

**验证点**:
- ✅ API 接口可用
- ✅ 强制撤单生效
- ✅ Portfolio 收到通知

---

### 6.12 批量订单处理
**场景描述**: Portfolio 同时生成多个订单

**触发条件**: 多个信号同时触发

**系统行为**:
```python
# Portfolio 处理多个信号
def on_signals(self, signals: List[Signal]):
    orders = []

    for signal in signals:
        # 通过风控
        signal = self.apply_risk_managements(signal)

        # 通过 Sizer
        order = self.sizer.cal(self.portfolio_info, signal)

        orders.append(order)

    # 批量提交订单
    for order in orders:
        self.submit_order(order)

    # 或批量提交到 Kafka
    kafka.send_batch("orders.cn", orders)
```

**验证点**:
- ✅ 批量订单正确处理
- ✅ 风控逐个检查
- ✅ Sizer 逐个计算

---

## 7. 系统异常情况 (9个场景)

### 7.1 内存泄漏
**场景描述**: ExecutionNode 长时间运行后内存持续增长

**触发条件**: 程序bug / 对象未释放

**系统行为**:
```python
# 监控内存使用
def monitor_memory():
    import psutil
    process = psutil.Process()

    while True:
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        GLOG.INFO(f"Memory usage: {memory_mb:.2f} MB")

        if memory_mb > 1000:  # 超过1GB
            GLOG.WARN("Memory usage high, possible leak")
            # 触发告警
            send_alert(f"Memory leak detected: {memory_mb} MB")
            # 建议重启 Node

        time.sleep(60)
```

**验证点**:
- ✅ 内存监控
- ✅ 泄漏检测
- ✅ 告警通知

---

### 7.2 CPU占用过高
**场景描述**: ExecutionNode CPU 占用率过高

**触发条件**: 死循环 / 算法复杂度高

**系统行为**:
```python
# 监控 CPU 使用
def monitor_cpu():
    import psutil

    while True:
        cpu_pct = psutil.cpu_percent(interval=1)

        if cpu_pct > 90:
            GLOG.WARN(f"CPU usage high: {cpu_pct}%")
            # 检查哪个线程占用高
            for thread in threading.enumerate():
                # 分析线程栈
                pass

        time.sleep(10)
```

**验证点**:
- ✅ CPU 监控
- ✅ 高占用告警
- ✅ 问题诊断

---

### 7.3 磁盘空间不足
**场景描述**: 服务器磁盘空间不足

**触发条件**: 日志文件过大 / 数据库增长

**系统行为**:
```python
# 监控磁盘空间
def monitor_disk():
    import shutil

    while True:
        disk = shutil.disk_usage("/")
        usage_pct = disk.used / disk.total * 100

        if usage_pct > 90:
            GLOG.WARN(f"Disk usage high: {usage_pct:.2f}%")
            # 清理旧日志
            clean_old_logs()
            # 告警
            send_alert(f"Disk space low: {usage_pct:.2f}%")

        time.sleep(300)  # 每5分钟检查
```

**验证点**:
- ✅ 磁盘监控
- ✅ 自动清理
- ✅ 告警通知

---

### 7.4 线程死锁
**场景描述**: ExecutionNode 线程死锁

**触发条件**: 锁使用不当

**系统行为**:
```python
# 监控线程状态
def monitor_threads():
    while True:
        for thread in threading.enumerate():
            # 检查线程是否阻塞
            if thread.is_alive() and is_blocked(thread):
                GLOG.WARN(f"Thread {thread.name} may be deadlocked")
                # 输出线程栈
                traceback.print_stack(thread)

        time.sleep(10)
```

**验证点**:
- ✅ 线程监控
- ✅ 死锁检测
- ✅ 栈信息输出

---

### 7.5 数据库死锁
**场景描述**: 数据库事务死锁

**触发条件**: 并发事务冲突

**系统行为**:
```python
# 数据库操作捕获死锁异常
@retry(max_try=3, delay=1)
def update_portfolio_state(portfolio_id: str, state: dict):
    try:
        db.execute(
            "UPDATE portfolios SET state = ? WHERE portfolio_id = ?",
            (json.dumps(state), portfolio_id)
        )
        db.commit()

    except DatabaseError as e:
        if "Deadlock" in str(e):
            GLOG.WARN(f"Database deadlock detected: {e}")
            db.rollback()
            raise  # 触发重试
        else:
            GLOG.ERROR(f"Database error: {e}")
            raise
```

**验证点**:
- ✅ 死锁检测
- ✅ 自动重试
- ✅ 日志记录

---

### 7.6 消息队列溢出
**场景描述**: Portfolio Queue 满载

**触发条件**: 消息生产速度 > 消费速度

**系统行为**:
```python
# Kafka 消费线程检测 Queue 满载
def route_message(self, event: EventPriceUpdate):
    for portfolio_id in self.get_interested_portfolios(event.code):
        processor = self.processors[portfolio_id]

        # 检查 Queue 是否满
        if processor.queue.full():
            GLOG.WARN(f"Portfolio {portfolio_id} queue full, dropping event")
            # 触发告警
            send_alert(f"Portfolio {portfolio_id} queue full")
            # 丢弃消息或阻塞
            continue

        # 正常放入
        processor.queue.put(event, block=False)
```

**验证点**:
- ✅ Queue 满载检测
- ✅ Backpressure 触发
- ✅ 告警通知

---

### 7.7 端口占用
**场景描述**: 服务端口被占用

**触发条件**: 服务未正常关闭 / 重复启动

**系统行为**:
```python
# 启动服务前检查端口
def check_port_available(port: int):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(("localhost", port))
        if result == 0:
            raise RuntimeError(f"Port {port} already in use")

# 启动前检查
check_port_available(8000)  # API Gateway
check_port_available(9092)  # Kafka
check_port_available(6379)  # Redis
```

**验证点**:
- ✅ 端口检查
- ✅ 启动前验证
- ✅ 错误提示

---

### 7.8 配置错误
**场景描述**: 配置文件或环境变量错误

**触发条件**: 人为错误 / 部署问题

**系统行为**:
```python
# 启动时验证配置
def validate_config():
    errors = []

    # 检查必需的环境变量
    required_vars = ["REDIS_HOST", "KAFKA_BROKERS", "DATABASE_URL"]
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required env var: {var}")

    # 检查配置值合法性
    kafka_brokers = os.getenv("KAFKA_BROKERS")
    if not kafka_brokers:
        errors.append("KAFKA_BROKERS cannot be empty")

    if errors:
        GLOG.ERROR("Configuration errors:")
        for error in errors:
            GLOG.ERROR(f"  - {error}")
        sys.exit(1)

# 启动时调用
validate_config()
```

**验证点**:
- ✅ 配置验证
- ✅ 启动前检查
- ✅ 错误提示

---

### 7.9 依赖服务未就绪
**场景描述**: 依赖的服务（Redis/Kafka/数据库）未启动

**触发条件**: 服务启动顺序错误

**系统行为**:
```python
# 启动前等待依赖服务
def wait_for_service(host: str, port: int, timeout: int = 60):
    import socket

    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                GLOG.INFO(f"Service {host}:{port} is ready")
                return True
        except ConnectionRefusedError:
            time.sleep(1)

    raise RuntimeError(f"Service {host}:{port} not ready after {timeout}s")

# 启动时等待
wait_for_service("redis", 6379)
wait_for_service("kafka1", 9092)
wait_for_service("mysql", 3306)
```

**验证点**:
- ✅ 服务就绪检查
- ✅ 自动等待
- ✅ 超时错误

---

## 8. 运维操作 (8个场景)

### 8.1 手动触发负载均衡
**场景描述**: 运维人员手动触发 Portfolio 负载均衡

**触发条件**: POST /api/schedule/rebalance

**系统行为**:
```python
# API Gateway
@app.post("/api/schedule/rebalance")
def manual_rebalance():
    # 发送 Kafka 命令到 Scheduler
    kafka.send("scheduler.control", {
        "action": "rebalance",
        "timestamp": datetime.now().isoformat()
    })

    return {"status": "rebalancing initiated"}

# Scheduler 收到命令
def on_rebalance_command():
    # 立即执行调度循环
    self.schedule()
```

**验证点**:
- ✅ API 接口可用
- ✅ 调度立即执行
- ✅ Portfolio 迁移完成

---

### 8.2 紧急停止所有交易
**场景描述**: 紧急情况下停止所有 Portfolio

**触发条件**: POST /api/emergency/stop

**系统行为**:
```python
# API Gateway
@app.post("/api/emergency/stop")
def emergency_stop():
    # 发送停止命令到所有 Node
    kafka.send("execution.control", {
        "action": "stop_all_portfolios",
        "timestamp": datetime.now().isoformat()
    })

    # 同时发送到 LiveEngine
    kafka.send("livecore.control", {
        "action": "stop",
        "reason": "emergency"
    })

    return {"status": "emergency stop initiated"}

# ExecutionNode 收到命令
def on_stop_all_portfolios():
    for portfolio_id in list(self.portfolios.keys()):
        self.stop_portfolio(portfolio_id)
```

**验证点**:
- ✅ API 接口可用
- ✅ 所有 Portfolio 停止
- ✅ 订单撤回

---

### 8.3 数据库备份
**场景描述**: 定时备份数据库

**触发条件**: Cron 任务 / 手动触发

**系统行为**:
```bash
# 备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/mysql"

# 备份 MySQL
mysqldump -u root -p${MYSQL_ROOT_PASSWORD} \
  ginkgo > ${BACKUP_DIR}/ginkgo_${DATE}.sql

# 压缩备份
gzip ${BACKUP_DIR}/ginkgo_${DATE}.sql

# 删除7天前的备份
find ${BACKUP_DIR} -name "ginkgo_*.sql.gz" -mtime +7 -delete
```

**验证点**:
- ✅ 备份成功
- ✅ 压缩存储
- ✅ 旧备份清理

---

### 8.4 数据库恢复
**场景描述**: 从备份恢复数据库

**触发条件**: 数据损坏 / 误删除

**系统行为**:
```bash
# 恢复脚本
#!/bin/bash
BACKUP_FILE=$1

# 检查备份文件
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# 停止所有服务
docker-compose down

# 恢复数据库
gunzip < ${BACKUP_FILE} | mysql -u root -p${MYSQL_ROOT_PASSWORD} ginkgo

# 启动服务
docker-compose up -d
```

**验证点**:
- ✅ 备份文件检查
- ✅ 数据恢复成功
- ✅ 服务正常启动

---

### 8.5 系统升级
**场景描述**: 升级系统到新版本

**触发条件**: 发布新版本

**系统行为**:
```bash
# 滚动升级脚本
#!/bin/bash

# 1. 拉取新镜像
docker pull ginkgo-execution-node:v2.0

# 2. 逐个升级 ExecutionNode
for node in node_a node_b node_c; do
    echo "Upgrading ${node}..."

    # 停止旧容器
    docker stop ${node}

    # 启动新容器
    docker run -d --name ${node} ginkgo-execution-node:v2.0

    # 等待 Node 就绪
    sleep 10

    echo "${node} upgraded"
done

# 3. 升级 LiveCore
docker-compose up -d --force-recreate livecore

# 4. 升级 API Gateway
docker-compose up -d --force-recreate api-gateway
```

**验证点**:
- ✅ 滚动升级
- ✅ 无服务中断
- ✅ 新版本验证

---

### 8.6 配置热更新
**场景描述**: 更新系统配置而不重启

**触发条件**: 配置文件变更

**系统行为**:
```python
# 配置监控线程
def config_watcher():
    last_modified = 0

    while True:
        config_file = "/etc/ginkgo/config.yaml"

        # 检查文件修改时间
        current_modified = os.path.getmtime(config_file)

        if current_modified != last_modified:
            GLOG.INFO("Config file changed, reloading...")

            # 重新加载配置
            new_config = load_config(config_file)

            # 应用新配置
            apply_config(new_config)

            last_modified = current_modified

        time.sleep(5)
```

**验证点**:
- ✅ 配置文件监控
- ✅ 热重载
- ✅ 无需重启

---

### 8.7 日志清理
**场景描述**: 清理旧日志文件

**触发条件**: 定时任务 / 磁盘空间不足

**系统行为**:
```bash
# 日志清理脚本
#!/bin/bash
LOG_DIR="/var/log/ginkgo"
RETENTION_DAYS=30

# 清理旧日志
find ${LOG_DIR} -name "*.log" -mtime +${RETENTION_DAYS} -delete

# 压缩7天前的日志
find ${LOG_DIR} -name "*.log" -mtime +7 -exec gzip {} \;

echo "Log cleanup completed"
```

**验证点**:
- ✅ 旧日志删除
- ✅ 自动压缩
- ✅ 磁盘空间释放

---

### 8.8 监控告警配置
**场景描述**: 配置监控指标和告警规则

**触发条件**: 运维配置

**系统行为**:
```yaml
# Prometheus 告警规则
groups:
  - name: ginkgo_alerts
    rules:
      # Node 心跳丢失
      - alert: NodeHeartbeatLost
        expr: time() - node_heartbeat_timestamp_seconds > 30
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Node heartbeat lost: {{ $labels.node_id }}"

      # Portfolio Queue 满载
      - alert: PortfolioQueueFull
        expr: portfolio_queue_size / portfolio_queue_max_size > 0.9
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Portfolio queue full: {{ $labels.portfolio_id }}"

      # Kafka Lag 过高
      - alert: KafkaLagHigh
        expr: kafka_consumer_lag > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Kafka lag high: {{ $labels.topic }}"
```

**验证点**:
- ✅ 监控指标采集
- ✅ 告警规则匹配
- ✅ 告警通知发送

---

## 9. 边缘情况 (10个场景)

### 9.1 消息重复消费
**场景描述**: Kafka Consumer 重启后重复消费消息

**触发条件**: Offset 未提交 / Consumer 组重平衡

**系统行为**:
```python
# Portfolio 幂等处理
class Portfolio:
    def __init__(self):
        self.processed_events = set()  # 已处理事件ID集合
        self.max_cache_size = 10000    # 最大缓存

    def on_event(self, event: EventBase):
        # 检查是否已处理
        if event.event_id in self.processed_events:
            GLOG.DEBUG(f"Duplicate event {event.event_id}, skipping")
            return

        # 处理事件
        self.process_event(event)

        # 标记为已处理
        self.processed_events.add(event.event_id)

        # 限制缓存大小
        if len(self.processed_events) > self.max_cache_size:
            # 清理旧事件（FIFO）
            self.processed_events = set(list(self.processed_events)[1000:])
```

**验证点**:
- ✅ 重复检测
- ✅ 幂等处理
- ✅ 缓存管理

---

### 9.2 消息丢失
**场景描述**: Kafka 消息丢失

**触发条件**: Broker 故障 / 副本不足

**系统行为**:
```python
# Kafka Producer 配置防止丢失
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKERS,
    # 幂等性
    enable_idempotence=True,
    # 确认所有副本
    acks="all",
    # 重试
    retries=3,
    # 批量发送
    batch_size=16384
)

# Kafka Consumer 配置
consumer = KafkaConsumer(
    # 自动提交关闭（手动控制）
    enable_auto_commit=False,
    # 从最早的消息开始消费
    auto_offset_reset="earliest"
)
```

**验证点**:
- ✅ Producer 幂等性
- ✅ 确认所有副本
- ✅ Consumer 手动提交

---

### 9.3 极端行情（闪崩）
**场景描述**: 市场出现极端行情（如单日跌停）

**触发条件**: 市场异常

**系统行为**:
```python
# Portfolio 价格合理性检查
def on_price_update(self, event: EventPriceUpdate):
    last_price = self.price_cache.get(event.code)

    if last_price:
        change_ratio = abs(event.price - last_price) / last_price

        # 涨跌停检查（如±10%）
        if change_ratio > 0.1:
            GLOG.WARN(f"Limit move detected for {event.code}: {change_ratio:.2%}")

            # 触发风控
            # 1. 暂停新开仓
            self.pause_opening_position = True

            # 2. 生成平仓信号（如果持仓）
            if self.get_position(event.code).volume > 0:
                signal = Signal(
                    code=event.code,
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"Limit move: {change_ratio:.2%}"
                )
                self.submit_order_from_signal(signal)

            # 3. 告警
            send_alert(f"Limit move: {event.code} {change_ratio:.2%}")

            return  # 不更新价格缓存

    # 正常处理
    self.price_cache[event.code] = event.price
```

**验证点**:
- ✅ 极端行情检测
- ✅ 风控触发
- ✅ 告警通知

---

### 9.4 交易时间外
**场景描述**: 非交易时间收到价格数据

**触发条件**: 数据源错误 / 时区问题

**系统行为**:
```python
# Portfolio 检查交易时间
def on_price_update(self, event: EventPriceUpdate):
    # 检查是否在交易时间内
    current_time = datetime.now().time()
    if not (time(9, 30) <= current_time <= time(15, 0)):
        GLOG.WARN(f"Received data outside trading hours: {current_time}")
        # 丢弃数据
        return

    # 检查日期（非周末）
    if datetime.now().weekday() >= 5:  # 周六、周日
        GLOG.WARN("Received data on weekend")
        return

    # 正常处理
    self.process_price_update(event)
```

**验证点**:
- ✅ 交易时间检查
- ✅ 非交易数据丢弃
- ✅ 日志记录

---

### 9.5 零持仓交易
**场景描述**: Portfolio 尝试平仓零持仓的股票

**触发条件**: 策略错误 / 信号重复

**系统行为**:
```python
# Sizer 检查持仓
class FixedSizer(BaseSizer):
    def cal(self, portfolio_info: Dict, signal: Signal) -> Order:
        current_position = portfolio_info["positions"].get(signal.code, 0)

        # 平仓信号检查
        if signal.direction == DIRECTION_TYPES.SHORT:
            if current_position == 0:
                GLOG.WARN(f"Cannot close zero position for {signal.code}")
                return None  # 不生成订单

        # 正常处理
        return Order(...)
```

**验证点**:
- ✅ 持仓检查
- ✅ 无效订单阻止
- ✅ 日志记录

---

### 9.6 除权除息
**场景描述**: 股票除权除息，价格调整

**触发条件**: 公司分红 / 拆股

**系统行为**:
```python
# Data 模块推送除权除息事件
class EventDividendAdjustment(EventBase):
    code: str
    ex_date: datetime
    dividend: float  # 每股分红
    split_ratio: float  # 拆股比例（如2表示1股变2股）

# Portfolio 处理除权除息
def on_dividend_adjustment(self, event: EventDividendAdjustment):
    # 1. 调整持仓数量
    position = self.get_position(event.code)
    if event.split_ratio > 1:
        position.volume *= event.split_ratio

    # 2. 调整成本价
    position.cost /= event.split_ratio

    # 3. 现金分红入账
    if event.dividend > 0:
        dividend_amount = position.volume * event.dividend
        self.cash += dividend_amount

    # 4. 保存到数据库
    self.save_portfolio_state()
```

**验证点**:
- ✅ 持仓数量调整
- ✅ 成本价调整
- ✅ 分红入账

---

### 9.7 股票停牌
**场景描述**: Portfolio 订阅的股票停牌

**触发条件**: 公司公告

**系统行为**:
```python
# Data 模块推送停牌事件
class EventStockSuspension(EventBase):
    code: str
    suspend_date: datetime
    reason: str

# Portfolio 处理停牌
def on_stock_suspension(self, event: EventStockSuspension):
    GLOG.INFO(f"Stock {event.code} suspended: {event.reason}")

    # 1. 从兴趣集移除
    if event.code in self.interested_codes:
        self.interested_codes.remove(event.code)

    # 2. 更新 interest_map
    self.node.update_interest_map(self.portfolio_id, self.interested_codes)

    # 3. 如果有持仓，标记为不可交易
    if self.get_position(event.code).volume > 0:
        GLOG.WARN(f"Stock {event.code} suspended with position, cannot close")
        # 设置停牌标记
        self.get_position(event.code).suspended = True
```

**验证点**:
- ✅ 停牌检测
- ✅ 兴趣集更新
- ✅ 持仓标记

---

### 9.8 资金分红入账
**场景描述**: Portfolio 持仓分红入账

**触发条件**: 公司分红派息

**系统行为**: 见9.6（除权除息）

**验证点**:
- ✅ 分红金额正确
- ✅ 现金增加
- ✅ 数据库记录

---

### 9.9 系统时间回拨
**场景描述**: 服务器时间被回拨

**触发条件**: NTP 同步错误 / 手动调整

**系统行为**:
```python
# 检测时间回拨
def detect_time_backward():
    last_timestamp = get_last_timestamp()
    current_timestamp = time.time()

    if current_timestamp < last_timestamp:
        GLOG.ERROR(f"Time backward detected: {current_timestamp} < {last_timestamp}")

        # 触发告警
        send_alert("Time backward detected!")

        # 停止处理新消息
        # 或等待时间恢复正常
        return False

    return True

# 处理消息前检查
def on_event(self, event: EventBase):
    if not detect_time_backward():
        return

    # 正常处理
    process_event(event)
```

**验证点**:
- ✅ 时间回拨检测
- ✅ 告警通知
- ✅ 消息暂停

---

### 9.10 并发控制失败
**场景描述**: 并发控制机制失效

**触发条件**: 锁失效 / 竞态条件

**系统行为**:
```python
# 使用分布式锁（Redis）
def acquire_lock(portfolio_id: str):
    lock_key = f"lock:portfolio:{portfolio_id}"

    # 尝试获取锁（超时30秒）
    acquired = redis.set(lock_key, "locked", nx=True, ex=30)

    if not acquired:
        GLOG.WARN(f"Failed to acquire lock for {portfolio_id}")
        return False

    return True

def release_lock(portfolio_id: str):
    lock_key = f"lock:portfolio:{portfolio_id}"
    redis.delete(lock_key)

# 使用锁
if acquire_lock(portfolio_id):
    try:
        # 执行操作
        update_portfolio(portfolio_id)
    finally:
        release_lock(portfolio_id)
```

**验证点**:
- ✅ 分布式锁
- ✅ 超时释放
- ✅ 异常处理

---

## 场景优先级说明

| 优先级 | 说明 | 场景数量 |
|--------|------|---------|
| P0 | 核心业务流程，必须正确处理 | 49 |
| P1 | 重要异常处理，影响系统可用性 | 28 |
| P2 | 运维辅助，提升可维护性 | 15 |

---

## 建议的实施优先级

### Phase 1: MVP (P0核心场景)
- 1.1-1.15: 正常业务流程（15个，含信号产生）
- 2.1-2.6: Portfolio生命周期（6个）
- 3.1-3.4: Node生命周期（4个）
- 5.1-5.3: 数据源和连接（3个）
- 6.1-6.6: 交易异常（6个）

### Phase 2: 可靠性增强 (P0+P1)
- 2.7-2.10: Portfolio故障恢复（4个）
- 3.5-3.8: Node管理（4个）
- 4.1-4.6: 系统组件管理（6个）
- 5.4-5.7: 数据源异常处理（4个）
- 6.7-6.12: 复杂交易场景（6个）
- 7.1-7.6: 系统异常（6个）

### Phase 3: 完善功能 (P1+P2)
- 8.1-8.8: 运维操作（8个）
- 9.1-9.10: 边缘情况（10个）
- 7.7-7.9: 系统配置（3个）
- 5.8-5.10: 高级连接处理（3个）

---

## 总结

**总计: 88个场景**（新增11个信号产生场景）

- **核心业务**: 15个场景（日常交易流程 + 信号产生）
  - 数据推送、订单处理（8个）
  - **信号产生（11个）：正常信号、买入/卖出、信号冲突、无信号、风控拦截/调整/覆盖、异常数据过滤、信号过期、频率限制**
- **Portfolio管理**: 10个场景（创建、启动、变更、停止、删除、迁移）
- **Node管理**: 8个场景（启动、停止、故障、扩容）
- **系统组件**: 6个场景（LiveEngine、Scheduler、Data、API Gateway）
- **数据连接**: 10个场景（Kafka、Redis、数据库、外部数据源）
- **交易异常**: 12个场景（资金、持仓、风控、订单异常）
- **系统异常**: 9个场景（内存、CPU、磁盘、死锁）
- **运维操作**: 8个场景（负载均衡、备份、升级、监控）
- **边缘情况**: 10个场景（重复、丢失、闪崩、停牌、分红）

所有场景都已在spec中涵盖相应的设计和解决方案。

## 信号产生流程总结

### 完整信号处理流程

```
市场数据到达（EventPriceUpdate）
    ↓
数据有效性验证（过滤异常数据）
    ↓
策略计算（BaseStrategy.cal）
    ├─ 数据缓存更新
    ├─ 指标计算（MA、RSI、MACD等）
    ├─ 信号条件判断
    └─ 生成Signal列表
    ↓
信号处理（Portfolio）
    ├─ 风控信号生成（主动风控）
    ├─ 风控信号优先检查
    │   ├─ 有风控信号 → 覆盖策略信号
    │   └─ 无风控信号 → 继续策略信号
    ├─ 策略信号应用风控（被动风控）
    │   ├─ 依次通过各风控模块
    │   ├─ 风控拦截 → 返回None
    │   └─ 风控调整 → 修改Signal.volume
    └─ 有效信号进入Sizer
    ↓
Sizer计算订单量
    ↓
生成Order并提交到Kafka
```

### 信号优先级

```
优先级从高到低：
1. 主动风控信号（止损、止盈、紧急平仓）
2. 被动风控拦截/调整
3. 策略信号
```
