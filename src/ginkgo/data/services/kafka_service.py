"""
Kafka消息队列服务 - 扁平化架构实现

提供消息发布/订阅、主题管理、队列监控等功能
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import threading
import uuid

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs.utils.common import time_logger, retry


class KafkaService(BaseService):
    """Kafka消息队列服务 - 直接继承BaseService"""

    def __init__(self, kafka_crud=None, **deps):
        """
        初始化Kafka服务

        Args:
            kafka_crud: KafkaCRUD实例，如果为None则自动创建
            **deps: 其他依赖
        """
        if kafka_crud is None:
            from ginkgo.data.crud import KafkaCRUD
            kafka_crud = KafkaCRUD()

        super().__init__(crud_repo=kafka_crud, **deps)

        # 为了向后兼容，保留kafka属性
        self.kafka = kafka_crud

        # 消息处理状态跟踪
        self._message_handlers = {}  # {topic: handler_function}
        self._consumer_threads = {}  # {topic: thread}
        self._stop_events = {}      # {topic: threading.Event}

        # 消息发送统计
        self._send_stats = {
            "total_sent": 0,
            "failed_sends": 0,
            "last_send_time": None
        }

        # 消息接收统计
        self._receive_stats = {
            "total_received": 0,
            "last_receive_time": None
        }

    # ==================== 标准接口实现 ====================

    def get(self, topic: str = None, **filters) -> ServiceResult:
        """获取Kafka主题信息"""
        try:
            if topic:
                # 获取特定主题信息
                topic_info = self._crud_repo.get_topic_info(topic)
                return ServiceResult.success(
                    data={'topic': topic, 'info': topic_info},
                    message=f"成功获取主题{topic}信息"
                )
            else:
                # 获取所有主题
                topics = self._crud_repo.list_topics()
                return ServiceResult.success(
                    data={'topics': topics, 'count': len(topics)},
                    message=f"找到{len(topics)}个主题"
                )
        except Exception as e:
            return ServiceResult.error(f"获取Kafka主题信息失败: {str(e)}")

    def count(self, topic: str = None) -> ServiceResult:
        """统计主题数量或消息数量"""
        try:
            if topic:
                # 统计特定主题的消息数量
                message_count = self._crud_repo.get_message_count(topic)
                return ServiceResult.success(
                    data={'topic': topic, 'message_count': message_count},
                    message=f"主题{topic}共有{message_count}条消息"
                )
            else:
                # 统计所有主题数量
                topics = self._crud_repo.list_topics()
                return ServiceResult.success(
                    data={'topic_count': len(topics)},
                    message=f"共有{len(topics)}个主题"
                )
        except Exception as e:
            return ServiceResult.error(f"统计Kafka主题数量失败: {str(e)}")

    def validate(self, topic: str, message: Any = None) -> ServiceResult:
        """验证Kafka数据"""
        try:
            if not topic:
                return ServiceResult.error("主题名不能为空")

            if not isinstance(topic, str):
                return ServiceResult.error("主题名必须是字符串")

            # 检查主题名格式
            if not topic.replace('_', '').replace('-', '').isalnum():
                return ServiceResult.error("主题名只能包含字母、数字、下划线和连字符")

            return ServiceResult.success(message="Kafka数据验证通过")
        except Exception as e:
            return ServiceResult.error(f"Kafka数据验证失败: {str(e)}")

    def check_integrity(self, topic: str) -> ServiceResult:
        """检查Kafka主题完整性"""
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

    # ==================== 消息发布服务 ====================
    
    def publish_message(self, topic: str, message: Any, key: str = None,
                       add_metadata: bool = True) -> bool:
        """
        发布消息到指定主题
        
        Args:
            topic: 主题名称
            message: 消息内容
            key: 消息键，用于分区
            add_metadata: 是否添加元数据
            
        Returns:
            bool: 发送是否成功
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
            else:
                self._send_stats["failed_sends"] += 1
                self._logger.ERROR(f"Failed to publish message to topic: {topic}")
            
            self._log_operation_end("publish_message", success)
            return success
            
        except Exception as e:
            self._send_stats["failed_sends"] += 1
            self._logger.ERROR(f"Error publishing message to {topic}: {e}")
            return False
    
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
    
    # ==================== 消息订阅服务 ====================
    
    def subscribe_topic(self, topic: str, handler: Callable[[Dict[str, Any]], bool],
                       group_id: str = None, auto_start: bool = True) -> bool:
        """
        订阅主题并设置消息处理器
        
        Args:
            topic: 主题名称
            handler: 消息处理函数，接收消息字典，返回处理是否成功
            group_id: 消费者组ID
            auto_start: 是否自动开始消费
            
        Returns:
            bool: 订阅是否成功
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
    
    def stop_consuming(self, topic: str) -> bool:
        """
        停止消费指定主题
        
        Args:
            topic: 主题名称
            
        Returns:
            bool: 停止是否成功
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
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Error stopping consumer for topic {topic}: {e}")
            return False
    
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
    
    # ==================== 主题管理服务 ====================
    
    def get_topic_status(self, topic: str) -> Dict[str, Any]:
        """
        获取主题状态信息
        
        Args:
            topic: 主题名称
            
        Returns:
            Dict: 主题状态信息
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
            
            return status
            
        except Exception as e:
            self._logger.ERROR(f"Error getting topic status for {topic}: {e}")
            return {"topic": topic, "error": str(e)}
    
    def list_active_subscriptions(self) -> List[Dict[str, Any]]:
        """
        列出所有活跃的订阅
        
        Returns:
            List[Dict]: 订阅状态列表
        """
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
        
        return subscriptions
    
    def unsubscribe_topic(self, topic: str) -> bool:
        """
        取消订阅主题
        
        Args:
            topic: 主题名称
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            # 停止消费
            self.stop_consuming(topic)
            
            # 移除处理器
            if topic in self._message_handlers:
                del self._message_handlers[topic]
            
            self._logger.INFO(f"Unsubscribed from topic: {topic}")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Error unsubscribing from topic {topic}: {e}")
            return False
    
    # ==================== 队列监控和统计 ====================
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            Dict: 统计信息
        """
        kafka_status = self._crud_repo.get_kafka_status()
        
        return {
            "kafka_connection": kafka_status,
            "send_statistics": self._send_stats.copy(),
            "receive_statistics": self._receive_stats.copy(),
            "active_subscriptions": len(self._message_handlers),
            "running_consumers": len([t for t in self._consumer_threads.values() 
                                    if t.is_alive()]),
            "subscription_details": self.list_active_subscriptions()
        }
    
    def get_unconsumed_messages_count(self, topic: str, group_id: str = None) -> ServiceResult:
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
            lag_result = self.get_unconsumed_messages_count(topic, group_id)
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

    def get_queue_metrics(self, topics: List[str] = None) -> Dict[str, Any]:
        """
        获取队列指标

        Args:
            topics: 主题列表，None表示所有订阅的主题

        Returns:
            Dict: 队列指标
        """
        if topics is None:
            topics = list(self._message_handlers.keys())

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "topics": {}
        }

        for topic in topics:
            try:
                # 获取未消费消息数量
                lag_result = self.get_unconsumed_messages_count(topic)

                if lag_result.success:
                    lag_data = lag_result.data
                    metrics["topics"][topic] = {
                        "unconsumed_messages": lag_data["unconsumed_messages"],
                        "total_messages": lag_data["total_messages"],
                        "consumer_lag": lag_data.get("lag_level", "未知")
                    }
                else:
                    metrics["topics"][topic] = {"error": lag_result.error}
            except Exception as e:
                metrics["topics"][topic] = {"error": str(e)}

        return metrics
    
    def reset_statistics(self) -> bool:
        """
        重置统计信息
        
        Returns:
            bool: 重置是否成功
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
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Error resetting statistics: {e}")
            return False
    
    # ==================== 健康检查和系统管理 ====================
    
    def health_check(self) -> Dict[str, Any]:
        """
        执行服务健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        base_health = self.get_health_status()
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
        
        return health_status
    
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
    
    # ==================== 数据更新信号发送 ====================
    
    def send_stockinfo_update_signal(self) -> bool:
        """发送股票基本信息更新信号"""
        return self.publish_message("ginkgo_data_update", {
            "type": "stockinfo",
            "code": ""
        })

    def send_adjustfactor_update_signal(self, code: str, fast: bool = True) -> bool:
        """发送复权因子更新信号"""  
        return self.publish_message("ginkgo_data_update", {
            "type": "adjust",
            "code": code,
            "fast": fast
        })

    def send_daybar_update_signal(self, code: str, fast: bool = True) -> bool:
        """发送日K线数据更新信号"""
        return self.publish_message("ginkgo_data_update", {
            "type": "bar",
            "code": code,
            "fast": fast
        })

    def send_tick_update_signal(self, code: str, fast: bool = False, max_update: int = 0) -> bool:
        """发送分笔数据更新信号"""
        return self.publish_message("ginkgo_data_update", {
            "type": "tick",
            "code": code,
            "fast": fast,
            "max_update": max_update
        })

    def send_worker_kill_signal(self) -> bool:
        """发送worker停止信号"""
        return self.publish_message("ginkgo_data_update", {
            "type": "kill",
            "code": ""
        })
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.shutdown()
        except:
            pass