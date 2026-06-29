"""#6282: backtest run 前数据预检

回测前预查 selector codes 的 day bar 覆盖，数据缺失/稀疏时前置阻断，
而非跑完整个回测才给模糊警告「selector may have returned empty symbols」。

模块: task_helpers.check_data_coverage + resolve_selector_codes, backtest_cli.run_task 调用。
"""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock

from ginkgo.enums import FILE_TYPES
from ginkgo.workers.backtest_worker.task_helpers import (
    check_data_coverage,
    resolve_selector_codes,
    build_preflight_warning,
)


class TestCheckDataCoverage:
    """check_data_coverage: 按 code + 窗口计数 bar，标记稀疏/缺失"""

    @pytest.mark.unit
    def test_flags_sparse_and_missing_keeps_sufficient(self):
        """覆盖不均（000001:3 / 000002:0 / 600036:244）应分别标 sparse/missing/ok

        RED: check_data_coverage 尚不存在 → ImportError。
        """
        bar_crud = MagicMock()
        counts = {"000001.SZ": 3, "000002.SZ": 0, "600036.SH": 244}

        def fake_count(filters):
            return counts[filters["code"]]

        bar_crud.count.side_effect = fake_count

        coverage, sparse = check_data_coverage(
            codes=["000001.SZ", "000002.SZ", "600036.SH"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2026, 1, 1),
            bar_crud=bar_crud,
            min_bars=10,
        )

        assert coverage == {"000001.SZ": 3, "000002.SZ": 0, "600036.SH": 244}
        # 稀疏(3<10) + 缺失(0<10) 被标，充足(244) 不标
        assert set(sparse) == {"000001.SZ", "000002.SZ"}
        assert "600036.SH" not in sparse

    @pytest.mark.unit
    def test_count_called_with_code_and_window_filters(self):
        """bar_crud.count 须带 code + timestamp 窗口过滤（否则查全表非窗口）"""
        bar_crud = MagicMock()
        bar_crud.count.return_value = 100

        check_data_coverage(
            codes=["000001.SZ"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2026, 1, 1),
            bar_crud=bar_crud,
        )

        bar_crud.count.assert_called_once()
        filters = bar_crud.count.call_args.args[0]
        assert filters["code"] == "000001.SZ"
        assert filters["timestamp__gte"] == datetime(2025, 1, 1)
        assert filters["timestamp__lte"] == datetime(2026, 1, 1)

    @pytest.mark.unit
    def test_count_exception_treated_as_zero(self):
        """查 bar 抛异常（如表不存在）应降级为 0 条，不阻断预检流程"""
        bar_crud = MagicMock()
        bar_crud.count.side_effect = RuntimeError("table missing")

        coverage, sparse = check_data_coverage(
            codes=["000001.SZ"],
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2026, 1, 1),
            bar_crud=bar_crud,
            min_bars=10,
        )
        assert coverage["000001.SZ"] == 0
        assert "000001.SZ" in sparse


class TestResolveSelectorCodes:
    """resolve_selector_codes: 从 FixedSelector params 提取显式 codes"""

    @staticmethod
    def _mapping(uuid, type_):
        m = MagicMock()
        m.uuid = uuid
        m.type = type_
        return m

    @staticmethod
    def _param(value):
        p = MagicMock()
        p.value = value
        return p

    @pytest.mark.unit
    def test_extracts_codes_from_fixed_selector_comma_string(self):
        """FixedSelector codes 存为逗号分隔串 → 提取全部 code"""
        mapping_crud = MagicMock()
        sel = self._mapping("map-sel", FILE_TYPES.SELECTOR.value)
        mapping_crud.find.return_value = [sel]
        param_crud = MagicMock()
        param_crud.find_by_mapping_id.return_value = [
            self._param("default_selector"),  # name（非 code）
            self._param("000001.SZ,000002.SZ,600036.SH"),  # codes
        ]

        codes = resolve_selector_codes("pid", mapping_crud, param_crud)

        assert set(codes) == {"000001.SZ", "000002.SZ", "600036.SH"}

    @pytest.mark.unit
    def test_extracts_codes_from_json_list_value(self):
        """codes 存为 json 序列化的 list 串 → 反序列化后提取"""
        mapping_crud = MagicMock()
        mapping_crud.find.return_value = [self._mapping("map-sel", FILE_TYPES.SELECTOR.value)]
        param_crud = MagicMock()
        param_crud.find_by_mapping_id.return_value = [
            self._param('["000001.SZ", "000002.SZ"]'),
        ]

        codes = resolve_selector_codes("pid", mapping_crud, param_crud)

        assert set(codes) == {"000001.SZ", "000002.SZ"}

    @pytest.mark.unit
    def test_dynamic_selector_no_codes_returns_empty(self):
        """动态 selector（cn_all/momentum，params 无 code token）→ 返回空（调用方跳过预检）"""
        mapping_crud = MagicMock()
        mapping_crud.find.return_value = [self._mapping("map-sel", FILE_TYPES.SELECTOR.value)]
        param_crud = MagicMock()
        param_crud.find_by_mapping_id.return_value = [
            self._param("cn_all"),  # 无 6 位代码 token
        ]

        codes = resolve_selector_codes("pid", mapping_crud, param_crud)

        assert codes == []

    @pytest.mark.unit
    def test_only_selector_mappings_scanned_not_strategy(self):
        """strategy mapping 的 params 不应被扫（仅 SELECTOR 类型）"""
        mapping_crud = MagicMock()
        mapping_crud.find.return_value = [
            self._mapping("map-strat", FILE_TYPES.STRATEGY.value),
            self._mapping("map-sel", FILE_TYPES.SELECTOR.value),
        ]
        param_crud = MagicMock()
        # 不同 mapping_uuid 返回不同 params
        def by_id(mid):
            if mid == "map-strat":
                return [self._param("000999.SZ")]  # strategy 的 code-like 值，不应被提
            return [self._param("000001.SZ")]
        param_crud.find_by_mapping_id.side_effect = by_id

        codes = resolve_selector_codes("pid", mapping_crud, param_crud)

        assert codes == ["000001.SZ"]


class TestBuildPreflightWarning:
    """build_preflight_warning: sparse 报告 → 人可读阻断消息"""

    @pytest.mark.unit
    def test_sparse_report_yields_message_naming_code_window_count(self):
        """sparse 非空 → 消息须含 code、窗口、bar 条数、建议"""
        report = {
            "codes": ["000001.SZ", "000002.SZ"],
            "coverage": {"000001.SZ": 3, "000002.SZ": 0},
            "sparse": ["000001.SZ", "000002.SZ"],
            "ok": False,
        }
        msg = build_preflight_warning(report, "2025-01-01", "2026-01-01")
        assert msg is not None
        assert "000001.SZ" in msg
        assert "000002.SZ" in msg
        assert "2025-01-01" in msg
        assert "2026-01-01" in msg
        # 条数须体现，让用户知道是「几乎没数据」还是「完全没数据」
        assert "3" in msg
        assert "0" in msg

    @pytest.mark.unit
    def test_ok_report_returns_none(self):
        """ok=True（无稀疏）→ 返回 None（调用方放行）"""
        report = {
            "codes": ["000001.SZ"],
            "coverage": {"000001.SZ": 244},
            "sparse": [],
            "ok": True,
        }
        assert build_preflight_warning(report, "2025-01-01", "2026-01-01") is None

    @pytest.mark.unit
    def test_dynamic_selector_ok_report_returns_none(self):
        """动态 selector（codes 空）→ 无可预查 → 返回 None（放行，不误阻断）"""
        report = {"codes": [], "coverage": {}, "sparse": [], "ok": True}
        assert build_preflight_warning(report, "2025-01-01", "2026-01-01") is None
