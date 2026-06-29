"""seam 测试：回测派发契约 DTO 层（ADR-018）。

测接口面（replace 不 layer）——不起 Kafka、不调 service，只断言 DTO 层契约：
- round-trip to_payload/from_payload（start/stop/cancel）
- 9 默认值应用（唯一默认表归 DTO）
- from_payload 拒畸形（缺 task_uuid / 未知或缺 command / start 缺 portfolio_uuid·dates）
- stop/cancel 多余字段忽略（判别联合守护在返回类型层面）
- 订正孤儿：to_payload 不含 priority/timeout；BacktestProgressDTO 已删

详见 docs/adrs/ADR-018-backtest-assignment-contract.md
"""
import pytest

from ginkgo.interfaces.dtos.backtest_assignment_dto import (
    BacktestAssignmentConfig,
    StartAssignment,
    StopAssignment,
    CancelAssignment,
    from_payload,
    MalformedAssignmentError,
)


# ---------- helpers ----------

def _full_config_dict():
    """完整 config（全 11 字段），用于 round-trip。"""
    return {
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "initial_cash": 500000.0,
        "commission_rate": 0.0005,
        "slippage_rate": 0.0002,
        "benchmark_return": 0.08,
        "max_position_ratio": 0.5,
        "stop_loss_ratio": 0.07,
        "take_profit_ratio": 0.2,
        "frequency": "WEEK",
        "analyzers": [{"name": "win_rate", "type": "analyzer", "config": {"window": 30}}],
    }


def _full_start_raw():
    return {
        "task_uuid": "abc123",
        "portfolio_uuid": "port-1",
        "name": "test-backtest",
        "command": "start",
        "config": _full_config_dict(),
    }


# ---------- round-trip ----------

class TestRoundTrip:
    def test_start_round_trip_object(self):
        cmd = from_payload(_full_start_raw())
        assert isinstance(cmd, StartAssignment)
        # 对象 round-trip：to_payload → from_payload 回到相等对象
        assert from_payload(cmd.to_payload()) == cmd

    def test_start_to_payload_structure(self):
        back = from_payload(_full_start_raw()).to_payload()
        assert back["command"] == "start"
        assert back["task_uuid"] == "abc123"
        assert back["portfolio_uuid"] == "port-1"
        assert back["name"] == "test-backtest"
        assert back["config"] == _full_config_dict()  # 含 analyzers 透传

    def test_stop_round_trip(self):
        cmd = from_payload({"task_uuid": "abc123", "command": "stop"})
        assert isinstance(cmd, StopAssignment)
        assert cmd.task_uuid == "abc123"
        assert cmd.to_payload() == {"task_uuid": "abc123", "command": "stop"}

    def test_cancel_round_trip(self):
        cmd = from_payload({"task_uuid": "xyz", "command": "cancel"})
        assert isinstance(cmd, CancelAssignment)
        assert cmd.to_payload() == {"task_uuid": "xyz", "command": "cancel"}


# ---------- 默认值（唯一默认表归 DTO）----------

class TestDefaults:
    def test_defaults_applied_when_optional_missing(self):
        """config 只给 required，9 optional 填默认（消除消费端硬编码默认表）。"""
        raw = {
            "task_uuid": "t1", "portfolio_uuid": "p1", "name": "n", "command": "start",
            "config": {"start_date": "2025-01-01", "end_date": "2025-12-31"},
        }
        cfg = from_payload(raw).config
        assert cfg.initial_cash == 100000.0
        assert cfg.commission_rate == 0.0003
        assert cfg.slippage_rate == 0.0001
        assert cfg.benchmark_return == 0.0
        assert cfg.max_position_ratio == 0.3
        assert cfg.stop_loss_ratio == 0.05
        assert cfg.take_profit_ratio == 0.15
        assert cfg.frequency == "DAY"
        assert cfg.analyzers == []

    def test_provided_values_override_defaults(self):
        cfg = from_payload(_full_start_raw()).config
        assert cfg.initial_cash == 500000.0
        assert cfg.frequency == "WEEK"


# ---------- 拒畸形（构造即校验）----------

class TestRejectMalformed:
    def test_missing_task_uuid(self):
        with pytest.raises(MalformedAssignmentError):
            from_payload({"command": "start", "portfolio_uuid": "p", "name": "n",
                          "config": {"start_date": "s", "end_date": "e"}})

    def test_missing_command_rejected(self):
        """契约化后缺 command = 畸形（今天消费 .get('command','start') 默认 start 的行为收紧）。"""
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "portfolio_uuid": "p", "name": "n",
                          "config": {"start_date": "s", "end_date": "e"}})

    def test_unknown_command(self):
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "command": "foo"})

    def test_start_missing_portfolio_uuid(self):
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "command": "start", "name": "n",
                          "config": {"start_date": "s", "end_date": "e"}})

    def test_start_missing_dates(self):
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "portfolio_uuid": "p", "name": "n",
                          "command": "start", "config": {}})

    def test_start_empty_dates_rejected(self):
        """空串 dates 视同缺失（ADR-018 第⑤步：补第③步删 worker 校验后的真空）。"""
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "portfolio_uuid": "p", "name": "n",
                          "command": "start", "config": {"start_date": "", "end_date": "2025-01-01"}})

    def test_start_empty_portfolio_uuid_rejected(self):
        """空串 portfolio_uuid 视同缺失（#5646 回归：start 字段与 config 同守 min_length=1 拒空串）。"""
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "portfolio_uuid": "", "name": "n",
                          "command": "start", "config": {"start_date": "s", "end_date": "e"}})

    def test_start_empty_name_rejected(self):
        """空串 name 视同缺失（#5646 回归：start 字段与 config 同守 min_length=1 拒空串）。"""
        with pytest.raises(MalformedAssignmentError):
            from_payload({"task_uuid": "t", "portfolio_uuid": "p", "name": "",
                          "command": "start", "config": {"start_date": "s", "end_date": "e"}})


# ---------- stop/cancel 多余字段忽略（守护在返回类型层面）----------

class TestStopIgnoresExtras:
    def test_stop_with_extra_config_ignored(self):
        """stop 误带 config 不 raise，多余字段忽略；StopAssignment 类型本身无 config 字段。"""
        cmd = from_payload({"task_uuid": "t", "command": "stop", "config": {"start_date": "s"}})
        assert isinstance(cmd, StopAssignment)
        assert cmd.task_uuid == "t"
        assert not hasattr(cmd, "config")


# ---------- 订正孤儿 DTO ----------

class TestOrphanCorrection:
    def test_to_payload_no_priority_timeout(self):
        payload = from_payload(_full_start_raw()).to_payload()
        assert "priority" not in payload
        assert "timeout" not in payload

    def test_backtest_progress_dto_deleted(self):
        """BacktestProgressDTO（反向链路死代码）已删。"""
        import ginkgo.interfaces.dtos.backtest_assignment_dto as mod
        assert not hasattr(mod, "BacktestProgressDTO")
        assert not hasattr(mod, "BacktestAssignmentDTO")  # 旧 dataclass 实现已替换
