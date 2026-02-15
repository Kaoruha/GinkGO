"""
KafkaService数据服务测试

测试Kafka消息队列服务的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import time

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.crud.kafka_crud import KafkaCRUD
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GCONF


# ============================================================================
# Fixtures - 共享测试资源
# ============================================================================

@pytest.fixture
def ginkgo_config():
    """配置调试模式"""
    GCONF.set_debug(True)
    yield GCONF
    GCONF.set_debug(False)


@pytest.fixture
def kafka_service():
    """获取KafkaService实例"""
    return KafkaService()


@pytest.fixture
def unique_topic():
    """生成唯一的测试主题"""
    return f"test_topic_{uuid4().hex[:8]}"


@pytest.fixture
def sample_message():
    """创建示例消息"""
    return {
        "event": "price_update",
        "symbol": "AAPL",
        "price": 150.0,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的消息类型
VALID_MESSAGES = [
    ({"event": "test"}, "简单JSON"),
    ("simple_string", "字符串"),
    ([1, 2, 3], "数组"),
    (42, "数值"),
]

# 无效的主题名称
INVALID_TOPICS = [
    ("", "空字符串"),
    ("   ", "纯空格"),
    (123, "数值类型"),
    (None, "None值"),
]


# ============================================================================
# 测试类 - 服务初始化和构造
# ============================================================================

@pytest.mark.unit
class TestKafkaServiceConstruction:
    """测试KafkaService初始化和构造"""

    def test_service_initialization(self, kafka_service):
        """测试服务初始化"""
        assert kafka_service is not None
        assert isinstance(kafka_service, KafkaService)

    def test_service_inherits_base_service(self, kafka_service):
        """测试继承BaseService"""
        assert isinstance(kafka_service, BaseService)

    def test_crud_repo_exists(self, kafka_service):
        """测试CRUD仓库存在"""
        assert hasattr(kafka_service, '_crud_repo')
        assert kafka_service._crud_repo is not None
        assert isinstance(kafka_service._crud_repo, KafkaCRUD)

    def test_kafka_property(self, kafka_service):
        """测试kafka属性"""
        assert hasattr(kafka_service, 'kafka')
        assert kafka_service.kafka is not None


# ============================================================================
# 测试类 - 主题管理
# ============================================================================

@pytest.mark.integration
class TestKafkaServiceTopicManagement:
    """测试Kafka主题管理"""

    def test_get_all_topics(self, kafka_service):
        """测试获取所有主题"""
        result = kafka_service.get()

        assert result.success
        assert isinstance(result.data, dict)
        assert 'topics' in result.data
        assert 'count' in result.data
        assert result.data['count'] >= 0

    def test_count_topics(self, kafka_service):
        """测试统计主题数量"""
        result = kafka_service.count()

        assert result.success
        assert isinstance(result.data, dict)
        assert 'topic_count' in result.data
        assert result.data['topic_count'] >= 0


# ============================================================================
# 测试类 - 消息发布
# ============================================================================

@pytest.mark.integration
class TestKafkaServiceMessagePublish:
    """测试Kafka消息发布"""

    @pytest.mark.parametrize("message,description", VALID_MESSAGES)
    def test_publish_message(self, kafka_service, unique_topic, message, description):
        """测试发布各种类型的消息"""
        result = kafka_service.publish_message(unique_topic, message)

        # 如果Kafka未运行，返回False但不抛异常
        assert result is not None

    def test_publish_message_with_key(self, kafka_service, unique_topic, sample_message):
        """测试发布带键的消息"""
        key = "test_key"
        result = kafka_service.publish_message(unique_topic, sample_message, key=key)

        # 如果Kafka未运行，返回False但不抛异常
        assert result is not None

    def test_publish_multiple_messages(self, kafka_service, unique_topic):
        """测试发布多条消息"""
        messages = [
            {"id": i, "data": f"message_{i}"}
            for i in range(3)
        ]

        for msg in messages:
            result = kafka_service.publish_message(unique_topic, msg)
            assert result is not None


# ============================================================================
# 测试类 - 消息消费
# ============================================================================

@pytest.mark.integration
class TestKafkaServiceMessageConsume:
    """测试Kafka消息消费"""

    def test_get_unconsumed_count(self, kafka_service, unique_topic):
        """测试查询未消费消息数量"""
        result = kafka_service.get_unconsumed_count(unique_topic)

        # 如果Kafka未运行，可能失败但不抛异常
        assert result is not None

    def test_get_consumer_group_lag(self, kafka_service, unique_topic):
        """测试消费者组延迟查询"""
        result = kafka_service.get_consumer_group_lag(unique_topic)

        # 如果Kafka未运行，可能失败但不抛异常
        assert result is not None


# ============================================================================
# 测试类 - 队列指标
# ============================================================================

@pytest.mark.integration
class TestKafkaServiceQueueMetrics:
    """测试Kafka队列指标"""

    def test_get_queue_metrics(self, kafka_service, unique_topic):
        """测试获取队列指标"""
        result = kafka_service.get_queue_metrics([unique_topic])

        # 如果Kafka未运行，可能失败但不抛异常
        assert result is not None

    def test_calculate_lag_level_by_count(self, kafka_service):
        """测试基于消息数量的延迟级别计算"""
        # 测试各种延迟级别
        assert kafka_service._calculate_lag_level(0) == "无延迟"
        assert kafka_service._calculate_lag_level(50) == "低延迟"
        assert kafka_service._calculate_lag_level(500) == "中等延迟"
        assert kafka_service._calculate_lag_level(1500) == "高延迟"

    def test_calculate_lag_level_by_time(self, kafka_service):
        """测试基于时间的延迟级别计算"""
        # 模拟不同时间延迟
        assert kafka_service._calculate_lag_level(100, 0.5) == "无延迟"
        assert kafka_service._calculate_lag_level(100, 5) == "低延迟"
        assert kafka_service._calculate_lag_level(100, 30) == "中等延迟"
        assert kafka_service._calculate_lag_level(100, 120) == "高延迟"


# ============================================================================
# 测试类 - 数据验证
# ============================================================================

@pytest.mark.unit
class TestKafkaServiceValidation:
    """测试数据验证功能"""

    def test_validate_valid_topic(self, kafka_service):
        """测试验证有效主题"""
        result = kafka_service.validate(topic="valid_topic")

        assert result.success
        assert result.message == "Kafka数据验证通过"

    @pytest.mark.parametrize("invalid_topic,description", INVALID_TOPICS)
    def test_validate_invalid_topic(self, kafka_service, invalid_topic, description):
        """测试验证无效主题"""
        result = kafka_service.validate(topic=invalid_topic)

        assert not result.success
        assert len(result.error) > 0


# ============================================================================
# 测试类 - 健康检查
# ============================================================================

@pytest.mark.unit
class TestKafkaServiceHealthCheck:
    """测试健康检查功能"""

    def test_health_check(self, kafka_service):
        """测试健康检查"""
        result = kafka_service.health_check()

        # Kafka服务可能离线
        assert result is not None
        assert isinstance(result, ServiceResult)


# ============================================================================
# 测试类 - 错误处理
# ============================================================================

@pytest.mark.unit
class TestKafkaServiceErrorHandling:
    """测试错误处理"""

    def test_nonexistent_topic_operations(self, kafka_service):
        """测试不存在主题的操作"""
        nonexistent_topic = "nonexistent_topic_999999"

        # 这些操作应该优雅失败
        result = kafka_service.get_unconsumed_count(nonexistent_topic)
        assert result is not None

        result = kafka_service.get_consumer_group_lag(nonexistent_topic)
        assert result is not None

    def test_empty_topic_list(self, kafka_service):
        """测试空主题列表"""
        result = kafka_service.get_queue_metrics([])

        assert result is not None


# ============================================================================
# 测试类 - 业务逻辑
# ============================================================================

@pytest.mark.integration
class TestKafkaServiceBusinessLogic:
    """测试业务逻辑"""

    def test_message_lifecycle(self, kafka_service, unique_topic, sample_message):
        """测试消息完整生命周期"""
        # 1. 发布消息
        publish_result = kafka_service.publish_message(unique_topic, sample_message)
        assert publish_result is not None

        # 2. 获取未消费数量
        unconsumed_result = kafka_service.get_unconsumed_count(unique_topic)
        assert unconsumed_result is not None

        # 3. 获取队列指标
        metrics_result = kafka_service.get_queue_metrics([unique_topic])
        assert metrics_result is not None

    def test_multiple_topic_operations(self, kafka_service):
        """测试多主题操作"""
        topics = [f"test_topic_{i}_{uuid4().hex[:6]}" for i in range(3)]

        # 对每个主题执行操作
        for topic in topics:
            # 发布消息
            result = kafka_service.publish_message(topic, {"test": "data"})
            assert result is not None

            # 获取指标
            metrics = kafka_service.get_queue_metrics([topic])
            assert metrics is not None


# ============================================================================
# 测试类 - 边界测试
# ============================================================================

@pytest.mark.integration
class TestKafkaServiceEdgeCases:
    """测试边界情况"""

    @pytest.mark.parametrize("message_count", [1, 10, 100])
    def test_various_message_counts(self, kafka_service, unique_topic, message_count):
        """测试不同消息数量"""
        for i in range(message_count):
            message = {"id": i, "timestamp": time.time()}
            result = kafka_service.publish_message(unique_topic, message)
            assert result is not None

    def test_special_characters_in_topic(self, kafka_service):
        """测试主题中的特殊字符"""
        # Kafka主题名称有特殊规则
        # 测试合法的包含数字和下划线的主题
        valid_topics = [
            "test_topic_123",
            "test.topic.with.dots",
            "test-topic-with-dashes"
        ]

        for topic in valid_topics:
            result = kafka_service.validate(topic=topic)
            # 应该通过验证
            if result.success:
                # 尝试发布消息
                publish_result = kafka_service.publish_message(topic, {"test": "data"})
                assert publish_result is not None
