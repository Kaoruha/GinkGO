"""
Live Account 相关数据模型

与前端 web-ui/src/api/modules/live.ts 中的类型定义对应
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class ExchangeType(str, Enum):
    """交易所类型"""
    OKX = "okx"
    BINANCE = "binance"


class EnvironmentType(str, Enum):
    """环境类型"""
    TESTNET = "testnet"
    PRODUCTION = "production"


class AccountStatus(str, Enum):
    """账号状态"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class LiveAccountSummary(BaseModel):
    """实盘账号摘要"""
    uuid: str
    user_id: str
    exchange: ExchangeType
    environment: EnvironmentType
    name: str
    description: Optional[str] = None
    status: AccountStatus
    validation_status: Optional[str] = None
    last_validated_at: Optional[str] = None
    created_at: str
    updated_at: str


class LiveAccountDetail(LiveAccountSummary):
    """实盘账号详情"""
    pass


class CreateLiveAccountRequest(BaseModel):
    """创建实盘账号请求"""
    exchange: ExchangeType
    name: str = Field(..., min_length=1, max_length=200)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    passphrase: Optional[str] = None
    environment: EnvironmentType = Field(default=EnvironmentType.TESTNET)
    description: Optional[str] = None
    auto_validate: bool = Field(default=False)


class UpdateLiveAccountRequest(BaseModel):
    """更新实盘账号请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    description: Optional[str] = None


class UpdateAccountStatusRequest(BaseModel):
    """更新账号状态请求"""
    status: AccountStatus


class ValidateAccountResponse(BaseModel):
    """验证账号响应"""
    valid: bool
    message: str
    account_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CurrencyBalance(BaseModel):
    """币种余额"""
    currency: str
    available: str
    frozen: str
    balance: str


class BalanceResponse(BaseModel):
    """余额响应"""
    total_equity: str
    available_balance: str
    frozen_balance: str
    currency_balances: List[CurrencyBalance] = []


class PositionItem(BaseModel):
    """持仓项"""
    symbol: str
    side: str
    size: str
    avg_price: str
    current_price: str
    unrealized_pnl: str
    unrealized_pnl_percentage: str
    margin: str


class PositionsResponse(BaseModel):
    """持仓响应"""
    positions: List[PositionItem] = []
