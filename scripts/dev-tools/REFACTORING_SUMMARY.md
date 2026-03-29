# 测试重构总结

## 重构概述

本次重构将 `test/database/`、`test/lab/`、`test/notifiers/`、`test/performance/` 目录下的测试文件从 `unittest.TestCase` 迁移到 `pytest` 框架，采用最佳实践。

## 重构要点

### 1. 使用 Fixtures 共享测试资源

- **`conftest.py`** 文件定义共享的 fixtures
- 使用 `@pytest.fixture` 装饰器创建可重用的测试资源
- Fixture 作用域：`function`（默认）、`class`、`module`、`session`

```python
@pytest.fixture
def mock_portfolio():
    """Mock Portfolio实例."""
    portfolio = Mock()
    portfolio.uuid = "test_portfolio_uuid"
    return portfolio
```

### 2. 参数化测试减少重复代码

使用 `@pytest.mark.parametrize` 装饰器实现数据驱动测试：

```python
@pytest.mark.parametrize("direction,expected_name", [
    (DIRECTION_TYPES.LONG, "LONG"),
    (DIRECTION_TYPES.SHORT, "SHORT"),
])
def test_signal_direction_enum(self, direction, expected_name):
    assert direction.name == expected_name
```

### 3. 使用标记分类测试

使用 `@pytest.mark.*` 标记进行测试分类：

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.database` - 数据库测试
- `@pytest.mark.slow` - 慢速测试

### 4. 清晰的测试类分组

按功能模块组织测试类：

```python
@pytest.mark.lab
@pytest.mark.sizer
class TestBaseSizerConstruction:
    """测试BaseSizer类的构造和初始化."""
```

## 重构文件清单

### test/database/ 目录

| 文件 | 说明 |
|------|------|
| `conftest.py` | 数据库测试共享 fixtures |
| `test_demo_pytest.py` | 示例测试（pytest版） |
| `drivers/test_clickdriver_pytest.py` | ClickHouse驱动测试 |
| `drivers/test_mysqldriver_pytest.py` | MySQL驱动测试 |
| `drivers/test_base_driver_pytest.py` | 基础驱动测试 |

### test/lab/ 目录

| 文件 | 说明 |
|------|------|
| `conftest.py` | 实验室测试共享 fixtures |
| `test_signal_base_pytest.py` | Signal基础测试 |
| `test_sizer_base_pytest.py` | Sizer基础测试 |
| `test_selector_base_pytest.py` | Selector基础测试 |

### test/notifiers/ 目录

| 文件 | 说明 |
|------|------|
| `test_mail_pytest.py` | 邮件通知测试 |
| `test_beep_pytest.py` | 声音通知测试 |
| `test_telegram_pytest.py` | Telegram通知测试 |

### test/performance/ 目录

| 文件 | 说明 |
|------|------|
| `conftest.py` | 性能测试共享 fixtures |
| `test_servicehub_performance_optimized.py` | ServiceHub性能测试（优化版） |
| `test_backtest_benchmark_optimized.py` | 回测基准测试（优化版） |

## 使用方法

### 运行所有测试

```bash
pytest test/
```

### 运行特定类型的测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"
```

### 运行特定目录的测试

```bash
# 运行数据库测试
pytest test/database/

# 运行实验室测试
pytest test/lab/

# 运行性能测试
pytest test/performance/
```

### 运行特定标记的测试

```bash
# 运行ClickHouse相关测试
pytest -m clickhouse

# 运行策略测试
pytest -m strategy

# 运行性能测试
pytest -m performance
```

### 运行特定文件

```bash
pytest test/database/test_demo_pytest.py
```

## 测试命名约定

### 文件命名

- 测试文件：`test_*.py` 或 `*_test.py`
- 新重构文件：`test_*_pytest.py`（与原文件区分）

### 类命名

- 测试类：`Test*`
- 使用描述性名称，如 `TestSignalConstruction`

### 方法命名

- 测试方法：`test_*`
- 使用描述性名称，如 `test_signal_initialization_with_direction`

## Pytest vs Unittest 对比

| 特性 | Unittest | Pytest |
|------|----------|--------|
| 测试类 | 继承 `unittest.TestCase` | 普通类，无需继承 |
| 断言 | `self.assertEqual()` | `assert` 语句 |
| Setup | `setUp()`, `tearDown()` | `@pytest.fixture` |
| 参数化 | 需要手动实现 | `@pytest.mark.parametrize` |
| 标记 | 需要手动实现 | `@pytest.mark.*` |
| 跳过测试 | `@unittest.skip()` | `@pytest.mark.skip()` |
| Fixture | 无内置支持 | 强大的fixture系统 |

## 最佳实践

### 1. 使用描述性的测试名称

```python
# 好的命名
def test_signal_initialization_with_long_direction():
    pass

# 不好的命名
def test_1():
    pass
```

### 2. 使用fixture进行设置和清理

```python
@pytest.fixture
def database():
    db = create_database()
    yield db
    cleanup_database(db)
```

### 3. 使用参数化减少重复

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_multiply_by_two(input, expected):
    assert input * 2 == expected
```

### 4. 使用标记组织测试

```python
@pytest.mark.unit
def test_fast_test():
    pass

@pytest.mark.slow
def test_slow_test():
    pass
```

## 注意事项

1. **数据库测试**：运行前必须启用调试模式
   ```bash
   ginkgo system config set --debug on
   ```

2. **性能测试**：标记为 `@pytest.mark.slow`，默认不运行

3. **集成测试**：需要相应的数据库/服务可用

4. **原测试文件**：保留原有文件，新文件使用 `_pytest` 后缀

## 迁移指南

如果你想继续迁移其他测试文件：

1. **导入pytest**
   ```python
   import pytest
   from unittest.mock import Mock, patch
   ```

2. **移除unittest.TestCase继承**
   ```python
   # 旧：class TestSignal(unittest.TestCase):
   # 新：
   class TestSignal:
   ```

3. **替换setup/tearDown为fixtures**
   ```python
   @pytest.fixture
   def setup_data(self):
       data = create_data()
       yield data
       cleanup_data(data)
   ```

4. **替换断言方法**
   ```python
   # 旧：self.assertEqual(a, b)
   # 新：assert a == b
   ```

5. **添加适当的标记**
   ```python
   @pytest.mark.unit
   def test_something():
       pass
   ```

## 配置文件

重构后的测试使用 `pytest.refactored.ini` 配置文件，包含：

- 测试发现模式
- 自定义标记定义
- 日志配置
- 输出格式

要使用此配置：
```bash
pytest -c pytest.refactored.ini
```

或重命名为 `pytest.ini` 使用默认配置。

## 下一步

1. **逐步迁移**：继续迁移其他测试目录
2. **覆盖率分析**：添加 pytest-cov 进行覆盖率分析
3. **CI集成**：配置CI/CD管道自动运行测试
4. **性能监控**：添加性能基准测试的历史追踪

## 参考资料

- [Pytest文档](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest参数化](https://docs.pytest.org/en/stable/parametrize.html)
- [Pytest标记](https://docs.pytest.org/en/stable/mark.html)
