"""
AutoBroker - 自动API执行器

专门用于实盘自动交易，通过API提交订单并轮询状态直到完成
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from abc import abstractmethod

from ginkgo.trading.brokers.base_broker import (
    BaseBroker, ExecutionResult, ExecutionStatus, BrokerCapabilities
)
from ginkgo.libs import GLOG
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES


class AutoBroker(BaseBroker):
    """
    自动API执行Broker基类
    
    核心特点：
    - 自动通过API提交订单到实盘Broker
    - 持续轮询订单状态直到FILLED/CANCELLED/REJECTED
    - 支持多种实盘Broker的统一接口封装
    - 完整的错误处理和重试机制
    - 实时状态更新和回调通知
    
    子类需要实现：
    - _submit_order_to_api(): 提交订单到具体API
    - _cancel_order_via_api(): 通过API取消订单
    - _query_order_from_api(): 从API查询订单状态
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化AutoBroker
        
        Args:
            config: 配置字典，包含：
                - polling_interval_seconds: 轮询间隔（秒，默认5）
                - max_polling_duration_minutes: 最大轮询时长（分钟，默认60）
                - max_retry_attempts: 最大重试次数（默认3）
                - retry_delay_seconds: 重试延迟（秒，默认10）
                - api_timeout_seconds: API超时时间（秒，默认30）
                - enable_streaming: 是否启用实时数据流（默认False）
        """
        super().__init__(config)
        
        # 轮询配置
        self._polling_interval = config.get('polling_interval_seconds', 5)
        self._max_polling_duration_minutes = config.get('max_polling_duration_minutes', 60)
        self._max_retry_attempts = config.get('max_retry_attempts', 3)
        self._retry_delay_seconds = config.get('retry_delay_seconds', 10)
        self._api_timeout_seconds = config.get('api_timeout_seconds', 30)
        self._enable_streaming = config.get('enable_streaming', False)
        
        # 轮询任务管理
        self._polling_tasks: Dict[str, asyncio.Task] = {}
        self._active_orders: Set[str] = set()
        
        # 重试计数器
        self._retry_counts: Dict[str, int] = {}
        
        # API客户端（由子类初始化）
        self._api_client = None
        
    def _init_capabilities(self) -> BrokerCapabilities:
        """初始化AutoBroker的能力描述"""
        caps = BrokerCapabilities()
        caps.execution_type = "async"  # 异步执行
        caps.supports_streaming = self._enable_streaming
        caps.supports_batch_ops = True  # 支持批量操作
        caps.supports_market_data = True
        caps.supports_positions = True
        caps.max_orders_per_second = 10  # API限制
        caps.max_concurrent_orders = 100
        caps.order_timeout_seconds = self._max_polling_duration_minutes * 60
        caps.supported_order_types = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
        caps.supported_time_in_force = ["DAY", "GTC", "IOC", "FOK"]
        return caps
    
    def _detect_execution_mode(self) -> str:
        """
        AutoBroker专用于实盘自动交易
        
        Returns:
            str: 'live'
        """
        return 'live'
    
    # ============= 抽象方法：子类实现具体API =============
    @abstractmethod
    async def _submit_order_to_api(self, order: "Order") -> Dict[str, Any]:
        """
        提交订单到具体的API
        
        Args:
            order: 订单对象
            
        Returns:
            Dict[str, Any]: API响应，包含broker_order_id等信息
        """
        pass
    
    @abstractmethod
    async def _cancel_order_via_api(self, broker_order_id: str) -> Dict[str, Any]:
        """
        通过API取消订单
        
        Args:
            broker_order_id: Broker端订单ID
            
        Returns:
            Dict[str, Any]: API响应
        """
        pass
    
    @abstractmethod
    async def _query_order_from_api(self, broker_order_id: str) -> Dict[str, Any]:
        """
        从API查询订单状态
        
        Args:
            broker_order_id: Broker端订单ID
            
        Returns:
            Dict[str, Any]: API响应，包含订单状态信息
        """
        pass
    
    @abstractmethod
    def _parse_api_response_to_execution_result(
        self, 
        api_response: Dict[str, Any], 
        order_id: str
    ) -> ExecutionResult:
        """
        解析API响应为ExecutionResult
        
        Args:
            api_response: API响应
            order_id: 本地订单ID
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    async def _initialize_api_client(self) -> bool:
        """
        初始化API客户端
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    # ============= 连接管理 =============
    async def connect(self) -> bool:
        """连接到API Broker"""
        try:
            # 初始化API客户端
            if not await self._initialize_api_client():
                self._logger.ERROR("Failed to initialize API client")
                return False
            
            # 测试API连接
            if not await self._test_api_connection():
                self._logger.ERROR("API connection test failed")
                return False
            
            # 启动实时数据流（如果支持）
            if self._enable_streaming:
                self.start_streaming()
            
            self._connected = True
            self._logger.INFO(f"{self.name} connected successfully")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to connect {self.name}: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开API连接"""
        try:
            # 停止所有轮询任务
            await self._stop_all_polling_tasks()
            
            # 关闭API客户端
            if self._api_client:
                await self._cleanup_api_client()
            
            self._connected = False
            self._logger.INFO(f"{self.name} disconnected")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to disconnect {self.name}: {e}")
            return False
    
    # ============= 订单管理 =============
    async def submit_order(self, order: "Order") -> ExecutionResult:
        """
        提交订单到API并启动状态轮询
        
        Args:
            order: 订单对象
            
        Returns:
            ExecutionResult: 提交结果
        """
        if not self.is_connected:
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message=f"{self.name} not connected",
                execution_mode=self.execution_mode,
                requires_confirmation=False
            )
        
        # 基础验证
        if not self.validate_order(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Order validation failed",
                execution_mode=self.execution_mode,
                requires_confirmation=False
            )
        
        # 检查是否已有相同订单在处理
        if order.uuid in self._active_orders:
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Order already being processed",
                execution_mode=self.execution_mode,
                requires_confirmation=False
            )
        
        try:
            # 提交到API
            api_response = await self._submit_order_with_retry(order)
            
            # 解析响应
            result = self._parse_api_response_to_execution_result(api_response, order.uuid)
            
            # 如果提交成功，启动轮询
            if result.status == ExecutionStatus.SUBMITTED:
                self._active_orders.add(order.uuid)
                self._start_order_polling(order.uuid, result.broker_order_id)
                
                # 记录订单映射
                if result.broker_order_id:
                    self._order_mapping[order.uuid] = result.broker_order_id
            
            # 更新缓存
            self._update_order_status(result)
            
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to submit order {order.uuid}: {e}")
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message=f"API submission error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=False
            )
    
    async def cancel_order(self, order_id: str) -> ExecutionResult:
        """
        通过API取消订单
        
        Args:
            order_id: 本地订单ID
            
        Returns:
            ExecutionResult: 取消结果
        """
        try:
            # 获取broker订单ID
            broker_order_id = self._order_mapping.get(order_id)
            if not broker_order_id:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message="Broker order ID not found",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False
                )
            
            # 通过API取消
            api_response = await self._cancel_order_with_retry(broker_order_id)
            
            # 解析响应
            result = self._parse_api_response_to_execution_result(api_response, order_id)
            
            # 停止轮询任务
            await self._stop_polling_task(order_id)
            
            # 更新缓存
            self._update_order_status(result)
            
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to cancel order {order_id}: {e}")
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message=f"API cancellation error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=False
            )
    
    async def query_order(self, order_id: str) -> ExecutionResult:
        """
        查询订单状态
        
        Args:
            order_id: 本地订单ID
            
        Returns:
            ExecutionResult: 订单状态
        """
        try:
            # 首先检查缓存
            cached_result = self.get_cached_order_status(order_id)
            if cached_result and cached_result.is_final_status:
                return cached_result
            
            # 获取broker订单ID
            broker_order_id = self._order_mapping.get(order_id)
            if not broker_order_id:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message="Broker order ID not found",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False
                )
            
            # 从API查询
            api_response = await self._query_order_with_retry(broker_order_id)
            
            # 解析响应
            result = self._parse_api_response_to_execution_result(api_response, order_id)
            
            # 更新缓存
            self._update_order_status(result)
            
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to query order {order_id}: {e}")
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message=f"API query error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=False
            )
    
    # ============= 轮询和重试机制 =============
    def _start_order_polling(self, order_id: str, broker_order_id: str):
        """启动订单状态轮询任务"""
        task = asyncio.create_task(
            self._poll_order_status(order_id, broker_order_id)
        )
        self._polling_tasks[order_id] = task
        
        self._logger.DEBUG(f"Started polling for order {order_id}")
    
    async def _poll_order_status(self, order_id: str, broker_order_id: str):
        """轮询订单状态直到完成"""
        start_time = clock_now()
        max_duration = timedelta(minutes=self._max_polling_duration_minutes)
        
        try:
            while clock_now() - start_time < max_duration:
                # 查询状态
                try:
                    api_response = await self._query_order_from_api(broker_order_id)
                    result = self._parse_api_response_to_execution_result(api_response, order_id)
                    
                    # 更新缓存和触发回调
                    self._update_order_status(result)
                    
                    # 检查是否为最终状态
                    if result.is_final_status:
                        self._logger.INFO(f"Order {order_id} reached final status: {result.status}")
                        break
                        
                except Exception as e:
                    self._logger.ERROR(f"Error polling order {order_id}: {e}")
                
                # 等待下次轮询
                await asyncio.sleep(self._polling_interval)
            
            else:
                # 轮询超时
                self._logger.WARN(f"Order {order_id} polling timeout after {self._max_polling_duration_minutes} minutes")
                timeout_result = ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.EXPIRED,
                    message="Polling timeout - status unknown",
                    execution_mode=self.execution_mode,
                    requires_confirmation=False
                )
                self._update_order_status(timeout_result)
                
        except asyncio.CancelledError:
            self._logger.DEBUG(f"Polling task cancelled for order {order_id}")
        except Exception as e:
            self._logger.ERROR(f"Polling task error for order {order_id}: {e}")
        finally:
            # 清理
            self._active_orders.discard(order_id)
            self._polling_tasks.pop(order_id, None)
    
    async def _stop_polling_task(self, order_id: str):
        """停止指定订单的轮询任务"""
        task = self._polling_tasks.get(order_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._active_orders.discard(order_id)
        self._polling_tasks.pop(order_id, None)
    
    async def _stop_all_polling_tasks(self):
        """停止所有轮询任务"""
        tasks = list(self._polling_tasks.values())
        
        for task in tasks:
            if not task.done():
                task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._polling_tasks.clear()
        self._active_orders.clear()
    
    async def _submit_order_with_retry(self, order: "Order") -> Dict[str, Any]:
        """带重试的订单提交"""
        return await self._retry_api_operation(
            lambda: self._submit_order_to_api(order),
            f"submit order {order.uuid}"
        )
    
    async def _cancel_order_with_retry(self, broker_order_id: str) -> Dict[str, Any]:
        """带重试的订单取消"""
        return await self._retry_api_operation(
            lambda: self._cancel_order_via_api(broker_order_id),
            f"cancel order {broker_order_id}"
        )
    
    async def _query_order_with_retry(self, broker_order_id: str) -> Dict[str, Any]:
        """带重试的订单查询"""
        return await self._retry_api_operation(
            lambda: self._query_order_from_api(broker_order_id),
            f"query order {broker_order_id}"
        )
    
    async def _retry_api_operation(self, operation, operation_name: str) -> Dict[str, Any]:
        """API操作重试机制"""
        last_exception = None
        
        for attempt in range(self._max_retry_attempts):
            try:
                # 设置超时
                return await asyncio.wait_for(operation(), timeout=self._api_timeout_seconds)
                
            except asyncio.TimeoutError as e:
                last_exception = e
                self._logger.WARN(f"API timeout for {operation_name} (attempt {attempt + 1})")
            except Exception as e:
                last_exception = e
                self._logger.WARN(f"API error for {operation_name} (attempt {attempt + 1}): {e}")
            
            # 最后一次尝试失败，不再等待
            if attempt < self._max_retry_attempts - 1:
                await asyncio.sleep(self._retry_delay_seconds)
        
        raise last_exception or Exception(f"Max retry attempts exceeded for {operation_name}")
    
    # ============= 辅助方法 =============
    async def _test_api_connection(self) -> bool:
        """测试API连接"""
        try:
            # 子类可重写此方法进行特定的连接测试
            # 这里使用账户信息查询作为连接测试
            await self.get_account_info()
            return True
        except Exception as e:
            self._logger.ERROR(f"API connection test failed: {e}")
            return False
    
    async def _cleanup_api_client(self):
        """清理API客户端"""
        # 子类可重写此方法进行特定的清理操作
        try:
            if hasattr(self._api_client, 'close'):
                await self._api_client.close()
            self._api_client = None
        except Exception as e:
            self._logger.ERROR(f"Error cleaning up API client: {e}")
    
    def get_active_orders_count(self) -> int:
        """获取活跃订单数量"""
        return len(self._active_orders)
    
    def get_polling_status(self) -> Dict[str, Any]:
        """获取轮询状态信息"""
        return {
            'active_orders': list(self._active_orders),
            'polling_tasks': list(self._polling_tasks.keys()),
            'polling_interval': self._polling_interval,
            'max_duration_minutes': self._max_polling_duration_minutes
        }
