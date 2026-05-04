# LogIngester 设计文档

> CLI 回测日志事后灌入 ClickHouse

## 背景

CLI `ginkgo backtest run` 执行回测时，日志通过 GinkgoLogger 写入本地文件（`~/.ginkgo/logs/bt_*.log`）。在 Docker 环境中 Vector 采集这些文件写入 ClickHouse，但本地 CLI 运行时没有 Vector，日志不会入库，WebUI 无法查看。

## 方案

在回测完成后，用 Python 等价复刻 Vector 的「读文件 → 解析 JSON → 扁平化字段 → 路由到表 → 批量 INSERT」流水线，将日志灌入 ClickHouse。

### 调用时机

`backtest_cli.py` 的 `run` 命令中，`_save_results()` 之后自动调用。用户无感知。

### 错误处理

静默降级：ClickHouse 写入失败时 `GLOG.WARN`，不影响回测结果。

### 去重保障

`MBacktestLog` 使用 `ReplacingMergeTree + sipHash64(message)` 去重。Vector 和 LogIngester 各灌一次同一条日志会自动合并。

## 受影响文件

```
src/ginkgo/
├── client/backtest_cli.py           # 修改: _save_results() 后调用日志灌入
├── services/logging/
│   ├── __init__.py                   # 修改: 导出 LogIngester
│   └── log_ingester.py              # 新增: LogIngester 类
└── data/models/model_logs.py         # 不改: 复用 MBacktestLog/MComponentLog/MPerformanceLog
```

## LogIngester 核心设计

### 数据流

```
bt_<uuid>_<ts>.log (JSON行)
    ↓ 逐行 json.loads
    ↓ normalize() 扁平化 ginkgo.* 字段
    ↓ 按 log_category 路由到 MBacktestLog / MComponentLog / MPerformanceLog
    ↓ 分批 add_all() → ClickHouse
```

### normalize 逻辑

等价于 Vector `normalize_fields`（`.conf/vector.toml` L39-133），将嵌套 JSON 映射到 Model 属性：

- `@timestamp` → `timestamp`（格式化为 `%Y-%m-%d %H:%M:%S`）
- `log.level` → `level`
- `log.logger` → `logger_name`
- `message` → `message`
- `ginkgo.log_category` → `event_category`（路由键）
- `ginkgo.event_type` → `event_type`
- `ginkgo.task_id` → `task_id`
- `ginkgo.engine_id` → `engine_id`
- `ginkgo.portfolio_id` → `portfolio_id`
- `ginkgo.symbol` → `symbol` 等 40+ 字段逐一映射

### 路由逻辑

```python
category_model = {
    "backtest": MBacktestLog,
    "component": MComponentLog,
    "performance": MPerformanceLog,
}
```

### 批量写入

复用现有 `add_all()` 函数（`src/ginkgo/data/drivers/__init__.py`），每 500 条一批。

### 核心方法

```python
class LogIngester:
    def ingest_file(self, log_path: str) -> IngestResult
    def ingest_task_logs(self, task_uuid: str) -> IngestResult
```

- `ingest_task_logs`：根据 `task_uuid[:8]` 前缀匹配 `bt_<prefix>_*.log` 文件
- `ingest_file`：读单文件，逐行解析，分批写入

## 不做的事

- 不修改 GinkgoLogger
- 不修改 Vector 配置
- 不新增 CLI 命令
- 不处理实时场景
