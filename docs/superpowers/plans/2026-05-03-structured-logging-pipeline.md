# 结构化日志管道补全 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全回测日志的 portfolio_id 注入、Vector 字段提取、API 筛选，实现 task_id + portfolio_id + event_type 完整链路

**Architecture:** 扩展 blog proxy 支持 `log_*_event` 方法路由，t1backtest.py 批量替换 `GLOG.log_*` → `self.blog.log_*`，Vector TOML 补全 30+ 字段提取，API 传入 portfolio_id 筛选

**Tech Stack:** Python 3.12, Vector TOML, ClickHouse, FastAPI

---

### Task 1: 扩展 blog proxy 支持 `log_*` 方法路由

**Files:**
- Modify: `src/ginkgo/entities/mixins/context_mixin.py:57-65`

- [ ] **Step 1: 修改 `_LogChain.__call__` 方法**

将当前的：

```python
    def __call__(self, *args, **kwargs):
        pid = object.__getattribute__(self, '_pid')
        if pid:
            kwargs.setdefault('portfolio_id', pid)
        from ginkgo.libs import GLOG
        obj = GLOG.backtest
        for attr in object.__getattribute__(self, '_path'):
            obj = getattr(obj, attr)
        return obj(*args, **kwargs)
```

替换为：

```python
    def __call__(self, *args, **kwargs):
        pid = object.__getattribute__(self, '_pid')
        if pid:
            kwargs.setdefault('portfolio_id', pid)
        from ginkgo.libs import GLOG
        path = object.__getattribute__(self, '_path')
        if path[0].startswith('log_'):
            obj = GLOG
        else:
            obj = GLOG.backtest
        for attr in path:
            obj = getattr(obj, attr)
        return obj(*args, **kwargs)
```

- [ ] **Step 2: 语法验证**

Run: `python3 -c "import ast; ast.parse(open('src/ginkgo/entities/mixins/context_mixin.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 3: 单元测试验证路由**

Run: `python3 -c "
from ginkgo.entities.mixins.context_mixin import _PortfolioLogProxy, _LogChain

proxy = _PortfolioLogProxy('test-portfolio-123')

# Test 1: log_* 路径 → path[0] 以 log_ 开头
chain = proxy.log_engine_error_event
assert isinstance(chain, _LogChain)
path = object.__getattribute__(chain, '_path')
assert path == ('log_engine_error_event',), f'Got {path}'

# Test 2: namespace 路径 → 不以 log_ 开头
chain2 = proxy.trade.order
path2 = object.__getattribute__(chain2, '_path')
assert path2 == ('trade', 'order'), f'Got {path2}'

# Test 3: portfolio_id 注入
assert object.__getattribute__(chain, '_pid') == 'test-portfolio-123'

print('All proxy routing tests passed')
"`

Expected: `All proxy routing tests passed`

- [ ] **Step 4: 提交**

```bash
git add src/ginkgo/entities/mixins/context_mixin.py
git commit -m "feat: extend blog proxy to route log_*_event methods with portfolio_id injection"
```

---

### Task 2: t1backtest.py 批量替换 GLOG.log_* → self.blog.log_*

**Files:**
- Modify: `src/ginkgo/trading/portfolios/t1backtest.py`（45 处）

- [ ] **Step 1: 使用 replace_all 批量替换**

在 `src/ginkgo/trading/portfolios/t1backtest.py` 中，将所有 `GLOG.log_` 替换为 `self.blog.log_`。

替换字符串：`GLOG.log_` → `self.blog.log_`（replace_all: true）

这会覆盖以下 45 处调用：
- `GLOG.log_t1_settlement_event` → `self.blog.log_t1_settlement_event`（1 处）
- `GLOG.log_time_advance_event` → `self.blog.log_time_advance_event`（2 处）
- `GLOG.log_t1_delay_event` → `self.blog.log_t1_delay_event`（4 处）
- `GLOG.log_engine_error_event` → `self.blog.log_engine_error_event`（24 处）
- `GLOG.log_order_event` → `self.blog.log_order_event`（1 处）
- `GLOG.log_risk_event` → `self.blog.log_risk_event`（2 处）
- `GLOG.log_order_rejected_event` → `self.blog.log_order_rejected_event`（5 处）
- `GLOG.log_price_received_event` → `self.blog.log_price_received_event`（1 处）
- `GLOG.log_position_event` → `self.blog.log_position_event`（1 处）
- `GLOG.log_strategy_signal_event` → `self.blog.log_strategy_signal_event`（1 处）
- `GLOG.log_order_ack_event` → `self.blog.log_order_ack_event`（1 处）
- `GLOG.log_order_expired_event` → `self.blog.log_order_expired_event`（1 处）
- `GLOG.log_order_cancelled_event` → `self.blog.log_order_cancelled_event`（1 处）

- [ ] **Step 2: 语法验证**

Run: `python3 -c "import ast; ast.parse(open('src/ginkgo/trading/portfolios/t1backtest.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 3: 确认无残留 GLOG.log_ 调用**

Run: `grep -n 'GLOG\.log_' src/ginkgo/trading/portfolios/t1backtest.py`

Expected: 无输出（所有 GLOG.log_ 已替换）

- [ ] **Step 4: 确认 self.blog.log_ 调用数量**

Run: `grep -c 'self\.blog\.log_' src/ginkgo/trading/portfolios/t1backtest.py`

Expected: 45

- [ ] **Step 5: 提交**

```bash
git add src/ginkgo/trading/portfolios/t1backtest.py
git commit -m "refactor: replace GLOG.log_*_event with self.blog.log_* for portfolio_id injection"
```

---

### Task 3: Vector TOML 补全 30+ 字段提取

**Files:**
- Modify: `.conf/vector.toml:39-99`（normalize_fields transform）

- [ ] **Step 1: 在 normalize_fields 的 `risk_reason` 提取行之后、`字段映射` 注释之前，插入所有缺失字段的提取**

在 `.conf/vector.toml` 中，找到：

```toml
if exists(.ginkgo.risk_reason) { .risk_reason = .ginkgo.risk_reason }
```

在它之后插入：

```toml
if exists(.ginkgo.signal_weight) { .signal_weight = .ginkgo.signal_weight }
if exists(.ginkgo.signal_confidence) { .signal_confidence = .ginkgo.signal_confidence }
if exists(.ginkgo.order_type) { .order_type = .ginkgo.order_type }
if exists(.ginkgo.limit_price) { .limit_price = .ginkgo.limit_price }
if exists(.ginkgo.frozen_money) { .frozen_money = .ginkgo.frozen_money }
if exists(.ginkgo.ack_message) { .ack_message = .ginkgo.ack_message }
if exists(.ginkgo.order_status) { .order_status = .ginkgo.order_status }
if exists(.ginkgo.remain_volume) { .remain_volume = .ginkgo.remain_volume }
if exists(.ginkgo.trade_id) { .trade_id = .ginkgo.trade_id }
if exists(.ginkgo.expire_reason) { .expire_reason = .ginkgo.expire_reason }
if exists(.ginkgo.cancelled_quantity) { .cancelled_quantity = .ginkgo.cancelled_quantity }
if exists(.ginkgo.expired_quantity) { .expired_quantity = .ginkgo.expired_quantity }
if exists(.ginkgo.position_cost) { .position_cost = .ginkgo.position_cost }
if exists(.ginkgo.position_price) { .position_price = .ginkgo.position_price }
if exists(.ginkgo.total_value) { .total_value = .ginkgo.total_value }
if exists(.ginkgo.available_cash) { .available_cash = .ginkgo.available_cash }
if exists(.ginkgo.frozen_cash) { .frozen_cash = .ginkgo.frozen_cash }
if exists(.ginkgo.net_value) { .net_value = .ginkgo.net_value }
if exists(.ginkgo.drawdown) { .drawdown = .ginkgo.drawdown }
if exists(.ginkgo.pnl) { .pnl = .ginkgo.pnl }
if exists(.ginkgo.risk_limit_value) { .risk_limit_value = .ginkgo.risk_limit_value }
if exists(.ginkgo.risk_actual_value) { .risk_actual_value = .ginkgo.risk_actual_value }
if exists(.ginkgo.engine_status) { .engine_status = .ginkgo.engine_status }
if exists(.ginkgo.progress) { .progress = .ginkgo.progress }
if exists(.ginkgo.error_code) { .error_code = .ginkgo.error_code }
if exists(.ginkgo.error_message) { .error_message = .ginkgo.error_message }
if exists(.ginkgo.tracking_id) { .tracking_id = .ginkgo.tracking_id }
if exists(.ginkgo.expected_price) { .expected_price = .ginkgo.expected_price }
if exists(.ginkgo.actual_price) { .actual_price = .ginkgo.actual_price }
if exists(.ginkgo.expected_volume) { .expected_volume = .ginkgo.expected_volume }
if exists(.ginkgo.actual_volume) { .actual_volume = .ginkgo.actual_volume }
if exists(.ginkgo.price_deviation) { .price_deviation = .ginkgo.price_deviation }
if exists(.ginkgo.volume_deviation) { .volume_deviation = .ginkgo.volume_deviation }
if exists(.ginkgo.delay_seconds) { .delay_seconds = .ginkgo.delay_seconds }
if exists(.ginkgo.source_type) { .source = to_string!(.ginkgo.source_type) }
```

- [ ] **Step 2: 验证 TOML 语法**

Run: `python3 -c "import tomllib; tomllib.load(open('.conf/vector.toml', 'rb')); print('TOML OK')"`

Expected: `TOML OK`

- [ ] **Step 3: 提交**

```bash
git add .conf/vector.toml
git commit -m "feat: add 35 missing field extractions to Vector normalize_fields transform"
```

---

### Task 4: API 筛选修复 — 传入 portfolio_id

**Files:**
- Modify: `api/api/backtest.py:1202-1208`

- [ ] **Step 1: 在 kwargs 中加入 portfolio_id**

在 `api/api/backtest.py` 的 `get_backtest_logs` 函数中，找到：

```python
        kwargs = dict(
            task_id=task_id,
            level=level,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
```

替换为：

```python
        kwargs = dict(
            task_id=task_id,
            portfolio_id=portfolio_id,
            level=level,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
```

- [ ] **Step 2: 语法验证**

Run: `python3 -c "import ast; ast.parse(open('api/api/backtest.py').read()); print('OK')"`

Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add api/api/backtest.py
git commit -m "fix: pass portfolio_id to log query for per-portfolio log filtering"
```

---

### Task 5: 验证 — 端到端检查

- [ ] **Step 1: 重新构建 Docker 镜像并重启**

```bash
cd /home/kaoru/Ginkgo && docker compose build backtest-worker vector && docker compose up -d backtest-worker vector
```

- [ ] **Step 2: 通过 WebUI 发起一次回测**

在 WebUI 创建并运行一个回测任务，获取 engine_id。

- [ ] **Step 3: 检查日志文件中 portfolio_id 是否注入**

```bash
docker exec ginkgo-backtest-worker-1 grep 'log_engine_error_event\|log_order_event\|log_t1_' /var/log/ginkgo/bt_*.log | head -3 | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    g = d.get('ginkgo', {})
    print(f'event_type={g.get(\"event_type\",\"?\")} portfolio_id={g.get(\"portfolio_id\",\"MISSING\")}')
"
```

Expected: 每行都显示 `portfolio_id=非空值`

- [ ] **Step 4: 检查 ClickHouse 中 error_code 字段是否有值**

```bash
docker exec ginkgo-clickhouse clickhouse-client -q "
SELECT event_type, count(), any(portfolio_id), any(error_code)
FROM ginkgo.ginkgo_logs_backtest
WHERE engine_id = '<新回测的engine_id>'
GROUP BY event_type ORDER BY count() DESC
"
```

Expected: `error_code` 列对 ENGINEERROR 事件有值（不再为空）

- [ ] **Step 5: 最终提交并推送**

```bash
git push
```
