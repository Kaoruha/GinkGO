# LogIngester 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI 回测完成后自动将日志文件灌入 ClickHouse，使 WebUI 能查看 CLI 回测日志。

**Architecture:** 新增 `LogIngester` 类，等价复刻 Vector 的「读文件 → 解析 → 扁平化 → 路由 → INSERT」流水线。在 `backtest_cli.py` 的 `_save_results()` 之后自动调用，静默降级。

**Tech Stack:** Python 3.12, SQLAlchemy (ClickHouse), structlog JSON, existing `add_all()` bulk insert

---

### Task 1: 创建 LogIngester — normalize + 路由 + 批量写入

**Files:**
- Create: `src/ginkgo/services/logging/log_ingester.py`

- [ ] **Step 1: 创建 log_ingester.py 基础结构**

```python
# src/ginkgo/services/logging/log_ingester.py
"""
LogIngester - 事后日志灌入器

等价于 Vector 的日志采集流水线：
读 JSON 日志文件 → 扁平化 ginkgo.* 字段 → 按 category 路由到 ORM Model → add_all() 批量写入 ClickHouse

用于 CLI 回测完成后将日志灌入 ClickHouse，使 WebUI 能查看日志。
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Type

from ginkgo.libs import GLOG
from ginkgo.libs.core.config import GCONF


@dataclass
class IngestResult:
    total_lines: int = 0
    inserted: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)


# JSON 嵌套字段 → ORM Model 列名 的映射
# 和 .conf/vector.toml normalize_fields 一一对应
_FIELD_MAPPING = {
    # ginkgo.* → 顶层
    "event_type": "event_type",
    "strategy_id": "strategy_id",
    "symbol": "symbol",
    "direction": "direction",
    "signal_volume": "signal_volume",
    "signal_reason": "signal_reason",
    "signal_weight": "signal_weight",
    "signal_confidence": "signal_confidence",
    "order_id": "order_id",
    "order_type": "order_type",
    "limit_price": "limit_price",
    "frozen_money": "frozen_money",
    "broker_order_id": "broker_order_id",
    "ack_message": "ack_message",
    "order_status": "order_status",
    "transaction_price": "transaction_price",
    "transaction_volume": "transaction_volume",
    "remain_volume": "remain_volume",
    "commission": "commission",
    "slippage": "slippage",
    "trade_id": "trade_id",
    "reject_code": "reject_code",
    "reject_reason": "reject_reason",
    "cancel_reason": "cancel_reason",
    "expire_reason": "expire_reason",
    "cancelled_quantity": "cancelled_quantity",
    "expired_quantity": "expired_quantity",
    "position_code": "position_code",
    "position_volume": "position_volume",
    "position_cost": "position_cost",
    "position_price": "position_price",
    "total_value": "total_value",
    "available_cash": "available_cash",
    "frozen_cash": "frozen_cash",
    "net_value": "net_value",
    "drawdown": "drawdown",
    "pnl": "pnl",
    "risk_type": "risk_type",
    "risk_reason": "risk_reason",
    "risk_limit_value": "risk_limit_value",
    "risk_actual_value": "risk_actual_value",
    "engine_status": "engine_status",
    "progress": "progress",
    "error_code": "error_code",
    "error_message": "error_message",
    "tracking_id": "tracking_id",
    "expected_price": "expected_price",
    "actual_price": "actual_price",
    "expected_volume": "expected_volume",
    "actual_volume": "actual_volume",
    "price_deviation": "price_deviation",
    "volume_deviation": "volume_deviation",
    "delay_seconds": "delay_seconds",
    # 任务关联
    "task_id": "task_id",
    "engine_id": "engine_id",
    "portfolio_id": "portfolio_id",
    "business_timestamp": "business_timestamp",
}

# 需要特殊处理的顶层字段（不在 _FIELD_MAPPING 中的）
_SPECIAL_FIELDS = {
    "source": "source",
}

# log_category → ORM Model
_CATEGORY_MODEL: Dict[str, Type] = {}

def _get_category_models():
    """延迟导入避免循环依赖"""
    global _CATEGORY_MODEL
    if not _CATEGORY_MODEL:
        from ginkgo.data.models.model_logs import (
            MBacktestLog, MComponentLog, MPerformanceLog,
        )
        _CATEGORY_MODEL = {
            "backtest": MBacktestLog,
            "component": MComponentLog,
            "performance": MPerformanceLog,
        }
    return _CATEGORY_MODEL

BATCH_SIZE = 500


def _parse_timestamp(ts_str: str) -> Optional[str]:
    """将 ISO/datetime 字符串转为 ClickHouse 兼容的 %Y-%m-%d %H:%M:%S 格式"""
    if not ts_str:
        return None
    ts_str = ts_str.replace("Z", "").replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts_str, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def normalize(raw: dict) -> Optional[dict]:
    """
    将 structlog 输出的 JSON 行扁平化为 ORM 友好的 dict。

    等价于 .conf/vector.toml 中的 normalize_fields transform。
    """
    ginkgo = raw.get("ginkgo", {}) or {}

    # 路由键
    event_category = ginkgo.get("log_category", "")
    if not event_category:
        return None

    result = {
        # 基础字段
        "timestamp": _parse_timestamp(raw.get("@timestamp", "")),
        "level": (raw.get("log", {}) or {}).get("level", "INFO"),
        "logger_name": (raw.get("log", {}) or {}).get("logger", ""),
        "message": raw.get("message", ""),
        "event_category": event_category,
        # 分布式追踪
        "trace_id": (raw.get("trace", {}) or {}).get("id", ""),
        "span_id": (raw.get("trace", {}) or {}).get("span_id", ""),
    }

    # ginkgo.* 字段映射
    for ginkgo_key, model_key in _FIELD_MAPPING.items():
        val = ginkgo.get(ginkgo_key)
        if val is not None:
            result[model_key] = val

    # source 特殊处理（Vector 中 source_type 非字符串时映射）
    source_val = ginkgo.get("source_type")
    if source_val is not None and not isinstance(source_val, str):
        result["source"] = source_val

    # business_timestamp 格式化
    if "business_timestamp" in result and result["business_timestamp"]:
        bt = result["business_timestamp"]
        if isinstance(bt, str):
            result["business_timestamp"] = _parse_timestamp(bt)

    # 元数据
    process = raw.get("process", {}) or {}
    if process.get("pid"):
        result["pid"] = process["pid"]
    host = raw.get("host", {}) or {}
    if host.get("hostname"):
        result["hostname"] = host["hostname"]

    result["ingested_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return result


class LogIngester:
    """事后日志灌入器"""

    def ingest_file(self, log_path: str) -> IngestResult:
        """读取单个日志文件，批量灌入 ClickHouse"""
        result = IngestResult()

        if not os.path.exists(log_path):
            GLOG.WARN(f"Log file not found: {log_path}")
            return result

        # 按 category 分组收集 ORM 对象
        batches: Dict[str, List] = {}
        category_models = _get_category_models()

        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                result.total_lines += 1

                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    result.skipped += 1
                    continue

                try:
                    flat = normalize(raw)
                    if flat is None:
                        result.skipped += 1
                        continue

                    category = flat.get("event_category", "")
                    model_cls = category_models.get(category)
                    if model_cls is None:
                        result.skipped += 1
                        continue

                    # 构造 ORM 对象（只传 Model 中存在的列）
                    obj = model_cls()
                    for col in model_cls.__table__.columns:
                        if col.name in flat:
                            setattr(obj, col.name, flat[col.name])

                    batches.setdefault(category, []).append(obj)

                    # 达到批次大小时 flush
                    if len(batches.get(category, [])) >= BATCH_SIZE:
                        self._flush_batch(batches[category], result)
                        batches[category] = []

                except Exception as e:
                    result.errors += 1
                    if len(result.error_messages) < 10:
                        result.error_messages.append(str(e))

        # flush 剩余
        for category, items in batches.items():
            if items:
                self._flush_batch(items, result)

        GLOG.INFO(f"LogIngest: {log_path} → {result.inserted} inserted, {result.skipped} skipped, {result.errors} errors")
        return result

    def ingest_task_logs(self, task_uuid: str) -> IngestResult:
        """根据 task_uuid 前缀匹配 bt_<prefix>_*.log 文件并灌入"""
        log_dir = GCONF.LOGGING_PATH
        prefix = f"bt_{task_uuid[:8]}"
        result = IngestResult()

        if not os.path.exists(log_dir):
            GLOG.WARN(f"Log directory not found: {log_dir}")
            return result

        for fname in sorted(Path(log_dir).glob(f"{prefix}_*.log")):
            file_result = self.ingest_file(str(fname))
            result.total_lines += file_result.total_lines
            result.inserted += file_result.inserted
            result.skipped += file_result.skipped
            result.errors += file_result.errors
            result.error_messages.extend(file_result.error_messages)

        return result

    def _flush_batch(self, items: List, result: IngestResult):
        """批量写入 ClickHouse"""
        try:
            from ginkgo.data.drivers import add_all
            count, _ = add_all(items)
            result.inserted += count
        except Exception as e:
            result.errors += len(items)
            GLOG.WARN(f"LogIngest batch failed ({len(items)} records): {e}")
            if len(result.error_messages) < 10:
                result.error_messages.append(str(e))
```

- [ ] **Step 2: 验证 normalize 逻辑与 Vector TOML 一致**

手动对比 `normalize()` 中的字段映射与 `.conf/vector.toml` L39-133 的 `normalize_fields` transform，确认所有字段一一对应。

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/services/logging/log_ingester.py
git commit -m "feat: add LogIngester for post-backtest log ingestion into ClickHouse"
```

---

### Task 2: 更新 __init__.py 导出

**Files:**
- Modify: `src/ginkgo/services/logging/__init__.py`

- [ ] **Step 1: 添加 LogIngester 和 IngestResult 导出**

在现有 imports 后添加：

```python
from ginkgo.services.logging.log_ingester import LogIngester, IngestResult
```

更新 `__all__` 列表添加 `"LogIngester"` 和 `"IngestResult"`。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/services/logging/__init__.py
git commit -m "feat: export LogIngester from logging service module"
```

---

### Task 3: 集成到 backtest_cli.py

**Files:**
- Modify: `src/ginkgo/client/backtest_cli.py`

- [ ] **Step 1: 在 `_save_results()` 之后添加日志灌入调用**

在 `run_task` 函数的非 bg 路径中（约 L211 之后），`_save_results()` 调用后添加：

```python
            _save_results(service, task.uuid, engine, portfolio_uuid)

            # 灌入日志到 ClickHouse（静默降级）
            try:
                from ginkgo.services.logging.log_ingester import LogIngester
                ingester = LogIngester()
                ingest_result = ingester.ingest_task_logs(task.uuid)
                if ingest_result.inserted > 0:
                    console.print(f"   Logs ingested: {ingest_result.inserted} records")
            except Exception:
                pass  # 静默降级，不影响回测结果
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/client/backtest_cli.py
git commit -m "feat: auto-ingest backtest logs to ClickHouse after CLI run"
```

---

### Task 4: 端到端验证

**Files:** 无代码变更

- [ ] **Step 1: 创建并运行 CLI 回测**

```bash
ginkgo backtest create --portfolio bb739b51f0634fb0b4403298443b516d --start 2024-01-01 --end 2024-01-31 --name "日志灌入验证"
ginkgo backtest run <uuid>
```

预期：控制台输出 `Logs ingested: N records`

- [ ] **Step 2: 验证 ClickHouse 中有日志数据**

```sql
SELECT event_type, count() FROM ginkgo_logs_backtest
WHERE task_id = '<uuid>' GROUP BY event_type ORDER BY count() DESC
```

预期：多种 event_type（SIGNALGENERATION, ORDERSUBMITTED 等），非空。

- [ ] **Step 3: 验证 WebUI 日志页面可查看**

打开 WebUI → 回测任务详情 → 日志 tab，确认有日志条目显示。

- [ ] **Step 4: 验证去重**

如果 Vector 同时在跑，检查同一条日志是否被去重（ReplacingMergeTree 最终只保留一条）。

- [ ] **Step 5: Commit 验证结果（如有修复）**
