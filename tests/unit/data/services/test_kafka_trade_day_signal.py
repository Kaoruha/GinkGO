"""
send_trade_day_signal 单元测试（#6488 kafka wiring）

镜像 send_stockinfo_update_signal 的契约：发 DATA_UPDATE topic + 标识 payload。
mock publish_message 隔离真 kafka，只验证信号契约（topic + payload 结构）。
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.interfaces.kafka_topics import KafkaTopics


class TestSendTradeDaySignal:
    """send_trade_day_signal 信号契约测试"""

    @pytest.mark.unit
    def test_send_trade_day_signal_publishes_correct_payload(self):
        """send_trade_day_signal 发 DATA_UPDATE topic + trade_day payload"""
        # __new__ 跳过 __init__，避免 producer 连真 kafka（CI 无 kafka 友好）
        # 信号方法契约只依赖 self.publish_message，不依赖 producer 实例状态
        svc = KafkaService.__new__(KafkaService)
        with patch.object(svc, "publish_message", return_value=True) as mock_pub:
            result = svc.send_trade_day_signal()

        assert result is True
        mock_pub.assert_called_once_with(
            KafkaTopics.DATA_UPDATE, {"type": "trade_day", "code": ""}
        )
