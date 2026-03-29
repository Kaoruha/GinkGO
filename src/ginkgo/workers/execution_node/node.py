# Upstream: LiveCore（通过Kafka接收市场数据和订单回报）
# Downstream: Portfolio（调用事件处理方法）、Kafka（发布订单提交）
# Role: ExecutionNode执行节点，运行多个Portfolio实例，从Kafka接收事件并路由到Portfolio


"""
ExecutionNode执行节点

ExecutionNode是Portfolio的运行容器，负责：
- 运行多个Portfolio实例（无数量限制）
- 从数据库加载Portfolio配置并创建实例
- 从Kafka订阅market.data和orders.feedback topic
- 使用InterestMap路由事件到对应的PortfolioProcessor
- 收集Portfolio生成的订单并提交到Kafka orders.submission topic
- 上报心跳和状态到Redis

核心架构：单Kafka消费线程 + 多PortfolioProcessor处理线程
- Kafka消费线程：快速消费消息，根据InterestMap路由到Portfolio Queue
- PortfolioProcessor线程：每个Portfolio独立线程，从Queue取消息并处理
- InterestMap：映射股票代码到订阅的Portfolio ID列表

心跳和调度命令处理已拆分到独立模块：
- HeartbeatManager: 心跳上报、指标更新、状态同步
- SchedulerCommandHandler: 调度命令（reload/migrate/pause/resume/shutdown）

云原生设计（Phase 5）：
- ✅ 状态在内存（重启后清空）
- ✅ Scheduler 自动检测离线（心跳 TTL=30s）
- ✅ Scheduler 自动重新分配 Portfolio
- ✅ ExecutionNode 重新上线后等待新任务
"""

from typing import Dict, Optional, TYPE_CHECKING, List
from threading import Thread, Lock, Event
from queue import Queue
from datetime import datetime
import time
import logging

from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor
from ginkgo.workers.execution_node.interest_map import InterestMap
from ginkgo.workers.execution_node.heartbeat_manager import HeartbeatManager
from ginkgo.workers.execution_node.scheduler_command_handler import SchedulerCommandHandler
from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer, GinkgoProducer
from ginkgo import services
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG

# 获取日志记录器
logger = logging.getLogger(__name__)


class ExecutionNode:
    """ExecutionNode执行节点，运行多个Portfolio实例"""

    def __init__(self, node_id: str):
        """
        初始化ExecutionNode（云原生无状态设计）

        Args:
            node_id: 节点唯一标识

        云原生设计原则：
        - 状态在内存（重启后清空）
        - Scheduler 自动检测离线（心跳 TTL=30s）
        - Scheduler 自动重新分配 Portfolio
        - ExecutionNode 重新上线后等待新任务
        """
        self.node_id = node_id

        # Portfolio管理：{portfolio_id: PortfolioProcessor}
        # 注意：这些对象只在运行时存在，不持久化
        self.portfolios: Dict[str, PortfolioProcessor] = {}
        self.portfolio_lock = Lock()

        # Portfolio实例持有：{portfolio_id: PortfolioLive}
        # ExecutionNode持有唯一实例，PortfolioProcessor持有引用
        self._portfolio_instances: Dict[str, "PortfolioLive"] = {}

        # InterestMap：股票代码到Portfolio ID列表的映射
        # O(1)查询订阅某股票的Portfolio列表
        self.interest_map: InterestMap = InterestMap()

        # Kafka消费者
        self.market_data_consumer: Optional[GinkgoConsumer] = None
        self.order_feedback_consumer: Optional[GinkgoConsumer] = None
        self.schedule_updates_consumer: Optional[GinkgoConsumer] = None

        # Kafka生产者（订单提交）
        self.order_producer = GinkgoProducer()

        # 运行状态（同时存储到Redis）
        self.is_running = False
        self.is_paused = False
        self.should_stop = False

        # 消费线程
        self.market_data_thread: Optional[Thread] = None
        self.order_feedback_thread: Optional[Thread] = None
        self.schedule_updates_thread: Optional[Thread] = None

        # 心跳线程
        self.heartbeat_thread: Optional[Thread] = None
        self.heartbeat_interval = 10  # 10秒发送一次心跳
        self.heartbeat_ttl = 30  # 心跳TTL 30秒

        # 背压统计
        self.backpressure_count = 0
        self.dropped_event_count = 0
        self.total_event_count = 0

        # 节点元数据
        self.max_portfolios = 5  # 最大可运行的Portfolio数量

        # 设置日志类别（用于Vector路由）
        GLOG.set_log_category("component")
        self.started_at: Optional[str] = None

        # output_queue listener 线程追踪
        self.output_queue_threads: Dict[str, Thread] = {}  # {portfolio_id: Thread}
        self.output_queue_stop_events: Dict[str, Event] = {}  # {portfolio_id: Event}

        # Portfolio队列管理（ExecutionNode持有所有队列）
        self.input_queues: Dict[str, Queue] = {}  # {portfolio_id: Queue}
        self.output_queues: Dict[str, Queue] = {}  # {portfolio_id: Queue}

        # 初始化子模块（心跳管理 + 调度命令处理）
        self._heartbeat_manager = HeartbeatManager(self)
        self._command_handler = SchedulerCommandHandler(self)

    def start(self):
        """
        启动 ExecutionNode（支持重启）

        架构原则：
        - 单向控制流：Scheduler 是唯一的控制中心
        - ExecutionNode 被动接收 Kafka 命令（portfolio.migrate, node.pause, node.resume）
        - 心跳机制让 Scheduler 发现节点，但所有分配决策由 Scheduler 做出

        重启支持：
        - ✅ 支持重新启动（正常停止后可重启）
        - ✅ 状态在内存（重启后清空）
        - ✅ 心跳机制（TTL=30s）实现自动故障检测
        - ✅ 单向控制：Scheduler → Kafka → ExecutionNode

        启动流程：
        1. 检查是否已运行
        2. 重置停止标志（支持重启）
        3. 清理旧的心跳数据
        4. 上报心跳到 Redis（让 Scheduler 发现节点）
        5. 启动心跳线程（维持节点在线状态）
        6. 启动调度更新线程（接收 Scheduler 命令）
        7. 启动市场数据消费线程（接收 PriceUpdate 事件）
        8. 启动订单回报消费线程（接收 OrderFeedback 事件）

        Raises:
            RuntimeError: 如果节点已经在运行
        """
        if self.is_running:
            raise RuntimeError(f"ExecutionNode {self.node_id} is already running")

        # 检查node_id是否已被其他实例使用
        if self._heartbeat_manager.is_node_id_in_use():
            GLOG.ERROR(f"\n[ERROR] ExecutionNode {self.node_id} is already in use by another process!")
            GLOG.ERROR(f"[ERROR] Cannot start duplicate node_id.")
            GLOG.ERROR(f"\nPossible solutions:")
            GLOG.ERROR(f"  1. Stop the other ExecutionNode instance (Ctrl+C)")
            GLOG.ERROR(f"  2. Use a different node_id: ginkgo execution start --node-id <new_id>")
            GLOG.ERROR(f"  3. Cleanup stale data: ginkgo execution cleanup --node-id {self.node_id}")
            raise RuntimeError(f"ExecutionNode {self.node_id} is already in use")

        # 重置停止标志（支持重启）
        self.should_stop = False

        # 设置运行标志
        self.is_running = True
        self.started_at = datetime.now().isoformat()

        if self.is_paused:
            GLOG.INFO(f"Resuming ExecutionNode {self.node_id} (was paused)")
            self.is_paused = False
        else:
            GLOG.INFO(f"Starting ExecutionNode {self.node_id}")

        # 0. 清理旧的心跳和指标数据（防止节点异常重启后残留）
        self._heartbeat_manager.cleanup_old_heartbeat_data()

        # 1. 立即发送心跳（让 Scheduler 发现节点）
        self._heartbeat_manager.send_heartbeat()

        # 2. 启动心跳上报线程（维持节点在线状态）
        self._start_heartbeat_thread()

        # 3. 启动调度更新订阅线程（接收 Scheduler 命令：pause/resume/migrate）
        self._start_schedule_updates_thread()

        # 4. 启动市场数据消费线程（接收 EventPriceUpdate）
        self._start_market_data_consumer_thread()

        # 5. 启动订单回报消费线程（接收 EventOrderPartiallyFilled）
        self._start_order_feedback_consumer_thread()

        GLOG.INFO(f"[INFO] ExecutionNode {self.node_id} started")

        # 发送启动通知
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                f"执行节点 {self.node_id} 已启动",
                level="INFO",
                module="ExecutionNode",
                details={
                    "节点ID": self.node_id,
                    "最大Portfolio数": self.max_portfolios,
                    "心跳间隔": f"{self.heartbeat_interval}秒"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")
        GLOG.INFO(f"[INFO] Portfolio count: {len(self.portfolios)} (waiting for Scheduler)")
        GLOG.INFO(f"[INFO] Node is ready to receive portfolio.migrate commands from Scheduler")

    def stop(self):
        """
        停止ExecutionNode - 优雅关闭流程

        核心策略：
        1. 先关闭 Consumer，停止拉取新消息
        2. 等待 Portfolio 消费完 input_queue
        3. 等待 output_queue 发送完毕
        4. Portfolio 彻底关闭
        5. 等待所有线程退出
        6. 上报状态、清理资源
        """
        if not self.is_running:
            GLOG.WARN(f"[WARNING] ExecutionNode {self.node_id} is not running")
            return

        GLOG.INFO(f"Stopping ExecutionNode {self.node_id}")

        # 0. 设置停止标志（通知所有线程）
        self.should_stop = True
        self.is_running = False

        # 1. 关闭 Kafka Consumers - 切断新消息来源
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 1 步：关闭 Kafka Consumers（停止拉取新消息）")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        if self.market_data_consumer:
            try:
                self.market_data_consumer.close()
                GLOG.INFO(f"[INFO]   ✅ Market data consumer closed")
                GLOG.INFO(f"[INFO]      └─ 不再拉取 Price Update")
                GLOG.INFO(f"[INFO]      └─ 不会触发策略生成新订单")
            except Exception as e:
                GLOG.ERROR(f"[ERROR]   ✗ Error closing market data consumer: {e}")

        if self.order_feedback_consumer:
            try:
                self.order_feedback_consumer.close()
                GLOG.INFO(f"[INFO]   ✅ Order feedback consumer closed")
                GLOG.INFO(f"[INFO]      └─ 不再拉取 Order Feedback")
                GLOG.INFO(f"[INFO]      └─ 不会触发风控生成新订单")
            except Exception as e:
                GLOG.ERROR(f"[ERROR]   ✗ Error closing order feedback consumer: {e}")

        if self.schedule_updates_consumer:
            try:
                self.schedule_updates_consumer.close()
                GLOG.INFO(f"[INFO]   ✅ Schedule updates consumer closed")
                GLOG.INFO(f"[INFO]      └─ 不再接收调度命令")
            except Exception as e:
                GLOG.ERROR(f"[ERROR]   ✗ Error closing schedule updates consumer: {e}")

        # 2. 等待 Portfolio 消费完 input_queue
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 2 步：等待 Portfolio 处理完 input_queue 中的消息")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        with self.portfolio_lock:
            processors = list(self.portfolios.values())

        if processors:
            wait_start = time.time()
            while time.time() - wait_start < 5:  # 最多等待 5 秒
                total_remaining = 0
                for processor in processors:
                    remaining = processor.get_queue_size()
                    total_remaining += remaining

                if total_remaining == 0:
                    GLOG.INFO(f"[INFO]   ✅ 所有 input_queue 已清空")
                    GLOG.INFO(f"[INFO]      └─ 已拉取的消息已处理完毕")
                    break
                else:
                    GLOG.DEBUG(f"  等待 {total_remaining} 个事件处理完成...")
                    time.sleep(0.1)
            else:
                if total_remaining > 0:
                    GLOG.WARN(f"[WARNING] ⚠️  超时，仍有 {total_remaining} 个事件未处理")
        else:
            GLOG.INFO(f"[INFO]   ℹ️  没有 Portfolio 运行，跳过")

        # 3. 等待 output_queue 发送完毕并停止 listener
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 3 步：等待 output_queue 中的订单发送完成")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        if self.output_queue_threads:
            GLOG.INFO(f"[INFO]   停止 {len(self.output_queue_threads)} output queue listeners...")

            # 设置停止事件
            for stop_event in self.output_queue_stop_events.values():
                stop_event.set()

            # 等待所有 listener 完成
            for portfolio_id, thread in self.output_queue_threads.items():
                if thread.is_alive():
                    GLOG.DEBUG(f"  等待 output_queue listener ({portfolio_id[:8]}...) 完成...")
                    thread.join(timeout=5)
                    if thread.is_alive():
                        GLOG.WARN(f"[WARNING]   ⚠️  Output queue listener ({portfolio_id[:8]}...) 未能在 5 秒内完成")
                    else:
                        GLOG.INFO(f"[INFO]   ✅ Output queue listener ({portfolio_id[:8]}...) 已完成")
                else:
                    GLOG.INFO(f"[INFO]   ✅ Output queue listener ({portfolio_id[:8]}...) 已停止")

            # 清空追踪
            self.output_queue_threads.clear()
            self.output_queue_stop_events.clear()
            GLOG.INFO(f"[INFO]   ✅ 所有 output_queue listener 已停止")
        else:
            GLOG.INFO(f"[INFO]   ℹ️  没有 output_queue listener 运行，跳过")

        # 4. 关闭 Producer - 确保所有订单已发送
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 4 步：关闭 Producer（确保所有订单已发送）")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        if hasattr(self, 'order_producer') and self.order_producer:
            try:
                self.order_producer.close()
                GLOG.INFO(f"[INFO]   ✅ Order producer closed")
                GLOG.INFO(f"[INFO]      └─ flush() 确保所有订单已发送")
                GLOG.INFO(f"[INFO]      └─ close() 关闭连接")
            except Exception as e:
                GLOG.ERROR(f"[ERROR]   ✗ Error closing order producer: {e}")
        else:
            GLOG.INFO(f"[INFO]   ℹ️  Order producer 不存在，跳过")

        # 5. 等待所有 Portfolio 关闭
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 5 步：等待所有 PortfolioProcessor 线程退出")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        with self.portfolio_lock:
            processors = list(self.portfolios.values())

        for processor in processors:
            if processor.is_alive():
                portfolio_id_short = processor.portfolio_id[:8] if len(processor.portfolio_id) > 8 else processor.portfolio_id
                GLOG.DEBUG(f"  等待 Portfolio ({portfolio_id_short}...) 退出...")
                processor.join(timeout=5)
                if processor.is_alive():
                    GLOG.WARN(f"[WARNING]   ⚠️  Portfolio ({portfolio_id_short}...) 未能在 5 秒内退出")
                else:
                    GLOG.INFO(f"[INFO]   ✅ Portfolio ({portfolio_id_short}...) 已退出")
            else:
                portfolio_id_short = processor.portfolio_id[:8] if len(processor.portfolio_id) > 8 else processor.portfolio_id
                GLOG.INFO(f"[INFO]   ✅ Portfolio ({portfolio_id_short}...) 已停止")

        if processors:
            GLOG.INFO(f"[INFO]   ✅ 所有 PortfolioProcessor 线程已退出")
        else:
            GLOG.INFO(f"[INFO]   ℹ️  没有 PortfolioProcessor 运行，跳过")

        # 6. 等待其他线程退出
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 6 步：等待其他线程退出")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        threads_to_wait = [
            ("Market data thread", self.market_data_thread),
            ("Order feedback thread", self.order_feedback_thread),
            ("Schedule updates thread", self.schedule_updates_thread),
        ]

        for name, thread in threads_to_wait:
            if thread and thread.is_alive():
                GLOG.DEBUG(f"  等待 {name} 退出...")
                thread.join(timeout=5)
                if not thread.is_alive():
                    GLOG.INFO(f"[INFO]   ✅ {name} 已退出")
                else:
                    GLOG.WARN(f"[WARNING]   ⚠️  {name} 未能在 5 秒内退出")

        # 7. 停止心跳线程
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 7 步：停止心跳线程")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
            if not self.heartbeat_thread.is_alive():
                GLOG.INFO(f"[INFO]   ✅ Heartbeat thread 已退出")
            else:
                GLOG.WARN(f"[WARNING]   ⚠️  Heartbeat thread 未能在 5 秒内退出")

        # 8. 清理 Redis（上报离线状态）
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 8 步：清理 Redis 数据（上报离线状态）")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        try:
            redis_client = self._get_redis_client()
            if redis_client:
                from ginkgo.data.redis_schema import RedisKeyBuilder
                heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(self.node_id)
                metrics_key = f"node:metrics:{self.node_id}"

                deleted_heartbeat = redis_client.delete(heartbeat_key)
                if deleted_heartbeat:
                    GLOG.INFO(f"[INFO]   ✅ 心跳数据已删除（Scheduler 将检测到节点离线）")

                deleted_metrics = redis_client.delete(metrics_key)
                if deleted_metrics:
                    GLOG.INFO(f"[INFO]   ✅ 指标数据已删除")

        except Exception as e:
            GLOG.ERROR(f"[ERROR]   ✗ 清理 Redis 失败: {e}")

        # 9. 清空内存
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] 第 9 步：清空内存数据结构")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        with self.portfolio_lock:
            portfolio_count = len(self.portfolios)
            self.portfolios.clear()

        self.input_queues.clear()
        self.output_queues.clear()

        GLOG.INFO(f"[INFO]   ✅ 内存已清空 (portfolios: {portfolio_count}, queues释放)")

        # 10. 完成
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")
        GLOG.INFO(f"[INFO] ✅ ExecutionNode {self.node_id} 已完全停止")
        GLOG.INFO(f"[INFO] ══════════════════════════════════════════════")

        # 发送优雅退出通知
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                f"执行节点 {self.node_id} 已优雅退出",
                level="SUCCESS",  # 使用绿色表示成功退出
                module="ExecutionNode",
                details={
                    "节点ID": self.node_id,
                    "关闭的Portfolio数": portfolio_count,
                    "运行时长": self._get_uptime()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send shutdown notification: {e}")

    def load_portfolio(self, portfolio_id: str) -> bool:
        """
        从数据库加载Portfolio配置并创建实例

        架构说明（单向控制流）：
        - 此方法只应被 Scheduler 通过 Kafka 的 portfolio.migrate 命令调用
        - ExecutionNode 被动接收命令，不主动加载 Portfolio
        - 所有 Portfolio 分配决策由 Scheduler 中心调度控制

        控制流：
        Scheduler → Redis schedule:plan → Kafka schedule.updates → ExecutionNode.load_portfolio()

        Args:
            portfolio_id: Portfolio ID（UUID）

        Returns:
            bool: 加载成功返回True

        Raises:
            ValueError: Portfolio不是实盘Portfolio或不存在
        """
        try:
            logger.info(f"[LOAD] Loading portfolio {portfolio_id[:8]} from database...")

            # 1. 通过PortfolioService从数据库查询Portfolio配置
            portfolio_service = services.data.portfolio_service()
            portfolio_result = portfolio_service.get(portfolio_id=portfolio_id)

            if not portfolio_result.is_success():
                logger.error(f"[LOAD] Failed to load portfolio {portfolio_id[:8]}: {portfolio_result.error}")
                return False

            # portfolio_result.data 是MPortfolio对象列表
            portfolios = portfolio_result.data
            if not portfolios or len(portfolios) == 0:
                logger.error(f"[LOAD] Portfolio {portfolio_id[:8]} not found in database")
                return False

            portfolio_model = portfolios[0]
            logger.info(f"[LOAD] Found portfolio: {portfolio_model.name} (is_live={portfolio_model.is_live})")

            # 2. 验证is_live=True
            if not portfolio_model.is_live:
                raise ValueError(f"Portfolio {portfolio_id} is not a live portfolio")

            # 3. 使用PortfolioService加载完整的Portfolio（包含所有组件）
            logger.info(f"[LOAD] Loading portfolio with all components via PortfolioService...")
            load_result = portfolio_service.load_portfolio_with_components(portfolio_id)

            if not load_result.is_success:
                logger.error(f"[LOAD] Failed to load portfolio with components: {load_result.error}")
                return False

            portfolio = load_result.data
            logger.info(f"[LOAD] ✓ Portfolio loaded with all components")

            # 4. 恢复 Portfolio 状态（从数据库）
            logger.info(f"[LOAD] Restoring portfolio state from database...")
            self._restore_portfolio_state(portfolio, portfolio_id)

            with self.portfolio_lock:
                # 5. 检查是否已加载
                if portfolio_id in self.portfolios:
                    logger.warning(f"[LOAD] Portfolio {portfolio_id[:8]} already loaded")
                    return False

                # 6. 保存Portfolio实例（ExecutionNode持有唯一实例）
                self._portfolio_instances[portfolio_id] = portfolio
                logger.info(f"[LOAD] Portfolio instance saved")

                # 7. 创建Input Queue和Output Queue（ExecutionNode持有所有队列）
                logger.info(f"[LOAD] Creating dual queues (input/output)...")
                input_queue = Queue(maxsize=1000)
                output_queue = Queue(maxsize=1000)

                # 保存到ExecutionNode的队列字典
                self.input_queues[portfolio_id] = input_queue
                self.output_queues[portfolio_id] = output_queue

                # 8. 创建PortfolioProcessor（传入队列引用）
                logger.info(f"[LOAD] Creating PortfolioProcessor...")
                processor = PortfolioProcessor(
                    portfolio=portfolio,
                    input_queue=input_queue,
                    output_queue=output_queue,
                    max_queue_size=1000
                )

                # 9. 启动output_queue监听器（ExecutionNode负责序列化并发Kafka）
                logger.info(f"[LOAD] Starting output queue listener...")
                self._start_output_queue_listener(output_queue, portfolio_id)

                # 10. 启动Processor
                logger.info(f"[LOAD] Starting PortfolioProcessor thread...")
                processor.start()

                # 11. 注册到ExecutionNode
                self.portfolios[portfolio_id] = processor
                logger.info(f"[LOAD] PortfolioProcessor registered")

                # 12. 添加到InterestMap（Phase 4实现）
                # 获取Portfolio订阅的股票代码列表
                logger.info(f"[LOAD] Setting up interest map subscriptions...")
                subscribed_codes = self._get_subscribed_codes(portfolio)
                if subscribed_codes:
                    self.interest_map.add_portfolio(portfolio_id, subscribed_codes)
                    logger.info(f"[LOAD] Portfolio subscribed to {len(subscribed_codes)} codes: {subscribed_codes[:5]}...")
                else:
                    logger.warning(f"[LOAD] Portfolio has no subscribed codes, using default subscription")
                    # MVP阶段：使用默认订阅（前5个A股）
                    default_codes = ["000001.SZ", "000002.SZ", "000004.SZ", "600000.SH", "600036.SH"]
                    self.interest_map.add_portfolio(portfolio_id, default_codes)

                logger.info(f"[LOAD] ✓ Portfolio {portfolio_id[:8]} loaded successfully with dual queues")
                logger.info(f"[LOAD] Total portfolios on node: {len(self.portfolios)}")

                # 发送Portfolio加载成功通知
                try:
                    from ginkgo.notifier.core.notification_service import notify
                    notify(
                        f"Portfolio {portfolio_model.name} 已加载到节点 {self.node_id}",
                        level="INFO",
                        module="ExecutionNode",
                        details={
                            "Portfolio名称": portfolio_model.name,
                            "节点ID": self.node_id,
                            "订阅股票数": len(subscribed_codes) if subscribed_codes else 0,
                            "当前节点Portfolio数": len(self.portfolios)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send portfolio load notification: {e}")

                # TODO: 上报状态到Redis（Phase 5实现）
                return True

        except ValueError as e:
            logger.error(f"[LOAD] Validation error loading portfolio {portfolio_id[:8]}: {e}")
            return False
        except Exception as e:
            logger.error(f"[LOAD] Error loading portfolio {portfolio_id[:8]}: {e}")
            return False

    def _restore_portfolio_state(self, portfolio: "PortfolioLive", portfolio_id: str):
        """
        从数据库恢复Portfolio状态（MVP阶段：占位符实现）

        Phase 4需要恢复的状态：
        - 当前持仓（positions）
        - 活跃订单（active orders）
        - 现金余额（cash balance）
        - 已实现盈亏（realized P&L）

        MVP阶段：
        - 占位符实现，不恢复任何状态
        - Portfolio以全新状态启动
        - TODO: Phase 4实现完整的状态恢复逻辑

        Args:
            portfolio: Portfolio实例
            portfolio_id: Portfolio ID
        """
        logger.info(f"[RESTORE] Portfolio state restoration (MVP placeholder)")
        logger.info(f"[RESTORE] TODO: Implement state restoration in Phase 4")
        # MVP阶段：不恢复任何状态，Portfolio以全新状态启动
        # Phase 4需要：
        # 1. 从数据库读取当前持仓
        # 2. 从数据库读取活跃订单
        # 3. 恢复现金余额
        # 4. 恢复已实现盈亏

    def _get_subscribed_codes(self, portfolio: "PortfolioLive") -> List[str]:
        """
        获取Portfolio订阅的股票代码列表

        Args:
            portfolio: PortfolioLive实例

        Returns:
            List[str]: 订阅的股票代码列表

        MVP阶段：返回空列表，使用默认订阅
        Phase 4：从Portfolio的strategy中获取订阅列表
        """
        # MVP阶段：返回空，让load_portfolio使用默认订阅
        # Phase 4：可以从portfolio.strategy.get_subscribed_codes()获取
        # 或者从数据库配置中读取
        return []

    def unload_portfolio(self, portfolio_id: str) -> bool:
        """
        卸载Portfolio实例（优雅停止）

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 卸载成功返回True
        """
        with self.portfolio_lock:
            if portfolio_id not in self.portfolios:
                GLOG.WARN(f"[WARNING] Portfolio {portfolio_id} not found")
                return False

            # 优雅停止PortfolioProcessor（等待队列清空）
            processor = self.portfolios[portfolio_id]
            GLOG.INFO(f"[INFO] Unloading Portfolio {portfolio_id}...")
            processor.graceful_stop(timeout=30.0)

        # 在锁外等待 PortfolioProcessor 线程退出
        processor.join(timeout=10)
        if processor.is_alive():
            GLOG.WARN(f"[WARNING] Processor {portfolio_id} did not stop gracefully")
        else:
            GLOG.INFO(f"[INFO] Processor {portfolio_id} stopped")

        # 在锁外停止 output_queue listener 线程
        if portfolio_id in self.output_queue_stop_events:
            GLOG.INFO(f"[INFO] Stopping output queue listener for {portfolio_id}...")
            self.output_queue_stop_events[portfolio_id].set()

        if portfolio_id in self.output_queue_threads:
            thread = self.output_queue_threads[portfolio_id]
            thread.join(timeout=10)
            if thread.is_alive():
                GLOG.WARN(f"[WARNING] Output queue listener for {portfolio_id} did not stop gracefully")
            else:
                GLOG.INFO(f"[INFO] Output queue listener for {portfolio_id} stopped")

            del self.output_queue_threads[portfolio_id]
            del self.output_queue_stop_events[portfolio_id]

        # 再次获取锁，从ExecutionNode移除
        with self.portfolio_lock:
            del self.portfolios[portfolio_id]
            del self._portfolio_instances[portfolio_id]

            # 清理队列（ExecutionNode持有所有队列）
            if portfolio_id in self.input_queues:
                del self.input_queues[portfolio_id]
            if portfolio_id in self.output_queues:
                del self.output_queues[portfolio_id]

            GLOG.INFO(f"[INFO] Portfolio {portfolio_id} unloaded successfully")

            # 从InterestMap移除订阅（Phase 4实现）
            subscribed_codes = self.interest_map.get_all_subscriptions(portfolio_id)
            if subscribed_codes:
                self.interest_map.remove_portfolio(portfolio_id, subscribed_codes)
                GLOG.INFO(f"[INFO] Removed {len(subscribed_codes)} subscriptions from InterestMap")

            return True

    # ========================================================================
    # Kafka 消费线程
    # ========================================================================

    def _start_market_data_consumer_thread(self):
        """
        启动市场数据消费线程

        创建 Kafka Consumer 并启动消费线程，接收 EventPriceUpdate 事件
        """
        if self.market_data_thread and self.market_data_thread.is_alive():
            logger.warning(f"Market data consumer thread already running for node {self.node_id}")
            return

        # 创建Kafka消费者
        self.market_data_consumer = GinkgoConsumer(
            KafkaTopics.MARKET_DATA,
            group_id=f"execution_node_{self.node_id}"
        )

        # 启动消费线程
        self.market_data_thread = Thread(
            target=self._consume_market_data,
            daemon=True,
            name=f"market_data_{self.node_id}"
        )
        self.market_data_thread.start()
        logger.info(f"Market data consumer thread started for node {self.node_id}")

    def _start_order_feedback_consumer_thread(self):
        """
        启动订单回报消费线程

        创建 Kafka Consumer 并启动消费线程，接收 EventOrderPartiallyFilled 事件
        """
        if self.order_feedback_thread and self.order_feedback_thread.is_alive():
            logger.warning(f"Order feedback consumer thread already running for node {self.node_id}")
            return

        # 创建Kafka消费者
        self.order_feedback_consumer = GinkgoConsumer(
            KafkaTopics.ORDERS_FEEDBACK,
            group_id=f"execution_node_{self.node_id}"
        )

        # 启动消费线程
        self.order_feedback_thread = Thread(
            target=self._consume_order_feedback,
            daemon=True,
            name=f"order_feedback_{self.node_id}"
        )
        self.order_feedback_thread.start()
        logger.info(f"Order feedback consumer thread started for node {self.node_id}")

    def _consume_market_data(self):
        """
        消费市场数据线程（单线程快速消费和路由）

        线程职责：
        1. 从Kafka快速消费EventPriceUpdate消息
        2. 查询InterestMap获取订阅该股票的Portfolio列表
        3. 非阻塞分发消息到各PortfolioProcessor的Queue
        4. 消息成功放入队列后立即提交 offset
        """
        from ginkgo.trading.events.price_update import EventPriceUpdate

        GLOG.INFO(f"Market data consumer thread started for node {self.node_id}")

        while self.is_running:
            try:
                # 暂停状态：不处理新的事件
                if self.is_paused:
                    time.sleep(0.1)  # 短暂休眠避免CPU空转
                    continue

                # 检查 consumer 是否可用
                if self.market_data_consumer.consumer is None:
                    time.sleep(1)
                    continue

                for message in self.market_data_consumer.consumer:
                    if not self.is_running:
                        break

                    # 暂停状态检查
                    if self.is_paused:
                        break

                    event_data = message.value

                    # T069/T070: 恢复分布式追踪上下文（从 PriceUpdateDTO 的 trace_id/span_id）
                    trace_id = event_data.get('trace_id')
                    span_id = event_data.get('span_id')
                    if trace_id:
                        GLOG.set_trace_id(trace_id)
                    if span_id:
                        GLOG.set_span_id(span_id)

                    # 解析EventPriceUpdate
                    event = EventPriceUpdate(
                        code=event_data['code'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        price=event_data['price'],
                        volume=event_data.get('volume', 0)
                    )

                    # 路由到对应的Portfolio
                    self._route_event_to_portfolios(event)

                    # 消息成功放入队列后立即提交 offset
                    # 此时消息已经在 ExecutionNode 的内存中，不会丢失（除非进程崩溃）
                    self.market_data_consumer.commit()

            except Exception as e:
                if self.is_running:
                    time.sleep(1)  # 消费异常时延迟

        GLOG.INFO(f"Market data consumer thread stopped for node {self.node_id}")

    def _consume_order_feedback(self):
        """消费订单回报线程 - 消息成功放入队列后立即提交 offset"""
        from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled

        GLOG.INFO(f"Order feedback consumer thread started for node {self.node_id}")

        while self.is_running:
            try:
                # 暂停状态：不处理订单回报
                if self.is_paused:
                    time.sleep(0.1)  # 短暂休眠避免CPU空转
                    continue

                # 检查 consumer 是否可用
                if self.order_feedback_consumer.consumer is None:
                    time.sleep(1)
                    continue

                for message in self.order_feedback_consumer.consumer:
                    if not self.is_running:
                        break

                    # 暂停状态检查
                    if self.is_paused:
                        break

                    event_data = message.value

                    # 解析EventOrderPartiallyFilled
                    event = EventOrderPartiallyFilled(
                        order_id=event_data['order_id'],
                        code=event_data['code'],
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        direction=event_data['direction'],
                        filled_volume=event_data['filled_volume'],
                        filled_price=event_data['filled_price']
                    )

                    # 路由到对应的Portfolio
                    portfolio_id = event_data.get('portfolio_id')
                    if portfolio_id and portfolio_id in self.portfolios:
                        self.input_queues[portfolio_id].put(event)

                    # 消息成功放入队列后立即提交 offset
                    # 此时消息已经在 ExecutionNode 的内存中，不会丢失（除非进程崩溃）
                    self.order_feedback_consumer.commit()

            except Exception as e:
                if self.is_running:
                    time.sleep(1)  # 消费异常时延迟

        GLOG.INFO(f"Order feedback consumer thread stopped for node {self.node_id}")

    def _route_event_to_portfolios(self, event):
        """
        路由事件到对应的Portfolio（使用InterestMap优化）

        路由策略：
        1. 检查暂停状态（PAUSED时不处理事件）
        2. 使用InterestMap查询订阅该股票的Portfolio列表（O(1)查询）
        3. 使用短暂超时（100ms）尝试放入队列
        4. 超时后记录背压统计，继续尝试下一个Portfolio
        5. 丢弃时记录详细日志和队列使用率

        性能优势：
        - Phase 3（无InterestMap）：O(n) 遍历所有Portfolio
        - Phase 4（有InterestMap）：O(1) 直接查询订阅者

        Args:
            event: EventPriceUpdate事件
        """
        import queue

        # 暂停状态：不处理事件
        if self.is_paused:
            logger.debug(f"ExecutionNode {self.node_id} is paused, skipping event routing for {event.code}")
            return

        self.total_event_count += 1

        # Phase 4：使用InterestMap优化路由（O(1)查询）
        # 获取订阅该股票的Portfolio列表
        portfolio_ids = self.interest_map.get_portfolios(event.code)

        # 如果InterestMap中没有记录，回退到遍历所有Portfolio（兼容性）
        if not portfolio_ids:
            # MVP阶段兼容：遍历所有Portfolio
            with self.portfolio_lock:
                portfolio_ids = list(self.portfolios.keys())

        # 路由事件到订阅的Portfolio
        for portfolio_id in portfolio_ids:
            # 获取processor（需要线程安全）
            with self.portfolio_lock:
                if portfolio_id not in self.portfolios:
                    # Portfolio可能已卸载，跳过
                    continue
                processor = self.portfolios[portfolio_id]

            try:
                # 使用短暂超时（100ms）尝试放入队列
                # 优势：给队列处理时间，减少事件丢失
                self.input_queues[portfolio_id].put(event, block=True, timeout=0.1)

            except queue.Full:
                # 队列满，记录背压
                self.backpressure_count += 1
                self.dropped_event_count += 1

                # 获取队列使用率
                try:
                    queue_size = self.input_queues[portfolio_id].qsize()
                    # max_queue_size在创建队列时定义（1000）
                    queue_usage = queue_size / 1000 if 1000 > 0 else 0
                except Exception as e:
                    GLOG.ERROR(f"Failed to get queue size for portfolio {portfolio_id}: {e}")
                    queue_size = -1
                    queue_usage = -1

                # 记录详细背压日志
                GLOG.WARN(f"[BACKPRESSURE] Portfolio {portfolio_id} queue full")
                GLOG.WARN(f"  - Event: {event.code} at {event.timestamp if hasattr(event, 'timestamp') else 'N/A'}")
                GLOG.WARN(f"  - Queue: {queue_size}/1000 ({queue_usage*100:.1f}%)")
                GLOG.WARN(f"  - Total backpressure: {self.backpressure_count}, dropped: {self.dropped_event_count}")

                # TODO: Phase 4 - 发送背压告警到监控系统
                # self._send_backpressure_alert(portfolio_id, queue_usage, event)

            except Exception as e:
                # 其他异常（不应该发生）
                GLOG.ERROR(f"[ERROR] Failed to route event to {portfolio_id}: {type(e).__name__}: {e}")
                continue

    def _start_output_queue_listener(self, queue: Queue, portfolio_id: str):
        """
        启动output_queue监听器（双队列模式）

        监听PortfolioProcessor的output_queue，处理订单等领域事件：
        - 接收Portfolio发布的事件（Order等）
        - 序列化订单为DTO
        - 发送到Kafka orders.submission topic

        Args:
            queue: PortfolioProcessor的output_queue
            portfolio_id: Portfolio ID
        """
        import threading

        # 创建停止事件（用于优雅退出）
        stop_event = threading.Event()
        self.output_queue_stop_events[portfolio_id] = stop_event

        def listener_thread():
            GLOG.INFO(f"Output queue listener started for portfolio {portfolio_id}")

            while not stop_event.is_set():  # 检查停止事件
                try:
                    # 从队列取领域事件
                    event = queue.get(timeout=0.1)

                    # 处理订单事件
                    from ginkgo.entities import Order
                    if isinstance(event, Order):
                        # 暂停状态：不提交新订单
                        if self.is_paused:
                            logger.warning(f"ExecutionNode {self.node_id} is paused, order {event.uuid} not submitted")
                            queue.task_done()
                            continue

                        # ORDER PERSISTENCE: 写入新订单到数据库 (status=NEW) - order_crud.insert(event)
                        # from ginkgo.data.crud import OrderCRUD; from ginkgo.enums import ORDERSTATUS_TYPES
                        # order_crud = OrderCRUD(); event.status = ORDERSTATUS_TYPES.NEW; order_crud.insert(event)

                        # 使用DTO序列化订单并发送到Kafka
                        from ginkgo.interfaces.dtos import OrderSubmissionDTO

                        order_dto = OrderSubmissionDTO(
                            order_id=str(event.uuid),
                            portfolio_id=event.portfolio_id,
                            code=event.code,
                            direction=event.direction.value,
                            volume=event.volume,
                            price=str(event.price) if event.price else None,
                            timestamp=event.timestamp.isoformat() if event.timestamp else None
                        )

                        # 发送到Kafka
                        success = self.order_producer.send(KafkaTopics.ORDERS_SUBMISSION, order_dto.model_dump_json())
                        if success:
                            GLOG.INFO(f"Order {event.uuid} sent to Kafka via output_queue")
                        else:
                            GLOG.ERROR(f"[ERROR] Failed to send order {event.uuid} to Kafka")
                    else:
                        # 其他事件类型（如Signal），暂时记录日志
                        GLOG.DEBUG(f"Output queue event received for {portfolio_id}: {type(event).__name__}")

                    queue.task_done()

                except Exception as e:
                    # 导入queue.Empty用于类型检查
                    from queue import Empty

                    # 忽略队列超时异常（正常的空队列超时）
                    if isinstance(e, Empty):
                        continue

                    # 其他异常：打印完整的错误堆栈
                    import traceback
                    GLOG.ERROR(f"\n{'='*80}")
                    GLOG.ERROR(f"[ERROR] Error processing output_queue for {portfolio_id}")
                    GLOG.ERROR(f"{'='*80}")
                    GLOG.ERROR(f"Exception Type: {type(e).__name__}")
                    GLOG.ERROR(f"Exception Message: {str(e)}")
                    if 'event' in locals():
                        GLOG.ERROR(f"Event Type: {type(event).__name__}")
                        GLOG.ERROR(f"Event Object: {event}")
                    GLOG.ERROR(f"\nFull Traceback:")
                    for line in traceback.format_exc().split('\n'):
                        GLOG.ERROR(line)
                    GLOG.ERROR(f"{'='*80}\n")

                    # 仍然标记task_done，避免阻塞队列
                    try:
                        queue.task_done()
                    except Exception as e:
                        GLOG.ERROR(f"Failed to call task_done on output queue for portfolio {portfolio_id}: {e}")

            GLOG.INFO(f"Output queue listener stopped for portfolio {portfolio_id}")

        thread = threading.Thread(
            target=listener_thread,
            daemon=True,  # 守护线程，主进程退出时自动终止
            name=f"output_queue_{portfolio_id}"
        )
        thread.start()

        # 追踪线程
        self.output_queue_threads[portfolio_id] = thread
        GLOG.DEBUG(f"Output queue listener thread started for portfolio {portfolio_id}")

    # ========================================================================
    # 心跳线程启动（委托给 HeartbeatManager）
    # ========================================================================

    def _start_heartbeat_thread(self):
        """启动心跳上报线程（委托给 HeartbeatManager）"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            logger.warning(f"Heartbeat thread already running for node {self.node_id}")
            return

        self.heartbeat_thread = Thread(
            target=self._heartbeat_manager.heartbeat_loop,
            daemon=True,
            name=f"heartbeat_{self.node_id}"
        )
        self.heartbeat_thread.start()
        logger.info(f"Heartbeat thread started for node {self.node_id}")

    # ========================================================================
    # 节点控制命令（pause/resume/stop）
    # ========================================================================

    def pause(self):
        """
        暂停 ExecutionNode

        暂停后：
        - 心跳继续上报（状态=PAUSED）
        - 不处理新的事件（PriceUpdate、OrderFeedback）
        - 不提交新订单到Kafka
        - 仍响应调度命令（pause/resume/reload/migrate）
        """
        if self.is_paused:
            logger.warning(f"ExecutionNode {self.node_id} is already paused")
            return

        logger.info(f"Pausing ExecutionNode {self.node_id}")
        self.is_paused = True
        logger.info(f"ExecutionNode {self.node_id} PAUSED")
        logger.info(f"  - Market data consumption: SUSPENDED")
        logger.info(f"  - Order feedback consumption: SUSPENDED")
        logger.info(f"  - Order submission: SUSPENDED")
        logger.info(f"  - Heartbeat: ACTIVE (status=PAUSED)")
        logger.info(f"  - Command handling: ACTIVE")

    def resume(self):
        """
        恢复 ExecutionNode

        恢复后：
        - 继续处理事件（PriceUpdate、OrderFeedback）
        - 继续提交订单到Kafka
        - 心跳状态恢复为RUNNING
        """
        if not self.is_paused:
            logger.warning(f"ExecutionNode {self.node_id} is not paused")
            return

        logger.info(f"Resuming ExecutionNode {self.node_id}")
        self.is_paused = False
        logger.info(f"ExecutionNode {self.node_id} RESUMED")
        logger.info(f"  - Market data consumption: ACTIVE")
        logger.info(f"  - Order feedback consumption: ACTIVE")
        logger.info(f"  - Order submission: ACTIVE")
        logger.info(f"  - Heartbeat: ACTIVE (status=RUNNING)")

    def get_status(self) -> dict:
        """
        获取节点状态

        Returns:
            dict: 包含节点状态信息的字典，包括：
                - 基本状态：node_id, status, is_running, is_paused, should_stop
                - Portfolio信息：portfolio_count, portfolios（详细状态）
                - 背压统计：total_events, backpressure_count, dropped_events, backpressure_rate
        """
        # 确定节点状态
        if not self.is_running:
            status = "STOPPED"
        elif self.is_paused:
            status = "PAUSED"
        else:
            status = "RUNNING"

        # 计算背压率
        backpressure_rate = 0.0
        if self.total_event_count > 0:
            backpressure_rate = self.backpressure_count / self.total_event_count

        # 获取所有Portfolio的详细状态
        with self.portfolio_lock:
            portfolio_statuses = {}
            for portfolio_id, processor in self.portfolios.items():
                portfolio_statuses[portfolio_id] = processor.get_status()

        return {
            # 基本状态
            "node_id": self.node_id,
            "status": status,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "should_stop": self.should_stop,
            "portfolio_count": len(self.portfolios),
            "started_at": self.started_at,

            # Portfolio详细状态
            "portfolios": portfolio_statuses,

            # 背压统计
            "backpressure": {
                "total_events": self.total_event_count,
                "backpressure_count": self.backpressure_count,
                "dropped_events": self.dropped_event_count,
                "backpressure_rate": backpressure_rate
            }
        }

    def _get_uptime(self) -> str:
        """
        计算节点运行时长

        Returns:
            str: 格式化的运行时长（如 "2小时30分钟"）
        """
        if not self.started_at:
            return "未知"

        try:
            from datetime import datetime
            start_time = datetime.fromisoformat(self.started_at)
            uptime_seconds = (datetime.now() - start_time).total_seconds()

            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)

            if hours > 0:
                return f"{hours}小时{minutes}分钟{seconds}秒"
            elif minutes > 0:
                return f"{minutes}分钟{seconds}秒"
            else:
                return f"{seconds}秒"
        except Exception:
            return "未知"

    def _get_redis_client(self):
        """
        获取 Redis 客户端

        Returns:
            Redis: Redis 客户端实例，失败返回 None
        """
        try:
            from ginkgo.data.crud import RedisCRUD
            redis_crud = RedisCRUD()
            return redis_crud.redis
        except Exception as e:
            logger.error(f"Failed to get Redis client: {e}")
            return None

    # ========================================================================
    # 调度更新订阅（委托给 SchedulerCommandHandler）
    # ========================================================================

    def _start_schedule_updates_thread(self):
        """启动调度更新订阅线程"""
        if self.schedule_updates_thread and self.schedule_updates_thread.is_alive():
            logger.warning(f"Schedule updates thread already running for node {self.node_id}")
            return

        self.schedule_updates_thread = Thread(
            target=self._schedule_updates_loop,
            daemon=True,
            name=f"schedule_updates_{self.node_id}"
        )
        self.schedule_updates_thread.start()
        logger.info(f"Schedule updates thread started for node {self.node_id}")

    def _schedule_updates_loop(self):
        """
        调度更新消费循环

        订阅 Kafka schedule.updates topic，处理调度命令：
        - portfolio.reload: 重新加载Portfolio配置
        - portfolio.migrate: 迁移Portfolio到其他Node
        - node.shutdown: 关闭ExecutionNode

        命令处理委托给 SchedulerCommandHandler
        """
        try:
            # 创建 Kafka 消费者（直接订阅 topic）
            topic = KafkaTopics.SCHEDULE_UPDATES
            self.schedule_updates_consumer = GinkgoConsumer(
                topic=topic,
                group_id=f"execution_node_{self.node_id}",
                offset="latest"  # 从最新消息开始消费
            )

            logger.info(f"Subscribed to {topic} topic for node {self.node_id}")
            GLOG.INFO(f"[INFO] Subscribed to {topic} topic")

            while self.is_running:
                try:
                    # 消费消息（超时1秒）
                    # GinkgoConsumer.consumer 是底层的 KafkaConsumer
                    messages = self.schedule_updates_consumer.consumer.poll(timeout_ms=1000)

                    if not messages:
                        continue

                    # 处理每个消息 - 委托给 SchedulerCommandHandler
                    for tp, records in messages.items():
                        for msg in records:
                            self._command_handler.handle_schedule_update(msg)

                except Exception as e:
                    logger.error(f"Error consuming schedule updates: {e}")
                    time.sleep(1)  # 出错后等待1秒再重试

        except Exception as e:
            logger.error(f"Failed to start schedule updates consumer: {e}")
        finally:
            logger.info(f"Schedule updates loop stopped for node {self.node_id}")

    def _receive_portfolio(self, portfolio_id: str):
        """
        接收迁移的Portfolio（从其他节点迁移到本节点）

        Args:
            portfolio_id: Portfolio ID
        """
        try:
            logger.info(f"[RECEIVE] Starting portfolio receive process: {portfolio_id[:8]}")
            logger.info(f"[RECEIVE] Loading portfolio configuration from database...")

            # 从数据库加载Portfolio
            load_result = self.load_portfolio(portfolio_id)

            if load_result:
                logger.info(f"[RECEIVE] ✓ Portfolio {portfolio_id[:8]} received and loaded successfully")
                logger.info(f"[RECEIVE] Portfolio is now running on node {self.node_id}")

                # 更新Redis metrics（portfolio_count）
                self._heartbeat_manager.update_node_metrics()
            else:
                logger.error(f"[RECEIVE] ✗ Failed to load portfolio {portfolio_id[:8]}")
                # 发送加载失败警告
                try:
                    from ginkgo.notifier.core.notification_service import notify
                    notify(
                        f"Portfolio加载失败 - {portfolio_id[:8]}",
                        level="WARN",
                        module="ExecutionNode",
                        details={
                            "Portfolio ID": portfolio_id[:8],
                            "节点ID": self.node_id,
                            "失败原因": "load_portfolio返回False"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send load failure notification: {e}")

        except Exception as e:
            logger.error(f"[RECEIVE] ✗ Failed to receive portfolio {portfolio_id[:8]}: {e}")
