"""
回测相关API路由

完全基于 Ginkgo 服务层，不直接访问数据库
"""

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import json
import asyncio

from core.logging import logger
from core.redis_client import get_backtest_progress
from core.response import ok, paginated
from core.exceptions import NotFoundError, ValidationError, BusinessError
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.data.containers import container
from ginkgo.data.services.result_service import ResultService

router = APIRouter()


# ==================== Service 辅助函数 ====================

def get_backtest_task_service():
    """获取 BacktestTaskService 实例"""
    return container.backtest_task_service()


def get_engine_service():
    """获取 EngineService 实例"""
    return container.engine_service()


def get_portfolio_service():
    """获取 PortfolioService 实例"""
    return container.portfolio_service()


def get_result_service() -> ResultService:
    """获取 ResultService 实例"""
    return container.result_service()


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


class AnalyzerTypeInfo(BaseModel):
    """分析器类型信息"""
    name: str
    type: str
    description: str = ""
    parameters: Dict[str, Any] = {}


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


# ==================== Service 层操作 ====================

def get_engine_info(engine_uuid: str) -> dict:
    """从服务层获取Engine信息"""
    engine_service = get_engine_service()
    result = engine_service.get(needle=engine_uuid)

    if not result.is_success() or not result.data:
        raise NotFoundError("Engine", engine_uuid)

    # 处理返回数据（可能是列表或单个对象）
    engine = result.data
    if isinstance(engine, list) and len(engine) > 0:
        engine = engine[0]
    elif isinstance(engine, list):
        raise NotFoundError("Engine", engine_uuid)

    return {
        "uuid": getattr(engine, 'uuid', engine_uuid),
        "name": getattr(engine, 'name', ''),
        "is_live": getattr(engine, 'is_live', 0),
    }


def get_portfolio_info(portfolio_uuid: str) -> dict:
    """从服务层获取Portfolio信息"""
    portfolio_service = get_portfolio_service()
    result = portfolio_service.get(portfolio_id=portfolio_uuid)

    if not result.is_success() or not result.data:
        raise NotFoundError("Portfolio", portfolio_uuid)

    # 处理返回数据（可能是列表或单个对象）
    portfolio = result.data
    if isinstance(portfolio, list) and len(portfolio) > 0:
        portfolio = portfolio[0]
    elif isinstance(portfolio, list):
        raise NotFoundError("Portfolio", portfolio_uuid)

    return {
        "uuid": getattr(portfolio, 'uuid', portfolio_uuid),
        "name": getattr(portfolio, 'name', 'Unknown Portfolio'),
    }


def build_backtest_config(data: BacktestTaskCreate) -> dict:
    """构建回测配置（不访问数据库）"""
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

    # 如果提供了 Engine，获取其信息
    if data.engine_uuid:
        engine_info = get_engine_info(data.engine_uuid)
        config.update({
            "engine_uuid": data.engine_uuid,
            "engine_name": engine_info["name"],
        })

    return config


def create_backtest_task(data: BacktestTaskCreate) -> dict:
    """
    创建回测任务（使用服务层）

    按照 Engine 装配逻辑组织配置，支持多个 Portfolio
    """
    # 构建配置
    config = build_backtest_config(data)

    # 获取 Portfolio 名称（主Portfolio）
    primary_portfolio_uuid = data.portfolio_uuids[0]
    try:
        portfolio_info = get_portfolio_info(primary_portfolio_uuid)
        portfolio_name = portfolio_info["name"]
    except NotFoundError:
        portfolio_name = "Unknown Portfolio"

    # 使用服务层创建任务
    task_service = get_backtest_task_service()
    result = task_service.create(
        name=data.name,
        portfolio_id=primary_portfolio_uuid,
        portfolio_name=portfolio_name,
        config_snapshot=config,
    )

    if not result.is_success():
        raise BusinessError(f"Failed to create backtest task: {result.error}")

    task = result.data

    return {
        "uuid": task.uuid,
        "name": data.name,
        "portfolio_uuid": primary_portfolio_uuid,
        "portfolio_uuids": data.portfolio_uuids,
        "portfolio_name": portfolio_name,
        "state": "PENDING",
        "progress": 0.0,
        "engine_uuid": config.get("engine_uuid"),
        "config": config,
        "created_at": task.created_at if hasattr(task, 'created_at') else datetime.utcnow().isoformat() + "Z",
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


# ==================== API 路由 ====================

@router.get("/")
async def list_backtests(
    status: Optional[str] = Query(None, description="按状态筛选"),
    portfolio_id: Optional[str] = Query(None, description="按投资组合筛选"),
    sort_by: Optional[str] = Query(None, description="排序字段: annual_return / sharpe_ratio / max_drawdown / win_rate / created_at"),
    sort_order: Optional[str] = Query("desc", description="排序方向: asc / desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取回测任务列表（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 使用服务层获取任务
        result = task_service.get(portfolio_id=portfolio_id, status=status)

        if not result.is_success():
            return paginated(items=[], total=0, page=page, page_size=page_size)

        tasks = result.data or []

        # 批量获取 portfolio 名称
        portfolio_ids = set()
        for task in tasks:
            pid = task.get("portfolio_id") if isinstance(task, dict) else getattr(task, 'portfolio_id', '')
            if pid:
                portfolio_ids.add(pid)
        portfolio_names = {}
        if portfolio_ids:
            try:
                portfolio_names = get_portfolio_service().get_names_by_ids(list(portfolio_ids))
            except Exception:
                pass

        # 转换为 API 模型
        summaries = []
        for task in tasks:
            task_dict = task if isinstance(task, dict) else {
                "uuid": getattr(task, 'uuid', ''),
                "name": getattr(task, 'name', ''),
                "portfolio_id": getattr(task, 'portfolio_id', ''),
                "status": getattr(task, 'status', 'created'),
                "progress": getattr(task, 'progress', 0) or 0,
                "total_pnl": getattr(task, 'total_pnl', 0.0) or 0.0,
                "total_orders": getattr(task, 'total_orders', 0) or 0,
                "total_signals": getattr(task, 'total_signals', 0) or 0,
                "total_positions": getattr(task, 'total_positions', 0) or 0,
                "max_drawdown": getattr(task, 'max_drawdown', 0.0) or 0.0,
                "sharpe_ratio": getattr(task, 'sharpe_ratio', 0.0) or 0.0,
                "annual_return": getattr(task, 'annual_return', 0.0) or 0.0,
                "win_rate": getattr(task, 'win_rate', 0.0) or 0.0,
                "final_portfolio_value": getattr(task, 'final_portfolio_value', 0.0) or 0.0,
                "created_at": getattr(task, 'create_at', None),
                "started_at": getattr(task, 'start_time', None),
                "finished_at": getattr(task, 'end_time', None),
                "error_message": getattr(task, 'error_message', '') or '',
            }

            # 将 datetime 对象转换为字符串
            def format_date(dt):
                if dt is None:
                    return None
                if isinstance(dt, str):
                    return dt
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)

            created_at_str = format_date(task_dict.get("created_at"))
            started_at_str = format_date(task_dict.get("started_at"))
            completed_at_str = format_date(task_dict.get("finished_at"))

            summaries.append(BacktestTaskSummary(
                uuid=task_dict["uuid"],
                name=task_dict["name"],
                portfolio_id=task_dict["portfolio_id"],
                portfolio_name=portfolio_names.get(task_dict["portfolio_id"], ""),
                status=task_dict["status"],
                progress=task_dict["progress"],
                total_pnl=task_dict["total_pnl"],
                total_orders=task_dict["total_orders"],
                total_signals=task_dict["total_signals"],
                total_positions=task_dict["total_positions"],
                max_drawdown=task_dict["max_drawdown"],
                sharpe_ratio=task_dict["sharpe_ratio"],
                annual_return=task_dict["annual_return"],
                win_rate=task_dict["win_rate"],
                final_portfolio_value=task_dict["final_portfolio_value"],
                created_at=created_at_str or "",
                started_at=started_at_str,
                completed_at=completed_at_str,
                error_message=task_dict["error_message"],
            ))

        # 排序
        sortable_fields = {"annual_return", "sharpe_ratio", "max_drawdown", "win_rate", "created_at", "total_pnl"}
        if sort_by in sortable_fields:
            reverse = sort_order != "asc"
            summaries.sort(key=lambda s: getattr(s, sort_by, 0) or 0, reverse=reverse)

        # 分页
        total = len(summaries)
        start = (page - 1) * page_size
        end = start + page_size
        paged_summaries = summaries[start:end]

        return paginated(items=[s.dict() for s in paged_summaries], total=total, page=page, page_size=page_size)

    except Exception as e:
        logger.error(f"Error listing backtests: {str(e)}")
        raise BusinessError(f"Error listing backtests: {str(e)}")


@router.get("/engines")
async def list_backtest_engines(
    is_live: bool = Query(False, description="过滤是否实盘引擎")
):
    """获取可用的回测引擎列表"""
    try:
        engine_service = get_engine_service()
        # is_live=0 表示回测引擎
        result = engine_service.get(is_live=0 if not is_live else 1)

        if not result.is_success():
            return ok(data=[], message="Engines retrieved successfully")

        engines = []
        for engine in (result.data or []):
            engine_dict = engine if isinstance(engine, dict) else {
                "uuid": getattr(engine, 'uuid', ''),
                "name": getattr(engine, 'name', ''),
                "backtest_start_date": getattr(engine, 'backtest_start_date', None),
                "backtest_end_date": getattr(engine, 'backtest_end_date', None),
            }
            engines.append({
                "uuid": engine_dict["uuid"],
                "name": engine_dict["name"],
                "start_date": engine_dict.get("backtest_start_date"),
                "end_date": engine_dict.get("backtest_end_date"),
            })

        return ok(data=engines, message="Engines retrieved successfully")

    except Exception as e:
        logger.error(f"Error listing engines: {str(e)}")
        raise BusinessError(f"Error listing engines: {str(e)}")


@router.get("/analyzers")
async def list_analyzers():
    """
    获取可用的分析器类型列表

    返回系统中所有可用的分析器类型及其参数
    """
    try:
        analyzer_service = container.analyzer_service()
        result = analyzer_service.get_analyzer_types()

        if not result.is_success():
            return ok(data=[])

        return ok(data=result.data or [])

    except Exception as e:
        logger.error(f"Error listing analyzers: {str(e)}")
        # 返回空列表而不是抛出异常
        return ok(data=[], message="Analyzers retrieved successfully")


@router.get("/{uuid}")
async def get_backtest(uuid: str):
    """获取回测任务详情（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]
        elif isinstance(task, list):
            raise NotFoundError("BacktestTask", uuid)

        # 转换为字典
        task_dict = task if isinstance(task, dict) else {
            "uuid": getattr(task, 'uuid', uuid),
            "name": getattr(task, 'name', ''),
            "portfolio_id": getattr(task, 'portfolio_id', ''),
            "status": getattr(task, 'status', 'created'),
            "progress": getattr(task, 'progress', 0) or 0,
            "total_pnl": getattr(task, 'total_pnl', 0.0) or 0.0,
            "total_orders": getattr(task, 'total_orders', 0) or 0,
            "total_signals": getattr(task, 'total_signals', 0) or 0,
            "total_positions": getattr(task, 'total_positions', 0) or 0,
            "total_events": getattr(task, 'total_events', 0) or 0,
            "max_drawdown": getattr(task, 'max_drawdown', 0.0) or 0.0,
            "sharpe_ratio": getattr(task, 'sharpe_ratio', 0.0) or 0.0,
            "annual_return": getattr(task, 'annual_return', 0.0) or 0.0,
            "win_rate": getattr(task, 'win_rate', 0.0) or 0.0,
            "final_portfolio_value": getattr(task, 'final_portfolio_value', 0.0) or 0.0,
            "config_snapshot": getattr(task, 'config_snapshot', '{}'),
            "created_at": getattr(task, 'create_at', None),
            "started_at": getattr(task, 'start_time', None),
            "finished_at": getattr(task, 'end_time', None),
            "error_message": getattr(task, 'error_message', '') or '',
            "backtest_start_date": getattr(task, 'backtest_start_date', None),
            "backtest_end_date": getattr(task, 'backtest_end_date', None),
        }

        # 解析 config JSON
        import json
        config_str = task_dict.get("config_snapshot", "{}")
        if isinstance(config_str, str):
            config = json.loads(config_str)
        else:
            config = config_str or {}

        # 将 datetime 对象转换为字符串
        def format_date(dt):
            if dt is None:
                return None
            if isinstance(dt, str):
                return dt
            return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)

        detail = BacktestTaskDetail(
            uuid=task_dict["uuid"],
            name=task_dict["name"],
            portfolio_id=task_dict["portfolio_id"],
            status=task_dict["status"],
            progress=task_dict["progress"],
            total_pnl=task_dict["total_pnl"],
            total_orders=task_dict["total_orders"],
            total_signals=task_dict["total_signals"],
            total_positions=task_dict["total_positions"],
            total_events=task_dict["total_events"],
            max_drawdown=task_dict["max_drawdown"],
            sharpe_ratio=task_dict["sharpe_ratio"],
            annual_return=task_dict["annual_return"],
            win_rate=task_dict["win_rate"],
            final_portfolio_value=task_dict["final_portfolio_value"],
            backtest_start_date=format_date(task_dict.get("backtest_start_date")),
            backtest_end_date=format_date(task_dict.get("backtest_end_date")),
            engine_uuid=config.get("engine_uuid"),
            created_at=format_date(task_dict.get("created_at")) or "",
            started_at=format_date(task_dict.get("started_at")),
            completed_at=format_date(task_dict.get("finished_at")),
            config=config,
            error_message=task_dict.get("error_message", ""),
        )

        return ok(data=detail.dict(), message="Backtest task retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error getting backtest: {str(e)}")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_backtest(data: BacktestTaskCreate):
    """
    创建回测任务

    流程：
    1. 创建任务记录（写入数据库）
    2. 发送到Kafka（后台任务，不阻塞响应）
    3. 返回任务详情
    """
    try:
        # 1. 创建任务（使用服务层）
        task = create_backtest_task(data)

        # 2. 发送到Kafka（后台任务，不阻塞响应）
        # 使用 asyncio.create_task 让 Kafka 发送在后台运行
        asyncio.create_task(send_task_to_kafka(
            task_uuid=task["uuid"],
            portfolio_uuids=data.portfolio_uuids,
            name=data.name,
            config=task["config"],
        ))

        # 立即返回响应，不等待 Kafka
        return ok(data=task, message="Backtest task created successfully")

    except (NotFoundError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error creating backtest: {str(e)}")
        raise BusinessError(f"Error creating backtest: {str(e)}")


@router.post("/{uuid}/start")
async def start_backtest(uuid: str):
    """启动回测任务（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get_by_id(uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        # 启动任务（使用正确的参数）
        result = task_service.start_task(uuid)

        if not result.is_success():
            raise BusinessError(f"Failed to start task: {result.error}")

        task_id = result.data.get("task_id", uuid) if isinstance(result.data, dict) else uuid
        return ok(data={"uuid": uuid, "task_id": task_id, "state": "PENDING"},
                  message="Backtest task started successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error starting backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error starting backtest: {str(e)}")


@router.post("/{uuid}/stop")
async def stop_backtest(uuid: str):
    """停止回测任务

    状态机规则：只能停止 running 状态的任务
    """
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get_by_id(uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        # 停止任务（service层会处理状态检查和Kafka消息）
        result = task_service.stop_task(uuid)

        if not result.is_success():
            raise BusinessError(f"Failed to stop task: {result.error}")

        return ok(data={"uuid": uuid, "task_id": result.data.get("task_id"), "status": "stopped"},
                  message="Backtest task stopped successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error stopping backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error stopping backtest: {str(e)}")


@router.post("/{uuid}/cancel")
async def cancel_backtest(uuid: str):
    """取消回测任务

    状态机规则：只能取消 created/pending 状态的任务（尚未开始执行的任务）
    """
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get_by_id(uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        # 取消任务（service层会处理状态检查和Kafka消息）
        result = task_service.cancel_task(uuid)

        if not result.is_success():
            raise BusinessError(f"Failed to cancel task: {result.error}")

        return ok(data={"uuid": uuid, "task_id": result.data.get("task_id"), "status": "stopped"},
                  message="Backtest task cancelled successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error cancelling backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error cancelling backtest: {str(e)}")


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(uuid: str):
    """删除回测任务（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get_by_id(uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        # 删除任务
        result = task_service.delete(uuid)

        if not result.is_success():
            raise BusinessError(f"Failed to delete task: {result.error}")

        logger.info(f"Backtest task {uuid} deleted successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error deleting backtest: {str(e)}")


@router.get("/{uuid}/events")
async def backtest_events(uuid: str):
    """
    SSE 端点 - 推送回测进度

    通过Server-Sent Events实时推送回测进度
    """
    from fastapi import Request

    async def event_stream():
        """生成SSE事件流"""
        try:
            while True:
                # 从Redis获取进度
                progress_data = await get_backtest_progress(uuid)

                if not progress_data:
                    # 如果没有进度数据，发送心跳
                    yield "event: keepalive\ndata: {}\n\n"
                    await asyncio.sleep(1)
                    continue

                # 发送进度事件
                import json
                data = json.dumps(progress_data)
                yield f"event: progress\ndata: {data}\n\n"

                # 如果任务完成，结束流
                state = progress_data.get("state", "")
                if state in ["COMPLETED", "FAILED", "CANCELLED"]:
                    break

                await asyncio.sleep(0.5)  # 每0.5秒推送一次

        except Exception as e:
            logger.error(f"Error in event stream for {uuid}: {e}")
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{uuid}/signals")
async def get_backtest_signals(
    uuid: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页数量")
):
    """
    获取回测信号记录（按 task_id 过滤）

    Args:
        uuid: BacktestTask.uuid 或 BacktestTask.task_id
        page: 页码（1-based）
        page_size: 每页数量

    Returns:
        按 task_id 过滤的信号列表
    """
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]

        task_id = getattr(task, 'task_id', uuid)

        # 使用 ResultService 查询信号
        result_service = get_result_service()
        result = result_service.get_signals(task_id=task_id, page=page, page_size=page_size)

        if not result.is_success():
            return paginated(items=[], total=0, page=page, page_size=page_size,
                             message=result.error or "Failed to retrieve signals")

        signals = result.data.get("data", [])
        total = result.data.get("total", 0)

        # 转换信号为字典格式
        signals_data = []
        for s in signals:
            signals_data.append({
                "uuid": getattr(s, 'uuid', ''),
                "portfolio_id": getattr(s, 'portfolio_id', ''),
                "engine_id": getattr(s, 'engine_id', ''),
                "task_id": getattr(s, 'task_id', ''),
                "code": getattr(s, 'code', ''),
                "direction": getattr(s, 'direction', None),
                "reason": getattr(s, 'reason', ''),
                "timestamp": getattr(s, 'timestamp', None),
                "source": getattr(s, 'source', None),
            })

        return paginated(items=signals_data, total=total, page=page, page_size=page_size,
                         message="Signals retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting signals for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting signals: {str(e)}")


@router.get("/{uuid}/orders")
async def get_backtest_orders(uuid: str):
    """
    获取回测订单记录（按 task_id 过滤）

    Args:
        uuid: BacktestTask.uuid 或 BacktestTask.task_id

    Returns:
        按 task_id 过滤的订单列表
    """
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]

        task_id = getattr(task, 'task_id', uuid)

        # 使用 ResultService 查询订单
        result_service = get_result_service()
        result = result_service.get_orders(task_id=task_id)

        if not result.is_success():
            return ok(data={"data": [], "total": 0},
                      message=result.error or "Failed to retrieve orders")

        orders = result.data.get("data", [])
        total = result.data.get("total", 0)

        # 转换订单为字典格式
        orders_data = []
        for o in orders:
            orders_data.append({
                "uuid": getattr(o, 'uuid', ''),
                "portfolio_id": getattr(o, 'portfolio_id', ''),
                "engine_id": getattr(o, 'engine_id', ''),
                "task_id": getattr(o, 'task_id', ''),
                "code": getattr(o, 'code', ''),
                "direction": getattr(o, 'direction', None),
                "order_type": getattr(o, 'order_type', None),
                "status": getattr(o, 'status', None),
                "volume": getattr(o, 'volume', 0),
                "limit_price": str(getattr(o, 'limit_price', 0)),
                "transaction_price": str(getattr(o, 'transaction_price', 0)),
                "transaction_volume": getattr(o, 'transaction_volume', 0),
                "fee": str(getattr(o, 'fee', 0)),
                "timestamp": getattr(o, 'timestamp', None),
            })

        return ok(data={"data": orders_data, "total": total},
                  message="Orders retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting orders for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting orders: {str(e)}")


@router.get("/{uuid}/positions")
async def get_backtest_positions(uuid: str):
    """
    获取回测持仓记录（按 task_id 过滤）

    Args:
        uuid: BacktestTask.uuid 或 BacktestTask.task_id

    Returns:
        按 task_id 过滤的持仓列表
    """
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]

        task_id = getattr(task, 'task_id', uuid)

        # 使用 ResultService 查询持仓
        result_service = get_result_service()
        result = result_service.get_positions(task_id=task_id)

        if not result.is_success():
            return ok(data={"data": [], "total": 0},
                      message=result.error or "Failed to retrieve positions")

        positions = result.data.get("data", [])
        total = result.data.get("total", 0)

        # 转换持仓为字典格式
        positions_data = []
        for p in positions:
            positions_data.append({
                "uuid": getattr(p, 'uuid', ''),
                "portfolio_id": getattr(p, 'portfolio_id', ''),
                "engine_id": getattr(p, 'engine_id', ''),
                "task_id": getattr(p, 'task_id', ''),
                "code": getattr(p, 'code', ''),
                "cost": str(getattr(p, 'cost', 0)),
                "volume": getattr(p, 'volume', 0),
                "frozen_volume": getattr(p, 'frozen_volume', 0),
                "price": str(getattr(p, 'price', 0)),
                "fee": str(getattr(p, 'fee', 0)),
            })

        return ok(data={"data": positions_data, "total": total},
                  message="Positions retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting positions for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting positions: {str(e)}")


@router.get("/{uuid}/netvalue")
async def get_backtest_netvalue(uuid: str):
    """获取回测净值数据"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]

        task_id = getattr(task, 'task_id', uuid)
        portfolio_id = task.portfolio_id

        result_service = get_result_service()
        result = result_service.get_analyzer_values(
            task_id=task_id,
            portfolio_id=portfolio_id,
            analyzer_name="net_value",
        )

        if not result.is_success() or not result.data:
            return ok(data={"strategy": [], "benchmark": []}, message="No net value data")

        records = result.data
        strategy = []
        for r in records:
            ts = r.business_timestamp.isoformat() if r.business_timestamp else (r.timestamp.isoformat() if r.timestamp else "")
            strategy.append({"time": ts, "value": float(r.value) if r.value is not None else None})

        return ok(data={"strategy": strategy, "benchmark": []}, message="Net value retrieved")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting netvalue for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting net value: {str(e)}")


@router.get("/{uuid}/analyzers")
async def get_backtest_analyzers(uuid: str):
    """获取回测任务的分析器列表"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]

        task_id = getattr(task, 'task_id', uuid)
        portfolio_id = task.portfolio_id

        result_service = get_result_service()

        # Get analyzer records for this portfolio filtered by task_id
        analyzer_crud = container.analyzer_record_crud()
        records = analyzer_crud.find_by_portfolio(portfolio_id=portfolio_id, task_id=task_id)

        from collections import OrderedDict
        grouped = OrderedDict()
        for r in records:
            name = getattr(r, 'name', None)
            if name is None:
                continue
            if name not in grouped:
                grouped[name] = []
            val = float(r.value) if r.value is not None else None
            if val is not None:
                grouped[name].append(val)

        analyzers = []
        for name, values in grouped.items():
            # records are desc_order=True, so values[0] is newest
            latest = values[0] if values else None
            count = len(values)
            change = (values[0] - values[-1]) if len(values) > 1 else 0
            analyzers.append({
                "name": name,
                "latest_value": latest,
                "record_count": count,
                "stats": {"count": count, "latest": latest, "change": change}
            })

        return ok(data={"analyzers": analyzers}, message="Analyzers retrieved")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting analyzers for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting analyzers: {str(e)}")


@router.get("/{uuid}/analyzer/{analyzer_name}")
async def get_backtest_analyzer_data(
    uuid: str,
    analyzer_name: str
):
    """
    获取回测分析器数据

    Args:
        uuid: BacktestTask.uuid 或 task_id
        analyzer_name: 分析器名称（如 net_value, drawdown 等）

    Returns:
        分析器时序数据和统计信息
    """
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_by_id(uuid)

        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = result.data
        if isinstance(task, list) and len(task) > 0:
            task = task[0]

        # 使用任务的 task_id（支持历史运行查看）
        task_id = getattr(task, 'task_id', uuid)
        portfolio_id = task.portfolio_id

        # 使用 ResultService 查询分析器记录
        result_service = get_result_service()
        result = result_service.get_analyzer_values(
            task_id=task_id,
            portfolio_id=portfolio_id,
            analyzer_name=analyzer_name,
        )

        if not result.is_success() or not result.data:
            return ok(data={"data": [], "stats": None}, message="No analyzer data found")

        records = result.data

        if not records:
            return ok(data={"data": [], "stats": None}, message="No analyzer data found")

        # 转换为前端格式
        data = []
        values = []
        for r in records:
            data.append({
                "time": r.business_timestamp.isoformat() if r.business_timestamp else r.timestamp.isoformat(),
                "value": float(r.value) if r.value is not None else None
            })
            if r.value is not None:
                values.append(float(r.value))

        # 计算统计信息
        stats = None
        if values:
            stats = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "first": values[0] if values else None,
                "latest": values[-1] if values else None,
                "change": (values[-1] - values[0]) if len(values) > 1 else 0
            }

        return ok(data={"data": data, "stats": stats},
                  message="Analyzer data retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting analyzer data for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting analyzer data: {str(e)}")


@router.get("/{uuid}/logs")
async def get_backtest_logs(
    uuid: str,
    level: Optional[str] = Query(None, description="日志级别: DEBUG/INFO/WARNING/ERROR/CRITICAL"),
    event_type: Optional[str] = Query(None, description="事件类型"),
    start_time: Optional[str] = Query(None, description="开始时间 (YYYY-MM-DD)"),
    end_time: Optional[str] = Query(None, description="结束时间 (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取回测任务的日志"""
    try:
        task_service = get_backtest_task_service()
        task_result = task_service.get_by_id(uuid)
        if not task_result.is_success() or not task_result.data:
            raise NotFoundError("BacktestTask", uuid)

        task = task_result.data
        task_id = getattr(task, 'task_id', None)
        portfolio_id = getattr(task, 'portfolio_id', None)

        from ginkgo.services.logging.containers import LoggingContainer
        logging_container = LoggingContainer()
        log_service = logging_container.log_service()

        kwargs = dict(
            portfolio_id=portfolio_id,
            task_id=task_id,
            level=level,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )

        if start_time:
            kwargs['start_time'] = datetime.strptime(start_time, "%Y-%m-%d")
        if end_time:
            kwargs['end_time'] = datetime.strptime(end_time + " 23:59:59", "%Y-%m-%d %H:%M:%S")

        logs = log_service.query_backtest_logs(**kwargs)
        total = log_service.get_log_count(log_type="backtest", portfolio_id=portfolio_id, task_id=task_id, level=level)

        return ok(data={"logs": logs, "total": total, "limit": limit, "offset": offset},
                  message="Logs retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting logs for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting logs: {str(e)}")
