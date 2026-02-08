"""
事务状态记录模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TransactionStep(BaseModel):
    """事务步骤记录"""
    name: str
    status: str = Field(..., description="步骤状态: pending, executing, completed, failed, compensated")
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None


class TransactionRecord(BaseModel):
    """事务记录"""
    transaction_id: str
    entity_type: str = Field(..., description="实体类型: portfolio, backtest")
    entity_id: Optional[str] = None
    status: str = Field(..., description="事务状态: pending, completed, failed, compensated")
    steps: List[TransactionStep] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
