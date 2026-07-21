"""#6745 DataWorker topic 对齐：5 个 send_*_signal publish 契约 smoke（#6685 diff coverage gate 采集）。

背景：producer 旧发 ginkgo.data.update，worker 听 ginkgo.data.commands（#6741 已对齐
worker 端，#6745 把 producer 端 5 个信号统一改发 DATA_COMMANDS）。本 PR 改动 5 个
send_*_signal 方法体（kafka_service.py L567/575/582/589/597），均被 containers import
链触达（class 定义行 executed → 非 exempt）但 smoke 不调其方法体 → diff coverage gate
报 0/5 红。

本 smoke 用 `__new__` 跳过 __init__（避免 producer 连真 kafka，CI 无 kafka 友好），
patch publish_message 隔离，仅验证信号 publish 契约（topic + {command,params} 结构）。
其中 tick 的 force→overwrite 映射是数据修复语义关键点（ControlCommandDTO TICK 契约：
delete + re-insert），必须锁定。

锁定要点：
- topic 必须是 KafkaTopics.DATA_COMMANDS（worker 唯一监听口）
- command 名（stockinfo/trade_day/adjustfactor/bar_snapshot/tick）与 worker 分发键一致
- params 结构；tick 用 overwrite（非 force）

纳入 gate 合集采集（见 ci.yml smoke-tests job）。
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 添加项目路径（镜像 test_kafka_trade_day_signal.py）
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.interfaces.kafka_topics import KafkaTopics


def _make_svc():
    """__new__ 跳过 __init__，避免 producer 连真 kafka。
    信号方法契约只依赖 self.publish_message，不依赖 producer 实例状态。"""
    return KafkaService.__new__(KafkaService)


class TestSendDataCommandsSignal:
    """5 个 send_*_signal 的 publish 契约（topic=DATA_COMMANDS + {command,params}）。"""

    @pytest.mark.unit
    def test_send_stockinfo_update_signal(self):
        svc = _make_svc()
        with patch.object(svc, "publish_message", return_value=True) as mock_pub:
            result = svc.send_stockinfo_update_signal()
        assert result is True
        mock_pub.assert_called_once_with(
            KafkaTopics.DATA_COMMANDS, {"command": "stockinfo", "params": {}}
        )

    @pytest.mark.unit
    def test_send_trade_day_signal(self):
        svc = _make_svc()
        with patch.object(svc, "publish_message", return_value=True) as mock_pub:
            result = svc.send_trade_day_signal()
        assert result is True
        mock_pub.assert_called_once_with(
            KafkaTopics.DATA_COMMANDS, {"command": "trade_day", "params": {}}
        )

    @pytest.mark.unit
    def test_send_adjustfactor_update_signal(self):
        svc = _make_svc()
        with patch.object(svc, "publish_message", return_value=True) as mock_pub:
            result = svc.send_adjustfactor_update_signal("000001", full=True, force=False)
        assert result is True
        mock_pub.assert_called_once_with(
            KafkaTopics.DATA_COMMANDS,
            {"command": "adjustfactor", "params": {"code": "000001", "full": True, "force": False}},
        )

    @pytest.mark.unit
    def test_send_daybar_update_signal(self):
        svc = _make_svc()
        with patch.object(svc, "publish_message", return_value=True) as mock_pub:
            result = svc.send_daybar_update_signal("600000", full=False, force=True)
        assert result is True
        # daybar 的 command 名是 bar_snapshot（worker dispatches on bar_snapshot）
        mock_pub.assert_called_once_with(
            KafkaTopics.DATA_COMMANDS,
            {"command": "bar_snapshot", "params": {"code": "600000", "full": False, "force": True}},
        )

    @pytest.mark.unit
    def test_send_tick_update_signal_maps_force_to_overwrite(self):
        """tick 的 force→overwrite 映射是数据修复语义关键点（TICK 契约：delete + re-insert）。"""
        svc = _make_svc()
        with patch.object(svc, "publish_message", return_value=True) as mock_pub:
            result = svc.send_tick_update_signal("000002", full=True, force=True)
        assert result is True
        mock_pub.assert_called_once_with(
            KafkaTopics.DATA_COMMANDS,
            {"command": "tick", "params": {"code": "000002", "full": True, "overwrite": True}},
        )
