"""
Portfolio相关数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PortfolioMode(str, Enum):
    """Portfolio运行模式"""
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class PortfolioState(str, Enum):
    """Portfolio状态"""
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class StrategySummary(BaseModel):
    """策略摘要"""
    uuid: str
    name: str
    type: str
    mount_id: Optional[str] = None  # 挂载ID
    code: Optional[str] = None  # 组件代码内容（用于解析参数）


class SelectorSummary(BaseModel):
    """选股器摘要"""
    uuid: str
    name: str
    type: str
    code: Optional[str] = None  # 组件代码内容
    mount_id: Optional[str] = None  # 挂载ID


class SizerSummary(BaseModel):
    """仓位管理器摘要"""
    uuid: str
    name: str
    type: str
    code: Optional[str] = None  # 组件代码内容
    mount_id: Optional[str] = None  # 挂载ID


class RiskManagerSummary(BaseModel):
    """风控管理器摘要"""
    uuid: str
    name: str
    type: str
    code: Optional[str] = None  # 组件代码内容
    mount_id: Optional[str] = None  # 挂载ID


class RiskAlertSummary(BaseModel):
    """风控警报摘要"""
    uuid: str
    type: str
    level: str
    message: str
    triggered_at: datetime
    handled: bool


class Position(BaseModel):
    """持仓信息"""
    code: str
    volume: int
    cost_price: float
    current_price: float


class PortfolioSummary(BaseModel):
    """Portfolio摘要"""
    uuid: str
    name: str
    mode: PortfolioMode
    state: PortfolioState
    config_locked: bool
    net_value: float
    created_at: datetime


class PortfolioDetail(PortfolioSummary):
    """Portfolio详情"""
    initial_cash: float
    current_cash: float
    positions: List[Position] = []
    strategies: List[StrategySummary] = []
    selectors: List[SelectorSummary] = []
    sizers: List[SizerSummary] = []
    risk_managers: List[RiskManagerSummary] = []
    risk_alerts: List[RiskAlertSummary] = []
    # Note: Analyzers 已移至 Engine 级别配置


class PortfolioCreate(BaseModel):
    """创建Portfolio请求"""
    name: str = Field(..., min_length=1, max_length=200)
    initial_cash: float = Field(..., gt=0)
    mode: PortfolioMode = Field(default=PortfolioMode.BACKTEST)
    risk_config: Optional[dict] = None
    # 图数据（用于节点图编辑器创建）
    graph_data: Optional[Dict[str, Any]] = None
    strategies: Optional[List[Dict[str, Any]]] = None
    selectors: Optional[List[Dict[str, Any]]] = None
    sizers: Optional[List[Dict[str, Any]]] = None
    risk_managers: Optional[List[Dict[str, Any]]] = None


class PortfolioUpdate(BaseModel):
    """更新Portfolio请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    state: Optional[PortfolioState] = None
    graph_data: Optional[Dict[str, Any]] = None
    config_locked: Optional[bool] = None


class PortfolioGraphData(BaseModel):
    """节点图数据"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    viewport: Optional[Dict[str, Any]] = None


class PortfolioConfigResponse(BaseModel):
    """投资组合配置响应"""
    uuid: str
    portfolio_uuid: str
    name: str
    description: Optional[str]
    graph_data: PortfolioGraphData
    mode: PortfolioMode
    version: int
    is_template: bool
    tags: List[str]
    created_at: datetime
    updated_at: datetime
