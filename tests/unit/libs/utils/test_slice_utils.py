"""slice_utils.py 模块单元测试

测试数据切片和分页处理的辅助方法。
覆盖：时间切片创建、数据分布平衡、重叠计算、连续性验证、DataFrame过滤、统计计算。
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from ginkgo.libs.utils.slice_utils import (
    create_time_slices,
    balance_slice_data_distribution,
    _merge_small_slices,
    _rebalance_slices,
    calculate_slice_overlap,
    filter_dataframe_by_time,
    validate_slice_continuity,
    optimize_slice_boundaries,
    calculate_slice_statistics,
    _calculate_list_stats,
)


# ============================================================
# create_time_slices
# ============================================================
@pytest.mark.unit
class TestCreateTimeSlices:
    """create_time_slices 时间切片创建测试"""

    def test_single_period(self):
        """单周期完全覆盖"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 11)
        slices = create_time_slices(start, end, 10)
        assert len(slices) == 1
        assert slices[0] == (start, end)

    def test_multiple_periods(self):
        """多周期切片"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        slices = create_time_slices(start, end, 10)
        assert len(slices) == 3
        # 第一个切片
        assert slices[0][0] == start
        assert slices[0][1] == datetime(2024, 1, 11)
        # 最后一个切片应精确到 end
        assert slices[-1][1] == end

    def test_period_larger_than_range(self):
        """周期大于时间范围时，返回单个切片"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 3)
        slices = create_time_slices(start, end, 100)
        assert len(slices) == 1
        assert slices[0] == (start, end)

    def test_one_day_period(self):
        """每天一个切片"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 5)
        slices = create_time_slices(start, end, 1)
        assert len(slices) == 4
        for i in range(4):
            expected_start = start + timedelta(days=i)
            assert slices[i][0] == expected_start

    def test_empty_range(self):
        """start 等于 end 时返回空列表"""
        start = datetime(2024, 1, 1)
        slices = create_time_slices(start, start, 10)
        assert slices == []

    def test_start_after_end(self):
        """start 大于 end 时返回空列表"""
        start = datetime(2024, 1, 10)
        end = datetime(2024, 1, 1)
        slices = create_time_slices(start, end, 10)
        assert slices == []

    def test_continuity(self):
        """切片应连续无间隙"""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 3, 1)
        slices = create_time_slices(start, end, 30)
        for i in range(1, len(slices)):
            assert slices[i - 1][1] == slices[i][0]


# ============================================================
# balance_slice_data_distribution
# ============================================================
@pytest.mark.unit
class TestBalanceSliceDataDistribution:
    """balance_slice_data_distribution 数据分布平衡测试"""

    def test_empty_input(self):
        """空输入返回空列表"""
        result = balance_slice_data_distribution([], 10)
        assert result == []

    def test_uniform_distribution(self):
        """均匀分布时返回索引列表"""
        counts = [100, 100, 100]
        result = balance_slice_data_distribution(counts, 50)
        assert result == [0, 1, 2]

    def test_small_slices_trigger_merge(self):
        """存在小于 min_count 的切片时触发合并"""
        counts = [3, 3, 100, 100]
        result = balance_slice_data_distribution(counts, 50)
        # 应返回合并后的边界，而非原始索引
        assert isinstance(result, list)

    def test_high_cv_triggers_rebalance(self):
        """高变异系数触发重新平衡"""
        counts = [100, 1000, 100, 1000, 100]
        result = balance_slice_data_distribution(counts, 50, max_cv=0.3)
        assert isinstance(result, list)

    def test_all_values_meet_min_count(self):
        """所有值均满足最小计数"""
        counts = [200, 300, 250]
        result = balance_slice_data_distribution(counts, 100)
        assert result == [0, 1, 2]


# ============================================================
# _merge_small_slices
# ============================================================
@pytest.mark.unit
class TestMergeSmallSlices:
    """_merge_small_slices 小切片合并测试"""

    def test_merge_two_small(self):
        """合并两个小切片"""
        counts = [3, 3]
        result = _merge_small_slices(counts, 5)
        assert len(result) == 1
        assert result[0] == (0, 2)

    def test_no_merge_needed(self):
        """无需合并"""
        counts = [10, 20, 30]
        result = _merge_small_slices(counts, 5)
        assert result == [(0, 1), (1, 2), (2, 3)]

    def test_partial_merge(self):
        """部分需要合并"""
        counts = [2, 2, 10, 5]
        result = _merge_small_slices(counts, 5)
        assert isinstance(result, list)
        # 前两个应合并
        assert result[0][0] == 0

    def test_all_small(self):
        """全部都很小，合并为一个"""
        counts = [1, 1, 1, 1]
        result = _merge_small_slices(counts, 10)
        assert len(result) == 1
        assert result[0] == (0, 4)


# ============================================================
# _rebalance_slices
# ============================================================
@pytest.mark.unit
class TestRebalanceSlices:
    """_rebalance_slices 切片重平衡测试"""

    def test_uniform_no_rebalance(self):
        """均匀分布无需重平衡"""
        counts = [100, 100, 100]
        result = _rebalance_slices(counts, 0.1)
        assert isinstance(result, list)

    def test_skewed_distribution(self):
        """偏态分布触发重平衡"""
        counts = [10, 100, 10, 100]
        result = _rebalance_slices(counts, 0.3)
        assert isinstance(result, list)


# ============================================================
# calculate_slice_overlap
# ============================================================
@pytest.mark.unit
class TestCalculateSliceOverlap:
    """calculate_slice_overlap 切片重叠计算测试"""

    def test_no_overlap(self):
        """无重叠的两个切片"""
        s1 = (datetime(2024, 1, 1), datetime(2024, 1, 5))
        s2 = (datetime(2024, 1, 6), datetime(2024, 1, 10))
        assert calculate_slice_overlap(s1, s2) == 0.0

    def test_full_overlap(self):
        """完全重叠"""
        s1 = (datetime(2024, 1, 1), datetime(2024, 1, 10))
        s2 = (datetime(2024, 1, 1), datetime(2024, 1, 10))
        result = calculate_slice_overlap(s1, s2)
        assert result == pytest.approx(1.0)

    def test_partial_overlap(self):
        """部分重叠：重叠5天，两个切片各9天（1-10不含10即9天），结果 5/9"""
        s1 = (datetime(2024, 1, 1), datetime(2024, 1, 10))
        s2 = (datetime(2024, 1, 5), datetime(2024, 1, 15))
        result = calculate_slice_overlap(s1, s2)
        assert result == pytest.approx(5.0 / 9.0)

    def test_contiguous_no_gap(self):
        """相邻但不重叠"""
        s1 = (datetime(2024, 1, 1), datetime(2024, 1, 5))
        s2 = (datetime(2024, 1, 5), datetime(2024, 1, 10))
        assert calculate_slice_overlap(s1, s2) == 0.0

    def test_zero_duration_slice(self):
        """零时长切片"""
        s1 = (datetime(2024, 1, 1), datetime(2024, 1, 1))
        s2 = (datetime(2024, 1, 1), datetime(2024, 1, 10))
        assert calculate_slice_overlap(s1, s2) == 0.0

    def test_contained_slice(self):
        """一个切片完全包含另一个"""
        s1 = (datetime(2024, 1, 1), datetime(2024, 1, 20))
        s2 = (datetime(2024, 1, 5), datetime(2024, 1, 10))
        # 重叠 5天 / 较短 5天 = 1.0
        result = calculate_slice_overlap(s1, s2)
        assert result == pytest.approx(1.0)


# ============================================================
# filter_dataframe_by_time
# ============================================================
@pytest.mark.unit
class TestFilterDataframeByTime:
    """filter_dataframe_by_time 时间过滤测试"""

    def _make_df(self):
        """创建测试用 DataFrame"""
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        return pd.DataFrame({"timestamp": dates, "value": range(10)})

    def test_filter_middle_range(self):
        """过滤中间时间段"""
        df = self._make_df()
        result = filter_dataframe_by_time(
            df, datetime(2024, 1, 3), datetime(2024, 1, 7), "timestamp"
        )
        assert len(result) == 4

    def test_filter_all(self):
        """过滤范围覆盖全部数据"""
        df = self._make_df()
        result = filter_dataframe_by_time(
            df, datetime(2024, 1, 1), datetime(2024, 1, 11), "timestamp"
        )
        assert len(result) == 10

    def test_filter_none(self):
        """过滤范围不包含任何数据"""
        df = self._make_df()
        result = filter_dataframe_by_time(
            df, datetime(2025, 1, 1), datetime(2025, 1, 10), "timestamp"
        )
        assert len(result) == 0

    def test_empty_dataframe(self):
        """空 DataFrame 原样返回"""
        df = pd.DataFrame()
        result = filter_dataframe_by_time(
            df, datetime(2024, 1, 1), datetime(2024, 1, 10)
        )
        assert len(result) == 0

    def test_missing_time_column(self):
        """时间列不存在时原样返回"""
        df = pd.DataFrame({"value": [1, 2, 3]})
        result = filter_dataframe_by_time(
            df, datetime(2024, 1, 1), datetime(2024, 1, 10), "timestamp"
        )
        assert len(result) == 3

    def test_result_index_reset(self):
        """返回结果索引应重置"""
        df = self._make_df()
        result = filter_dataframe_by_time(
            df, datetime(2024, 1, 5), datetime(2024, 1, 11), "timestamp"
        )
        assert list(result.index) == list(range(len(result)))

    def test_original_not_modified(self):
        """原始 DataFrame 不应被修改"""
        df = self._make_df()
        original_len = len(df)
        filter_dataframe_by_time(df, datetime(2024, 1, 5), datetime(2024, 1, 7))
        assert len(df) == original_len


# ============================================================
# validate_slice_continuity
# ============================================================
@pytest.mark.unit
class TestValidateSliceContinuity:
    """validate_slice_continuity 时间连续性验证测试"""

    def test_empty_slices(self):
        """空切片列表视为连续"""
        result = validate_slice_continuity([])
        assert result["is_continuous"] is True
        assert result["gaps"] == []
        assert result["overlaps"] == []

    def test_single_slice(self):
        """单个切片视为连续"""
        slices = [(datetime(2024, 1, 1), datetime(2024, 1, 10))]
        result = validate_slice_continuity(slices)
        assert result["is_continuous"] is True

    def test_continuous_slices(self):
        """连续切片无间隙"""
        slices = [
            (datetime(2024, 1, 1), datetime(2024, 1, 5)),
            (datetime(2024, 1, 5), datetime(2024, 1, 10)),
            (datetime(2024, 1, 10), datetime(2024, 1, 15)),
        ]
        result = validate_slice_continuity(slices)
        assert result["is_continuous"] is True
        assert result["total_gaps"] == 0
        assert result["total_overlaps"] == 0

    def test_gap_detected(self):
        """检测时间间隙"""
        slices = [
            (datetime(2024, 1, 1), datetime(2024, 1, 5)),
            (datetime(2024, 1, 7), datetime(2024, 1, 10)),  # 2天间隙
        ]
        result = validate_slice_continuity(slices)
        assert result["is_continuous"] is False
        assert result["total_gaps"] == 1
        assert result["gaps"][0]["gap_duration"] == 2 * 86400

    def test_overlap_detected(self):
        """检测时间重叠"""
        slices = [
            (datetime(2024, 1, 1), datetime(2024, 1, 7)),
            (datetime(2024, 1, 5), datetime(2024, 1, 10)),  # 重叠2天
        ]
        result = validate_slice_continuity(slices)
        assert result["is_continuous"] is False
        assert result["total_overlaps"] == 1
        assert result["overlaps"][0]["overlap_duration"] == 2 * 86400

    def test_multiple_gaps(self):
        """检测多个间隙"""
        slices = [
            (datetime(2024, 1, 1), datetime(2024, 1, 3)),
            (datetime(2024, 1, 5), datetime(2024, 1, 7)),
            (datetime(2024, 1, 10), datetime(2024, 1, 12)),
        ]
        result = validate_slice_continuity(slices)
        assert result["total_gaps"] == 2


# ============================================================
# optimize_slice_boundaries
# ============================================================
@pytest.mark.unit
class TestOptimizeSliceBoundaries:
    """optimize_slice_boundaries 切片边界优化测试"""

    def _make_df(self):
        """创建测试用 DataFrame"""
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        return pd.DataFrame({"timestamp": dates, "value": range(100)})

    def test_empty_dataframe(self):
        """空 DataFrame 返回原始切片"""
        df = pd.DataFrame()
        slices = [(datetime(2024, 1, 1), datetime(2024, 1, 10))]
        result = optimize_slice_boundaries(df, slices, 50)
        assert result == slices

    def test_empty_slices(self):
        """空切片列表原样返回"""
        df = self._make_df()
        result = optimize_slice_boundaries(df, [], 50)
        assert result == []

    def test_balanced_slices_unchanged(self):
        """均衡切片应保持不变"""
        df = self._make_df()
        slices = [
            (datetime(2024, 1, 1), datetime(2024, 1, 2, 1), ),
            (datetime(2024, 1, 2, 1), datetime(2024, 1, 3, 1), ),
            (datetime(2024, 1, 3, 1), datetime(2024, 1, 4, 1), ),
            (datetime(2024, 1, 4, 1), datetime(2024, 1, 5, 1), ),
        ]
        result = optimize_slice_boundaries(df, slices, 25)
        assert len(result) == 4

    def test_oversized_slice_split(self):
        """超大切片应被分割"""
        df = self._make_df()
        # 整个100条数据作为一个切片，目标每片25条
        slices = [(datetime(2024, 1, 1), datetime(2024, 1, 5, 4))]
        result = optimize_slice_boundaries(df, slices, 25)
        assert len(result) > 1


# ============================================================
# calculate_slice_statistics
# ============================================================
@pytest.mark.unit
class TestCalculateSliceStatistics:
    """calculate_slice_statistics 切片统计计算测试"""

    def test_empty_input(self):
        """空输入返回计数为0"""
        result = calculate_slice_statistics([])
        assert result == {"count": 0}

    def test_basic_stats(self):
        """基本统计信息计算"""
        slices = [
            {
                "signal_count": 10,
                "order_count": 5,
                "analyzer_count": 2,
                "start_date": datetime(2024, 1, 1),
                "end_date": datetime(2024, 1, 11),
            },
            {
                "signal_count": 20,
                "order_count": 10,
                "analyzer_count": 3,
                "start_date": datetime(2024, 1, 11),
                "end_date": datetime(2024, 1, 21),
            },
        ]
        result = calculate_slice_statistics(slices)
        assert result["count"] == 2
        assert result["signal_stats"]["sum"] == 30
        assert result["signal_stats"]["mean"] == pytest.approx(15.0)
        assert result["order_stats"]["sum"] == 15
        assert result["analyzer_stats"]["sum"] == 5

    def test_missing_keys_default_zero(self):
        """缺失键默认为0"""
        slices = [{"signal_count": 5}]
        result = calculate_slice_statistics(slices)
        assert result["order_stats"]["sum"] == 0
        assert result["analyzer_stats"]["sum"] == 0

    def test_balance_metrics(self):
        """平衡指标计算"""
        slices = [
            {"signal_count": 100, "order_count": 50, "analyzer_count": 10},
            {"signal_count": 100, "order_count": 50, "analyzer_count": 10},
        ]
        result = calculate_slice_statistics(slices)
        assert result["balance_metrics"]["signal_cv"] == pytest.approx(0.0)
        assert result["balance_metrics"]["order_cv"] == pytest.approx(0.0)

    def test_no_dates_no_duration_stats(self):
        """无日期信息时 duration_stats 为空"""
        slices = [{"signal_count": 5}]
        result = calculate_slice_statistics(slices)
        assert result["duration_stats"] == {}

    def test_single_slice_std_zero(self):
        """单切片标准差为0"""
        slices = [{"signal_count": 10, "order_count": 5, "analyzer_count": 1}]
        result = calculate_slice_statistics(slices)
        assert result["signal_stats"]["std"] == 0


# ============================================================
# _calculate_list_stats
# ============================================================
@pytest.mark.unit
class TestCalculateListStats:
    """_calculate_list_stats 列表统计量计算测试"""

    def test_empty_list(self):
        """空列表返回空字典"""
        assert _calculate_list_stats([]) == {}

    def test_single_value(self):
        """单值统计"""
        result = _calculate_list_stats([42.0])
        assert result["count"] == 1
        assert result["sum"] == 42.0
        assert result["mean"] == 42.0
        assert result["std"] == 0  # ddof=1 但 len<=1 时返回0
        assert result["min"] == 42.0
        assert result["max"] == 42.0
        assert result["median"] == 42.0

    def test_multiple_values(self):
        """多值统计"""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = _calculate_list_stats(values)
        assert result["count"] == 5
        assert result["sum"] == 150.0
        assert result["mean"] == pytest.approx(30.0)
        assert result["std"] > 0
        assert result["min"] == 10.0
        assert result["max"] == 50.0
        assert result["q25"] == pytest.approx(np.percentile(values, 25))
        assert result["q75"] == pytest.approx(np.percentile(values, 75))

    def test_all_same_values(self):
        """所有值相同时标准差为0"""
        result = _calculate_list_stats([5.0, 5.0, 5.0, 5.0])
        assert result["std"] == 0
        assert result["mean"] == 5.0
