"""ginkgo_kafka 驱动 kafka-python 3.0.0 兼容回归守护（#6157）。

容器 Dockerfile 用 ``uv pip install --system .`` 不读 uv.lock，按 pyproject
``kafka-python>=2.2.15``（无上限）现解析抓到 3.0.0；该版本移除 NoBrokersAvailable
（"找不到 broker"语义并入 KafkaConnectionError）。ginkgo_kafka 一 import 即
ImportError，livecore 崩溃循环。

守护：驱动源码不得引用版本脆弱名 NoBrokersAvailable，只用 2.x/3.x 共有的
KafkaConnectionError / KafkaError。本地（2.2.15）该 import 能过，故用 inspect
检查源码符号存在性做 red→green。
"""
import inspect

import pytest


@pytest.mark.unit
def test_ginkgo_kafka_not_referencing_removed_no_brokers_available():
    """ginkgo_kafka 源码不得引用 NoBrokersAvailable（kafka-python 3.0.0 已删，#6157）。

    红：当前源码 import 了 NoBrokersAvailable（L16）。
    绿：改用 KafkaConnectionError（2.x/3.x 共有）后该名从源码消失。
    """
    from ginkgo.data.drivers import ginkgo_kafka

    source = inspect.getsource(ginkgo_kafka)
    assert "NoBrokersAvailable" not in source, (
        "ginkgo_kafka 引用了 NoBrokersAvailable —— kafka-python 3.0.0 已移除该名，"
        "容器（resolver 抓 3.0.0）一 import 即 ImportError。改用 KafkaConnectionError。"
    )
