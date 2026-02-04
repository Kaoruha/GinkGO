"""
Portfolio相关API路由
"""

from fastapi import APIRouter, HTTPException, status, Query, Request
from typing import Optional
from core.database import get_db
from core.logging import logger
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


@router.get("", response_model=list[PortfolioSummary])
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
            return []

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

        return portfolios
    except Exception as e:
        logger.error(f"Error listing portfolios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing portfolios: {str(e)}"
        )


@router.get("/{uuid}", response_model=PortfolioDetail)
async def get_portfolio(uuid: str):
    """获取Portfolio详情（从数据库，包含组件配置）"""
    # 组件类型映射 (FILE_TYPES)
    TYPE_NAMES = {
        '1': 'STRATEGY',
        '3': 'RISKMANAGER',
        '4': 'SELECTOR',
        '5': 'SIZER',
        '6': 'STRATEGY',
        'STRATEGY': 'STRATEGY',
        'SELECTOR': 'SELECTOR',
        'SIZER': 'SIZER',
        'RISKMANAGER': 'RISKMANAGER',
    }

    try:
        # 获取PortfolioService
        portfolio_service = get_portfolio_service()

        # 获取基本信息
        portfolio_result = portfolio_service.get(portfolio_id=uuid)
        if not portfolio_result.is_success():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {uuid} not found"
            )

        portfolio_model = portfolio_result.data
        if isinstance(portfolio_model, list):
            portfolio_model = portfolio_model[0] if portfolio_model else None

        if portfolio_model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {uuid} not found"
            )

        # 获取组件信息
        components_result = portfolio_service.get_components(portfolio_id=uuid)

        # 获取FileService用于获取组件代码
        file_service = get_file_service()

        # 解析组件 (FILE_TYPES: STRATEGY=6, SELECTOR=4, SIZER=5, RISKMANAGER=3)
        strategies = []
        selectors = []
        sizers = []
        risk_managers = []

        if components_result.is_success():
            for comp in components_result.data or []:
                comp_type = comp.get('component_type', '')
                component_id = comp.get('component_id', '')

                # 获取文件详情
                code_content = None
                try:
                    file_result = file_service.get(filters={"uuid": component_id}, as_dataframe=False)
                    if file_result.is_success() and file_result.data:
                        file_data = file_result.data
                        files = file_data.get("files", [])
                        if files and len(files) > 0:
                            file_obj = files[0]
                            if hasattr(file_obj, 'data') and file_obj.data:
                                try:
                                    code_content = file_obj.data.decode('utf-8')
                                except:
                                    code_content = str(file_obj.data)
                except Exception as e:
                    logger.warning(f"Failed to get file {component_id}: {str(e)}")

                # 转换类型为可读名称
                readable_type = TYPE_NAMES.get(comp_type, comp_type)

                # 调试日志：打印组件代码
                component_name = comp.get('component_name', '')
                if 'fixed' in component_name.lower() or 'selector' in readable_type.lower():
                    logger.info(f"Component {component_name} ({component_id}): code_length={len(code_content) if code_content else 0}, code_preview={code_content[:200] if code_content else None}")

                # 保留mapping中的所有字段
                component_info = {
                    "uuid": component_id,
                    "name": comp.get('component_name', ''),
                    "type": readable_type,
                    "mount_id": comp.get('mount_id', ''),
                    "created_at": comp.get('created_at'),
                    "code": code_content,  # 组件代码（用于解析参数）
                }

                # 支持数字字符串和枚举名称
                if comp_type in ('STRATEGY', '6', '1'):
                    strategies.append(component_info)
                elif comp_type in ('SELECTOR', '4'):
                    selectors.append(component_info)
                elif comp_type in ('SIZER', '5'):
                    sizers.append(component_info)
                elif comp_type in ('RISKMANAGER', '3'):
                    risk_managers.append(component_info)

        return {
            "uuid": portfolio_model.uuid,
            "name": portfolio_model.name,
            "mode": "BACKTEST" if portfolio_model.is_live == 0 else "LIVE",
            "state": "INITIALIZED",
            "config_locked": False,
            "net_value": 1.0,
            "created_at": portfolio_model.create_at.isoformat() if hasattr(portfolio_model, 'create_at') and portfolio_model.create_at else None,
            "initial_cash": float(portfolio_model.initial_capital) if hasattr(portfolio_model, 'initial_capital') else 0,
            "current_cash": float(portfolio_model.cash) if hasattr(portfolio_model, 'cash') else 0,
            "positions": [],
            "strategies": strategies,
            "selectors": selectors,
            "sizers": sizers,
            "risk_managers": risk_managers,
            "risk_alerts": []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio {uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting portfolio: {str(e)}"
        )


@router.post("", response_model=PortfolioDetail, status_code=status.HTTP_201_CREATED)
async def create_portfolio(data: PortfolioCreate):
    """创建Portfolio"""
    import uuid as uuid_lib
    from datetime import datetime

    async with get_db() as db:
        portfolio_uuid = str(uuid_lib.uuid4())
        await db.execute(
            """INSERT INTO portfolio (uuid, name, initial_capital, cash, is_live, created_at)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [portfolio_uuid, data.name, data.initial_cash, data.initial_cash, 0, datetime.utcnow()]
        )
        await db.commit()

        return {
            "uuid": portfolio_uuid,
            "name": data.name,
            "mode": "BACKTEST",
            "state": "INITIALIZED",
            "config_locked": False,
            "net_value": 1.0,
            "created_at": datetime.utcnow().isoformat(),
            "initial_cash": data.initial_cash,
            "current_cash": data.initial_cash,
            "positions": [],
            "strategies": [],
            "selectors": [],
            "sizers": [],
            "risk_managers": [],
            "risk_alerts": []
        }


@router.put("/{uuid}", response_model=PortfolioDetail)
async def update_portfolio(uuid: str, data: dict):
    """更新Portfolio"""
    async with get_db() as db:
        await db.execute(
            "UPDATE portfolio SET update_at = NOW() WHERE uuid = %s",
            [uuid]
        )
        await db.commit()

        # 返回更新后的数据
        return await get_portfolio(uuid)


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(uuid: str):
    """删除Portfolio（软删除）"""
    async with get_db() as db:
        await db.execute(
            "UPDATE portfolio SET is_del = 1, update_at = NOW() WHERE uuid = %s",
            [uuid]
        )
        await db.commit()
