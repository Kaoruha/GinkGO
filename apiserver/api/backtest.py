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
from core.response import APIResponse, PaginatedResponse, paginated_response
from core.exceptions import NotFoundError, ValidationError, BusinessError
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.data.containers import container

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
        portfolio_uuid=primary_portfolio_uuid,
        portfolio_name=portfolio_name,
        config=config,
    )

    if not result.is_success():
        raise BusinessError(f"Failed to create backtest task: {result.error}")

    task_info = result.data.get("task_info", {})

    return {
        "uuid": task_info.get("uuid", str(uuid.uuid4())),
        "name": data.name,
        "portfolio_uuid": primary_portfolio_uuid,
        "portfolio_uuids": data.portfolio_uuids,
        "portfolio_name": portfolio_name,
        "state": "PENDING",
        "progress": 0.0,
        "engine_uuid": config.get("engine_uuid"),
        "config": config,
        "created_at": task_info.get("created_at", datetime.utcnow().isoformat() + "Z"),
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

    logger.info(f"Cancel command sent for task {task_uuid}")


# ==================== API 路由 ====================

@router.get("/", response_model=PaginatedResponse[BacktestTaskSummary])
async def list_backtests(
    state: Optional[str] = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """获取回测任务列表（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 使用服务层获取任务
        result = task_service.get(state=state) if state else task_service.get()

        if not result.is_success():
            return paginated_response([], page, page_size, 0)

        tasks = result.data or []

        # 转换为 API 模型
        summaries = []
        for task in tasks:
            task_dict = task if isinstance(task, dict) else {
                "uuid": getattr(task, 'uuid', ''),
                "name": getattr(task, 'name', ''),
                "portfolio_name": getattr(task, 'portfolio_name', ''),
                "state": getattr(task, 'state', 'PENDING'),
                "progress": getattr(task, 'progress', 0.0),
                "created_at": getattr(task, 'created_at', None),
                "started_at": getattr(task, 'started_at', None),
                "finished_at": getattr(task, 'finished_at', None),
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
                portfolio_name=task_dict["portfolio_name"],
                state=task_dict["state"],
                progress=task_dict["progress"],
                created_at=created_at_str or "",
                started_at=started_at_str,
                completed_at=completed_at_str,
            ))

        # 分页
        total = len(summaries)
        start = (page - 1) * page_size
        end = start + page_size
        paged_summaries = summaries[start:end]

        return paginated_response(paged_summaries, page, page_size, total)

    except Exception as e:
        logger.error(f"Error listing backtests: {str(e)}")
        raise BusinessError(f"Error listing backtests: {str(e)}")


@router.get("/engines", response_model=APIResponse[List[dict]])
async def list_backtest_engines(
    is_live: bool = Query(False, description="过滤是否实盘引擎")
):
    """获取可用的回测引擎列表"""
    try:
        engine_service = get_engine_service()
        # is_live=0 表示回测引擎
        result = engine_service.get(is_live=0 if not is_live else 1)

        if not result.is_success():
            return {
                "success": True,
                "data": [],
                "error": None,
                "message": "Engines retrieved successfully"
            }

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

        return {
            "success": True,
            "data": engines,
            "error": None,
            "message": "Engines retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error listing engines: {str(e)}")
        raise BusinessError(f"Error listing engines: {str(e)}")


@router.get("/analyzers", response_model=APIResponse[List[AnalyzerTypeInfo]])
async def list_analyzers():
    """
    获取可用的分析器类型列表

    返回系统中所有可用的分析器类型及其参数
    """
    try:
        from core.response import success_response
        analyzer_service = container.analyzer_service()
        result = analyzer_service.get_analyzer_types()

        if not result.is_success():
            return success_response([])

        return success_response(result.data or [])

    except Exception as e:
        logger.error(f"Error listing analyzers: {str(e)}")
        # 返回空列表而不是抛出异常
        return {"success": True, "data": [], "error": None, "message": "Analyzers retrieved successfully"}


@router.get("/{uuid}", response_model=APIResponse[BacktestTaskDetail])
async def get_backtest(uuid: str):
    """获取回测任务详情（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get(uuid=uuid)

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
            "portfolio_uuid": getattr(task, 'portfolio_uuid', ''),
            "portfolio_name": getattr(task, 'portfolio_name', ''),
            "state": getattr(task, 'state', 'PENDING'),
            "progress": getattr(task, 'progress', 0.0),
            "config": getattr(task, 'config', '{}'),
            "created_at": getattr(task, 'created_at', None),
            "started_at": getattr(task, 'started_at', None),
            "finished_at": getattr(task, 'finished_at', None),
            "worker_id": getattr(task, 'worker_id', None),
            "error": getattr(task, 'error_message', None),
        }

        # 解析 config JSON
        import json
        config_str = task_dict.get("config", "{}")
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
            portfolio_name=task_dict["portfolio_name"],
            portfolio_uuid=task_dict["portfolio_uuid"],
            state=task_dict["state"],
            progress=task_dict["progress"],
            engine_uuid=config.get("engine_uuid"),
            created_at=format_date(task_dict.get("created_at")) or "",
            started_at=format_date(task_dict.get("started_at")),
            completed_at=format_date(task_dict.get("finished_at")),
            config=config,
            result=None,  # 结果需要从 Redis 获取
            worker_id=task_dict.get("worker_id"),
            error=task_dict.get("error"),
        )

        return {
            "success": True,
            "data": detail.dict(),
            "error": None,
            "message": "Backtest task retrieved successfully"
        }

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error getting backtest: {str(e)}")


@router.post("/", response_model=APIResponse[BacktestTaskDetail], status_code=status.HTTP_201_CREATED)
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
        return {
            "success": True,
            "data": task,
            "error": None,
            "message": "Backtest task created successfully"
        }

    except (NotFoundError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error creating backtest: {str(e)}")
        raise BusinessError(f"Error creating backtest: {str(e)}")


@router.post("/{uuid}/start", response_model=APIResponse[dict])
async def start_backtest(uuid: str):
    """启动回测任务（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get(uuid=uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        # 启动任务
        result = task_service.start_task(uuid, worker_id="api")

        if not result.is_success():
            raise BusinessError(f"Failed to start task: {result.error}")

        return {
            "success": True,
            "data": {"uuid": uuid, "state": "RUNNING"},
            "error": None,
            "message": "Backtest task started successfully"
        }

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error starting backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error starting backtest: {str(e)}")


@router.post("/{uuid}/stop", response_model=APIResponse[dict])
async def stop_backtest(uuid: str):
    """停止回测任务（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get(uuid=uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("BacktestTask", uuid)

        # 取消任务
        result = task_service.cancel_task(uuid)

        if not result.is_success():
            raise BusinessError(f"Failed to stop task: {result.error}")

        # 发送取消命令到Kafka（后台任务，不阻塞响应）
        asyncio.create_task(send_cancel_to_kafka(uuid))

        return {
            "success": True,
            "data": {"uuid": uuid, "state": "CANCELLED"},
            "error": None,
            "message": "Backtest task stopped successfully"
        }

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error stopping backtest {uuid}: {str(e)}")
        raise BusinessError(f"Error stopping backtest: {str(e)}")


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backtest(uuid: str):
    """删除回测任务（使用 service 层）"""
    try:
        task_service = get_backtest_task_service()

        # 检查任务是否存在
        result = task_service.get(uuid=uuid)
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
