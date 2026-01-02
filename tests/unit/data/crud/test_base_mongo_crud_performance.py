# Upstream: None
# Downstream: None
# Role: BaseMongoCRUD性能基准测试验证CRUD操作满足SC-001到SC-005性能指标


"""
BaseMongoCRUD Performance Benchmark Tests

验证性能指标:
- SC-001: MongoDB CRUD 操作响应时间 < 50ms (p95)
- SC-002: 连接池支持 >= 10 并发连接
- SC-003: TTL 索引自动清理过期记录（在通知记录模型测试）
- SC-004: 单次可查询 >= 1000 用户
- SC-005: 级联删除 < 100ms
"""

import pytest
import time
import pandas as pd
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.data.crud.base_mongo_crud import BaseMongoCRUD
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from ginkgo.enums import SOURCE_TYPES


# 测试模型
class MTestModel(MMongoBase):
    """测试用的简单模型"""

    __tablename__ = "test_performance"

    def __init__(self, value: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    def model_dump_for_mongo(self) -> dict:
        """序列化为MongoDB文档"""
        data = {
            "uuid": self.uuid,
            "meta": self.meta,
            "desc": self.desc,
            "create_at": self.create_at,
            "update_at": self.update_at,
            "is_del": self.is_del,
            "source": self.source.value if isinstance(self.source, SOURCE_TYPES) else self.source,
            "value": self.value
        }
        return data

    @classmethod
    def from_mongo(cls, data: dict) -> "MTestModel":
        """从MongoDB文档反序列化"""
        return cls(
            uuid=data.get("uuid"),
            meta=data.get("meta", ""),
            desc=data.get("desc", ""),
            create_at=data.get("create_at"),
            update_at=data.get("update_at"),
            is_del=data.get("is_del", False),
            source=data.get("source", SOURCE_TYPES.OTHER),
            value=data.get("value", 0)
        )


# 测试CRUD
class TestModelCRUD(BaseMongoCRUD[MTestModel]):
    """测试模型的CRUD"""
    _model_class = MTestModel


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBPerformance:
    """MongoDB CRUD 性能基准测试"""

    @pytest.fixture
    def driver(self):
        """MongoDB驱动实例"""
        from ginkgo.data.drivers import _connection_manager
        return _connection_manager.get_mongo_connection()

    @pytest.fixture
    def crud(self, driver):
        """CRUD实例"""
        return TestModelCRUD(MTestModel, driver)

    @pytest.fixture
    def cleanup(self, crud):
        """清理测试数据"""
        yield
        try:
            collection = crud._get_collection()
            collection.delete_many({"is_del": False})
        except Exception:
            pass

    # ==================== SC-001: CRUD 响应时间 < 50ms p95 ====================

    def test_add_performance_p95(self, crud, cleanup):
        """测试 add() 方法 p95 响应时间 < 50ms"""
        latencies = []
        iterations = 100

        for _ in range(iterations):
            model = MTestModel(value=1)

            start = time.perf_counter()
            crud.add(model)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)  # 转换为毫秒

        # 计算 p95
        latencies_sorted = sorted(latencies)
        p95_index = int(iterations * 0.95)
        p95_latency = latencies_sorted[p95_index]

        print(f"\nadd() p95 latency: {p95_latency:.2f}ms")
        assert p95_latency < 50, f"SC-001: p95 latency {p95_latency:.2f}ms >= 50ms"

    def test_get_performance_p95(self, crud, cleanup):
        """测试 get() 方法 p95 响应时间 < 50ms"""
        # 先插入数据
        model = MTestModel(value=1)
        uuid = crud.add(model)
        assert uuid is not None

        latencies = []
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            crud.get(uuid)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)

        latencies_sorted = sorted(latencies)
        p95_index = int(iterations * 0.95)
        p95_latency = latencies_sorted[p95_index]

        print(f"\nget() p95 latency: {p95_latency:.2f}ms")
        assert p95_latency < 50, f"SC-001: p95 latency {p95_latency:.2f}ms >= 50ms"

    def test_update_performance_p95(self, crud, cleanup):
        """测试 update() 方法 p95 响应时间 < 50ms"""
        model = MTestModel(value=1)
        uuid = crud.add(model)

        latencies = []
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            crud.update(uuid, {"value": 2})
            end = time.perf_counter()

            latencies.append((end - start) * 1000)

        latencies_sorted = sorted(latencies)
        p95_index = int(iterations * 0.95)
        p95_latency = latencies_sorted[p95_index]

        print(f"\nupdate() p95 latency: {p95_latency:.2f}ms")
        assert p95_latency < 50, f"SC-001: p95 latency {p95_latency:.2f}ms >= 50ms"

    # ==================== SC-002: 连接池 >= 10 并发连接 ====================

    def test_concurrent_connections(self, crud, cleanup):
        """测试连接池支持 >= 10 并发连接"""
        concurrency = 10
        operations_per_thread = 10

        def worker(worker_id: int) -> List[float]:
            """工作线程函数"""
            latencies = []
            for i in range(operations_per_thread):
                model = MTestModel(value=worker_id * 100 + i)

                start = time.perf_counter()
                crud.add(model)
                end = time.perf_counter()

                latencies.append((end - start) * 1000)
            return latencies

        all_latencies = []
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(worker, i): i for i in range(concurrency)}

            for future in as_completed(futures):
                latencies = future.result()
                all_latencies.extend(latencies)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        print(f"\n{concurrency} concurrent threads completed {len(all_latencies)} operations in {total_time:.2f}s")
        print(f"Average latency: {sum(all_latencies) / len(all_latencies):.2f}ms")

        # 验证所有操作都成功
        assert len(all_latencies) == concurrency * operations_per_thread
        assert total_time < 30, f"Concurrent operations took too long: {total_time:.2f}s"

    # ==================== SC-004: 查询 >= 1000 用户 ====================

    def test_query_large_dataset(self, crud, cleanup):
        """测试单次查询 >= 1000 记录的性能"""
        # 批量插入 1000 条记录
        models = [MTestModel(value=i) for i in range(1000)]
        inserted = crud.add_many(models)
        assert inserted == 1000

        # 查询性能测试
        start = time.perf_counter()
        results = crud.get_all(limit=1000)
        end = time.perf_counter()

        latency = (end - start) * 1000

        print(f"\nQuery 1000 records latency: {latency:.2f}ms")
        assert len(results) == 1000, f"SC-004: Expected 1000 records, got {len(results)}"
        assert latency < 200, f"Query 1000 records took {latency:.2f}ms >= 200ms"

    def test_query_large_dataset_p95(self, crud, cleanup):
        """测试查询大结果集的 p95 性能"""
        # 批量插入 1000 条记录
        models = [MTestModel(value=i) for i in range(1000)]
        inserted = crud.add_many(models)
        assert inserted == 1000

        latencies = []
        iterations = 50

        for _ in range(iterations):
            start = time.perf_counter()
            results = crud.get_all(limit=1000)
            end = time.perf_counter()

            assert len(results) == 1000
            latencies.append((end - start) * 1000)

        latencies_sorted = sorted(latencies)
        p95_index = int(iterations * 0.95)
        p95_latency = latencies_sorted[p95_index]

        print(f"\nQuery 1000 records p95 latency: {p95_latency:.2f}ms")
        assert p95_latency < 200, f"SC-001 (large query): p95 latency {p95_latency:.2f}ms >= 200ms"

    # ==================== 批量操作优化 ====================

    def test_batch_insert_vs_single(self, crud, cleanup):
        """对比批量插入和单条插入的性能"""
        batch_size = 100

        # 批量插入
        batch_models = [MTestModel(value=i) for i in range(batch_size)]
        start = time.perf_counter()
        crud.add_many(batch_models)
        batch_time = time.perf_counter() - start

        # 单条插入
        start = time.perf_counter()
        for i in range(batch_size, batch_size * 2):
            model = MTestModel(value=i)
            crud.add(model)
        single_time = time.perf_counter() - start

        speedup = single_time / batch_time
        print(f"\nBatch insert: {batch_time:.4f}s, Single insert: {single_time:.4f}s")
        print(f"Speedup: {speedup:.2f}x")

        assert speedup > 2, f"Batch insert should be at least 2x faster, got {speedup:.2f}x"

    # ==================== 缓存效果验证 ====================

    def test_cache_effectiveness(self, crud, cleanup):
        """验证查询缓存效果"""
        model = MTestModel(value=1)
        uuid = crud.add(model)

        # 第一次查询（缓存未命中）
        start = time.perf_counter()
        crud.get(uuid)
        first_time = time.perf_counter() - start

        # 第二次查询（缓存命中）
        start = time.perf_counter()
        crud.get(uuid)
        cached_time = time.perf_counter() - start

        speedup = first_time / (cached_time if cached_time > 0 else 0.000001)
        print(f"\nFirst query: {first_time*1000:.4f}ms, Cached query: {cached_time*1000:.4f}ms")
        print(f"Cache speedup: {speedup:.2f}x")

        assert cached_time < first_time, "Cached query should be faster"


@pytest.mark.unit
@pytest.mark.database
class TestMongoDBConnectionPool:
    """连接池专项测试"""

    @pytest.fixture
    def driver(self):
        """MongoDB驱动实例"""
        from ginkgo.data.drivers import _connection_manager
        return _connection_manager.get_mongo_connection()

    def test_connection_pool_config(self, driver):
        """验证连接池配置"""
        # 验证 MongoClient 配置
        assert driver.client is not None
        print(f"\nMongoClient maxPoolSize: {driver.client.MAX_POOL_SIZE}")
        print(f"MongoClient minPoolSize: {driver.client.MIN_POOL_SIZE}")

        # 配置应该满足 SC-002
        assert driver.client.MAX_POOL_SIZE >= 10, "SC-002: maxPoolSize >= 10"
        assert driver.client.MIN_POOL_SIZE >= 1, "minPoolSize should be at least 1"

    def test_health_check_performance(self, driver):
        """测试 health_check 性能"""
        latencies = []

        for _ in range(50):
            start = time.perf_counter()
            is_healthy = driver.health_check()
            end = time.perf_counter()

            assert is_healthy is True
            latencies.append((end - start) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        print(f"\nhealth_check() average latency: {avg_latency:.2f}ms")
        assert avg_latency < 20, f"health_check too slow: {avg_latency:.2f}ms"
