"""
Order-level Metrics TDD测试

FillRate, AvgSlippage, CancelRate 指标的单元测试套件。
"""
import pytest
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.analysis.metrics.order import FillRate, AvgSlippage, CancelRate
from ginkgo.trading.analysis.metrics.base import Metric


# ============================================================
# 测试数据
# ============================================================

def _order_df():
    """标准测试数据: 3笔订单, 2笔成交(o1,o3), 1笔撤单(o2)"""
    return pd.DataFrame({
        "order_id": ["o1", "o2", "o3"],
        "code": ["000001", "000002", "000001"],
        "direction": [1, 1, -1],
        "status": [1, 0, 1],  # filled, cancelled, filled
        "volume": [100, 200, 50],
        "limit_price": [10.0, 20.0, 10.2],
        "transaction_price": [10.1, 0.0, 10.0],
    })


# ============================================================
# FillRate 测试
# ============================================================

@pytest.mark.unit
class TestFillRate:
    """订单成交率指标测试"""

    def test_protocol_compliance(self):
        """FillRate满足Metric协议"""
        m = FillRate()
        assert isinstance(m, Metric)

    def test_name(self):
        """指标名称为fill_rate"""
        assert FillRate.name == "fill_rate"

    def test_requires_order(self):
        """依赖order数据源"""
        assert FillRate.requires == ["order"]

    def test_basic_fill_rate(self):
        """标准数据: 3笔中2笔成交, 成交率2/3"""
        m = FillRate()
        data = {"order": _order_df()}
        result = m.compute(data)
        assert result == pytest.approx(2 / 3)

    def test_all_filled(self):
        """全部成交时返回1.0"""
        df = _order_df().copy()
        df["status"] = [1, 1, 1]
        m = FillRate()
        result = m.compute({"order": df})
        assert result == 1.0

    def test_all_cancelled(self):
        """全部撤单时返回0.0"""
        df = _order_df().copy()
        df["status"] = [0, 0, 0]
        m = FillRate()
        result = m.compute({"order": df})
        assert result == 0.0

    def test_empty_dataframe(self):
        """空DataFrame返回0.0"""
        m = FillRate()
        result = m.compute({"order": pd.DataFrame()})
        assert result == 0.0


# ============================================================
# AvgSlippage 测试
# ============================================================

@pytest.mark.unit
class TestAvgSlippage:
    """平均滑点指标测试"""

    def test_protocol_compliance(self):
        """AvgSlippage满足Metric协议"""
        m = AvgSlippage()
        assert isinstance(m, Metric)

    def test_name(self):
        """指标名称为avg_slippage"""
        assert AvgSlippage.name == "avg_slippage"

    def test_requires_order(self):
        """依赖order数据源"""
        assert AvgSlippage.requires == ["order"]

    def test_basic_slippage(self):
        """标准数据: o1滑点-0.1, o3滑点0.2, 平均0.05"""
        # o1: 10.0 - 10.1 = -0.1
        # o3: 10.2 - 10.0 =  0.2
        # o2 status=0, 排除
        m = AvgSlippage()
        result = m.compute({"order": _order_df()})
        assert result == pytest.approx(0.05)

    def test_no_filled_orders(self):
        """无成交订单时返回0.0"""
        df = _order_df().copy()
        df["status"] = [0, 0, 0]
        m = AvgSlippage()
        result = m.compute({"order": df})
        assert result == 0.0

    def test_empty_dataframe(self):
        """空DataFrame返回0.0"""
        m = AvgSlippage()
        result = m.compute({"order": pd.DataFrame()})
        assert result == 0.0

    def test_zero_slippage(self):
        """成交价等于限价时滑点为0.0"""
        df = _order_df().copy()
        df["transaction_price"] = df["limit_price"]
        m = AvgSlippage()
        result = m.compute({"order": df})
        assert result == pytest.approx(0.0)


# ============================================================
# CancelRate 测试
# ============================================================

@pytest.mark.unit
class TestCancelRate:
    """撤单率指标测试"""

    def test_protocol_compliance(self):
        """CancelRate满足Metric协议"""
        m = CancelRate()
        assert isinstance(m, Metric)

    def test_name(self):
        """指标名称为cancel_rate"""
        assert CancelRate.name == "cancel_rate"

    def test_requires_order(self):
        """依赖order数据源"""
        assert CancelRate.requires == ["order"]

    def test_basic_cancel_rate(self):
        """标准数据: 3笔中1笔撤单, 撤单率1/3"""
        m = CancelRate()
        result = m.compute({"order": _order_df()})
        assert result == pytest.approx(1 / 3)

    def test_all_cancelled(self):
        """全部撤单时返回1.0"""
        df = _order_df().copy()
        df["status"] = [0, 0, 0]
        m = CancelRate()
        result = m.compute({"order": df})
        assert result == 1.0

    def test_no_cancellations(self):
        """无撤单时返回0.0"""
        df = _order_df().copy()
        df["status"] = [1, 1, 1]
        m = CancelRate()
        result = m.compute({"order": df})
        assert result == 0.0

    def test_empty_dataframe(self):
        """空DataFrame返回0.0"""
        m = CancelRate()
        result = m.compute({"order": pd.DataFrame()})
        assert result == 0.0
