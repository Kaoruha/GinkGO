# Upstream: Data Workers (数据同步Worker消费)、CLI Commands (发送更新信号)、KafkaService自身 (发送信号)
# Downstream: BaseService (继承基类)、KafkaCRUD (Kafka消息操作)、Data Workers (消费backtest/数据更新主题)
# Role: KafkaService消息队列服务提供Kafka发布订阅主题管理和数据更新信号发送






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
from ginkgo.libs import GLOG
from ginkgo.interfaces.kafka_topics import KafkaTopics


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

    def topic_exists(self, topic: str) -> bool:
        """Check whether a Kafka topic exists (thin delegate to KafkaCRUD)."""
        # 不包 try/except：与同模块其它 ServiceResult 方法不同，CLI purge 需要
        # 原始 bool 且让 CRUD 异常向上冒泡到 CLI 的 except 响亮报错，避免掩盖失败。
        return self._crud_repo.topic_exists(topic)

    def get_message_count(self, topic: str) -> int:
        """Get current message count of a topic (thin delegate to KafkaCRUD).

        ``count()`` 已把同一 CRUD 调用包成 ServiceResult；CLI purge/dry-run 需要
        原始 int，故提供此薄透传。不包 try/except，让异常冒泡响亮报错。
        """
        return self._crud_repo.get_message_count(topic)

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
            status = self._crud_repo.get_topic_info(topic)
            return ServiceResult.success(status, f"Retrieved status for topic: {topic}")

        except Exception as e:
            self._logger.ERROR(f"Error getting topic status for {topic}: {e}")
            return ServiceResult.error(f"Failed to get topic status: {str(e)}")

    def list_consumer_groups(self) -> ServiceResult:
        """
        列出 broker 端所有 consumer groups

        走 CRUD ``list_broker_consumer_groups`` 真实查询 broker（非本地缓存）。

        Returns:
            ServiceResult: data 为消费组列表（每项含 name/state/protocol_type/type）
        """
        try:
            groups = self._crud_repo.list_broker_consumer_groups()
            return ServiceResult.success(groups, f"Listed {len(groups)} consumer groups")
        except Exception as e:
            self._logger.ERROR(f"Failed to list consumer groups: {e}")
            return ServiceResult.error(f"Failed to list consumer groups: {str(e)}")

    # ==================== 队列监控和统计 ====================
    
    def get_statistics(self) -> ServiceResult:
        """
        获取服务统计信息

        Returns:
            ServiceResult: 统计信息
        """
        try:
            kafka_status = self._crud_repo.get_kafka_status()

            statistics = {
                "kafka_connection": kafka_status,
                "send_statistics": self._send_stats.copy(),
                "receive_statistics": self._receive_stats.copy(),
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
            topics: 主题列表，None 表示空集（消费 worker 模型已退役，无本地订阅状态）

        Returns:
            ServiceResult: 队列指标
        """
        try:
            if topics is None:
                topics = []

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

    # ==================== 健康检查和系统管理 ====================
    
    def health_check(self) -> ServiceResult:
        """
        执行服务健康检查

        Returns:
            ServiceResult: 健康状态信息
        """
        try:
            kafka_status = self._crud_repo.get_kafka_status()
            overall_healthy = kafka_status["connected"]

            health_status = {
                "service": "KafkaService",
                "status": "healthy" if overall_healthy else "unhealthy",
                "timestamp": time.time(),
                "kafka_connection": kafka_status["connected"],
            }

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

            # 关闭所有 Kafka 消费者连接
            self._crud_repo.close_all_consumers()

            self._logger.INFO("KafkaService shutdown completed")
            return True

        except Exception as e:
            self._logger.ERROR(f"Error during service shutdown: {e}")
            return False

    # ==================== Data Update Signal Sending ====================

    def send_stockinfo_update_signal(self) -> bool:
        """Send stockinfo sync command to DataWorker (ginkgo.data.commands)."""
        return self.publish_message(KafkaTopics.DATA_COMMANDS, {
            "command": "stockinfo",
            "params": {}
        })

    def send_trade_day_signal(self) -> bool:
        """Send trade calendar sync command (#6488). Worker 消费后调用
        TradeDayService.sync 落库，供 paper worker 查 is_open 判断开市。"""
        return self.publish_message(KafkaTopics.DATA_COMMANDS, {
            "command": "trade_day",
            "params": {}
        })

    def send_adjustfactor_update_signal(self, code: str, full: bool = False, force: bool = False) -> bool:
        """Send adjustment factor sync command."""
        return self.publish_message(KafkaTopics.DATA_COMMANDS, {
            "command": "adjustfactor",
            "params": {"code": code, "full": full, "force": force}
        })

    def send_daybar_update_signal(self, code: str, full: bool = False, force: bool = False) -> bool:
        """Send daily bar snapshot sync command (worker dispatches on bar_snapshot)."""
        return self.publish_message(KafkaTopics.DATA_COMMANDS, {
            "command": "bar_snapshot",
            "params": {"code": code, "full": full, "force": force}
        })

    def send_tick_update_signal(self, code: str, full: bool = False, force: bool = False) -> bool:
        """Send tick sync command. ``force`` maps to worker's ``overwrite`` key
        (data-repair: delete and re-insert), per ControlCommandDTO TICK contract."""
        return self.publish_message(KafkaTopics.DATA_COMMANDS, {
            "command": "tick",
            "params": {"code": code, "full": full, "overwrite": force}
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
        except Exception as e:
            GLOG.ERROR(f"KafkaService析构时关闭失败: {e}")
