# 数据模型和驱动测试重构指南

## 重构概述

本次重构将 `test/data/models/` 和 `test/data/drivers/` 目录下的测试文件从 unittest/TDD 模式迁移到 pytest 最佳实践。

## 重构要点

### 1. 使用 pytest fixtures 共享测试资源

**Models conftest.py** 提供共享fixtures:
- `sample_uuid` - 示例UUID
- `sample_timestamp` - 示例时间戳
- `sample_bar_data` - 示例K线数据
- `sample_position_data` - 示例持仓数据
- `mock_database_session` - 模拟数据库会话
- `boundary_values` - 边界值测试数据

**Drivers conftest.py** 提供共享fixtures:
- `mock_logger` - 模拟日志器
- `mock_engine` - 模拟数据库引擎
- `connection_stats` - 连接统计信息
- `error_scenarios` - 错误场景
- `thread_pool` - 线程池

### 2. 参数化测试减少重复代码

```python
@pytest.mark.parametrize("attr,value,expected_type", [
    ("string_attr", "test_value", str),
    ("int_attr", 42, int),
    ("float_attr", 3.14, float),
])
def test_to_dataframe_handles_various_types(self, attr, value, expected_type):
    """测试to_dataframe处理各种数据类型"""
    model = MBase()
    setattr(model, attr, value)
    df = model.to_dataframe()
    assert attr in df.columns
```

### 3. 使用 @pytest.mark.unit 和 @pytest.mark.integration 标记

```python
@pytest.mark.unit
class TestMBaseConstruction:
    """单元测试 - 不依赖数据库"""

@pytest.mark.integration
class TestMBaseDatabaseOperations:
    """集成测试 - 需要数据库连接"""
```

### 4. 清晰的测试类分组

测试类按功能分组：
- `TestXxxConstruction` - 构造测试
- `TestXxxFields` - 字段测试
- `TestXxxMethods` - 方法测试
- `TestXxxEdgeCases` - 边界测试
- `TestXxxErrorHandling` - 错误处理

### 5. 补全边界测试

```python
@pytest.mark.parametrize("invalid_source", [
    "invalid_string",
    9999,
    -9999,
])
def test_invalid_source_handling(self, invalid_source):
    """测试无效source处理"""
    model = MClickBase(source=invalid_source)
    assert model.source == -1
```

## 重构后的文件结构

### Models 测试文件

| 原文件 | 新文件 | 说明 |
|--------|--------|------|
| test_base_model_comprehensive.py | test_base_model_pytest.py | MBase基础模型测试 |
| test_clickbase_model_comprehensive.py | test_clickbase_model_pytest.py | MClickBase模型测试 |
| test_mysqlbase_model_comprehensive.py | test_mysqlbase_model_pytest.py | MMysqlBase模型测试 |
| test_specific_models_comprehensive.py | test_specific_models_pytest.py | 具体业务模型测试 |
| test_position_model.py | test_position_model_pytest.py | Position模型测试 |
| test_modelbase_query_template_comprehensive.py | test_modelbase_query_pytest.py | 查询模板测试 |

### Drivers 测试文件

| 原文件 | 新文件 | 说明 |
|--------|--------|------|
| test_base_driver_comprehensive.py | test_base_driver_pytest.py | 基础驱动测试 |
| test_clickhouse_driver_comprehensive.py | test_clickhouse_driver_pytest.py | ClickHouse驱动测试 |
| test_mysql_driver_comprehensive.py | test_mysql_driver_pytest.py | MySQL驱动测试 |
| test_redis_driver_comprehensive.py | test_redis_driver_pytest.py | Redis驱动测试 |
| test_mongodb_driver_comprehensive.py | test_mongodb_driver_pytest.py | MongoDB驱动测试 |

## 运行测试

### 运行所有单元测试
```bash
pytest test/data/models/ -m unit -v
pytest test/data/drivers/ -m unit -v
```

### 运行特定测试文件
```bash
pytest test/data/models/test_base_model_pytest.py -v
pytest test/data/drivers/test_base_driver_pytest.py -v
```

### 运行特定测试类
```bash
pytest test/data/models/test_base_model_pytest.py::TestMBaseConstruction -v
```

### 运行特定测试方法
```bash
pytest test/data/models/test_base_model_pytest.py::TestMBaseConstruction::test_mbase_can_be_instantiated -v
```

### 运行集成测试(需要数据库)
```bash
pytest test/data/models/ -m integration -v
pytest test/data/drivers/ -m integration -v
```

### 生成覆盖率报告
```bash
pytest test/data/models/ --cov=src/ginkgo/data/models --cov-report=html
pytest test/data/drivers/ --cov=src/ginkgo/data/drivers --cov-report=html
```

## pytest最佳实践

### 1. 使用 assert 而非 unittest 断言
```python
# ✅ 正确: pytest 风格
assert model.uuid is not None
assert model.source == -1
assert isinstance(model.timestamp, datetime.datetime)

# ❌ 错误: unittest 风格
self.assertIsNotNone(model.uuid)
self.assertEqual(model.source, -1)
self.assertIsInstance(model.timestamp, datetime.datetime)
```

### 2. 使用 pytest.raises 测试异常
```python
# ✅ 正确: pytest 异常测试
with pytest.raises(NotImplementedError, match="need to overload"):
    model.update()

# ❌ 错误: unittest 异常测试
self.assertRaises(NotImplementedError, model.update)
```

### 3. 使用 fixtures 而非 setUp/tearDown
```python
# ✅ 正确: pytest fixture
@pytest.fixture
def sample_model():
    return MClickBase()

def test_model_uuid(sample_model):
    assert sample_model.uuid is not None

# ❌ 错误: unittest setUp
def setUp(self):
    self.model = MClickBase()
```

### 4. 使用参数化测试
```python
# ✅ 正确: 参数化测试
@pytest.mark.parametrize("value,expected", [
    (1, True),
    (0, False),
    (-1, False),
])
def test_is_positive(value, expected):
    assert is_positive(value) is expected

# ❌ 错误: 重复测试
def test_is_positive_1(self):
    assert is_positive(1) is True

def test_is_positive_0(self):
    assert is_positive(0) is False
```

### 5. 使用描述性的测试名称
```python
# ✅ 正确: 描述性名称
def test_uuid_uniqueness(self):
    """测试UUID唯一性"""
    model1 = MClickBase()
    model2 = MClickBase()
    assert model1.uuid != model2.uuid

# ❌ 错误: 模糊名称
def test_1(self):
    """测试"""
    pass
```

## 测试覆盖率目标

- 基础模型 (MBase, MClickBase, MMysqlBase): 90%+
- 具体业务模型: 85%+
- 数据库驱动: 80%+
- 错误处理和边界情况: 100% (关键路径)

## 持续改进

1. 补充更多集成测试用例
2. 添加性能测试
3. 增加并发测试
4. 完善错误场景测试
5. 添加 fuzz 测试

## 注意事项

1. 所有数据库相关测试需要先开启调试模式
2. 集成测试需要实际的数据库连接
3. 测试数据应该与生产数据隔离
4. 清理测试数据避免污染
5. 使用 mock 避免实际数据库操作(单元测试)
