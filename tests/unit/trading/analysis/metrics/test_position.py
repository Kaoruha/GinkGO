"""
持仓层级指标 TDD 测试

覆盖 MaxPositions 和 ConcentrationTopN 两个指标的完整测试套件，
使用多时间戳样本数据验证计算逻辑。
"""
import pytest
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.analysis.metrics.position import MaxPositions, ConcentrationTopN
from ginkgo.trading.analysis.metrics.base import Metric


# ============================================================
# 测试样本数据
# ============================================================

TS1 = datetime(2024, 1, 2)
TS2 = datetime(2024, 1, 3)
TS3 = datetime(2024, 1, 4)

SAMPLE_POSITION = pd.DataFrame({
    "code": [
        "000001.SZ", "000002.SZ", "600036.SH",                # TS1: 3 positions
        "000001.SZ", "000002.SZ", "600036.SH", "601318.SH",   # TS2: 4 positions (peak)
        "000001.SZ", "000002.SZ", "600036.SH",                 # TS3: 2 active + 1 closed
    ],
    "volume": [
        1000, 2000, 1500,
        1000, 2500, 1500, 800,
        1000, 0, 1500,                                         # 000002.SZ closed at TS3
    ],
    "cost": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 8.5, 10.0],
    "price": [11.0, 11.0, 11.0, 11.0, 11.0, 11.0, 11.0, 11.0, 9.0, 11.0],
    "timestamp": [
        TS1, TS1, TS1,
        TS2, TS2, TS2, TS2,
        TS3, TS3, TS3,
    ],
})


# ============================================================
# MaxPositions 测试
# ============================================================

@pytest.mark.unit
class TestMaxPositions:
    """MaxPositions 指标测试"""

    def test_protocol_satisfaction(self):
        """MaxPositions 满足 Metric Protocol"""
        m = MaxPositions()
        assert isinstance(m, Metric)

    def test_name(self):
        """name 属性正确"""
        m = MaxPositions()
        assert m.name == "max_positions"

    def test_requires(self):
        """requires 包含 position"""
        m = MaxPositions()
        assert m.requires == ["position"]

    def test_sample_data_max_is_4(self):
        """样本数据中 TS2 有 4 个非零持仓，为最大值"""
        m = MaxPositions()
        result = m.compute({"position": SAMPLE_POSITION})
        assert result == 4

    def test_counts_unique_codes(self):
        """同一 code 同一 timestamp 只计一次"""
        df = pd.DataFrame({
            "code": ["A", "A", "B"],
            "volume": [100, 200, 300],
            "cost": [1.0, 1.0, 1.0],
            "price": [1.1, 1.1, 1.1],
            "timestamp": [TS1, TS1, TS1],
        })
        m = MaxPositions()
        result = m.compute({"position": df})
        assert result == 2  # A appears twice but counted once

    def test_ignores_zero_volume(self):
        """volume=0 的持仓不计入"""
        df = pd.DataFrame({
            "code": ["A", "B", "C"],
            "volume": [100, 0, 200],
            "cost": [1.0, 1.0, 1.0],
            "price": [1.1, 1.1, 1.1],
            "timestamp": [TS1, TS1, TS1],
        })
        m = MaxPositions()
        result = m.compute({"position": df})
        assert result == 2

    def test_empty_data_returns_0(self):
        """空数据返回 0"""
        m = MaxPositions()
        result = m.compute({"position": pd.DataFrame(columns=["code", "volume", "cost", "price", "timestamp"])})
        assert result == 0

    def test_all_zero_volume_returns_0(self):
        """所有 volume 都为 0 时返回 0"""
        df = pd.DataFrame({
            "code": ["A", "B"],
            "volume": [0, 0],
            "cost": [1.0, 1.0],
            "price": [1.1, 1.1],
            "timestamp": [TS1, TS1],
        })
        m = MaxPositions()
        result = m.compute({"position": df})
        assert result == 0

    def test_across_multiple_timestamps(self):
        """跨多个时间戳取最大值"""
        df = pd.DataFrame({
            "code": ["A", "B", "C", "A"],
            "volume": [100, 200, 300, 100],
            "cost": [1.0] * 4,
            "price": [1.1] * 4,
            "timestamp": [TS1, TS1, TS2, TS3],
        })
        m = MaxPositions()
        result = m.compute({"position": df})
        # TS1: 2, TS2: 1, TS3: 1 -> max is 2
        assert result == 2


# ============================================================
# ConcentrationTopN 测试
# ============================================================

@pytest.mark.unit
class TestConcentrationTopN:
    """ConcentrationTopN 指标测试"""

    def test_protocol_satisfaction(self):
        """ConcentrationTopN 满足 Metric Protocol"""
        m = ConcentrationTopN()
        assert isinstance(m, Metric)

    def test_name(self):
        """name 属性正确"""
        m = ConcentrationTopN()
        assert m.name == "concentration_top_n"

    def test_requires(self):
        """requires 包含 position"""
        m = ConcentrationTopN()
        assert m.requires == ["position"]

    def test_default_params(self):
        """默认 n=3"""
        m = ConcentrationTopN()
        assert m.params == {"n": 3}

    def test_custom_n(self):
        """自定义 n 参数"""
        m = ConcentrationTopN(n=5)
        assert m.params == {"n": 5}

    def test_sample_data_top3(self):
        """样本数据最后一个时间戳(TS3): 000001.SZ=1000, 600036.SH=1500, 000002.SZ=0

        total_volume = 1000 + 1500 + 0 = 2500
        top 3 by volume: 600036.SH(1500) + 000001.SZ(1000) + 000002.SZ(0) = 2500
        concentration = 2500 / 2500 = 1.0
        """
        m = ConcentrationTopN(n=3)
        result = m.compute({"position": SAMPLE_POSITION})
        assert result == 1.0

    def test_top1_concentration(self):
        """n=1 时只取最大持仓占比"""
        m = ConcentrationTopN(n=1)
        # TS3: 600036.SH=1500 is max, total=2500 (1000+0+1500)
        result = m.compute({"position": SAMPLE_POSITION})
        assert result == 1500 / 2500

    def test_empty_data_returns_0(self):
        """空数据返回 0.0"""
        m = ConcentrationTopN()
        result = m.compute({"position": pd.DataFrame(columns=["code", "volume", "cost", "price", "timestamp"])})
        assert result == 0.0

    def test_all_zero_volume_returns_0(self):
        """总 volume 为 0 时返回 0.0"""
        df = pd.DataFrame({
            "code": ["A", "B"],
            "volume": [0, 0],
            "cost": [1.0, 1.0],
            "price": [1.1, 1.1],
            "timestamp": [TS3, TS3],
        })
        m = ConcentrationTopN()
        result = m.compute({"position": df})
        assert result == 0.0

    def test_uses_last_timestamp(self):
        """只使用最后一个时间戳的数据"""
        df = pd.DataFrame({
            "code": ["A", "B", "A"],
            "volume": [100, 900, 200],
            "cost": [1.0] * 3,
            "price": [1.1] * 3,
            "timestamp": [TS1, TS1, TS3],
        })
        m = ConcentrationTopN(n=1)
        # TS3 has only A with volume=200, total=200, top1=200 -> 1.0
        result = m.compute({"position": df})
        assert result == 1.0

    def test_return_type_is_float(self):
        """返回值类型为 float"""
        df = pd.DataFrame({
            "code": ["A", "B"],
            "volume": [100, 200],
            "cost": [1.0, 1.0],
            "price": [1.1, 1.1],
            "timestamp": [TS3, TS3],
        })
        m = ConcentrationTopN(n=1)
        result = m.compute({"position": df})
        assert isinstance(result, float)

    def test_equality_distribution(self):
        """均匀分布时 top_n / total = n / total_count"""
        df = pd.DataFrame({
            "code": ["A", "B", "C", "D"],
            "volume": [100, 100, 100, 100],
            "cost": [1.0] * 4,
            "price": [1.1] * 4,
            "timestamp": [TS3, TS3, TS3, TS3],
        })
        m = ConcentrationTopN(n=2)
        result = m.compute({"position": df})
        assert result == pytest.approx(0.5)
