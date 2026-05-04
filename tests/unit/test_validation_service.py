import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


def _make_net_value_records(start_date, daily_returns, portfolio_id="pf-001", task_id="task-001"):
    """辅助函数：构造 net_value 模拟记录列表"""
    records = []
    value = 1.0
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    for r in daily_returns:
        value *= (1 + r)
        rec = MagicMock()
        rec.value = value
        rec.business_timestamp = dt
        rec.portfolio_id = portfolio_id
        rec.task_id = task_id
        rec.name = "net_value"
        records.append(rec)
        dt += timedelta(days=1)
    return records


class TestSegmentStability:
    def test_split_into_equal_segments(self):
        """242 个交易日分成 4 段，每段应约 60~61 天"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        returns = np.array([0.01] * 242)
        segments = svc._split_returns(returns, 4)
        assert len(segments) == 4
        # 每段长度之和等于总长度
        assert sum(len(s) for s in segments) == 242

    def test_stability_score_high_when_consistent(self):
        """各段收益一致时，稳定性评分应接近 1"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        # 每段收益都是 +1%
        segment_returns = [0.01, 0.01, 0.01, 0.01]
        score = svc._calc_stability_score(segment_returns)
        assert score > 0.99

    def test_stability_score_low_when_inconsistent(self):
        """各段收益差异大时，稳定性评分应较低"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        segment_returns = [0.08, 0.02, -0.03, 0.01]
        score = svc._calc_stability_score(segment_returns)
        assert score < 0.6

    def test_stability_score_zero_when_near_zero_returns(self):
        """平均绝对收益 < 0.001 时返回 0"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        segment_returns = [0.0001, -0.0001, 0.0002, -0.0001]
        score = svc._calc_stability_score(segment_returns)
        assert score == 0

    def test_segment_metrics(self):
        """计算单段的收益、夏普、最大回撤"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        # 5天，每天 +1%
        daily_returns = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
        metrics = svc._calc_segment_metrics(daily_returns)
        assert metrics["total_return"] > 0.04  # ~5.1%
        assert metrics["sharpe"] is not None
        assert metrics["max_drawdown"] >= 0  # 回撤是正值表示亏损幅度
        assert metrics["win_rate"] == 1.0  # 全部正收益

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_segment_stability_multi_window(self, mock_get_records):
        """多窗口分段稳定性端到端测试"""
        from ginkgo.data.services.validation_service import ValidationService
        # 构造 120 天净值为缓慢上涨的数据
        daily_returns = [0.002] * 120
        records = _make_net_value_records("2024-01-02", daily_returns, task_id="test-task")
        mock_get_records.return_value = records

        svc = ValidationService.__new__(ValidationService)
        result = svc.segment_stability(task_id="test-task", portfolio_id="pf-001", n_segments_list=[2, 4])

        assert result.is_success()
        data = result.data
        assert len(data["windows"]) == 2
        assert data["windows"][0]["n_segments"] == 2
        assert data["windows"][1]["n_segments"] == 4
        # 一致上涨的数据稳定性应较高
        for w in data["windows"]:
            assert w["stability_score"] > 0.5


class TestMonteCarlo:
    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_monte_carlo_basic(self, mock_get_records):
        """蒙特卡洛模拟基本流程"""
        from ginkgo.data.services.validation_service import ValidationService
        daily_returns = [0.005] * 50 + [-0.003] * 50
        records = _make_net_value_records("2024-01-02", daily_returns, task_id="test-task")
        mock_get_records.return_value = records

        svc = ValidationService.__new__(ValidationService)
        result = svc.monte_carlo(
            task_id="test-task",
            portfolio_id="pf-001",
            n_simulations=1000,
            confidence=0.95,
        )

        assert result.is_success()
        data = result.data
        assert "var" in data
        assert "cvar" in data
        assert "actual_return" in data
        assert "percentile" in data
        assert "loss_probability" in data
        assert 0 <= data["percentile"] <= 100
        assert data["loss_probability"] >= 0

    def test_monte_carlo_var_cvar(self):
        """VaR 应小于 CVaR（绝对值）"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        np.random.seed(42)
        simulated_returns = np.random.normal(0.001, 0.02, 10000)
        actual_return = 0.05
        result = svc._calc_monte_carlo_stats(simulated_returns, actual_return, 0.95)
        assert result["cvar"] <= result["var"]
