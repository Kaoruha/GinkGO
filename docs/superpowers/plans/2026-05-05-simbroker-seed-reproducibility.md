# SimBroker 随机种子可复现性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 SimBroker 支持固定随机种子，实现回测结果完全可复现。

**Architecture:** SimBroker 构造时创建独立的 `numpy.random.Generator` 实例，替换所有全局随机调用。4 条实例化路径透传 `random_seed` 参数。

**Tech Stack:** Python 3.12, numpy, scipy.stats, pytest

---

### Task 1: 添加 random_seed 参数 + 替换 scipy.stats 调用

**Files:**
- Modify: `src/ginkgo/trading/brokers/sim_broker.py:17-69` (imports + constructor)
- Modify: `src/ginkgo/trading/brokers/sim_broker.py:390-445` (_get_random_transaction_price)
- Test: `tests/unit/trading/brokers/test_sim_broker_reproducibility.py`

- [ ] **Step 1: 编写可复现性测试**

创建 `tests/unit/trading/brokers/test_sim_broker_reproducibility.py`：

```python
import sys
import os
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import DIRECTION_TYPES, ATTITUDE_TYPES


class TestSeedReproducibility:
    """SimBroker 随机种子可复现性测试"""

    def _make_market_data(self, low=10.0, high=11.0, close=10.5):
        data = MagicMock()
        data.low = low
        data.high = high
        data.close = close
        data.open = 10.3
        data.volume = 1000000
        return data

    def _make_order(self, direction=DIRECTION_TYPES.LONG):
        order = MagicMock()
        order.direction = direction
        order.code = "000001.SZ"
        order.volume = 100
        order.limit_price = 10.5
        order.order_type = None  # 市价单
        order.portfolio_id = "test-portfolio"
        order.frozen_money = 2000
        order.uuid = "test-uuid-12345678"
        return order

    def test_same_seed_same_price_sequence(self):
        """相同 seed 产生完全相同的成交价序列"""
        seed = 42
        prices1 = []
        prices2 = []

        for _ in range(10):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_order()
            price = broker._get_random_transaction_price(order, self._make_market_data())
            prices1.append(float(price))

        for _ in range(10):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_order()
            price = broker._get_random_transaction_price(order, self._make_market_data())
            prices2.append(float(price))

        assert prices1 == prices2

    def test_different_seed_different_price(self):
        """不同 seed 产生不同成交价"""
        broker1 = SimBroker(random_seed=42, attitude=ATTITUDE_TYPES.RANDOM)
        broker2 = SimBroker(random_seed=99, attitude=ATTITUDE_TYPES.RANDOM)

        broker1.update_market_data("000001.SZ", self._make_market_data())
        broker2.update_market_data("000001.SZ", self._make_market_data())

        order = self._make_order()
        p1 = float(broker1._get_random_transaction_price(order, self._make_market_data()))
        p2 = float(broker2._get_random_transaction_price(order, self._make_market_data()))

        assert p1 != p2

    def test_no_seed_produces_random_results(self):
        """不传 seed 每次结果不同"""
        prices = set()
        for _ in range(10):
            broker = SimBroker(attitude=ATTITUDE_TYPES.RANDOM)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_order()
            price = float(broker._get_random_transaction_price(order, self._make_market_data()))
            prices.add(price)

        assert len(prices) > 1

    def test_optimistic_attitude_reproducible(self):
        """OPTIMISTIC 态度下成交价也可复现"""
        seed = 42
        broker1 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker2 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)

        broker1.update_market_data("000001.SZ", self._make_market_data())
        broker2.update_market_data("000001.SZ", self._make_market_data())

        order = self._make_order()
        p1 = float(broker1._get_random_transaction_price(order, self._make_market_data()))
        p2 = float(broker2._get_random_transaction_price(order, self._make_market_data()))

        assert p1 == p2

    def test_pessimistic_attitude_reproducible(self):
        """PESSIMISTIC 态度下成交价也可复现"""
        seed = 42
        broker1 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)
        broker2 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)

        broker1.update_market_data("000001.SZ", self._make_market_data())
        broker2.update_market_data("000001.SZ", self._make_market_data())

        order = self._make_order()
        p1 = float(broker1._get_random_transaction_price(order, self._make_market_data()))
        p2 = float(broker2._get_random_transaction_price(order, self._make_market_data()))

        assert p1 == p2

    def test_sell_direction_reproducible(self):
        """卖出方向也可复现"""
        seed = 42
        broker1 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)
        broker2 = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.OPTIMISTIC)

        broker1.update_market_data("000001.SZ", self._make_market_data())
        broker2.update_market_data("000001.SZ", self._make_market_data())

        order = self._make_order(direction=DIRECTION_TYPES.SHORT)
        p1 = float(broker1._get_random_transaction_price(order, self._make_market_data()))
        p2 = float(broker2._get_random_transaction_price(order, self._make_market_data()))

        assert p1 == p2


class TestFillProbabilityReproducibility:
    """限价单成交概率可复现性测试"""

    def _make_limit_order(self, direction=DIRECTION_TYPES.LONG):
        from ginkgo.enums import ORDER_TYPES
        order = MagicMock()
        order.direction = direction
        order.code = "000001.SZ"
        order.volume = 100
        order.limit_price = 10.5
        order.order_type = ORDER_TYPES.LIMITORDER
        order.portfolio_id = "test-portfolio"
        order.frozen_money = 2000
        order.uuid = "test-uuid-12345678"
        return order

    def _make_market_data(self, low=10.0, high=11.0, close=10.5):
        data = MagicMock()
        data.low = low
        data.high = high
        data.close = close
        data.open = 10.3
        data.volume = 1000000
        return data

    def test_pessimistic_fill_probability_reproducible(self):
        """PESSIMISTIC 态度下成交概率可复现"""
        results1 = []
        results2 = []
        seed = 42

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results1.append(broker._can_order_be_filled(order, self._make_market_data()))

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.PESSIMISTIC)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results2.append(broker._can_order_be_filled(order, self._make_market_data()))

        assert results1 == results2

    def test_random_fill_probability_reproducible(self):
        """RANDOM 态度下成交概率可复现"""
        results1 = []
        results2 = []
        seed = 42

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results1.append(broker._can_order_be_filled(order, self._make_market_data()))

        for _ in range(20):
            broker = SimBroker(random_seed=seed, attitude=ATTITUDE_TYPES.RANDOM)
            broker.update_market_data("000001.SZ", self._make_market_data())
            order = self._make_limit_order()
            results2.append(broker._can_order_be_filled(order, self._make_market_data()))

        assert results1 == results2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/brokers/test_sim_broker_reproducibility.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'random_seed'`

- [ ] **Step 3: 修改 SimBroker 构造函数**

修改 `src/ginkgo/trading/brokers/sim_broker.py`：

**替换 import 部分**（第 17-22 行）：
```python
import pandas as pd
import traceback
from decimal import Decimal
from typing import Dict, List, Optional, Any
from scipy import stats
import numpy as np
```
移除 `import random`，新增 `import numpy as np`。

**替换构造函数**（第 45-69 行）：
```python
    def __init__(self, name: str = "SimBroker", random_seed=None, **config):
        """
        初始化SimBroker

        Args:
            name: Broker名称
            random_seed: 随机种子 (None=不可复现, 固定值=可复现)
            config: 配置字典，包含：
                - attitude: 撮合态度 (OPTIMISTIC/PESSIMISTIC/RANDOM)
                - commission_rate: 手续费率 (默认0.0003)
                - commission_min: 最小手续费 (默认5)
                - slip_base: 滑点基数 (默认0.01)
        """
        super().__init__(name=name)

        # 独立随机数生成器，不依赖全局状态
        self._rng = np.random.default_rng(random_seed)

        # 模拟交易配置
        self._attitude = config.get("attitude", ATTITUDE_TYPES.RANDOM)
        self._commission_rate = Decimal(str(config.get("commission_rate", 0.0003)))
        self._commission_min = Decimal(str(config.get("commission_min", 5)))
        self._slip_base = config.get("slip_base", 0.01)
        self._slippage_tolerance = Decimal(str(config.get("slippage_tolerance", 0.05)))

        # 设置市场属性（用于Router市场映射）
        self.market = "SIM"  # 通用模拟市场，支持所有品种

        GLOG.INFO(f"SimBroker initialized with attitude={self._attitude.name}, commission_rate={self._commission_rate}")
```

- [ ] **Step 4: 替换 _get_random_transaction_price 中的 scipy 调用**

修改 `src/ginkgo/trading/brokers/sim_broker.py` 第 390-445 行的 `_get_random_transaction_price` 方法：

```python
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

        GLOG.DEBUG(f"🎲 [SIMBROKER] RANDOM_PARAMS: low={low}, high={high}, mean={mean}, std_dev={std_dev}, direction={direction.name}, attitude={attitude}")

        from ginkgo.enums import ATTITUDE_TYPES

        if attitude == ATTITUDE_TYPES.RANDOM:
            rs = stats.norm.rvs(loc=mean, scale=std_dev, size=1, random_state=self._rng)
        else:
            skewness_right = mean
            skewness_left = -mean
            if attitude == ATTITUDE_TYPES.OPTIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1, random_state=self._rng)
                else:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1, random_state=self._rng)
            elif attitude == ATTITUDE_TYPES.PESSIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1, random_state=self._rng)
                else:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1, random_state=self._rng)

        raw_result = rs[0]
        rs = max(low, min(high, raw_result))
        result = to_decimal(round(rs, 2))

        GLOG.INFO(f"🎲 [SIMBROKER] RANDOM_GENERATION: raw={raw_result}, clipped={rs}, final={result}")

        return result
```

- [ ] **Step 5: 替换 _can_order_be_filled 中的 random.random()**

修改 `src/ginkgo/trading/brokers/sim_broker.py` 第 554-558 行：

```python
        if self._attitude == ATTITUDE_TYPES.OPTIMISTIC:
            return True
        elif self._attitude == ATTITUDE_TYPES.PESSIMISTIC:
            return self._rng.random() > 0.3
        else:  # RANDOM
            return self._rng.random() > 0.2
```

- [ ] **Step 6: 清理 _get_random_transaction_price 中的无用代码**

删除第 414-418 行的随机种子状态日志（使用全局 `random` 和 `np.random` 的调试代码，不再需要）：

```python
        # 删除以下行:
        import random
        import numpy as np
        py_seed = random.getstate()[1][0] if len(random.getstate()[1]) > 0 else 'N/A'
        np_seed = np.random.get_state()[1][0] if len(np.random.get_state()[1]) > 0 else 'N/A'
        GLOG.DEBUG(f"🎲 [SIMBROKER] RANDOM_STATE: py_seed={py_seed}, np_seed={np_seed}")
```

以及第 409 行附近重复的 `from scipy import stats`（文件顶部已导入）。

- [ ] **Step 7: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/brokers/test_sim_broker_reproducibility.py -v`
Expected: 9 tests PASS

- [ ] **Step 8: 运行已有 SimBroker 测试确认无回归**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/brokers/ -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add src/ginkgo/trading/brokers/sim_broker.py tests/unit/trading/brokers/test_sim_broker_reproducibility.py
git commit -m "feat: add random_seed to SimBroker for reproducible backtests"
```

---

### Task 2: InfrastructureFactory 透传 random_seed

**Files:**
- Modify: `src/ginkgo/trading/services/_assembly/infrastructure_factory.py:198-207`

- [ ] **Step 1: 修改 default_cfg 添加 random_seed**

修改 `infrastructure_factory.py` 第 198-207 行的 `default_cfg` 字典：

```python
        default_cfg = {
            "name": "SimBroker",
            "attitude": broker_attitude,
            "commission_rate": 0.0003,
            "commission_min": 5,
            "random_seed": engine_data.get("random_seed", None),
        }
```

`random_seed` 随 `cfg` 自然透传到 `SimBroker(**cfg)`。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/services/_assembly/infrastructure_factory.py
git commit -m "feat: pass random_seed through InfrastructureFactory to SimBroker"
```

---

### Task 3: TaskEngineBuilder 透传 random_seed

**Files:**
- Modify: `src/ginkgo/trading/services/_assembly/task_engine_builder.py:245-256`

- [ ] **Step 1: 添加 random_seed 到 SimBroker 构造参数**

修改 `task_engine_builder.py` 第 251-256 行：

```python
        broker = SimBroker(
            name="SimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=task.config.commission_rate,
            commission_min=5,
            random_seed=getattr(task.config, "random_seed", None),
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/services/_assembly/task_engine_builder.py
git commit -m "feat: pass random_seed through TaskEngineBuilder to SimBroker"
```

---

### Task 4: 最终验证

- [ ] **Step 1: 运行全部 SimBroker 相关测试**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/brokers/ -v`
Expected: ALL PASS

- [ ] **Step 2: 运行 assembly 相关测试（如存在）**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/ -k "infrastructure_factory or task_engine" -v --timeout=60`
Expected: ALL PASS (或无匹配测试时 NO TESTS RAN)

- [ ] **Step 3: Push**

```bash
git push -u origin 023-fix/simbroker-seed-reproducibility
```
