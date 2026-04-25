# 组件 ID 自动注入重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 portfolio_id/engine_id/task_id 从用户组件代码中移除，改为通过基类工厂方法自动注入，彻底消除 run_id/task_id 迁移遗漏的根因。

**Architecture:** 在 SizerBase 和 RiskBase 中添加 create_order()/create_signal() 工厂方法（模仿已有的 BaseStrategy.create_signal()）。Signal/Order 构造函数的三个 ID 参数改为可选，去掉非空校验。所有内置组件代码全部改为使用工厂方法。重新 seed file 表。

**Tech Stack:** Python 3.12, singledispatchmethod, ContextMixin

---

### Task 1: Signal 构造函数 — 去掉 ID 非空校验

**Files:**
- Modify: `src/ginkgo/entities/signal.py:28-110`

- [ ] **Step 1: 修改 Signal.__init__ 签名**

`portfolio_id`、`engine_id`、`task_id` 已有默认值 `""`，无需改动签名。

- [ ] **Step 2: 修改 Signal.set() 注册方法，去掉三段非空校验**

在 `src/ginkgo/entities/signal.py` 中，删除 `set()` 方法中 lines 94-110 的三段非空校验：

```python
# 删除这六段（保留类型校验，删除值非空校验）：
# portfolio_id 非空校验 (lines 97-98)
if not portfolio_id:
    raise ValueError("portfolio_id cannot be empty.")

# engine_id 非空校验 (lines 103-104)
if not engine_id:
    raise ValueError("engine_id cannot be empty.")

# task_id 非空校验 (lines 109-110)
if not task_id:
    raise ValueError("task_id cannot be empty.")
```

保留所有 `isinstance` 类型校验。只删除 `if not xxx: raise ValueError(...)` 这三对。

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/entities/signal.py
git commit -m "refactor: remove non-empty validation for IDs in Signal constructor"
```

---

### Task 2: Order 构造函数 — 去掉 ID 非空校验，加默认值

**Files:**
- Modify: `src/ginkgo/entities/order.py:34-144`

- [ ] **Step 1: 修改 Order.__init__ 签名，给三个 ID 加默认值**

将：
```python
def __init__(
    self,
    portfolio_id: str,
    engine_id: str,
    task_id: str,
    code: str,
```
改为：
```python
def __init__(
    self,
    portfolio_id: str = "",
    engine_id: str = "",
    task_id: str = "",
    code: str = "",
```

- [ ] **Step 2: 修改 Order.set() 注册方法，去掉三段非空校验**

删除 lines 131-144 中三段非空校验：
```python
# 删除：
if not portfolio_id:
    raise ValueError("portfolio_id cannot be empty.")

if not engine_id:
    raise ValueError("engine_id cannot be empty.")

if not task_id:
    raise ValueError("task_id cannot be empty.")
```

保留所有 `isinstance` 类型校验。同时保留 `code` 的非空校验（code 是业务必填字段）。

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/entities/order.py
git commit -m "refactor: make ID params optional, remove non-empty validation in Order"
```

---

### Task 3: SizerBase 加 create_order() 工厂方法

**Files:**
- Modify: `src/ginkgo/trading/bases/sizer_base.py`

- [ ] **Step 1: 在 SizerBase 中添加 create_order 方法**

在 `cal()` 方法之前添加：

```python
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES

def create_order(self, code: str, direction, volume: int,
                 limit_price=0, order_type=None, status=None,
                 frozen_money=0, frozen_volume=0,
                 transaction_price=0, transaction_volume=0,
                 remain=0, fee=0, **kwargs):
    """
    创建带有完整上下文的订单。

    自动填充 portfolio_id、engine_id、task_id，仓位管理器只需关注业务参数。

    Args:
        code: 股票代码
        direction: 交易方向 (DIRECTION_TYPES)
        volume: 订单数量
        limit_price: 限价，默认0
        order_type: 订单类型，默认 MARKETORDER
        status: 订单状态，默认 NEW
        **kwargs: 其他 Order 参数 (如 business_timestamp)
    """
    from ginkgo.entities import Order
    from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES

    if order_type is None:
        order_type = ORDER_TYPES.MARKETORDER
    if status is None:
        status = ORDERSTATUS_TYPES.NEW

    return Order(
        portfolio_id=self.portfolio_id or "",
        engine_id=self.engine_id or "",
        task_id=self.task_id or "",
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

注意：将 TYPE_CHECKING 中的 `from ginkgo.entities import Order` 导入保留（用于类型注解），`create_order` 方法内局部导入避免循环依赖。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/bases/sizer_base.py
git commit -m "feat: add create_order() factory method to SizerBase"
```

---

### Task 4: RiskBase 加 create_signal() 工厂方法

**Files:**
- Modify: `src/ginkgo/trading/bases/risk_base.py`

- [ ] **Step 1: 在 RiskBase 中添加 create_signal 方法**

在 `generate_signals()` 方法之后添加：

```python
def create_signal(self, code: str, direction, reason: str = "",
                  volume: int = 0, weight: float = 0.0,
                  strength: float = 0.5, confidence: float = 0.5,
                  **kwargs):
    """
    创建带有完整上下文的风控信号。

    自动填充 portfolio_id、engine_id、task_id，风控组件只需关注业务参数。

    Args:
        code: 股票代码
        direction: 交易方向 (DIRECTION_TYPES)
        reason: 信号原因
        volume: 建议交易量
        weight: 信号权重
        strength: 信号强度
        confidence: 信号置信度
        **kwargs: 其他 Signal 参数
    """
    from ginkgo.entities import Signal

    return Signal(
        portfolio_id=self.portfolio_id or "",
        engine_id=self.engine_id or "",
        task_id=self.task_id or "",
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

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/bases/risk_base.py
git commit -m "feat: add create_signal() factory method to RiskBase"
```

---

### Task 5: 替换策略组件 — 使用 create_signal()

**Files:**
- Modify: `src/ginkgo/trading/strategies/moving_average_crossover.py`
- Modify: `src/ginkgo/trading/strategies/momentum.py`
- Modify: `src/ginkgo/trading/strategies/trend_follow.py`
- Modify: `src/ginkgo/trading/strategies/trend_reverse.py`
- Modify: `src/ginkgo/trading/strategies/mean_reversion.py`
- Modify: `src/ginkgo/trading/strategies/random_signal_strategy.py`

每个策略中的 `Signal(portfolio_id=..., engine_id=..., task_id=..., code=..., direction=..., reason=..., ...)` 替换为 `self.create_signal(code=..., direction=..., reason=..., ...)`。

通用替换规则：
- 删除 `portfolio_id=portfolio_info.get("uuid")` / `portfolio_id=self.portfolio_id` / `portfolio_id=portfolio_info["uuid"]`
- 删除 `engine_id=self.engine_id` / `engine_id=engine_id`
- 删除 `task_id=self.task_id` / `task_id=task_id`
- 删除 `source=SOURCE_TYPES.STRATEGY`（create_signal 使用默认值 OTHER 即可，source 在 EventSignalGeneration 中设置）
- 保留所有业务参数：`code`, `direction`, `reason`, `volume`, `weight`, `strength`, `confidence`

- [ ] **Step 1: 替换 moving_average_crossover.py**

查找所有 `Signal(` 调用，替换为 `self.create_signal(`，删除三个 ID 参数和 source 参数。

- [ ] **Step 2: 替换 momentum.py**

同上，该文件有 4 处 Signal 创建。

- [ ] **Step 3: 替换 trend_follow.py**

同上。该文件之前缺少 task_id，现在通过 create_signal 自动填充。

- [ ] **Step 4: 替换 trend_reverse.py**

同上，2 处。

- [ ] **Step 5: 替换 mean_reversion.py**

同上，1 处。

- [ ] **Step 6: 替换 random_signal_strategy.py**

该文件的 `_create_signal()` 方法（约 line 175）直接构造 Signal。改为调用 `self.create_signal()`。

- [ ] **Step 7: Commit**

```bash
git add src/ginkgo/trading/strategies/
git commit -m "refactor: strategies use create_signal() instead of manual Signal construction"
```

---

### Task 6: 替换 Sizer 组件 — 使用 create_order()

**Files:**
- Modify: `src/ginkgo/trading/sizers/fixed_sizer.py`
- Modify: `src/ginkgo/trading/sizers/atr_sizer.py`

- [ ] **Step 1: 替换 fixed_sizer.py**

LONG 方向（约 line 125）：
```python
# 之前：
o = Order(
    portfolio_id=portfolio_info["portfolio_id"],
    engine_id=self.engine_id,
    task_id=portfolio_info.get("task_id", ""),
    code=code,
    direction=DIRECTION_TYPES.LONG,
    order_type=ORDER_TYPES.MARKETORDER,
    status=ORDERSTATUS_TYPES.NEW,
    volume=planned_size,
    limit_price=0,
    frozen_money=planned_cost,
    ...
)
# 之后：
o = self.create_order(
    code=code,
    direction=DIRECTION_TYPES.LONG,
    volume=planned_size,
    limit_price=0,
    frozen_money=planned_cost,
    transaction_price=0,
    transaction_volume=0,
    remain=planned_cost,
    fee=0,
    business_timestamp=signal.business_timestamp if hasattr(signal, 'business_timestamp') else current_time,
)
```

SHORT 方向同理。删除不再需要的导入：`ORDER_TYPES, ORDERSTATUS_TYPES`（如果不再直接使用）。

- [ ] **Step 2: 替换 atr_sizer.py**

atr_sizer 使用 `Order()` + `o.set()` 模式。替换为 `self.create_order()` 一次性创建。

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/sizers/
git commit -m "refactor: sizers use create_order() instead of manual Order construction"
```

---

### Task 7: 替换风控组件 — 使用 create_signal()

**Files:**
- Modify: `src/ginkgo/trading/risk_management/loss_limit_risk.py`
- Modify: `src/ginkgo/trading/risk_management/margin_risk.py`
- Modify: `src/ginkgo/trading/risk_management/max_drawdown_risk.py`
- Modify: `src/ginkgo/trading/risk_management/position_ratio_risk.py`
- Modify: `src/ginkgo/trading/risk_management/volatility_risk.py`
- Modify: `src/ginkgo/trading/risk_management/capital_risk.py`
- Modify: `src/ginkgo/trading/risk_management/liquidity_risk.py`
- Modify: `src/ginkgo/trading/risk_management/profit_target_risk.py`
- Modify: `src/ginkgo/trading/risk_management/concentration_risk.py`

通用替换规则：
- `Signal(portfolio_id=..., engine_id=..., task_id=..., code=..., ...)` → `self.create_signal(code=..., ...)`
- 删除 `portfolio_id=portfolio_info["uuid"]` / `portfolio_id=portfolio_info.get("uuid", "")` / `portfolio_id=portfolio_id`
- 删除 `engine_id=self.engine_id` / `engine_id="xxx"` (硬编码值)
- 删除 `task_id=self.task_id` / `task_id=""` / `task_id="0"` (硬编码值)
- 删除 `source=SOURCE_TYPES.STRATEGY` / `source="xxx"` (字符串形式的 source)
- 保留所有业务参数

**特别注意 profit_target_risk.py:**
- Line 117: 标准替换
- Line 137: `signal = Signal()` 后逐属性赋值 → 改为 `signal = self.create_signal(code=event.code, direction=DIRECTION_TYPES.SHORT, reason=...)` 一次性创建
- 删除 `signal.strength = 0.9` / `signal.strength = 0.95` 改为在 create_signal 中传入

- [ ] **Step 1: 替换 loss_limit_risk.py**
- [ ] **Step 2: 替换 margin_risk.py**
- [ ] **Step 3: 替换 max_drawdown_risk.py**
- [ ] **Step 4: 替换 position_ratio_risk.py**
- [ ] **Step 5: 替换 volatility_risk.py**
- [ ] **Step 6: 替换 capital_risk.py**
- [ ] **Step 7: 替换 liquidity_risk.py**
- [ ] **Step 8: 替换 profit_target_risk.py**
- [ ] **Step 9: 替换 concentration_risk.py**
- [ ] **Step 10: Commit**

```bash
git add src/ginkgo/trading/risk_management/
git commit -m "refactor: risk managers use create_signal() instead of manual Signal construction"
```

---

### Task 8: 替换 signal_processing 组件

**Files:**
- Modify: `src/ginkgo/trading/signal_processing/batch_processor.py`
- Modify: `src/ginkgo/trading/signal_processing/resource_optimizer.py`

- [ ] **Step 1: 替换 batch_processor.py**

`batch_processor.py` 不继承 SizerBase，无法用 `self.create_order()`。改为直接构造 Order，从 signal 复制 ID：

```python
# 之前（缺少 task_id）：
order = Order(
    code=signal.code,
    direction=signal.direction,
    volume=volume,
    limit_price=estimated_price,
    frozen=estimated_price * volume,
    timestamp=signal.timestamp,
    portfolio_id=signal.portfolio_id,
    engine_id=signal.engine_id
)

# 之后：
order = Order(
    portfolio_id=signal.portfolio_id,
    engine_id=signal.engine_id,
    task_id=signal.task_id,
    code=signal.code,
    direction=signal.direction,
    volume=volume,
    limit_price=estimated_price,
    frozen_money=estimated_price * volume,
    timestamp=signal.timestamp,
)
```

注意参数名可能需要修正（`frozen` → `frozen_money`，添加缺失的 `task_id`）。

- [ ] **Step 2: 替换 resource_optimizer.py**

同理，从 portfolio_info 获取 ID：

```python
order = Order(
    portfolio_id=portfolio_info.get('portfolio_id', ''),
    engine_id=portfolio_info.get('engine_id', ''),
    task_id=portfolio_info.get('task_id', ''),
    ...
)
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/signal_processing/
git commit -m "refactor: signal processing uses proper ID passing"
```

---

### Task 9: 更新组件模板

**Files:**
- Modify: `src/ginkgo/client/component_cli_db.py:70-234`

- [ ] **Step 1: 更新策略模板**

将模板中 `Signal(code=..., direction=..., ...)` 改为 `self.create_signal(code=..., direction=..., ...)`，删除 portfolio_id/engine_id/task_id/source 参数。

注意：模板中的导入路径也需要修正（使用当前正确的导入路径而非 `ginkgo.backtest.*`）。

- [ ] **Step 2: 更新风控模板**

将 `Signal(...)` 改为 `self.create_signal(...)`。

- [ ] **Step 3: 更新仓位管理器模板**

当前 sizer 模板没有 Order 创建，无需改动。

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/client/component_cli_db.py
git commit -m "refactor: update component templates to use factory methods"
```

---

### Task 10: 重新 seed file 表 + 验证

**Files:**
- No code changes (database operation)

- [ ] **Step 1: 清除 Python 缓存**

```bash
find src -name "*.pyc" -delete
```

- [ ] **Step 2: 重新 seed file 表**

运行 `ginkgo init` 将更新后的磁盘代码同步到 MySQL `file` 表。注意这会覆盖 file 表中已有的同名组件（包括之前手动修复 run_id→task_id 的那些）。

- [ ] **Step 3: 验证 file 表中的 fixed_sizer 不再包含 run_id**

```python
python3 -c "
from ginkgo.data.containers import container
crud = container.cruds.file()
files = crud.find()
for f in files:
    if f.type == 5 and f.name == 'fixed_sizer':
        code = f.data.decode('utf-8') if isinstance(f.data, bytes) else str(f.data)
        assert 'run_id' not in code, 'fixed_sizer still has run_id!'
        assert 'create_order' in code, 'fixed_sizer not using create_order!'
        print('OK: fixed_sizer uses create_order, no run_id')
"
```

- [ ] **Step 4: Commit (if any fixes needed)**

---

### Task 11: 运行 example 回测验证

**Files:**
- No code changes (verification only)

- [ ] **Step 1: 运行 backtest_with_task_example.py**

```bash
cd /home/kaoru/Ginkgo && .venv/bin/python examples/backtest_with_task_example.py
```

**验收标准：**
- 脚本正常运行无报错
- 输出中有非零的信号数、订单数
- 有持仓（position_count > 0）
- netvalue 有变化（不等于初始资金）
- AnalyzerRecord 记录数 > 0

- [ ] **Step 2: 运行 complete_backtest_example.py**

```bash
cd /home/kaoru/Ginkgo && .venv/bin/python examples/complete_backtest_example.py
```

**验收标准同上。**

---

### Task 12: WebUI 回测验证

**Files:**
- No code changes (verification only)

- [ ] **Step 1: 确保 API 服务器和 Worker 运行**

```bash
# 检查 API 服务器
curl -s http://localhost:8000/api/v1/health || echo "API server not running"

# 检查 Worker
ps aux | grep worker-backtest | grep -v grep
```

- [ ] **Step 2: 通过 Python 创建并启动回测任务**

使用 portfolio `b3e54c90c6624de5a16893d43b7acead`，日期范围有 bar 数据的区间。

- [ ] **Step 3: 等待回测完成，查询分析器记录**

验证所有 analyzer_record 的 value 字段不全部为 0（特别是 net_value）。

- [ ] **Step 4: 通过 WebUI 确认**

在浏览器中打开回测详情页，确认净值曲线有变化。

---

### Task 13: 还原 backtest_feeder.py 调试日志

**Files:**
- Modify: `src/ginkgo/trading/feeders/backtest_feeder.py:148-153`

- [ ] **Step 1: 将调试日志还原为原级别**

```python
# 还原：
GLOG.DEBUG(f"ADVANCE_TIME: {target_time.date()}, interested={self._interested_codes}")

if len(self._interested_codes) == 0:
    GLOG.WARN(f"No interested symbols at {target_time}, selector may not have published codes")
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/feeders/backtest_feeder.py
git commit -m "chore: revert debug logging in backtest_feeder"
```
