"""
Ginkgo Data CRUD Validation Module

配置化数据验证框架，提供统一的数据验证和类型转换功能。

Features:
- 多类型转换支持
- 字段约束验证（范围、枚举、正则表达式）
- 统一异常处理
- 配置化验证规则
- 优化的枚举类型处理

Usage:
    from ginkgo.data.crud.validation import ValidationError, validate_data_by_config

    field_config = {
        'code': {'type': 'string', 'pattern': r'^[0-9]{6}\\.(SZ|SH)$'},
        'price': {'type': ['decimal', 'float'], 'min': 0.001},
        'volume': {'type': ['int', 'string'], 'min': 0},
        'status': {'type': 'ENGINESTATUS_TYPES', 'default': ENGINESTATUS_TYPES.IDLE.value}
    }

    try:
        validated_data = validate_data_by_config(data, field_config)
    except ValidationError as e:
        print(f"Validation failed: {e}")
"""

import re
from typing import Dict, Any, List, Union, Type
from decimal import Decimal
from datetime import datetime

# 导入枚举类型用于直接映射
try:
    from ginkgo.enums import (
        ENGINESTATUS_TYPES, SOURCE_TYPES, DIRECTION_TYPES,
        ORDER_TYPES, ORDERSTATUS_TYPES, FREQUENCY_TYPES,
        MARKET_TYPES, ATTITUDE_TYPES, FILE_TYPES,
        RECORDSTAGE_TYPES, GRAPHY_TYPES, PARAMETER_TYPES,
        CAPITALADJUSTMENT_TYPES, ADJUSTMENT_TYPES, STRATEGY_TYPES,
        MODEL_TYPES, ENGINE_TYPES, ENGINE_ARCHITECTURE,
        EXECUTION_MODE, EXECUTION_STATUS, TRACKING_STATUS,
        ACCOUNT_TYPE, COMPONENT_TYPES, ENTITY_TYPES, TIME_MODE,
        TICKDIRECTION_TYPES, EVENT_TYPES, PRICEINFO_TYPES,
        TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES,
        CURRENCY_TYPES, LIVE_MODE
    )
except ImportError:
    # 如果导入失败，使用空的枚举映射
    ENGINESTATUS_TYPES = SOURCE_TYPES = DIRECTION_TYPES = None
    ORDER_TYPES = ORDERSTATUS_TYPES = FREQUENCY_TYPES = None
    MARKET_TYPES = ATTITUDE_TYPES = FILE_TYPES = None
    RECORDSTAGE_TYPES = GRAPHY_TYPES = PARAMETER_TYPES = None
    CAPITALADJUSTMENT_TYPES = ADJUSTMENT_TYPES = STRATEGY_TYPES = None
    MODEL_TYPES = ENGINE_TYPES = ENGINE_ARCHITECTURE = None
    EXECUTION_MODE = EXECUTION_STATUS = TRACKING_STATUS = None
    ACCOUNT_TYPE = COMPONENT_TYPES = ENTITY_TYPES = TIME_MODE = None
    TICKDIRECTION_TYPES = EVENT_TYPES = PRICEINFO_TYPES = None
    TRANSFERDIRECTION_TYPES = TRANSFERSTATUS_TYPES = None
    CURRENCY_TYPES = LIVE_MODE = None


# 枚举类映射表 - 避免globals()查找，提高性能和类型安全性
ENUM_MAP = {
    'ENGINESTATUS_TYPES': ENGINESTATUS_TYPES,
    'SOURCE_TYPES': SOURCE_TYPES,
    'DIRECTION_TYPES': DIRECTION_TYPES,
    'ORDER_TYPES': ORDER_TYPES,
    'ORDERSTATUS_TYPES': ORDERSTATUS_TYPES,
    'FREQUENCY_TYPES': FREQUENCY_TYPES,
    'MARKET_TYPES': MARKET_TYPES,
    'ATTITUDE_TYPES': ATTITUDE_TYPES,
    'FILE_TYPES': FILE_TYPES,
    'RECORDSTAGE_TYPES': RECORDSTAGE_TYPES,
    'GRAPHY_TYPES': GRAPHY_TYPES,
    'PARAMETER_TYPES': PARAMETER_TYPES,
    'CAPITALADJUSTMENT_TYPES': CAPITALADJUSTMENT_TYPES,
    'ADJUSTMENT_TYPES': ADJUSTMENT_TYPES,
    'STRATEGY_TYPES': STRATEGY_TYPES,
    'MODEL_TYPES': MODEL_TYPES,
    'ENGINE_TYPES': ENGINE_TYPES,
    'ENGINE_ARCHITECTURE': ENGINE_ARCHITECTURE,
    'EXECUTION_MODE': EXECUTION_MODE,
    'EXECUTION_STATUS': EXECUTION_STATUS,
    'TRACKING_STATUS': TRACKING_STATUS,
    'ACCOUNT_TYPE': ACCOUNT_TYPE,
    'COMPONENT_TYPES': COMPONENT_TYPES,
    'ENTITY_TYPES': ENTITY_TYPES,
    'TIME_MODE': TIME_MODE,
    'TICKDIRECTION_TYPES': TICKDIRECTION_TYPES,
    'EVENT_TYPES': EVENT_TYPES,
    'PRICEINFO_TYPES': PRICEINFO_TYPES,
    'TRANSFERDIRECTION_TYPES': TRANSFERDIRECTION_TYPES,
    'TRANSFERSTATUS_TYPES': TRANSFERSTATUS_TYPES,
    'CURRENCY_TYPES': CURRENCY_TYPES,
    'LIVE_MODE': LIVE_MODE,
}


class ValidationError(Exception):
    """统一数据验证异常"""
    
    def __init__(self, message: str, field: str = None, value=None):
        self.field = field
        self.value = value
        super().__init__(message)


def validate_data_by_config(data: dict, field_config: dict) -> dict:
    """
    根据配置验证数据 - 支持多类型转换
    
    Args:
        data: 待验证的数据字典
        field_config: 字段配置字典
        
    Returns:
        验证并转换后的数据字典
        
    Raises:
        ValidationError: 当验证失败时
        
    Example:
        field_config = {
            'code': {'type': 'string', 'pattern': r'^[0-9]{6}\\.(SZ|SH)$'},
            'price': {'type': ['decimal', 'float'], 'min': 0.001},
            'volume': {'type': ['int', 'string'], 'min': 0}
        }
        validated = validate_data_by_config(data, field_config)
    """
    if not field_config:
        return data.copy()
    
    validated = {}
    
    # 1. 必填字段检查 - 配置中的所有字段都必须存在
    for field_name in field_config.keys():
        if field_name not in data:
            raise ValidationError(
                f"Missing required field: {field_name}",
                field_name,
                None
            )

    # 2. 逐字段验证和转换
    for field_name, field_spec in field_config.items():
        field_value = data[field_name]
        
        try:
            # 类型转换
            converted_value = convert_to_type(field_value, field_spec.get('type'))
            
            # 范围验证
            validate_field_constraints(field_name, converted_value, field_spec)
            
            validated[field_name] = converted_value
            
        except ValidationError as e:
            # 直接传递ValidationError，保持原始错误信息
            raise e
        except Exception as e:
            # 其他异常（如类型转换异常）包装为ValidationError
            raise ValidationError(
                f"Field '{field_name}' validation failed: {str(e)}",
                field_name,
                field_value
            )
    
    # 3. 保留非配置字段（不验证，直接复制）
    for field_name, field_value in data.items():
        if field_name not in field_config:
            validated[field_name] = field_value
    
    return validated


def convert_to_type(value: Any, type_config: Union[str, List[str]]) -> Any:
    """
    多类型转换函数 - 按优先级尝试类型转换
    
    Args:
        value: 待转换的值
        type_config: 类型配置，可以是单个类型或类型列表
        
    Returns:
        转换后的值
        
    Raises:
        ValueError: 当所有类型转换都失败时
    """
    if type_config is None:
        return value
    
    # 统一为列表格式
    if isinstance(type_config, str):
        type_list = [type_config]
    else:
        type_list = type_config
    
    # 按顺序尝试转换
    conversion_errors = []
    
    for type_name in type_list:
        try:
            return _convert_single_type(value, type_name)
        except Exception as e:
            conversion_errors.append(f"{type_name}: {str(e)}")
            continue
    
    # 所有转换都失败
    raise ValueError(
        f"Cannot convert value '{value}' to any of types {type_list}. "
        f"Errors: {'; '.join(conversion_errors)}"
    )


def _convert_single_type(value: Any, type_name: str) -> Any:
    """
    单一类型转换 - 支持枚举类型

    Args:
        value: 待转换的值
        type_name: 目标类型名称

    Returns:
        转换后的值
    """
    # 严格的类型预检查 - 拒绝明显不兼容的类型
    if type_name in ['int', 'float', 'decimal']:
        if isinstance(value, (dict, list, tuple, set)):
            raise ValueError(f"Cannot convert {type(value).__name__} to {type_name}")

    if type_name == 'string':
        if isinstance(value, (dict, list, tuple, set)):
            raise ValueError(f"Cannot convert {type(value).__name__} to string")

    # 如果已经是目标类型，直接返回
    type_checkers = {
        'string': lambda x: isinstance(x, str),
        'int': lambda x: isinstance(x, int) and not isinstance(x, bool),
        'float': lambda x: isinstance(x, float),
        'decimal': lambda x: isinstance(x, Decimal),
        'datetime': lambda x: isinstance(x, datetime),
        'bool': lambda x: isinstance(x, bool),
        'bytes': lambda x: isinstance(x, bytes),
    }

    if type_name in type_checkers and type_checkers[type_name](value):
        return value

    # 检查枚举类型
    if type_name in ENUM_MAP:
        enum_class = ENUM_MAP[type_name]
        if enum_class is None:
            raise ValueError(f"Enum type '{type_name}' not available")

        # 如果已经是枚举对象，验证其有效性
        if hasattr(value, '__class__') and hasattr(value, '__members__') and hasattr(value, 'value'):
            if value.__class__ is enum_class:
                # 验证是否为有效的枚举值
                try:
                    enum_class(value.value)  # 这会抛出ValueError如果值无效
                    return value  # 直接返回枚举对象
                except ValueError:
                    raise ValueError(f"Invalid enum value: {value}")
            else:
                # 枚举类型不匹配，这里不能直接return，让后续逻辑处理
                pass
        else:
            # 尝试将值转换为枚举
            try:
                return enum_class.validate_input(value)
            except (ValueError, TypeError):
                # 枚举转换失败，这里不能continue，让后续逻辑处理
                pass
    
    # 类型转换逻辑
    if type_name == 'string':
        if value is None:
            raise ValueError("Cannot convert None to string")
        return str(value).strip()
    
    elif type_name == 'int':
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Cannot convert empty string to int")
            # 检查是否为整数格式的字符串
            if '.' in value:
                # 尝试转为float再检查是否为整数
                float_val = float(value)
                if not float_val.is_integer():
                    raise ValueError(f"String '{value}' is not an integer")
                return int(float_val)
            return int(value)
        elif isinstance(value, (float, Decimal)):
            if not float(value).is_integer():
                raise ValueError(f"Value {value} is not an integer")
            return int(value)
        else:
            return int(value)
    
    elif type_name == 'float':
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Cannot convert empty string to float")
            return float(value)
        else:
            return float(value)
    
    elif type_name == 'decimal':
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Cannot convert empty string to decimal")
            return Decimal(value)
        else:
            return Decimal(str(value))
    
    elif type_name == 'datetime':
        if isinstance(value, str):
            try:
                # 使用 Ginkgo 的日期时间规范化函数
                from ginkgo.libs import datetime_normalize
                return datetime_normalize(value)
            except Exception:
                raise ValueError(f"Cannot parse datetime from string '{value}'")
        else:
            raise ValueError(f"Cannot convert {type(value).__name__} to datetime")
    
    elif type_name == 'bool':
        if isinstance(value, str):
            lower_val = value.lower().strip()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            elif lower_val in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"Cannot convert string '{value}' to bool")
        else:
            return bool(value)
    
    elif type_name == 'bytes':
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            # 字符串转bytes，使用UTF-8编码
            return value.encode('utf-8')
        else:
            raise ValueError(f"Cannot convert {type(value).__name__} to bytes")
    
    elif type_name == 'enum':
        # 枚举类型需要配合 choices 参数使用
        return value
    
    elif type_name == 'numeric':
        # numeric 是 int|float|decimal 的别名
        for numeric_type in ['int', 'float', 'decimal']:
            try:
                return _convert_single_type(value, numeric_type)
            except:
                continue
        raise ValueError(f"Cannot convert '{value}' to any numeric type")
    
    else:
        raise ValueError(f"Unknown type '{type_name}'")


def validate_field_constraints(field_name: str, value: Any, field_spec: dict) -> None:
    """
    验证字段约束条件
    
    Args:
        field_name: 字段名
        value: 字段值
        field_spec: 字段规格配置
        
    Raises:
        ValidationError: 当约束验证失败时
    """
    # 最小值/最小长度检查
    if 'min' in field_spec:
        min_val = field_spec['min']
        if isinstance(value, str):
            if len(value) < min_val:
                raise ValidationError(
                    f"String length {len(value)} is below minimum {min_val}",
                    field_name,
                    value
                )
        elif isinstance(value, (int, float, Decimal)):
            # 统一类型进行精确比较，避免浮点数精度问题
            if isinstance(value, Decimal) and not isinstance(min_val, Decimal):
                # value是Decimal，min_val是float/int，将min_val转为Decimal比较
                min_val_decimal = Decimal(str(min_val))
                if value < min_val_decimal:
                    raise ValidationError(
                        f"Value {value} is below minimum {min_val}",
                        field_name,
                        value
                    )
            elif isinstance(min_val, Decimal) and not isinstance(value, Decimal):
                # min_val是Decimal，value是float/int，将value转为Decimal比较
                value_decimal = Decimal(str(value))
                if value_decimal < min_val:
                    raise ValidationError(
                        f"Value {value} is below minimum {min_val}",
                        field_name,
                        value
                    )
            else:
                # 同类型直接比较
                if value < min_val:
                    raise ValidationError(
                        f"Value {value} is below minimum {min_val}",
                        field_name,
                        value
                    )
    
    # 最大值/最大长度检查
    if 'max' in field_spec:
        max_val = field_spec['max']
        if isinstance(value, str):
            if len(value) > max_val:
                raise ValidationError(
                    f"String length {len(value)} exceeds maximum {max_val}",
                    field_name,
                    value
                )
        elif isinstance(value, (int, float, Decimal)):
            # 统一类型进行精确比较，避免浮点数精度问题
            if isinstance(value, Decimal) and not isinstance(max_val, Decimal):
                # value是Decimal，max_val是float/int，将max_val转为Decimal比较
                max_val_decimal = Decimal(str(max_val))
                if value > max_val_decimal:
                    raise ValidationError(
                        f"Value {value} exceeds maximum {max_val}",
                        field_name,
                        value
                    )
            elif isinstance(max_val, Decimal) and not isinstance(value, Decimal):
                # max_val是Decimal，value是float/int，将value转为Decimal比较
                value_decimal = Decimal(str(value))
                if value_decimal > max_val:
                    raise ValidationError(
                        f"Value {value} exceeds maximum {max_val}",
                        field_name,
                        value
                    )
            else:
                # 同类型直接比较
                if value > max_val:
                    raise ValidationError(
                        f"Value {value} exceeds maximum {max_val}",
                        field_name,
                        value
                    )
    
    # 枚举值检查 - 支持枚举对象和数值双重格式
    if 'choices' in field_spec:
        choices = field_spec['choices']
        
        # 智能枚举匹配
        is_valid = False
        
        # 1. 直接匹配
        if value in choices:
            is_valid = True
        else:
            # 2. 交叉匹配：枚举对象 vs 数值
            for choice in choices:
                # 如果choice是枚举对象，value是数值
                if hasattr(choice, 'value') and choice.value == value:
                    is_valid = True
                    break
                # 如果choice是数值，value是枚举对象  
                elif hasattr(value, 'value') and value.value == choice:
                    is_valid = True
                    break
        
        if not is_valid:
            raise ValidationError(
                f"Value '{value}' is not in allowed choices: {choices}",
                field_name,
                value
            )
    
    # 正则表达式检查
    if 'pattern' in field_spec and isinstance(value, str):
        pattern = field_spec['pattern']
        if not re.match(pattern, value):
            raise ValidationError(
                f"Value '{value}' does not match pattern '{pattern}'",
                field_name,
                value
            )