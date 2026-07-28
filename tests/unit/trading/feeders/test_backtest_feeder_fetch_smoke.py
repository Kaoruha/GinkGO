# Upstream: BacktestFeeder._fetch_day_bars_batch, bar_service.get(code=str), BarMapper
# Downstream: -
# Role: #6745 diff-coverage smoke —— _fetch_day_bars_batch 由全市场批量改 feedable 子集逐股取，
#       本测试覆盖空 codes / 取失败 continue / 正常取三条分支 + advance_time 调用点。
"""
BacktestFeeder._fetch_day_bars_batch 覆盖 smoke（#6745）。

性能根因修复：原 get(code=None) 每日拉全市场逐股复权（165s/天，10 年 ~115h 不可行），
现只取 feedable 子集，每股走 get(code=str) 快速路径。本 smoke mock bar_service 调起
方法体三条分支（空 codes 早返 / 取失败或空数据 continue / 正常取映射），供 diff coverage gate 采集。
"""
from datetime import datetime
from unittest.mock import Mock, patch

import ginkgo.data.mappers as mappers_mod
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.time.providers import LogicalTimeProvider


def _make_bar(code: str) -> Bar:
    return Bar(
        code=code,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.0,
        volume=10000,
        amount=1000000.0,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=datetime(2023, 6, 1, 9, 30),
    )


def test_fetch_day_bars_batch_empty_codes_returns_empty():
    """空 codes 早返 {}，不查 bar_service（feedable 为空时的快速路径）。"""
    feeder = BacktestFeeder()
    feeder.bar_service = Mock()
    result = feeder._fetch_day_bars_batch(datetime(2023, 6, 1, 9, 30), [])
    assert result == {}
    feeder.bar_service.get.assert_not_called()


def test_fetch_day_bars_batch_skips_failed_and_empty_keeps_success():
    """逐股取：A 成功→映射；B success 但 data 空→continue；C success=False→continue。
    覆盖 for 循环 + get 调用 + 两条 continue 分支 + from_models + bars_by_code 赋值。"""
    feeder = BacktestFeeder()
    mock_bs = Mock()
    mock_bs.get.side_effect = lambda code, **kw: (
        ServiceResult(success=True, data=["model_a"]) if code == "A.SZ"
        else (ServiceResult(success=True, data=[]) if code == "B.SZ"
              else ServiceResult(success=False, error="db down"))
    )
    feeder.bar_service = mock_bs
    bar_a = _make_bar("A.SZ")
    with patch.object(mappers_mod.BarMapper, "models_to_entities", return_value=[bar_a]):
        result = feeder._fetch_day_bars_batch(
            datetime(2023, 6, 1, 9, 30), ["A.SZ", "B.SZ", "C.SZ"]
        )
    # 只 A 命中（B 空数据、C 失败均 continue 跳过）
    assert list(result.keys()) == ["A.SZ"]
    assert result["A.SZ"] is bar_a
    # 三个 code 各查一次（逐股快速路径，非全市场批量）
    assert mock_bs.get.call_count == 3
    # 每次都传 code=str + 当日日期
    for call in mock_bs.get.call_args_list:
        assert call.kwargs["code"] in ("A.SZ", "B.SZ", "C.SZ")
        assert call.kwargs["start_date"] == call.kwargs["end_date"]


def test_advance_time_passes_feedable_subset_to_fetch():
    """advance_time 调用点：把 feedable 子集传给 _fetch_day_bars_batch（#6745 契约）。
    覆盖 advance_time 内 `self._fetch_day_bars_batch(target_time, feedable)` 改动行。"""
    feeder = BacktestFeeder()
    feeder.set_time_provider(LogicalTimeProvider(datetime(2023, 6, 1)))
    feeder._interested_codes = ["A.SZ"]

    mock_bs = Mock()
    mock_bs.get_available_codes.return_value = ServiceResult(
        success=True, data=["A.SZ"]
    )
    mock_bs.get.return_value = ServiceResult(success=True, data=["model_a"])
    feeder.bar_service = mock_bs

    bar_a = _make_bar("A.SZ")
    captured: list = []
    feeder.set_event_publisher(captured.append)
    with patch.object(mappers_mod.BarMapper, "models_to_entities", return_value=[bar_a]):
        feeder.advance_time(datetime(2023, 6, 1, 9, 30))

    # feedable=[A] 传给 fetch → 逐股 get(code="A.SZ") 非全市场 code=None
    _args, kwargs = mock_bs.get.call_args
    assert kwargs.get("code") == "A.SZ", "应只取 feedable 子集，逐股 get(code=str)"
    assert len(captured) == 1
