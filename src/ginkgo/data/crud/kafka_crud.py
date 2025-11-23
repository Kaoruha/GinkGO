"""
KafkaCRUD - Kafka消息队列CRUD操作

提供统一的Kafka基础操作接口，符合项目CRUD架构模式
参考RedisService的设计，实现Kafka的Producer/Consumer操作
"""

import json
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
import threading
import time

from ginkgo.libs import GLOG, time_logger, retry
from ginkgo.data.drivers import GinkgoProducer, GinkgoConsumer, kafka_topic_llen


class KafkaCRUD:
    """
    Kafka基础CRUD操作类
    
    提供原子级Kafka操作，负责：
    - Kafka Producer/Consumer连接管理
    - 消息发送和接收操作
    - 主题管理和监控
    - 连接状态监控和错误处理
    """
    
    def __init__(self, producer_connection=None, default_group_id: str = "ginkgo_default"):
        """
        初始化KafkaCRUD
        
        Args:
            producer_connection: Kafka Producer连接实例，如果为None则自动创建
            default_group_id: 默认消费者组ID
        """
        if producer_connection is None:
            producer_connection = GinkgoProducer()
            
        self._producer = producer_connection
        self._default_group_id = default_group_id
        self._consumers = {}  # 缓存消费者实例 {topic_group_key: consumer}
        self._connection_tested = False
        self._lock = threading.Lock()
        
        GLOG.DEBUG("KafkaCRUD initialized")
    
    @property
    def producer(self):
        """获取Kafka Producer实例"""
        return self._producer
    
    def _test_connection(self) -> bool:
        """
        测试Kafka连接可用性
        
        Returns:
            bool: 连接是否可用
        """
        if self._connection_tested:
            return True
            
        try:
            # 尝试获取一个测试主题的元数据来验证连接
            test_consumer = GinkgoConsumer("test_connection_topic", group_id=self._default_group_id)
            if test_consumer.consumer is not None:
                test_consumer.consumer.close()
                self._connection_tested = True
                GLOG.DEBUG("Kafka connection test successful")
                return True
            else:
                GLOG.ERROR("Kafka connection test failed: consumer is None")
                return False
        except Exception as e:
            GLOG.ERROR(f"Kafka connection test failed: {e}")
            return False
    
    def _get_consumer_key(self, topic: str, group_id: str) -> str:
        """生成消费者缓存键"""
        return f"{topic}_{group_id}"
    
    def _get_or_create_consumer(self, topic: str, group_id: str = None, 
                               offset: str = "earliest") -> Optional[GinkgoConsumer]:
        """
        获取或创建消费者实例
        
        Args:
            topic: 主题名称
            group_id: 消费者组ID，None则使用默认值
            offset: 偏移量策略
            
        Returns:
            GinkgoConsumer实例或None
        """
        if group_id is None:
            group_id = self._default_group_id
            
        consumer_key = self._get_consumer_key(topic, group_id)
        
        with self._lock:
            if consumer_key not in self._consumers:
                try:
                    consumer = GinkgoConsumer(topic, group_id, offset)
                    self._consumers[consumer_key] = consumer
                    GLOG.DEBUG(f"Created new consumer for topic: {topic}, group: {group_id}")
                except Exception as e:
                    GLOG.ERROR(f"Failed to create consumer for {topic}: {e}")
                    return None
            
            return self._consumers[consumer_key]
    
    # ==================== 消息发送操作 ====================
    
    @time_logger
    @retry(max_try=3)
    def send_message(self, topic: str, message: Any, key: str = None) -> bool:
        """
        发送消息到指定主题
        
        Args:
            topic: 主题名称
            message: 要发送的消息（支持字典、列表、字符串等）
            key: 消息键，用于分区
            
        Returns:
            bool: 发送是否成功
        """
        try:
            if not self._test_connection():
                return False
                
            # 准备消息数据
            if isinstance(message, (dict, list)):
                msg_data = message
            else:
                msg_data = {"content": message, "timestamp": datetime.now().isoformat()}
            
            # 添加元数据
            if key:
                msg_data["_key"] = key
                
            self._producer.send(topic, msg_data)
            GLOG.DEBUG(f"Sent message to topic: {topic}")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"Failed to send message to topic {topic}: {e}")
            return False
    
    @time_logger
    def send_batch_messages(self, topic: str, messages: List[Dict[str, Any]]) -> int:
        """
        批量发送消息
        
        Args:
            topic: 主题名称
            messages: 消息列表
            
        Returns:
            int: 成功发送的消息数量
        """
        success_count = 0
        
        try:
            if not self._test_connection():
                return 0
                
            for message in messages:
                if self.send_message(topic, message):
                    success_count += 1
                    
            GLOG.DEBUG(f"Batch sent {success_count}/{len(messages)} messages to topic: {topic}")
            return success_count
            
        except Exception as e:
            GLOG.ERROR(f"Failed to send batch messages to topic {topic}: {e}")
            return success_count
    
    # ==================== 消息接收操作 ====================
    
    @time_logger
    def consume_messages(self, topic: str, group_id: str = None, 
                        timeout_ms: int = 1000, max_records: int = 1) -> List[Dict[str, Any]]:
        """
        消费消息
        
        Args:
            topic: 主题名称
            group_id: 消费者组ID
            timeout_ms: 超时时间（毫秒）
            max_records: 最大消息数量
            
        Returns:
            List[Dict]: 消息列表
        """
        messages = []
        
        try:
            consumer = self._get_or_create_consumer(topic, group_id)
            if not consumer:
                return messages
                
            # 消费消息
            msg_pack = consumer.consumer.poll(timeout_ms=timeout_ms, max_records=max_records)
            
            for topic_partition, records in msg_pack.items():
                for record in records:
                    message_data = {
                        "topic": record.topic,
                        "partition": record.partition,
                        "offset": record.offset,
                        "key": record.key.decode('utf-8') if record.key else None,
                        "value": record.value,
                        "timestamp": datetime.fromtimestamp(record.timestamp / 1000) if record.timestamp else None
                    }
                    messages.append(message_data)
                    
            GLOG.DEBUG(f"Consumed {len(messages)} messages from topic: {topic}")
            return messages
            
        except Exception as e:
            GLOG.ERROR(f"Failed to consume messages from topic {topic}: {e}")
            return messages
    
    @time_logger
    def consume_with_callback(self, topic: str, callback: Callable[[Dict[str, Any]], bool], 
                             group_id: str = None, max_messages: int = None) -> int:
        """
        使用回调函数消费消息
        
        Args:
            topic: 主题名称
            callback: 消息处理回调函数，返回True表示处理成功
            group_id: 消费者组ID
            max_messages: 最大消息数量，None表示无限制
            
        Returns:
            int: 成功处理的消息数量
        """
        processed_count = 0
        
        try:
            consumer = self._get_or_create_consumer(topic, group_id)
            if not consumer:
                return 0
                
            for message in consumer.consumer:
                try:
                    message_data = {
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "key": message.key.decode('utf-8') if message.key else None,
                        "value": message.value,
                        "timestamp": datetime.fromtimestamp(message.timestamp / 1000) if message.timestamp else None
                    }
                    
                    # 调用回调函数处理消息
                    if callback(message_data):
                        processed_count += 1
                        consumer.commit()  # 提交偏移量
                        
                    # 检查是否达到最大消息数量
                    if max_messages and processed_count >= max_messages:
                        break
                        
                except Exception as callback_error:
                    GLOG.ERROR(f"Callback processing error: {callback_error}")
                    
            GLOG.DEBUG(f"Processed {processed_count} messages from topic: {topic}")
            return processed_count
            
        except Exception as e:
            GLOG.ERROR(f"Failed to consume with callback from topic {topic}: {e}")
            return processed_count
    
    def commit_offset(self, topic: str, group_id: str = None) -> bool:
        """
        手动提交消费偏移量
        
        Args:
            topic: 主题名称  
            group_id: 消费者组ID
            
        Returns:
            bool: 提交是否成功
        """
        try:
            consumer = self._get_or_create_consumer(topic, group_id)
            if consumer:
                consumer.commit()
                GLOG.DEBUG(f"Committed offset for topic: {topic}, group: {group_id}")
                return True
            return False
            
        except Exception as e:
            GLOG.ERROR(f"Failed to commit offset for topic {topic}: {e}")
            return False
    
    # ==================== 主题和队列管理 ====================
    
    @time_logger
    def get_topic_message_count(self, topic: str) -> int:
        """
        获取主题中的未消费消息数量
        
        Args:
            topic: 主题名称
            
        Returns:
            int: 消息数量
        """
        try:
            return kafka_topic_llen(topic)
        except Exception as e:
            GLOG.ERROR(f"Failed to get message count for topic {topic}: {e}")
            return 0
    
    @time_logger
    def topic_exists(self, topic: str) -> bool:
        """
        检查主题是否存在
        
        Args:
            topic: 主题名称
            
        Returns:
            bool: 主题是否存在
        """
        try:
            # 尝试创建消费者来检查主题是否存在
            test_consumer = GinkgoConsumer(topic, group_id=f"test_{int(time.time())}")
            if test_consumer.consumer:
                partitions = test_consumer.consumer.partitions_for_topic(topic)
                test_consumer.consumer.close()
                return partitions is not None
            return False
            
        except Exception as e:
            GLOG.ERROR(f"Failed to check topic existence {topic}: {e}")
            return False
    
    def list_consumer_groups(self, topic: str = None) -> List[str]:
        """
        列出消费者组（简化实现）
        
        Args:
            topic: 主题名称，None表示所有主题
            
        Returns:
            List[str]: 消费者组列表
        """
        # 返回当前缓存的消费者组
        groups = set()
        for consumer_key in self._consumers.keys():
            topic_name, group_id = consumer_key.rsplit('_', 1)
            if topic is None or topic_name == topic:
                groups.add(group_id)
        
        return list(groups)
    
    # ==================== 监控和状态 ====================
    
    @time_logger
    def get_kafka_status(self) -> Dict[str, Any]:
        """
        获取Kafka连接状态和统计信息
        
        Returns:
            Dict[str, Any]: Kafka状态信息
        """
        try:
            if not self._test_connection():
                return {"connected": False, "error": "Connection failed"}
                
            # 收集活跃消费者信息
            active_consumers = []
            for consumer_key, consumer in self._consumers.items():
                topic, group_id = consumer_key.rsplit('_', 1)
                active_consumers.append({
                    "topic": topic,
                    "group_id": group_id,
                    "active": consumer.consumer is not None
                })
            
            return {
                "connected": True,
                "producer_active": self._producer is not None,
                "active_consumers": len(active_consumers),
                "consumer_details": active_consumers,
                "default_group_id": self._default_group_id
            }
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Kafka status: {e}")
            return {"connected": False, "error": str(e)}
    
    @time_logger
    def get_topic_info(self, topic: str) -> Dict[str, Any]:
        """
        获取主题详细信息
        
        Args:
            topic: 主题名称
            
        Returns:
            Dict[str, Any]: 主题信息
        """
        try:
            info = {
                "topic": topic,
                "exists": self.topic_exists(topic),
                "message_count": self.get_topic_message_count(topic),
                "consumer_groups": self.list_consumer_groups(topic)
            }
            
            return info
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get topic info for {topic}: {e}")
            return {"topic": topic, "error": str(e)}
    
    # ==================== 清理和关闭 ====================
    
    def close_consumer(self, topic: str, group_id: str = None) -> bool:
        """
        关闭指定的消费者
        
        Args:
            topic: 主题名称
            group_id: 消费者组ID
            
        Returns:
            bool: 关闭是否成功
        """
        if group_id is None:
            group_id = self._default_group_id
            
        consumer_key = self._get_consumer_key(topic, group_id)
        
        try:
            with self._lock:
                if consumer_key in self._consumers:
                    consumer = self._consumers[consumer_key]
                    if consumer.consumer:
                        consumer.consumer.close()
                    del self._consumers[consumer_key]
                    GLOG.DEBUG(f"Closed consumer for topic: {topic}, group: {group_id}")
                    return True
                return False
                
        except Exception as e:
            GLOG.ERROR(f"Failed to close consumer for {topic}: {e}")
            return False
    
    def close_all_consumers(self) -> int:
        """
        关闭所有消费者
        
        Returns:
            int: 关闭的消费者数量
        """
        closed_count = 0
        
        try:
            with self._lock:
                for consumer_key, consumer in list(self._consumers.items()):
                    try:
                        if consumer.consumer:
                            consumer.consumer.close()
                        closed_count += 1
                    except Exception as e:
                        GLOG.ERROR(f"Error closing consumer {consumer_key}: {e}")
                
                self._consumers.clear()
                GLOG.DEBUG(f"Closed {closed_count} consumers")
                
        except Exception as e:
            GLOG.ERROR(f"Error closing all consumers: {e}")
            
        return closed_count
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.close_all_consumers()
        except:
            pass