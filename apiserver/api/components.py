"""
组件相关API路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import ast
import inspect

from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES, COMPONENT_TYPES
from ginkgo.data.services.component_parameter_extractor import get_component_parameter_names
from core.logging import logger
from services.component_parameter_service import get_component_parameter_service
from models.component import ComponentParameter

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

@router.get("/", response_model=List[ComponentSummary])
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

        # 提取组件参数
        parameters = []
        if code:
            try:
                parameters = extract_component_parameters(file_record.name, code, component_type)
            except Exception as e:
                logger.warning(f"Failed to extract parameters for {file_record.name}: {e}")

        created_at = file_record.create_at if file_record.create_at else datetime.utcnow()
        updated_at = file_record.update_at if file_record.update_at else None

        return {
            "uuid": file_record.uuid,
            "name": file_record.name,
            "component_type": component_type,
            "file_type": file_type_value,
            "code": code,
            "description": file_record.desc if file_record.desc else f"{component_type.capitalize()} component",
            "parameters": parameters,
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


@router.post("/", response_model=ComponentDetail)
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


# ==================== 组件参数端点 ====================

@router.get("/parameters/{component_name}", response_model=List[ComponentParameter])
async def get_component_parameters(component_name: str):
    """获取组件的参数定义"""
    try:
        service = get_component_parameter_service()
        params = service.get_component_parameters(component_name)
        if not params:
            raise HTTPException(
                status_code=404,
                detail=f"Component parameters not found: {component_name}"
            )
        return params
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting component parameters for {component_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get component parameters: {str(e)}"
        )


@router.get("/parameters", response_model=Dict[str, List[ComponentParameter]])
async def get_all_component_parameters():
    """获取所有组件的参数定义"""
    try:
        service = get_component_parameter_service()
        return service.get_all_component_definitions()
    except Exception as e:
        logger.error(f"Error getting all component parameters: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get component parameters: {str(e)}"
        )


# ==================== 辅助函数 ====================

def extract_component_parameters(component_name: str, code: str, component_type: str) -> List[Dict[str, Any]]:
    """
    从组件代码中提取参数信息

    Returns:
        List[Dict]: 参数列表，每个参数包含：
            - name: 参数名
            - type: 参数类型 (string, number, boolean, select)
            - default: 默认值
            - required: 是否必需
            - description: 描述
            - options: 选项（仅select类型）
            - min: 最小值（仅number类型）
            - max: 最大值（仅number类型）
            - step: 步长（仅number类型）
    """
    parameters = []

    try:
        # 使用AST解析代码
        tree = ast.parse(code)

        # 查找组件类
        component_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 查找包含component名称的类
                class_name = node.name.lower().replace('_', '')
                comp_name = component_name.lower().replace('_', '')
                if comp_name in class_name or class_name in comp_name:
                    component_class = node
                    break

        # 如果没找到精确匹配，查找第一个包含组件类型关键词的类
        if not component_class:
            type_keywords = {
                'strategy': 'strategy',
                'selector': 'selector',
                'sizer': 'sizer',
                'risk': 'risk',
                'analyzer': 'analyzer'
            }
            keyword = type_keywords.get(component_type.lower(), '')

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if keyword and keyword in node.name.lower():
                        component_class = node
                        break

        if not component_class:
            return parameters

        # 查找__init__方法
        init_method = None
        for node in component_class.body:
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                init_method = node
                break

        if not init_method:
            return parameters

        # 提取参数信息
        for arg in init_method.args.args:
            arg_name = arg.arg

            # 跳过self
            if arg_name == 'self':
                continue

            # 跳过name参数（通用参数）
            if arg_name == 'name':
                continue

            # 获取参数的默认值
            default_value = None
            has_default = False
            param_index = init_method.args.args.index(arg)

            # defaults对应的是没有默认值的参数之后的有默认值的参数
            num_no_default = len(init_method.args.args) - len(init_method.args.defaults)
            if param_index >= num_no_default:
                default_index = param_index - num_no_default
                if default_index < len(init_method.args.defaults):
                    default_node = init_method.args.defaults[default_index]
                    default_value = _get_default_value(default_node)
                    has_default = True

            # 推断参数类型
            param_type = _infer_parameter_type(arg_name, default_value)

            # 构建参数对象
            param_info = {
                "name": arg_name,
                "label": _format_parameter_label(arg_name),
                "type": param_type,
                "default": default_value,
                "required": not has_default,
                "description": f"{_format_parameter_label(arg_name)}参数"
            }

            # 根据参数名添加额外约束
            extra_info = _get_parameter_constraints(arg_name, param_type)
            param_info.update(extra_info)

            parameters.append(param_info)

    except Exception as e:
        logger.warning(f"Failed to parse component parameters: {e}")

    return parameters


def _get_default_value(node):
    """从AST节点获取默认值"""
    try:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.NameConstant):
            return node.value
        elif isinstance(node, ast.List):
            return [_get_default_value(item) for item in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                _get_default_value(k): _get_default_value(v)
                for k, v in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.Call):
            # 处理函数调用（如 list(), dict()）
            return None
        return None
    except:
        return None


def _infer_parameter_type(param_name: str, default_value: Any) -> str:
    """推断参数类型"""
    if default_value is not None:
        if isinstance(default_value, bool):
            return "boolean"
        elif isinstance(default_value, int):
            return "number"
        elif isinstance(default_value, float):
            return "number"
        elif isinstance(default_value, list):
            return "array"
        elif isinstance(default_value, dict):
            return "object"
        else:
            return "string"

    # 根据参数名推断类型
    name_lower = param_name.lower()

    # 常见的数字参数
    if any(kw in name_lower for kw in [
        'period', 'length', 'window', 'day', 'count', 'num',
        'volume', 'amount', 'ratio', 'percent', 'rate',
        'limit', 'max', 'min', 'threshold', 'level'
    ]):
        return "number"

    # 布尔参数
    if any(kw in name_lower for kw in ['enable', 'disable', 'use', 'is_', 'has_']):
        return "boolean"

    # 数组/列表参数
    if any(kw in name_lower for kw in ['codes', 'symbols', 'list', 'array']):
        return "array"

    return "string"


def _format_parameter_label(param_name: str) -> str:
    """格式化参数标签（将参数名转为可读的中文或英文标签）"""
    # 常见参数名的中文映射
    label_map = {
        'codes': '股票代码',
        'symbols': '股票代码',
        'volume': '数量',
        'amount': '金额',
        'period': '周期',
        'length': '长度',
        'window': '窗口',
        'ratio': '比例',
        'percent': '百分比',
        'rate': '比率',
        'count': '数量',
        'limit': '限制',
        'max': '最大值',
        'min': '最小值',
        'threshold': '阈值',
        'level': '水平',
        'probability': '概率',
        'buy_probability': '买入概率',
        'sell_probability': '卖出概率',
        'short_period': '短期周期',
        'long_period': '长期周期',
        'std_dev': '标准差',
        'overbought': '超买',
        'oversold': '超卖',
        'fast_period': '快线周期',
        'slow_period': '慢线周期',
        'signal_period': '信号周期',
        'atr_multiplier': 'ATR倍数',
        'risk_percent': '风险比例',
        'loss_limit': '止损限制',
        'profit_limit': '止盈限制',
        'max_drawdown': '最大回撤',
        'win_rate': '胜率',
    }

    if param_name in label_map:
        return label_map[param_name]

    # 转换为驼峰命名
    return ''.join(word.capitalize() for word in param_name.split('_'))


def _get_parameter_constraints(param_name: str, param_type: str) -> Dict[str, Any]:
    """根据参数名和类型获取约束条件"""
    constraints = {}

    if param_type == "number":
        name_lower = param_name.lower()

        # 比例/百分比参数
        if any(kw in name_lower for kw in ['ratio', 'percent', 'probability', 'rate']):
            constraints.update({
                'min': 0,
                'max': 100 if 'percent' in name_lower else 1,
                'step': 0.01,
                'precision': 2
            })
        # 周期参数
        elif any(kw in name_lower for kw in ['period', 'length', 'window']):
            constraints.update({
                'min': 1,
                'max': 1000,
                'step': 1,
                'precision': 0
            })
        # 数量/金额参数
        elif any(kw in name_lower for kw in ['volume', 'amount', 'count']):
            constraints.update({
                'min': 0,
                'max': 1000000,
                'step': 1,
                'precision': 0
            })
        else:
            # 默认数字约束
            constraints.update({
                'min': 0,
                'max': 10000,
                'step': 1,
                'precision': 0
            })

    return constraints
