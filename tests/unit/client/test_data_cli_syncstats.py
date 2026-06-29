"""#6054: SyncStats 三态计数器 + 统一汇总格式。

data_cli.sync 的 day/tick/adjustfactor 三分支各自维护 success_count/error_count
（day 另有 skipped_count），汇总格式不一致（day 三态 vs tick/adjustfactor 二态），
且 adjustfactor 的 no-data 情况漏计数。SyncStats 收敛「三态计数 + 格式化」到一处，
三分支共用，杜绝漂移（见 issue #6054 简报）。
"""
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest

from ginkgo.client.data_cli import SyncStats


class TestSyncStats:
    """SyncStats 纯逻辑：三态计数 + 统一 summary 格式。"""

    def test_empty_summary_format(self):
        """零计数 → ``{Type} sync completed. Success: 0, Skipped: 0, Errors: 0``。"""
        stats = SyncStats()
        assert stats.summary("Day") == (
            "Day sync completed. Success: 0, Skipped: 0, Errors: 0"
        )

    def test_three_state_counts(self):
        """record_success/skipped/error 累加 → summary 反映正确计数。"""
        stats = SyncStats()
        stats.record_success()
        stats.record_success()
        stats.record_skipped()
        stats.record_error()
        stats.record_error()
        stats.record_error()
        assert stats.summary("Tick") == (
            "Tick sync completed. Success: 2, Skipped: 1, Errors: 3"
        )

    def test_type_name_interpolated(self):
        """type_name 原样插到汇总行开头（day/tick/adjustfactor 三分支复用）。"""
        stats = SyncStats()
        stats.record_success()
        assert stats.summary("Adjustfactor").startswith("Adjustfactor sync completed.")
