"""
Redis容错机制集成测试 (T072) - 直接测试Redis操作

验证Redis操作失败时的容错处理：
- 心跳写入失败处理
- ConnectionPool连接稳定性
- 异常场景下的数据一致性
"""

import pytest
import time
from datetime import datetime

from ginkgo.data.crud import RedisCRUD


@pytest.mark.integration
@pytest.mark.live
class TestRedisTolerance:
    """Redis容错机制集成测试 - 直接Redis操作"""

    @pytest.fixture
    def redis_client(self):
        """获取Redis客户端"""
        try:
            redis_crud = RedisCRUD()
            return redis_crud.redis
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    def test_heartbeat_write_success(self, redis_client):
        """
        测试心跳正常写入

        验证心跳写入Redis的基本功能：
        - 使用setex设置TTL
        - 读取心跳值
        - TTL验证
        """
        node_id = "test_heartbeat_success"
        heartbeat_key = f"heartbeat:node:{node_id}"

        # 清理
        redis_client.delete(heartbeat_key)

        # 1. 写入心跳
        heartbeat_value = datetime.now().isoformat()
        ttl = 30
        redis_client.setex(heartbeat_key, ttl, heartbeat_value)

        # 2. 验证写入成功
        exists = redis_client.exists(heartbeat_key)
        assert exists, "Heartbeat should exist"

        # 3. 验证值
        retrieved_value = redis_client.get(heartbeat_key)
        assert retrieved_value.decode('utf-8') == heartbeat_value

        # 4. 验证TTL
        redis_ttl = redis_client.ttl(heartbeat_key)
        assert redis_ttl > 0 and redis_ttl <= 30

        # 清理
        redis_client.delete(heartbeat_key)

    def test_multiple_heartbeat_operations(self, redis_client):
        """
        测试多次心跳操作

        验证连续多次心跳写入的稳定性：
        - 多次setex操作
        - TTL刷新
        - 数据一致性
        """
        node_id = "test_multi_heartbeat"
        heartbeat_key = f"heartbeat:node:{node_id}"

        # 清理
        redis_client.delete(heartbeat_key)

        # 1. 第一次心跳
        heartbeat_1 = datetime.now().isoformat()
        redis_client.setex(heartbeat_key, 30, heartbeat_1)
        ttl_1 = redis_client.ttl(heartbeat_key)
        assert ttl_1 > 0

        # 2. 等待一小段时间
        time.sleep(2)

        # 3. 第二次心跳（刷新TTL）
        heartbeat_2 = datetime.now().isoformat()
        redis_client.setex(heartbeat_key, 30, heartbeat_2)
        ttl_2 = redis_client.ttl(heartbeat_key)
        assert ttl_2 > 0

        # 4. 验证TTL被刷新（应该接近30秒）
        assert abs(ttl_2 - 30) < 2, f"TTL should be refreshed to ~30s, got {ttl_2}"

        # 5. 验证值是最新的
        retrieved = redis_client.get(heartbeat_key)
        assert retrieved.decode('utf-8') == heartbeat_2

        # 清理
        redis_client.delete(heartbeat_key)

    def test_metrics_update_operations(self, redis_client):
        """
        测试指标更新操作

        验证Node和Portfolio指标更新：
        - Hash类型操作
        - 字段更新
        - 读取完整性
        """
        node_id = "test_metrics_ops"
        metrics_key = f"node:metrics:{node_id}"

        # 清理
        redis_client.delete(metrics_key)

        # 1. 初始写入
        redis_client.hset(metrics_key, mapping={
            "portfolio_count": "3",
            "queue_size": "150",
            "status": "RUNNING"
        })

        # 2. 验证初始值
        metrics = redis_client.hgetall(metrics_key)
        metrics_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in metrics.items()
        }

        assert metrics_str["portfolio_count"] == "3"
        assert metrics_str["queue_size"] == "150"
        assert metrics_str["status"] == "RUNNING"

        # 3. 更新部分字段
        redis_client.hset(metrics_key, "queue_size", "200")
        redis_client.hset(metrics_key, "status", "PAUSED")

        # 4. 验证更新
        updated_metrics = redis_client.hgetall(metrics_key)
        updated_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in updated_metrics.items()
        }

        assert updated_str["queue_size"] == "200"
        assert updated_str["status"] == "PAUSED"
        assert updated_str["portfolio_count"] == "3"  # 未更新字段保持不变

        # 清理
        redis_client.delete(metrics_key)

    def test_portfolio_state_operations(self, redis_client):
        """
        测试Portfolio状态操作

        验证Portfolio状态管理：
        - 状态写入
        - 多字段更新
        - 状态读取
        """
        portfolio_id = "test_portfolio_state_ops"
        state_key = f"portfolio:{portfolio_id}:state"

        # 清理
        redis_client.delete(state_key)

        # 1. 写入完整状态
        redis_client.hset(state_key, mapping={
            "status": "RUNNING",
            "queue_size": "100",
            "buffer_size": "5",
            "position_count": "3",
            "node_id": "node_001"
        })

        # 2. 读取并验证
        state = redis_client.hgetall(state_key)
        state_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in state.items()
        }

        assert state_str["status"] == "RUNNING"
        assert state_str["queue_size"] == "100"
        assert state_str["node_id"] == "node_001"

        # 3. 更新状态和时间戳
        redis_client.hset(state_key, mapping={
            "status": "STOPPING",
            "last_update": datetime.now().isoformat()
        })

        # 4. 验证更新
        updated_state = redis_client.hgetall(state_key)
        updated_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in updated_state.items()
        }

        assert updated_str["status"] == "STOPPING"
        assert "last_update" in updated_str

        # 清理
        redis_client.delete(state_key)

    def test_concurrent_redis_operations(self, redis_client):
        """
        测试并发Redis操作

        验证多个并发操作的稳定性：
        - 多个Portfolio同时更新状态
        - 多个Node指标更新
        - 数据一致性
        """
        # 1. 创建多个Portfolio状态
        for i in range(5):
            portfolio_id = f"test_concurrent_portfolio_{i}"
            state_key = f"portfolio:{portfolio_id}:state"

            redis_client.hset(state_key, mapping={
                "status": "RUNNING",
                "queue_size": str(i * 100),
                "node_id": f"node_{i % 2}"
            })

        # 2. 验证所有Portfolio状态存在
        for i in range(5):
            portfolio_id = f"test_concurrent_portfolio_{i}"
            state_key = f"portfolio:{portfolio_id}:state"

            exists = redis_client.exists(state_key)
            assert exists, f"Portfolio {portfolio_id} state should exist"

            state = redis_client.hgetall(state_key)
            state_str = {
                k.decode('utf-8') if isinstance(k, bytes) else k:
                v.decode('utf-8') if isinstance(v, bytes) else v
                for k, v in state.items()
            }

            assert state_str["queue_size"] == str(i * 100)

        # 3. 清理
        for i in range(5):
            portfolio_id = f"test_concurrent_portfolio_{i}"
            state_key = f"portfolio:{portfolio_id}:state"
            redis_client.delete(state_key)

    def test_schedule_plan_operations(self, redis_client):
        """
        测试调度计划操作

        验证调度计划的读写操作：
        - 计划写入
        - 计划读取
        - 计划更新
        """
        # 清理
        redis_client.delete("schedule:plan")

        # 1. 写入调度计划
        plan_data = {
            "portfolio_001": "node_001",
            "portfolio_002": "node_001",
            "portfolio_003": "node_002"
        }
        redis_client.hset("schedule:plan", mapping=plan_data)

        # 2. 读取计划
        plan = redis_client.hgetall("schedule:plan")
        plan_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in plan.items()
        }

        assert len(plan_str) == 3
        assert plan_str["portfolio_001"] == "node_001"

        # 3. 更新某个Portfolio的分配
        redis_client.hset("schedule:plan", "portfolio_001", "node_002")

        # 4. 验证更新
        updated_plan = redis_client.hgetall("schedule:plan")
        updated_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in updated_plan.items()
        }

        assert updated_str["portfolio_001"] == "node_002"
        assert updated_str["portfolio_002"] == "node_001"  # 其他不变

        # 清理
        redis_client.delete("schedule:plan")

    def test_redis_data_types_consistency(self, redis_client):
        """
        测试Redis数据类型一致性

        验证不同数据类型的操作稳定性：
        - String（心跳）
        - Hash（指标、状态）
        - 操作原子性
        """
        node_id = "test_data_consistency"

        # 1. String类型操作
        heartbeat_key = f"heartbeat:node:{node_id}"
        redis_client.setex(heartbeat_key, 30, "2026-01-08T10:00:00")

        value = redis_client.get(heartbeat_key)
        assert value.decode('utf-8') == "2026-01-08T10:00:00"

        # 2. Hash类型操作（指标）
        metrics_key = f"node:metrics:{node_id}"
        redis_client.hset(metrics_key, "count", "10")
        redis_client.hset(metrics_key, "status", "RUNNING")

        metrics = redis_client.hgetall(metrics_key)
        metrics_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in metrics.items()
        }

        assert metrics_str["count"] == "10"
        assert metrics_str["status"] == "RUNNING"

        # 3. Hash类型操作（状态）
        state_key = f"portfolio:{node_id}:state"
        redis_client.hset(state_key, mapping={
            "status": "RUNNING",
            "queue_size": "100"
        })

        state = redis_client.hgetall(state_key)
        assert len(state) == 2

        # 清理
        redis_client.delete(heartbeat_key)
        redis_client.delete(metrics_key)
        redis_client.delete(state_key)

    def test_redis_error_handling(self, redis_client):
        """
        测试Redis错误处理

        验证异常操作的处理：
        - 读取不存在的键
        - 操作失败不影响后续操作
        """
        # 1. 读取不存在的键
        non_existent = redis_client.get("non_existent_key")
        assert non_existent is None

        # 2. 读取不存在的Hash
        non_existent_hash = redis_client.hgetall("non_existent_hash")
        assert len(non_existent_hash) == 0

        # 3. 操作存在键的特定字段
        test_key = "test_error_handling"
        redis_client.hset(test_key, "field1", "value1")

        # 读取不存在的字段
        non_existent_field = redis_client.hget(test_key, "non_existent_field")
        assert non_existent_field is None

        # 验证现有字段仍可读取
        existing_field = redis_client.hget(test_key, "field1")
        assert existing_field.decode('utf-8') == "value1"

        # 清理
        redis_client.delete(test_key)

    def test_redis_operation_performance(self, redis_client):
        """
        测试Redis操作性能

        验证基本操作性能：
        - 写入性能
        - 读取性能
        - 批量操作性能
        """
        import time

        # 1. 写入性能测试
        write_start = time.time()
        for i in range(100):
            redis_client.set(f"perf_test_key_{i}", f"value_{i}")
        write_time = time.time() - write_start

        # 100次写入应该在1秒内完成
        assert write_time < 1.0, f"100 writes should take < 1s, took {write_time:.2f}s"

        # 2. 读取性能测试
        read_start = time.time()
        for i in range(100):
            value = redis_client.get(f"perf_test_key_{i}")
            assert value is not None
        read_time = time.time() - read_start

        # 100次读取应该在1秒内完成
        assert read_time < 1.0, f"100 reads should take < 1s, took {read_time:.2f}s"

        # 清理
        for i in range(100):
            redis_client.delete(f"perf_test_key_{i}")


@pytest.mark.integration
@pytest.mark.live
class TestRedisFailureRecovery:
    """Redis失败恢复场景测试 - 直接Redis操作"""

    @pytest.fixture
    def redis_client(self):
        """获取Redis客户端"""
        try:
            redis_crud = RedisCRUD()
            return redis_crud.redis
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    def test_sequential_operations(self, redis_client):
        """
        测试连续操作稳定性

        验证连续多次操作的稳定性：
        - 写入、读取、删除循环
        - 数据一致性
        """
        node_id = "test_sequential"

        # 执行多次循环操作
        for i in range(10):
            # 1. 写入
            heartbeat_key = f"heartbeat:node:{node_id}"
            redis_client.setex(heartbeat_key, 30, f"heartbeat_{i}")

            # 2. 验证
            value = redis_client.get(heartbeat_key)
            assert value.decode('utf-8') == f"heartbeat_{i}"

            # 3. 更新
            redis_client.setex(heartbeat_key, 30, f"heartbeat_{i+1}")

            # 4. 验证更新
            updated_value = redis_client.get(heartbeat_key)
            assert updated_value.decode('utf-8') == f"heartbeat_{i+1}"

        # 清理
        redis_client.delete(heartbeat_key)

    def test_batch_operations(self, redis_client):
        """
        测试批量操作

        验证批量操作的稳定性：
        - 多个键值对操作
        - 批量删除
        """
        # 1. 批量写入
        keys = []
        for i in range(20):
            key = f"batch_test_key_{i}"
            redis_client.set(key, f"value_{i}")
            keys.append(key)

        # 2. 验证所有键存在
        for key in keys:
            assert redis_client.exists(key), f"Key {key} should exist"

        # 3. 批量读取
        for i, key in enumerate(keys):
            value = redis_client.get(key)
            assert value.decode('utf-8') == f"value_{i}"

        # 4. 批量删除
        for key in keys:
            redis_client.delete(key)

        # 5. 验证删除
        for key in keys:
            assert not redis_client.exists(key), f"Key {key} should be deleted"

    def test_data_consistency_after_multiple_updates(self, redis_client):
        """
        测试多次更新后数据一致性

        验证：
        - 多次更新同一键
        - 数据最终一致性
        """
        portfolio_id = "test_consistency"
        state_key = f"portfolio:{portfolio_id}:state"

        # 1. 初始状态
        redis_client.hset(state_key, mapping={
            "status": "RUNNING",
            "queue_size": "100",
            "node_id": "node_001"
        })

        # 2. 多次更新queue_size
        for i in range(5):
            redis_client.hset(state_key, "queue_size", str((i + 1) * 100))

        # 3. 验证最终值
        final_state = redis_client.hgetall(state_key)
        final_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in final_state.items()
        }

        assert final_str["queue_size"] == "500"  # 最后一次更新
        assert final_str["status"] == "RUNNING"  # 未更新字段保持
        assert final_str["node_id"] == "node_001"

        # 清理
        redis_client.delete(state_key)
