"""#5594: api-stats 端点真实数据聚合测试。

验证 ApiStatsCollector（内存聚合器）的 record/get_stats 行为，
以及 get_api_stats 端点不再返回硬编码假数据。
"""
# 注意：api_modules fixture 临时把 api/ 加进 sys.path，
# 使 `from middleware.api_stats import collector` 可解析（同 rate_limit 的 from core.logging）。
# 单个测试用 `def test_x(api_modules):` 然后在函数内 import。


def test_collector_records_single_request(api_modules):
    """record 一个 200 请求 → today/month_calls=1, success_rate=100, avg_response_time>0。"""
    from middleware.api_stats import collector

    collector.reset()
    collector.record(status_code=200, response_time_ms=12.5)

    stats = collector.get_stats()
    assert stats["today_calls"] == 1
    assert stats["month_calls"] == 1
    assert stats["success_rate"] == 100.0
    assert stats["avg_response_time"] == 12.5


def test_collector_success_rate_mixed_status(api_modules):
    """200 + 500 → success_rate=50.0（2xx 占比）。"""
    from middleware.api_stats import collector

    collector.reset()
    collector.record(status_code=200, response_time_ms=10.0)
    collector.record(status_code=500, response_time_ms=20.0)

    stats = collector.get_stats()
    assert stats["today_calls"] == 2
    assert stats["success_rate"] == 50.0


def test_collector_avg_response_time_is_mean(api_modules):
    """多个响应时间 → avg=算术均值。"""
    from middleware.api_stats import collector

    collector.reset()
    collector.record(status_code=200, response_time_ms=10.0)
    collector.record(status_code=200, response_time_ms=30.0)

    stats = collector.get_stats()
    assert stats["avg_response_time"] == 20.0


def test_endpoint_returns_collector_stats_not_hardcoded(api_modules, monkeypatch):
    """端点应返回 collector 的真实统计，而非硬编码 15234/456789。"""
    import asyncio

    from middleware.api_stats import collector

    fixed = {
        "today_calls": 7,
        "month_calls": 42,
        "success_rate": 90.0,
        "avg_response_time": 33.0,
    }
    monkeypatch.setattr(collector, "get_stats", lambda: fixed)

    # api_modules 把 api/api/settings.py 折叠为 api.settings（arch_api_test_import_collapse）
    from api.settings import get_api_stats

    result = asyncio.run(get_api_stats())
    assert result["data"] == fixed  # 硬编码 15234 时此处失败
