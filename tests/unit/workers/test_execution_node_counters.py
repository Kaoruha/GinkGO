"""
ExecutionNode 背压计数器线程安全测试 (#5563)

验证 market-data 消费线程(写)、心跳线程(读)、API status(读) 并发访问
total_event_count / backpressure_count / dropped_event_count 时不丢计数、
读到的三元组自洽（rate 计算分子分母一致）。

根因：`int += 1` 是 LOAD/INCR/STORE 三步非原子，GIL 仅字节码边界释放，
多线程并发递增会丢计数；独立读分子/分母算 rate 会跨时刻不一致。

构造方式：object.__new__ 跳过 ExecutionNode.__init__（GinkgoProducer 构造可能
连 Kafka），只设 _counter_lock + 三个 counter，专注测"线程安全计数"这一行为。
"""
import threading
import pytest
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.workers.execution_node.backpressure import BackpressureChecker


def _make_node_counters_only() -> ExecutionNode:
    """构造仅含计数器 + lock 的 ExecutionNode（跳过 Kafka/Redis init 副作用）"""
    from threading import Lock
    node = object.__new__(ExecutionNode)
    node._counter_lock = Lock()
    node.total_event_count = 0
    node.backpressure_count = 0
    node.dropped_event_count = 0
    return node


@pytest.mark.unit
class TestCounterThreadSafety:
    """#5563: 并发递增计数器应精确（无丢计数）"""

    def test_record_event_processed_thread_safe(self):
        """10 线程并发 record_event_processed，total_event_count 应精确等于总和

        无锁的 `+= 1` 在高并发下会丢计数；封装方法用 Lock 保护后必须精确。
        """
        node = _make_node_counters_only()
        THREADS, PER_THREAD = 10, 5000

        def worker():
            for _ in range(PER_THREAD):
                node.record_event_processed()

        threads = [threading.Thread(target=worker) for _ in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert node.total_event_count == THREADS * PER_THREAD

    def test_record_backpressure_drop_thread_safe(self):
        """record_backpressure_drop 原子递增 backpressure + dropped，两者须相等"""
        node = _make_node_counters_only()
        THREADS, PER_THREAD = 8, 2000

        def worker():
            for _ in range(PER_THREAD):
                node.record_backpressure_drop()

        threads = [threading.Thread(target=worker) for _ in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        expected = THREADS * PER_THREAD
        assert node.backpressure_count == expected
        assert node.dropped_event_count == expected

    def test_snapshot_counters_consistent_under_concurrent_rw(self):
        """并发写事件 + 背压丢弃，snapshot 三元组自洽（bp==dropped，total/bp 精确）"""
        node = _make_node_counters_only()
        EVENTS, DROPS = 10000, 3000

        def event_worker():
            for _ in range(EVENTS):
                node.record_event_processed()

        def drop_worker():
            for _ in range(DROPS):
                node.record_backpressure_drop()

        threads = [threading.Thread(target=event_worker),
                   threading.Thread(target=drop_worker)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total, bp, dropped = node._snapshot_counters()
        assert total == EVENTS
        assert bp == DROPS
        assert dropped == DROPS


@pytest.mark.unit
class TestBackpressureCheckerCounterSafety:
    """#5563: BackpressureChecker 的 int counter (total_checks/warning_count/
    critical_count) 的 += 原在锁外，与 history list 的锁分离；重构后须并入
    同一 self.lock，保证并发 check_queue_status 不丢计数。
    """

    def test_check_queue_status_counters_thread_safe(self):
        """并发 check_queue_status，total_checks 精确等于调用总数"""
        checker = BackpressureChecker(warning_threshold=0.5, critical_threshold=0.8)
        THREADS, PER = 8, 500

        def worker():
            for i in range(PER):
                checker.check_queue_status("p1", current_size=(i % 10) * 100, max_size=1000)

        threads = [threading.Thread(target=worker) for _ in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = checker.get_statistics()
        expected = THREADS * PER
        assert stats["total_checks"] == expected
        # OK 不计入 warning/critical，故两者之和 <= total
        assert stats["warning_count"] + stats["critical_count"] <= expected

    def test_history_size_never_exceeds_max_under_concurrency(self):
        """并发写入历史，history_size 不超过 history_max_size（trim 在锁内原子）"""
        checker = BackpressureChecker()
        checker.history_max_size = 50
        THREADS, PER = 6, 100

        def worker():
            for _ in range(PER):
                checker.check_queue_status("p1", current_size=600, max_size=1000)

        threads = [threading.Thread(target=worker) for _ in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(checker.backpressure_history) <= checker.history_max_size
