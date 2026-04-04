# Upstream: Kafka（订阅orders.submission topic）
# Downstream: TradeGateway（调用执行订单）、Kafka（发布orders.feedback topic）
# Role: 交易网关适配器，订阅Kafka订单并执行，监控订单成交并发布回报


"""
交易网关适配器 (TradeGatewayAdapter)

TradeGatewayAdapter负责实盘交易的订单执行流程：
- 订阅Kafka orders.submission topic，接收ExecutionNode提交的订单
- 调用TradeGateway执行订单（同步，确认提交）
- 监控订单成交状态（独立线程异步查询）
- 发布订单回报到Kafka orders.feedback topic

架构设计：
- 继承Thread：作为独立线程运行在LiveCore中
- 双线程模型：
  1. 主线程：订阅Kafka orders.submission，处理订单提交
  2. 监控线程：定期查询订单成交状态，发布回报到Kafka

关键要点：
- pending_orders：保存待成交订单 {order_id: order_info}
- 同步提交：submit_order()只确认提交，不等待成交
- 异步监控：_monitor_orders_loop()定期查询订单状态
- 事件发布：订单成交后发布EventOrderPartiallyFilled到Kafka

MVP阶段（Phase 3）：
- 基础Kafka订阅和消息处理
- 调用TradeGateway执行订单
- 模拟订单成交监控（Phase 3使用模拟成交）

Phase 4扩展：
- 真实券商API集成
- 订单对账机制
- 异常处理和重试
"""

from threading import Thread
from typing import List, Dict, Optional
from datetime import datetime
import time

from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.bases.base_broker import BaseBroker
from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer, GinkgoProducer
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG


class TradeGatewayAdapter(Thread):
    """交易网关适配器，订阅Kafka订单并执行"""

    def __init__(self, brokers: List[BaseBroker], order_timeout: int = 30):
        """
        初始化TradeGatewayAdapter

        Args:
            brokers: 券商接口列表
            order_timeout: 订单超时时间（秒），默认30秒
        """
        super().__init__(daemon=True)

        # 创建TradeGateway实例
        self.gateway = TradeGateway(brokers=brokers)

        # Kafka消费者（订阅orders.submission）
        self.kafka_consumer: Optional[GinkgoConsumer] = None

        # Kafka生产者（发布orders.feedback）
        self.kafka_producer = GinkgoProducer()

        # 订单超时配置
        self.order_timeout = order_timeout  # 默认30秒超时

        # 订单统计
        self.total_orders = 0  # 总订单数
        self.filled_orders = 0  # 已成交订单
        self.expired_orders = 0  # 超时订单
        self.failed_orders = 0  # 失败订单

        # 运行状态
        self.is_running = False

        # 设置日志分类
        GLOG.set_log_category("component")

    def run(self):
        """
        运行TradeGatewayAdapter：订阅Kafka orders.submission topic

        主线程职责：
        1. 订阅Kafka orders.submission topic
        2. 接收订单并解析
        3. 调用TradeGateway执行（同步，确认提交）
        4. 订单状态由数据库管理
        """
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES
        from datetime import datetime

        self.is_running = True
        GLOG.INFO("TradeGatewayAdapter starting...")

        # 创建Kafka消费者
        self.kafka_consumer = GinkgoConsumer(
            KafkaTopics.ORDERS_SUBMISSION,
            group_id="trade_gateway_adapter"
        )

        # 启动订单监控线程
        self._start_monitor_thread()

        GLOG.INFO("TradeGatewayAdapter started, consuming orders...")

        # 发送启动通知
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                "TradeGatewayAdapter启动成功",
                level="INFO",
                module="TradeGatewayAdapter",
                details={
                    "组件": "TradeGatewayAdapter",
                    "Broker数量": len(self.gateway.brokers) if hasattr(self.gateway, 'brokers') else 0,
                    "启动时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        except Exception as notify_error:
            GLOG.WARN(f"Failed to send start notification: {notify_error}")

        # 消费订单提交
        while self.is_running:
            try:
                for message in self.kafka_consumer.consumer:
                    if not self.is_running:
                        break

                    order_data = message.value

                    # 处理订单
                    self._process_order(order_data)

                    # 手动提交offset
                    self.kafka_consumer.commit()

            except Exception as e:
                if self.is_running:
                    GLOG.ERROR(f"Error consuming orders: {e}")

        GLOG.INFO("TradeGatewayAdapter stopped")

        # 发送停止通知
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                "TradeGatewayAdapter已停止",
                level="INFO",
                module="TradeGatewayAdapter",
                details={
                    "组件": "TradeGatewayAdapter",
                    "停止时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "总订单数": self.total_orders,
                    "已成交": self.filled_orders,
                    "超时": self.expired_orders,
                    "失败": self.failed_orders,
                },
            )
        except Exception as notify_error:
            GLOG.WARN(f"Failed to send stop notification: {notify_error}")

    def _process_order(self, order_data: dict):
        """
        处理订单：调用TradeGateway执行

        Args:
            order_data: 订单数据（字典）
        """
        from ginkgo.entities import Order
        from ginkgo.enums import ORDERSTATUS_TYPES

        # ORDER IDEMPOTENCY: 检查订单是否已存在 - order_crud.get_order_by_uuid(order_id)
        # from ginkgo.data.crud import OrderCRUD; existing_order = order_crud.get_order_by_uuid(order_id)
        # if existing_order.status in [SUBMITTED, PARTIAL_FILLED, FILLED]: return  # 跳过重复订单

        # 更新总订单统计
        self.total_orders += 1

        try:
            # 构造Order对象
            order = Order(
                portfolio_id=order_data['portfolio_id'],
                engine_id=order_data.get('engine_id', 'live_engine'),
                run_id=order_data.get('run_id', 'live_run'),
                code=order_data['code'],
                direction=DIRECTION_TYPES(order_data['direction']),
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=order_data['volume'],
                limit_price=order_data['limit_price']
            )

            # 提交到TradeGateway（同步，确认提交）
            # TODO: Phase 3调用TradeGateway.submit_order()
            # MVP阶段：模拟提交成功
            GLOG.INFO(f"Order {order.uuid} submitted to TradeGateway (simulation)")

            # ORDER PERSISTENCE: 更新订单状态为 SUBMITTED - order_crud.update(order)
            # from ginkgo.data.crud import OrderCRUD; order.status = ORDERSTATUS_TYPES.SUBMITTED; order_crud.update(order)

        except Exception as e:
            # 更新失败订单统计
            self.failed_orders += 1
            GLOG.ERROR(f"Error processing order {order_data.get('code', 'unknown')}: {e}")
            import traceback
            traceback.print_exc()

    def _start_monitor_thread(self):
        """启动订单监控线程"""
        monitor_thread = Thread(target=self._monitor_orders_loop, daemon=True)
        monitor_thread.start()
        GLOG.INFO("Order monitor thread started")

    def _monitor_orders_loop(self):
        """
        订单监控循环：检查订单成交状态

        监控线程职责：
        1. 定期从数据库查询待成交订单状态
        2. 检测到成交后生成EventOrderPartiallyFilled
        3. 发布到Kafka orders.feedback topic
        4. 更新数据库订单状态

        MVP阶段：模拟成交逻辑（提交1秒后自动成交）
        Phase 4：调用TradeGateway.get_order_status()查询真实状态
        """
        GLOG.INFO("Order monitor loop running")

        while self.is_running:
            try:
                # 检查所有待成交订单
                self._check_order_status()

                # 休眠1秒
                time.sleep(1)

            except Exception as e:
                GLOG.ERROR(f"Error in monitor loop: {e}")

        GLOG.INFO("Order monitor loop stopped")

    def _check_order_status(self):
        """
        检查订单成交状态（基于数据库查询）

        MVP阶段：模拟成交逻辑（提交1秒后自动成交）
        Phase 4：调用TradeGateway.get_order_status()查询真实状态
        """
        from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled
        from ginkgo.data.services import order_service
        from ginkgo.enums import ORDERSTATUS_TYPES
        from decimal import Decimal

        current_time = datetime.now()

        # ORDER QUERY: 从数据库查询待成交订单
        pending_orders = order_service.get_orders_by_status([
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.PARTIAL_FILLED
        ])

        if not pending_orders:
            return

        # 遍历待成交订单
        for order in pending_orders:
            try:
                # 计算订单已存在时间
                submitted_at = order.timestamp or order.create_time
                if not submitted_at:
                    continue

                time_elapsed = (current_time - submitted_at).total_seconds()

                # 检查是否超时
                if time_elapsed >= self.order_timeout:
                    GLOG.WARN(f"Order {order.uuid[:8]} expired (> {self.order_timeout}s)")
                    # TODO: 更新订单状态为EXPIRED
                    # order.status = ORDERSTATUS_TYPES.EXPIRED
                    # order_service.update_order(order)
                    self.expired_orders += 1
                    continue

                # MVP阶段：模拟成交（1秒后自动成交）
                if time_elapsed >= 1.0 and order.status == ORDERSTATUS_TYPES.SUBMITTED:
                    # 生成成交事件
                    fill_event = EventOrderPartiallyFilled(
                        order=order,
                        filled_quantity=float(order.volume),  # 全部成交
                        fill_price=float(order.limit_price),  # 使用limit_price
                        timestamp=current_time,
                        commission=Decimal('5.25'),  # 模拟手续费
                        portfolio_id=order.portfolio_id,
                        engine_id=order.engine_id,
                        run_id=order.run_id
                    )

                    # 发布到Kafka
                    self._publish_fill_event(fill_event)

                    # ORDER PERSISTENCE: 更新订单成交状态到数据库
                    # order.status = ORDERSTATUS_TYPES.FILLED
                    # order.transaction_volume = order.volume
                    # order_service.update_order(order)

                    # 更新成交统计
                    self.filled_orders += 1
                    GLOG.INFO(f"Order {order.uuid[:8]} filled (simulation)")

            except Exception as e:
                GLOG.ERROR(f"Error checking order {order.uuid[:8]}: {e}")
                continue

        # 定期打印统计信息（每60次检查，约1分钟）
        if self.total_orders % 60 == 0 and self.total_orders > 0:
            self._print_statistics()

    def _publish_fill_event(self, fill_event):
        """
        发布成交事件到Kafka

        Args:
            fill_event: EventOrderPartiallyFilled事件
        """
        try:
            from ginkgo.interfaces.dtos import OrderFeedbackDTO

            # 使用DTO序列化事件
            feedback_dto = OrderFeedbackDTO(
                order_id=fill_event.order.uuid,
                portfolio_id=fill_event.portfolio_id,
                engine_id=fill_event.engine_id,
                run_id=fill_event.run_id,
                code=fill_event.order.code,
                direction=fill_event.order.direction.value,
                filled_quantity=fill_event.filled_quantity,
                fill_price=fill_event.fill_price,
                timestamp=fill_event.timestamp.isoformat()
            )

            # 发布到Kafka
            self.kafka_producer.send(KafkaTopics.ORDERS_FEEDBACK, feedback_dto.model_dump_json())
            GLOG.INFO(f"Fill event sent to Kafka for order {fill_event.order.uuid[:8]}")

        except Exception as e:
            GLOG.ERROR(f"Error publishing fill event: {e}")

    def _print_statistics(self):
        """打印订单统计信息"""
        from ginkgo.data.services import order_service
        from ginkgo.enums import ORDERSTATUS_TYPES

        # 从数据库查询待成交订单数量
        pending_orders = order_service.get_orders_by_status([
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.PARTIAL_FILLED
        ])
        pending_count = len(pending_orders) if pending_orders else 0

        GLOG.INFO(f"{'='*60}")
        GLOG.INFO(f"TradeGatewayAdapter Order Statistics:")
        GLOG.INFO(f"  Total orders:    {self.total_orders}")
        GLOG.INFO(f"  Filled orders:   {self.filled_orders}")
        GLOG.INFO(f"  Expired orders:  {self.expired_orders}")
        GLOG.INFO(f"  Failed orders:   {self.failed_orders}")
        GLOG.INFO(f"  Pending orders:  {pending_count} (from DB)")
        GLOG.INFO(f"  Fill rate:       {self.filled_orders/max(self.total_orders,1)*100:.1f}%")
        GLOG.INFO(f"{'='*60}")

    def get_statistics(self) -> dict:
        """
        获取订单统计信息

        Returns:
            dict: 订单统计字典
        """
        from ginkgo.data.services import order_service
        from ginkgo.enums import ORDERSTATUS_TYPES

        # 从数据库查询待成交订单数量
        pending_orders = order_service.get_orders_by_status([
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.PARTIAL_FILLED
        ])
        pending_count = len(pending_orders) if pending_orders else 0

        return {
            "total_orders": self.total_orders,
            "filled_orders": self.filled_orders,
            "expired_orders": self.expired_orders,
            "failed_orders": self.failed_orders,
            "pending_orders": pending_count,
            "fill_rate": self.filled_orders / max(self.total_orders, 1),
            "order_timeout": self.order_timeout
        }

    def stop(self):
        """
        停止TradeGatewayAdapter - 优雅关闭流程

        核心策略：
        1. 设置停止标志（通知主循环退出）
        2. 打印最终统计
        3. 提交 Kafka offset
        4. 关闭 Kafka 连接
        5. 等待监控线程结束
        """
        GLOG.INFO("")
        GLOG.INFO("═══════════════════════════════════════════════════════")
        GLOG.INFO("🛑 Stopping TradeGatewayAdapter")
        GLOG.INFO("═══════════════════════════════════════════════════════")

        # 0. 设置停止标志
        GLOG.INFO("[Step 1] Setting stop flag...")
        self.is_running = False
        GLOG.INFO("  ✅ Stop flag set")

        # 1. 打印最终统计
        GLOG.INFO("[Step 2] Printing final statistics...")
        self._print_statistics()

        # 2. 关闭 Kafka Consumer
        GLOG.INFO("[Step 3] Closing Kafka Consumer...")
        if self.kafka_consumer:
            try:
                # 提交最终 offset
                self.kafka_consumer.commit()
                GLOG.INFO("  ✅ Final offset committed")

                # 关闭 consumer
                self.kafka_consumer.close()
                GLOG.INFO("  ✅ Kafka consumer closed")
            except Exception as e:
                GLOG.ERROR(f"  ✗ Error closing Kafka consumer: {e}")
        else:
            GLOG.INFO("  ℹ️  No Kafka consumer to close")

        # 3. 关闭 Kafka Producer
        GLOG.INFO("[Step 4] Closing Kafka Producer...")
        if self.kafka_producer:
            try:
                self.kafka_producer.close()
                GLOG.INFO("  ✅ Kafka producer closed")
            except Exception as e:
                GLOG.ERROR(f"  ✗ Error closing Kafka producer: {e}")
        else:
            GLOG.INFO("  ℹ️  No Kafka producer to close")

        # 4. 等待监控线程结束
        GLOG.INFO("[Step 5] Waiting for monitor thread...")
        if hasattr(self, 'monitor_thread') and self.monitor_thread:
            if self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
                if self.monitor_thread.is_alive():
                    GLOG.WARN("  ⚠️  Monitor thread did not finish gracefully")
                else:
                    GLOG.INFO("  ✅ Monitor thread finished")
        else:
            GLOG.INFO("  ℹ️  No monitor thread running")

        GLOG.INFO("")
        GLOG.INFO("═══════════════════════════════════════════════════════")
        GLOG.INFO("✅ TradeGatewayAdapter stopped gracefully")
        GLOG.INFO("═══════════════════════════════════════════════════════")
        GLOG.INFO("")
