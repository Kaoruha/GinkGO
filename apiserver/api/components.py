"""
组件相关API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES, COMPONENT_TYPES
from core.logging import logger

router = APIRouter()


# ==================== 数据模型 ====================

class ComponentSummary(BaseModel):
    """组件摘要"""
    uuid: str
    name: str
    component_type: str  # strategy, analyzer, risk, sizer, selector
    file_type: int
    description: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    is_active: bool = True


class ComponentDetail(BaseModel):
    """组件详情"""
    uuid: str
    name: str
    component_type: str
    file_type: int
    code: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = []
    created_at: str
    updated_at: Optional[str] = None


class ComponentCreate(BaseModel):
    """创建组件请求"""
    name: str
    component_type: str  # strategy, analyzer, risk, sizer, selector
    code: str
    description: Optional[str] = None


class ComponentUpdate(BaseModel):
    """更新组件请求"""
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


# ==================== 组件类型映射 ====================

COMPONENT_FILE_TYPE_MAP = {
    "strategy": FILE_TYPES.STRATEGY,
    "analyzer": FILE_TYPES.ANALYZER,
    "risk": FILE_TYPES.RISKMANAGER,
    "sizer": FILE_TYPES.SIZER,
    "selector": FILE_TYPES.SELECTOR,
}

FILE_TYPE_TO_COMPONENT_TYPE = {
    FILE_TYPES.STRATEGY.value: "strategy",
    FILE_TYPES.ANALYZER.value: "analyzer",
    FILE_TYPES.RISKMANAGER.value: "risk",
    FILE_TYPES.SIZER.value: "sizer",
    FILE_TYPES.SELECTOR.value: "selector",
}


def get_file_service():
    """获取FileService实例"""
    return container.file_service()


# ==================== API路由 ====================

@router.get("", response_model=List[ComponentSummary])
async def list_components(
    component_type: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """获取组件列表"""
    try:
        file_service = get_file_service()
        components = []

        # 根据组件类型过滤
        types_to_check = []
        if component_type:
            if component_type in COMPONENT_FILE_TYPE_MAP:
                types_to_check.append(COMPONENT_FILE_TYPE_MAP[component_type])
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid component type: {component_type}"
                )
        else:
            # 检查所有组件类型
            types_to_check = list(COMPONENT_FILE_TYPE_MAP.values())

        # 获取各类型的文件
        for file_type in types_to_check:
            result = file_service.get_by_type(file_type)
            if result.is_success():
                files = result.data.get("files", [])
                for file_record in files:
                    # MFile对象使用属性访问而不是字典.get()
                    component_type_name = FILE_TYPE_TO_COMPONENT_TYPE.get(
                        file_type.value, "unknown"
                    )

                    created_at = file_record.create_at if file_record.create_at else datetime.utcnow()
                    updated_at = file_record.update_at if file_record.update_at else None
                    components.append({
                        "uuid": file_record.uuid,
                        "name": file_record.name,
                        "component_type": component_type_name,
                        "file_type": file_type.value,
                        "description": f"{component_type_name.capitalize()} component",
                        "created_at": created_at.isoformat(),
                        "updated_at": updated_at.isoformat() if updated_at else None,
                        "is_active": not file_record.is_del
                    })

        # 过滤和排序
        if is_active is not None:
            components = [c for c in components if c["is_active"] == is_active]

        # 按更新时间倒序排序，没有更新时间的按创建时间排序
        components.sort(key=lambda x: x.get("updated_at") or x["created_at"], reverse=True)

        return components

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing components: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list components: {str(e)}"
        )


@router.get("/{uuid}", response_model=ComponentDetail)
async def get_component(uuid: str):
    """获取组件详情"""
    try:
        file_service = get_file_service()

        # 使用 get_by_uuid 方法获取单个文件
        result = file_service.get_by_uuid(uuid)

        if not result.is_success() or not result.data:
            raise HTTPException(
                status_code=404,
                detail=f"Component not found: {uuid}"
            )

        # result.data 是字典，'file' 键才是 MFile 对象
        file_record = result.data.get("file")

        if not file_record:
            raise HTTPException(
                status_code=404,
                detail=f"Component file not found: {uuid}"
            )

        # 处理文件类型 - MFile.type 是整数值
        file_type_value = file_record.type
        component_type = FILE_TYPE_TO_COMPONENT_TYPE.get(file_type_value, "unknown")

        # 获取代码内容
        code = None
        content_result = file_service.get_content(uuid)
        file_data = content_result.data if content_result.is_success() else None
        if file_data:
            try:
                code = file_data.decode('utf-8')
            except:
                code = file_data.decode('latin-1', errors='ignore')

        created_at = file_record.create_at if file_record.create_at else datetime.utcnow()
        updated_at = file_record.update_at if file_record.update_at else None

        return {
            "uuid": file_record.uuid,
            "name": file_record.name,
            "component_type": component_type,
            "file_type": file_type_value,
            "code": code,
            "description": file_record.desc if file_record.desc else f"{component_type.capitalize()} component",
            "parameters": [],
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat() if updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting component {uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get component: {str(e)}"
        )


@router.post("", response_model=ComponentDetail)
async def create_component(data: ComponentCreate):
    """创建组件"""
    try:
        file_service = get_file_service()

        # 获取对应的文件类型
        if data.component_type not in COMPONENT_FILE_TYPE_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid component type: {data.component_type}"
            )

        file_type = COMPONENT_FILE_TYPE_MAP[data.component_type]

        # 使用 add 方法创建文件
        result = file_service.add(
            name=data.name,
            file_type=file_type,
            data=data.code.encode('utf-8') if data.code else b'',
            description=data.description
        )

        if not result.is_success():
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create component: {result.message}"
            )

        # 获取创建的文件记录
        file_uuid = result.data.get("uuid") if result.data else None
        if not file_uuid:
            raise HTTPException(
                status_code=500,
                detail="Failed to get created component UUID"
            )

        # 返回创建的组件详情
        return await get_component(file_uuid)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating component: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create component: {str(e)}"
        )


@router.put("/{uuid}")
async def update_component(uuid: str, data: ComponentUpdate):
    """更新组件"""
    try:
        file_service = get_file_service()
        file_crud = file_service._crud_repo

        # 验证存在
        result = file_service.get_by_uuid(uuid)
        if not result.is_success() or not result.data or not result.data.get("exists"):
            raise HTTPException(
                status_code=404,
                detail=f"Component not found: {uuid}"
            )

        # 准备更新 - desc 是数据库字段名，data 是内容字段
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.description is not None:
            updates["desc"] = data.description
        if data.code is not None:
            updates["data"] = data.code.encode('utf-8')

        if updates:
            file_crud.modify(filters={"uuid": uuid}, updates=updates)

        return {"message": "Component updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating component {uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update component: {str(e)}"
        )


@router.delete("/{uuid}")
async def delete_component(uuid: str):
    """删除组件"""
    try:
        file_service = get_file_service()

        # 使用 soft_delete 方法软删除文件
        result = file_service.soft_delete(uuid)

        if not result.is_success():
            raise HTTPException(
                status_code=404,
                detail=f"Component not found or already deleted: {uuid}"
            )

        return {"message": "Component deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting component {uuid}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete component: {str(e)}"
        )
