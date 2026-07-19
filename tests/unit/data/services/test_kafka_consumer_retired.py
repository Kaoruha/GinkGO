"""
#6736: KafkaService 消费 worker 模型（零活调用方，含阻塞迭代器 stop 语义 bug）退役。

#6726 已删 threading main_control 远控消费链，#6727 已删 redis 进程 helper 与
ginkgo status 残留输出。本 issue 收尾 KafkaService 自身的消费 worker 模型：
subscribe_topic / start_consuming / stop_consuming / unsubscribe_topic / _consumer_worker
+ 状态字段 + 连带的散落执行类死方法（publish_batch_messages / reset_statistics /
send_worker_kill_signal）+ KafkaCRUD.consume_with_callback（阻塞迭代器 bug 所在，
唯一调用方是死的 _consumer_worker）。

主力消费（DataWorker / paper_trading_worker / execution_node）绕过 KafkaService
直接用 drivers 层 GinkgoConsumer.poll，本就不依赖这套消费模型——blast radius = 0。
保留所有状态/查询接口（get_* / count / validate / check_integrity）与生产/信号路径。
"""
import pytest

from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.crud.kafka_crud import KafkaCRUD
from ginkgo.libs.core.threading import GinkgoThreadManager


# ===========================================================================
# KafkaService 消费 worker 模型退役
# ===========================================================================

class TestKafkaServiceConsumerWorkerRetired:
    """消费 worker 模型零活调用方（#6726 删 threading 链后唯一外部入口已断），应移除。"""

    @pytest.mark.unit
    def test_subscription_methods_removed(self):
        """subscribe_topic / start_consuming / stop_consuming / unsubscribe_topic 已移除。"""
        assert not hasattr(KafkaService, "subscribe_topic")
        assert not hasattr(KafkaService, "start_consuming")
        assert not hasattr(KafkaService, "stop_consuming")
        assert not hasattr(KafkaService, "unsubscribe_topic")

    @pytest.mark.unit
    def test_consumer_worker_removed(self):
        """_consumer_worker（threading.Thread target，含阻塞迭代器调用）已移除。"""
        assert not hasattr(KafkaService, "_consumer_worker")

    @pytest.mark.unit
    def test_list_active_subscriptions_removed(self):
        """list_active_subscriptions 仅基于消费字段，消费模型删后成孤儿，应移除。"""
        assert not hasattr(KafkaService, "list_active_subscriptions")

    @pytest.mark.unit
    def test_consumer_state_fields_not_initialized(self, kafka_service):
        """__init__ 不再初始化 _message_handlers / _consumer_threads / _stop_events。"""
        assert not hasattr(kafka_service, "_message_handlers")
        assert not hasattr(kafka_service, "_consumer_threads")
        assert not hasattr(kafka_service, "_stop_events")


# ===========================================================================
# KafkaService 散落执行类死方法退役
# ===========================================================================

class TestKafkaServiceDeadExecMethodsRetired:
    """零调用方的执行类死方法（非状态/查询接口）应移除。"""

    @pytest.mark.unit
    def test_publish_batch_messages_removed(self):
        """publish_batch_messages（批量发布执行类，零调用）已移除。"""
        assert not hasattr(KafkaService, "publish_batch_messages")

    @pytest.mark.unit
    def test_reset_statistics_removed(self):
        """reset_statistics（重置统计执行类，零调用）已移除。"""
        assert not hasattr(KafkaService, "reset_statistics")

    @pytest.mark.unit
    def test_send_worker_kill_signal_removed(self):
        """send_worker_kill_signal（双死：零调用 + DataWorker 无 type==kill 分支）已移除。"""
        assert not hasattr(KafkaService, "send_worker_kill_signal")


# ===========================================================================
# KafkaCRUD consume_with_callback 退役
# ===========================================================================

class TestKafkaCRUDConsumeWithCallbackRetired:
    """consume_with_callback（裸阻塞迭代器，唯一调用方是死的 _consumer_worker）。"""

    @pytest.mark.unit
    def test_consume_with_callback_removed(self):
        assert not hasattr(KafkaCRUD, "consume_with_callback")


# ===========================================================================
# threading.py 孤儿清理（#6726 漏删）
# ===========================================================================

class TestThreadingOrphansRetired:
    """#6726 删了 get_proc_status/kill_proc 的唯一调用方（main_status/watch_dog_status
    property / kill_maincontrol / kill_watch_dog）却漏删本体，二者成孤儿，应移除。"""

    @pytest.mark.unit
    def test_get_proc_status_removed(self):
        assert not hasattr(GinkgoThreadManager, "get_proc_status")

    @pytest.mark.unit
    def test_kill_proc_removed(self):
        assert not hasattr(GinkgoThreadManager, "kill_proc")


# ===========================================================================
# fixtures
# ===========================================================================

@pytest.fixture
def kafka_service():
    return KafkaService()
