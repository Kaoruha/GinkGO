# Upstream: GinkgoLogger (JSON 日志文件输出)
# Downstream: add_all(), MBacktestLog/MComponentLog/MPerformanceLog
# Role: 事后日志灌入器 — 等价于 Vector 的读文件→解析→路由→INSERT 流水线

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


# JSON ginkgo.* 字段 → ORM Model 列名
# 和 .conf/vector.toml normalize_fields 一一对应
_FIELD_MAPPING = {
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
    "task_id": "task_id",
    "engine_id": "engine_id",
    "portfolio_id": "portfolio_id",
    "business_timestamp": "business_timestamp",
}

# log_category → ORM Model（延迟填充避免循环依赖）
_CATEGORY_MODEL: Dict[str, Type] = {}

BATCH_SIZE = 500


def _get_category_models():
    global _CATEGORY_MODEL
    if not _CATEGORY_MODEL:
        from ginkgo.data.models import (
            MBacktestLog, MComponentLog, MPerformanceLog,
        )
        _CATEGORY_MODEL = {
            "backtest": MBacktestLog,
            "component": MComponentLog,
            "performance": MPerformanceLog,
        }
    return _CATEGORY_MODEL


def _parse_timestamp(ts_str: str) -> Optional[str]:
    """将 ISO/datetime 字符串转为 ClickHouse 兼容的 %Y-%m-%d %H:%M:%S"""
    if not ts_str:
        return None
    ts_str = ts_str.replace("Z", "").replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
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

    event_category = ginkgo.get("log_category", "")
    if not event_category:
        return None

    result = {
        "timestamp": _parse_timestamp(raw.get("@timestamp", "")),
        "level": (raw.get("log", {}) or {}).get("level", "INFO"),
        "logger_name": (raw.get("log", {}) or {}).get("logger", ""),
        "message": raw.get("message", ""),
        "event_category": event_category,
        "trace_id": (raw.get("trace", {}) or {}).get("id", ""),
        "span_id": (raw.get("trace", {}) or {}).get("span_id", ""),
    }

    for ginkgo_key, model_key in _FIELD_MAPPING.items():
        val = ginkgo.get(ginkgo_key)
        if val is not None:
            result[model_key] = val

    # source 特殊处理
    source_val = ginkgo.get("source_type")
    if source_val is not None and not isinstance(source_val, str):
        result["source"] = source_val

    # business_timestamp 格式化
    if "business_timestamp" in result and isinstance(result["business_timestamp"], str):
        result["business_timestamp"] = _parse_timestamp(result["business_timestamp"])

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

                    obj = model_cls()
                    for col in model_cls.__table__.columns:
                        if col.name in flat:
                            setattr(obj, col.name, flat[col.name])

                    batches.setdefault(category, []).append(obj)

                    if len(batches[category]) >= BATCH_SIZE:
                        self._flush_batch(batches[category], result)
                        batches[category] = []

                except Exception as e:
                    result.errors += 1
                    if len(result.error_messages) < 10:
                        result.error_messages.append(str(e))

        for items in batches.values():
            if items:
                self._flush_batch(items, result)

        GLOG.INFO(f"LogIngest: {log_path} → {result.inserted} inserted, "
                  f"{result.skipped} skipped, {result.errors} errors")
        return result

    def ingest_task_logs(self, task_uuid: str) -> IngestResult:
        """根据 task_uuid 前缀匹配 bt_<prefix>*.log 文件并灌入 (#5293)。

        文件命名有两个 producer，下划线落点不同：
        - ``engine_assembly_service`` (CLI/orchestrator): ``bt_<32hex 全UUID>_<ts>``
        - ``backtest_worker.task_processor``: ``bt_<8hex>_<ts>``

        故 glob 用 ``bt_{task_uuid[:8]}*`` —— 不要求第 8 位后紧跟下划线，
        让 ``*`` 同时吸收 ``_<ts>`` (短) 与 ``<剩余24hex>_<ts>`` (全)。
        原版 ``bt_{task_uuid[:8]}_*`` 要求下划线在第 8 位后, 全 UUID 文件
        下划线在第 32 位后 → 永不匹配 → 本地 CLI 回测日志不灌入 ClickHouse
        → ``ginkgo logging logs --task <id>`` 恒空 (#5293)。
        行级 task_id 来自日志内容而非文件名, 文件级前缀碰撞不影响查询正确性。
        """
        log_dir = GCONF.LOGGING_PATH
        prefix = f"bt_{task_uuid[:8]}"
        result = IngestResult()

        if not os.path.exists(log_dir):
            GLOG.WARN(f"Log directory not found: {log_dir}")
            return result

        for fname in sorted(Path(log_dir).glob(f"{prefix}*.log")):
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
