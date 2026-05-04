# SimBroker 随机种子可复现性设计

**日期**: 2026-05-05
**状态**: Draft

## 问题

SimBroker 使用全局 `scipy.stats` 和 `random` 生成随机数，未固定种子：
- 市价单成交价：5 处 `scipy.stats.norm.rvs()` / `skewnorm.rvs()` 调用
- 限价单成交概率：2 处 `random.random()` 调用
- 所有 SimBroker 实例共享全局随机状态，互相干扰
- 与 `RandomSignalStrategy` 的 `random.seed(12345)` 交叉污染

结果：同一策略跑两次，成交价、订单、净值曲线都不同。

## 目标

给定相同 `random_seed` + 相同策略参数，两次回测完全一致。

## 方案：SimBroker 自持 numpy.random.Generator

### SimBroker 内部改造

构造函数新增 `random_seed` 参数：

```python
def __init__(self, name="SimBroker", random_seed=None, **config):
    self._rng = np.random.default_rng(random_seed)
```

- `random_seed=None`（默认）：每次运行不同，向后兼容
- `random_seed=42`：可复现

随机调用替换（共 7 处，分布在 2 个方法中）：

**`_get_random_transaction_price()`（5 处 scipy.stats 调用）：**

| 行号 | 原调用 | 替换为 |
|------|--------|--------|
| 422 | `stats.norm.rvs(loc=mean, scale=std_dev, size=1)` | `stats.norm.rvs(loc=mean, scale=std_dev, size=1, random_state=self._rng)` |
| 429 | `stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)` | `stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1, random_state=self._rng)` |
| 431 | `stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)` | `stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1, random_state=self._rng)` |
| 435 | `stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)` | `stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1, random_state=self._rng)` |
| 437 | `stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)` | `stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1, random_state=self._rng)` |

**`_can_order_be_filled()`（2 处 random.random() 调用）：**

| 行号 | 原调用 | 替换为 |
|------|--------|--------|
| 556 | `random.random() > 0.3` | `self._rng.random() > 0.3` |
| 558 | `random.random() > 0.2` | `self._rng.random() > 0.2` |

移除 `import random`（所有随机调用改为 `self._rng`）。

### Seed 数据源

`random_seed` 的权威来源是**引擎配置**（`engine_data` / `task.config`），在创建回测时由用户指定。不传则默认 `None`（随机行为）。

### Seed 传递链路

项目有两条独立的 Broker 创建路径，需同时改造：

#### 路径 1：InfrastructureFactory（主路径）

`create_broker_from_config()` 当前通过 `cfg` dict 构建参数后 `SimBroker(**cfg)` 传入。
改造方式：将 `random_seed` 加入 `default_cfg`，从 `engine_data` 提取：

```python
default_cfg = {
    "name": "SimBroker",
    "attitude": broker_attitude,
    "commission_rate": 0.0003,
    "commission_min": 5,
    "random_seed": engine_data.get("random_seed", None),  # 新增
}
```

这样 `random_seed` 会随 `cfg` 自然透传到 SimBroker 构造函数。

#### 路径 2：TaskEngineBuilder（Task 构建路径）

`_create_gateway_from_task()` 当前硬编码 SimBroker 参数。
改造方式：从 `task.config` 提取 seed，添加到构造参数：

```python
broker = SimBroker(
    name="SimBroker",
    attitude=ATTITUDE_TYPES.OPTIMISTIC,
    commission_rate=task.config.commission_rate,
    commission_min=5,
    random_seed=getattr(task.config, "random_seed", None),  # 新增
)
```

#### 路径 3：Paper Trading Worker

`PaperTradingWorker` 直接 `SimBroker()` 无参数。改造为可选传入 seed（PAPER 模式通常不需要固定，保持 `None`）。

#### 路径 4：DI 容器

`containers.py` 的 `providers.Factory` 天然支持透传构造参数，无需改动定义本身。调用方传入 `random_seed` 即可。

### RandomSignalStrategy 隔离

SimBroker 改用独立 `numpy.random.Generator` 后，与 `RandomSignalStrategy` 的全局 `random` 互不干扰，无需额外改动。

### 不改动的部分

- `BaseBroker`：seed 是 SimBroker 特有需求，不提升到基类
- `RandomSignalStrategy`：继续使用全局 `random`
- 示例/测试文件：不强制传 seed，默认 None 保持随机行为

## 受影响文件

**核心改动**：
- `src/ginkgo/trading/brokers/sim_broker.py` — 随机数替换

**Seed 传递**：
- `src/ginkgo/trading/services/_assembly/infrastructure_factory.py` — 从 engine_data 提取 seed
- `src/ginkgo/trading/services/_assembly/task_engine_builder.py` — 从 task.config 提取 seed
- `src/ginkgo/workers/paper_trading_worker.py` — 可选传入 seed
- `src/ginkgo/trading/core/containers.py` — Factory 支持透传

**新增测试**：
- `tests/unit/backtest/brokers/test_sim_broker_reproducibility.py` — 可复现性验证

## 测试验证

```python
def test_same_seed_same_price():
    """相同 seed 产生完全相同的成交价序列"""

def test_different_seed_different_price():
    """不同 seed 产生不同成交价"""

def test_no_seed_random():
    """不传 seed 每次不同"""

def test_optimistic_attitude_reproducible():
    """OPTIMISTIC 态度下成交价也可复现"""

def test_pessimistic_fill_probability_reproducible():
    """PESSIMISTIC 态度下成交概率可复现"""
```
