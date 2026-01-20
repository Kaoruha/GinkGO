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

MVP阶段（Phase 3）：
- 单Portfolio运行
- 基础Kafka订阅和消息路由
- 简单的订单提交流程
- 从数据库加载Portfolio配置

Phase 4扩展：
- InterestMap路由机制（O(1)查询）
- 多Portfolio并行运行
- Backpressure反压机制

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
from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer, GinkgoProducer
from ginkgo import services
from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES
from ginkgo.interfaces.kafka_topics import KafkaTopics

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
        self.started_at: Optional[str] = None

        # output_queue listener 线程追踪
        self.output_queue_threads: Dict[str, Thread] = {}  # {portfolio_id: Thread}
        self.output_queue_stop_events: Dict[str, Event] = {}  # {portfolio_id: Event}

        # Portfolio队列管理（ExecutionNode持有所有队列）
        self.input_queues: Dict[str, Queue] = {}  # {portfolio_id: Queue}
        self.output_queues: Dict[str, Queue] = {}  # {portfolio_id: Queue}

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
        if self._is_node_id_in_use():
            print(f"\n[ERROR] ExecutionNode {self.node_id} is already in use by another process!")
            print(f"[ERROR] Cannot start duplicate node_id.")
            print(f"\nPossible solutions:")
            print(f"  1. Stop the other ExecutionNode instance (Ctrl+C)")
            print(f"  2. Use a different node_id: ginkgo execution start --node-id <new_id>")
            print(f"  3. Cleanup stale data: ginkgo execution cleanup --node-id {self.node_id}")
            raise RuntimeError(f"ExecutionNode {self.node_id} is already in use")

        # 重置停止标志（支持重启）
        self.should_stop = False

        # 设置运行标志
        self.is_running = True
        self.started_at = datetime.now().isoformat()

        if self.is_paused:
            print(f"Resuming ExecutionNode {self.node_id} (was paused)")
            self.is_paused = False
        else:
            print(f"Starting ExecutionNode {self.node_id}")

        # 0. 清理旧的心跳和指标数据（防止节点异常重启后残留）
        self._cleanup_old_heartbeat_data()

        # 1. 立即发送心跳（让 Scheduler 发现节点）
        self._send_heartbeat()

        # 2. 启动心跳上报线程（维持节点在线状态）
        self._start_heartbeat_thread()

        # 3. 启动调度更新订阅线程（接收 Scheduler 命令：pause/resume/migrate）
        self._start_schedule_updates_thread()

        # 4. 启动市场数据消费线程（接收 EventPriceUpdate）
        self._start_market_data_consumer_thread()

        # 5. 启动订单回报消费线程（接收 EventOrderPartiallyFilled）
        self._start_order_feedback_consumer_thread()

        print(f"[INFO] ExecutionNode {self.node_id} started")

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
        print(f"[INFO] Portfolio count: {len(self.portfolios)} (waiting for Scheduler)")
        print(f"[INFO] Node is ready to receive portfolio.migrate commands from Scheduler")

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
            print(f"[WARNING] ExecutionNode {self.node_id} is not running")
            return

        print(f"Stopping ExecutionNode {self.node_id}")

        # 0. 设置停止标志（通知所有线程）
        self.should_stop = True
        self.is_running = False

        # 1. 关闭 Kafka Consumers - 切断新消息来源
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 1 步：关闭 Kafka Consumers（停止拉取新消息）")
        print(f"[INFO] ══════════════════════════════════════════════")

        if self.market_data_consumer:
            try:
                self.market_data_consumer.close()
                print(f"[INFO]   ✅ Market data consumer closed")
                print(f"[INFO]      └─ 不再拉取 Price Update")
                print(f"[INFO]      └─ 不会触发策略生成新订单")
            except Exception as e:
                print(f"[ERROR]   ✗ Error closing market data consumer: {e}")

        if self.order_feedback_consumer:
            try:
                self.order_feedback_consumer.close()
                print(f"[INFO]   ✅ Order feedback consumer closed")
                print(f"[INFO]      └─ 不再拉取 Order Feedback")
                print(f"[INFO]      └─ 不会触发风控生成新订单")
            except Exception as e:
                print(f"[ERROR]   ✗ Error closing order feedback consumer: {e}")

        if self.schedule_updates_consumer:
            try:
                self.schedule_updates_consumer.close()
                print(f"[INFO]   ✅ Schedule updates consumer closed")
                print(f"[INFO]      └─ 不再接收调度命令")
            except Exception as e:
                print(f"[ERROR]   ✗ Error closing schedule updates consumer: {e}")

        # 2. 等待 Portfolio 消费完 input_queue
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 2 步：等待 Portfolio 处理完 input_queue 中的消息")
        print(f"[INFO] ══════════════════════════════════════════════")

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
                    print(f"[INFO]   ✅ 所有 input_queue 已清空")
                    print(f"[INFO]      └─ 已拉取的消息已处理完毕")
                    break
                else:
                    print(f"[DEBUG]   等待 {total_remaining} 个事件处理完成...")
                    time.sleep(0.1)
            else:
                if total_remaining > 0:
                    print(f"[WARNING] ⚠️  超时，仍有 {total_remaining} 个事件未处理")
        else:
            print(f"[INFO]   ℹ️  没有 Portfolio 运行，跳过")

        # 3. 等待 output_queue 发送完毕并停止 listener
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 3 步：等待 output_queue 中的订单发送完成")
        print(f"[INFO] ══════════════════════════════════════════════")

        if self.output_queue_threads:
            print(f"[INFO]   停止 {len(self.output_queue_threads)} output queue listeners...")

            # 设置停止事件
            for stop_event in self.output_queue_stop_events.values():
                stop_event.set()

            # 等待所有 listener 完成
            for portfolio_id, thread in self.output_queue_threads.items():
                if thread.is_alive():
                    print(f"[DEBUG]   等待 output_queue listener ({portfolio_id[:8]}...) 完成...")
                    thread.join(timeout=5)
                    if thread.is_alive():
                        print(f"[WARNING]   ⚠️  Output queue listener ({portfolio_id[:8]}...) 未能在 5 秒内完成")
                    else:
                        print(f"[INFO]   ✅ Output queue listener ({portfolio_id[:8]}...) 已完成")
                else:
                    print(f"[INFO]   ✅ Output queue listener ({portfolio_id[:8]}...) 已停止")

            # 清空追踪
            self.output_queue_threads.clear()
            self.output_queue_stop_events.clear()
            print(f"[INFO]   ✅ 所有 output_queue listener 已停止")
        else:
            print(f"[INFO]   ℹ️  没有 output_queue listener 运行，跳过")

        # 4. 关闭 Producer - 确保所有订单已发送
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 4 步：关闭 Producer（确保所有订单已发送）")
        print(f"[INFO] ══════════════════════════════════════════════")

        if hasattr(self, 'order_producer') and self.order_producer:
            try:
                self.order_producer.close()
                print(f"[INFO]   ✅ Order producer closed")
                print(f"[INFO]      └─ flush() 确保所有订单已发送")
                print(f"[INFO]      └─ close() 关闭连接")
            except Exception as e:
                print(f"[ERROR]   ✗ Error closing order producer: {e}")
        else:
            print(f"[INFO]   ℹ️  Order producer 不存在，跳过")

        # 5. 等待所有 Portfolio 关闭
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 5 步：等待所有 PortfolioProcessor 线程退出")
        print(f"[INFO] ══════════════════════════════════════════════")

        with self.portfolio_lock:
            processors = list(self.portfolios.values())

        for processor in processors:
            if processor.is_alive():
                portfolio_id_short = processor.portfolio_id[:8] if len(processor.portfolio_id) > 8 else processor.portfolio_id
                print(f"[DEBUG]   等待 Portfolio ({portfolio_id_short}...) 退出...")
                processor.join(timeout=5)
                if processor.is_alive():
                    print(f"[WARNING]   ⚠️  Portfolio ({portfolio_id_short}...) 未能在 5 秒内退出")
                else:
                    print(f"[INFO]   ✅ Portfolio ({portfolio_id_short}...) 已退出")
            else:
                portfolio_id_short = processor.portfolio_id[:8] if len(processor.portfolio_id) > 8 else processor.portfolio_id
                print(f"[INFO]   ✅ Portfolio ({portfolio_id_short}...) 已停止")

        if processors:
            print(f"[INFO]   ✅ 所有 PortfolioProcessor 线程已退出")
        else:
            print(f"[INFO]   ℹ️  没有 PortfolioProcessor 运行，跳过")

        # 6. 等待其他线程退出
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 6 步：等待其他线程退出")
        print(f"[INFO] ══════════════════════════════════════════════")

        threads_to_wait = [
            ("Market data thread", self.market_data_thread),
            ("Order feedback thread", self.order_feedback_thread),
            ("Schedule updates thread", self.schedule_updates_thread),
        ]

        for name, thread in threads_to_wait:
            if thread and thread.is_alive():
                print(f"[DEBUG]   等待 {name} 退出...")
                thread.join(timeout=5)
                if not thread.is_alive():
                    print(f"[INFO]   ✅ {name} 已退出")
                else:
                    print(f"[WARNING]   ⚠️  {name} 未能在 5 秒内退出")

        # 7. 停止心跳线程
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 7 步：停止心跳线程")
        print(f"[INFO] ══════════════════════════════════════════════")

        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
            if not self.heartbeat_thread.is_alive():
                print(f"[INFO]   ✅ Heartbeat thread 已退出")
            else:
                print(f"[WARNING]   ⚠️  Heartbeat thread 未能在 5 秒内退出")

        # 8. 清理 Redis（上报离线状态）
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 8 步：清理 Redis 数据（上报离线状态）")
        print(f"[INFO] ══════════════════════════════════════════════")

        try:
            redis_client = self._get_redis_client()
            if redis_client:
                heartbeat_key = f"heartbeat:node:{self.node_id}"
                metrics_key = f"node:metrics:{self.node_id}"

                deleted_heartbeat = redis_client.delete(heartbeat_key)
                if deleted_heartbeat:
                    print(f"[INFO]   ✅ 心跳数据已删除（Scheduler 将检测到节点离线）")

                deleted_metrics = redis_client.delete(metrics_key)
                if deleted_metrics:
                    print(f"[INFO]   ✅ 指标数据已删除")

        except Exception as e:
            print(f"[ERROR]   ✗ 清理 Redis 失败: {e}")

        # 9. 清空内存
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] 第 9 步：清空内存数据结构")
        print(f"[INFO] ══════════════════════════════════════════════")

        with self.portfolio_lock:
            portfolio_count = len(self.portfolios)
            self.portfolios.clear()

        self.input_queues.clear()
        self.output_queues.clear()

        print(f"[INFO]   ✅ 内存已清空 (portfolios: {portfolio_count}, queues释放)")

        # 10. 完成
        print(f"[INFO] ══════════════════════════════════════════════")
        print(f"[INFO] ✅ ExecutionNode {self.node_id} 已完全停止")
        print(f"[INFO] ══════════════════════════════════════════════")

        # 发送优雅退出通知
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                f"执行节点 {self.node_id} 已优雅退出",
                level="INFO",
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

                # 输出运行时组件快照
                self._print_portfolio_runtime_snapshot(portfolio)

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

    def _load_portfolio_components(self, portfolio: "PortfolioLive", portfolio_model):
        """
        [DEPRECATED] 此方法已废弃，请使用PortfolioService.load_portfolio_with_components()

        组件加载逻辑已移到PortfolioService中，这样可以：
        - 职责分离（Service负责业务逻辑，Node负责调度）
        - 代码复用（其他地方也可以使用Service加载Portfolio）
        - 简化ExecutionNode代码

        Args:
            portfolio: PortfolioLive实例
            portfolio_model: 数据库中的Portfolio模型
        """
        # 不再使用此方法，直接返回
        logger.warning("[DEPRECATED] _load_portfolio_components已废弃，组件由PortfolioService加载")
        return

        print(f"[INFO] ══════════════════════════════════════════════════════")
        print(f"[INFO] 📦 Portfolio Components Loading")
        print(f"[INFO] ══════════════════════════════════════════════════════")
        print(f"[INFO] Portfolio: {portfolio.name} ({portfolio.portfolio_id[:8]})")

        try:
            # 获取Portfolio的所有组件
            # Portfolio现在已经使用数据库UUID，所以portfolio.portfolio_id就是正确的ID
            components_result = portfolio_service.get_components(portfolio_id=portfolio.portfolio_id)

            if not components_result.is_success():
                print(f"[WARNING] Failed to load components: {components_result.error}")
                return

            components = components_result.data

            # 分类统计
            strategies = []
            sizers = []
            risk_managers = []

            if components:
                print(f"[INFO] Found {len(components)} components in database")

                # 第二版：实际加载组件到Portfolio
                # 组件分类
                strategies_list = []
                selectors_list = []
                sizers_list = []
                risk_managers_list = []

                for component in components:
                    comp_type = component.get('component_type', 'UNKNOWN')

                    if comp_type == 'strategy':
                        strategies_list.append(component)
                    elif comp_type == 'selector':
                        selectors_list.append(component)
                    elif comp_type == 'sizer':
                        sizers_list.append(component)
                    elif comp_type == 'risk_management':
                        risk_managers_list.append(component)

                # 组件统计
                print(f"[INFO]")
                print(f"[INFO] ══════════════════════════════════════════════════════")
                print(f"[INFO] 📊 Component Summary")
                print(f"[INFO] ══════════════════════════════════════════════════════")
                print(f"[INFO] Strategies:   {len(strategies_list)}")
                print(f"[INFO] Selectors:    {len(selectors_list)}")
                print(f"[INFO] Sizers:       {len(sizers_list)}")
                print(f"[INFO] Risk Managers: {len(risk_managers_list)}")
                print(f"[INFO] Total:        {len(components)}")

                # 实际加载组件
                self._bind_components_to_portfolio(
                    portfolio,
                    strategies_list,
                    selectors_list,
                    sizers_list,
                    risk_managers_list
                )
            else:
                print(f"[INFO] No components found in database")
                print(f"[INFO] Using default components for portfolio")

                # 使用默认组件
                self._bind_components_to_portfolio(
                    portfolio,
                    [],  # 空策略列表 - 会使用默认RandomSignalStrategy
                    [],  # 空selector列表 - 会使用默认CNAllSelector
                    [],  # 空sizer列表 - 会使用默认FixedSizer
                    []   # 空风控列表 - 会使用默认PositionRatioRisk
                )

        except Exception as e:
            print(f"[ERROR] Error loading portfolio components: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

        print(f"[INFO] ══════════════════════════════════════════════════════")

    def _print_portfolio_runtime_snapshot(self, portfolio: "PortfolioLive"):
        """
        输出 Portfolio 运行时组件快照

        显示当前加载到 Portfolio 中的所有组件及其配置参数。

        Args:
            portfolio: PortfolioLive 实例
        """
        print(f"[INFO]")
        print(f"[INFO] ══════════════════════════════════════════════════════")
        print(f"[INFO] 🔍 Portfolio Runtime Snapshot")
        print(f"[INFO] ══════════════════════════════════════════════════════")
        print(f"[INFO] Portfolio: {portfolio.name} ({portfolio.portfolio_id[:8]})")
        print(f"[INFO] Engine ID: {portfolio.engine_id[:8] if portfolio.engine_id else 'N/A'}")
        print(f"[INFO] Run ID: {portfolio.run_id[:8] if portfolio.run_id else 'N/A'}")
        print(f"[INFO]")

        # 1. 基本信息
        print(f"[INFO] 📋 Basic Information")
        print(f"[INFO] ├─ Initial Capital: {portfolio.initial_capital}")
        print(f"[INFO] ├─ Current Cash: {portfolio.cash}")
        print(f"[INFO] ├─ Frozen Cash: {portfolio.frozen_cash}")
        # PortfolioLive 可能没有 get_total_value() 方法，使用 cash 代替
        total_value = portfolio.get_total_value() if hasattr(portfolio, 'get_total_value') else portfolio.cash
        print(f"[INFO] ├─ Total Value: {total_value}")
        print(f"[INFO] ├─ Position Count: {len(portfolio.positions)}")
        print(f"[INFO] └─ Status: {portfolio._status}")
        print(f"[INFO]")

        # 2. 策略组件
        print(f"[INFO] ───────────────────────────────────────────────────────")
        print(f"[INFO] 📊 Strategy Components ({len(portfolio.strategies)})")
        print(f"[INFO] ───────────────────────────────────────────────────────")

        if portfolio.strategies:
            for i, strategy in enumerate(portfolio.strategies, 1):
                print(f"[INFO]")
                print(f"[INFO] Strategy #{i}: {strategy.name}")
                print(f"[INFO]   ├─ Type: {type(strategy).__name__}")
                print(f"[INFO]   ├─ UUID: {strategy.uuid[:8] if strategy.uuid else 'N/A'}")
                print(f"[INFO]   └─ Parameters:")

                # 获取策略参数
                params = self._get_component_parameters(strategy)
                for param_name, param_value in params.items():
                    print(f"[INFO]      ├─ {param_name}: {param_value}")
        else:
            print(f"[INFO] ⚠️  No strategies loaded (Portfolio will not generate signals)")

        print(f"[INFO]")

        # 3. Sizer 组件
        print(f"[INFO] ───────────────────────────────────────────────────────")
        print(f"[INFO] 📏 Sizer Component")
        print(f"[INFO] ───────────────────────────────────────────────────────")

        if portfolio.sizer:
            print(f"[INFO]")
            print(f"[INFO] Sizer: {portfolio.sizer.name}")
            print(f"[INFO]   ├─ Type: {type(portfolio.sizer).__name__}")
            print(f"[INFO]   ├─ UUID: {portfolio.sizer.uuid[:8] if portfolio.sizer.uuid else 'N/A'}")
            print(f"[INFO]   └─ Parameters:")

            # 获取 Sizer 参数
            params = self._get_component_parameters(portfolio.sizer)
            for param_name, param_value in params.items():
                print(f"[INFO]      ├─ {param_name}: {param_value}")
        else:
            print(f"[INFO] ⚠️  No sizer loaded (Orders will use default size)")

        print(f"[INFO]")

        # 4. 风控组件
        print(f"[INFO] ───────────────────────────────────────────────────────")
        print(f"[INFO] 🛡️  Risk Management Components ({len(portfolio.risk_managers)})")
        print(f"[INFO] ───────────────────────────────────────────────────────")

        if portfolio.risk_managers:
            for i, risk_manager in enumerate(portfolio.risk_managers, 1):
                print(f"[INFO]")
                print(f"[INFO] Risk Manager #{i}: {risk_manager.name}")
                print(f"[INFO]   ├─ Type: {type(risk_manager).__name__}")
                print(f"[INFO]   ├─ UUID: {risk_manager.uuid[:8] if risk_manager.uuid else 'N/A'}")
                print(f"[INFO]   └─ Parameters:")

                # 获取风控参数
                params = self._get_component_parameters(risk_manager)
                for param_name, param_value in params.items():
                    print(f"[INFO]      ├─ {param_name}: {param_value}")
        else:
            print(f"[INFO] ⚠️  No risk managers loaded (Orders will not be filtered)")

        print(f"[INFO]")

        # 5. 持仓快照
        print(f"[INFO] ───────────────────────────────────────────────────────")
        print(f"[INFO] 💼 Current Positions ({len(portfolio.positions)})")
        print(f"[INFO] ───────────────────────────────────────────────────────")

        if portfolio.positions:
            for code, position in list(portfolio.positions.items())[:5]:  # 只显示前5个
                print(f"[INFO]   {code}: {position.volume} shares @ {position.price}")
            if len(portfolio.positions) > 5:
                print(f"[INFO]   ... and {len(portfolio.positions) - 5} more")
        else:
            print(f"[INFO]   No positions yet")

        print(f"[INFO]")
        print(f"[INFO] ══════════════════════════════════════════════════════")
        print(f"[INFO] ✅ Runtime Snapshot Complete")
        print(f"[INFO] ══════════════════════════════════════════════════════")

    def _get_component_parameters(self, component) -> dict:
        """
        获取组件的所有配置参数

        通过反射获取组件实例的所有属性，过滤掉内部属性和方法。

        Args:
            component: 组件实例（Strategy、Sizer、RiskManagement）

        Returns:
            dict: 参数字典
        """
        params = {}

        # 需要过滤的属性
        filtered_attrs = {
            '_logger', '_name', '_uuid', 'logger', 'name', 'uuid',
            '__class__', '__module__', '__dict__', '__weakref__',
            'is_active', 'set_active', 'get_info', 'cal', 'generate_signals'
        }

        try:
            # 获取所有实例属性
            for attr_name in dir(component):
                # 过滤掉方法和特殊属性
                if attr_name.startswith('_') or callable(getattr(component, attr_name)):
                    continue

                if attr_name in filtered_attrs:
                    continue

                try:
                    attr_value = getattr(component, attr_name)

                    # 过滤掉复杂对象
                    if isinstance(attr_value, (str, int, float, bool, list, dict, type(None))):
                        params[attr_name] = attr_value
                except:
                    pass

        except Exception as e:
            print(f"[WARNING] Error getting parameters for {type(component).__name__}: {e}")

        return params

    def _bind_components_to_portfolio(
        self,
        portfolio: "PortfolioLive",
        strategies_list: list,
        selectors_list: list,
        sizers_list: list,
        risk_managers_list: list
    ):
        """
        将数据库中的组件配置实例化并绑定到Portfolio

        参考回测引擎的_perform_component_binding方法实现

        Args:
            portfolio: PortfolioLive实例
            strategies_list: 策略组件配置列表
            selectors_list: 选股器组件配置列表
            sizers_list: 仓位管理组件配置列表
            risk_managers_list: 风控管理器组件配置列表
        """
        print(f"[INFO]")
        print(f"[INFO] ══════════════════════════════════════════════════════")
        print(f"[INFO] 🔧 Binding Components to Portfolio")
        print(f"[INFO] ══════════════════════════════════════════════════════")

        try:
            # 1. 加载策略 (必需)
            if len(strategies_list) == 0:
                print(f"[WARNING] No strategy found, using default RandomSignalStrategy")
                default_strategy = self._get_default_component('strategy')
                if default_strategy:
                    portfolio.add_strategy(default_strategy)
                    print(f"[INFO] ✅ Added default strategy: {default_strategy.__class__.__name__}")
            else:
                for strategy_config in strategies_list:
                    strategy = self._instantiate_component_from_config(strategy_config, 'strategy')
                    if strategy:
                        portfolio.add_strategy(strategy)
                        print(f"[INFO] ✅ Added strategy: {strategy.__class__.__name__}")

            # 2. 加载选股器 (必需)
            if len(selectors_list) == 0:
                print(f"[WARNING] No selector found, using default CNAllSelector")
                default_selector = self._get_default_component('selector')
                if default_selector:
                    portfolio.bind_selector(default_selector)
                    print(f"[INFO] ✅ Bound default selector: {default_selector.__class__.__name__}")
            else:
                selector_config = selectors_list[0]  # 只使用第一个selector
                selector = self._instantiate_component_from_config(selector_config, 'selector')
                if selector:
                    portfolio.bind_selector(selector)
                    print(f"[INFO] ✅ Bound selector: {selector.__class__.__name__}")

            # 3. 加载仓位管理 (必需)
            if len(sizers_list) == 0:
                print(f"[WARNING] No sizer found, using default FixedSizer")
                default_sizer = self._get_default_component('sizer')
                if default_sizer:
                    portfolio.bind_sizer(default_sizer)
                    print(f"[INFO] ✅ Bound default sizer: {default_sizer.__class__.__name__}")
            else:
                sizer_config = sizers_list[0]  # 只使用第一个sizer
                sizer = self._instantiate_component_from_config(sizer_config, 'sizer')
                if sizer:
                    portfolio.bind_sizer(sizer)
                    print(f"[INFO] ✅ Bound sizer: {sizer.__class__.__name__}")

            # 4. 加载风控管理器 (可选)
            if len(risk_managers_list) == 0:
                print(f"[INFO] No risk managers found, using default PositionRatioRisk")
                default_risk = self._get_default_component('risk_management')
                if default_risk:
                    portfolio.add_risk_manager(default_risk)
                    print(f"[INFO] ✅ Added default risk manager: {default_risk.__class__.__name__}")
            else:
                for risk_config in risk_managers_list:
                    risk_manager = self._instantiate_component_from_config(risk_config, 'risk_management')
                    if risk_manager:
                        portfolio.add_risk_manager(risk_manager)
                        print(f"[INFO] ✅ Added risk manager: {risk_manager.__class__.__name__}")

            print(f"[INFO]")
            print(f"[INFO] ✅ Component binding completed")

        except Exception as e:
            print(f"[ERROR] Failed to bind components: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

        print(f"[INFO] ══════════════════════════════════════════════════════")

    def _instantiate_component_from_config(self, component_config: dict, component_type: str):
        """
        从组件配置实例化组件

        参考回测引擎的_instantiate_component_from_file方法

        Args:
            component_config: 组件配置字典 (包含component_id=file_id)
            component_type: 组件类型 (strategy/selector/sizer/risk_management)

        Returns:
            组件实例，失败返回None
        """
        try:
            # component_config包含: mount_id, portfolio_id, component_id(file_id), component_name, component_type
            file_id = component_config.get('component_id')  # 注意：这里是component_id，对应file_id
            if not file_id:
                print(f"[WARNING] No component_id in component config")
                return None

            # 获取参数
            mount_id = component_config.get('mount_id')
            component_params = []

            if mount_id:
                try:
                    from ginkgo.data.containers import container
                    param_crud = container.cruds.param()
                    param_records = param_crud.find(filters={"mapping_id": mount_id})

                    if param_records:
                        # 按index排序
                        sorted_params = sorted(param_records, key=lambda p: p.index)
                        component_params = [param.value for param in sorted_params]
                        print(f"[DEBUG] Found {len(component_params)} params for {component_config.get('component_name')}")
                    else:
                        print(f"[DEBUG] No params found for mount_id {mount_id[:8]}...")

                except Exception as e:
                    print(f"[WARNING] Failed to get params: {e}")

            # 获取file_service
            file_service = services.data.file_service()

            # 获取文件内容
            file_result = file_service.get_by_uuid(file_id)
            if not file_result.success or not file_result.data:
                print(f"[WARNING] Failed to get file {file_id[:8]}...: {file_result.error}")
                # 尝试使用默认组件
                return self._get_default_component(component_type)

            file_info = file_result.data
            if isinstance(file_info, dict) and "file" in file_info:
                mfile = file_info["file"]
                if hasattr(mfile, "data") and mfile.data:
                    if isinstance(mfile.data, bytes):
                        code_content = mfile.data.decode("utf-8", errors="ignore")
                    else:
                        code_content = str(mfile.data)
                else:
                    # Fallback: 使用默认组件
                    print(f"[WARNING] No file data, using default component")
                    return self._get_default_component(component_type)
            else:
                return self._get_default_component(component_type)

            # 动态执行代码
            import importlib.util
            import tempfile
            import os
            import sys

            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
                temp_file.write(code_content)
                temp_file_path = temp_file.name

            try:
                # 为兼容性添加get_bars函数
                from ginkgo.data.containers import container as data_container

                def get_bars_stub(*args, **kwargs):
                    """兼容性存根"""
                    bar_service = data_container.bar_service()
                    return bar_service.get(*args, **kwargs)

                sys.modules["ginkgo.data"] = type(sys)("ginkgo.data")
                sys.modules["ginkgo.data"].get_bars = get_bars_stub
                sys.modules["ginkgo.data"].container = data_container

                # 动态导入模块
                spec = importlib.util.spec_from_file_location("dynamic_component", temp_file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 查找组件类
                component_class = None
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and hasattr(attr, "__bases__"):
                        # 检查是否是组件类
                        is_component = False

                        # 检查__abstract__属性
                        if hasattr(attr, "__abstract__") and not getattr(attr, "__abstract__", True):
                            is_component = True
                        else:
                            # 检查基类名称
                            for base in attr.__bases__:
                                base_name = base.__name__
                                if base_name.endswith("Strategy") or base_name.endswith("Selector") or \
                                   base_name.endswith("Sizer") or base_name.endswith("RiskManagement") or \
                                   base_name == "BaseStrategy" or base_name == "BaseSelector" or \
                                   base_name == "BaseSizer" or base_name == "BaseRiskManagement":
                                    is_component = True
                                    break

                        if is_component:
                            component_class = attr
                            break

                if component_class is None:
                    print(f"[ERROR] No component class found in file")
                    return self._get_default_component(component_type)

                # 实例化组件
                try:
                    if component_params:
                        # 有参数：使用参数实例化
                        print(f"[DEBUG] Creating {component_class.__name__} with params: {component_params}")
                        component = component_class(*component_params)
                    else:
                        # 无参数：尝试无参实例化（允许使用默认值）
                        print(f"[INFO] No params found for {component_class.__name__}, attempting instantiation with defaults")
                        component = component_class()

                    print(f"[DEBUG] Created {component_class.__name__} instance")
                    return component
                except Exception as e:
                    print(f"[ERROR] Failed to instantiate {component_class.__name__}: {e}")
                    return self._get_default_component(component_type)

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        except Exception as e:
            print(f"[ERROR] Failed to instantiate component: {e}")
            return self._get_default_component(component_type)

    def _get_default_component(self, component_type: str):
        """
        获取默认组件作为fallback

        Args:
            component_type: 组件类型

        Returns:
            默认组件实例
        """
        if component_type == 'strategy':
            print(f"[INFO] Using default RandomSignalStrategy")
            from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
            return RandomSignalStrategy()

        elif component_type == 'selector':
            print(f"[INFO] Using default CNAllSelector")
            from ginkgo.trading.selectors.cn_all_selector import CNAllSelector
            return CNAllSelector()

        elif component_type == 'sizer':
            print(f"[INFO] Using default FixedSizer")
            from ginkgo.trading.sizers.fixed_sizer import FixedSizer
            return FixedSizer()

        elif component_type == 'risk_management':
            print(f"[INFO] Using default PositionRatioRisk")
            from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
            return PositionRatioRisk()

        else:
            print(f"[WARNING] Unknown component type: {component_type}")
            return None

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
                print(f"[WARNING] Portfolio {portfolio_id} not found")
                return False

            # 优雅停止PortfolioProcessor（等待队列清空）
            processor = self.portfolios[portfolio_id]
            print(f"[INFO] Unloading Portfolio {portfolio_id}...")
            processor.graceful_stop(timeout=30.0)

        # 在锁外等待 PortfolioProcessor 线程退出
        processor.join(timeout=10)
        if processor.is_alive():
            print(f"[WARNING] Processor {portfolio_id} did not stop gracefully")
        else:
            print(f"[INFO] Processor {portfolio_id} stopped")

        # 在锁外停止 output_queue listener 线程
        if portfolio_id in self.output_queue_stop_events:
            print(f"[INFO] Stopping output queue listener for {portfolio_id}...")
            self.output_queue_stop_events[portfolio_id].set()

        if portfolio_id in self.output_queue_threads:
            thread = self.output_queue_threads[portfolio_id]
            thread.join(timeout=10)
            if thread.is_alive():
                print(f"[WARNING] Output queue listener for {portfolio_id} did not stop gracefully")
            else:
                print(f"[INFO] Output queue listener for {portfolio_id} stopped")

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

            print(f"[INFO] Portfolio {portfolio_id} unloaded successfully")

            # 从InterestMap移除订阅（Phase 4实现）
            subscribed_codes = self.interest_map.get_all_subscriptions(portfolio_id)
            if subscribed_codes:
                self.interest_map.remove_portfolio(portfolio_id, subscribed_codes)
                print(f"[INFO] Removed {len(subscribed_codes)} subscriptions from InterestMap")

            return True

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

        print(f"Market data consumer thread started for node {self.node_id}")

        while self.is_running:
            try:
                # 暂停状态：不处理新的事件
                if self.is_paused:
                    time.sleep(0.1)  # 短暂休眠避免CPU空转
                    continue

                for message in self.market_data_consumer.consumer:
                    if not self.is_running:
                        break

                    # 暂停状态检查
                    if self.is_paused:
                        break

                    event_data = message.value

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
                    print(f"[ERROR] Error consuming market data: {e}")

        print(f"Market data consumer thread stopped for node {self.node_id}")

    def _consume_order_feedback(self):
        """消费订单回报线程 - 消息成功放入队列后立即提交 offset"""
        from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled

        print(f"Order feedback consumer thread started for node {self.node_id}")

        while self.is_running:
            try:
                # 暂停状态：不处理订单回报
                if self.is_paused:
                    time.sleep(0.1)  # 短暂休眠避免CPU空转
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
                    print(f"[ERROR] Error consuming order feedback: {e}")

        print(f"Order feedback consumer thread stopped for node {self.node_id}")

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
                except:
                    queue_size = -1
                    queue_usage = -1

                # 记录详细背压日志
                print(f"[BACKPRESSURE] Portfolio {portfolio_id} queue full")
                print(f"  - Event: {event.code} at {event.timestamp if hasattr(event, 'timestamp') else 'N/A'}")
                print(f"  - Queue: {queue_size}/1000 ({queue_usage*100:.1f}%)")
                print(f"  - Total backpressure: {self.backpressure_count}, dropped: {self.dropped_event_count}")

                # TODO: Phase 4 - 发送背压告警到监控系统
                # self._send_backpressure_alert(portfolio_id, queue_usage, event)

            except Exception as e:
                # 其他异常（不应该发生）
                print(f"[ERROR] Failed to route event to {portfolio_id}: {type(e).__name__}: {e}")
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
            print(f"Output queue listener started for portfolio {portfolio_id}")

            while not stop_event.is_set():  # 检查停止事件
                try:
                    # 从队列取领域事件
                    event = queue.get(timeout=0.1)

                    # 处理订单事件
                    from ginkgo.trading.entities import Order
                    if isinstance(event, Order):
                        # 暂停状态：不提交新订单
                        if self.is_paused:
                            logger.warning(f"ExecutionNode {self.node_id} is paused, order {event.uuid} not submitted")
                            queue.task_done()
                            continue

                        # ORDER PERSISTENCE: 写入新订单到数据库 (status=NEW) - order_crud.insert(event)
                        # from ginkgo.data.crud import OrderCRUD; from ginkgo.enums import ORDERSTATUS_TYPES
                        # order_crud = OrderCRUD(); event.status = ORDERSTATUS_TYPES.NEW; order_crud.insert(event)

                        # 序列化订单为DTO并发送到Kafka
                        order_data = {
                            "order_id": str(event.uuid),
                            "portfolio_id": event.portfolio_id,
                            "code": event.code,
                            "direction": event.direction.value,
                            "volume": event.volume,
                            "price": str(event.price) if event.price else None,
                            "timestamp": event.timestamp.isoformat() if event.timestamp else None
                        }

                        # 发送到Kafka
                        success = self.order_producer.send(KafkaTopics.ORDERS_SUBMISSION, order_data)
                        if success:
                            print(f"Order {event.uuid} sent to Kafka via output_queue")
                        else:
                            print(f"[ERROR] Failed to send order {event.uuid} to Kafka")
                    else:
                        # 其他事件类型（如Signal），暂时记录日志
                        print(f"[DEBUG] Output queue event received for {portfolio_id}: {type(event).__name__}")

                    queue.task_done()

                except Exception as e:
                    # 导入queue.Empty用于类型检查
                    from queue import Empty

                    # 忽略队列超时异常（正常的空队列超时）
                    if isinstance(e, Empty):
                        continue

                    # 其他异常：打印完整的错误堆栈
                    import traceback
                    print(f"\n{'='*80}")
                    print(f"[ERROR] Error processing output_queue for {portfolio_id}")
                    print(f"{'='*80}")
                    print(f"Exception Type: {type(e).__name__}")
                    print(f"Exception Message: {str(e)}")
                    if 'event' in locals():
                        print(f"Event Type: {type(event).__name__}")
                        print(f"Event Object: {event}")
                    print(f"\nFull Traceback:")
                    traceback.print_exc()
                    print(f"{'='*80}\n")

                    # 仍然标记task_done，避免阻塞队列
                    try:
                        queue.task_done()
                    except:
                        pass

            print(f"Output queue listener stopped for portfolio {portfolio_id}")

        thread = threading.Thread(
            target=listener_thread,
            daemon=True,  # 守护线程，主进程退出时自动终止
            name=f"output_queue_{portfolio_id}"
        )
        thread.start()

        # 追踪线程
        self.output_queue_threads[portfolio_id] = thread
        print(f"[DEBUG] Output queue listener thread started for portfolio {portfolio_id}")



    # ========================================================================
    # 心跳机制（Phase 5实现）
    # ========================================================================

    def _start_heartbeat_thread(self):
        """启动心跳上报线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            logger.warning(f"Heartbeat thread already running for node {self.node_id}")
            return

        self.heartbeat_thread = Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"heartbeat_{self.node_id}"
        )
        self.heartbeat_thread.start()
        logger.info(f"Heartbeat thread started for node {self.node_id}")

    def _heartbeat_loop(self):
        """
        心跳上报循环（每10秒发送一次）

        心跳数据包含：
        - 心跳时间戳
        - Portfolio 数量
        - 队列使用情况
        - 性能指标
        """
        while self.is_running:
            try:
                # 发送心跳到 Redis
                self._send_heartbeat()

                # 更新性能指标到 Redis
                self._update_node_metrics()

                # 更新节点状态到 Redis (T068)
                self._update_node_state()

                # 更新所有Portfolio状态到 Redis (T067)
                self._update_all_portfolios_state()

                # 等待下一次心跳
                for _ in range(self.heartbeat_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in heartbeat loop for node {self.node_id}: {e}")
                time.sleep(5)  # 出错后等待5秒再重试

        logger.info(f"Heartbeat loop stopped for node {self.node_id}")

    def _is_node_id_in_use(self) -> bool:
        """
        检查node_id是否已被其他实例使用

        通过检查Redis中的心跳键和TTL来判断：
        - 心跳键不存在 → 可用
        - 心跳键存在但TTL < 10秒 → 残留数据，可用
        - 心跳键存在且TTL >= 10秒 → 被其他实例使用，不可用

        Returns:
            bool: True表示node_id已被使用，False表示可用
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                logger.warning("Failed to get Redis client for node_id check")
                return False  # 无法检查，保守策略：允许启动

            heartbeat_key = f"heartbeat:node:{self.node_id}"
            heartbeat_exists = redis_client.exists(heartbeat_key)

            if not heartbeat_exists:
                # 心跳不存在，node_id可用
                return False

            # 心跳存在，检查TTL
            ttl = redis_client.ttl(heartbeat_key)

            if ttl < 0:
                # 永不过期的键（异常情况），认为被占用
                logger.warning(f"Heartbeat for {self.node_id} has no expiration")
                return True
            elif ttl < 10:
                # TTL < 10秒，很可能是残留数据，允许启动
                logger.info(f"Heartbeat TTL ({ttl}s) is short, treating as stale data")
                return False
            else:
                # TTL >= 10秒，有其他实例在运行
                logger.warning(f"Heartbeat for {self.node_id} exists with TTL {ttl}s (in use)")
                return True

        except Exception as e:
            logger.error(f"Failed to check if node_id is in use: {e}")
            return False  # 检查失败，保守策略：允许启动

    def _cleanup_old_heartbeat_data(self):
        """
        清理旧的心跳和指标数据

        在节点启动时调用，确保没有残留的过期数据：
        - 删除旧的 heartbeat:node:{node_id}
        - 删除旧的 node:metrics:{node_id}

        云原生设计：节点重启后完全清空旧状态
        """
        try:
            # 获取 Redis 客户端
            redis_client = self._get_redis_client()
            if not redis_client:
                logger.error("Failed to get Redis client for cleanup")
                return

            # 构造键名
            heartbeat_key = f"heartbeat:node:{self.node_id}"
            metrics_key = f"node:metrics:{self.node_id}"

            # 删除旧的心跳数据
            deleted_heartbeat = redis_client.delete(heartbeat_key)
            if deleted_heartbeat:
                logger.info(f"Cleaned up old heartbeat data for node {self.node_id}")

            # 删除旧的指标数据
            deleted_metrics = redis_client.delete(metrics_key)
            if deleted_metrics:
                logger.info(f"Cleaned up old metrics data for node {self.node_id}")

            logger.debug(f"Cleanup completed for node {self.node_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup old data for node {self.node_id}: {e}")

    def _check_initial_assignments(self):
        """
        [DEPRECATED] 启动时检查Redis中的调度计划，加载分配给本节点的Portfolio

        ⚠️ 此方法已废弃！
        为了保持单向控制流，ExecutionNode 不再主动查询 Redis。
        所有 Portfolio 分配必须通过 Scheduler 的 Kafka 命令（portfolio.migrate）。

        新架构：
        - Scheduler → Kafka schedule.updates → ExecutionNode
        - ExecutionNode 启动时发送心跳，等待 Scheduler 发送迁移命令
        - 完全的中心调度，ExecutionNode 只被动接收命令

        此方法保留仅为向后兼容，不应再被调用。
        """
        # 废弃警告
        logger.warning("[DEPRECATED] _check_initial_assignments() is deprecated and should not be called.")
        logger.warning("[DEPRECATED] Portfolio assignments must come through Kafka portfolio.migrate commands from Scheduler.")

        try:
            logger.info(f"[INIT] Checking initial portfolio assignments from Redis...")

            # 获取Redis客户端
            redis_client = self._get_redis_client()
            if not redis_client:
                logger.error("[INIT] Failed to get Redis client")
                return

            # 从Redis读取调度计划
            schedule_plan_key = "schedule:plan"
            schedule_plan = redis_client.hgetall(schedule_plan_key)

            if not schedule_plan:
                logger.info("[INIT] No portfolios in schedule plan yet")
                return

            # 解析调度计划（bytes转str）
            plan_dict = {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in schedule_plan.items()
            }

            logger.info(f"[INIT] Schedule plan contains {len(plan_dict)} portfolios total")

            # 找出分配给本node的portfolio
            my_portfolios = [
                portfolio_id
                for portfolio_id, node_id in plan_dict.items()
                if node_id == self.node_id
            ]

            if not my_portfolios:
                logger.info(f"[INIT] No portfolios assigned to node {self.node_id} yet")
                return

            logger.info(f"[INIT] Found {len(my_portfolios)} portfolios assigned to this node:")
            for pid in my_portfolios:
                logger.info(f"[INIT]   - {pid[:8]}")

            # 加载每个portfolio
            for portfolio_id in my_portfolios:
                try:
                    logger.info(f"[INIT] Loading portfolio {portfolio_id[:8]}...")
                    success = self.load_portfolio(portfolio_id)
                    if success:
                        logger.info(f"[INIT] ✓ Portfolio {portfolio_id[:8]} loaded successfully")
                    else:
                        logger.error(f"[INIT] ✗ Failed to load portfolio {portfolio_id[:8]}")
                except Exception as e:
                    logger.error(f"[INIT] ✗ Error loading portfolio {portfolio_id[:8]}: {e}")

            logger.info(f"[INIT] Initial assignment check completed. Total loaded: {len(self.portfolios)}")

        except Exception as e:
            logger.error(f"[INIT] Failed to check initial assignments: {e}")

    def _send_heartbeat(self):
        """
        发送心跳到 Redis

        Redis Key: heartbeat:node:{node_id}
        Value: 当前时间戳
        TTL: 30秒（超过30秒无心跳认为节点离线）
        """
        try:
            # 获取 Redis 客户端
            redis_client = self._get_redis_client()
            if not redis_client:
                logger.error("Failed to get Redis client for heartbeat")
                return

            # 构造心跳键
            heartbeat_key = f"heartbeat:node:{self.node_id}"

            # 设置心跳值（当前时间戳）
            heartbeat_value = datetime.now().isoformat()

            # 设置键并附带TTL
            redis_client.setex(
                heartbeat_key,
                self.heartbeat_ttl,
                heartbeat_value
            )

            logger.debug(f"Heartbeat sent for node {self.node_id}")

        except Exception as e:
            logger.error(f"Failed to send heartbeat for node {self.node_id}: {e}")

    def _update_node_metrics(self):
        """
        更新节点性能指标到 Redis

        Redis Key: node:metrics:{node_id} (Hash)
        Fields:
        - portfolio_count: Portfolio 数量
        - queue_size: 平均队列大小
        - status: 节点状态 (RUNNING/PAUSED/STOPPED)
        - cpu_usage: CPU 使用率（预留）
        - memory_usage: 内存使用（预留）
        """
        try:
            # 获取 Redis 客户端
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            # 确定节点状态
            if not self.is_running:
                status = "STOPPED"
            elif self.is_paused:
                status = "PAUSED"
            else:
                status = "RUNNING"

            # 收集性能指标
            metrics = {
                "portfolio_count": str(len(self.portfolios)),
                "queue_size": str(self._get_average_queue_size()),
                "status": status,  # 节点状态
                "cpu_usage": "0.0",  # 预留，未来实现
                "memory_usage": "0",  # 预留，未来实现
                "total_events": str(self.total_event_count),
                "backpressure_count": str(self.backpressure_count),
                "dropped_events": str(self.dropped_event_count)
            }

            # 更新到 Redis
            metrics_key = f"node:metrics:{self.node_id}"
            redis_client.hset(metrics_key, mapping=metrics)

            logger.debug(f"Metrics updated for node {self.node_id}: {metrics}")

        except Exception as e:
            logger.error(f"Failed to update metrics for node {self.node_id}: {e}")

    def _get_average_queue_size(self) -> int:
        """
        获取所有 Portfolio 的平均队列大小

        Returns:
            int: 平均队列大小
        """
        try:
            if not self.portfolios:
                return 0

            total_size = 0
            # 使用ExecutionNode持有的队列字典
            for portfolio_id, queue in self.input_queues.items():
                total_size += queue.qsize()

            return total_size // len(self.input_queues)

        except Exception as e:
            logger.error(f"Failed to get average queue size: {e}")
            return 0

    def _update_portfolio_state(self, portfolio_id: str):
        """
        更新Portfolio状态到Redis (T067)

        Redis Key: portfolio:{portfolio_id}:state (Hash)
        Fields:
        - status: Portfolio运行状态 (RUNNING/PAUSED/STOPPED/RELOADING/MIGRATING)
        - queue_size: 输入队列大小
        - buffer_size: 缓存消息大小
        - position_count: 持仓数量
        - node_id: 所在节点ID

        Args:
            portfolio_id: Portfolio ID
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            # 获取Portfolio实例
            portfolio = self._portfolio_instances.get(portfolio_id)
            if not portfolio:
                logger.warning(f"Portfolio {portfolio_id} not found for state update")
                return

            # 获取队列大小
            queue_size = 0
            if portfolio_id in self.input_queues:
                queue_size = self.input_queues[portfolio_id].qsize()

            # 获取缓存大小（如果有buffer机制）
            buffer_size = 0
            # TODO: 从PortfolioProcessor获取buffer大小

            # 获取持仓数量
            position_count = 0
            if hasattr(portfolio, 'positions'):
                position_count = len(portfolio.positions)

            # 获取Portfolio状态
            status = "UNKNOWN"
            if hasattr(portfolio, 'get_status'):
                status_obj = portfolio.get_status()
                status = str(status_obj).split('.')[-1] if status_obj else "UNKNOWN"

            # 构造状态字典
            state = {
                "status": status,
                "queue_size": str(queue_size),
                "buffer_size": str(buffer_size),
                "position_count": str(position_count),
                "node_id": self.node_id
            }

            # 写入Redis
            state_key = f"portfolio:{portfolio_id}:state"
            redis_client.hset(state_key, mapping=state)

            logger.debug(f"Portfolio state updated: {portfolio_id} -> {state}")

        except Exception as e:
            logger.error(f"Failed to update portfolio state {portfolio_id}: {e}")

    def _update_all_portfolios_state(self):
        """
        更新所有Portfolio的状态到Redis (T067)

        在心跳周期中调用，批量更新所有Portfolio状态
        """
        try:
            for portfolio_id in list(self._portfolio_instances.keys()):
                self._update_portfolio_state(portfolio_id)

        except Exception as e:
            logger.error(f"Failed to update all portfolios state: {e}")

    def _update_node_state(self):
        """
        更新ExecutionNode状态到Redis (T068)

        Redis Key: execution_node:{node_id}:info (Hash)
        Fields:
        - status: 节点状态 (RUNNING/PAUSED/STOPPED)
        - portfolio_count: Portfolio数量
        - max_portfolios: 最大Portfolio数量
        - queue_usage_70pct: 队列使用率是否超过70%
        - queue_usage_95pct: 队列使用率是否超过95%
        - uptime_seconds: 运行时长（秒）
        - started_at: 启动时间
        """
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            # 确定节点状态
            if not self.is_running:
                status = "STOPPED"
            elif self.is_paused:
                status = "PAUSED"
            else:
                status = "RUNNING"

            # 计算队列使用率
            avg_queue_size = self._get_average_queue_size()
            queue_usage_70pct = avg_queue_size > 700  # 假设队列上限1000
            queue_usage_95pct = avg_queue_size > 950

            # 计算运行时长
            uptime_seconds = 0
            if self.started_at:
                try:
                    from datetime import datetime
                    started = datetime.fromisoformat(self.started_at)
                    uptime_seconds = int((datetime.now() - started).total_seconds())
                except Exception:
                    pass

            # 构造状态字典
            state = {
                "status": status,
                "portfolio_count": str(len(self.portfolios)),
                "max_portfolios": str(self.max_portfolios),
                "queue_usage_70pct": str(queue_usage_70pct),
                "queue_usage_95pct": str(queue_usage_95pct),
                "uptime_seconds": str(uptime_seconds),
                "started_at": self.started_at or ""
            }

            # 写入Redis
            info_key = f"execution_node:{self.node_id}:info"
            redis_client.hset(info_key, mapping=state)

            logger.debug(f"Node state updated: {self.node_id} -> {state}")

        except Exception as e:
            logger.error(f"Failed to update node state {self.node_id}: {e}")

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
    # 调度更新订阅（Phase 5实现 - T046）
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
            print(f"[INFO] Subscribed to {topic} topic")

            while self.is_running:
                try:
                    # 消费消息（超时1秒）
                    # GinkgoConsumer.consumer 是底层的 KafkaConsumer
                    messages = self.schedule_updates_consumer.consumer.poll(timeout_ms=1000)

                    if not messages:
                        continue

                    # 处理每个消息
                    for tp, records in messages.items():
                        for msg in records:
                            self._handle_schedule_update(msg)

                except Exception as e:
                    logger.error(f"Error consuming schedule updates: {e}")
                    time.sleep(1)  # 出错后等待1秒再重试

        except Exception as e:
            logger.error(f"Failed to start schedule updates consumer: {e}")
        finally:
            logger.info(f"Schedule updates loop stopped for node {self.node_id}")

    def _handle_schedule_update(self, msg):
        """
        处理调度更新消息

        Args:
            msg: Kafka消息对象（GinkgoConsumer已反序列化，msg.value是dict）

        消息格式（JSON）：
        {
            "command": "portfolio.reload" | "portfolio.migrate" | "node.shutdown",
            "portfolio_id": "portfolio_uuid",
            "target_node": "target_node_id",  // 仅portfolio.migrate需要
            "timestamp": "2026-01-06T10:00:00"
        }
        """
        try:
            # GinkgoConsumer 已经反序列化了消息，msg.value 直接是 dict
            command_data = msg.value

            command = command_data.get('command')
            portfolio_id = command_data.get('portfolio_id', '')
            timestamp = command_data.get('timestamp')
            target_node = command_data.get('target_node', '')
            source_node = command_data.get('source_node', '')

            logger.info(f"{'─'*80}")
            logger.info(f"[KAFKA] Received schedule command: {command}")
            logger.info(f"  Portfolio ID: {portfolio_id[:8] if portfolio_id else 'N/A'}")
            logger.info(f"  Source Node:  {source_node if source_node else 'None (new assignment)'}")
            logger.info(f"  Target Node:  {target_node}")
            logger.info(f"  Timestamp:    {timestamp}")
            logger.info(f"{'─'*80}")

            # 路由到不同的处理方法
            if command == 'portfolio.reload':
                self._handle_portfolio_reload(portfolio_id, command_data)
            elif command == 'portfolio.migrate':
                self._handle_portfolio_migrate(portfolio_id, command_data)
            elif command == 'node.pause':
                self._handle_node_pause(command_data)
            elif command == 'node.resume':
                self._handle_node_resume(command_data)
            elif command == 'node.shutdown':
                self._handle_node_shutdown(command_data)
            else:
                logger.warning(f"Unknown schedule command: {command}")

        except Exception as e:
            logger.error(f"Error handling schedule update: {e}")

    def _handle_portfolio_reload(self, portfolio_id: str, command_data: dict):
        """
        处理Portfolio重新加载命令（T048 - 完整实现）

        完整流程：
        1. 检查Portfolio是否存在
        2. 调用Portfolio.graceful_reload()
        3. 处理消息缓存（如果需要）
        4. 验证重载结果

        Args:
            portfolio_id: Portfolio ID
            command_data: 命令数据
        """
        logger.info(f"Reloading portfolio {portfolio_id}")

        try:
            # 检查Portfolio是否存在
            if portfolio_id not in self._portfolio_instances:
                logger.warning(f"Portfolio {portfolio_id} not found in node {self.node_id}")
                return

            # 获取Portfolio实例
            portfolio = self._portfolio_instances[portfolio_id]

            # 调用优雅重载
            logger.info(f"Calling graceful_reload() for portfolio {portfolio_id}")
            success = portfolio.graceful_reload(timeout=30)

            if success:
                logger.info(f"Portfolio {portfolio_id} reloaded successfully")
            else:
                logger.error(f"Portfolio {portfolio_id} reload failed")

        except Exception as e:
            logger.error(f"Failed to reload portfolio {portfolio_id}: {e}")

    def _handle_portfolio_migrate(self, portfolio_id: str, command_data: dict):
        """
        处理Portfolio迁移命令（T050 - 完整实现）

        完整流程：
        1. 检查是否是迁移到本节点（接收端）
        2. 如果是迁出本节点：优雅停止并移除
        3. 更新调度计划

        Args:
            portfolio_id: Portfolio ID
            command_data: 命令数据，包含target_node
        """
        target_node = command_data.get('target_node')

        logger.info(f"[MIGRATE] Processing portfolio migration: {portfolio_id[:8]} -> {target_node}")

        try:
            # 情况 1: 迁移到本节点（接收端）
            if target_node == self.node_id:
                logger.info(f"[MIGRATE] Portfolio {portfolio_id[:8]} is being migrated TO this node ({self.node_id})")
                logger.info(f"[MIGRATE] Starting portfolio receive and load process...")
                self._receive_portfolio(portfolio_id)
                return

            # 情况 2: 从本节点迁出（发送端）
            if portfolio_id not in self._portfolio_instances:
                logger.warning(f"[MIGRATE] Portfolio {portfolio_id[:8]} not found in node {self.node_id} (nothing to migrate away)")
                return

            logger.info(f"[MIGRATE] Migrating portfolio {portfolio_id[:8]} AWAY from this node")

            # 获取Portfolio实例
            portfolio = self._portfolio_instances[portfolio_id]

            # 设置迁移状态
            portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.MIGRATING)
            logger.info(f"[MIGRATE] Set portfolio status to MIGRATING")

            # 停止PortfolioProcessor
            if portfolio_id in self.portfolios:
                processor = self.portfolios[portfolio_id]
                processor.stop()
                logger.info(f"[MIGRATE] Processor stopped for portfolio {portfolio_id[:8]}")

            # 从本节点移除
            with self.portfolio_lock:
                if portfolio_id in self.portfolios:
                    del self.portfolios[portfolio_id]

                if portfolio_id in self._portfolio_instances:
                    del self._portfolio_instances[portfolio_id]

            # 从InterestMap移除订阅
            # TODO: 实现 InterestMap.remove_portfolio() 方法
            logger.info(f"[MIGRATE] Portfolio {portfolio_id[:8]} removed from node {self.node_id}")
            logger.info(f"[MIGRATE] Migration away completed successfully")

        except Exception as e:
            logger.error(f"[MIGRATE] Failed to migrate portfolio {portfolio_id[:8]}: {e}")

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
                self._update_node_metrics()
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

    def _handle_node_pause(self, command_data: dict):
        """
        处理节点暂停命令

        Args:
            command_data: 命令数据
        """
        logger.info(f"Received node pause command for {self.node_id}")
        self.pause()

    def _handle_node_resume(self, command_data: dict):
        """
        处理节点恢复命令

        Args:
            command_data: 命令数据
        """
        logger.info(f"Received node resume command for {self.node_id}")
        self.resume()

    def _handle_node_shutdown(self, command_data: dict):
        """
        处理节点关闭命令

        Args:
            command_data: 命令数据
        """
        logger.info(f"Received node shutdown command for {self.node_id}")

        try:
            # 优雅关闭节点
            logger.info(f"Shutting down node {self.node_id} gracefully")

            # TODO: 实现优雅关闭流程
            # 1. 停止接收新消息
            # 2. 等待现有消息处理完成
            # 3. 关闭所有Portfolio
            # 4. 退出

            self.stop()

        except Exception as e:
            logger.error(f"Failed to shutdown node {self.node_id}: {e}")
