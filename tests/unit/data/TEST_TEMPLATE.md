# Pytest测试模板

使用此模板快速创建符合pytest最佳实践的测试文件。

## 模板结构

```python
"""
模块/功能名称测试 - Pytest最佳实践

测试范围说明
涵盖主要功能点1、功能点2、功能点3
"""
import pytest
import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.models.your_model import YourModel


# ==================== 测试类1: 构造测试 ====================

@pytest.mark.unit
class TestYourModelConstruction:
    """测试YourModel构造功能"""

    def test_model_can_be_instantiated(self):
        """测试模型可以被实例化"""
        model = YourModel()
        assert model is not None
        assert isinstance(model, YourModel)

    def test_model_has_required_fields(self):
        """测试模型有必需字段"""
        required_fields = ['field1', 'field2', 'field3']
        model = YourModel()
        for field in required_fields:
            assert hasattr(model, field)

    @pytest.mark.parametrize("field,expected_default", [
        ("field1", "default_value"),
        ("field2", 0),
        ("field3", None),
    ])
    def test_field_defaults(self, field, expected_default):
        """测试字段默认值"""
        model = YourModel()
        assert getattr(model, field) == expected_default


# ==================== 测试类2: 字段测试 ====================

@pytest.mark.unit
class TestYourModelFields:
    """测试YourModel字段定义"""

    def test_field1_type(self):
        """测试field1类型"""
        model = YourModel()
        assert isinstance(model.field1, str)

    def test_field2_validation(self):
        """测试field2验证"""
        model = YourModel()
        model.field2 = 100
        assert model.field2 == 100

    @pytest.mark.parametrize("invalid_value", [
        -1,
        0,
        None,
        "invalid",
    ])
    def test_field2_rejects_invalid(self, invalid_value):
        """测试field2拒绝无效值"""
        model = YourModel()
        with pytest.raises((ValueError, TypeError)):
            model.field2 = invalid_value


# ==================== 测试类3: 方法测试 ====================

@pytest.mark.unit
class TestYourModelMethods:
    """测试YourModel方法"""

    def test_method_returns_expected_value(self):
        """测试方法返回期望值"""
        model = YourModel()
        result = model.some_method()
        assert result == "expected"

    def test_method_with_arguments(self):
        """测试带参数的方法"""
        model = YourModel()
        result = model.method_with_args(arg1="value1", arg2=2)
        assert result is not None

    def test_method_raises_on_invalid_input(self):
        """测试无效输入时方法抛出异常"""
        model = YourModel()
        with pytest.raises(ValueError, match="invalid"):
            model.method_with_invalid_input("invalid")


# ==================== 测试类4: 边界测试 ====================

@pytest.mark.unit
class TestYourModelEdgeCases:
    """测试YourModel边界情况"""

    @pytest.mark.parametrize("boundary_value", [
        0,
        1,
        100,
        999999,
    ])
    def test_boundary_values(self, boundary_value):
        """测试边界的值"""
        model = YourModel()
        model.field = boundary_value
        assert model.field == boundary_value

    def test_none_handling(self):
        """测试None值处理"""
        model = YourModel()
        model.field = None
        assert model.field is None

    def test_empty_string_handling(self):
        """测试空字符串处理"""
        model = YourModel()
        model.field = ""
        assert model.field == ""


# ==================== 测试类5: 错误处理 ====================

@pytest.mark.unit
class TestYourModelErrorHandling:
    """测试YourModel错误处理"""

    def test_graceful_error_handling(self):
        """测试优雅的错误处理"""
        model = YourModel()
        # 应该不抛出异常
        result = model.method_that_might_fail()
        assert result is not None

    def test_error_logging(self, mock_logger):
        """测试错误日志记录"""
        model = YourModel()
        model.set_logger(mock_logger)
        model.method_that_logs_errors()
        mock_logger.error.assert_called()


# ==================== 集成测试(可选) ====================

@pytest.mark.integration
class TestYourModelIntegration:
    """测试YourModel集成功能"""

    @pytest.fixture
    def db_session(self, ginkgo_config):
        """数据库会话fixture"""
        from ginkgo.data.drivers import get_driver
        driver = get_driver("mysql")
        with driver.get_session() as session:
            yield session

    def test_database_save(self, db_session):
        """测试数据库保存"""
        model = YourModel()
        model.field1 = "test"
        db_session.add(model)
        db_session.commit()

        # 验证保存
        retrieved = db_session.query(YourModel).first()
        assert retrieved.field1 == "test"


# ==================== 参数化测试模板 ====================

@pytest.mark.unit
class TestYourModelParameterized:
    """测试YourModel参数化场景"""

    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
        ("input3", "output3"),
    ])
    def test_method_with_various_inputs(self, input, expected):
        """测试方法处理各种输入"""
        model = YourModel()
        result = model.process(input)
        assert result == expected


# ==================== Fixtures模板 ====================

@pytest.fixture
def sample_model():
    """示例模型实例"""
    model = YourModel()
    model.field1 = "sample_value"
    model.field2 = 100
    return model

@pytest.fixture
def mock_external_service():
    """模拟外部服务"""
    service = Mock()
    service.call.return_value = "mocked_response"
    return service


# ==================== 使用fixtures ====================

@pytest.mark.unit
class TestYourModelWithFixtures:
    """使用fixtures测试YourModel"""

    def test_with_sample_model(self, sample_model):
        """测试使用示例模型"""
        assert sample_model.field1 == "sample_value"
        assert sample_model.field2 == 100

    def test_with_mocked_service(self, mock_external_service):
        """测试使用模拟服务"""
        model = YourModel()
        result = model.call_external_service(mock_external_service)
        assert result == "mocked_response"
        mock_external_service.call.assert_called_once()
```

## 测试文件创建检查清单

- [ ] 导入必要的模块(pytest, sys, unittest.mock等)
- [ ] 添加项目路径到sys.path
- [ ] 导入被测试的模块
- [ ] 创建测试类(使用Test*命名)
- [ ] 添加适当的标记(@pytest.mark.unit/integration)
- [ ] 使用描述性的类和方法名
- [ ] 添加docstring说明测试目的
- [ ] 使用assert而非unittest断言
- [ ] 使用pytest.raises处理异常
- [ ] 使用fixtures共享测试资源
- [ ] 使用参数化减少重复代码
- [ ] 覆盖正常、边界、错误场景

## 命名规范

### 测试文件
```
test_<module_name>.py
例如: test_base_model_pytest.py
```

### 测试类
```
Test<Functionality><Aspect>
例如: TestMClickBaseConstruction
```

### 测试方法
```
test_<scenario>_<condition>_<expected_result>()
例如: test_uuid_uniqueness()
```

## 标记使用

```python
# 单元测试 - 快速,无数据库依赖
@pytest.mark.unit
class TestModelUnit:
    pass

# 集成测试 - 需要数据库
@pytest.mark.integration
class TestModelIntegration:
    pass

# 慢速测试
@pytest.mark.slow
class TestModelPerformance:
    pass

# 自定义标记
@pytest.mark.financial
class TestFinancialCalculations:
    pass
```

## 运行特定测试

```bash
# 运行特定文件
pytest test/data/models/test_your_model.py -v

# 运行特定类
pytest test/data/models/test_your_model.py::TestYourModelConstruction -v

# 运行特定方法
pytest test/data/models/test_your_model.py::TestYourModelConstruction::test_model_can_be_instantiated -v

# 运行标记的测试
pytest test/data/models/ -m unit -v

# 运行并生成覆盖率
pytest test/data/models/test_your_model.py --cov=src/ginkgo/data/models --cov-report=html
```
