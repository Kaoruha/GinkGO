"""
OKXBroker - OKX交易所Broker实现

提供与OKX交易所的API接口，支持：
- 账户管理
- 订单提交和撤销
- 持仓查询
- 实时行情订阅
"""

import time
import hmac
import base64
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests

from .base_broker import BaseBroker, ExecutionResult, ExecutionStatus, Position, AccountInfo
from ginkgo.backtest.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES
from ginkgo.libs import GLOG


class OKXBroker(BaseBroker):
    """
    OKX交易所Broker实现
    
    注意：这是一个基础实现框架，实际使用时需要：
    1. 安装OKX Python SDK: pip install okx
    2. 配置API密钥和权限
    3. 根据具体交易需求调整参数
    """
    
    def __init__(self, broker_config: Dict[str, Any]):
        """
        初始化OKX Broker
        
        Args:
            broker_config: 配置字典，包含:
                - api_key: API密钥
                - secret_key: 密钥
                - passphrase: 口令
                - sandbox: 是否使用沙盒环境
                - instType: 产品类型 (SPOT, MARGIN, SWAP, FUTURES, OPTION)
        """
        super().__init__(broker_config)
        
        # OKX API配置
        self.api_key = broker_config.get('api_key', '')
        self.secret_key = broker_config.get('secret_key', '')
        self.passphrase = broker_config.get('passphrase', '')
        self.sandbox = broker_config.get('sandbox', True)
        self.inst_type = broker_config.get('instType', 'SPOT')  # 产品类型
        
        # API端点
        if self.sandbox:
            self.base_url = "https://www.okx.com"  # 沙盒环境
        else:
            self.base_url = "https://www.okx.com"  # 生产环境
            
        # HTTP会话
        self.session = requests.Session()
        
        # 订单映射 {local_order_id: okx_order_id}
        self._order_mapping = {}
        
    def connect(self) -> bool:
        """
        建立与OKX的连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 测试API连接 - 获取账户信息
            account_info = self._get_account_balance()
            if account_info:
                self._connected = True
                GLOG.info(f"OKXBroker connected successfully")
                return True
            else:
                GLOG.ERROR("OKXBroker connection failed - unable to get account info")
                return False
                
        except Exception as e:
            GLOG.ERROR(f"OKXBroker connection failed: {str(e)}")
            return False
            
    def disconnect(self) -> bool:
        """断开连接"""
        self._connected = False
        self.session.close()
        return True
        
    def submit_order(self, order: Order) -> ExecutionResult:
        """
        提交订单到OKX
        
        Args:
            order: 订单对象
            
        Returns:
            ExecutionResult: 执行结果
        """
        if not self.is_connected:
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message="Not connected to OKX"
            )
            
        if not self.validate_order(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Order validation failed"
            )
            
        try:
            # 构建OKX订单参数
            okx_order_data = self._build_okx_order(order)
            
            # 提交订单
            response = self._place_order(okx_order_data)
            
            if response and response.get('code') == '0':
                # 订单提交成功
                okx_order_id = response['data'][0]['ordId']
                self._order_mapping[order.uuid] = okx_order_id
                
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.SUBMITTED,
                    broker_order_id=okx_order_id,
                    message="Order submitted successfully"
                )
            else:
                error_msg = response.get('msg', 'Unknown error') if response else 'API call failed'
                return ExecutionResult(
                    order_id=order.uuid,
                    status=ExecutionStatus.REJECTED,
                    message=f"Order rejected: {error_msg}"
                )
                
        except Exception as e:
            GLOG.ERROR(f"OKXBroker order submission failed: {str(e)}")
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message=f"Submission error: {str(e)}"
            )
            
    def cancel_order(self, order_id: str) -> ExecutionResult:
        """
        撤销订单
        
        Args:
            order_id: 本地订单ID
            
        Returns:
            ExecutionResult: 执行结果
        """
        if not self.is_connected:
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message="Not connected to OKX"
            )
            
        try:
            okx_order_id = self._order_mapping.get(order_id)
            if not okx_order_id:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message="Order ID not found"
                )
                
            # 撤销订单
            response = self._cancel_order_api(okx_order_id)
            
            if response and response.get('code') == '0':
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.CANCELLED,
                    message="Order cancelled successfully"
                )
            else:
                error_msg = response.get('msg', 'Unknown error') if response else 'API call failed'
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message=f"Cancel failed: {error_msg}"
                )
                
        except Exception as e:
            GLOG.ERROR(f"OKXBroker order cancellation failed: {str(e)}")
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message=f"Cancellation error: {str(e)}"
            )
            
    def query_order(self, order_id: str) -> ExecutionResult:
        """
        查询订单状态
        
        Args:
            order_id: 本地订单ID
            
        Returns:
            ExecutionResult: 订单状态
        """
        if not self.is_connected:
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message="Not connected to OKX"
            )
            
        try:
            okx_order_id = self._order_mapping.get(order_id)
            if not okx_order_id:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message="Order ID not found"
                )
                
            # 查询订单
            response = self._get_order_info(okx_order_id)
            
            if response and response.get('code') == '0' and response['data']:
                order_data = response['data'][0]
                status = self._convert_okx_status(order_data['state'])
                
                return ExecutionResult(
                    order_id=order_id,
                    status=status,
                    filled_volume=float(order_data.get('fillSz', 0)),
                    filled_price=float(order_data.get('avgPx', 0)),
                    broker_order_id=okx_order_id,
                    message=f"Order status: {order_data['state']}"
                )
            else:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message="Failed to query order status"
                )
                
        except Exception as e:
            GLOG.ERROR(f"OKXBroker order query failed: {str(e)}")
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message=f"Query error: {str(e)}"
            )
            
    def get_positions(self) -> List[Position]:
        """
        获取持仓信息
        
        Returns:
            List[Position]: 持仓列表
        """
        if not self.is_connected:
            return []
            
        try:
            response = self._get_positions_api()
            positions = []
            
            if response and response.get('code') == '0':
                for pos_data in response['data']:
                    position = Position(
                        code=pos_data['instId'],
                        volume=float(pos_data['pos']),
                        available_volume=float(pos_data['availPos']),
                        avg_price=float(pos_data['avgPx']),
                        market_value=float(pos_data['notionalUsd']),
                        unrealized_pnl=float(pos_data['upl']),
                        direction=DIRECTION_TYPES.LONG if pos_data['posSide'] == 'long' else DIRECTION_TYPES.SHORT
                    )
                    positions.append(position)
                    
            return positions
            
        except Exception as e:
            GLOG.ERROR(f"OKXBroker get positions failed: {str(e)}")
            return []
            
    def get_account_info(self) -> AccountInfo:
        """
        获取账户信息
        
        Returns:
            AccountInfo: 账户信息
        """
        if not self.is_connected:
            return AccountInfo(
                total_asset=0, available_cash=0, frozen_cash=0, 
                market_value=0, total_pnl=0
            )
            
        try:
            response = self._get_account_balance()
            
            if response and response.get('code') == '0' and response['data']:
                balance_data = response['data'][0]
                details = balance_data.get('details', [])
                
                # 通常取USDT或主要货币的余额
                main_currency = details[0] if details else {}
                
                return AccountInfo(
                    total_asset=float(balance_data.get('totalEq', 0)),
                    available_cash=float(main_currency.get('availBal', 0)),
                    frozen_cash=float(main_currency.get('frozenBal', 0)),
                    market_value=float(balance_data.get('notionalUsd', 0)),
                    total_pnl=float(balance_data.get('upl', 0))
                )
                
        except Exception as e:
            GLOG.ERROR(f"OKXBroker get account info failed: {str(e)}")
            
        return AccountInfo(
            total_asset=0, available_cash=0, frozen_cash=0, 
            market_value=0, total_pnl=0
        )
    
    # ==================== Private API Methods ====================
    
    def _build_okx_order(self, order: Order) -> Dict[str, str]:
        """构建OKX订单参数"""
        order_data = {
            'instId': order.code,
            'tdMode': 'cash',  # 交易模式：现金交易
            'side': 'buy' if order.direction == DIRECTION_TYPES.LONG else 'sell',
            'sz': str(order.volume),
            'ordType': 'limit' if order.order_type == ORDER_TYPES.LIMITORDER else 'market'
        }
        
        if order.order_type == ORDER_TYPES.LIMITORDER:
            order_data['px'] = str(order.limit_price)
            
        return order_data
    
    def _convert_okx_status(self, okx_status: str) -> ExecutionStatus:
        """转换OKX订单状态到内部状态"""
        status_mapping = {
            'live': ExecutionStatus.SUBMITTED,
            'filled': ExecutionStatus.FILLED,
            'partially_filled': ExecutionStatus.PARTIALLY_FILLED,
            'canceled': ExecutionStatus.CANCELLED,
            'mmp_canceled': ExecutionStatus.CANCELLED,
        }
        return status_mapping.get(okx_status, ExecutionStatus.FAILED)
    
    def _get_signature(self, message: str) -> str:
        """生成API签名"""
        return base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()
        ).decode('utf-8')
    
    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        """生成请求头"""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        message = timestamp + method.upper() + request_path + body
        signature = self._get_signature(message)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def _place_order(self, order_data: Dict[str, str]) -> Optional[Dict]:
        """下单API调用"""
        url = f"{self.base_url}/api/v5/trade/order"
        body = json.dumps(order_data)
        headers = self._get_headers('POST', '/api/v5/trade/order', body)
        
        # TODO(human): Add robust error handling and retry logic here
        # Consider: exponential backoff, rate limit handling (429), server errors (5xx),
        # timeout configuration, and consistent retry behavior
        
        response = self.session.post(url, headers=headers, data=body)
        return response.json() if response.status_code == 200 else None
    
    def _cancel_order_api(self, order_id: str) -> Optional[Dict]:
        """撤单API调用"""
        url = f"{self.base_url}/api/v5/trade/cancel-order"
        order_data = {'ordId': order_id}
        body = json.dumps(order_data)
        headers = self._get_headers('POST', '/api/v5/trade/cancel-order', body)
        
        response = self.session.post(url, headers=headers, data=body)
        return response.json() if response.status_code == 200 else None
    
    def _get_order_info(self, order_id: str) -> Optional[Dict]:
        """查询订单API调用"""
        url = f"{self.base_url}/api/v5/trade/order"
        params = {'ordId': order_id}
        request_path = '/api/v5/trade/order?' + '&'.join([f"{k}={v}" for k, v in params.items()])
        headers = self._get_headers('GET', request_path)
        
        response = self.session.get(url, headers=headers, params=params)
        return response.json() if response.status_code == 200 else None
    
    def _get_positions_api(self) -> Optional[Dict]:
        """获取持仓API调用"""
        url = f"{self.base_url}/api/v5/account/positions"
        headers = self._get_headers('GET', '/api/v5/account/positions')
        
        response = self.session.get(url, headers=headers)
        return response.json() if response.status_code == 200 else None
    
    def _get_account_balance(self) -> Optional[Dict]:
        """获取账户余额API调用"""
        url = f"{self.base_url}/api/v5/account/balance"
        headers = self._get_headers('GET', '/api/v5/account/balance')
        
        response = self.session.get(url, headers=headers)
        return response.json() if response.status_code == 200 else None