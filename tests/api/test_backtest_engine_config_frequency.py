# #5386 — engine_config.frequency 被丢弃
"""
验证 API 创建回测时 engine_config.frequency 被正确捕获并写入 config，
而非被 Pydantic 静默丢弃。

根因：frequency 定义在 ComponentConfig（误置），EngineConfig 无此字段，
客户端 POST engine_config.frequency 时 Pydantic ignore 多余字段 → 丢弃。
build_backtest_config 只在 component_config 存在时映射 frequency。
"""
import pytest


class TestEngineConfigRetainsFrequency:
    """EngineConfig 应接受并保留 frequency 字段"""

    def test_engine_config_accepts_frequency(self):
        from api.backtest import EngineConfig

        cfg = EngineConfig(
            start_date="2025-06-01",
            end_date="2025-12-31",
            frequency="MIN",
        )
        assert cfg.frequency == "MIN"

    def test_engine_config_frequency_defaults_to_day(self):
        from api.backtest import EngineConfig

        cfg = EngineConfig(start_date="2025-06-01", end_date="2025-12-31")
        assert cfg.frequency == "DAY"


class TestBuildBacktestConfigIncludesFrequency:
    """build_backtest_config 应把 engine_config.frequency 写入 config（顶层）"""

    def test_config_contains_frequency_from_engine_config(self):
        from api.backtest import build_backtest_config, BacktestTaskCreate, EngineConfig

        data = BacktestTaskCreate(
            name="test",
            portfolio_uuids=["p-uuid-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
                frequency="MIN",
            ),
        )
        config = build_backtest_config(data)
        assert "frequency" in config, "engine_config.frequency 未写入 config"
        assert config["frequency"] == "MIN"

    def test_config_frequency_defaults_to_day_without_component_config(self):
        """仅 engine_config（无 component_config）时，frequency 仍应落入 config"""
        from api.backtest import build_backtest_config, BacktestTaskCreate, EngineConfig

        data = BacktestTaskCreate(
            name="test",
            portfolio_uuids=["p-uuid-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )
        config = build_backtest_config(data)
        assert config["frequency"] == "DAY"
