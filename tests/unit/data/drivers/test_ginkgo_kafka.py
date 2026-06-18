"""ginkgo_kafka 驱动 kafka-python 3.0.0 兼容回归守护（#6157）。

容器 Dockerfile 用 ``uv pip install --system .`` 不读 uv.lock，按 pyproject
``kafka-python>=2.2.15``（无上限）现解析抓到 3.0.0；该版本移除 NoBrokersAvailable
（"找不到 broker"语义并入 KafkaConnectionError）。ginkgo_kafka 一 import 即
ImportError，livecore 崩溃循环。

守护：驱动源码不得引用版本脆弱名 NoBrokersAvailable，只用 2.x/3.x 共有的
KafkaConnectionError / KafkaError。本地（2.2.15）该 import 能过，故用 inspect
检查源码符号存在性做 red→green。
"""
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_ginkgo_kafka_not_referencing_removed_no_brokers_available():
    """ginkgo_kafka 不得 import NoBrokersAvailable（kafka-python 3.0.0 已删，#6157）。

    运行时校验模块命名空间（非 inspect.getsource 全文字符串匹配，回应 review）：
    注释里可提及该名做解释，只要没真的 import 绑定进命名空间。
    """
    import ginkgo.data.drivers.ginkgo_kafka as _mod

    assert not hasattr(_mod, "NoBrokersAvailable"), (
        "ginkgo_kafka 把 NoBrokersAvailable 绑进命名空间 —— kafka-python 3.0.0 已移除该名，"
        "容器（resolver 抓 3.0.0）一 import 即 ImportError。改用 KafkaError（基类）。"
    )


@pytest.mark.unit
def test_send_kafka_timeout_degrades_disconnect():
    """KafkaTimeoutError（3.x bootstrap 失败，非 KafkaConnectionError 子类）应被捕获并降级断开。

    red: except KafkaConnectionError 抓不住 KafkaTimeoutError（issubclass=False），落
    except Exception 不设 _connected=False → 降级不彻底。
    green: 改 except KafkaError（基类）后，timeout 进降级分支设 _connected=False。
    回应 #6157 review：运行时行为校验，非 inspect.getsource 字符串匹配。
    """
    from kafka.errors import KafkaTimeoutError
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

    p = GinkgoProducer.__new__(GinkgoProducer)  # 绕过真实连接 __init__
    p._connected = True
    future = MagicMock()
    future.get.side_effect = KafkaTimeoutError("bootstrap timeout")
    p.producer = MagicMock()
    p.producer.send.return_value = future

    result = p.send("topic", "msg")

    assert result is False
    assert p._connected is False  # timeout 必须触发降级断开
