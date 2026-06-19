"""DataWorker consumer 自愈测试 -- #6183

DataWorker.run() 长期运行时，Kafka 消费者遇异常会被置 None
（GinkgoConsumer.__init__ 异常即 self.consumer=None），而 run() 的
except 分支只 time.sleep(5) 重试同一个 None，导致一次瞬时断连即永久空转
（错误计数无限增长）。修复：提取 _rebuild_consumer，consumer 失效时
调 _init_consumer 重建（失败明确退避，不 raise）。
"""
import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import MagicMock, patch
import pytest

from ginkgo.data.worker import DataWorker


def _make_worker():
    """构造一个不连 Kafka 的 DataWorker（_consumer 延迟初始化）。"""
    return DataWorker(bar_crud=MagicMock(), node_id="test-rebuild")


def _healthy_consumer():
    """一个健康 consumer mock：有底层 consumer、已连接。"""
    c = MagicMock()
    c.consumer = MagicMock()  # 底层 KafkaConsumer 对象存在
    c.is_connected = True
    return c


class TestRebuildConsumer:
    """#6183: _rebuild_consumer 检测失效并重建。"""

    def test_rebuild_when_consumer_lost(self):
        """consumer 为 None（失效）-> 调 _init_consumer 重建 -> 返回 True。"""
        worker = _make_worker()
        worker._consumer = None  # 失效（初始化失败置 None）

        healthy = _healthy_consumer()

        def fake_init():
            worker._consumer = healthy

        with patch.object(worker, "_init_consumer", side_effect=fake_init) as mock_init:
            result = worker._rebuild_consumer()

        assert result is True
        mock_init.assert_called_once()

    def test_rebuild_returns_false_on_init_failure(self):
        """_init_consumer 抛异常时 _rebuild_consumer 不 raise，返回 False（调用方退避）。"""
        worker = _make_worker()
        worker._consumer = None

        with patch.object(worker, "_init_consumer", side_effect=RuntimeError("kafka down")):
            result = worker._rebuild_consumer()

        assert result is False

    def test_skip_rebuild_when_consumer_healthy(self):
        """consumer 健康时不重建（不调 _init_consumer）。"""
        worker = _make_worker()
        worker._consumer = _healthy_consumer()

        with patch.object(worker, "_init_consumer") as mock_init:
            result = worker._rebuild_consumer()

        assert result is True
        mock_init.assert_not_called()


class TestRunSelfHeal:
    """#6183: run() 在 poll 异常且 consumer 失效时重建并恢复消费（端到端自愈）。

    直接同步调用 worker.run()（它是 Thread.run 入口），通过 _stop_event
    控制循环退出，避免起真实线程。
    """

    def test_run_rebuilds_and_resumes_after_disconnect(self):
        """poll 抛异常（断连）-> 重建 -> 用新 consumer 恢复消费。"""
        worker = _make_worker()

        # 失效 consumer：底层 consumer 存在但已断连，poll 抛异常
        broken = MagicMock()
        broken.consumer = MagicMock()
        broken.consumer.poll.side_effect = RuntimeError("broker gone")
        broken.is_connected = False
        worker._consumer = broken

        # 重建后的健康 consumer：poll 返空，第二次后停止循环
        healthy = _healthy_consumer()
        poll_count = [0]

        def healthy_poll(timeout_ms=1000):
            poll_count[0] += 1
            if poll_count[0] >= 2:
                worker._stop_event.set()
            return {}

        healthy.consumer.poll.side_effect = healthy_poll

        with patch.object(worker, "_init_consumer", side_effect=lambda: setattr(worker, "_consumer", healthy)):
            worker.run()  # 同步执行 run 循环

        # 重建发生：_consumer 从 broken 换成 healthy
        assert worker._consumer is healthy
        # 恢复消费：健康 consumer 的 poll 被调用
        assert healthy.consumer.poll.call_count >= 2

    def test_run_backs_off_when_rebuild_keeps_failing(self):
        """重建持续失败时 run() 退避而非狂刷（验证不无限重建无节流）。"""
        worker = _make_worker()

        broken = MagicMock()
        broken.consumer = MagicMock()
        broken.consumer.poll.side_effect = RuntimeError("broker gone")
        broken.is_connected = False
        worker._consumer = broken

        # _init_consumer 持续失败，且 _rebuild_consumer 内 _init_consumer 失败
        # 不重建成功 -> run() 每次 except 走 sleep(5) 退避分支
        rebuild_calls = [0]

        real_rebuild = worker._rebuild_consumer

        def counting_rebuild():
            rebuild_calls[0] += 1
            if rebuild_calls[0] >= 3:
                worker._stop_event.set()
            return real_rebuild()

        # _init_consumer 始终失败 -> _rebuild_consumer 返 False -> run sleep(5)
        with patch.object(worker, "_init_consumer", side_effect=RuntimeError("still down")), \
             patch.object(worker, "_rebuild_consumer", side_effect=counting_rebuild), \
             patch("ginkgo.data.worker.worker.time.sleep") as mock_sleep:
            worker.run()

        # 退避被调用（非死循环重试同一个 None）
        assert mock_sleep.call_count >= 1
