"""
组件参数模型 - 前后端共享
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ParamType(str, Enum):
    """参数类型"""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"


class ComponentParameter(BaseModel):
    """组件参数定义"""
    name: str = Field(..., description="参数名（代码中使用）")
    display_name: str = Field(..., description="显示名称（前端显示）")
    type: ParamType = Field(..., description="参数类型")
    default_value: Any = Field(None, description="默认值")
    description: str = Field("", description="参数描述")
    required: bool = Field(False, description="是否必需")
    min_value: Optional[float] = Field(None, description="最小值（数值类型）")
    max_value: Optional[float] = Field(None, description="最大值（数值类型）")
    options: Optional[List[Any]] = Field(None, description="可选值（枚举类型）")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "period",
                "display_name": "周期",
                "type": "int",
                "default_value": 252,
                "description": "计算周期",
                "required": False,
                "min_value": 1,
                "max_value": 1000
            }
        }


class ComponentConfig(BaseModel):
    """组件配置（前后端共享）"""
    component_uuid: str
    component_name: str
    component_type: str  # STRATEGY, SELECTOR, SIZER, RISKMANAGER, ANALYZER
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "component_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "component_name": "SharpeAnalyzer",
                "component_type": "ANALYZER",
                "parameters": {
                    "period": 252,
                    "risk_free_rate": 0.03,
                    "annualization": 252
                }
            }
        }


# 预定义组件参数定义
COMPONENT_PARAMETER_DEFINITIONS: Dict[str, List[ComponentParameter]] = {
    "SharpeAnalyzer": [
        ComponentParameter(
            name="period",
            display_name="计算周期",
            type=ParamType.INT,
            default_value=252,
            description="用于计算收益率的周期数",
            min_value=1,
            max_value=10000
        ),
        ComponentParameter(
            name="risk_free_rate",
            display_name="无风险利率",
            type=ParamType.FLOAT,
            default_value=0.03,
            description="年化无风险利率",
            min_value=0.0,
            max_value=1.0
        ),
        ComponentParameter(
            name="annualization",
            display_name="年化系数",
            type=ParamType.INT,
            default_value=252,
            description="一年中的交易日数量",
            options=[1, 252, 365]
        )
    ],
    "MaxDrawdownAnalyzer": [
        ComponentParameter(
            name="use_returns",
            display_name="使用收益率",
            type=ParamType.BOOL,
            default_value=True,
            description="是否使用收益率计算（否则使用净值）"
        )
    ],
    "PositionRatioRisk": [
        ComponentParameter(
            name="max_position_ratio",
            display_name="最大持仓比例",
            type=ParamType.FLOAT,
            default_value=0.2,
            description="单个股票最大持仓比例",
            min_value=0.0,
            max_value=1.0
        ),
        ComponentParameter(
            name="max_total_position_ratio",
            display_name="最大总持仓比例",
            type=ParamType.FLOAT,
            default_value=0.8,
            description="所有股票总持仓比例上限",
            min_value=0.0,
            max_value=1.0
        )
    ],
    "LossLimitRisk": [
        ComponentParameter(
            name="loss_limit",
            display_name="止损比例",
            type=ParamType.FLOAT,
            default_value=0.1,
            description="触发止损的亏损比例",
            min_value=0.0,
            max_value=1.0
        )
    ],
    "ProfitLimitRisk": [
        ComponentParameter(
            name="profit_limit",
            display_name="止盈比例",
            type=ParamType.FLOAT,
            default_value=0.2,
            description="触发止盈的盈利比例",
            min_value=0.0,
            max_value=10.0
        )
    ],
    "FixedAmountSizer": [
        ComponentParameter(
            name="amount",
            display_name="交易金额",
            type=ParamType.FLOAT,
            default_value=10000.0,
            description="每次交易的固定金额",
            min_value=0.0
        )
    ],
    "FixedRatioSizer": [
        ComponentParameter(
            name="ratio",
            display_name="交易比例",
            type=ParamType.FLOAT,
            default_value=0.1,
            description="每次交易占总资产的比例",
            min_value=0.0,
            max_value=1.0
        )
    ],
    "VolatilityRatioSizer": [
        ComponentParameter(
            name="base_ratio",
            display_name="基础比例",
            type=ParamType.FLOAT,
            default_value=0.1,
            description="基础交易比例",
            min_value=0.0,
            max_value=1.0
        ),
        ComponentParameter(
            name="volatility_window",
            display_name="波动率窗口",
            type=ParamType.INT,
            default_value=20,
            description="计算波动率的周期",
            min_value=1,
            max_value=1000
        )
    ],
    "AllSelector": [
        ComponentParameter(
            name="codes",
            display_name="股票代码列表",
            type=ParamType.LIST,
            default_value=[],
            description="选中的股票代码列表"
        )
    ],
    "StaticSelector": [
        ComponentParameter(
            name="codes",
            display_name="股票代码列表",
            type=ParamType.LIST,
            default_value=[],
            description="固定的股票代码列表",
            required=True
        )
    ],
}
