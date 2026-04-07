# Upstream: PaperTradingWorker (每日循环调用偏差检测)
# Downstream: LiveDeviationDetector (z-score检测)、Redis (基线缓存)、Kafka (告警)
# Role: 偏差检测共享逻辑，管理基线获取、告警发送和自动熔断
import json
from datetime import datetime
from typing import Dict, List, Optional

from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG


class DeviationChecker:
    """Shared deviation detection logic for Paper and Live modes."""

    def __init__(self, producer=None, source: str = "deviation-checker", takedown_callback=None):
        self._producer = producer
        self._source = source
        self._takedown_callback = takedown_callback
        self._detectors: Dict[str, object] = {}

    def get_detector(self, portfolio_id: str):
        return self._detectors.get(portfolio_id)

    def set_detector(self, portfolio_id: str, detector) -> None:
        self._detectors[portfolio_id] = detector

    def get_baseline(self, portfolio_id: str) -> Optional[dict]:
        """Get baseline from Redis cache, compute on miss."""
        from ginkgo import services

        try:
            redis_svc = services.data.redis_service()
            if redis_svc:
                cached = redis_svc.get(f"deviation:baseline:{portfolio_id}")
                if cached:
                    return json.loads(cached)
        except Exception:
            pass

        try:
            redis_svc = services.data.redis_service()
            source_id = None
            if redis_svc:
                source_id = redis_svc.get(f"deviation:source:{portfolio_id}")

            if not source_id:
                GLOG.DEBUG(f"[DEV-CHECKER] No source portfolio for {portfolio_id[:8]}")
                return None

            task_service = services.data.backtest_task_service()
            task_result = task_service.list(
                portfolio_id=source_id, status="completed", page_size=1,
            )
            if not task_result.is_success() or not task_result.data:
                return None

            latest_task = task_result.data[0] if isinstance(task_result.data, list) else task_result.data
            run_id = getattr(latest_task, "run_id", None)
            engine_id = getattr(latest_task, "engine_id", None)
            if not run_id:
                return None

            from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
            evaluator = BacktestEvaluator()
            eval_result = evaluator.evaluate_backtest_stability(
                portfolio_id=source_id, engine_id=engine_id,
            )
            if eval_result.get("status") != "success":
                return None

            baseline = eval_result.get("monitoring_baseline")
            if not baseline:
                return None

            if redis_svc:
                redis_svc.set(
                    f"deviation:baseline:{portfolio_id}",
                    json.dumps(baseline, default=str),
                )
            return baseline
        except Exception as e:
            GLOG.WARN(f"[DEV-CHECKER] Baseline computation failed for {portfolio_id[:8]}: {e}")
            return None

    def get_deviation_config(self, portfolio_id: str) -> dict:
        """Read deviation detection config from Redis."""
        from ginkgo import services

        try:
            redis_svc = services.data.redis_service()
            if redis_svc:
                config_json = redis_svc.get(f"deviation:config:{portfolio_id}")
                if config_json:
                    return json.loads(config_json)
        except Exception:
            pass

        return {
            "auto_takedown": False,
            "slice_period_days": None,
            "confidence_levels": [0.68, 0.95, 0.99],
            "alert_channels": ["kafka"],
            "check_time": "20:30",
            "anomaly_pnl_threshold": -0.05,
        }

    def run_deviation_check(self, portfolio_id: str, today_records: Dict) -> Optional[Dict]:
        """Run deviation check for a single portfolio. Returns result dict or None."""
        detector = self._detectors.get(portfolio_id)
        if not detector:
            return None

        try:
            slice_complete = detector.accumulate_live_data(
                analyzer_records=today_records.get("analyzers"),
                signal_records=today_records.get("signals"),
                order_records=today_records.get("orders"),
            )
            if slice_complete:
                return detector.check_deviation_on_slice_complete()
        except Exception as e:
            GLOG.ERROR(f"[DEV-CHECKER] Deviation check error for {portfolio_id[:8]}: {e}")

        return None

    def run_daily_point_check(self, portfolio_id: str, day_index: int,
                               current_metrics: Dict[str, float]) -> Optional[Dict]:
        """
        每日点时偏差检测（不依赖切片完成）

        Args:
            portfolio_id: 组合ID
            day_index: 当前切片内的天数（从 1 开始）
            current_metrics: 当前指标值

        Returns:
            检测结果或 None
        """
        detector = self._detectors.get(portfolio_id)
        if not detector:
            return None

        try:
            result = detector.check_point_in_time(day_index, current_metrics)
            if result and result.get("status") == "completed":
                config = self.get_deviation_config(portfolio_id)
                self.handle_deviation_result(
                    portfolio_id, result,
                    auto_takedown=config.get("auto_takedown", False),
                )
            return result
        except Exception as e:
            GLOG.ERROR(f"[DEV-CHECKER] Daily point check error for {portfolio_id[:8]}: {e}")
            return None

    def handle_deviation_result(self, portfolio_id: str, result: Dict, auto_takedown: bool = False) -> None:
        """Handle deviation result: alert + optional auto takedown."""
        level = result.get("overall_level", "NORMAL")

        if level == "NORMAL":
            GLOG.DEBUG(f"[DEV-CHECKER] {portfolio_id[:8]}: deviation NORMAL")
            return

        deviations = result.get("deviations", {})
        severity_metrics = [
            f"{k} (z={v['z_score']:.1f})"
            for k, v in deviations.items()
            if v.get("level") != "NORMAL"
        ]

        if level == "MODERATE":
            GLOG.WARN(f"[DEV-CHECKER] {portfolio_id[:8]}: MODERATE - {', '.join(severity_metrics)}")
        elif level == "SEVERE":
            GLOG.ERROR(f"[DEV-CHECKER] {portfolio_id[:8]}: SEVERE - {', '.join(severity_metrics)}")

        self.send_deviation_alert(portfolio_id, level, result)

        if level == "SEVERE" and auto_takedown and self._takedown_callback:
            GLOG.ERROR(f"[DEV-CHECKER] Auto-takedown triggered for {portfolio_id[:8]}")
            self._takedown_callback(portfolio_id)

    def send_deviation_alert(self, portfolio_id: str, level: str, result: Dict) -> None:
        """Send deviation alert to Kafka SYSTEM_EVENTS with multi-metric details."""
        if not self._producer:
            return

        deviations = result.get("deviations", {})
        deviation_details = [
            {
                "metric": k,
                "level": v.get("level"),
                "z_score": v.get("z_score", 0),
                "threshold": v.get("threshold", 2.0),
            }
            for k, v in deviations.items()
            if v.get("level") != "NORMAL"
        ]

        try:
            self._producer.send(
                KafkaTopics.SYSTEM_EVENTS,
                {
                    "source": self._source,
                    "type": "deviation_alert",
                    "level": level,
                    "portfolio_id": portfolio_id,
                    "deviation_details": deviation_details,
                    "risk_score": result.get("risk_score", 0),
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            GLOG.ERROR(f"[DEV-CHECKER] Failed to send deviation alert: {e}")
