"""#5646: 空 portfolio 关联的回测启动应返回明确错误，而非派发无效任务
让 worker 报误导性的 'portfolio_uuid is required'。

根因: start_task 派发 Kafka 前不校验 portfolio_uuid 解析结果。
assignment["portfolio_uuid"] = portfolio_uuid or task.portfolio_id，
task.portfolio_id（model 默认空串）为空时仍派发，worker node.py:290
消费时报 'portfolio_uuid is required'，让用户以为 UUID 没传——
实际是 backtest task 记录的 portfolio 关联为空。

修复: 派发前（状态机检查后、清理旧数据前）校验
resolved = portfolio_uuid or task.portfolio_id，空则返回明确 error，
不派发、不误导。
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService

_TASK_UUID = "aa11223344556677889900aabbccddee"


def _make_task(portfolio_id: str = "", status: str = "created"):
    """模拟一条 backtest task 记录（含 start_task 读取的属性）。"""
    task = MagicMock()
    task.uuid = _TASK_UUID
    task.task_id = _TASK_UUID
    task.status = status
    task.portfolio_id = portfolio_id
    task.config_snapshot = json.dumps(
        {"start_date": "2025-01-01", "end_date": "2025-06-01"}
    )
    task.backtest_start_date = None
    task.backtest_end_date = None
    task.name = "bt"
    return task


class TestStartTaskEmptyPortfolio:
    """#5646: portfolio 关联为空时 start_task 返回明确不误导的错误。"""

    @pytest.mark.unit
    def test_empty_portfolio_returns_clear_error_and_does_not_dispatch(self):
        """portfolio_id 空 + 未传 portfolio_uuid → 明确 error + 不派发 Kafka。"""
        crud = MagicMock()
        crud.get_by_uuid.return_value = _make_task(portfolio_id="")
        svc = BacktestTaskService(crud)

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer") as producer_cls:
            result = svc.start_task(uuid=_TASK_UUID)

        # 明确失败
        assert not result.is_success(), "空 portfolio 关联应返回失败，而非派发无效任务"
        # 不误导：不得复用 worker 的字面报错
        assert "portfolio_uuid is required" not in result.error
        # 点明 portfolio 关联问题
        assert "portfolio" in result.error.lower()
        # 不派发 Kafka（不产生 worker 会误报的无效任务）
        producer_cls.assert_not_called()

    @pytest.mark.unit
    def test_valid_portfolio_dispatches_with_portfolio_uuid(self):
        """回归保护：portfolio_id 非空 → 正常派发，assignment 含非空 portfolio_uuid。"""
        port_uuid = "port11223344556677889900aabbccdd"
        crud = MagicMock()
        crud.get_by_uuid.return_value = _make_task(portfolio_id=port_uuid)
        svc = BacktestTaskService(crud)

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer") as producer_cls:
            result = svc.start_task(uuid=_TASK_UUID)

        assert result.is_success(), "有效 portfolio 关联应正常启动，不受校验影响"
        producer_instance = producer_cls.return_value
        producer_instance.send.assert_called_once()
        _topic, sent_assignment = producer_instance.send.call_args.args
        assert sent_assignment["portfolio_uuid"] == port_uuid

    @pytest.mark.unit
    def test_explicit_portfolio_uuid_arg_overrides_empty_task_field(self):
        """显式传 portfolio_uuid 参数时，即使 task.portfolio_id 空也正常派发
        （校验的 or 语义：portfolio_uuid 参数优先）。"""
        crud = MagicMock()
        crud.get_by_uuid.return_value = _make_task(portfolio_id="")
        svc = BacktestTaskService(crud)

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer") as producer_cls:
            result = svc.start_task(uuid=_TASK_UUID, portfolio_uuid="explicit-port-uuid")

        assert result.is_success(), "显式传 portfolio_uuid 时应正常派发"
        _topic, sent_assignment = producer_cls.return_value.send.call_args.args
        assert sent_assignment["portfolio_uuid"] == "explicit-port-uuid"
