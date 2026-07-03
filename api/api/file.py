"""文件管理 flat 适配路由 (#5659)

前端 web-ui/src/api/modules/file.ts 调用的 /api/v1/file_list、/api/v1/file、
/api/v1/update_file、/api/v1/file/{id} 等 flat 端点在后端无对应路由（全 404）。
FileService 能力完整，但只通过 /components（组件视角）、
/node-graphs/{uuid}/files（portfolio 绑定视角）暴露。本 router 提供面向
"全局文件管理"语义的 flat 适配端点，薄委托 FileService 既有方法，不改 service 核心。
"""
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from typing import Optional

from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES
from core.logging import logger
from core.response import ok, paginated

router = APIRouter()


def get_file_service():
    """获取 FileService 实例（与 components.py 同源容器注入）"""
    return container.file_service()


def _file_to_dict(file_record):
    """ORM MFile → JSON 可序列化 dict（#5659 review 修复）

    FileService.list_components/get_by_uuid 返 MFile ORM 实例（ADR-010: file_crud
    hook 为 identity，直接返 ORM 不转 entity）。早期实现把 ORM 对象直接塞进
    paginated()/ok()，端到端必 `TypeError: MFile not JSON serializable`。
    参照同目录 components.py:137-158 的转换模式：datetime 调 isoformat()。
    """
    if file_record is None:
        return None
    created_at = file_record.create_at if hasattr(file_record, "create_at") else None
    updated_at = file_record.update_at if hasattr(file_record, "update_at") else None
    is_del = file_record.is_del if hasattr(file_record, "is_del") else False
    return {
        "uuid": file_record.uuid,
        "name": file_record.name,
        "type": file_record.type if hasattr(file_record, "type") else 0,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "is_active": not is_del,
    }


@router.get("/file_list")
async def list_files(
    query: str = "",
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    type: Optional[int] = None,
):
    """获取文件列表（flat 适配路由，薄委托 FileService.list_components）

    与 GET /api/v1/components 等价，提供前端 file.ts 期望的 flat 命名。
    page 为 1-based（前端约定），下推 service 时转 0-based。
    """
    try:
        file_service = get_file_service()
        file_types = [FILE_TYPES.from_int(type)] if type is not None else None
        result = file_service.list_components(
            file_types=file_types,
            keyword=query or None,
            is_del=False,
            page=page - 1,
            page_size=size,
        )
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to list files",
            )
        result_data = result.data or {}
        # ORM MFile → dict（service 返 ModelList，直接塞 paginated 会序列化崩）
        items = [_file_to_dict(f) for f in result_data.get("data", [])]
        total = result_data.get("total", 0)
        return paginated(items=items, total=total, page=page, page_size=size)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files",
        )


class FileCreate(BaseModel):
    """前端 file.ts create(name, type, content) 的请求体"""

    name: str
    type: int
    content: str = ""


class FileUpdate(BaseModel):
    """前端 file.ts update(file_id, content) 的请求体"""

    file_id: str
    content: str


@router.get("/file/{file_id}")
async def get_file(file_id: str):
    """获取单个文件（flat 适配路由，薄委托 FileService.get_by_uuid）"""
    try:
        file_service = get_file_service()
        result = file_service.get_by_uuid(file_id)
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to get file",
            )
        data = result.data or {}
        if not data.get("exists"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )
        # ORM MFile → dict（service 返 ORM 单对象，直接塞 ok 会序列化崩）
        return ok(data=_file_to_dict(data.get("file")))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file",
        )


@router.post("/file", status_code=status.HTTP_201_CREATED)
async def create_file(data: FileCreate):
    """创建文件（flat 适配路由，薄委托 FileService.add）

    从 FileService.add 返回的 {"file_info": {"uuid": ...}} 嵌套结构提取 uuid
    （#5885 同款陷阱：直接 result.data.get("uuid") 取到 None）。
    """
    try:
        file_service = get_file_service()
        file_type = FILE_TYPES.from_int(data.type)
        result = file_service.add(
            name=data.name,
            file_type=file_type,
            data=data.content.encode("utf-8") if data.content else b"",
        )
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to create file",
            )
        file_info = (result.data or {}).get("file_info") or {}
        uuid = file_info.get("uuid")
        if not uuid:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get created file UUID",
            )
        return ok(data={"uuid": uuid, "name": data.name}, message="File created")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file",
        )


@router.post("/update_file")
async def update_file(data: FileUpdate):
    """更新文件内容（flat 适配路由，薄委托 FileService.update）

    content 字符串编码为 bytes 下推（FileService.update.data 参数要求 bytes）。
    """
    try:
        file_service = get_file_service()
        exists = file_service.get_by_uuid(data.file_id)
        if not (exists.is_success() and (exists.data or {}).get("exists")):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {data.file_id}",
            )
        result = file_service.update(
            file_id=data.file_id,
            data=data.content.encode("utf-8") if data.content else b"",
        )
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to update file",
            )
        return ok(message="File updated")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating file {data.file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file",
        )


@router.delete("/file/{file_id}")
async def delete_file(file_id: str):
    """删除文件（flat 适配路由，薄委托 FileService.soft_delete）"""
    try:
        file_service = get_file_service()
        result = file_service.soft_delete(file_id)
        if not result.is_success():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "Failed to delete file",
            )
        return ok(message="File deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )
