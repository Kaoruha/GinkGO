"""
回测相关API路由

按照 Engine 装配逻辑设计：
1. Engine 配置：时间范围、Broker 参数
2. Portfolio 选择：选择投资组合
3. 组件配置：策略、选择器、Sizer、风控、分析器
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import json

from core.database import get_db
from core.logging import logger
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
from ginkgo.interfaces.kafka_topics import KafkaTopics

router = APIRouter()

# Kafka Producer（延迟初始化）
_kafka_producer: Optional[GinkgoProducer] = None


def get_kafka_producer() -> GinkgoProducer:
    """获取Kafka Producer（单例）"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = GinkgoProducer()
    return _kafka_producer


# ==================== 数据模型 ====================

class BacktestTaskSummary(BaseModel):
    """回测任务摘要"""
    uuid: str
    name: str
    portfolio_name: str
    state: str  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    progress: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BacktestTaskDetail(BaseModel):
    """回测任务详情"""
    uuid: str
    name: str
    portfolio_name: str
    portfolio_uuid: str
    state: str
    progress: float

    # Engine信息（从 config 中解析）
    engine_uuid: Optional[str] = None

    # 时间信息
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # 回测配置
    config: dict

    # 回测结果
    result: Optional[dict] = None

    # Worker信息
    worker_id: Optional[str] = None

    # 错误信息
    error: Optional[str] = None


class AnalyzerConfig(BaseModel):
    """分析器配置"""
    name: str = Field(..., description="分析器名称")
    type: str = Field(..., description="分析器类型，如 SharpeAnalyzer, DrawdownAnalyzer")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="分析器参数")


class EngineConfig(BaseModel):
    """Engine 配置"""
    # 时间范围
    start_date: str = Field(..., description="回测开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="回测结束日期 (YYYY-MM-DD)")

    # Broker 类型选择
    broker_type: str = Field("backtest", description="Broker类型: backtest(SimBroker)")

    # 初始资金（可选，用于覆盖 Portfolio 的 initial_cash）
    initial_cash: Optional[float] = Field(None, gt=0, description="初始资金覆盖（可选）")

    # Broker 配置
    commission_rate: float = Field(0.0003, ge=0, description="手续费率")
    slippage_rate: float = Field(0.0001, ge=0, description="滑点率")
    broker_attitude: int = Field(2, description="Broker态度: 1=PESSIMISTIC, 2=OPTIMISTIC, 3=RANDOM")
    commission_min: Optional[int] = Field(5, ge=0, description="最小手续费")

    # 分析器配置（Engine 级别）
    analyzers: Optional[List[AnalyzerConfig]] = Field(default_factory=list, description="分析器列表")


class ComponentConfig(BaseModel):
    """组件配置"""
    # 风控参数
    max_position_ratio: Optional[float] = Field(0.3, gt=0, le=1, description="最大持仓比例")
    stop_loss_ratio: Optional[float] = Field(0.05, ge=0, le=1, description="止损比例")
    take_profit_ratio: Optional[float] = Field(0.15, ge=0, le=1, description="止盈比例")

    # 其他参数
    benchmark_return: Optional[float] = Field(0.0, description="基准收益率")
    frequency: Optional[str] = Field("DAY", description="数据频率")


class BacktestTaskCreate(BaseModel):
    """
    创建回测任务

    按照 Engine 装配逻辑设计：
    1. Engine 配置：时间范围、Broker 参数
    2. Portfolio 选择：支持多个投资组合
    3. 组件配置：策略、风控等参数
    """
    # 基本信息
    name: str = Field(..., min_length=1, max_length=255, description="任务名称")

    # 可选：选择现有 Engine（会预填充配置）
    engine_uuid: Optional[str] = Field(None, description="Engine UUID（可选，用于预填充配置）")

    # Portfolio 选择（支持多个）
    portfolio_uuids: List[str] = Field(..., min_items=1, description="Portfolio UUID 列表")

    # Engine 配置（如果选择 Engine 则可选覆盖）
    engine_config: EngineConfig

    # 组件配置（可选）
    component_config: Optional[ComponentConfig] = None


# ==================== 数据库操作 ====================

async def get_engine_config(db, engine_uuid: str) -> dict:
    """从数据库获取Engine配置"""
    query = """
        SELECT uuid, name, backtest_start_date, backtest_end_date,
               broker_attitude, config_snapshot
        FROM engine
        WHERE uuid = %s AND is_live = 0
    """
    await db.execute(query, [engine_uuid])
    engine = await db.fetchone()

    if not engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine {engine_uuid} not found or not a backtest engine"
        )

    return {
        "uuid": engine["uuid"],
        "name": engine["name"],
        "start_date": engine["backtest_start_date"].isoformat() if engine["backtest_start_date"] else None,
        "end_date": engine["backtest_end_date"].isoformat() if engine["backtest_end_date"] else None,
        "broker_attitude": engine["broker_attitude"],
        "config_snapshot": json.loads(engine["config_snapshot"]) if engine["config_snapshot"] else {},
    }


async def get_portfolio_name(db, portfolio_uuid: str) -> str:
    """获取Portfolio名称"""
    # TODO: 从portfolio表查询
    # 暂时返回占位符
    return "Unknown Portfolio"


async def create_backtest_task(db, data: BacktestTaskCreate) -> dict:
    """
    创建回测任务（写入MySQL）

    按照 Engine 装配逻辑组织配置，支持多个 Portfolio
    """
    task_uuid = str(uuid.uuid4())
    now = datetime.utcnow()

    # 如果提供了 Engine，获取其配置作为基础
    engine_base_config = {}
    if data.engine_uuid:
        engine_config = await get_engine_config(db, data.engine_uuid)
        engine_base_config = {
            "engine_uuid": data.engine_uuid,
            "engine_name": engine_config["name"],
        }

    # 构建 config（合并 Engine 配置和用户提供的配置）
    config = {
        # Engine 配置
        "start_date": data.engine_config.start_date,
        "end_date": data.engine_config.end_date,
        "commission_rate": data.engine_config.commission_rate,
        "slippage_rate": data.engine_config.slippage_rate,
        "broker_attitude": data.engine_config.broker_attitude,
        "commission_min": data.engine_config.commission_min,
        "broker_type": data.engine_config.broker_type,
        # 初始资金覆盖（可选）
        "initial_cash": data.engine_config.initial_cash,
        # 分析器配置（Engine 级别）
        "analyzers": [a.dict() for a in (data.engine_config.analyzers or [])],
        # Portfolio 列表
        "portfolio_uuids": data.portfolio_uuids,
        # 来自 Engine 的基础配置
        **engine_base_config,
    }

    # 添加组件配置（如果有）
    if data.component_config:
        config.update({
            "max_position_ratio": data.component_config.max_position_ratio,
            "stop_loss_ratio": data.component_config.stop_loss_ratio,
            "take_profit_ratio": data.component_config.take_profit_ratio,
            "benchmark_return": data.component_config.benchmark_return,
            "frequency": data.component_config.frequency,
        })

    # 获取 Portfolio 名称（多个）
    portfolio_names = []
    for portfolio_uuid in data.portfolio_uuids:
        name = await get_portfolio_name(db, portfolio_uuid)
        portfolio_names.append(name)
    portfolio_name_str = ", ".join(portfolio_names)

    # 写入数据库（主 Portfolio 是第一个）
    primary_portfolio_uuid = data.portfolio_uuids[0]
    query = """
        INSERT INTO backtest_tasks (
            uuid, name, portfolio_uuid, portfolio_name, state, progress,
            config, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    await db.execute(query, (
        task_uuid, data.name, primary_portfolio_uuid, portfolio_name_str,
        "PENDING", 0.0, json.dumps(config), now
    ))

    return {
        "uuid": task_uuid,
        "name": data.name,
        "portfolio_uuid": primary_portfolio_uuid,
        "portfolio_uuids": data.portfolio_uuids,
        "portfolio_name": portfolio_name_str,
        "state": "PENDING",
        "progress": 0.0,
        "engine_uuid": config.get("engine_uuid"),
        "config": config,
        "created_at": now.isoformat() + "Z",
        "started_at": None,
        "completed_at": None,
        "result": None,
        "worker_id": None,
        "error": None,
    }


async def send_task_to_kafka(task_uuid: str, portfolio_uuids: list, name: str, config: dict):
    """发送任务到Kafka"""
    producer = get_kafka_producer()

    assignment = {
        "command": "start",
        "task_uuid": task_uuid,
        "portfolio_uuid": portfolio_uuids[0] if portfolio_uuids else None,  # 主 Portfolio
        "portfolio_uuids": portfolio_uuids,  # 所有 Portfolio
        "name": name,
        "config": config,
        "priority": 0,
    }

    producer.send(
        topic=KafkaTopics.BACKTEST_ASSIGNMENTS,
        msg=assignment,
    )

    logger.info(f"Task {task_uuid} sent to Kafka with {len(portfolio_uuids)} portfolio(s)")


async def send_cancel_to_kafka(task_uuid: str):
    """发送取消命令到Kafka"""
    producer = get_kafka_producer()

    command = {
        "command": "cancel",
        "task_uuid": task_uuid,
    }

    producer.send(
        topic=KafkaTopics.BACKTEST_ASSIGNMENTS,
        msg=command,
    )

    logger.info(f"Cancel command for {task_uuid} sent to Kafka")


# ==================== API路由 ====================

@router.get("", response_model=list[BacktestTaskSummary])
async def list_backtests(
    state: Optional[str] = Query(None, description="按状态筛选"),
):
    """获取回测任务列表"""
    async with get_db() as db:
        query = "SELECT * FROM backtest_tasks"
        params = []

        if state:
            query += " WHERE state = %s"
            params.append(state)

        query += " ORDER BY created_at DESC"

        await db.execute(query, params)
        results = await db.fetchall()

    summaries = []
    for row in results:
        summaries.append({
            "uuid": row["uuid"],
            "name": row["name"],
            "portfolio_name": row["portfolio_name"],
            "state": row["state"],
            "progress": float(row["progress"]) if row["progress"] else 0.0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "started_at": row["started_at"].isoformat() if row.get("started_at") else None,
            "completed_at": row["completed_at"].isoformat() if row.get("completed_at") else None,
        })

    return summaries


@router.get("/engines", response_model=list[dict])
async def list_backtest_engines(
    is_live: bool = Query(False, description="过滤是否实盘引擎")
):
    """
    获取可用的 Engine 列表

    返回所有回测 Engine（is_live=0），可用于预填充配置
    """
    async with get_db() as db:
        query = """
            SELECT
                uuid,
                name,
                is_live,
                backtest_start_date,
                backtest_end_date,
                broker_attitude,
                create_at
            FROM engine
            WHERE is_live = %s
            ORDER BY create_at DESC
        """
        await db.execute(query, [int(is_live)])
        results = await db.fetchall()

        engines = []
        for row in results:
            engines.append({
                "uuid": row["uuid"],
                "name": row["name"],
                "is_live": bool(row["is_live"]),
                "backtest_start_date": row["backtest_start_date"].isoformat() if row["backtest_start_date"] else None,
                "backtest_end_date": row["backtest_end_date"].isoformat() if row["backtest_end_date"] else None,
                "broker_attitude": row["broker_attitude"],
                "created_at": row["create_at"].isoformat() if row["create_at"] else None,
            })

        return engines


# ==================== 分析器 API ====================

class AnalyzerTypeInfo(BaseModel):
    """分析器类型信息"""
    type: str = Field(..., description="分析器类型标识")
    name: str = Field(..., description="分析器名称")
    description: str = Field(..., description="分析器描述")
    default_config: Dict[str, Any] = Field(default_factory=dict, description="默认配置")


@router.get("/analyzers", response_model=list[AnalyzerTypeInfo])
async def list_analyzers():
    """
    获取可用的分析器类型列表

    返回所有支持的分析器类型及其默认配置
    """
    # TODO: 未来可以从数据库或配置文件读取
    analyzers = [
        {
            "type": "SharpeAnalyzer",
            "name": "Sharpe",
            "description": "夏普比率分析",
            "default_config": {
                "period": 252,
                "risk_free_rate": 0.03,
                "annualization": 252
            }
        },
        {
            "type": "DrawdownAnalyzer",
            "name": "Drawdown",
            "description": "最大回撤分析",
            "default_config": {}
        },
        {
            "type": "ReturnAnalyzer",
            "name": "Return",
            "description": "收益率分析",
            "default_config": {
                "benchmark_return": 0.0
            }
        },
        {
            "type": "PortfolioAnalyzer",
            "name": "Portfolio",
            "description": "投资组合分析",
            "default_config": {}
        },
        {
            "type": "ComparisonAnalyzer",
            "name": "Comparison",
            "description": "多Portfolio对比分析",
            "default_config": {}
        }
    ]

    return analyzers


@router.get("/{uuid}", response_model=BacktestTaskDetail)
async def get_backtest(uuid: str):
    """获取回测任务详情"""
    async with get_db() as db:
        query = "SELECT * FROM backtest_tasks WHERE uuid = %s"
        await db.execute(query, [uuid])
        result = await db.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest task {uuid} not found"
            )

        # 解析配置
        config = json.loads(result["config"]) if result["config"] else {}
        engine_uuid = config.get("engine_uuid")  # 从 config 中提取 engine_uuid

        return {
            "uuid": result["uuid"],
            "name": result["name"],
            "portfolio_uuid": result["portfolio_uuid"],
            "portfolio_name": result["portfolio_name"],
            "state": result["state"],
            "progress": float(result["progress"]) if result["progress"] else 0.0,
            "engine_uuid": engine_uuid,
            "created_at": result["created_at"].isoformat() if result["created_at"] else None,
            "started_at": result["started_at"].isoformat() if result.get("started_at") else None,
            "completed_at": result["completed_at"].isoformat() if result.get("completed_at") else None,
            "config": config,
            "result": json.loads(result["result"]) if result.get("result") else None,
            "worker_id": result.get("worker_id"),
            "error": result.get("error"),
        }


@router.post("", response_model=BacktestTaskDetail, status_code=status.HTTP_201_CREATED)
async def create_backtest(data: BacktestTaskCreate):
    """
    创建回测任务

    按照 Engine 装配逻辑：
    1. Engine 配置：时间范围、Broker 参数
    2. Portfolio：选择投资组合
    3. 组件配置：风控等参数

    流程：
    1. 写入MySQL（state=PENDING）
    2. 发送到Kafka
    3. 返回任务详情
    """
    async with get_db() as db:
        # 创建任务（写入数据库）
        task = await create_backtest_task(db, data)

    # 发送到Kafka（分配给Worker）
    await send_task_to_kafka(
        task_uuid=task["uuid"],
        portfolio_uuids=data.portfolio_uuids,
        name=data.name,
        config=task["config"],
    )

    logger.info(f"Backtest task {task['uuid']} created and sent to Kafka")

    return task


@router.post("/{uuid}/start")
async def start_backtest(uuid: str):
    """启动回测任务（发送到Kafka）"""
    async with get_db() as db:
        query = "SELECT * FROM backtest_tasks WHERE uuid = %s"
        await db.execute(query, [uuid])
        result = await db.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest task {uuid} not found"
            )

        if result["state"] not in ["PENDING", "FAILED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start backtest in state {result['state']}"
            )

        # 发送到Kafka
        config = json.loads(result["config"]) if result["config"] else {}
        portfolio_uuids = config.get("portfolio_uuids", [result["portfolio_uuid"]])
        await send_task_to_kafka(
            task_uuid=uuid,
            portfolio_uuids=portfolio_uuids,
            name=result["name"],
            config=config,
        )

        # 更新状态
        await db.execute(
            "UPDATE backtest_tasks SET state = %s, started_at = %s WHERE uuid = %s",
            ["PENDING", datetime.utcnow(), uuid]
        )

        return {"message": "Backtest task sent to execution queue"}


@router.post("/{uuid}/stop")
async def stop_backtest(uuid: str):
    """停止回测任务"""
    async with get_db() as db:
        query = "SELECT * FROM backtest_tasks WHERE uuid = %s"
        await db.execute(query, [uuid])
        result = await db.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest task {uuid} not found"
            )

        if result["state"] != "RUNNING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop backtest in state {result['state']}"
            )

        # 发送取消命令到Kafka
        await send_cancel_to_kafka(uuid)

        # 更新状态
        await db.execute(
            "UPDATE backtest_tasks SET state = %s, completed_at = %s WHERE uuid = %s",
            ["CANCELLED", datetime.utcnow(), uuid]
        )

        return {"message": "Cancel command sent"}


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(uuid: str):
    """删除回测任务"""
    async with get_db() as db:
        query = "SELECT * FROM backtest_tasks WHERE uuid = %s"
        await db.execute(query, [uuid])
        result = await db.fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest task {uuid} not found"
            )

        # 只能删除非运行中的任务
        if result["state"] == "RUNNING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete running backtest"
            )

        # 删除任务
        await db.execute("DELETE FROM backtest_tasks WHERE uuid = %s", [uuid])

        return None
