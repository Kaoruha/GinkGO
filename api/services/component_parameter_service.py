"""
组件参数服务 - 提供组件参数元数据和验证
"""
from typing import List, Optional, Dict, Any
from models.component import (
    ComponentParameter,
    ComponentConfig,
    COMPONENT_PARAMETER_DEFINITIONS,
    ParamType
)
from core.logging import logger


class ComponentParameterService:
    """组件参数服务"""

    def get_component_parameters(self, component_name: str) -> List[ComponentParameter]:
        """获取组件的参数定义"""
        return COMPONENT_PARAMETER_DEFINITIONS.get(component_name, [])

    def get_all_component_definitions(self) -> Dict[str, List[ComponentParameter]]:
        """获取所有组件的参数定义"""
        return COMPONENT_PARAMETER_DEFINITIONS

    def validate_component_config(self, config: ComponentConfig) -> tuple[bool, List[str]]:
        """验证组件配置"""
        errors = []

        # 获取参数定义
        params_def = self.get_component_parameters(config.component_name)
        params_dict = {p.name: p for p in params_def}

        # 检查必需参数
        provided_params = set(config.parameters.keys())
        required_params = {p.name for p in params_def if p.required}

        missing_params = required_params - provided_params
        if missing_params:
            errors.append(f"缺少必需参数: {', '.join(missing_params)}")

        # 验证参数值
        for param_name, param_value in config.parameters.items():
            if param_name not in params_dict:
                errors.append(f"未知参数: {param_name}")
                continue

            param_def = params_dict[param_name]

            # 类型验证
            if param_def.type == ParamType.INT:
                if not isinstance(param_value, int):
                    try:
                        param_value = int(param_value)
                    except (ValueError, TypeError):
                        errors.append(f"{param_name}: 必须是整数")
                        continue

            # 范围验证
            if param_def.min_value is not None:
                if isinstance(param_value, (int, float)) and param_value < param_def.min_value:
                    errors.append(f"{param_name}: 小于最小值 {param_def.min_value}")

            if param_def.max_value is not None:
                if isinstance(param_value, (int, float)) and param_value > param_def.max_value:
                    errors.append(f"{param_name}: 大于最大值 {param_def.max_value}")

            # 枚举验证
            if param_def.options is not None:
                if param_value not in param_def.options:
                    errors.append(f"{param_name}: 值必须是 {param_def.options} 之一")

        return len(errors) == 0, errors

    def normalize_component_config(self, config: ComponentConfig) -> ComponentConfig:
        """标准化组件配置（填充默认值）"""
        params_def = self.get_component_parameters(config.component_name)
        params_dict = {p.name: p for p in params_def}

        normalized_parameters = {}

        # 复制现有参数
        for param_name, param_value in config.parameters.items():
            if param_name in params_dict:
                normalized_parameters[param_name] = param_value

        # 填充默认值
        for param_def in params_def:
            if param_def.name not in normalized_parameters and param_def.default_value is not None:
                normalized_parameters[param_def.name] = param_def.default_value

        return ComponentConfig(
            component_uuid=config.component_uuid,
            component_name=config.component_name,
            component_type=config.component_type,
            parameters=normalized_parameters
        )

    def get_parameter_value(self, config: ComponentConfig, param_name: str, default: Any = None) -> Any:
        """获取参数值（支持默认值回退）"""
        params_def = self.get_component_parameters(config.component_name)
        params_dict = {p.name: p for p in params_def}

        if param_name in config.parameters:
            return config.parameters[param_name]

        if param_name in params_dict:
            param_def = params_dict[param_name]
            if param_def.default_value is not None:
                return param_def.default_value

        return default

    def merge_parameters(self, base_params: Dict[str, Any], override_params: Dict[str, Any]) -> Dict[str, Any]:
        """合并参数配置（override_params 覆盖 base_params）"""
        merged = base_params.copy()
        merged.update(override_params)
        return merged

    def convert_to_worker_format(self, config: ComponentConfig) -> Dict[str, Any]:
        """
        将组件配置转换为 Worker 格式

        前端格式: {component_uuid: "abc", parameters: {period: 252, risk_free_rate: 0.03}}
        Worker格式: {period: 252, risk_free_rate: 0.03}
        """
        normalized = self.normalize_component_config(config)
        return normalized.parameters

    def convert_from_worker_format(
        self,
        component_uuid: str,
        component_name: str,
        component_type: str,
        worker_params: Dict[str, Any]
    ) -> ComponentConfig:
        """
        将 Worker 格式转换为组件配置

        Worker格式: {period: 252, risk_free_rate: 0.03}
        前端格式: {component_uuid: "abc", parameters: {period: 252, risk_free_rate: 0.03}}
        """
        return ComponentConfig(
            component_uuid=component_uuid,
            component_name=component_name,
            component_type=component_type,
            parameters=worker_params
        )


# 全局实例
_parameter_service: Optional[ComponentParameterService] = None


def get_component_parameter_service() -> ComponentParameterService:
    """获取组件参数服务实例"""
    global _parameter_service
    if _parameter_service is None:
        _parameter_service = ComponentParameterService()
    return _parameter_service
