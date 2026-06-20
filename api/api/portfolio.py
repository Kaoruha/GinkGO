"""
Portfolio相关API路由
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from typing import Optional
from core.logging import logger
from core.response import ok, pagination_meta
from core.exceptions import NotFoundError, ValidationError, BusinessError
from datetime import datetime
import sys
from pathlib import Path

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

from models.portfolio import (
    PortfolioSummary,
    PortfolioDetail,
    PortfolioCreate,
    PortfolioMode,
    PortfolioState
)

router = APIRouter()


def get_portfolio_service():
    """获取PortfolioService实例"""
    from ginkgo.data.containers import container
    return container.portfolio_service()


_RUNSTATE_MAP = {
    -1: "VOID", 0: "INITIALIZED", 1: "RUNNING", 2: "PAUSED",
    3: "STOPPING", 4: "STOPPED", 5: "RELOADING", 6: "MIGRATING", 7: "OFFLINE",
}


def _map_state(state_value) -> str:
    if isinstance(state_value, int):
        return _RUNSTATE_MAP.get(state_value, "INITIALIZED")
    if hasattr(state_value, "value"):
        return _RUNSTATE_MAP.get(state_value.value, "INITIALIZED")
    return str(state_value)


def _map_mode(mode_value) -> str:
    """将 mode 数值映射为字符串"""
    from ginkgo.enums import PORTFOLIO_MODE_TYPES
    if isinstance(mode_value, int):
        if mode_value == PORTFOLIO_MODE_TYPES.BACKTEST.value:
            return "BACKTEST"
        elif mode_value == PORTFOLIO_MODE_TYPES.PAPER.value:
            return "PAPER"
        else:
            return "LIVE"
    return str(mode_value)


def _get_backtest_task_service():
    """获取BacktestTaskService实例"""
    from ginkgo.data.containers import container
    return container.backtest_task_service()


def _get_deployment_service():
    """获取DeploymentService实例"""
    from ginkgo.trading.containers import trading_container
    return trading_container.deployment_service()


def _get_latest_backtest_metrics(portfolio_id: str) -> dict:
    """获取 portfolio 最新已完成回测的绩效指标"""
    try:
        result = _get_backtest_task_service().get_latest_completed(portfolio_id=portfolio_id)
        if result.is_success():
            return result.data
    except Exception:
        pass
    return {}


def _count_backtests(portfolio_id: str) -> int:
    """统计 portfolio 的回测次数"""
    try:
        result = _get_backtest_task_service().count_by_portfolio(portfolio_id=portfolio_id)
        if result.is_success():
            return result.data
    except Exception:
        pass
    return 0


def _get_related_portfolios(portfolio_id: str, mode_int: int) -> list:
    """获取关联组合摘要"""
    try:
        deployment_svc = _get_deployment_service()
        related = []

        if mode_int == 0:  # BACKTEST: find deployed PAPER/LIVE
            dep_result = deployment_svc.find_by_source_portfolio(source_portfolio_id=portfolio_id)
            deployments = dep_result.data if dep_result.is_success() else []
            if deployments:
                portfolio_svc = get_portfolio_service()
                for dep in deployments:
                    target_list = portfolio_svc.get(portfolio_id=dep.target_portfolio_id)
                    if target_list and target_list.data:
                        t = target_list.data[0]
                        mode_str = "PAPER" if t.mode == 1 else "LIVE"
                        metrics = {
                            "annual_return": float(getattr(t, "annual_return", 0) or 0),
                            "max_drawdown": float(getattr(t, "max_drawdown", 0) or 0),
                        }
                        related.append({
                            "uuid": t.uuid,
                            "name": t.name,
                            "mode": mode_str,
                            "state": _map_state(t.state),
                            **metrics,
                        })
        else:  # PAPER/LIVE: find source BACKTEST
            dep_result = deployment_svc.find_by_target_portfolio(target_portfolio_id=portfolio_id)
            deployments = dep_result.data if dep_result.is_success() else []
            if deployments:
                portfolio_svc = get_portfolio_service()
                source_id = deployments[0].source_portfolio_id
                source_list = portfolio_svc.get(portfolio_id=source_id)
                if source_list and source_list.data:
                    s = source_list.data[0]
                    bt_metrics = _get_latest_backtest_metrics(source_id)
                    related.append({
                        "uuid": s.uuid,
                        "name": s.name,
                        "mode": "BACKTEST",
                        "state": _map_state(s.state),
                        "relation": "source",
                        **bt_metrics,
                    })
                # Other deployments from same source
                for dep in deployments:
                    if dep.target_portfolio_id != portfolio_id:
                        other_list = portfolio_svc.get(portfolio_id=dep.target_portfolio_id)
                        if other_list and other_list.data:
                            o = other_list.data[0]
                            related.append({
                                "uuid": o.uuid,
                                "name": o.name,
                                "mode": "PAPER" if o.mode == 1 else "LIVE",
                                "state": _map_state(o.state),
                                "annual_return": float(getattr(o, "annual_return", 0) or 0),
                                "max_drawdown": float(getattr(o, "max_drawdown", 0) or 0),
                            })
        return related
    except Exception:
        return []


def get_file_service():
    """获取FileService实例"""
    from ginkgo.data.containers import container
    return container.file_service()


def get_mapping_service():
    """获取PortfolioMappingService实例"""
    from ginkgo.data.containers import container
    return container.portfolio_mapping_service()

def get_param_names(component_name: str, file_type: str = None):
    """获取组件参数名映射"""
    from ginkgo.data.services.component_parameter_extractor import get_component_parameter_names
    return get_component_parameter_names(component_name, None, file_type, None)


@router.get("/")
async def list_portfolios(
    mode: Optional[PortfolioMode] = Query(None, description="按运行模式筛选"),
    page: int = Query(0, ge=0, description="页码（0-based）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="按名称搜索"),
):
    """获取Portfolio列表（分页）"""
    try:
        portfolio_service = get_portfolio_service()

        # 确定筛选条件
        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        filters = {"is_del": False}
        if mode == PortfolioMode.BACKTEST:
            filters["mode"] = PORTFOLIO_MODE_TYPES.BACKTEST.value
        elif mode == PortfolioMode.LIVE:
            filters["mode"] = PORTFOLIO_MODE_TYPES.LIVE.value
        elif mode == PortfolioMode.PAPER:
            filters["mode"] = PORTFOLIO_MODE_TYPES.PAPER.value
        if keyword:
            filters["name"] = keyword

        # fix(#4582): 通过 Service 方法分页查询，不再直调 _crud_repo
        result = portfolio_service.list_paginated(
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="update_at",
            desc_order=True,
        )
        if not result.success:
            raise BusinessError(result.error or "查询投资组合失败")
        portfolios = result.data["items"]
        total = result.data["total"]

        items = []
        for p in (portfolios or []):
            mode_int = p.mode

            # Performance metrics
            if mode_int == PORTFOLIO_MODE_TYPES.BACKTEST.value:
                metrics = _get_latest_backtest_metrics(p.uuid)
                backtest_count = _count_backtests(p.uuid)
            else:
                metrics = {
                    "annual_return": float(getattr(p, "annual_return", 0) or 0),
                    "sharpe_ratio": float(getattr(p, "sharpe_ratio", 0) or 0),
                    "max_drawdown": float(getattr(p, "max_drawdown", 0) or 0),
                    "win_rate": float(getattr(p, "win_rate", 0) or 0),
                }
                backtest_count = 0

            items.append({
                "uuid": p.uuid,
                "name": p.name,
                "mode": _map_mode(p.mode),
                "state": _map_state(p.state),
                "config_locked": portfolio_service.is_portfolio_frozen(p.uuid),
                "annual_return": metrics.get("annual_return"),
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "max_drawdown": metrics.get("max_drawdown"),
                "win_rate": metrics.get("win_rate"),
                "backtest_count": backtest_count,
                "last_backtest_date": metrics.get("last_backtest_date"),
                "related": _get_related_portfolios(p.uuid, mode_int),
                "created_at": p.create_at.isoformat() if hasattr(p, 'create_at') and p.create_at else None,
            })

        return ok(data=items, message="Portfolios retrieved successfully", meta=pagination_meta(page + 1, total, page_size))
    except Exception as e:
        logger.error(f"Error listing portfolios: {str(e)}")
        raise BusinessError(f"Error listing portfolios: {str(e)}")


@router.get("/stats")
async def get_portfolio_stats():
    """获取 Portfolio 统计数据"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.get_stats()
        data = result.data if result.is_success() else {
            "total": 0, "running": 0, "avg_net_value": 1.0, "total_assets": 0,
        }
        return ok(data=data, message="Stats retrieved successfully")
    except Exception as e:
        logger.error(f"Error getting portfolio stats: {e}")
        return ok(data={
            "total": 0, "running": 0, "avg_net_value": 1.0, "total_assets": 0,
        }, message="Stats retrieved successfully")


@router.get("/{uuid}")
async def get_portfolio(uuid: str):
    """获取Portfolio详情（包含组件配置和参数）"""
    try:
        # 获取服务
        portfolio_service = get_portfolio_service()
        mapping_service = get_mapping_service()
        file_service = get_file_service()

        # 获取Portfolio基本信息
        portfolio_result = portfolio_service.get(portfolio_id=uuid)
        if not portfolio_result.is_success():
            raise NotFoundError("Portfolio", uuid)

        portfolio_model = portfolio_result.data
        if isinstance(portfolio_model, list):
            portfolio_model = portfolio_model[0] if portfolio_model else None

        if portfolio_model is None:
            raise NotFoundError("Portfolio", uuid)

        # 获取组件映射和参数
        mappings_result = mapping_service.get_portfolio_mappings(uuid, include_params=True)

        strategies = []
        selectors = []
        sizers = []
        risk_managers = []
        analyzers = []

        if mappings_result.is_success():
            from ginkgo.enums import FILE_TYPES

            for m in mappings_result.data:
                # 获取文件信息
                file_result = file_service.get_by_uuid(m['file_id'])
                file_obj = None
                if file_result.is_success() and file_result.data:
                    file_obj = file_result.data.get("file") if isinstance(file_result.data, dict) else file_result.data

                file_type = m.get('type')
                component_info = {
                    "uuid": m['file_id'],
                    "name": file_obj.name if file_obj else m.get('name', ''),
                    "type": m.get('type'),
                }

                # 添加参数
                params = m.get('params', {})
                if params:
                    component_name = file_obj.name if file_obj else ""
                    file_type_str = None
                    if file_type is not None:
                        file_type_val = int(file_type)
                        type_map = {
                            FILE_TYPES.STRATEGY.value: "strategy",
                            FILE_TYPES.SELECTOR.value: "selector",
                            FILE_TYPES.SIZER.value: "sizer",
                            FILE_TYPES.RISKMANAGER.value: "risk_manager",
                            FILE_TYPES.ANALYZER.value: "analyzer",
                        }
                        file_type_str = type_map.get(file_type_val)
                    param_names = get_param_names(component_name, file_type_str)

                    config = {}
                    for key, value in params.items():
                        if key.startswith('param_'):
                            idx = int(key.split('_')[1])
                            if idx in param_names:
                                param_name = param_names[idx]
                                config[param_name] = value
                    component_info['config'] = config

                # 根据类型分组
                file_type_val = int(file_type) if file_type is not None else -1
                if file_type_val == FILE_TYPES.SELECTOR.value:
                    selectors.append(component_info)
                elif file_type_val == FILE_TYPES.SIZER.value:
                    sizers.append(component_info)
                elif file_type_val == FILE_TYPES.STRATEGY.value:
                    strategies.append(component_info)
                elif file_type_val == FILE_TYPES.RISKMANAGER.value:
                    risk_managers.append(component_info)
                elif file_type_val == FILE_TYPES.ANALYZER.value:
                    analyzers.append(component_info)

        from datetime import datetime
        create_at_value = portfolio_model.create_at if hasattr(portfolio_model, 'create_at') and portfolio_model.create_at else None

        data = {
            "uuid": uuid,
            "name": portfolio_model.name,
            "mode": "BACKTEST" if portfolio_model.mode == 0 else ("PAPER" if portfolio_model.mode == 1 else "LIVE"),
            "state": _map_state(portfolio_model.state),
            "config_locked": portfolio_service.is_portfolio_frozen(uuid),
            "net_value": 1.0,
            "created_at": create_at_value.isoformat() if isinstance(create_at_value, datetime) else create_at_value,
            "initial_cash": float(portfolio_model.initial_capital) if hasattr(portfolio_model, 'initial_capital') else 100000.0,
            "current_cash": float(portfolio_model.cash) if hasattr(portfolio_model, 'cash') else 100000.0,
            "positions": [],
            "strategies": strategies,
            "selectors": selectors,
            "sizers": sizers,
            "risk_managers": risk_managers,
            "analyzers": analyzers,
            "risk_alerts": []
        }

        return ok(data=data, message="Portfolio retrieved successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error getting portfolio: {str(e)}")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_portfolio(data: PortfolioCreate):
    """创建Portfolio（使用Saga事务保证一致性）

    通过Saga模式确保Portfolio创建的事务一致性：
    - 创建Portfolio实体
    - 添加Selector组件
    - 添加Sizer组件
    - 添加Strategy组件
    - 添加RiskManager组件
    - 添加Analyzer组件

    任何步骤失败都会自动回滚已完成的操作。
    """
    try:
        from services.saga_transaction import PortfolioSagaFactory
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        # 准备组件数据
        sizer_data = None
        if data.sizer_uuid:
            sizer_data = {'component_uuid': data.sizer_uuid, 'config': data.sizer_config or {}}

        # #5622 #5859: 使用请求体的 mode（映射为 core 枚举 int），而非硬编码 BACKTEST(0)
        mode_int = PORTFOLIO_MODE_TYPES[data.mode.value].value

        # 创建 Saga 事务
        saga = PortfolioSagaFactory.create_portfolio_saga(
            name=data.name,
            mode=mode_int,
            selectors=data.selectors,
            sizer=sizer_data,
            strategies=data.strategies,
            risk_managers=data.risk_managers or [],
            analyzers=data.analyzers or []
        )

        # 执行 Saga 事务
        success = await saga.execute()

        if not success:
            logger.error(f"Failed to create portfolio: {saga.error}")
            raise BusinessError(
                f"Failed to create portfolio: {str(saga.error)}. "
                "Transaction has been rolled back."
            )

        # 获取创建后的完整数据
        # saga.steps[0].result 可能是 dict 或对象
        step_result = saga.steps[0].result
        if isinstance(step_result, dict):
            portfolio_uuid = step_result.get('uuid')
        else:
            portfolio_uuid = getattr(step_result, 'uuid', None)

        if not portfolio_uuid:
            raise BusinessError("Failed to get portfolio UUID after creation")

        response = await get_portfolio(portfolio_uuid)
        return response

    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio: {str(e)}")
        raise BusinessError(f"Error creating portfolio: {str(e)}")


@router.put("/{uuid}")
async def update_portfolio(uuid: str, data: dict):
    """更新Portfolio及其组件配置（使用Saga事务保证一致性）

    通过Saga模式确保Portfolio更新的事务一致性：
    - 备份当前状态
    - 更新基本信息（名称、初始资金）
    - 删除旧组件映射
    - 添加新组件映射

    任何步骤失败都会自动回滚到更新前的状态。
    """
    try:
        from services.saga_transaction import PortfolioSagaFactory

        # 准备更新参数
        sizer_data = None
        if data.get('sizer_uuid'):
            sizer_data = {'component_uuid': data['sizer_uuid'], 'config': data.get('sizer_config') or {}}

        # 创建 Saga 事务
        saga = PortfolioSagaFactory.update_portfolio_saga(
            portfolio_uuid=uuid,
            name=data.get('name'),
            initial_cash=data.get('initial_cash'),
            selectors=data.get('selectors'),
            sizer=sizer_data,
            strategies=data.get('strategies'),
            risk_managers=data.get('risk_managers'),
            analyzers=data.get('analyzers')
        )

        # 执行 Saga 事务
        success = await saga.execute()

        if not success:
            logger.error(f"Failed to update portfolio: {saga.error}")
            raise BusinessError(
                f"Failed to update portfolio: {str(saga.error)}. "
                "Transaction has been rolled back."
            )

        # 返回更新后的数据
        response = await get_portfolio(uuid)
        return response

    except (NotFoundError, BusinessError):
        raise
    except Exception as e:
        logger.error(f"Error updating portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error updating portfolio: {str(e)}")


@router.post("/{uuid}/start")
async def start_portfolio(uuid: str):
    """启动 PAPER/LIVE Portfolio（发送 Kafka deploy 命令）"""
    try:
        from ginkgo.messages.control_command import ControlCommand
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.kafka_topics import KafkaTopics
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        portfolio_service = get_portfolio_service()

        # 验证存在并获取 mode
        result = portfolio_service.get(portfolio_id=uuid)
        if not result.is_success() or not result.data:
            raise NotFoundError("Portfolio", uuid)

        portfolio_list = result.data
        portfolio = portfolio_list[0] if portfolio_list else None
        if not portfolio:
            raise NotFoundError("Portfolio", uuid)

        mode = getattr(portfolio, 'mode', -1)
        if mode == PORTFOLIO_MODE_TYPES.BACKTEST.value:
            raise BusinessError("回测模式组合不支持 start，请使用新建回测")

        cmd = ControlCommand.deploy(uuid)
        producer = GinkgoProducer()
        success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())

        if not success:
            raise BusinessError("Failed to send deploy command via Kafka")

        logger.info(f"Start command sent for portfolio {uuid}")

        return ok(data={"success": True}, message="Start command sent")

    except NotFoundError:
        raise
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error starting portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error starting portfolio: {str(e)}")


@router.post("/{uuid}/stop")
async def stop_portfolio(uuid: str):
    """停止 PAPER/LIVE Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.stop(portfolio_id=uuid)

        if not result.is_success():
            raise BusinessError(result.error)

        logger.info(f"Stop command sent for portfolio {uuid}")

        return ok(data=result.data, message=result.message or "Stop command sent")

    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error stopping portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error stopping portfolio: {str(e)}")


@router.get("/{uuid}/analytics")
async def get_portfolio_analytics(uuid: str):
    """获取组合绩效指标 + 净值曲线数据"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.get_analytics(uuid)

        if not result.is_success():
            raise BusinessError(result.error or "获取绩效数据失败")

        return ok(data=result.data, message=result.message or "Analytics retrieved")
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics for portfolio {uuid}: {e}")
        raise BusinessError(f"Error getting analytics: {e}")


@router.get("/{uuid}/events")
async def get_portfolio_events(
    uuid: str,
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取统一事件时间线（信号/订单/成交/拒绝/风控）"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.list_events(uuid, limit=limit, offset=offset)

        if not result.is_success():
            raise BusinessError(result.error or "获取事件列表失败")

        data = result.data
        meta = pagination_meta(
            page=(offset // limit) + 1,
            total=data.get("total", 0),
            page_size=limit,
        )
        return ok(data=data.get("data", []), message="Events retrieved", meta=meta)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error getting events for portfolio {uuid}: {e}")
        raise BusinessError(f"Error getting events: {e}")


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(uuid: str):
    """删除Portfolio（通过 service 层）"""
    try:
        # 获取 PortfolioService
        portfolio_service = get_portfolio_service()

        # 调用 service 的 delete 方法
        result = portfolio_service.delete(portfolio_id=uuid)

        if not result.is_success():
            raise NotFoundError("Portfolio", uuid)

        logger.info(f"Portfolio {uuid} deleted successfully")

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error deleting portfolio: {str(e)}")
