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
from ginkgo.data.services.backtest_task_schemas import (
    BacktestTaskSummary, BacktestTaskDetail, BacktestTaskCreate,
    AnalyzerConfig, EngineConfig, ComponentConfig,
)

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


# ==================== 仅 API 层使用的模型 ====================

class AnalyzerTypeInfo(BaseModel):
    """分析器类型信息"""
    name: str
    type: str
    description: str = ""
    parameters: Dict[str, Any] = {}


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
    """获取回测任务列表"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.list_summaries(
            page=page - 1,
            page_size=page_size,
            portfolio_id=portfolio_id,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        if not result.is_success():
            return paginated(items=[], total=0, page=page, page_size=page_size)

        summaries = result.data
        total = result.metadata.get("total", 0)
        return paginated(items=[s.dict() for s in summaries], total=total, page=page, page_size=page_size)

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

    返回系统中所有可用的分析器类型及其参数。
    优先从 service 获取，失败时使用内置回退列表。
    """
    try:
        # 从 AnalyzerRegistry 直接获取已注册的分析器
        from ginkgo.trading.analysis.analyzers.registry import AnalyzerRegistry
        registry = AnalyzerRegistry()
        count = registry.scan_builtin()
        if count > 0:
            analyzers = []
            for name in registry.all_analyzers:
                analyzers.append({"name": name, "type": name, "description": name})
            return ok(data=analyzers)
    except Exception as e:
        logger.error(f"Error scanning analyzer registry: {str(e)}")

    # Registry 扫描失败时的回退列表（名称与实际 __init__ default name 一致）
    _FALLBACK_ANALYZERS = [
        {"name": "annualized_return", "type": "annualized_return", "description": "年化收益率"},
        {"name": "sharpe_ratio", "type": "sharpe_ratio", "description": "夏普比率"},
        {"name": "max_drawdown", "type": "max_drawdown", "description": "最大回撤"},
        {"name": "order_count", "type": "order_count", "description": "订单统计"},
        {"name": "volatility", "type": "volatility", "description": "波动率"},
        {"name": "profit_factor", "type": "profit_factor", "description": "盈亏比"},
        {"name": "win_rate", "type": "win_rate", "description": "胜率"},
    ]
    return ok(data=_FALLBACK_ANALYZERS, message="Analyzers retrieved from fallback catalog")


@router.get("/{uuid}")
async def get_backtest(uuid: str):
    """获取回测任务详情"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_detail(uuid)

        if not result.is_success():
            raise NotFoundError("BacktestTask", uuid)

        return ok(data=result.data.dict(), message="Backtest task retrieved successfully")

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

        task = result.data

        # 启动任务（service 层 start_task 内部已发送 Kafka 消息，无需重复发送）
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
        import json as _json

        # 连续无数据的最大次数，超过则判定任务不存在/超时
        max_empty_iterations = 3
        empty_count = 0

        try:
            while True:
                # 从Redis获取进度
                progress_data = await get_backtest_progress(uuid)

                if not progress_data:
                    empty_count += 1
                    if empty_count >= max_empty_iterations:
                        # 连续多次无数据，判定为任务不存在或超时
                        yield f"event: timeout\ndata: {_json.dumps({'reason': 'no_progress_data'})}\n\n"
                        break
                    # 发送心跳
                    yield "event: keepalive\ndata: {}\n\n"
                    await asyncio.sleep(1)
                    continue

                # 有数据时重置计数器
                empty_count = 0

                # 发送进度事件
                data = _json.dumps(progress_data)
                yield f"event: progress\ndata: {data}\n\n"

                # 如果任务完成，结束流
                state = progress_data.get("state", "")
                if state in ["COMPLETED", "FAILED", "CANCELLED"]:
                    break

                await asyncio.sleep(0.5)  # 每0.5秒推送一次

        except Exception as e:
            logger.error(f"Error in event stream for {uuid}: {e}")
            error_data = _json.dumps({"error": str(e)})
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
    """获取回测信号记录"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.list_signals(uuid, page=page, page_size=page_size)

        if not result.is_success():
            return paginated(items=[], total=0, page=page, page_size=page_size,
                             message=result.error or "Failed to retrieve signals")

        items = result.data
        total = result.metadata.get("total", 0)
        return paginated(items=[s.dict() for s in items], total=total, page=page, page_size=page_size,
                         message="Signals retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting signals for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting signals: {str(e)}")


@router.get("/{uuid}/orders")
async def get_backtest_orders(uuid: str):
    """获取回测订单记录"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.list_orders(uuid)

        if not result.is_success():
            return paginated(items=[], total=0,
                             message=result.error or "Failed to retrieve orders")

        items = result.data
        total = result.metadata.get("total", 0)
        return paginated(items=[o.dict() for o in items], total=total,
                         page=1, page_size=max(total, 1),
                         message="Orders retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting orders for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting orders: {str(e)}")


@router.get("/{uuid}/positions")
async def get_backtest_positions(uuid: str):
    """获取回测持仓记录"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.list_positions(uuid)

        if not result.is_success():
            return paginated(items=[], total=0,
                             message=result.error or "Failed to retrieve positions")

        items = result.data
        total = result.metadata.get("total", 0)
        return paginated(items=[p.dict() for p in items], total=total,
                         page=1, page_size=max(total, 1),
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
        result = task_service.get_netvalue(uuid)

        if not result.is_success():
            return ok(data={"strategy": [], "benchmark": []}, message="No net value data")

        nv = result.data
        return ok(data={"strategy": [p.dict() for p in nv.strategy], "benchmark": []},
                  message="Net value retrieved")

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
        result = task_service.list_analyzer_groups(uuid)

        if not result.is_success():
            raise NotFoundError("BacktestTask", uuid)

        groups = result.data
        return ok(data={"analyzers": [g.dict() for g in groups]}, message="Analyzers retrieved")

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
    """获取回测分析器时序数据和统计信息"""
    try:
        task_service = get_backtest_task_service()
        result = task_service.get_analyzer_data(uuid, analyzer_name)

        if not result.is_success():
            return ok(data={"data": [], "stats": None}, message="No analyzer data found")

        detail = result.data
        return ok(data={"data": [p.dict() for p in detail.data], "stats": detail.stats},
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
            task_id=task_id,
            portfolio_id=portfolio_id,
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
        total = log_service.get_log_count(log_type="backtest", task_id=task_id, level=level)

        return ok(data={"logs": logs, "total": total, "limit": limit, "offset": offset},
                  message="Logs retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting logs for {uuid}: {str(e)}")
        raise BusinessError(f"Error getting logs: {str(e)}")
