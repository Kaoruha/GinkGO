"""
#6736 review fix: `_start_queue_monitor` 的 `create_monitor_layout` 闭包曾引用
已删除的 `subscription_table`（消费 worker 模型 #6736 退役后，Active Subscriptions
面板语义失效，定义块被删但漏删 `layout.split_column` 内引用），致 `ginkgo kafka monitor`
启动即 `NameError`，被外层 `except Exception` 吞成"安静失败"。

回归保护：监控命令启动不进入 "Error starting queue monitor" 分支。
"""
import pytest


class _FakeLive:
    """rich.live.Live 的最小替身：context manager + update()，不真正渲染。"""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def update(self, *args, **kwargs):
        pass


@pytest.fixture
def _monitor_env(monkeypatch):
    """mock 掉监控命令的外部依赖，聚焦 create_monitor_layout 布局构造。"""
    from unittest.mock import MagicMock

    import ginkgo.data.containers as containers_mod
    import ginkgo.libs.core.threading as gtm_mod
    import rich.live as rich_live
    import signal as signal_mod

    fake_service = MagicMock()
    fake_result = MagicMock()
    fake_result.success = True
    fake_result.data = {}
    fake_service.get_statistics.return_value = fake_result

    mock_container = MagicMock()
    mock_container.kafka_service.return_value = fake_service
    monkeypatch.setattr(containers_mod, "container", mock_container)

    fake_gtm = MagicMock()
    fake_gtm.get_worker_count.return_value = 0
    fake_gtm.get_workers_status.return_value = {}
    monkeypatch.setattr(gtm_mod, "GinkgoThreadManager", lambda: fake_gtm)

    monkeypatch.setattr(rich_live, "Live", _FakeLive)
    monkeypatch.setattr(signal_mod, "signal", lambda *a, **kw: None)


class TestKafkaMonitorLayoutNoNameError:
    """#6736 review fix：监控布局构造不应引用已删除的 subscription_table。"""

    @pytest.mark.unit
    def test_start_queue_monitor_does_not_enter_error_branch(
        self, _monitor_env, capsys
    ):
        from ginkgo.client.kafka_cli import _start_queue_monitor

        # duration=0：while 首次检查 elapsed >= duration 即退出，不阻塞。
        _start_queue_monitor(duration=0, interval=1)

        out = capsys.readouterr().out
        assert "Error starting queue monitor" not in out
        assert "subscription_table" not in out
