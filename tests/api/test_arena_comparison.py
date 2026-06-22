"""Arena 对比端点测试 (#5400)

验证 POST /api/v1/arena/comparison：
- requestBody schema (task_ids 必填、min_length=1)
- 净值曲线聚合（按 task_id 分组时序）
- 基础统计计算（最终值/总回报率/最大回撤）
- service 失败/无数据时跳过不崩

参考 mock 模式：tests/api/test_dashboard_aggregation.py
"""
import pytest


class TestArenaComparisonSchema:
    """Slice 1: ArenaComparisonRequest schema"""

    def test_task_ids_required(self, api_modules):
        """task_ids 必填，缺失触发 ValidationError"""
        from pydantic import ValidationError
        from api.arena import ArenaComparisonRequest

        with pytest.raises(ValidationError):
            ArenaComparisonRequest()

    def test_empty_task_ids_rejected(self, api_modules):
        """空 task_ids 列表被拒（min_length=1）"""
        from pydantic import ValidationError
        from api.arena import ArenaComparisonRequest

        with pytest.raises(ValidationError):
            ArenaComparisonRequest(task_ids=[])

    def test_valid_task_ids(self, api_modules):
        """有效 task_ids 列表构造成功"""
        from api.arena import ArenaComparisonRequest

        req = ArenaComparisonRequest(task_ids=["t1", "t2"])
        assert req.task_ids == ["t1", "t2"]


class TestComputeStatistics:
    """Slice 2: _compute_statistics 纯函数（净值序列 → 基础统计）"""

    def test_empty_curve(self, api_modules):
        """空序列返零统计"""
        from api.arena import _compute_statistics
        stats = _compute_statistics([])
        assert stats == {"final_value": 0, "total_return": 0, "max_drawdown": 0}

    def test_basic_stats_with_drawdown(self, api_modules):
        """[1.0, 1.2, 0.9] → final=0.9, return=-10%, max_dd=25%
        peak=1.2（第二点）, trough=0.9 → (1.2-0.9)/1.2 = 25%
        """
        from api.arena import _compute_statistics
        curve = [
            {"date": "d1", "value": 1.0},
            {"date": "d2", "value": 1.2},
            {"date": "d3", "value": 0.9},
        ]
        stats = _compute_statistics(curve)
        assert stats["final_value"] == 0.9
        assert stats["total_return"] == -10.0
        assert stats["max_drawdown"] == 25.0

    def test_monotonic_increase_no_drawdown(self, api_modules):
        """[1.0, 1.5, 2.0] → max_dd=0, return=100%"""
        from api.arena import _compute_statistics
        curve = [
            {"date": "d1", "value": 1.0},
            {"date": "d2", "value": 1.5},
            {"date": "d3", "value": 2.0},
        ]
        stats = _compute_statistics(curve)
        assert stats["max_drawdown"] == 0
        assert stats["total_return"] == 100.0
        assert stats["final_value"] == 2.0


class TestArenaComparisonEndpoint:
    """Slice 3: POST /comparison 端点集成（mock container）"""

    @staticmethod
    def _make_record(ts, value):
        from unittest.mock import MagicMock
        rec = MagicMock()
        rec.business_timestamp = ts
        rec.timestamp = ts
        rec.value = value
        return rec

    def test_aggregates_net_values_and_statistics(self, api_modules):
        """两 task 各返 net_value records → 聚合净值曲线（排序）+ 统计"""
        import asyncio
        from unittest.mock import patch, MagicMock
        from api.arena import ArenaComparisonRequest, get_arena_comparison

        def fake_get(task_id, analyzer_name=None, limit=None):
            if task_id == "t1":
                # 故意乱序，验证按 date 升序排序
                records = [
                    self._make_record("2025-01-03", 0.9),
                    self._make_record("2025-01-01", 1.0),
                    self._make_record("2025-01-02", 1.2),
                ]
            else:
                records = [
                    self._make_record("2025-01-01", 1.0),
                    self._make_record("2025-01-02", 2.0),
                ]
            return MagicMock(is_success=lambda: True, data=records)

        mock_service = MagicMock()
        mock_service.get_by_task_id.side_effect = fake_get
        mock_container = MagicMock()
        mock_container.analyzer_service.return_value = mock_service

        req = ArenaComparisonRequest(task_ids=["t1", "t2"])
        with patch("ginkgo.data.containers.container", mock_container):
            result = asyncio.run(get_arena_comparison(request=req))

        data = result["data"]
        # 净值曲线按 task 分组
        assert set(data["net_values"].keys()) == {"t1", "t2"}
        assert len(data["net_values"]["t1"]) == 3
        # 排序验证（乱序输入 → 升序输出）
        dates = [nv["date"] for nv in data["net_values"]["t1"]]
        assert dates == ["2025-01-01", "2025-01-02", "2025-01-03"]
        # statistics 衍生自净值序列
        stats_by_task = {s["task_id"]: s for s in data["statistics"]}
        assert stats_by_task["t1"]["final_value"] == 0.9
        assert stats_by_task["t1"]["max_drawdown"] == 25.0
        assert stats_by_task["t2"]["total_return"] == 100.0
        # service 按 net_value analyzer + 大 page_size 查询（防截断，见 arch_analyzer_read_page_size）
        mock_service.get_by_task_id.assert_any_call(
            task_id="t1", analyzer_name="net_value", limit=10000
        )

    def test_skips_task_with_no_data(self, api_modules):
        """无数据 task 跳过，不崩"""
        import asyncio
        from unittest.mock import patch, MagicMock
        from api.arena import ArenaComparisonRequest, get_arena_comparison

        mock_service = MagicMock()
        mock_service.get_by_task_id.return_value = MagicMock(
            is_success=lambda: True, data=[]
        )
        mock_container = MagicMock()
        mock_container.analyzer_service.return_value = mock_service

        req = ArenaComparisonRequest(task_ids=["empty"])
        with patch("ginkgo.data.containers.container", mock_container):
            result = asyncio.run(get_arena_comparison(request=req))

        data = result["data"]
        assert data["net_values"] == {}
        assert data["statistics"] == []

    def test_skips_task_on_service_failure(self, api_modules):
        """service 失败（is_success=False）task 跳过"""
        import asyncio
        from unittest.mock import patch, MagicMock
        from api.arena import ArenaComparisonRequest, get_arena_comparison

        mock_service = MagicMock()
        mock_service.get_by_task_id.return_value = MagicMock(
            is_success=lambda: False, data=None
        )
        mock_container = MagicMock()
        mock_container.analyzer_service.return_value = mock_service

        req = ArenaComparisonRequest(task_ids=["fail"])
        with patch("ginkgo.data.containers.container", mock_container):
            result = asyncio.run(get_arena_comparison(request=req))

        data = result["data"]
        assert data["net_values"] == {}
        assert data["statistics"] == []
