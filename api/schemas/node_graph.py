"""
节点图配置 Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class NodePort(BaseModel):
    """节点端口定义"""
    name: str
    type: str  # 'input' or 'output'
    data_type: str
    required: bool = False
    label: Optional[str] = None


class NodeData(BaseModel):
    """节点数据"""
    label: str
    config: Dict[str, Any] = Field(default_factory=dict)
    componentUuid: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class GraphNode(BaseModel):
    """图节点"""
    id: str
    type: str = Field(..., pattern=r'^(engine|feeder|broker|portfolio|strategy|selector|sizer|risk|analyzer)$')
    position: Dict[str, float]
    data: NodeData


class GraphEdge(BaseModel):
    """图连接线"""
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    type: Optional[str] = None
    animated: bool = False


class Viewport(BaseModel):
    """画布视口状态"""
    x: float = 0
    y: float = 0
    zoom: float = Field(ge=0.1, le=2, default=1)


class GraphData(BaseModel):
    """节点图数据"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    viewport: Optional[Viewport] = None


class NodeGraphSummary(BaseModel):
    """节点图摘要"""
    uuid: str
    name: str
    description: Optional[str] = None
    is_template: bool = False
    is_public: bool = False
    version: int = 1
    created_at: datetime
    updated_at: datetime


class NodeGraph(NodeGraphSummary):
    """节点图详情"""
    graph_data: GraphData
    user_uuid: str
    parent_uuid: Optional[str] = None


# 别名，与前端类型保持一致
NodeGraphDetail = NodeGraph


class NodeGraphCreate(BaseModel):
    """创建节点图请求"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    graph_data: GraphData
    is_template: bool = False
    is_public: bool = False


class NodeGraphUpdate(BaseModel):
    """更新节点图请求"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    graph_data: Optional[GraphData] = None
    is_template: Optional[bool] = None
    is_public: Optional[bool] = None


class NodeTemplate(BaseModel):
    """节点图模板"""
    uuid: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    graph_data: GraphData
    is_system: bool = False
    created_at: datetime
    updated_at: datetime


class ValidationErrorItem(BaseModel):
    """验证错误项"""
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    message: str
    severity: str = Field(..., pattern=r'^(error|warning)$')


class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class AnalyzerConfig(BaseModel):
    """分析器配置"""
    uuid: Optional[str] = None  # 已有分析器的UUID
    name: str = Field(..., description="分析器名称")
    type: str = Field(..., description="分析器类型")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="分析器参数")


class EngineConfig(BaseModel):
    """Engine 配置"""
    start_date: str
    end_date: str
    broker_type: str = "backtest"
    initial_cash: Optional[float] = Field(None, gt=0, description="初始资金覆盖")
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0001
    broker_attitude: int = Field(default=2, ge=1, le=3)
    # 分析器配置（Engine 级别）
    analyzers: Optional[List[AnalyzerConfig]] = Field(default_factory=list, description="分析器列表")


class ComponentConfig(BaseModel):
    """组件配置"""
    max_position_ratio: Optional[float] = Field(None, ge=0, le=1)
    stop_loss_ratio: Optional[float] = Field(None, ge=0, le=1)
    take_profit_ratio: Optional[float] = Field(None, ge=0, le=1)
    benchmark_return: float = 0.0
    frequency: str = "DAY"


class BacktestTaskCreate(BaseModel):
    """回测任务创建配置"""
    name: str
    engine_uuid: Optional[str] = None
    portfolio_uuids: List[str]
    engine_config: EngineConfig
    component_config: Optional[ComponentConfig] = None


class CompileResult(BaseModel):
    """编译结果"""
    backtest_config: BacktestTaskCreate
    warnings: List[str] = Field(default_factory=list)


class PaginatedNodeGraphs(BaseModel):
    """分页节点图列表"""
    data: List[NodeGraphSummary]
    total: int
    page: int
    page_size: int
