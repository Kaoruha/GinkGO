"""
file_type 参数解析工具

无模块级副作用（无 FastAPI/core 依赖），可安全在测试中导入。
"""


def _resolve_file_type(raw):
    """解析 file_type 参数：支持整数、数字字符串、枚举名、别名、snake_case (#5774 #5578)"""
    from ginkgo.enums import FILE_TYPES

    if isinstance(raw, int):
        result = FILE_TYPES.from_int(raw)
        if result is None:
            raise ValueError(f"Invalid file_type integer: {raw}")
        return result

    s = str(raw).strip()

    # 数字字符串
    if s.isdigit():
        result = FILE_TYPES.from_int(int(s))
        if result is None:
            raise ValueError(f"Invalid file_type: {s}")
        return result

    # 别名映射（短名 → 枚举全名）
    alias_map = {
        "RISK": FILE_TYPES.RISKMANAGER,
    }
    upper = s.upper()
    if upper in alias_map:
        return alias_map[upper]

    # 枚举名匹配（含 snake_case 归一化重试：risk_manager → RISKMANAGER，#5578）
    result = FILE_TYPES.enum_convert(s)
    if result is None and "_" in upper:
        result = FILE_TYPES.enum_convert(upper.replace("_", ""))
    if result is None:
        raise ValueError(f"Unknown file_type: {s}")
    return result


def _validate_file_id(file_id):
    """校验 file_id 非空 (#5645)。

    空值（None / 空串 / 纯空白）raise ValueError；合法值返回 strip 后的字符串。
    用于 add_file_to_portfolio 端点防止空 file_id 静默成功（创建无效映射）。
    """
    if file_id is None or str(file_id).strip() == "":
        raise ValueError("file_id must not be empty")
    return str(file_id).strip()
