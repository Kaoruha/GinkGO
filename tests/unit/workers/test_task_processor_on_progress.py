"""#5479: BacktestProcessor._on_progress 统计聚合失败时记录日志，不静默 pass。"""
from unittest.mock import MagicMock, PropertyMock, patch


def test_on_progress_logs_on_stats_failure():
    """统计聚合异常 → GLOG.ERROR 被调用（非静默 pass），主流程仍上报进度。"""
    from ginkgo.workers.backtest_worker import task_processor as tp_mod
    from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor

    task = MagicMock()
    task.task_uuid = "abc12345xxxx"
    task.portfolio_uuid = "p-1"
    task.config.initial_cash = 100000.0
    progress_tracker = MagicMock()

    # __new__ 跳过 __init__ 的服务实例化；_on_progress 只用 task/_engine/progress_tracker/_stop_event
    proc = BacktestProcessor.__new__(BacktestProcessor)
    proc.task = task
    proc.progress_tracker = progress_tracker
    proc._stop_event = MagicMock()
    proc._stop_event.is_set.return_value = False

    # portfolio.worth 访问抛 → 统计块 except
    bad_portfolio = MagicMock()
    bad_portfolio.uuid = "p-1"
    type(bad_portfolio).worth = PropertyMock(side_effect=RuntimeError("stats boom"))
    proc._engine = MagicMock()
    proc._engine.portfolios = [bad_portfolio]

    with patch.object(tp_mod, "GLOG") as m_glog:
        proc._on_progress(0.5, "2026-01-01")  # 不应抛（主流程继续）

    assert m_glog.ERROR.called, "统计失败应记 GLOG.ERROR 而非静默 pass"
    assert progress_tracker.report_progress.called, "主流程上报不应中断"
