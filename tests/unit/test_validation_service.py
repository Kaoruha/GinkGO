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

        # fix(#5756): 用真 __init__ 构造；analyzer_crud 的全量查询(L257)也返回同一批记录；
        # records 全是 net_value，故 metrics 取 ["net_value"] 使数据自洽
        mock_crud = MagicMock()
        mock_crud.get_by_task_id.return_value = records
        svc = ValidationService(analyzer_record_crud=mock_crud, validation_result_crud=None)
        result = svc.segment_stability(
            task_id="test-task", portfolio_id="pf-001",
            n_segments_list=[2, 4], metrics=["net_value"],
        )

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

        # fix(#5756): 用真 __init__ 构造，_result_crud=None 跳过持久化分支
        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
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

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_monte_carlo_flat_equity_returns_error(self, mock_get_records):
        """fix(#5756): 净值无波动（收益率恒定）时，应返回明确错误，而非全零伪结果"""
        from ginkgo.data.services.validation_service import ValidationService
        # 恒定净值（如无交易回测）→ 收益率全零
        records = _make_net_value_records("2024-01-02", [0.0] * 100, task_id="test-task")
        mock_get_records.return_value = records

        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.monte_carlo(
            task_id="test-task",
            portfolio_id="pf-001",
            n_simulations=1000,
            confidence=0.95,
        )

        # 关键：不能返回"成功 + 全零"——那是误导用户的风险体检结果
        assert not result.is_success()
        assert result.error  # 必须有明确错误信息

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_monte_carlo_volatile_produces_meaningful_distribution(self, mock_get_records):
        """fix(#5756): 波动净值必须产出非零 VaR/CVaR 且分布跨多 bin（非全零/单 bin 退化）"""
        from ginkgo.data.services.validation_service import ValidationService
        np.random.seed(42)  # 稳定 bootstrap 抽样，保证断言可复现
        daily_returns = [0.005] * 50 + [-0.003] * 50
        records = _make_net_value_records("2024-01-02", daily_returns, task_id="test-task")
        mock_get_records.return_value = records

        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.monte_carlo(
            task_id="test-task",
            portfolio_id="pf-001",
            n_simulations=1000,
            confidence=0.95,
        )

        assert result.is_success()
        data = result.data
        # 波动数据 → VaR/CVaR 必须非零（全零即 #5756 退化）；CVaR ≤ VaR 恒成立
        assert data["var"] != 0
        assert data["cvar"] <= data["var"]
        # 1000 次模拟应分散到多个 bin，不能塌成单 bin（=模拟全相同）
        counts = data["distribution"]["counts"]
        assert sum(1 for c in counts if c > 0) > 1

    def test_monte_carlo_var_cvar(self):
        """VaR 应小于 CVaR（绝对值）"""
        from ginkgo.data.services.validation_service import ValidationService
        svc = ValidationService.__new__(ValidationService)
        np.random.seed(42)
        simulated_returns = np.random.normal(0.001, 0.02, 10000)
        actual_return = 0.05
        result = svc._calc_monte_carlo_stats(simulated_returns, actual_return, 0.95)
        assert result["cvar"] <= result["var"]


class TestWalkForward:
    """#5867: walk_forward 走步验证——基于已有 net_value 切 train/test 窗口算绩效"""

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_walk_forward_insufficient_data(self, mock_get_records):
        from ginkgo.data.services.validation_service import ValidationService
        mock_get_records.return_value = []
        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.walk_forward(task_id="t", portfolio_id="p")
        assert not result.is_success()
        assert "数据不足" in result.error

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_walk_forward_basic(self, mock_get_records):
        from ginkgo.data.services.validation_service import ValidationService
        # 120 天稳定正收益
        daily_returns = [0.001] * 120
        records = _make_net_value_records("2024-01-02", daily_returns, task_id="test-task")
        mock_get_records.return_value = records
        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.walk_forward(task_id="test-task", portfolio_id="pf-001", n_folds=3, train_ratio=0.7)
        assert result.is_success(), result.error
        data = result.data
        assert data["n_folds"] == 3
        assert len(data["folds"]) == 3
        fold = data["folds"][0]
        # 每折含 train/test 日期窗口 + 绩效
        assert "train_start" in fold and "test_end" in fold
        assert "train_return" in fold and "test_return" in fold
        # 汇总指标
        assert "avg_train_return" in data and "avg_test_return" in data
        assert "overfit_score" in data


class TestSensitivity:
    """#5867: sensitivity 敏感性分析——策略绩效对回测分段数（n_segments）的稳健性。
    真参数扫描需重跑回测（超范围），此处为基于已有 net_value 的统计敏感性：不同分段粒度下绩效的离散度。"""

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_sensitivity_unsupported_param_name(self, mock_get_records):
        from ginkgo.data.services.validation_service import ValidationService
        records = _make_net_value_records("2024-01-02", [0.001] * 100, task_id="t")
        mock_get_records.return_value = records
        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.sensitivity(task_id="t", portfolio_id="p", param_name="unknown_param", param_values=[2, 4])
        assert not result.is_success()
        assert "param_name" in result.error or "不支持" in result.error

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_sensitivity_n_segments(self, mock_get_records):
        from ginkgo.data.services.validation_service import ValidationService
        records = _make_net_value_records("2024-01-02", [0.001] * 200, task_id="t")
        mock_get_records.return_value = records
        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.sensitivity(task_id="t", portfolio_id="p", param_name="n_segments", param_values=[2, 4, 8])
        assert result.is_success(), result.error
        data = result.data
        assert data["param_name"] == "n_segments"
        assert len(data["records"]) == 3
        rec = data["records"][0]
        assert rec["param_value"] == 2
        assert "total_return" in rec and "sharpe" in rec and "max_drawdown" in rec
        assert "sensitivity_score" in data

    @patch("ginkgo.data.services.validation_service.ValidationService._get_net_value_records")
    def test_sensitivity_accepts_csv_string(self, mock_get_records):
        from ginkgo.data.services.validation_service import ValidationService
        # 前端 paramValues 是逗号分隔字符串，service 应兼容
        records = _make_net_value_records("2024-01-02", [0.001] * 200, task_id="t")
        mock_get_records.return_value = records
        svc = ValidationService(analyzer_record_crud=MagicMock(), validation_result_crud=None)
        result = svc.sensitivity(task_id="t", portfolio_id="p", param_name="n_segments", param_values="2,4,8")
        assert result.is_success(), result.error
        assert len(result.data["records"]) == 3
