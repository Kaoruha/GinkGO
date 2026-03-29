# Ginkgo Trading 测试重构说明

## 重构概述

本次重构将 `test/trading/` 目录下的测试文件从 unittest 模式迁移到 pytest 最佳实践，主要改进包括：

### 1. 主要改进

#### Fixture 共享
- 创建共享的 `conftest.py` 文件
- 定义常用测试数据 fixture（sample_bar_data, sample_tick_data, sample_order_data 等）
- 避免在多个测试文件中重复创建相同的测试数据

#### 参数化测试
- 使用 `@pytest.mark.parametrize` 减少重复代码
- 将相似测试用例合并为参数化测试
- 提高测试可维护性和可读性

#### 测试标记
- `@pytest.mark.unit`: 单元测试（不依赖外部资源）
- `@pytest.mark.integration`: 集成测试（需要数据库等）
- `@pytest.mark.financial`: 金融业务逻辑测试
- `@pytest.mark.slow`: 执行时间较长的测试
- `@pytest.mark.tdd`: TDD 测试（测试驱动开发）

#### 测试分组
- 按功能模块分组（Construction, Properties, Calculations, Validation 等）
- 每个测试类专注于一个特定方面
- 清晰的测试方法命名

### 2. 重构文件列表

#### Entities 目录
- `test_bar_refactored.py` - Bar 实体重构测试
- `test_order_refactored.py` - Order 实体重构测试
- `test_signal_refactored.py` - Signal 实体重构测试
- `test_position_refactored.py` - Position 实体重构测试
- `test_tick_refactored.py` - Tick 实体重构测试（待创建）

#### Events 目录
- `test_base_event_refactored.py` - EventBase 重构测试
- `test_event_payload_refactored.py` - Event Payload 重构测试

### 3. 运行测试

```bash
# 运行所有测试
pytest test/trading/

# 只运行单元测试
pytest -m unit test/trading/

# 只运行集成测试
pytest -m integration test/trading/

# 运行特定文件
pytest test/trading/entities/test_bar_refactored.py

# 运行特定测试类
pytest test/trading/entities/test_bar_refactored.py::TestBarConstruction

# 运行特定测试方法
pytest test/trading/entities/test_bar_refactored.py::TestBarConstruction::test_required_parameters

# 查看测试覆盖率
pytest --cov=ginkgo.trading.entities test/trading/entities/

# 生成详细报告
pytest -v test/trading/

# 生成 HTML 报告
pytest --html=report.html test/trading/
```

### 4. 测试命名规范

#### 测试文件
- 使用 `test_<module>_refactored.py` 命名重构后的文件
- 保持与源代码相同的目录结构

#### 测试类
- 使用 `Test<Functionality>` 命名
- 例如：`TestBarConstruction`, `TestOrderProperties`, `TestSignalValidation`

#### 测试方法
- 使用 `test_<scenario>` 或 `test_<feature>_<scenario>` 命名
- 使用描述性名称，说明测试的具体场景

### 5. Fixture 使用示例

```python
def test_with_fixture(sample_bar_data):
    """使用 fixture 的测试"""
    bar = Bar(**sample_bar_data)
    assert bar.code == "000001.SZ"
```

### 6. 参数化测试示例

```python
@pytest.mark.parametrize("direction,expected", [
    (DIRECTION_TYPES.LONG, 1),
    (DIRECTION_TYPES.SHORT, 2)
])
def test_direction_values(direction, expected):
    """测试方向枚举值"""
    assert direction.value == expected
```

### 7. 标记使用示例

```python
@pytest.mark.unit
class TestBarConstruction:
    """单元测试类"""

@pytest.mark.integration
def test_database_operation(ginkgo_config):
    """集成测试"""

@pytest.mark.financial
def test_pnl_calculation():
    """金融业务逻辑测试"""
```

### 8. 断言最佳实践

- 使用 pytest 原生断言（`assert`），不要使用 unittest 的断言方法
- 使用 `pytest.approx()` 进行浮点数比较
- 使用 `pytest.raises()` 进行异常测试
- 提供清晰的错误消息

```python
# 好的做法
assert result == expected, f"结果应该是 {expected}，实际是 {result}"
assert price1 == pytest.approx(price2, rel=1e-3)

# 避免
self.assertEqual(result, expected)  # unittest 风格
```

### 9. 数据库测试规范

- 所有数据库操作测试必须使用 `ginkgo_config` fixture
- 测试前设置 `GCONF.set_debug(True)`
- 测试后恢复原始配置

```python
def test_with_database(ginkgo_config):
    """需要数据库的测试"""
    # 测试代码...
    pass
```

### 10. 下一步工作

- [ ] 重构 `test_tick.py`
- [ ] 重构其他 entities 文件
- [ ] 重构 strategy 目录测试
- [ ] 重构 risk_managements 目录测试
- [ ] 重构 engines 目录测试
- [ ] 重构 portfolios 目录测试
- [ ] 添加更多集成测试
- [ ] 提高测试覆盖率

### 11. 迁移指南

将现有测试迁移到新规范：

1. **导入语句**
   ```python
   # 旧方式
   import unittest
   class TestBar(unittest.TestCase):
       pass

   # 新方式
   import pytest
   class TestBar:
       pass
   ```

2. **Setup/Teardown**
   ```python
   # 旧方式
   def setUp(self):
       self.bar = Bar()

   def tearDown(self):
       self.bar = None

   # 新方式
   @pytest.fixture
   def sample_bar():
       return Bar()
   ```

3. **断言**
   ```python
   # 旧方式
   self.assertEqual(x, y)
   self.assertTrue(x > y)

   # 新方式
   assert x == y
   assert x > y
   ```

4. **运行测试**
   ```python
   # 旧方式
   unittest.main()

   # 新方式（命令行）
   pytest
   ```
