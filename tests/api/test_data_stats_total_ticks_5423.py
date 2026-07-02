"""#5423: GET /api/v1/data/stats 的 total_ticks 必须反映实际数据量。

原实现第 171 行硬编码 `"total_ticks": 0`（注释：Tick数据分表存储，无法直接统计总量），
导致同步历史显示 543452 条但 stats 端点恒报 0。本测试锁定：
  total_ticks 取自 tick_service.count_all()（跨分表聚合），而非硬编码 0。

Upstream: api.data.get_data_stats
Downstream: TickService.count_all（#5423 新增，跨 _Tick 分表 system.tables 聚合）
"""
import asyncio

import pytest

from ginkgo.data.services.base_service import ServiceResult


def _make_service_getters(total_ticks: int):
    """构造 4 个 service getter mock，tick_service.count_all 返回 total_ticks。

    其余 count/get 给空数据，避免抽样循环 (get_tick_data_summary) 干扰断言焦点。
    """
    from unittest.mock import MagicMock

    mock_stock = MagicMock()
    mock_stock.count.return_value = ServiceResult.success(data=2)
    mock_stock.get.return_value = ServiceResult.success(data=[])  # 空样本 → 抽样循环零迭代

    mock_bar = MagicMock()
    mock_bar.count.return_value = ServiceResult.success(data=100)

    mock_adj = MagicMock()
    mock_adj.count.return_value = ServiceResult.success(data=5)

    mock_tick = MagicMock()
    mock_tick.count_all.return_value = ServiceResult.success(data=total_ticks)

    return {
        "get_stockinfo_service": lambda: mock_stock,
        "get_bar_service": lambda: mock_bar,
        "get_adjustfactor_service": lambda: mock_adj,
        "get_tick_service": lambda: mock_tick,
    }, mock_tick


@pytest.mark.unit
def test_total_ticks_reflects_count_all_not_hardcoded_zero(api_modules, monkeypatch):
    """#5423: total_ticks 必须取自 tick_service.count_all()，不能恒为 0。

    RED：当前 data.py:171 硬编码 `"total_ticks": 0`，count_all 返回 543452 但端点报 0。
    GREEN 后 total_ticks == 543452。
    """
    from api.data import get_data_stats

    getters, mock_tick = _make_service_getters(total_ticks=543452)
    for name, fn in getters.items():
        monkeypatch.setattr(f"api.data.{name}", fn)

    result = asyncio.run(get_data_stats())

    assert result["data"]["total_ticks"] == 543452, (
        "total_ticks 应取自 tick_service.count_all()，而非硬编码 0"
    )
    mock_tick.count_all.assert_called_once()


@pytest.mark.unit
def test_total_ticks_zero_when_no_tick_data(api_modules, monkeypatch):
    """无 tick 数据时 count_all 返回 0，total_ticks 也为 0（量级真实，非误导）。

    锁定降级语义：与同步历史一致——若确无数据，0 是真值而非占位。
    """
    from api.data import get_data_stats

    getters, mock_tick = _make_service_getters(total_ticks=0)
    for name, fn in getters.items():
        monkeypatch.setattr(f"api.data.{name}", fn)

    result = asyncio.run(get_data_stats())

    assert result["data"]["total_ticks"] == 0
    mock_tick.count_all.assert_called_once()


@pytest.mark.unit
def test_total_ticks_degrades_to_zero_on_count_all_failure(api_modules, monkeypatch):
    """count_all 失败（service 层返回 error）时 total_ticks 降级为 0，端点不 500。

    CRUD 层已对 DB 异常降级返回 0（见 test_tick_crud_mock），service 层包装错误为
    ServiceResult.error。端点对 is_success() 失败的 count_all 应取 0，保持与
    stockinfo/bar/adjustfactor 一致的容错语义。
    """
    from api.data import get_data_stats

    getters, mock_tick = _make_service_getters(total_ticks=0)
    # 覆盖为 error，模拟 service 层异常
    mock_tick.count_all.return_value = ServiceResult.error(error="db unreachable")
    for name, fn in getters.items():
        monkeypatch.setattr(f"api.data.{name}", fn)

    result = asyncio.run(get_data_stats())

    assert result["data"]["total_ticks"] == 0
