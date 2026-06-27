"""
节点图配置 API
提供节点图的 CRUD、验证、编译等接口
"""

from fastapi import APIRouter, HTTPException, status, Query
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
from core.logging import logger
from core.response import ok

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

router = APIRouter()


def get_portfolio_mapping_service():
    """获取 PortfolioMappingService 实例"""
    from ginkgo.data.containers import container
    return container.portfolio_mapping_service()


from ._file_type import _resolve_file_type, _validate_file_id  # noqa: F401 — 无副作用，可安全导入


def get_file_service():
    """获取 FileService 实例"""
    from ginkgo.data.containers import container
    return container.file_service()


# ==================== CRUD 操作 ====================

@router.get("")
async def list_node_graphs(
    portfolio_uuid: Optional[str] = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=500),
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
                return ok(data={
                    "items": [result.data],
                    "total": 1,
                })
            else:
                return ok(data={
                    "items": [],
                    "total": 0,
                })

        # TODO: 实现分页查询所有图
        return ok(data={
            "items": [],
            "total": 0,
        })
    except Exception as e:
        logger.error(f"Error listing node graphs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listing node graphs"
        )


@router.get("/{graph_uuid}")
async def get_node_graph(
    graph_uuid: str,
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

        return ok(data={
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
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting node graph"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_node_graph(
    data: NodeGraphCreate,
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

        return ok(data={
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
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating node graph: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating node graph"
        )


@router.put("/{graph_uuid}")
async def update_node_graph(
    graph_uuid: str,
    data: NodeGraphUpdate,
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
            detail="Error updating node graph"
        )


@router.delete("/{graph_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node_graph(
    graph_uuid: str,
):
    """
    删除节点图（清空图配置：删 Mongo 图文档 + engine_portfolio_mapping 行 + 关联 MParam）
    注：仅删图配置层，不删 Portfolio 实体本身。
    """
    try:
        service = get_portfolio_mapping_service()
        result = service.delete_graph(graph_uuid)
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to delete node graph"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting node graph"
        )


@router.post("/{graph_uuid}/duplicate")
async def duplicate_node_graph(
    graph_uuid: str,
    name: str,
):
    """
    复制节点图（读源图 → 以新 portfolio_uuid 写入图配置副本）
    """
    try:
        service = get_portfolio_mapping_service()
        result = service.duplicate_graph(graph_uuid, name=name)
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to duplicate node graph"
            )
        return ok(data=result.data, message="Graph duplicated successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error duplicating node graph"
        )


# ==================== 验证和编译 ====================

@router.post("/{graph_uuid}/validate")
async def validate_node_graph(
    graph_uuid: str,
    data: GraphData,
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

        result = ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        return ok(data=result.dict())
    except Exception as e:
        logger.error(f"Error validating node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating node graph"
        )


@router.post("/{graph_uuid}/compile")
async def compile_node_graph(
    graph_uuid: str,
    data: GraphData,
):
    """
    编译节点图为回测配置
    """
    try:
        # TODO: 实现编译逻辑
        # 需要将节点图转换为BacktestTaskCreate格式
        from schemas.node_graph import BacktestTaskCreate

        # 暂时返回模拟数据
        result = CompileResult(
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
        return ok(data=result.dict())
    except Exception as e:
        logger.error(f"Error compiling node graph {graph_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error compiling node graph"
        )


@router.post("/from-backtest/{backtest_uuid}")
async def create_from_backtest(
    backtest_uuid: str,
):
    """
    从回测配置读取节点图（查回测 → 取 portfolio_id → 返回该组合的现有图）
    语义：返回现有图，不创建新图（与 duplicate 区分）。
    """
    try:
        from ginkgo.data.containers import container

        bt_service = container.backtest_task_service()
        bt_result = bt_service.get_by_id(backtest_uuid)
        if not bt_result.is_success():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_uuid} not found"
            )
        portfolio_id = getattr(bt_result.data, "portfolio_id", "") or ""
        if not portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest {backtest_uuid} has no portfolio_id"
            )

        mapping_service = get_portfolio_mapping_service()
        graph_result = mapping_service.get_portfolio_graph(portfolio_id)
        if not graph_result.is_success():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node graph for backtest {backtest_uuid} (portfolio {portfolio_id}) not found"
            )

        return ok(data={
            "backtest_uuid": backtest_uuid,
            "portfolio_uuid": portfolio_id,
            "graph_data": graph_result.data.get("graph_data", {}),
            "metadata": graph_result.data.get("metadata", {}),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating from backtest {backtest_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating from backtest"
        )


# ==================== Portfolio 扩展接口 ====================

@router.get("/{portfolio_uuid}/mappings")
async def get_portfolio_mappings(
    portfolio_uuid: str,
    include_params: bool = False,
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

        return ok(data={
            "portfolio_uuid": portfolio_uuid,
            "mappings": result.data,
            "total": len(result.data),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio mappings {portfolio_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting portfolio mappings"
        )


@router.get("/{portfolio_uuid}/files")
async def get_portfolio_files(portfolio_uuid: str):
    """
    获取投资组合已绑定的文件列表 (#5806)

    委托 service.get_portfolio_mappings 返回文件级视图。
    与 GET /{portfolio_uuid}/mappings 同源；本端点 URL 语义更直白
    （RESTful /files），供前端「列文件」场景免带参数负载。
    """
    try:
        service = get_portfolio_mapping_service()

        result = service.get_portfolio_mappings(
            portfolio_uuid=portfolio_uuid,
            include_params=False,
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_uuid} not found"
            )

        return ok(data={
            "portfolio_uuid": portfolio_uuid,
            "files": result.data,
            "total": len(result.data),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio files {portfolio_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting portfolio files"
        )


@router.post("/{portfolio_uuid}/files")
async def add_file_to_portfolio(
    portfolio_uuid: str,
    file_id: str,
    file_type: str,
    name: Optional[str] = None,
    params: Optional[dict] = None,
):
    """
    添加文件到投资组合（自动同步到图结构）

    file_type 命名（统一归一化解析，见 _resolve_file_type #5774 #5578）：
      - 枚举名/大小写：strategy / STRATEGY / Strategy
      - 风控别名：risk / riskmanager / risk_manager / RISK 均映射为 RISKMANAGER
      - 整数/数字串：6 / "6"（FILE_TYPES 整数值）
    支持类型：ANALYZER / INDEX / RISKMANAGER / SELECTOR / SIZER / STRATEGY
    """
    try:
        from ginkgo.enums import FILE_TYPES

        # #5645: 空 file_id 校验（空串/None/纯空白）防止静默成功创建无效映射
        file_id = _validate_file_id(file_id)

        service = get_portfolio_mapping_service()

        # 解析 file_type：支持整数、数字字符串、枚举名、别名（#5774）
        resolved_type = _resolve_file_type(file_type)

        result = service.add_file(
            portfolio_uuid=portfolio_uuid,
            file_id=file_id,
            file_type=resolved_type,
            name=name,
            params=params,
        )

        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error or "Failed to add file"
            )

        return ok(data={
            "file_id": file_id,
        }, message="File added successfully")
    except HTTPException:
        raise
    except ValueError as e:
        # #5645: 入参校验失败（空 file_id / 无效 file_type）→ 400 而非 500
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding file to portfolio {portfolio_uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding file"
        )


@router.delete("/{portfolio_uuid}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_file_from_portfolio(
    portfolio_uuid: str,
    file_id: str,
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
            detail="Error removing file"
        )
