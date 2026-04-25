# 组件 ID 自动注入重构

## 背景

策略、仓位管理器、风控组件在创建 Signal/Order 时需要手动传递 `portfolio_id`、`engine_id`、`task_id`。这三个 ID 是框架内部概念，用户通过 Web UI 编写组件时不应关心。

**现状问题：**
- 只有 `BaseStrategy` 有 `create_signal()` 帮助方法，`SizerBase` 和 `RiskBase` 没有
- 6 个策略绕过帮助方法直接构造 Signal
- 3 个 Sizer 全部手动构造 Order
- 9 个风控组件手动构造 Signal，其中多个漏传 `task_id` 或硬编码假值
- `run_id → task_id` 迁移时磁盘代码和 file 表代码不一致导致回测失败

## 设计

### 原则

- **工厂方法优先**：`create_signal()`/`create_order()` 是创建实体的推荐方式
- **全部替换**：现有所有组件代码改为使用工厂方法，不保留手动传参
- **不向后兼容**：构造函数 ID 参数改为可选，去掉非空校验

### 1. Signal/Order 构造函数

将 `portfolio_id`、`engine_id`、`task_id` 三个参数改为可选，默认 `""`，去掉非空校验。

**Signal** (`entities/signal.py`):
```python
def __init__(
    self,
    portfolio_id: str = "",     # 改为可选
    engine_id: str = "",        # 改为可选
    task_id: str = "",          # 改为可选
    code: str = "Default Signal Code",
    direction: DIRECTION_TYPES = None,
    reason: str = "no reason",
    ...
)
```

`set()` 方法中对应的三段校验删除（不再要求非空）。

**Order** (`entities/order.py`):
```python
def __init__(
    self,
    portfolio_id: str = "",     # 改为可选
    engine_id: str = "",        # 改为可选
    task_id: str = "",          # 改为可选
    code: str = "",
    ...
)
```

### 2. SizerBase 加 `create_order()`

**文件**: `src/ginkgo/trading/bases/sizer_base.py`

模仿 `BaseStrategy.create_signal()`，提供 `create_order()` 方法：

```python
def create_order(self, code, direction, order_type, status, volume,
                 limit_price, frozen_money=0, frozen_volume=0,
                 transaction_price=0, transaction_volume=0,
                 remain=0, fee=0, **kwargs):
    return Order(
        portfolio_id=self.portfolio_id,
        engine_id=self.engine_id,
        task_id=self.task_id,
        code=code,
        direction=direction,
        order_type=order_type,
        status=status,
        volume=volume,
        limit_price=limit_price,
        frozen_money=frozen_money,
        frozen_volume=frozen_volume,
        transaction_price=transaction_price,
        transaction_volume=transaction_volume,
        remain=remain,
        fee=fee,
        **kwargs,
    )
```

### 3. RiskBase 加 `create_signal()`

**文件**: `src/ginkgo/trading/bases/risk_base.py`

与 `BaseStrategy.create_signal()` 相同逻辑：

```python
def create_signal(self, code, direction, reason="", volume=0,
                  weight=0.0, strength=0.5, confidence=0.5, **kwargs):
    return Signal(
        portfolio_id=self.portfolio_id,
        engine_id=self.engine_id,
        task_id=self.task_id,
        code=code,
        direction=direction,
        reason=reason,
        volume=volume,
        weight=weight,
        strength=strength,
        confidence=confidence,
        **kwargs,
    )
```

### 4. 现有组件代码替换

#### 策略（6 个文件）

| 文件 | 改动 |
|------|------|
| `moving_average_crossover.py` | `Signal(portfolio_id=..., engine_id=..., task_id=..., ...)` → `self.create_signal(code=..., ...)` |
| `momentum.py` | 同上，4 处 Signal 创建 |
| `trend_follow.py` | 同上，补上缺失的 task_id |
| `trend_reverse.py` | 同上，2 处 |
| `mean_reversion.py` | 同上，1 处 |
| `random_signal_strategy.py` | `_create_signal()` 方法改为调用 `self.create_signal()` |

#### 仓位管理器（2 个文件）

| 文件 | 改动 |
|------|------|
| `fixed_sizer.py` | LONG/SHORT 两处 `Order(...)` → `self.create_order(code=..., ...)` |
| `atr_sizer.py` | `Order()` + `o.set(...)` → `self.create_order(...)` |

#### 风控（9 个文件）

| 文件 | 改动 |
|------|------|
| `loss_limit_risk.py` | `Signal(...)` → `self.create_signal(...)` |
| `margin_risk.py` | 同上，移除 `task_id=""` 硬编码 |
| `max_drawdown_risk.py` | 同上，2 处 |
| `position_ratio_risk.py` | 同上 |
| `volatility_risk.py` | 同上，2 处 |
| `capital_risk.py` | 同上，移除 `task_id="0"` 和 `engine_id="capital_risk"` 硬编码 |
| `liquidity_risk.py` | 同上，2 处 |
| `profit_target_risk.py` | 同上，2 处，修复零 ID 的 trailing stop |
| `concentration_risk.py` | 同上，2 处 |

#### 信号处理（2 个文件）

| 文件 | 改动 |
|------|------|
| `batch_processor.py` | `Order(portfolio_id=signal.portfolio_id, ...)` → 从 signal 复制 ID，使用 sizer 的 `create_order()` 或直接从 signal 提取 |
| `resource_optimizer.py` | 同上，从 `portfolio_info` 获取 ID |

### 5. 组件模板更新

**文件**: `src/ginkgo/client/component_cli_db.py`

更新 `get_template_code()` 生成的模板代码：
- 策略模板：使用 `self.create_signal(code=..., direction=..., reason=...)`
- 仓位管理器模板：使用 `self.create_order(code=..., direction=..., ...)`
- 风控模板：使用 `self.create_signal(code=..., direction=..., reason=...)`

### 6. File 表重新 seed

修改完磁盘代码后，运行 `ginkgo init` 将更新后的代码同步到 MySQL `file` 表。

## 不改动的部分

- `Selector`：不创建 Signal/Order，无需改动
- `Analyzer`：ID 通过 `bind_portfolio()` 传播，走不同链路
- `BaseStrategy.create_signal()`：已存在，保持不变
- `Portfolio.on_price_received()`/`on_signal()`：不加兜底逻辑

## 验证

1. 运行回测确认 Signal/Order 创建正常，ID 正确填充
2. 通过 Web UI 创建新策略，确认模板代码使用工厂方法
3. 运行现有测试确保不破坏
