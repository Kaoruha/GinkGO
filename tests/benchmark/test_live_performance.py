"""
实盘交易架构性能基准测试 (T080)

验证端到端延迟性能指标：
- PriceUpdate → Signal: < 200ms (p95)
- Signal → Order: < 100ms (p95)
- Order → Kafka: < 100ms (p95)

测试方法：使用时间戳记录测量全链路延迟
"""

import pytest
import time
from datetime import datetime
from typing import List, Dict
from statistics import mean, median

from ginkgo.trading.enums import SOURCE_TYPES
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer


@pytest.mark.benchmark
@pytest.mark.live
class TestLiveTradingPerformance:
    """实盘交易性能基准测试"""

    @pytest.fixture
    def kafka_producer(self):
        """Kafka Producer实例"""
        try:
            producer = GinkgoProducer()
            if not producer.is_connected:
                pytest.skip("Kafka not available")
            yield producer
            producer.close()
        except Exception as e:
            pytest.skip(f"Kafka Producer initialization failed: {e}")

    def test_kafka_producer_send_latency(self, kafka_producer):
        """
        测试Kafka Producer发送延迟

        验证：Order → Kafka < 100ms (p95)
        """
        latencies = []
        test_count = 10

        for i in range(test_count):
            # 构造测试消息
            message = {
                "test_id": f"perf_test_{i}",
                "timestamp": datetime.now().isoformat()
            }

            # 记录开始时间
            start_time = time.time()

            # 发送消息
            result = kafka_producer.send("ginkgo.live.orders.submission", message)

            # 记录结束时间
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            if result:
                latencies.append(latency_ms)

        # 验证性能指标
        assert len(latencies) >= test_count * 0.8, "At least 80% of sends should succeed"

        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
        avg_latency = mean(latencies)

        # P95延迟应 < 100ms
        assert p95_latency < 100, f"P95 latency {p95_latency:.2f}ms > 100ms"
        assert avg_latency < 50, f"Average latency {avg_latency:.2f}ms > 50ms"

        print(f"Kafka Producer Latency - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")

    def test_event_price_update_creation_latency(self):
        """
        测试EventPriceUpdate创建延迟

        验证：事件创建开销 < 10ms
        """
        latencies = []
        test_count = 100

        for i in range(test_count):
            start_time = time.time()

            # 创建PriceUpdate事件
            event = EventPriceUpdate(
                timestamp=datetime.now(),
                source=SOURCE_TYPES.TUSHARE,
                code="000001.SZ",
                price=10.0
            )

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # 验证性能
        assert avg_latency < 5, f"Average event creation {avg_latency:.2f}ms > 5ms"
        assert p95_latency < 10, f"P95 event creation {p95_latency:.2f}ms > 10ms"

        print(f"Event Creation Latency - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")

    def test_redis_set_get_latency(self):
        """
        测试Redis SET/GET延迟

        验证：Redis操作 < 50ms (p95)
        """
        from ginkgo.data.crud import RedisCRUD

        try:
            redis_crud = RedisCRUD()
            # 测试连接
            redis_crud.redis.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

        latencies_set = []
        latencies_get = []
        test_count = 50

        for i in range(test_count):
            key = f"perf_test_key_{i}"
            value = {"test_data": f"value_{i}", "timestamp": datetime.now().isoformat()}

            # 测试SET延迟
            start_time = time.time()
            redis_crud.set(key, value, expire_seconds=60)
            set_latency_ms = (time.time() - start_time) * 1000
            latencies_set.append(set_latency_ms)

            # 测试GET延迟
            start_time = time.time()
            result = redis_crud.get(key)
            get_latency_ms = (time.time() - start_time) * 1000
            latencies_get.append(get_latency_ms)

            # 清理
            redis_crud.delete(key)

        avg_set_latency = mean(latencies_set)
        p95_set_latency = sorted(latencies_set)[int(len(latencies_set) * 0.95)]

        avg_get_latency = mean(latencies_get)
        p95_get_latency = sorted(latencies_get)[int(len(latencies_get) * 0.95)]

        # 验证性能
        assert p95_set_latency < 50, f"P95 SET latency {p95_set_latency:.2f}ms > 50ms"
        assert p95_get_latency < 50, f"P95 GET latency {p95_get_latency:.2f}ms > 50ms"

        print(f"Redis SET - Avg: {avg_set_latency:.2f}ms, P95: {p95_set_latency:.2f}ms")
        print(f"Redis GET - Avg: {avg_get_latency:.2f}ms, P95: {p95_get_latency:.2f}ms")

    def test_end_to_end_simulation_latency(self, kafka_producer):
        """
        端到端延迟模拟测试

        模拟完整链路：PriceUpdate → Signal → Order → Kafka
        验证总体延迟 < 200ms (p95)
        """
        latencies = []
        test_count = 20

        for i in range(test_count):
            # 1. 模拟PriceUpdate事件创建
            price_update_start = time.time()
            price_update = EventPriceUpdate(
                timestamp=datetime.now(),
                source=SOURCE_TYPES.TUSHARE,
                code="000001.SZ",
                price=10.0
            )
            price_update_latency = (time.time() - price_update_start) * 1000

            # 2. 模拟Signal生成（这里简化为创建时间）
            signal_start = time.time()
            # 在实际系统中，这里会调用Strategy.cal()
            signal = {
                "code": "000001.SZ",
                "direction": "LONG",
                "timestamp": datetime.now().isoformat()
            }
            signal_latency = (time.time() - signal_start) * 1000

            # 3. 模拟Order提交到Kafka
            order_start = time.time()
            order_message = {
                "portfolio_id": "test_portfolio",
                "code": "000001.SZ",
                "direction": "BUY",
                "volume": 100,
                "price": 10.0,
                "timestamp": datetime.now().isoformat()
            }
            result = kafka_producer.send("ginkgo.live.orders.submission", order_message)
            order_latency = (time.time() - order_start) * 1000

            if result:
                total_latency = price_update_latency + signal_latency + order_latency
                latencies.append(total_latency)

        # 验证端到端延迟
        assert len(latencies) >= test_count * 0.8, "At least 80% of tests should complete"

        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # 端到端延迟应 < 200ms
        assert p95_latency < 200, f"P95 E2E latency {p95_latency:.2f}ms > 200ms"
        assert avg_latency < 100, f"Average E2E latency {avg_latency:.2f}ms > 100ms"

        print(f"E2E Latency - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")

    def test_portfolio_state_update_latency(self):
        """
        测试Portfolio状态更新延迟

        验证：状态缓存到Redis < 50ms (p95)
        """
        from ginkgo.data.crud import RedisCRUD

        try:
            redis_crud = RedisCRUD()
            redis_crud.redis.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

        latencies = []
        test_count = 50

        for i in range(test_count):
            portfolio_id = f"test_portfolio_perf_{i}"
            state = {
                "status": "RUNNING",
                "queue_size": str(100 + i),
                "buffer_size": "5",
                "position_count": "3",
                "node_id": "test_node"
            }

            start_time = time.time()
            state_key = f"portfolio:{portfolio_id}:state"
            redis_crud.redis.hset(state_key, mapping=state)
            end_time = time.time()

            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)

            # 清理
            redis_crud.redis.delete(state_key)

        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # 验证性能
        assert p95_latency < 50, f"P95 state update {p95_latency:.2f}ms > 50ms"
        assert avg_latency < 20, f"Average state update {avg_latency:.2f}ms > 20ms"

        print(f"Portfolio State Update - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")


@pytest.mark.benchmark
@pytest.mark.live
class TestLiveTradingThroughput:
    """实盘交易吞吐量测试"""

    def test_kafka_producer_throughput(self):
        """
        测试Kafka Producer吞吐量

        验证：能处理 > 100 msg/s
        """
        from ginkgo.data.crud import RedisCRUD

        try:
            producer = GinkgoProducer()
            if not producer.is_connected:
                pytest.skip("Kafka not available")
        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")

        # 发送100条消息
        message_count = 100
        start_time = time.time()

        for i in range(message_count):
            message = {
                "test_id": f"throughput_test_{i}",
                "timestamp": datetime.now().isoformat()
            }
            producer.send_async("ginkgo.live.orders.submission", message)

        producer.flush()
        end_time = time.time()

        elapsed_seconds = end_time - start_time
        throughput = message_count / elapsed_seconds

        # 验证吞吐量
        assert throughput > 100, f"Throughput {throughput:.2f} msg/s < 100 msg/s"

        print(f"Kafka Producer Throughput: {throughput:.2f} msg/s")
        producer.close()

    def test_redis_write_throughput(self):
        """
        测试Redis写入吞吐量

        验证：能处理 > 1000 writes/s
        """
        from ginkgo.data.crud import RedisCRUD

        try:
            redis_crud = RedisCRUD()
            redis_crud.redis.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

        write_count = 100
        start_time = time.time()

        for i in range(write_count):
            key = f"throughput_test_{i}"
            value = {"data": f"value_{i}"}
            redis_crud.set(key, value, expire_seconds=60)

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        throughput = write_count / elapsed_seconds

        # 验证吞吐量
        assert throughput > 1000, f"Throughput {throughput:.2f} writes/s < 1000 writes/s"

        # 清理
        for i in range(write_count):
            redis_crud.delete(f"throughput_test_{i}")

        print(f"Redis Write Throughput: {throughput:.2f} writes/s")


@pytest.mark.benchmark
@pytest.mark.live
class TestLiveTradingResourceUsage:
    """实盘交易资源使用测试"""

    def test_memory_usage_stability(self):
        """
        测试内存使用稳定性

        验证：长时间运行内存不泄漏
        """
        import gc
        import sys

        # 获取初始内存
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 创建大量对象（模拟事件处理）
        events = []
        for i in range(1000):
            event = EventPriceUpdate(
                timestamp=datetime.now(),
                source=SOURCE_TYPES.TUSHARE,
                code=f"00000{i % 10}.SZ",
                price=10.0 + i
            )
            events.append(event)

        # 清理
        del events
        gc.collect()

        # 获取最终内存
        final_objects = len(gc.get_objects())

        # 验证内存增长合理（< 10%）
        object_growth = final_objects - initial_objects
        growth_ratio = object_growth / initial_objects if initial_objects > 0 else 0

        assert growth_ratio < 0.1, f"Memory growth {growth_ratio:.2%} > 10%"

        print(f"Memory Usage - Initial: {initial_objects}, Final: {final_objects}, Growth: {growth_ratio:.2%}")
