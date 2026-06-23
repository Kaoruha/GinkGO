# Upstream: api.api.backtest (API handler)
# Downstream: BacktestTaskService (Service 层序列化)
"""
Backtest Task Pydantic Schemas

Service 层返回给 API 的类型安全数据结构。
ORM → Schema 转换在 Service 内完成，API handler 只负责 ok(data=result.data)。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


# ==================== 回测任务 ====================

class BacktestTaskSummary(BaseModel):
    """回测任务列表项"""
    uuid: str
    name: str
    portfolio_id: str = ""
    portfolio_name: str = ""
    status: str = "created"
    progress: float = 0
    total_pnl: float = 0.0
    total_orders: int = 0
    total_signals: int = 0
    total_positions: int = 0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    annual_return: float = 0.0
    win_rate: float = 0.0
    final_portfolio_value: float = 0.0
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    backtest_start_date: Optional[str] = None
    backtest_end_date: Optional[str] = None
    error_message: str = ""


class BacktestTaskDetail(BaseModel):
    """回测任务详情"""
    uuid: str
    name: str
    portfolio_id: str = ""
    status: str = "created"
    progress: float = 0
    total_pnl: float = 0.0
    total_orders: int = 0
    total_signals: int = 0
    total_positions: int = 0
    total_events: int = 0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    annual_return: float = 0.0
    win_rate: float = 0.0
    final_portfolio_value: float = 0.0
    backtest_start_date: Optional[str] = None
    backtest_end_date: Optional[str] = None
    engine_uuid: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    config: dict = {}
    result: Optional[dict] = None
    error_message: str = ""


# ==================== 回测结果子项 ====================

class BacktestSignalItem(BaseModel):
    """信号列表项"""
    uuid: str = ""
    portfolio_id: str = ""
    engine_id: str = ""
    task_id: str = ""
    code: str = ""
    direction: Optional[str] = None
    reason: str = ""
    timestamp: Optional[str] = None
    source: Optional[str] = None


class BacktestOrderItem(BaseModel):
    """订单列表项"""
    uuid: str = ""
    portfolio_id: str = ""
    engine_id: str = ""
    task_id: str = ""
    code: str = ""
    direction: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    volume: int = 0
    limit_price: Optional[str] = None  # #5787: 市价单无价哨兵 None, 非 "0"
    transaction_price: str = "0"
    transaction_volume: int = 0
    fee: str = "0"
    timestamp: Optional[str] = None


class BacktestPositionItem(BaseModel):
    """持仓列表项"""
    uuid: str = ""
    portfolio_id: str = ""
    engine_id: str = ""
    task_id: str = ""
    code: str = ""
    cost: str = "0"
    volume: int = 0
    frozen_volume: int = 0
    price: str = "0"
    fee: str = "0"


class BacktestAnalyzerGroup(BaseModel):
    """分析器聚合结果"""
    name: str
    latest_value: Optional[float] = None
    record_count: int = 0
    stats: Dict[str, Any] = {}


class BacktestAnalyzerDataPoint(BaseModel):
    """分析器时序数据点"""
    time: str = ""
    value: Optional[float] = None


class BacktestAnalyzerDetail(BaseModel):
    """单个分析器的完整数据"""
    data: List[BacktestAnalyzerDataPoint] = []
    stats: Optional[Dict[str, Any]] = None


class BacktestNetValueData(BaseModel):
    """净值数据"""
    strategy: List[BacktestAnalyzerDataPoint] = []
    benchmark: List[BacktestAnalyzerDataPoint] = []


# ==================== 创建请求 ====================

class AnalyzerConfig(BaseModel):
    """分析器配置"""
    name: str = Field(..., description="分析器名称")
    type: str = Field(..., description="分析器类型")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="分析器参数")


class EngineConfig(BaseModel):
    """Engine 配置"""
    start_date: str = Field(..., description="回测开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="回测结束日期 (YYYY-MM-DD)")
    broker_type: str = Field("backtest", description="Broker类型")
    initial_cash: Optional[float] = Field(None, gt=0, description="初始资金覆盖")
    commission_rate: float = Field(0.0003, ge=0, description="手续费率")
    slippage_rate: float = Field(0.0001, ge=0, description="滑点率")
    broker_attitude: int = Field(2, ge=1, le=3, description="Broker态度")
    commission_min: Optional[int] = Field(5, ge=0, description="最小手续费")
    analyzers: Optional[List[AnalyzerConfig]] = Field(default_factory=list, description="分析器列表")


class ComponentConfig(BaseModel):
    """组件配置"""
    max_position_ratio: Optional[float] = Field(0.3, gt=0, le=1, description="最大持仓比例")
    stop_loss_ratio: Optional[float] = Field(0.05, ge=0, le=1, description="止损比例")
    take_profit_ratio: Optional[float] = Field(0.15, ge=0, le=1, description="止盈比例")
    benchmark_return: Optional[float] = Field(0.0, description="基准收益率")
    frequency: Optional[str] = Field("DAY", description="数据频率")


class BacktestTaskCreate(BaseModel):
    """创建回测任务请求"""
    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    engine_uuid: Optional[str] = Field(None, description="Engine UUID")
    portfolio_uuids: List[str] = Field(..., min_length=1, description="Portfolio UUID 列表")
    engine_config: EngineConfig
    component_config: Optional[ComponentConfig] = None
    # 旧字段兼容：旧客户端可能发送 portfolio_id (str) 而非 portfolio_uuids (list)
    portfolio_id: Optional[str] = Field(None, exclude=True, description="[已废弃] 请使用 portfolio_uuids")

    @model_validator(mode='before')
    @classmethod
    def _migrate_portfolio_id(cls, values: Any) -> Any:
        """将旧 portfolio_id (str) 转为 portfolio_uuids (list)"""
        if isinstance(values, dict):
            if 'portfolio_uuids' not in values and 'portfolio_id' in values:
                pid = values['portfolio_id']
                if pid:
                    values['portfolio_uuids'] = [pid]
        return values
