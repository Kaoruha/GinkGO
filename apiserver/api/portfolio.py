"""
Portfolio相关API路由
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from typing import Optional
from core.database import get_db
from core.logging import logger
from core.response import APIResponse, success_response
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

def get_param_service():
    """获取ParameterMetadataService实例"""
    from ginkgo.data.containers import container
    return container.parameter_metadata_service()


@router.get("/", response_model=APIResponse[list[PortfolioSummary]])
async def list_portfolios(
    mode: Optional[PortfolioMode] = Query(None, description="按运行模式筛选")
):
    """获取Portfolio列表（使用PortfolioService）"""
    try:
        # 获取PortfolioService
        portfolio_service = get_portfolio_service()

        # 确定筛选条件
        is_live_filter = None
        if mode == PortfolioMode.BACKTEST:
            is_live_filter = False
        elif mode == PortfolioMode.LIVE:
            is_live_filter = True
        elif mode == PortfolioMode.PAPER:
            is_live_filter = True

        # 获取列表
        result = portfolio_service.get(is_live=is_live_filter)

        if not result.is_success():
            return {
                "success": True,
                "data": [],
                "error": None,
                "message": "Portfolios retrieved successfully"
            }

        portfolios = []
        for p in result.data or []:
            mode_val = "BACKTEST" if p.is_live == 0 else "LIVE"
            portfolios.append({
                "uuid": p.uuid,
                "name": p.name,
                "mode": mode_val,
                "state": "INITIALIZED",
                "config_locked": False,
                "net_value": 1.0,
                "created_at": p.create_at.isoformat() if hasattr(p, 'create_at') and p.create_at else None
            })

        return {
            "success": True,
            "data": portfolios,
            "error": None,
            "message": "Portfolios retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error listing portfolios: {str(e)}")
        raise BusinessError(f"Error listing portfolios: {str(e)}")


@router.get("/{uuid}", response_model=APIResponse[PortfolioDetail])
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
                    # 将参数从param_0, param_1格式转换为实际参数名
                    param_service = get_param_service()
                    # 获取组件名称用于参数映射（不传file_type，让函数自动推断）
                    component_name = file_obj.name if file_obj else ""
                    param_names = param_service.get_component_parameter_names(
                        component_name=component_name
                    )

                    # 转换参数
                    config = {}
                    for key, value in params.items():
                        if key.startswith('param_'):
                            idx = int(key.split('_')[1])
                            if idx in param_names:
                                param_name = param_names[idx]
                                config[param_name] = value
                    component_info['config'] = config

                # 根据类型分组
                if file_type == FILE_TYPES.SELECTOR:
                    selectors.append(component_info)
                elif file_type == FILE_TYPES.SIZER:
                    sizers.append(component_info)
                elif file_type == FILE_TYPES.STRATEGY:
                    strategies.append(component_info)
                elif file_type == FILE_TYPES.RISKMANAGER:
                    risk_managers.append(component_info)
                elif file_type == FILE_TYPES.ANALYZER:
                    analyzers.append(component_info)

        from datetime import datetime
        create_at_value = portfolio_model.create_at if hasattr(portfolio_model, 'create_at') and portfolio_model.create_at else None

        data = {
            "uuid": uuid,
            "name": portfolio_model.name,
            "mode": "BACKTEST" if portfolio_model.is_live == 0 else "LIVE",
            "state": "INITIALIZED",
            "config_locked": False,
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

        return {
            "success": True,
            "data": data,
            "error": None,
            "message": "Portfolio retrieved successfully"
        }

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error getting portfolio: {str(e)}")


@router.post("/", response_model=APIResponse[PortfolioDetail], status_code=status.HTTP_201_CREATED)
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
            sizer_data = {'component_uuid': data.sizer_uuid, 'config': {}}

        # 创建 Saga 事务
        saga = PortfolioSagaFactory.create_portfolio_saga(
            name=data.name,
            is_live=False,  # BACKTEST 模式
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


@router.put("/{uuid}", response_model=APIResponse[PortfolioDetail])
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
            sizer_data = {'component_uuid': data['sizer_uuid'], 'config': {}}

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
