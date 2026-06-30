# #5541: get_broker_manager() 全局单例必须线程安全。
# 旧实现是无锁 check-then-set，多线程可同时穿过 `if _broker_manager is None`
# 各自构造实例，导致 broker 状态不一致/丢失。
# 验收：threading.Lock + 双重检查锁定 + 并发拿到同一实例且构造恰好一次。
import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import ginkgo.trading.brokers.broker_manager as bm


def _reset_singleton():
    """每个测试前把全局单例与（若存在）锁重置回初始态。"""
    bm._broker_manager = None


class _CountingBroker:
    """替身 BrokerManager：记录构造次数 + 放大 check-then-set 竞态窗口。"""

    instances = 0
    lock = threading.Lock()

    def __init__(self):
        time.sleep(0.05)  # 放大窗口，让并发线程都能穿过 None 检查
        type(self).lock.acquire()
        type(self).instances += 1
        type(self).lock.release()


class TestBrokerManagerSingletonThreadSafety:
    """#5541: get_broker_manager 必须是线程安全的单例。"""

    def setup_method(self):
        _reset_singleton()

    def test_concurrent_callers_get_same_instance(self):
        """tracer：多线程并发调用，全部拿到同一对象（id 相同）。"""
        results = []
        barrier = threading.Barrier(8)

        def worker():
            barrier.wait()  # 8 线程同时释放，最大化竞态
            results.append(id(bm.get_broker_manager()))

        with patch.object(bm, "BrokerManager", _CountingBroker):
            _CountingBroker.instances = 0
            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # 全部拿到同一实例
        assert len(set(results)) == 1, f"竟态产生多实例: {results}"
        # 构造恰好一次（双重检查锁定的核心保证）
        assert _CountingBroker.instances == 1

    def test_concurrent_no_extra_construction_after_init(self):
        """首次初始化后，后续并发调用不再构造。"""
        with patch.object(bm, "BrokerManager", _CountingBroker):
            _CountingBroker.instances = 0
            first = bm.get_broker_manager()
            assert _CountingBroker.instances == 1

            results = []
            barrier = threading.Barrier(16)

            def worker():
                barrier.wait()
                results.append(bm.get_broker_manager())

            threads = [threading.Thread(target=worker) for _ in range(16)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert len(set(id(r) for r in results)) == 1
        assert id(first) == id(results[0])
        assert _CountingBroker.instances == 1, "初始化后不应再构造"

    def test_sequential_returns_cached_instance(self):
        """顺序调用返回缓存实例（回归保护，非并发）。"""
        with patch.object(bm, "BrokerManager", _CountingBroker):
            _CountingBroker.instances = 0
            a = bm.get_broker_manager()
            b = bm.get_broker_manager()
        assert a is b
        assert _CountingBroker.instances == 1
