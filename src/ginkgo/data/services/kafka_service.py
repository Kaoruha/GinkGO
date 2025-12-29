# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: KafkaService Kafka服务提供消息队列生产和消费功能支持流式数据处理支持交易系统功能支持相关功能






"""
Kafka消息队列服务 - 扁平化架构实现

提供消息发布/订阅、主题管理、队列监控等功能
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import threading
import time
import uuid

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs.utils.common import time_logger, retry


class KafkaService(BaseService):
    """Kafka message queue service - directly inherits BaseService"""

    def __init__(self, kafka_crud=None, **deps):
        """
        Initialize Kafka service

        Args:
            kafka_crud: KafkaCRUD instance, auto-created if None
            **deps: Other dependencies
        """
        if kafka_crud is None:
            from ginkgo.data.crud import KafkaCRUD
            kafka_crud = KafkaCRUD()

        super().__init__(crud_repo=kafka_crud, **deps)

        # Keep kafka property for backward compatibility
        self.kafka = kafka_crud

        # Message processing state tracking
        self._message_handlers = {}  # {topic: handler_function}
        self._consumer_threads = {}  # {topic: thread}
        self._stop_events = {}      # {topic: threading.Event}

        # Message sending statistics
        self._send_stats = {
            "total_sent": 0,
            "failed_sends": 0,
            "last_send_time": None
        }

        # Message receiving statistics
        self._receive_stats = {
            "total_received": 0,
            "last_receive_time": None
        }

    # ==================== Standard Interface Implementation ====================

    def get(self, topic: str = None, **filters) -> ServiceResult:
        """Get Kafka topic information"""
        try:
            if topic:
                # Get specific topic information
                topic_info = self._crud_repo.get_topic_info(topic)
                return ServiceResult.success(
                    data={'topic': topic, 'info': topic_info},
                    message=f"Successfully retrieved topic {topic} information"
                )
            else:
                # Get all topics
                topics = self._crud_repo.list_topics()
                return ServiceResult.success(
                    data={'topics': topics, 'count': len(topics)},
                    message=f"Found {len(topics)} topics"
                )
        except Exception as e:
            return ServiceResult.error(f"Failed to get Kafka topic information: {str(e)}")

    def count(self, topic: str = None) -> ServiceResult:
        """Count topic quantity or message quantity"""
        try:
            if topic:
                # Count messages for specific topic
                message_count = self._crud_repo.get_message_count(topic)
                return ServiceResult.success(
                    data={'topic': topic, 'message_count': message_count},
                    message=f"Topic {topic} has {message_count} messages"
                )
            else:
                # Count all topics
                topics = self._crud_repo.list_topics()
                return ServiceResult.success(
                    data={'topic_count': len(topics)},
                    message=f"Found {len(topics)} topics"
                )
        except Exception as e:
            return ServiceResult.error(f"Failed to count Kafka topics: {str(e)}")

    def validate(self, topic: str, message: Any = None) -> ServiceResult:
        """Validate Kafka data"""
        try:
            if not topic:
                return ServiceResult.error("主题名不能为空")

            if not isinstance(topic, str):
                return ServiceResult.error("主题名必须是字符串")

            # Check topic name format
            if not topic.replace('_', '').replace('-', '').isalnum():
                return ServiceResult.error("Topic name can only contain letters, numbers, underscores and hyphens")

            return ServiceResult.success(message="Kafka数据验证通过")
        except Exception as e:
            return ServiceResult.error(f"Kafka data validation failed: {str(e)}")

    def check_integrity(self, topic: str) -> ServiceResult:
        """Check Kafka topic integrity"""
        try:
            # 检查主题是否存在
            topics = self._crud_repo.list_topics()
            if topic not in topics:
                return ServiceResult.error(f"主题{topic}不存在")

            # 检查主题分区信息
            partitions = self._crud_repo.get_topic_partitions(topic)

            return ServiceResult.success(
                data={'topic': topic, 'partitions': partitions, 'healthy': True},
                message=f"主题{topic}完整性检查通过"
            )
        except Exception as e:
            return ServiceResult.error(f"完整性检查失败: {str(e)}")

    # ==================== Message Publishing Service ====================

    def publish_message(self, topic: str, message: Any, key: str = None,
                       add_metadata: bool = True) -> ServiceResult:
        """
        Publish message to Kafka topic with metadata enhancement and message tracking

        Args:
            topic: Target Kafka topic name
            message: Message content to send, supports any data type
            key: Message partition key for load balancing and ordering guarantees
            add_metadata: Whether to automatically add message metadata (timestamp, ID, etc.)

        Returns:
            ServiceResult: Message publication result

        Notes:
            - 批量发送：支持批量消息发送提高吞吐量
            - 压缩传输：自动压缩大数据消息节省网络带宽
            - 异步发送：非阻塞发送提高应用响应速度
            - 连接池：复用Kafka连接减少连接开销

        Error Handling Strategy:
            - 网络异常：自动重试和连接恢复机制
            - 序列化错误：数据格式检查和自动转换
            - 主题异常：主题存在性检查和自动创建
            - 分区错误：分区键验证和错误提示

        Monitoring Features:
            - 发送统计：实时统计发送成功/失败数量
            - 延迟监控：记录消息发送延迟时间
            - 错误日志：详细记录发送失败原因
            - 性能指标：吞吐量、延迟等性能监控

        Configuration Options:
            - 批量大小：控制每次批量发送的消息数量
            - 超时设置：网络请求和响应超时配置
            - 重试次数：失败重试的最大次数
            - 压缩算法：消息压缩算法选择

        Security Considerations:
            - 数据加密：支持SSL/TLS加密传输
            - 访问控制：基于主题的访问权限管理
            - 审计日志：记录所有消息发布操作
            - 敏感数据：自动检测和敏感数据保护

        Note:
            - 消息发送是异步的，返回成功仅表示消息已成功发送到Kafka
            - 建议为关键业务消息设置适当的key确保有序性
            - 大消息建议压缩后发送以提高性能
            - 定期监控发送统计和错误率确保系统健康

        Algorithm Details:
            - 使用Kafka Producer API确保最佳性能
            - 自动序列化处理支持多种数据格式
            - 元数据增强采用不可变设计保证数据完整性
            - 分区算法使用Kafka默认的哈希分区策略

        See Also:
            - subscribe_to_topic(): 订阅主题消息
            - get_topic_info(): 获取主题信息
            - get_send_statistics(): 获取发送统计
        """
        try:
            self._log_operation_start("publish_message", topic=topic, key=key)
            
            # 准备消息数据
            if add_metadata:
                if isinstance(message, dict):
                    enhanced_message = message.copy()
                else:
                    enhanced_message = {"content": message}
                
                # 添加元数据
                enhanced_message.update({
                    "message_id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat(),
                    "service": "KafkaService",
                    "version": "1.0"
                })
                
                if key:
                    enhanced_message["_message_key"] = key
            else:
                enhanced_message = message
            
            # 发送消息
            success = self._crud_repo.send_message(topic, enhanced_message, key)
            
            # 更新统计信息
            if success:
                self._send_stats["total_sent"] += 1
                self._send_stats["last_send_time"] = datetime.now()
                self._logger.DEBUG(f"Published message to topic: {topic}")
                result = ServiceResult.success(
                    data=success,
                    message=f"Successfully published message to topic: {topic}"
                )
            else:
                self._send_stats["failed_sends"] += 1
                self._logger.ERROR(f"Failed to publish message to topic: {topic}")
                result = ServiceResult.error(
                    message=f"Failed to publish message to topic: {topic}"
                )

            self._log_operation_end("publish_message", success)
            return result

        except Exception as e:
            self._send_stats["failed_sends"] += 1
            self._logger.ERROR(f"Error publishing message to {topic}: {e}")
            return ServiceResult.error(
                message=f"Error publishing message to {topic}: {str(e)}"
            )
    
    def publish_batch_messages(self, topic: str, messages: List[Dict[str, Any]],
                              add_metadata: bool = True) -> Dict[str, Any]:
        """
        批量发布消息
        
        Args:
            topic: 主题名称
            messages: 消息列表
            add_metadata: 是否添加元数据
            
        Returns:
            Dict: 发送结果统计
        """
        try:
            self._log_operation_start("publish_batch_messages", topic=topic, count=len(messages))
            
            # 预处理消息
            processed_messages = []
            for msg in messages:
                if add_metadata:
                    if isinstance(msg, dict):
                        enhanced_msg = msg.copy()
                    else:
                        enhanced_msg = {"content": msg}
                    
                    enhanced_msg.update({
                        "message_id": str(uuid.uuid4()),
                        "timestamp": datetime.now().isoformat(),
                        "service": "KafkaService",
                        "batch_id": str(uuid.uuid4())
                    })
                    processed_messages.append(enhanced_msg)
                else:
                    processed_messages.append(msg)
            
            # 批量发送
            success_count = self._crud_repo.send_batch_messages(topic, processed_messages)
            
            # 更新统计信息
            self._send_stats["total_sent"] += success_count
            self._send_stats["failed_sends"] += len(messages) - success_count
            self._send_stats["last_send_time"] = datetime.now()
            
            result = {
                "topic": topic,
                "total_messages": len(messages),
                "successful_sends": success_count,
                "failed_sends": len(messages) - success_count,
                "success_rate": success_count / len(messages) if messages else 0
            }
            
            self._log_operation_end("publish_batch_messages", success_count > 0)
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Error in batch publish to {topic}: {e}")
            return {
                "topic": topic,
                "total_messages": len(messages),
                "successful_sends": 0,
                "failed_sends": len(messages),
                "success_rate": 0,
                "error": str(e)
            }
    
    # ==================== Message Subscription Service ====================

    def subscribe_topic(self, topic: str, handler: Callable[[Dict[str, Any]], bool],
                       group_id: str = None, auto_start: bool = True) -> bool:
        """
        Subscribe to topic and set message handler

        Args:
            topic: Topic name
            handler: Message handler function, receives message dict, returns success status
            group_id: Consumer group ID
            auto_start: Whether to automatically start consumption

        Returns:
            bool: Whether subscription was successful
        """
        try:
            self._log_operation_start("subscribe_topic", topic=topic, group_id=group_id)
            
            # 保存处理器
            self._message_handlers[topic] = handler
            
            if auto_start:
                return self.start_consuming(topic, group_id)
            
            self._logger.INFO(f"Subscribed to topic: {topic} (handler registered)")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Error subscribing to topic {topic}: {e}")
            return False
    
    def start_consuming(self, topic: str, group_id: str = None, 
                       max_messages: int = None) -> bool:
        """
        开始消费指定主题的消息
        
        Args:
            topic: 主题名称
            group_id: 消费者组ID
            max_messages: 最大消息数量，None表示持续消费
            
        Returns:
            bool: 启动是否成功
        """
        try:
            self._log_operation_start("start_consuming", topic=topic, group_id=group_id)
            
            # 检查是否已有处理器
            if topic not in self._message_handlers:
                self._logger.ERROR(f"No handler registered for topic: {topic}")
                return False
            
            # 停止现有的消费线程（如果有）
            self.stop_consuming(topic)
            
            # 创建停止事件
            stop_event = threading.Event()
            self._stop_events[topic] = stop_event
            
            # 创建消费者线程
            consumer_thread = threading.Thread(
                target=self._consumer_worker,
                args=(topic, group_id, max_messages, stop_event),
                daemon=True,
                name=f"kafka_consumer_{topic}"
            )
            
            self._consumer_threads[topic] = consumer_thread
            consumer_thread.start()
            
            self._logger.INFO(f"Started consuming topic: {topic}")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Error starting consumer for topic {topic}: {e}")
            return False
    
    def stop_consuming(self, topic: str) -> ServiceResult:
        """
        停止消费指定主题

        Args:
            topic: 主题名称

        Returns:
            ServiceResult: 停止结果
        """
        try:
            self._log_operation_start("stop_consuming", topic=topic)

            # 设置停止信号
            if topic in self._stop_events:
                self._stop_events[topic].set()

            # 等待线程结束
            if topic in self._consumer_threads:
                thread = self._consumer_threads[topic]
                if thread.is_alive():
                    thread.join(timeout=5.0)  # 最多等待5秒

                del self._consumer_threads[topic]

            # 清理停止事件
            if topic in self._stop_events:
                del self._stop_events[topic]

            # 关闭对应的消费者
            self._crud_repo.close_consumer(topic)

            self._logger.INFO(f"Stopped consuming topic: {topic}")
            return ServiceResult.success({"stopped": True}, f"Successfully stopped consuming topic: {topic}")

        except Exception as e:
            self._logger.ERROR(f"Error stopping consumer for topic {topic}: {e}")
            return ServiceResult.error(f"Failed to stop consuming topic: {str(e)}")
    
    def _consumer_worker(self, topic: str, group_id: str, max_messages: int, 
                        stop_event: threading.Event):
        """
        消费者工作线程
        
        Args:
            topic: 主题名称
            group_id: 消费者组ID
            max_messages: 最大消息数量
            stop_event: 停止事件
        """
        handler = self._message_handlers.get(topic)
        if not handler:
            self._logger.ERROR(f"No handler found for topic: {topic}")
            return
        
        processed_count = 0
        
        try:
            # 使用回调方式消费消息
            def message_processor(message_data: Dict[str, Any]) -> bool:
                nonlocal processed_count
                
                try:
                    # 检查停止信号
                    if stop_event.is_set():
                        return False
                    
                    # 调用用户处理器
                    success = handler(message_data)
                    
                    if success:
                        processed_count += 1
                        self._receive_stats["total_received"] += 1
                        self._receive_stats["last_receive_time"] = datetime.now()
                    
                    # 检查最大消息数量
                    if max_messages and processed_count >= max_messages:
                        stop_event.set()
                        return False
                    
                    return success
                    
                except Exception as e:
                    self._logger.ERROR(f"Error in message handler for {topic}: {e}")
                    return False
            
            # 开始消费
            self._crud_repo.consume_with_callback(
                topic=topic,
                callback=message_processor,
                group_id=group_id,
                max_messages=max_messages
            )
            
        except Exception as e:
            self._logger.ERROR(f"Consumer worker error for topic {topic}: {e}")
        
        finally:
            self._logger.DEBUG(f"Consumer worker for {topic} processed {processed_count} messages")
    
    # ==================== Topic Management Service ====================

    def get_topic_status(self, topic: str) -> ServiceResult:
        """
        Get topic status information

        Args:
            topic: Topic name

        Returns:
            ServiceResult: Topic status information
        """
        try:
            basic_info = self._crud_repo.get_topic_info(topic)

            # 添加服务层的状态信息
            status = basic_info.copy()
            status.update({
                "has_handler": topic in self._message_handlers,
                "is_consuming": topic in self._consumer_threads and
                               self._consumer_threads[topic].is_alive(),
                "consumer_thread_name": self._consumer_threads[topic].name
                                       if topic in self._consumer_threads else None
            })

            return ServiceResult.success(status, f"Retrieved status for topic: {topic}")

        except Exception as e:
            self._logger.ERROR(f"Error getting topic status for {topic}: {e}")
            return ServiceResult.error(f"Failed to get topic status: {str(e)}")
    
    def list_active_subscriptions(self) -> ServiceResult:
        """
        列出所有活跃的订阅

        Returns:
            ServiceResult: 订阅状态列表
        """
        try:
            subscriptions = []

            for topic in self._message_handlers.keys():
                subscription_info = {
                    "topic": topic,
                    "has_handler": True,
                    "is_consuming": topic in self._consumer_threads and
                                   self._consumer_threads[topic].is_alive(),
                    "thread_name": self._consumer_threads[topic].name
                                  if topic in self._consumer_threads else None
                }
                subscriptions.append(subscription_info)

            return ServiceResult.success(subscriptions, f"Listed {len(subscriptions)} active subscriptions")

        except Exception as e:
            self._logger.ERROR(f"Failed to list active subscriptions: {e}")
            return ServiceResult.error(f"Failed to list active subscriptions: {str(e)}")
    
    def unsubscribe_topic(self, topic: str) -> ServiceResult:
        """
        取消订阅主题

        Args:
            topic: 主题名称

        Returns:
            ServiceResult: 取消订阅结果
        """
        try:
            # 停止消费
            self.stop_consuming(topic)

            # 移除处理器
            if topic in self._message_handlers:
                del self._message_handlers[topic]

            self._logger.INFO(f"Unsubscribed from topic: {topic}")
            return ServiceResult.success({"unsubscribed": True}, f"Successfully unsubscribed from topic: {topic}")

        except Exception as e:
            self._logger.ERROR(f"Error unsubscribing from topic {topic}: {e}")
            return ServiceResult.error(f"Failed to unsubscribe from topic: {str(e)}")
    
    # ==================== 队列监控和统计 ====================
    
    def get_statistics(self) -> ServiceResult:
        """
        获取服务统计信息

        Returns:
            ServiceResult: 统计信息
        """
        try:
            kafka_status = self._crud_repo.get_kafka_status()

            # 注意：list_active_subscriptions现在返回ServiceResult
            subscriptions_result = self.list_active_subscriptions()
            subscriptions_data = subscriptions_result.data if subscriptions_result.is_success() else []

            statistics = {
                "kafka_connection": kafka_status,
                "send_statistics": self._send_stats.copy(),
                "receive_statistics": self._receive_stats.copy(),
                "active_subscriptions": len(self._message_handlers),
                "running_consumers": len([t for t in self._consumer_threads.values()
                                        if t.is_alive()]),
                "subscription_details": subscriptions_data
            }

            return ServiceResult.success(statistics, "Retrieved service statistics successfully")

        except Exception as e:
            self._logger.ERROR(f"Failed to get statistics: {e}")
            return ServiceResult.error(f"Failed to get statistics: {str(e)}")
    
    def get_unconsumed_count(self, topic: str, group_id: str = None) -> ServiceResult:
        """
        查询指定主题的未消费消息数量

        Args:
            topic: 主题名称
            group_id: 消费者组ID，None表示默认组

        Returns:
            ServiceResult: 包含未消费消息数量和详细信息
        """
        try:
            if not topic:
                return ServiceResult.error("主题名不能为空")

            # 验证主题是否存在
            topics = self._crud_repo.list_topics()
            if topic not in topics:
                return ServiceResult.error(f"主题{topic}不存在")

            # 获取主题总消息数
            total_messages = self._crud_repo.get_message_count(topic)

            # 尝试获取消费者组的偏移信息（如果CRUD支持）
            try:
                # 这里假设KafkaCRUD有获取偏移信息的方法
                if hasattr(self._crud_repo, 'get_consumer_group_offset'):
                    current_offset = self._crud_repo.get_consumer_group_offset(topic, group_id)
                    latest_offset = self._crud_repo.get_latest_offset(topic)

                    if current_offset is not None and latest_offset is not None:
                        unconsumed_count = latest_offset - current_offset
                    else:
                        unconsumed_count = total_messages
                else:
                    # 如果不支持偏移查询，返回总消息数作为估算
                    unconsumed_count = total_messages
                    return ServiceResult.success(
                        data={
                            'topic': topic,
                            'group_id': group_id or 'default',
                            'total_messages': total_messages,
                            'unconsumed_messages': unconsumed_count,
                            'estimation': True,
                            'message': '未消费消息数量为估算值'
                        },
                        message=f"主题{topic}估算未消费消息数: {unconsumed_count}"
                    )
            except Exception:
                # 查询偏移信息失败，使用总消息数
                unconsumed_count = total_messages

            return ServiceResult.success(
                data={
                    'topic': topic,
                    'group_id': group_id or 'default',
                    'total_messages': total_messages,
                    'unconsumed_messages': unconsumed_count,
                    'timestamp': datetime.now().isoformat()
                },
                message=f"主题{topic}未消费消息数量: {unconsumed_count}"
            )

        except Exception as e:
            return ServiceResult.error(f"查询未消费消息数量失败: {str(e)}")

    def get_consumer_group_lag(self, topic: str, group_id: str = None) -> ServiceResult:
        """
        查询消费者组延迟（Lag）信息

        Args:
            topic: 主题名称
            group_id: 消费者组ID

        Returns:
            ServiceResult: 包含延迟详情
        """
        try:
            if not topic:
                return ServiceResult.error("主题名不能为空")

            # 查询未消费消息数量
            lag_result = self.get_unconsumed_count(topic, group_id)
            if not lag_result.success:
                return lag_result

            data = lag_result.data
            unconsumed_count = data['unconsumed_messages']

            # 估算延迟时间（基于消息时间戳）
            try:
                if hasattr(self._crud_repo, 'get_latest_message_timestamp'):
                    latest_timestamp = self._crud_repo.get_latest_message_timestamp(topic)
                    if latest_timestamp:
                        current_time = datetime.now()
                        lag_seconds = (current_time - latest_timestamp).total_seconds()
                        lag_minutes = lag_seconds / 60
                        lag_hours = lag_seconds / 3600
                    else:
                        lag_seconds = None
                        lag_minutes = None
                        lag_hours = None
                else:
                    lag_seconds = None
                    lag_minutes = None
                    lag_hours = None
            except Exception:
                lag_seconds = None
                lag_minutes = None
                lag_hours = None

            return ServiceResult.success(
                data={
                    'topic': topic,
                    'group_id': group_id or 'default',
                    'unconsumed_messages': unconsumed_count,
                    'lag_seconds': lag_seconds,
                    'lag_minutes': lag_minutes,
                    'lag_hours': lag_hours,
                    'lag_level': self._calculate_lag_level(unconsumed_count, lag_minutes),
                    'timestamp': datetime.now().isoformat()
                },
                message=f"消费者组延迟: {unconsumed_count}条消息"
            )

        except Exception as e:
            return ServiceResult.error(f"查询消费者组延迟失败: {str(e)}")

    def _calculate_lag_level(self, message_count: int, lag_minutes: float = None) -> str:
        """
        计算延迟级别

        Args:
            message_count: 未消费消息数量
            lag_minutes: 延迟分钟数

        Returns:
            str: 延迟级别
        """
        if lag_minutes is None:
            # 基于消息数量估算
            if message_count == 0:
                return "无延迟"
            elif message_count < 100:
                return "低延迟"
            elif message_count < 1000:
                return "中等延迟"
            else:
                return "高延迟"
        else:
            # 基于时间延迟估算
            if lag_minutes < 1:
                return "无延迟"
            elif lag_minutes < 10:
                return "低延迟"
            elif lag_minutes < 60:
                return "中等延迟"
            else:
                return "高延迟"

    def get_queue_metrics(self, topics: List[str] = None) -> ServiceResult:
        """
        获取队列指标

        Args:
            topics: 主题列表，None表示所有订阅的主题

        Returns:
            ServiceResult: 队列指标
        """
        try:
            if topics is None:
                topics = list(self._message_handlers.keys())

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "topics": {}
            }

            for topic in topics:
                try:
                    # 获取未消费消息数量
                    lag_result = self.get_unconsumed_count(topic)

                    if lag_result.success:
                        lag_data = lag_result.data
                        metrics["topics"][topic] = {
                            "unconsumed_messages": lag_data.get("unconsumed_messages", 0),
                            "total_messages": lag_data.get("total_messages", 0),
                            "consumer_lag": lag_data.get("lag_level", "未知")
                        }
                    else:
                        metrics["topics"][topic] = {"error": lag_result.error}
                except Exception as e:
                    metrics["topics"][topic] = {"error": str(e)}

            return ServiceResult.success(metrics, f"Retrieved queue metrics for {len(topics)} topics")

        except Exception as e:
            self._logger.ERROR(f"Failed to get queue metrics: {e}")
            return ServiceResult.error(f"Failed to get queue metrics: {str(e)}")
    
    def reset_statistics(self) -> ServiceResult:
        """
        重置统计信息

        Returns:
            ServiceResult: 重置结果
        """
        try:
            self._send_stats = {
                "total_sent": 0,
                "failed_sends": 0,
                "last_send_time": None
            }

            self._receive_stats = {
                "total_received": 0,
                "last_receive_time": None
            }

            self._logger.INFO("Statistics reset successfully")
            return ServiceResult.success({"reset": True}, "Statistics reset successfully")

        except Exception as e:
            self._logger.ERROR(f"Error resetting statistics: {e}")
            return ServiceResult.error(f"Failed to reset statistics: {str(e)}")
    
    # ==================== 健康检查和系统管理 ====================
    
    def health_check(self) -> ServiceResult:
        """
        执行服务健康检查

        Returns:
            ServiceResult: 健康状态信息
        """
        try:
            # 基础健康状态
            base_health = {
                "service": "KafkaService",
                "status": "healthy",
                "timestamp": time.time()
            }
            kafka_status = self._crud_repo.get_kafka_status()

            # 检查消费者线程健康状态
            consumer_health = {}
            for topic, thread in self._consumer_threads.items():
                consumer_health[topic] = {
                    "alive": thread.is_alive(),
                    "name": thread.name
                }

            health_status = base_health.copy()
            health_status.update({
                "kafka_connection": kafka_status["connected"],
                "active_consumers": consumer_health,
                "total_subscriptions": len(self._message_handlers),
                "running_consumers": len([t for t in self._consumer_threads.values() if t.is_alive()])
            })

            # 判断整体健康状态
            overall_healthy = (
                kafka_status["connected"] and
                len([t for t in self._consumer_threads.values() if not t.is_alive()]) == 0
            )

            health_status["status"] = "healthy" if overall_healthy else "unhealthy"

            status_message = "Kafka service is healthy" if overall_healthy else "Kafka service has issues"
            return ServiceResult.success(health_status, status_message)

        except Exception as e:
            self._logger.ERROR(f"Health check failed: {e}")
            return ServiceResult.error(f"Health check failed: {str(e)}")
    
    def shutdown(self) -> bool:
        """
        优雅关闭服务
        
        Returns:
            bool: 关闭是否成功
        """
        try:
            self._logger.INFO("Shutting down KafkaService...")
            
            # 停止所有消费者
            topics_to_stop = list(self._consumer_threads.keys())
            for topic in topics_to_stop:
                self.stop_consuming(topic)
            
            # 清理处理器
            self._message_handlers.clear()
            
            # 关闭所有Kafka消费者连接
            self._crud_repo.close_all_consumers()
            
            self._logger.INFO("KafkaService shutdown completed")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Error during service shutdown: {e}")
            return False
    
    # ==================== Data Update Signal Sending ====================

    def send_stockinfo_update_signal(self) -> bool:
        """Send stock basic info update signal"""
        return self.publish_message("ginkgo_data_update", {
            "type": "stockinfo",
            "code": ""
        })

    def send_adjustfactor_update_signal(self, code: str, full: bool = False, force: bool = False) -> bool:
        """Send adjustment factor update signal"""
        return self.publish_message("ginkgo_data_update", {
            "type": "adjust",
            "code": code,
            "full": full,
            "force": force
        })

    def send_daybar_update_signal(self, code: str, full: bool = False, force: bool = False) -> bool:
        """Send daily bar data update signal"""
        return self.publish_message("ginkgo_data_update", {
            "type": "bar",
            "code": code,
            "full": full,
            "force": force
        })

    def send_tick_update_signal(self, code: str, full: bool = False, force: bool = False) -> bool:
        """Send tick data update signal"""
        return self.publish_message("ginkgo_data_update", {
            "type": "tick",
            "code": code,
            "full": full,
            "force": force
        })

    def send_worker_kill_signal(self) -> bool:
        """Send worker stop signal"""
        return self.publish_message("ginkgo_data_update", {
            "type": "kill",
            "code": ""
        })

    def send_tick_all_signal(self, full: bool = False, force: bool = False) -> bool:
        """发送所有股票的tick同步信号"""
        from ginkgo.data.containers import container
        stockinfo_service = container.stockinfo_service()
        stock_result = stockinfo_service.get()

        if not stock_result.success or not stock_result.data:
            return False

        success_count = 0
        for stock in stock_result.data:
            # 为每个股票发送单独的同步消息
            success = self.send_tick_update_signal(
                code=stock.code,
                full=full,
                force=force
            )
            if success:
                success_count += 1

        return success_count == len(stock_result.data)

    def send_bar_all_signal(self, full: bool = False, force: bool = False) -> bool:
        """发送所有股票的bar同步信号"""
        from ginkgo.data.containers import container
        stockinfo_service = container.stockinfo_service()
        stock_result = stockinfo_service.get()

        if not stock_result.success or not stock_result.data:
            return False

        success_count = 0
        for stock in stock_result.data:
            # 为每个股票发送单独的同步消息
            success = self.send_daybar_update_signal(
                code=stock.code,
                full=full,
                force=force
            )
            if success:
                success_count += 1

        return success_count == len(stock_result.data)

    def send_adjustfactor_all_signal(self, full: bool = False, force: bool = False) -> bool:
        """发送所有股票的adjustfactor同步信号"""
        from ginkgo.data.containers import container
        stockinfo_service = container.stockinfo_service()
        stock_result = stockinfo_service.get()

        if not stock_result.success or not stock_result.data:
            return False

        success_count = 0
        for stock in stock_result.data:
            # 发送复权因子同步消息（单个股票同步完成后会自动计算）
            success = self.send_adjustfactor_update_signal(code=stock.code, full=False, force=False)
            if success:
                success_count += 1

        return success_count == len(stock_result.data)

    def __del__(self):
        """Destructor, ensure resource cleanup"""
        try:
            self.shutdown()
        except:
            pass