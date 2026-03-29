# pytest重构示例

本文档展示如何将现有的 unittest/TDD 测试重构为 pytest 最佳实践。

## 示例1: 基础模型测试重构

### 重构前 (unittest/TDD风格)

```python
import unittest
from ginkgo.data.models.model_base import MBase

class TestMBase(unittest.TestCase):
    def setUp(self):
        self.model = MBase()

    def test_to_dataframe_excludes_private(self):
        df = self.model.to_dataframe()
        self.assertNotIn('_private_attr', df.columns)

    def test_to_dataframe_excludes_methods(self):
        df = self.model.to_dataframe()
        for col in df.columns:
            self.assertNotIsInstance(getattr(self.model, col), MethodType)
```

### 重构后 (pytest风格)

```python
import pytest
from ginkgo.data.models.model_base import MBase

@pytest.mark.unit
class TestMBaseToDataFrame:
    """测试MBase.to_dataframe()方法"""

    def test_to_dataframe_excludes_private_attributes(self):
        """测试to_dataframe排除私有属性"""
        model = MBase()
        model._private_attr = "should_not_appear"

        df = model.to_dataframe()
        assert '_private_attr' not in df.columns

    def test_to_dataframe_excludes_methods(self):
        """测试to_dataframe排除方法"""
        model = MBase()
        df = model.to_dataframe()

        # 排除内置方法
        for col in df.columns:
            assert not isinstance(getattr(model, col, None), MethodType)
```

## 示例2: 参数化测试重构

### 重构前 (重复代码)

```python
class TestMSourceHandling(unittest.TestCase):
    def test_set_source_with_tushare(self):
        model = MClickBase()
        model.set_source(SOURCE_TYPES.TUSHARE)
        self.assertEqual(model.source, SOURCE_TYPES.TUSHARE.value)

    def test_set_source_with_yahoo(self):
        model = MClickBase()
        model.set_source(SOURCE_TYPES.YAHOOFINANCE)
        self.assertEqual(model.source, SOURCE_TYPES.YAHOOFINANCE.value)

    def test_set_source_with_int(self):
        model = MClickBase()
        model.set_source(1)
        self.assertEqual(model.source, 1)
```

### 重构后 (参数化)

```python
@pytest.mark.unit
class TestMClickBaseSourceHandling:
    """测试MClickBase来源处理"""

    @pytest.mark.parametrize("source_input,expected_value", [
        (SOURCE_TYPES.TUSHARE, SOURCE_TYPES.TUSHARE.value),
        (SOURCE_TYPES.YAHOOFINANCE, SOURCE_TYPES.YAHOOFINANCE.value),
        (1, 1),
        (2, 2),
    ])
    def test_set_source_with_various_inputs(self, source_input, expected_value):
        """测试使用各种输入设置source"""
        model = MClickBase()
        model.set_source(source_input)
        assert model.source == expected_value
```

## 示例3: 使用fixtures重构

### 重构前 (setUp方法)

```python
class TestDatabaseDriver(unittest.TestCase):
    def setUp(self):
        self.driver = ConcreteTestDriver()
        self.mock_engine = Mock()
        self.mock_session = Mock()

    def test_driver_initialization(self):
        self.assertEqual(self.driver.driver_name, "TestDriver")
        self.assertIsNone(self.driver._engine)

    def test_session_creation(self):
        with self.driver.get_session() as session:
            self.assertIsNotNone(session)
```

### 重构后 (pytest fixtures)

```python
@pytest.fixture
def test_driver():
    """测试驱动实例"""
    return ConcreteTestDriver()

@pytest.fixture
def mock_session():
    """模拟会话"""
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session

@pytest.mark.unit
class TestDatabaseDriverConnection:
    """测试数据库驱动连接"""

    def test_driver_initialization(self, test_driver):
        """测试驱动初始化"""
        assert test_driver.driver_name == "TestDriver"
        assert test_driver._engine is None

    def test_session_commit_on_success(self, test_driver, mock_session):
        """测试成功时提交"""
        with test_driver.get_session() as session:
            pass
        mock_session.commit.assert_called_once()
```

## 示例4: 异常测试重构

### 重构前 (unittest风格)

```python
class TestMUpdate(unittest.TestCase):
    def test_update_raises_not_implemented(self):
        model = MClickBase()
        with self.assertRaises(NotImplementedError):
            model.update()

    def test_update_raises_with_message(self):
        model = MClickBase()
        with self.assertRaisesRegex(NotImplementedError, "overload"):
            model.update()
```

### 重构后 (pytest风格)

```python
@pytest.mark.unit
class TestMClickBaseUpdateMethod:
    """测试MClickBase update方法"""

    def test_update_raises_not_implemented(self):
        """测试update方法抛出NotImplementedError"""
        model = MClickBase()
        with pytest.raises(NotImplementedError, match="overload"):
            model.update()

    def test_update_exception_message(self):
        """测试update异常消息"""
        model = MClickBase()
        with pytest.raises(NotImplementedError) as exc_info:
            model.update()
        assert "overload" in str(exc_info.value)
```

## 示例5: 边界测试重构

### 重构前 (多个测试方法)

```python
class TestBoundaryValues(unittest.TestCase):
    def test_negative_price(self):
        model = MBar()
        with self.assertRaises(ValueError):
            model.price = Decimal("-1.00")

    def test_zero_price(self):
        model = MBar()
        with self.assertRaises(ValueError):
            model.price = Decimal("0")

    def test_none_price(self):
        model = MBar()
        with self.assertRaises(ValueError):
            model.price = None
```

### 重构后 (参数化 + 边界数据)

```python
@pytest.fixture
def invalid_prices():
    """无效价格数据"""
    return [
        (Decimal("-1.00"), "negative price"),
        (Decimal("0"), "zero price"),
        (None, "null price"),
        ("invalid", "string price")
    ]

@pytest.mark.unit
class TestMBarPriceValidation:
    """测试MBar价格验证"""

    @pytest.mark.parametrize("price,description", invalid_prices())
    def test_invalid_price_rejected(self, price, description):
        """测试拒绝无效价格"""
        model = MBar()
        with pytest.raises((ValueError, TypeError, AttributeError)):
            model.price = price
```

## 重构检查清单

- [ ] 移除 `unittest.TestCase` 继承
- [ ] 移除 `setUp` 和 `tearDown` 方法
- [ ] 替换 `self.assertXxx` 为 `assert`
- [ ] 替换 `self.assertRaises` 为 `pytest.raises`
- [ ] 创建共享 fixtures 到 conftest.py
- [ ] 使用 `@pytest.mark.parametrize` 减少重复
- [ ] 使用 `@pytest.mark.unit/integration` 标记
- [ ] 添加描述性文档字符串
- [ ] 使用清晰的测试类/方法命名
- [ ] 添加类型提示到 fixtures

## 常见问题

### Q1: 如何处理测试依赖?

**重构前:**
```python
def test_step1(self):
    self.result = 1 + 1

def test_step2(self):
    self.assertEqual(self.result, 2)  # 依赖test_step1
```

**重构后:**
```python
@pytest.fixture
def calculation_result():
    """提供计算结果"""
    return 1 + 1

def test_calculation(calculation_result):
    """测试计算结果"""
    assert calculation_result == 2
```

### Q2: 如何模拟数据库?

**重构前:**
```python
@patch('ginkgo.data.models.model_base.DBSession')
def test_database_operation(self, mock_session):
    mock_session.query.return_value = [...]
    result = self.model.query()
    self.assertIsNotNone(result)
```

**重构后:**
```python
@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = Mock()
    session.query.return_value = [...]
    return session

def test_database_operation(mock_db_session):
    """测试数据库操作"""
    result = model.query()
    assert result is not None
```

## 性能优化

### 使用参数化减少重复

```python
# 差: 10个重复测试
for i in range(10):
    def test_number_i(self):
        assert is_valid(i)

# 好: 1个参数化测试
@pytest.mark.parametrize("value", range(10))
def test_numbers_are_valid(self, value):
    assert is_valid(value)
```

### 使用标记分组

```python
# 运行快速测试
pytest -m "not slow" -v

# 仅运行单元测试
pytest -m unit -v

# 运行集成测试
pytest -m integration -v
```
