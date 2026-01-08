"""
心跳机制集成测试 (T047) - 直接测试Redis和Kafka Driver

验证心跳机制的核心功能：
- Redis心跳键的写入和TTL
- 性能指标到Redis的存储
- Scheduler读取心跳状态
"""

import pytest
import time
from datetime import datetime

from ginkgo.data.crud import RedisCRUD
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer


@pytest.mark.integration
@pytest.mark.live
class TestHeartbeatMechanism:
    """心跳机制集成测试 - 直接测试Redis"""

    @pytest.fixture
    def redis_client(self):
        """获取Redis客户端"""
        redis_crud = RedisCRUD()
        return redis_crud.redis

    def test_heartbeat_write_to_redis(self, redis_client):
        """测试心跳写入Redis（直接操作）"""
        node_id = "test_node_heartbeat_direct"
        heartbeat_key = f"heartbeat:node:{node_id}"

        # 清理旧数据
        redis_client.delete(heartbeat_key)

        # 直接写入心跳（模拟ExecutionNode._send_heartbeat的行为）
        heartbeat_value = datetime.now().isoformat()
        ttl = 30  # 30秒TTL

        redis_client.setex(heartbeat_key, ttl, heartbeat_value)

        # 验证心跳存在
        exists = redis_client.exists(heartbeat_key)
        assert exists, "Heartbeat key should exist in Redis"

        # 验证TTL
        redis_ttl = redis_client.ttl(heartbeat_key)
        assert redis_ttl > 0 and redis_ttl <= 30, f"Heartbeat TTL should be around 30 seconds, got {redis_ttl}"

        # 验证值正确
        stored_value = redis_client.get(heartbeat_key)
        assert stored_value.decode('utf-8') == heartbeat_value

        # 清理
        redis_client.delete(heartbeat_key)

    def test_heartbeat_ttl_expires(self, redis_client):
        """测试心跳在TTL后过期（使用短TTL）"""
        node_id = "test_node_expire_direct"
        heartbeat_key = f"heartbeat:node:{node_id}"

        # 清理
        redis_client.delete(heartbeat_key)

        # 写入心跳（短TTL用于测试）
        redis_client.setex(heartbeat_key, 2, datetime.now().isoformat())

        # 验证立即存在
        assert redis_client.exists(heartbeat_key), "Heartbeat should exist immediately"

        # 等待TTL过期
        time.sleep(3)

        # 验证已过期
        assert not redis_client.exists(heartbeat_key), "Heartbeat should expire after TTL"

        # 清理
        redis_client.delete(heartbeat_key)

    def test_multiple_heartbeats_refresh_ttl(self, redis_client):
        """测试多次心跳刷新TTL"""
        node_id = "test_node_refresh_direct"
        heartbeat_key = f"heartbeat:node:{node_id}"

        # 清理
        redis_client.delete(heartbeat_key)

        # 第一次心跳
        redis_client.setex(heartbeat_key, 30, datetime.now().isoformat())
        ttl1 = redis_client.ttl(heartbeat_key)
        assert ttl1 > 0, "TTL should be positive after first heartbeat"

        # 等待一小段时间
        time.sleep(2)

        # 第二次心跳（刷新TTL）
        redis_client.setex(heartbeat_key, 30, datetime.now().isoformat())
        ttl2 = redis_client.ttl(heartbeat_key)
        assert ttl2 > 0, "TTL should be positive after second heartbeat"

        # 验证TTL被刷新（第二次心跳后TTL应该接近30秒）
        # 注意：由于有2秒等待，ttl2应该接近30，而ttl1应该接近28
        assert abs(ttl2 - 30) < 2, f"TTL should be refreshed to ~30s, got {ttl2}"

        # 清理
        redis_client.delete(heartbeat_key)

    def test_node_metrics_write_to_redis(self, redis_client):
        """测试节点性能指标写入Redis（直接操作）"""
        node_id = "test_node_metrics_direct"
        metrics_key = f"node:metrics:{node_id}"

        # 清理
        redis_client.delete(metrics_key)

        # 直接写入指标（模拟ExecutionNode._update_node_metrics的行为）
        metrics = {
            "portfolio_count": "3",
            "queue_size": "150",
            "status": "RUNNING",
            "cpu_usage": "25.5",
            "total_events": "1000",
            "backpressure_count": "5",
            "dropped_events": "2"
        }

        redis_client.hset(metrics_key, mapping=metrics)

        # 验证指标存在
        exists = redis_client.exists(metrics_key)
        assert exists, "Metrics key should exist in Redis"

        # 读取并验证指标
        stored_metrics = redis_client.hgetall(metrics_key)

        # 转换bytes到str
        metrics_str = {
            k.decode('utf-8') if isinstance(k, bytes) else k:
            v.decode('utf-8') if isinstance(v, bytes) else v
            for k, v in stored_metrics.items()
        }

        # 验证必要字段
        assert "portfolio_count" in metrics_str
        assert "queue_size" in metrics_str
        assert "status" in metrics_str
        assert metrics_str["portfolio_count"] == "3"
        assert metrics_str["status"] == "RUNNING"

        # 清理
        redis_client.delete(metrics_key)

    def test_scheduler_reads_healthy_nodes(self, redis_client):
        """测试Scheduler读取健康节点（直接模拟）"""
        # 创建模拟心跳数据
        redis_client.delete("heartbeat:node:test_healthy_1")
        redis_client.delete("heartbeat:node:test_healthy_2")

        # 设置心跳（模拟ExecutionNode发送）
        redis_client.setex("heartbeat:node:test_healthy_1", 30, datetime.now().isoformat())
        redis_client.setex("heartbeat:node:test_healthy_2", 30, datetime.now().isoformat())

        # 扫描所有心跳键（模拟Scheduler._get_healthy_nodes）
        heartbeat_keys = redis_client.keys("heartbeat:node:*")

        healthy_nodes = []
        for key in heartbeat_keys:
            # 提取node_id
            node_id = key.decode('utf-8').replace("heartbeat:node:", "")

            # 获取性能指标
            metrics_key = f"node:metrics:{node_id}"
            metrics = redis_client.hgetall(metrics_key)

            # 获取Portfolio列表
            portfolios_key = f"node:{node_id}:portfolios"
            portfolio_ids = redis_client.smembers(portfolios_key)

            healthy_nodes.append({
                "node_id": node_id,
                "is_online": True,
                "metrics": metrics,
                "portfolio_ids": portfolio_ids
            })

        # 验证检测到2个节点
        assert len(healthy_nodes) == 2, "Should detect 2 healthy nodes"

        node_ids = {n['node_id'] for n in healthy_nodes}
        assert "test_healthy_1" in node_ids
        assert "test_healthy_2" in node_ids

        # 清理
        redis_client.delete("heartbeat:node:test_healthy_1")
        redis_client.delete("heartbeat:node:test_healthy_2")

    def test_scheduler_filters_offline_nodes(self, redis_client):
        """测试Scheduler过滤离线节点"""
        # 设置一个在线节点
        redis_client.delete("heartbeat:node:test_online_direct")
        redis_client.setex("heartbeat:node:test_online_direct", 30, datetime.now().isoformat())

        # 离线节点不设置心跳

        # 创建调度计划
        redis_client.hset("schedule:plan", mapping={
            "portfolio_online": "test_online_direct",
            "portfolio_offline": "test_offline_direct"
        })

        # 读取在线节点
        heartbeat_keys = redis_client.keys("heartbeat:node:*")
        online_node_ids = set()
        for key in heartbeat_keys:
            node_id = key.decode('utf-8').replace("heartbeat:node:", "")
            online_node_ids.add(node_id)

        # 检测孤儿Portfolio（离线节点的Portfolio）
        schedule_plan = redis_client.hgetall("schedule:plan")
        plan = {
            k.decode('utf-8'): v.decode('utf-8')
            for k, v in schedule_plan.items()
        }

        orphaned = []
        for portfolio_id, node_id in plan.items():
            if node_id not in online_node_ids and node_id != "__ORPHANED__":
                orphaned.append(portfolio_id)

        # 验证只检测到离线节点的Portfolio
        assert len(orphaned) == 1, "Should detect 1 orphaned portfolio"
        assert "portfolio_offline" in orphaned, "Orphaned portfolio should be from offline node"

        # 清理
        redis_client.delete("heartbeat:node:test_online_direct")
        redis_client.delete("schedule:plan")


@pytest.mark.integration
@pytest.mark.live
class TestKafkaDriverHeartbeat:
    """Kafka Driver心跳测试 - 直接测试Kafka"""

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

    def test_kafka_producer_send_heartbeat_message(self, kafka_producer):
        """测试Kafka Producer发送心跳消息"""
        node_id = "test_kafka_heartbeat_node"

        # 构造心跳消息
        heartbeat_message = {
            "type": "heartbeat",
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "portfolio_count": 2,
                "queue_size": 100,
                "status": "RUNNING"
            }
        }

        # 发送心跳到Kafka
        result = kafka_producer.send("ginkgo.live.system.events", heartbeat_message)

        # 验证发送成功
        assert result is True, "Heartbeat message should be sent successfully"

    def test_kafka_producer_multiple_heartbeats(self, kafka_producer):
        """测试发送多个心跳消息"""
        node_id = "test_kafka_multi_heartbeat"

        # 发送3个心跳
        for i in range(3):
            heartbeat_message = {
                "type": "heartbeat",
                "node_id": node_id,
                "sequence": i,
                "timestamp": datetime.now().isoformat()
            }

            result = kafka_producer.send("ginkgo.live.system.events", heartbeat_message)
            assert result is True, f"Heartbeat {i} should be sent successfully"

            # 短暂延迟
            time.sleep(0.1)

    def test_kafka_async_send_performance(self, kafka_producer):
        """测试Kafka异步发送性能"""
        node_id = "test_kafka_perf"
        message_count = 10

        start_time = time.time()

        # 异步发送多条心跳消息
        for i in range(message_count):
            heartbeat_message = {
                "type": "heartbeat",
                "node_id": node_id,
                "sequence": i,
                "timestamp": datetime.now().isoformat()
            }

            kafka_producer.send_async("ginkgo.live.system.events", heartbeat_message)

        # flush确保所有消息发送
        kafka_producer.flush()

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        # 验证性能（应该在1秒内完成）
        assert elapsed_ms < 1000, f"Sending {message_count} heartbeats should take < 1s, took {elapsed_ms:.2f}ms"

        print(f"Kafka async send performance: {message_count} messages in {elapsed_ms:.2f}ms")
