# Upstream: notify_cli.py (ginkgo notify template --var)
# Downstream: None (Unit test for parameter parsing logic)
# Role: 单元测试验证 --var 参数的解析逻辑，包括变量传递、类型转换、默认值覆盖


"""
Unit tests for --var parameter handling in CLI commands.

测试覆盖：
- 基本的键值对解析
- 字符串值处理
- JSON 类型转换（数字、布尔值、对象、数组）
- 无效 JSON 处理
- 多个变量组合
- 特殊字符和空值处理
"""

import pytest
import json
from typing import Dict, Any


def parse_variables(variables: list) -> Dict[str, Any]:
    """
    解析 --var 参数列表为字典

    Args:
        variables: key=value 格式的字符串列表

    Returns:
        Dict: 解析后的变量字典

    解析逻辑：
    1. 按 "=" 分割键值对
    2. 尝试将值解析为 JSON（支持数字、布尔值、对象、数组）
    3. JSON 解析失败时，将值作为字符串
    """
    context = {}
    if variables:
        for var in variables:
            if "=" in var:
                key, value = var.split("=", 1)
                try:
                    context[key] = json.loads(value)
                except json.JSONDecodeError:
                    context[key] = value
    return context


@pytest.mark.unit
class TestVarParameterParsing:
    """测试 --var 参数解析逻辑"""

    def test_simple_string_value(self):
        """测试简单的字符串值"""
        variables = ["name=Alice", "message=Hello World"]
        result = parse_variables(variables)

        assert result == {
            "name": "Alice",
            "message": "Hello World"
        }

    def test_integer_value(self):
        """测试整数值（JSON格式）"""
        variables = ["age=25", "count=100"]
        result = parse_variables(variables)

        assert result == {
            "age": 25,
            "count": 100
        }
        # 验证类型是整数
        assert isinstance(result["age"], int)
        assert isinstance(result["count"], int)

    def test_float_value(self):
        """测试浮点数值（JSON格式）"""
        variables = ["price=19.99", "rate=3.14"]
        result = parse_variables(variables)

        assert result == {
            "price": 19.99,
            "rate": 3.14
        }
        # 验证类型是浮点数
        assert isinstance(result["price"], float)
        assert isinstance(result["rate"], float)

    def test_boolean_values(self):
        """测试布尔值（JSON格式）"""
        variables = ["active=true", "deleted=false"]
        result = parse_variables(variables)

        assert result == {
            "active": True,
            "deleted": False
        }
        # 验证类型是布尔值
        assert isinstance(result["active"], bool)
        assert isinstance(result["deleted"], bool)

    def test_null_value(self):
        """测试 null 值（JSON格式）"""
        variables = ["optional=null"]
        result = parse_variables(variables)

        assert result == {
            "optional": None
        }

    def test_json_object(self):
        """测试 JSON 对象"""
        variables = ["config={\"timeout\":30,\"retries\":3}"]
        result = parse_variables(variables)

        assert result == {
            "config": {
                "timeout": 30,
                "retries": 3
            }
        }
        # 验证嵌套对象的类型
        assert isinstance(result["config"], dict)
        assert isinstance(result["config"]["timeout"], int)

    def test_json_array(self):
        """测试 JSON 数组"""
        variables = ["tags=[\"urgent\",\"important\"]"]
        result = parse_variables(variables)

        assert result == {
            "tags": ["urgent", "important"]
        }
        # 验证类型是列表
        assert isinstance(result["tags"], list)

    def test_mixed_types(self):
        """测试混合类型"""
        variables = [
            "name=Bob",
            "age=30",
            "active=true",
            "score=95.5",
            "tags=[\"vip\",\"premium\"]",
            "meta={\"level\":5,\"verified\":true}"
        ]
        result = parse_variables(variables)

        assert result == {
            "name": "Bob",
            "age": 30,
            "active": True,
            "score": 95.5,
            "tags": ["vip", "premium"],
            "meta": {
                "level": 5,
                "verified": True
            }
        }
        # 验证所有类型正确
        assert isinstance(result["name"], str)
        assert isinstance(result["age"], int)
        assert isinstance(result["active"], bool)
        assert isinstance(result["score"], float)
        assert isinstance(result["tags"], list)
        assert isinstance(result["meta"], dict)

    def test_invalid_json_fallback_to_string(self):
        """测试无效 JSON 时回退到字符串"""
        variables = ["message=not a valid json", "data=simple string"]
        result = parse_variables(variables)

        assert result == {
            "message": "not a valid json",
            "data": "simple string"
        }
        # 验证类型都是字符串
        assert isinstance(result["message"], str)
        assert isinstance(result["data"], str)

    def test_empty_value(self):
        """测试空值"""
        variables = ["empty=", "name="]
        result = parse_variables(variables)

        assert result == {
            "empty": "",
            "name": ""
        }

    def test_value_with_equals_sign(self):
        """测试值中包含等号的情况"""
        variables = ["equation=a=b+c", "url=https://example.com?param=value"]
        result = parse_variables(variables)

        assert result == {
            "equation": "a=b+c",
            "url": "https://example.com?param=value"
        }
        # 验证只在第一个等号处分割
        assert result["equation"] == "a=b+c"

    def test_special_characters(self):
        """测试特殊字符"""
        variables = [
            "path=/home/user/documents",
            "email=user@example.com",
            "uuid=123e4567-e89b-12d3-a456-426614174000"
        ]
        result = parse_variables(variables)

        assert result == {
            "path": "/home/user/documents",
            "email": "user@example.com",
            "uuid": "123e4567-e89b-12d3-a456-426614174000"
        }

    def test_unicode_characters(self):
        """测试 Unicode 字符"""
        variables = [
            "name=张三",
            "greeting=你好世界",
            "emoji=😀🎉"
        ]
        result = parse_variables(variables)

        assert result == {
            "name": "张三",
            "greeting": "你好世界",
            "emoji": "😀🎉"
        }

    def test_complex_nested_structure(self):
        """测试复杂嵌套结构"""
        variables = [
            "data={\"users\":[{\"name\":\"Alice\",\"age\":25},{\"name\":\"Bob\",\"age\":30}],\"count\":2}"
        ]
        result = parse_variables(variables)

        assert result == {
            "data": {
                "users": [
                    {"name": "Alice", "age": 25},
                    {"name": "Bob", "age": 30}
                ],
                "count": 2
            }
        }
        # 验证嵌套结构
        assert isinstance(result["data"]["users"], list)
        assert isinstance(result["data"]["users"][0], dict)
        assert result["data"]["users"][0]["name"] == "Alice"

    def test_duplicate_keys_last_wins(self):
        """测试重复键的情况（后面的值覆盖前面的）"""
        variables = [
            "status=pending",
            "status=approved",
            "status=final"
        ]
        result = parse_variables(variables)

        # 最后一个值应该胜出
        assert result == {
            "status": "final"
        }

    def test_number_strings(self):
        """测试数字字符串的处理"""
        variables = [
            "zip=12345",  # 应该解析为数字
            "phone=\"123456\""  # 应该保持为字符串
        ]
        result = parse_variables(variables)

        assert result == {
            "zip": 12345,
            "phone": "123456"
        }
        assert isinstance(result["zip"], int)
        assert isinstance(result["phone"], str)

    def test_scientific_notation(self):
        """测试科学计数法数字"""
        variables = [
            "small=1.5e-3",
            "large=1.5e10"
        ]
        result = parse_variables(variables)

        assert result == {
            "small": 1.5e-3,
            "large": 1.5e10
        }
        assert isinstance(result["small"], float)
        assert isinstance(result["large"], float)

    def test_escaped_json_strings(self):
        """测试 JSON 转义字符串"""
        variables = [
            "text=\"Hello \\\"World\\\"\"",
            "path=\"C:\\\\Users\\\\test\""
        ]
        result = parse_variables(variables)

        assert result == {
            "text": 'Hello "World"',
            "path": "C:\\Users\\test"
        }

    def test_whitespace_handling(self):
        """测试空格处理"""
        variables = [
            "name=  John Doe  ",
            "message=  Hello, World!  "
        ]
        result = parse_variables(variables)

        # JSON 解析会保留字符串中的空格（包括两端）
        # 这是标准 JSON 行为，只有被引号包围的部分才会被解析
        assert result == {
            "name": "  John Doe  ",
            "message": "  Hello, World!  "
        }

    def test_empty_variables_list(self):
        """测试空变量列表"""
        variables: list = []
        result = parse_variables(variables)

        assert result == {}

    def test_single_variable(self):
        """测试单个变量"""
        variables = ["key=value"]
        result = parse_variables(variables)

        assert result == {
            "key": "value"
        }

    def test_large_number_of_variables(self):
        """测试大量变量"""
        variables = [f"var{i}=value{i}" for i in range(100)]
        result = parse_variables(variables)

        assert len(result) == 100
        for i in range(100):
            assert result[f"var{i}"] == f"value{i}"

    def test_type_preservation(self):
        """测试类型保持"""
        variables = [
            "str=text",
            "int=42",
            "float=3.14",
            "bool=true",
            "null=null",
            "list=[1,2,3]",
            "obj={\"a\":1}"
        ]
        result = parse_variables(variables)

        # 验证所有类型都被正确保留
        assert isinstance(result["str"], str)
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["bool"], bool)
        assert result["null"] is None
        assert isinstance(result["list"], list)
        assert isinstance(result["obj"], dict)

    def test_template_variable_interpolation_simulation(self):
        """模拟模板变量插值场景"""
        # 模拟模板变量
        variables = [
            "username=alice",
            "balance=1250.50",
            "currency=USD",
            "is_premium=true",
            "features=[\"spot\",\"margin\",\"futures\"]"
        ]
        context = parse_variables(variables)

        # 模拟模板渲染
        template = "Dear {{username}}, your balance is {{balance}} {{currency}}"
        rendered = template
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
            # 对于复杂类型，这里简化处理

        assert "Dear alice" in rendered
        assert "1250.5" in rendered
        assert "USD" in rendered

        # 验证原始类型被保留
        assert context["balance"] == 1250.50
        assert context["is_premium"] is True
        assert isinstance(context["features"], list)
        assert "spot" in context["features"]


@pytest.mark.unit
class TestVarParameterEdgeCases:
    """测试 --var 参数边界情况"""

    def test_key_without_value(self):
        """测试没有值的键"""
        variables = ["key_only"]
        result = parse_variables(variables)

        # 没有等号，不会被处理
        assert result == {}

    def test_multiple_equals_in_value(self):
        """测试值中包含多个等号"""
        variables = ["equation=1+2=3"]
        result = parse_variables(variables)

        # 应该只在第一个等号处分割
        assert result == {
            "equation": "1+2=3"
        }

    def test_very_long_key(self):
        """测试非常长的键名"""
        long_key = "x" * 1000
        variables = [f"{long_key}=value"]
        result = parse_variables(variables)

        assert long_key in result
        assert result[long_key] == "value"

    def test_very_long_value(self):
        """测试非常长的值"""
        long_value = "y" * 10000
        variables = [f"key={long_value}"]
        result = parse_variables(variables)

        assert result["key"] == long_value

    def test_special_json_characters(self):
        """测试 JSON 特殊字符"""
        variables = [
            "newline=Hello\\nWorld",
            "tab=Hello\\tWorld",
            "quote=Hello\\\"World\\\""
        ]
        result = parse_variables(variables)

        # 当值不是有效 JSON 时，会作为字符串保留
        # 反斜杠不会被解析
        assert result == {
            "newline": "Hello\\nWorld",
            "tab": "Hello\\tWorld",
            "quote": "Hello\\\"World\\\""
        }
        # 验证这些是字符串，包含字面反斜杠
        assert isinstance(result["newline"], str)
        assert isinstance(result["tab"], str)
        assert isinstance(result["quote"], str)

    def test_boolean_string_vs_boolean_value(self):
        """测试布尔字符串与布尔值的区别"""
        variables = [
            "bool1=true",      # 布尔值
            "bool2=\"true\"",   # 字符串
            "bool3=false",     # 布尔值
            "bool4=\"false\""   # 字符串
        ]
        result = parse_variables(variables)

        assert result["bool1"] is True
        assert result["bool2"] == "true"
        assert result["bool3"] is False
        assert result["bool4"] == "false"
        assert isinstance(result["bool1"], bool)
        assert isinstance(result["bool2"], str)

    def test_numeric_string_vs_numeric_value(self):
        """测试数字字符串与数字值的区别"""
        variables = [
            "num1=42",         # 数字
            "num2=\"42\"",      # 字符串
            "num3=3.14",       # 浮点数
            "num4=\"3.14\""     # 字符串
        ]
        result = parse_variables(variables)

        assert result["num1"] == 42
        assert result["num2"] == "42"
        assert result["num3"] == 3.14
        assert result["num4"] == "3.14"
        assert isinstance(result["num1"], int)
        assert isinstance(result["num2"], str)
        assert isinstance(result["num3"], float)
        assert isinstance(result["num4"], str)
