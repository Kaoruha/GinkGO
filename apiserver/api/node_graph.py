"""
节点图配置 API
提供节点图的 CRUD、验证、编译等接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import uuid
from datetime import datetime
import sys
from pathlib import Path

from schemas.node_graph import (
    NodeGraphSummary,
    NodeGraphDetail,
    NodeGraphCreate,
    NodeGraphUpdate,
    GraphData,
    ValidationResult,
    CompileResult,
    ValidationErrorItem,
)
from core.database import get_db
from core.logging import logger

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

router = APIRouter()


def get_portfolio_mapping_service():
    """获取 PortfolioMappingService 实例"""
    from ginkgo.data.containers import container
    return container.portfolio_mapping_service()


def get_file_service():
    """获取 FileService 实例"""
    from ginkgo.data.containers import container
    return container.file_service()


# ==================== CRUD 操作 ====================

@router.get("/", response_model=dict)
async def list_node_graphs(
    portfolio_uuid: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db=Depends(get_db)
):
    """
    获取节点图列表
    """
    try:
        service = get_portfolio_mapping_service()

        # 如果指定了 portfolio_uuid，返回该投资组合的图数据
        if portfolio_uuid:
            result = service.get_portfolio_graph(portfolio_uuid)
            if result.is_success():
                return {
                    "items": [result.data],
                    "total": 1,
                }
            else:
                return {
                    "items": [],
                    "total": 0,
                }

        # TODO: 实现分页查询所有图
        return {
            "items": [],
            "total": 0,
        }
    except Exception as e:
        logger.error(f"Error listing node graphs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing node graphs: {str(e)}"
        )


@router.get("/{graph_uuid}", response_model=dict)
async def get_node_graph(
    graph_uuid: str,
    db=Depends(get_db)
):
    """
    获取节点图详情
    """
    try:
        service = get_portfolio_mapping_service()

        # graph_uuid 实际上是 portfolio_uuid
        result = service.get_portfolio_graph(graph_uuid)

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node graph {graph_uuid} not found"
            )

        graph_data = result.data.get("graph_data", {})
        metadata = result.data.get("metadata", {})

        return {
            "uuid": graph_uuid,
            "portfolio_uuid": graph_uuid,
            "name": metadata.get("name", ""),
            "description": "",
            "graph_data": graph_data,
            "mode": "BACKTEST",
            "version": 1,
            "is_template": False,
            "tags": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting node graph: {str(e)}"
        )


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_node_graph(
    data: NodeGraphCreate,
    db=Depends(get_db)
):
    """
    创建节点图
    """
    try:
        service = get_portfolio_mapping_service()

        # 使用 portfolio_uuid 作为标识
        portfolio_uuid = data.portfolio_uuid or str(uuid.uuid4())

        # 调用服务创建图配置
        result = service.create_from_graph_editor(
            portfolio_uuid=portfolio_uuid,
            graph_data=data.graph_data.dict(),
            name=data.name,
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to create node graph"
            )

        return {
            "uuid": portfolio_uuid,
            "portfolio_uuid": portfolio_uuid,
            "name": data.name,
            "description": data.description,
            "graph_data": data.graph_data,
            "user_uuid": "",  # TODO: 从JWT token获取
            "version": 1,
            "is_template": data.is_template or False,
            "is_public": data.is_public or False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating node graph: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating node graph: {str(e)}"
        )


@router.put("/{graph_uuid}", response_model=dict)
async def update_node_graph(
    graph_uuid: str,
    data: NodeGraphUpdate,
    db=Depends(get_db)
):
    """
    更新节点图
    """
    try:
        service = get_portfolio_mapping_service()

        # graph_uuid 实际上是 portfolio_uuid
        result = service.update_from_graph_editor(
            portfolio_uuid=graph_uuid,
            graph_data=data.graph_data.dict(),
            name=data.name,
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to update node graph"
            )

        # 返回更新后的数据
        return await get_node_graph(graph_uuid)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating node graph: {str(e)}"
        )


@router.delete("/{graph_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node_graph(
    graph_uuid: str,
    db=Depends(get_db)
):
    """
    删除节点图
    """
    try:
        # TODO: 实现删除逻辑
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Delete operation not yet implemented"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting node graph: {str(e)}"
        )


@router.post("/{graph_uuid}/duplicate", response_model=dict)
async def duplicate_node_graph(
    graph_uuid: str,
    name: str,
    db=Depends(get_db)
):
    """
    复制节点图
    """
    try:
        # TODO: 实现复制逻辑
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Duplicate operation not yet implemented"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error duplicating node graph: {str(e)}"
        )


# ==================== 验证和编译 ====================

@router.post("/{graph_uuid}/validate", response_model=ValidationResult)
async def validate_node_graph(
    graph_uuid: str,
    data: GraphData,
    db=Depends(get_db)
):
    """
    验证节点图配置
    """
    try:
        errors = []
        warnings = []

        # 基本验证
        if not data.nodes:
            errors.append(ValidationErrorItem(
                field="nodes",
                message="图必须包含至少一个节点",
                severity="error"
            ))

        # 验证节点配置
        for i, node in enumerate(data.nodes):
            node_id = node.id if hasattr(node, 'id') else node.get('id', '')
            node_type = node.type if hasattr(node, 'type') else node.get('type', '')
            node_data = node.data if hasattr(node, 'data') else node.get('data', {})

            # 检查文件ID
            file_id = node_data.get('file_id') if isinstance(node_data, dict) else None
            if not file_id:
                errors.append(ValidationErrorItem(
                    field=f"nodes[{i}].file_id",
                    message=f"节点 {node_id} 缺少 file_id",
                    severity="error",
                    node_id=node_id
                ))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    except Exception as e:
        logger.error(f"Error validating node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating node graph: {str(e)}"
        )


@router.post("/{graph_uuid}/compile", response_model=CompileResult)
async def compile_node_graph(
    graph_uuid: str,
    data: GraphData,
    db=Depends(get_db)
):
    """
    编译节点图为回测配置
    """
    try:
        # TODO: 实现编译逻辑
        # 需要将节点图转换为BacktestTaskCreate格式
        from schemas.node_graph import BacktestTaskCreate

        # 暂时返回模拟数据
        return CompileResult(
            backtest_config=BacktestTaskCreate(
                name="回测任务",
                portfolio_uuids=[graph_uuid],
                engine_config={
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "broker_type": "backtest",
                    "initial_cash": 1000000.0,
                    "commission_rate": 0.0003,
                    "slippage_rate": 0.0,
                    "broker_attitude": 2,
                }
            ),
            warnings=[]
        )
    except Exception as e:
        logger.error(f"Error compiling node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error compiling node graph: {str(e)}"
        )


@router.post("/from-backtest/{backtest_uuid}", response_model=dict)
async def create_from_backtest(
    backtest_uuid: str,
    db=Depends(get_db)
):
    """
    从回测配置创建节点图
    """
    try:
        # TODO: 实现反向编译逻辑
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Not implemented yet"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating from backtest {backtest_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating from backtest: {str(e)}"
        )


# ==================== Portfolio 扩展接口 ====================

@router.get("/{portfolio_uuid}/mappings", response_model=dict)
async def get_portfolio_mappings(
    portfolio_uuid: str,
    include_params: bool = False,
    db=Depends(get_db)
):
    """
    获取投资组合的文件映射（含参数）
    """
    try:
        service = get_portfolio_mapping_service()

        result = service.get_portfolio_mappings(
            portfolio_uuid=portfolio_uuid,
            include_params=include_params
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_uuid} not found"
            )

        return {
            "portfolio_uuid": portfolio_uuid,
            "mappings": result.data,
            "total": len(result.data),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio mappings {portfolio_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting portfolio mappings: {str(e)}"
        )


@router.post("/{portfolio_uuid}/files", response_model=dict)
async def add_file_to_portfolio(
    portfolio_uuid: str,
    file_id: str,
    file_type: str,
    name: Optional[str] = None,
    params: Optional[dict] = None,
    db=Depends(get_db)
):
    """
    添加文件到投资组合（自动同步到图结构）
    """
    try:
        from ginkgo.enums import FILE_TYPES

        service = get_portfolio_mapping_service()

        result = service.add_file(
            portfolio_uuid=portfolio_uuid,
            file_id=file_id,
            file_type=FILE_TYPES[file_type.upper()],
            name=name,
            params=params,
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to add file"
            )

        return {
            "success": True,
            "file_id": file_id,
            "message": "File added successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding file to portfolio {portfolio_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding file: {str(e)}"
        )


@router.delete("/{portfolio_uuid}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_file_from_portfolio(
    portfolio_uuid: str,
    file_id: str,
    db=Depends(get_db)
):
    """
    从投资组合移除文件（自动同步到图结构）
    """
    try:
        service = get_portfolio_mapping_service()

        result = service.remove_file(
            portfolio_uuid=portfolio_uuid,
            file_id=file_id,
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to remove file"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing file from portfolio {portfolio_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing file: {str(e)}"
        )
