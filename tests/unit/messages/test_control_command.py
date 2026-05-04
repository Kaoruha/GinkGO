# tests/unit/messages/test_control_command.py
import pytest
from datetime import datetime


class TestControlCommand:
    def test_deploy_factory(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.deploy("portfolio-123")
        d = cmd.to_dict()
        assert d["command"] == "deploy"
        assert d["params"]["portfolio_id"] == "portfolio-123"
        assert d["timestamp"] is not None

    def test_unload_factory(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.unload("portfolio-456")
        d = cmd.to_dict()
        assert d["command"] == "unload"
        assert d["params"]["portfolio_id"] == "portfolio-456"

    def test_daily_cycle_factory(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.daily_cycle()
        d = cmd.to_dict()
        assert d["command"] == "paper_trading"
        assert d["params"] == {}

    def test_from_dict_roundtrip(self):
        from ginkgo.messages.control_command import ControlCommand
        original = ControlCommand.deploy("abc-123")
        data = original.to_dict()
        restored = ControlCommand.from_dict(data)
        assert restored.command == "deploy"
        assert restored.params["portfolio_id"] == "abc-123"

    def test_from_dict_no_params(self):
        from ginkgo.messages.control_command import ControlCommand
        data = {"command": "paper_trading", "timestamp": datetime.now().isoformat()}
        cmd = ControlCommand.from_dict(data)
        assert cmd.command == "paper_trading"
        assert cmd.params == {}

    def test_to_dict_has_no_extra_keys(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.deploy("x")
        d = cmd.to_dict()
        assert set(d.keys()) == {"command", "params", "timestamp"}
