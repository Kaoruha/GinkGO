"""Unit tests for LogIngester task_uuid → bt_*.log 文件匹配 (#5293).

回归: ``ingest_task_logs`` 的 glob 曾要求 ``bt_{uuid[:8]}_*`` —— 第 8 位 hex 后紧跟
下划线。但实际日志文件由 ``engine_assembly_service`` 以 **全 UUID** 命名
(``bt_<32hex>_<ts>``)，下划线落在第 32 位后。glob 永不匹配 → 本地 CLI 回测日志
不灌入 ClickHouse → ``ginkgo logging logs --task <id>`` 恒空。

本测试构造全 UUID 命名的真实文件，验证 ``ingest_task_logs`` 能命中并灌入。
"""
import json
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestIngestTaskLogsGlob:
    """ingest_task_logs 必须匹配全 UUID 命名的 bt_*.log 文件 (#5293)。"""

    FULL_UUID = "fb965d187695463aada70ce163823b79"

    def _write_backtest_log(self, path, task_id: str):
        """写一行合法的 backtest-category JSON 日志 (带 task_id)。"""
        line = {
            "@timestamp": "2026-07-11 12:00:00",
            "log": {"level": "INFO", "logger": "ginkgo"},
            "message": "engine event",
            "ginkgo": {"log_category": "backtest", "task_id": task_id},
        }
        path.write_text(json.dumps(line) + "\n", encoding="utf-8")

    def test_matches_full_uuid_filename(self, tmp_path):
        """全 UUID 文件名 ``bt_<32hex>_<ts>`` 必须被 ingest_task_logs 命中。"""
        from ginkgo.services.logging.log_ingester import LogIngester

        log_file = tmp_path / f"bt_{self.FULL_UUID}_20260711120000.log"
        self._write_backtest_log(log_file, self.FULL_UUID)

        ingester = LogIngester()
        with patch("ginkgo.services.logging.log_ingester.GCONF") as mock_gconf, \
             patch("ginkgo.data.drivers.add_all", return_value=(1, None)):
            mock_gconf.LOGGING_PATH = str(tmp_path)
            result = ingester.ingest_task_logs(self.FULL_UUID)

        assert result.total_lines == 1, (
            f"glob 未命中全 UUID 文件 (inserted={result.inserted}, "
            f"total_lines={result.total_lines}) —— #5293 回归"
        )
        assert result.inserted == 1

    def test_matches_short_prefix_filename(self, tmp_path):
        """短前缀文件名 ``bt_<8hex>_<ts>`` (worker 路径) 仍应被命中。"""
        from ginkgo.services.logging.log_ingester import LogIngester

        log_file = tmp_path / f"bt_{self.FULL_UUID[:8]}_20260711120000.log"
        self._write_backtest_log(log_file, self.FULL_UUID)

        ingester = LogIngester()
        with patch("ginkgo.services.logging.log_ingester.GCONF") as mock_gconf, \
             patch("ginkgo.data.drivers.add_all", return_value=(1, None)):
            mock_gconf.LOGGING_PATH = str(tmp_path)
            result = ingester.ingest_task_logs(self.FULL_UUID)

        assert result.total_lines == 1
        assert result.inserted == 1

    def test_does_not_match_unrelated_task(self, tmp_path):
        """不同 task 的文件不应被误命中 (8-hex 前缀仍保证唯一性)。"""
        from ginkgo.services.logging.log_ingester import LogIngester

        other_uuid = "aaaaaaaabbbbccccddddeeeeffff0000"
        log_file = tmp_path / f"bt_{other_uuid}_20260711120000.log"
        self._write_backtest_log(log_file, other_uuid)

        ingester = LogIngester()
        with patch("ginkgo.services.logging.log_ingester.GCONF") as mock_gconf, \
             patch("ginkgo.data.drivers.add_all", return_value=(0, None)):
            mock_gconf.LOGGING_PATH = str(tmp_path)
            result = ingester.ingest_task_logs(self.FULL_UUID)

        assert result.total_lines == 0
