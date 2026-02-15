# 测试文件重构指南

本文档提供了 Ginkgo 项目测试文件的重构指南，确保所有测试都遵循 pytest 最佳实践。

## 重构目标

1. **使用 pytest fixtures** 替代 setUp/tearDown 方法
2. **使用参数化测试** 减少重复代码
3. **使用 pytest.mark 标记** 进行测试分类
4. **使用 pytest 原生断言** 替代 unittest 断言方法
5. **补全边界测试** 确保全面的测试覆盖

## 重构步骤

### 步骤 1: 识别需要重构的测试

查找使用以下模式的测试文件：
- `import unittest`
- `class TestXXX(unittest.TestCase):`
- `def setUp(self):`
- `self.assertXxx(...)`

### 步骤 2: 创建共享 fixtures

在相应目录创建 `conftest.py` 文件，添加可复用的 fixtures：

```python
@pytest.fixture
def test_entity():
    """创建测试实体"""
    entity = Entity()
    entity.code = "TEST001"
    entity.value = 100
    return entity

@pytest.fixture
def base_test_data():
    """基础测试数据"""
    return {
        "key1": "value1",
        "key2": "value2"
    }
```

### 步骤 3: 转换测试类

将 unittest.TestCase 类转换为普通类：

**重构前:**
```python
class TestOrder(unittest.TestCase):
    def setUp(self):
        self.order = Order(code="TEST001", volume=100)

    def test_volume(self):
        self.assertEqual(self.order.volume, 100)
```

**重构后:**
```python
@pytest.mark.unit
@pytest.mark.order
class TestOrder:
    @pytest.fixture
    def order(self):
        return Order(code="TEST001", volume=100)

    def test_volume(self, order):
        assert order.volume == 100
```

### 步骤 4: 使用参数化测试

使用 `@pytest.mark.parametrize` 减少重复测试：

**重构前:**
```python
def test_volume_100():
    assert calculate_size(100) == 100

def test_volume_200():
    assert calculate_size(200) == 200

def test_volume_500():
    assert calculate_size(500) == 500
```

**重构后:**
```python
@pytest.mark.parametrize("volume,expected", [
    (100, 100),
    (200, 200),
    (500, 500),
])
def test_calculate_size(volume, expected):
    assert calculate_size(volume) == expected
```

### 步骤 5: 使用 pytest 断言

替换 unittest 断言方法：

**重构前:**
```python
self.assertEqual(a, b)
self.assertTrue(x > 0)
self.assertRaises(ValueError, func)
```

**重构后:**
```python
assert a == b
assert x > 0
with pytest.raises(ValueError):
    func()
```

### 步骤 6: 添加测试标记

为测试添加适当的标记：

```python
@pytest.mark.unit
@pytest.mark.backtest
@pytest.mark.bar
class TestBarCalculations:
    """测试 Bar 计算功能"""
    pass
```

常用标记：
- `unit`: 单元测试
- `integration`: 集成测试
- `slow`: 慢速测试
- `database`: 数据库测试
- `backtest`: 回测测试
- `trading`: 交易测试
- `risk`: 风控测试
- `bar`: Bar 实体测试
- `order`: Order 实体测试
- `position`: Position 实体测试
- `signal`: Signal 实体测试

## 已完成的重构

### /test/unit/conftest.py
全局共享 fixtures：
- 时间相关 fixtures
- 股票代码 fixtures
- 核心实体 fixtures (Bar, Order, Position, Signal)
- 投资组合信息 fixtures
- Mock 对象 fixtures
- 测试数据生成器 fixtures

### /test/unit/trading/conftest.py
Trading 模块共享 fixtures：
- 测试策略、Sizer、选择器 fixtures
- 信号和事件 fixtures
- 投资组合信息 fixtures

### /test/unit/trading/risk/conftest.py
Risk 模块共享 fixtures：
- 风控管理器 fixtures
- 持仓信息 fixtures
- 价格事件 fixtures

### /test/unit/backtest/conftest.py
Backtest 模块共享 fixtures：
- Bar 数据 fixtures
- Order 和 Position 数据 fixtures
- 测试数据序列 fixtures

### 已重构的测试文件

1. `/test/unit/trading/risk/test_loss_limit_risk_refactored.py`
   - 使用参数化测试
   - 使用 fixtures 替代 setUp
   - 添加清晰的测试类分组
   - 补全边界测试

2. `/test/unit/backtest/test_order_refactored.py`
   - 使用 pytest.mark 标记
   - 参数化测试
   - 使用 fixtures
   - pytest 原生断言

3. `/test/unit/backtest/test_position_refactored.py`
   - 完整的属性测试
   - 操作测试
   - 随机值测试
   - 金融计算测试

4. `/test/unit/backtest/test_bar_refactored.py`
   - 计算属性测试
   - 随机值测试
   - 日期时间处理测试
   - 价格关系验证

## 待重构的测试文件列表

### backtest 目录
- `/test/unit/backtest/test_bar.py` -> 使用重构版本
- `/test/unit/backtest/test_order.py` -> 使用重构版本
- `/test/unit/backtest/test_position.py` -> 使用重构版本
- `/test/unit/backtest/test_tick.py`
- `/test/unit/backtest/test_base_analyzer.py`
- `/test/unit/backtest/test_events.py`
- `/test/unit/backtest/containers/`
- `/test/unit/backtest/indicators/`
- `/test/unit/backtest/risk_managements/`
- `/test/unit/backtest/services/`

### trading 目录
- `/test/unit/trading/risk/test_loss_limit_risk.py` -> 使用重构版本
- `/test/unit/trading/risk/test_profit_target_risk.py`
- `/test/unit/trading/entities/`
- `/test/unit/trading/feeders/`
- `/test/unit/trading/sizer/test_fixed_sizer.py` -> 已是良好示例
- `/test/unit/trading/portfolios/test_portfolio_t1_backtest.py` -> 已是良好示例
- `/test/unit/trading/engines/`
- `/test/unit/trading/selector/`
- `/test/unit/trading/brokers/`

### 其他目录
- `/test/unit/data/`
- `/test/unit/containers/`
- `/test/unit/libs/`
- `/test/unit/livecore/`
- `/test/unit/lab/`
- `/test/unit/notifiers/`
- `/test/unit/service_hub/`

## 重构模式库

### 模式 1: 实体属性测试

```python
@pytest.mark.unit
@pytest.mark.entity_name
class TestEntityNameProperties:
    """EntityName 属性测试"""

    @pytest.fixture
    def entity(self):
        return EntityName(param1="value1", param2="value2")

    def test_property1(self, entity):
        assert entity.property1 == "expected_value1"

    def test_property2(self, entity):
        assert entity.property2 == "expected_value2"
```

### 模式 2: 参数化计算测试

```python
@pytest.mark.unit
@pytest.mark.calculations
class TestCalculations:
    """计算功能测试"""

    @pytest.mark.parametrize("input1,input2,expected", [
        (1, 2, 3),
        (5, 10, 15),
        (100, 200, 300),
    ])
    def test_calculation(self, input1, input2, expected):
        result = calculate(input1, input2)
        assert result == expected
```

### 模式 3: 操作测试

```python
@pytest.mark.unit
@pytest.mark.operations
class TestEntityOperations:
    """实体操作测试"""

    @pytest.fixture
    def entity(self):
        return Entity()

    def test_operation_success(self, entity):
        result = entity.operation()
        assert result is True

    def test_operation_failure(self, entity):
        with pytest.raises(ValueError):
            entity.invalid_operation()
```

### 模式 4: 边界条件测试

```python
@pytest.mark.unit
@pytest.mark.edge_cases
class TestEdgeCases:
    """边界条件测试"""

    @pytest.mark.parametrize("value", [0, -1, -100])
    def test_negative_values(self, value):
        entity = Entity(value=value)
        assert entity.value == value or entity.handle_invalid()

    def test_zero_value(self):
        entity = Entity(value=0)
        result = entity.process()
        assert result == 0
```

## 运行重构后的测试

```bash
# 运行所有单元测试
pytest test/unit/ -v

# 运行特定标记的测试
pytest test/unit/ -m unit -v
pytest test/unit/ -m "not slow" -v

# 运行特定目录的测试
pytest test/unit/trading/ -v
pytest test/unit/backtest/ -v

# 生成覆盖率报告
pytest test/unit/ --cov=ginkgo --cov-report=html
```

## 最佳实践总结

1. **使用 fixtures 共享测试资源**
   - 优先使用 conftest.py 中的 fixtures
   - fixtures 应该是独立的、可组合的

2. **使用参数化测试减少重复**
   - 相同逻辑、不同数据的测试使用参数化
   - 测试数据应该在测试代码中清晰可见

3. **使用清晰的测试类分组**
   - 按功能分组（Construction, Properties, Operations）
   - 使用描述性的测试类名

4. **使用描述性的测试名**
   - `test_operation_under_condition`
   - `test_property_when_state`

5. **使用 pytest 标记**
   - 标记测试类型（unit, integration）
   - 标记功能模块（backtest, trading, risk）
   - 标记测试特征（slow, database）

6. **使用金融精度断言**
   - 使用 `pytest.approx()` 进行浮点比较
   - 使用 `Decimal` 进行金融计算
   - 明确精度要求

7. **补全边界测试**
   - 测试零值、负值、极大值
   - 测试无效输入
   - 测试边界条件

## 下一步行动

1. 逐个目录重构测试文件
2. 先从 `trading` 和 `backtest` 开始
3. 每完成一个目录，运行测试验证
4. 更新本文档记录重构进度
5. 最终删除旧的测试文件（使用 `_refactored` 后缀的文件）
