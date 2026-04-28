"""
Portfolio相关API路由
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from typing import Optional
from core.database import get_db
from core.logging import logger
from core.response import ok
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
    mode: Optional[PortfolioMode] = Query(None, description="按运行模式筛选")
):
    """获取Portfolio列表（使用PortfolioService）"""
    try:
        # 获取PortfolioService
        portfolio_service = get_portfolio_service()

        def _check_frozen(pid):
            try:
                return portfolio_service.is_portfolio_frozen(pid)
            except Exception:
                return False

        # 确定筛选条件
        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        mode_filter = None
        if mode == PortfolioMode.BACKTEST:
            mode_filter = PORTFOLIO_MODE_TYPES.BACKTEST.value
        elif mode == PortfolioMode.LIVE:
            mode_filter = PORTFOLIO_MODE_TYPES.LIVE.value
        elif mode == PortfolioMode.PAPER:
            mode_filter = PORTFOLIO_MODE_TYPES.PAPER.value

        # 获取列表
        result = portfolio_service.get(mode=mode_filter)

        if not result.is_success():
            return ok(data=[], message="Portfolios retrieved successfully")

        portfolios = []
        for p in result.data or []:
            mode_val = "BACKTEST" if p.mode == PORTFOLIO_MODE_TYPES.BACKTEST.value else ("PAPER" if p.mode == PORTFOLIO_MODE_TYPES.PAPER.value else "LIVE")
            portfolios.append({
                "uuid": p.uuid,
                "name": p.name,
                "mode": mode_val,
                "state": "INITIALIZED",
                "config_locked": _check_frozen(p.uuid),
                "net_value": 1.0,
                "created_at": p.create_at.isoformat() if hasattr(p, 'create_at') and p.create_at else None
            })

        return ok(data=portfolios, message="Portfolios retrieved successfully")
    except Exception as e:
        logger.error(f"Error listing portfolios: {str(e)}")
        raise BusinessError(f"Error listing portfolios: {str(e)}")


@router.get("/stats")
async def get_portfolio_stats():
    """获取 Portfolio 统计数据"""
    try:
        # 获取 PortfolioService
        portfolio_service = get_portfolio_service()

        # 使用 count 方法获取总数
        total_result = portfolio_service.count()
        total = total_result.data.get("count", 0) if total_result.is_success() else 0

        # 获取所有数据用于计算资产和净值
        result = portfolio_service.get(page=0, page_size=10000)

        total_assets = 0
        avg_net_value = 1.0
        running = 0

        if result.is_success() and result.data:
            portfolios = result.data
            total_assets = sum(float(p.initial_capital) for p in portfolios if p.initial_capital)

            # 计算平均净值和运行中数量
            net_values = []
            for p in portfolios:
                # 统计运行中的投资组合
                # 注意：旧版MPortfolio使用is_running字段
                is_running = getattr(p, 'is_running', None)

                if is_running == 1:
                    running += 1

                if p.initial_capital and p.cash and float(p.initial_capital) > 0:
                    net_values.append(float(p.cash) / float(p.initial_capital))

            avg_net_value = sum(net_values) / len(net_values) if net_values else 1.0

        return ok(data={
            "total": total,
            "running": running,
            "avg_net_value": round(avg_net_value, 4),
            "total_assets": total_assets,
        }, message="Stats retrieved successfully")

    except Exception as e:
        logger.error(f"Error getting portfolio stats: {str(e)}")
        # 发生错误时返回默认值
        return ok(data={
            "total": 0,
            "running": 0,
            "avg_net_value": 1.0,
            "total_assets": 0,
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
            "state": "INITIALIZED",
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

        # 准备组件数据
        sizer_data = None
        if data.sizer_uuid:
            sizer_data = {'component_uuid': data.sizer_uuid, 'config': data.sizer_config or {}}

        # 创建 Saga 事务
        saga = PortfolioSagaFactory.create_portfolio_saga(
            name=data.name,
            mode=0,  # BACKTEST 模式
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

        # 验证存在
        portfolios = portfolio_service._crud_repo.find(filters={"uuid": uuid})
        if not portfolios:
            raise NotFoundError("Portfolio", uuid)

        portfolio = portfolios[0]
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
