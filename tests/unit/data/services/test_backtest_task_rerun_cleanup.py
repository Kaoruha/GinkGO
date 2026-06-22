"""
BacktestTaskService.start_task 重跑清理循环契约测试

覆盖 backtest_task_service.py:609-627 的重跑旧数据清理逻辑（DI 改造后由容器注入 9 个 CRUD）：
- 注入的 9 个 CRUD 全部以 filters={"task_id": ...} 调用 remove
- CRUD 为 None（容器未注入）时 WARN 告警（非静默跳过），其余仍清理
- 单个 CRUD.remove 抛异常时不中断后续清理（容错，逐表 try-except）
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


# 9 个清理 CRUD 的 kwargs 名（与 __init__ 签名 / 清理循环 _cleanup_cruds 一一对应）
_CLEANUP_KWARGS = [
    "signal_crud", "order_crud", "position_crud", "position_record_crud",
    "analyzer_record_crud", "order_record_crud", "transfer_record_crud",
    "transfer_crud", "signal_tracker_crud",
]


def _make_task(**overrides):
    """构建可重跑状态的 mock task（status=completed 在 startable_states 内）"""
    task = MagicMock()
    task.uuid = "uuid-1234"
    task.task_id = "task-abc-001"
    task.portfolio_id = "portfolio-001"
    task.name = "rerun_cleanup_test"
    task.backtest_start_date = None
    task.backtest_end_date = None
    task.status = "completed"
    task.config_snapshot = json.dumps({
        "start_date": "2025-06-01",
        "end_date": "2026-06-01",
        "initial_cash": 100000.0,
    })
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@contextmanager
def _mock_kafka_and_container():
    """mock Kafka producer 与 container，隔离清理循环之后的发送流程"""
    mock_producer = MagicMock()
    with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer), \
         patch("ginkgo.data.containers.container", MagicMock()):
        yield mock_producer


def _make_service_with_cruds(crud_overrides=None):
    """
    构造注入 9 个 mock CRUD 的 service。

    crud_overrides: {kwarg_name: value}，可传 None 模拟「容器未注入」。
    返回 (svc, cruds)，cruds 为 kwargs_name → mock/None 映射，便于断言。
    """
    task = _make_task()
    crud_repo = MagicMock()
    crud_repo.get_by_uuid.return_value = task
    crud_repo.find.return_value = []

    kwargs = {"crud_repo": crud_repo}
    cruds = {}
    for name in _CLEANUP_KWARGS:
        val = (crud_overrides or {}).get(name, MagicMock())
        kwargs[name] = val
        cruds[name] = val

    svc = BacktestTaskService(**kwargs)
    svc.update_status = MagicMock(return_value=ServiceResult.success(task, "ok"))
    return svc, cruds


class TestRerunCleanupLoop:
    """start_task 重跑清理 9 张关联表（DI: CRUD 由容器注入）"""

    @pytest.mark.unit
    def test_all_nine_cruds_remove_called_with_task_id(self):
        """重跑时 9 个注入 CRUD 全部以 filters={"task_id": task_id} 调用 remove

        MySQL 4 个额外传 session（共享单事务，#5562）；CH 5 个无 session（CH 无事务）。
        filters 契约对 9 个一致，session 按库归属区分。
        """
        svc, cruds = _make_service_with_cruds()
        # MySQL 组走 driver.get_session() 事务，需装上 contextmanager 否则 with MagicMock() 失败
        TestRerunCleanupAtomicity._wire_mysql_transaction(cruds)
        task = svc._crud_repo.get_by_uuid.return_value

        with _mock_kafka_and_container():
            svc.start_task(uuid="uuid-1234")

        mysql_names = TestRerunCleanupAtomicity.MYSQL_CRUD_NAMES
        click_names = TestRerunCleanupAtomicity.CLICK_CRUD_NAMES
        for name in mysql_names + click_names:
            crud = cruds[name]
            assert crud.remove.called, f"{name} 未被清理"
            _, kwargs = crud.remove.call_args
            assert kwargs.get("filters") == {"task_id": task.task_id}, \
                f"{name} filters 契约破裂"
            if name in mysql_names:
                assert "session" in kwargs, f"{name} (MySQL) 应传入共享 session"
            else:
                assert "session" not in kwargs or kwargs["session"] is None, \
                    f"{name} (ClickHouse) 不应参与 MySQL 事务"

    @pytest.mark.unit
    def test_none_crud_warns_others_still_cleaned(self):
        """CRUD 为 None（容器未注入）时 WARN 告警，其余 CRUD 仍正常清理，不崩溃

        设计意图：清理路径缺注时必须「大声告警」而非静默跳过——
        静默跳过会让旧数据残留、回测结果悄悄污染（最坏故障模式）。
        """
        svc, cruds = _make_service_with_cruds(
            crud_overrides={"order_crud": None, "transfer_crud": None}
        )

        with _mock_kafka_and_container(), \
             patch("ginkgo.data.services.backtest_task_service.GLOG") as mock_glog:
            result = svc.start_task(uuid="uuid-1234")

        # None 的两个触发 WARN（大声告警，非静默跳过）
        delete_warns = [
            str(c.args[0]) for c in mock_glog.WARN.call_args_list
            if "Failed to delete" in str(c.args[0])
        ]
        assert any("order" in w for w in delete_warns), \
            f"order_crud=None 应触发 WARN，实际 delete WARN: {delete_warns}"
        assert any("transfer" in w for w in delete_warns), \
            f"transfer_crud=None 应触发 WARN，实际 delete WARN: {delete_warns}"
        # 其余 7 个仍调用 remove
        assert cruds["order_crud"] is None
        assert cruds["transfer_crud"] is None
        for name in _CLEANUP_KWARGS:
            crud = cruds[name]
            if crud is None:
                continue
            assert crud.remove.called, f"{name} 未被清理"
        # start_task 整体未因 None 崩溃
        assert result.success is True

    @pytest.mark.unit
    def test_clickhouse_cleanup_failure_does_not_abort_start(self):
        """ClickHouse 组 cleanup 失败 → best-effort 告警，不阻断 MySQL 事务与启动（CH 无事务，#5562）

        语义变更：原 test_partial_crud_failure_does_not_abort_cleanup 用 position(MySQL) 测容错，
        但 #5562 后 MySQL 组原子（任一失败→回滚→error，见 TestRerunCleanupAtomicity）。
        best-effort 容错仅对 ClickHouse 成立（CH 无事务能力）。
        """
        svc, cruds = _make_service_with_cruds()
        TestRerunCleanupAtomicity._wire_mysql_transaction(cruds)
        cruds["analyzer_record_crud"].remove.side_effect = Exception("analyzer CH 表锁")

        with _mock_kafka_and_container() as producer:
            result = svc.start_task(uuid="uuid-1234")

        # CH 失败被吞，best-effort 不阻断
        assert result.is_success() is True, "CH cleanup 失败应 best-effort，不阻断启动"
        assert producer.send.called, "CH 失败不应阻止发 Kafka"
        # MySQL 组仍清理（在事务内）
        assert cruds["position_crud"].remove.called
        assert cruds["signal_tracker_crud"].remove.called
        # CH analyzer_record 确实尝试过
        cruds["analyzer_record_crud"].remove.assert_called_once()


class TestRerunCleanupAtomicity:
    """start_task 重跑清理的原子性（#5562）

    库归属（_is_clickhouse 运行时属性为裁判）：
      MySQL 4 个（order/position/transfer/signal_tracker）—— 共享单事务，任一失败全回滚
      ClickHouse 5 个（signal/position_record/analyzer_record/order_record/transfer_record）
        —— CH 无事务（ALTER DELETE 异步 mutation），best-effort 删除+告警，不阻断

    设计变更：原逐表 try-except 容错（半清理仍启动）会让新回测用残留数据致结果污染（#5562 核心）。
    新契约：MySQL 组原子，失败→回滚→不启动；CH 组保留 best-effort。
    """

    # 与实现 _mysql_cleanups / _click_cleanups 对齐（_is_clickhouse 权威）
    MYSQL_CRUD_NAMES = ("order_crud", "position_crud", "transfer_crud", "signal_tracker_crud")
    CLICK_CRUD_NAMES = (
        "signal_crud", "position_record_crud", "analyzer_record_crud",
        "order_record_crud", "transfer_record_crud",
    )

    @staticmethod
    def _wire_mysql_transaction(cruds):
        """给 4 个 MySQL CRUD 装上共享 driver 事务 contextmanager（模拟单例 driver）。

        返回 (shared_session, stats) —— stats={'committed':int,'rolled_back':int}。
        """
        shared_session = MagicMock(name="shared_mysql_session")
        stats = {"committed": 0, "rolled_back": 0}

        @contextmanager
        def fake_tx():
            try:
                yield shared_session
                stats["committed"] += 1
            except Exception:
                stats["rolled_back"] += 1
                raise

        shared_driver = MagicMock(name="shared_mysql_driver")
        shared_driver.get_session.side_effect = fake_tx
        for name in TestRerunCleanupAtomicity.MYSQL_CRUD_NAMES:
            cruds[name]._get_connection.return_value = shared_driver
        return shared_session, stats

    @pytest.mark.unit
    def test_mysql_cleanup_failure_rolls_back_and_aborts_start(self):
        """MySQL 组 cleanup 中途失败 → 事务回滚 + start_task 返回 error，不发 Kafka（#5562）"""
        svc, cruds = _make_service_with_cruds()
        shared_session, stats = self._wire_mysql_transaction(cruds)
        cruds["position_crud"].remove.side_effect = RuntimeError("position 表锁")

        with _mock_kafka_and_container() as producer:
            result = svc.start_task(uuid="uuid-1234")

        assert result.is_success() is False, "MySQL cleanup 失败应返回 error，不启动半清理回测"
        assert producer.send.called is False, "cleanup 失败不应发 Kafka 启动命令"
        assert stats["rolled_back"] >= 1, "MySQL 事务应回滚"
        assert stats["committed"] == 0, "回滚路径不应 commit"

    @pytest.mark.unit
    def test_mysql_cruds_share_single_transaction_session(self):
        """4 个 MySQL CRUD 的 remove 收到同一 session 对象（事务共享，#5562）

        driver 单例 → 4 CRUD 共享 session_factory → 单事务（commit 一次）。
        CH 5 个不传 session（不参与 MySQL 事务）。
        """
        svc, cruds = _make_service_with_cruds()
        shared_session, stats = self._wire_mysql_transaction(cruds)

        with _mock_kafka_and_container():
            result = svc.start_task(uuid="uuid-1234")

        assert result.is_success() is True
        for name in self.MYSQL_CRUD_NAMES:
            _, kwargs = cruds[name].remove.call_args
            assert kwargs.get("session") is shared_session, \
                f"{name} 应收到共享 session，实际 {kwargs.get('session')}"
        for name in self.CLICK_CRUD_NAMES:
            _, kwargs = cruds[name].remove.call_args
            assert "session" not in kwargs or kwargs["session"] is None, \
                f"{name} (CH) 不应参与 MySQL 事务"
        assert stats["committed"] == 1, "MySQL 组应单事务 commit 一次"
        assert stats["rolled_back"] == 0
