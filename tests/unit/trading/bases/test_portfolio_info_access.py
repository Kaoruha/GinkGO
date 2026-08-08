"""portfolio_info 访问工具函数单测。

覆盖 #6470 提取的 4 个无状态 helper:
- get_positions: 归一 portfolio_base 构建处 list/dict 不一致
- total_market_value: 替换 concentration/volatility 的求和重复
- current_price: 替换 concentration 的 portfolio_info["prices"] 导航
- pnl_ratio: dict/object 双兼容,修复 profit_target 读字段 bug
"""
from types import SimpleNamespace

from ginkgo.trading.bases.portfolio_info_access import (
    current_price,
    get_positions,
    pnl_ratio,
    total_market_value,
)


# ---------------------------- get_positions ----------------------------

class TestGetPositions:
    def test_dict_passthrough(self):
        """dict 形态( portfolio_base.py:887 路径)原样返回。"""
        pos = {"000001.SZ": SimpleNamespace(code="000001.SZ", market_value=10)}
        assert get_positions({"positions": pos}) is pos

    def test_list_normalized_to_dict(self):
        """list 形态(portfolio_base.py:851 路径)归一为 {code: pos} dict。"""
        positions = [
            SimpleNamespace(code="000001.SZ", market_value=10),
            SimpleNamespace(code="000002.SZ", market_value=20),
        ]
        result = get_positions({"positions": positions})
        assert set(result.keys()) == {"000001.SZ", "000002.SZ"}
        assert result["000001.SZ"].market_value == 10

    def test_missing_key_returns_empty(self):
        assert get_positions({}) == {}

    def test_none_returns_empty(self):
        assert get_positions({"positions": None}) == {}

    def test_skips_falsy_entries_in_list(self):
        """list 中的 None/空元素跳过,不污染归一结果。"""
        positions = [None, SimpleNamespace(code="000001.SZ", market_value=10)]
        result = get_positions({"positions": positions})
        assert list(result.keys()) == ["000001.SZ"]


# ---------------------------- total_market_value ----------------------------

class TestTotalMarketValue:
    def test_empty_positions(self):
        assert total_market_value({}) == 0

    def test_sums_market_values(self):
        positions = {
            "A": SimpleNamespace(market_value=100),
            "B": SimpleNamespace(market_value=250.5),
        }
        assert total_market_value({"positions": positions}) == 350.5

    def test_skips_none_and_zero_market_value(self):
        """与 concentration/volatility 原内联守卫一致: if pos and pos.market_value。"""
        positions = {
            "A": SimpleNamespace(market_value=100),
            "B": SimpleNamespace(market_value=None),
            "C": SimpleNamespace(market_value=0),
            "D": None,
        }
        assert total_market_value({"positions": positions}) == 100

    def test_list_form_positions(self):
        """list 形态经 get_positions 归一后求和。"""
        positions = [
            SimpleNamespace(code="A", market_value=100),
            SimpleNamespace(code="B", market_value=200),
        ]
        assert total_market_value({"positions": positions}) == 300


# ---------------------------- current_price ----------------------------

class TestCurrentPrice:
    def test_returns_price_for_code(self):
        info = {"prices": {"000001.SZ": 12.34, "000002.SZ": 56.78}}
        assert current_price(info, "000001.SZ") == 12.34

    def test_missing_code_returns_none(self):
        """不兜底假价 100 — 调用方自行决定回退(守 refactor 行为)。"""
        assert current_price({"prices": {"000001.SZ": 12.34}}, "999999.SZ") is None

    def test_no_prices_key_returns_none(self):
        assert current_price({}, "000001.SZ") is None

    def test_none_prices_returns_none(self):
        assert current_price({"prices": None}, "000001.SZ") is None


# ---------------------------- pnl_ratio ----------------------------

class TestPnlRatio:
    def test_dict_with_ratio(self):
        """profit_target 测试契约: position 为 dict 携 profit_loss_ratio 键。"""
        assert pnl_ratio({"profit_loss_ratio": 0.16}) == 0.16

    def test_dict_missing_key_returns_zero(self):
        """修复点:原 getattr(dict, ...) 恒 0;dict 路径现在正确读键。"""
        assert pnl_ratio({"volume": 1000}) == 0

    def test_object_with_attr(self):
        assert pnl_ratio(SimpleNamespace(profit_loss_ratio=0.1)) == 0.1

    def test_object_missing_attr_returns_zero(self):
        """Position 模型当前无此字段 → 0(未来加字段自动生效)。"""
        assert pnl_ratio(SimpleNamespace(cost=100, price=110)) == 0

    def test_none_returns_zero(self):
        """defensive: position 查不到时不崩。"""
        assert pnl_ratio(None) == 0
