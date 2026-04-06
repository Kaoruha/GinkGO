# 偏差检测与策略下线设计

> 日期: 2026-04-06
> 状态: Approved

## 概述

将偏差检测从 Paper 模式扩展到 Live 模式，并新增人工策略下线能力。核心思路：提取共享模块，统一 Paper/Live 的偏差检测逻辑；通过 CLI + Web UI 提供策略下线操作入口。

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 检查频率（Live） | 收盘为主 + 异常触发 | 平衡实时性与系统复杂度 |
| 人为下线入口 | CLI + Web UI | 覆盖运维和操作员场景 |
| 下线行为 | 仅标记状态，不主动平仓 | 最小化副作用，保留操作员决策权 |
| Live 偏差实现 | 复用共享模块 | 零重复、职责清晰 |
| 告警通道 | Kafka SYSTEM_EVENTS | 已有基础设施，前端可直接消费 |

## 1. DeviationChecker 共享模块

### 1.1 模块位置

`src/ginkgo/trading/analysis/evaluation/deviation_checker.py`

### 1.2 类设计

```python
class DeviationChecker:
    """偏差检测共享逻辑，供 Paper/Live 模式使用"""

    def __init__(self):
        self._detectors: Dict[str, LiveDeviationDetector] = {}

    def get_baseline(self, portfolio_id: str) -> Optional[Dict]:
        """从 Redis 缓存获取 baseline，miss 则从 ClickHouse 计算"""

    def get_deviation_config(self, portfolio_id: str) -> Dict:
        """从 Redis 读取偏差检测配置"""

    def run_deviation_check(
        self, portfolio_id: str, today_records: List
    ) -> Optional[DeviationResult]:
        """执行偏差检测，返回结果或 None（无异常）"""

    def handle_deviation_result(
        self, portfolio_id: str, result: DeviationResult, auto_takedown: bool
    ) -> str:
        """处理偏差结果：NORMAL/MODERATE/SEVERE 分级处理"""

    def send_deviation_alert(
        self, portfolio_id: str, result: DeviationResult
    ) -> None:
        """发送告警到 Kafka SYSTEM_EVENTS topic"""
```

### 1.3 从 PaperTradingWorker 提取的方法

| 原方法 | 目标 |
|--------|------|
| `_get_baseline()` | → `DeviationChecker.get_baseline()` |
| `_get_deviation_config()` | → `DeviationChecker.get_deviation_config()` |
| `_run_deviation_check()` | → `DeviationChecker.run_deviation_check()` |
| `_handle_deviation_result()` | → `DeviationChecker.handle_deviation_result()` |
| `_send_deviation_alert()` | → `DeviationChecker.send_deviation_alert()` |

PaperTradingWorker 保留 `_load_today_records()`（依赖引擎上下文），其余偏差逻辑委托给 DeviationChecker。

### 1.4 依赖

- Redis: baseline 缓存、配置存储
- ClickHouse: analyzer records 查询
- Kafka: SYSTEM_EVENTS 告警发布
- `LiveDeviationDetector`: 核心检测算法
- `BacktestEvaluator`: baseline 生成

## 2. Live 模式集成

### 2.1 集成位置

```
livecore/scheduler/
├── scheduler.py              # 修改：注册每日收盘偏差检查任务
├── deviation_scheduler.py    # 新增：封装偏差检查的调度逻辑
└── command_handler.py        # 修改：添加 takedown 命令处理
```

### 2.2 触发机制

**每日收盘检查：**
- `DeviationScheduler` 使用 APScheduler 注册定时任务
- 收盘后（A股 15:05）调用 `DeviationChecker.run_deviation_check()`
- 遍历所有 `status=active` 的 LIVE portfolio

**异常触发：**
- 当单日 P&L 跌幅超过阈值（默认 -5%）时立即触发
- 阈值通过 `deviation:config:{id}` Redis key 配置
- 异常触发仅在交易时段（09:30-15:00）生效

### 2.3 数据流

```
LiveEngine 运行 → Analyzer 写入 ClickHouse records
                          ↓
DeviationScheduler 定时/异常触发
                          ↓
DeviationChecker.run_deviation_check(portfolio_id, today_records)
                          ↓
handle_deviation_result → SYSTEM_EVENTS (Kafka)
                         → 可选 auto_takedown
```

## 3. 策略下线机制

### 3.1 Portfolio 状态

新增 `status` 字段：

| 值 | 含义 |
|----|------|
| `active` | 正常运行（默认） |
| `offline` | 已下线，不执行任何操作 |

### 3.2 下线流程

```
CLI / API
    ↓
Kafka "control.commands" (command: "takedown")
    ↓
CommandHandler.handle_takedown()
    ↓
├── 更新 portfolio.status = "offline" (MySQL)
├── 发送 SYSTEM_EVENTS 通知
└── 根据模式执行:
    ├── Paper: Worker 下次循环检测到 offline，跳过该 portfolio
    └── Live: BrokerManager.pause_broker(portfolio_id)
```

### 3.3 上线流程

```
CLI / API
    ↓
Kafka "control.commands" (command: "online")
    ↓
CommandHandler.handle_online()
    ↓
├── 更新 portfolio.status = "active" (MySQL)
├── 发送 SYSTEM_EVENTS 通知
└── 根据模式执行:
    ├── Paper: Worker 下次循环恢复处理
    └── Live: BrokerManager.resume_broker(portfolio_id)
```

### 3.4 CLI 命令

```bash
# 下线策略
ginkgo portfolio takedown <portfolio_id> [--reason "人工下线"]

# 重新上线
ginkgo portfolio online <portfolio_id>

# 查看列表（显示状态）
ginkgo portfolio list
```

### 3.5 API 端点

```
POST /api/portfolios/{id}/takedown
  Body: { "reason": "人工下线" }
  Response: { "success": true, "status": "offline" }

POST /api/portfolios/{id}/online
  Response: { "success": true, "status": "active" }
```

### 3.6 Web UI

- Portfolio 列表页：显示状态标签（active/offline）
- Portfolio 详情页："下线"/"上线" 操作按钮
- 下线时弹出确认框，要求填写原因

## 4. 告警事件格式

### 4.1 SYSTEM_EVENTS 事件结构

```json
{
  "event_type": "DEVIATION_ALERT",
  "portfolio_id": "uuid",
  "mode": "paper | live",
  "severity": "MODERATE | SEVERE",
  "deviation_details": {
    "metric": "sharpe_ratio",
    "z_score": 2.3,
    "threshold": 2.0
  },
  "timestamp": "2026-04-06T15:05:00+08:00"
}
```

### 4.2 策略下线事件

```json
{
  "event_type": "PORTFOLIO_TAKEDOWN",
  "portfolio_id": "uuid",
  "mode": "paper | live",
  "reason": "人工下线",
  "operator": "cli | api",
  "timestamp": "2026-04-06T15:10:00+08:00"
}
```

### 4.3 MODERATE vs SEVERE 处理

| 级别 | 告警 | 自动下线 |
|------|------|----------|
| MODERATE | Kafka 事件 | 否 |
| SEVERE | Kafka 事件 | 可选（`auto_takedown` 默认关闭） |

## 5. 未修改的现有组件

- `LiveDeviationDetector` — 核心检测算法，不变
- `BacktestEvaluator` — baseline 生成，不变
- `BrokerManager` — 已有 pause/resume/stop，直接复用
- `CommandHandler` — 已有 pause/resume/status，新增 takedown/online
- Redis key 结构 — 复用现有 `deviation:baseline:{id}` / `deviation:config:{id}`

## 6. 文件变更清单

| 操作 | 文件 |
|------|------|
| 新增 | `src/ginkgo/trading/analysis/evaluation/deviation_checker.py` |
| 新增 | `src/ginkgo/livecore/scheduler/deviation_scheduler.py` |
| 修改 | `src/ginkgo/workers/paper_trading_worker.py` — 委托给 DeviationChecker |
| 修改 | `src/ginkgo/livecore/scheduler/command_handler.py` — 新增 takedown/online |
| 修改 | `src/ginkgo/livecore/scheduler/scheduler.py` — 注册每日偏差检查 |
| 修改 | `src/ginkgo/client/portfolio_cli.py` — 新增 takedown/online 命令 |
| 修改 | `src/ginkgo/data/models/` — portfolio status 字段 |
| 新增 | `tests/unit/trading/analysis/test_deviation_checker.py` |
| 新增 | `tests/unit/livecore/scheduler/test_deviation_scheduler.py` |
