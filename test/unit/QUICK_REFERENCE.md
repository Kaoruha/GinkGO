# pytest 测试重构快速参考

## 常用重构模式

### 1. unittest → pytest 转换

**重构前:**
```python
import unittest

class TestOrder(unittest.TestCase):
    def setUp(self):
        self.order = Order(code="TEST001", volume=100)

    def test_volume(self):
        self.assertEqual(self.order.volume, 100)
```

**重构后:**
```python
import pytest

@pytest.mark.unit
@pytest.mark.order
class TestOrder:
    @pytest.fixture
    def order(self):
        return Order(code="TEST001", volume=100)

    def test_volume(self, order):
        assert order.volume == 100
```

### 2. 断言转换

| unittest | pytest |
|----------|--------|
| self.assertEqual(a, b) | assert a == b |
| self.assertTrue(x) | assert x is True |
| self.assertFalse(x) | assert x is False |
| self.assertRaises(Error) | with pytest.raises(Error): |
| self.assertAlmostEqual(a, b) | assert a == pytest.approx(b) |

### 3. 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    (100, 100),
    (200, 200),
    (300, 300),
])
def test_calculation(input, expected):
    result = calculate(input)
    assert result == expected
```

### 4. 使用 Fixtures

```python
# 在测试方法中使用
def test_something(self, fixture_name):
    fixture_name.do_something()

# 在类中使用
class TestSomething:
    def test_method(self, fixture_name):
        fixture_name.do_something()
```

### 5. 测试标记

```python
@pytest.mark.unit
@pytest.mark.entity
@pytest.mark.slow
def test_slow_operation():
    time.sleep(2)
    assert True
```

运行标记测试:
```bash
pytest -m unit
pytest -m "unit and not slow"
pytest -m "risk or strategy"
```

## Fixtures 快速参考

### 全局 fixtures (test/unit/conftest.py)

```python
# 时间
test_timestamp() -> datetime(2024, 1, 15, 9, 30, 0)
test_date() -> datetime(2024, 1, 15).date()

# 股票代码
sample_stock_code() -> "000001.SZ"
sample_stock_codes() -> ["000001.SZ", "000002.SZ", ...]

# 实体
test_bar() -> Bar 对象
test_order() -> Order 对象
test_position() -> Position 对象
test_signal() -> Signal 对象

# 投资组合
base_portfolio_info() -> {"uuid": ..., "cash": ..., "positions": {}}
portfolio_with_position() -> {"uuid": ..., "positions": {"000001.SZ": ...}}
```

### Trading fixtures (test/unit/trading/conftest.py)

```python
test_strategy() -> TestStrategy 对象
test_sizer() -> TestSizer 对象
test_selector() -> TestSelector 对象
long_signal() -> 做多信号
short_signal() -> 做空信号
```

### Backtest fixtures (test/unit/backtest/conftest.py)

```python
standard_bar_data() -> 标准 Bar 数据字典
standard_order_data() -> 标准 Order 数据字典
standard_position_data() -> 标准 Position 数据字典
random_bar_data() -> 随机 Bar 数据
bar_sequence_10days() -> 10天 Bar 序列
```

## 测试命名规范

### 测试文件
- 单元测试: `test_*.py` 或 `*_test.py`
- 重构版本: `test_*_refactored.py`

### 测试类
```python
Test[Entity]Construction      # 构造测试
Test[Entity]Properties         # 属性测试
Test[Entity]Operations         # 操作测试
Test[Entity]Calculations       # 计算测试
Test[Entity]Validation        # 验证测试
Test[Entity]EdgeCases         # 边界测试
```

### 测试方法
```python
test_[operation]                          # 基本操作
test_[operation]_with_[condition]          # 带条件
test_[operation]_when_[state]            # 状态相关
test_[operation]_should_[expected]         # 期望行为
test_[property]_is_[value]                # 属性验证
test_[property]_when_[condition]          # 属性条件
```

## 常用标记

```python
@pytest.mark.unit           # 单元测试
@pytest.mark.integration    # 集成测试
@pytest.mark.slow          # 慢速测试
@pytest.mark.database       # 数据库测试
@pytest.mark.network        # 网络测试
@pytest.mark.backtest      # 回测测试
@pytest.mark.trading       # 交易测试
@pytest.mark.risk          # 风控测试
@pytest.mark.bar           # Bar 测试
@pytest.mark.order         # Order 测试
@pytest.mark.position      # Position 测试
@pytest.mark.signal        # Signal 测试
```

## 常用断言

```python
# 相等性
assert a == b
assert a != b

# 布尔
assert x is True
assert x is False
assert x in [1, 2, 3]
assert x not in [4, 5]

# 数值比较
assert a > b
assert a >= b
assert a < b
assert a <= b
assert a == pytest.approx(b, rel=1e-3)  # 浮点比较
assert a == pytest.approx(b, abs=0.01)

# 异常
with pytest.raises(ValueError):
    raise ValueError
with pytest.raises(ValueError, match="error message"):
    raise ValueError("error message")

# 类型
assert isinstance(x, int)
assert type(x) is int

# 集合
assert x in [1, 2, 3]
assert "key" in dict_obj
assert len(list) == 3
```

## 参数化测试模式

### 单一参数
```python
@pytest.mark.parametrize("value", [1, 2, 3, 4, 5])
def test_positive_values(value):
    assert value > 0
```

### 多个参数
```python
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (2, 3, 5),
    (5, 7, 12),
])
def test_addition(a, b, expected):
    assert a + b == expected
```

### 组合参数化
```python
@pytest.mark.parametrize("direction", [LONG, SHORT])
@pytest.mark.parametrize("volume", [100, 200, 500])
def test_order_creation(direction, volume):
    order = Order(direction=direction, volume=volume)
    assert order.direction == direction
    assert order.volume == volume
```

## Fixtures 作用域

```python
@pytest.fixture              # function 作用域 (默认)
@pytest.fixture(scope="function")  # 每个测试函数
@pytest.fixture(scope="class")      # 每个测试类
@pytest.fixture(scope="module")     # 每个模块
@pytest.fixture(scope="session")    # 每个会话
```

## 跳过和预期失败

```python
@pytest.mark.skip("暂时跳过")
def test_feature_not_ready():
    pass

@pytest.mark.skipif(condition, reason="条件不满足")
def test_conditional():
    pass

@pytest.mark.xfail(reason="已知问题")
def test_known_issue():
    assert False
```

## 测试运行命令

```bash
# 运行所有测试
pytest

# 运行指定文件
pytest test_file.py

# 运行指定类
pytest test_file.py::TestClass

# 运行指定方法
pytest test_file.py::TestClass::test_method

# 详细输出
pytest -v

# 停止在第一个失败
pytest -x

# 显示本地变量
pytest -l

# 显示慢速测试
pytest --durations=10

# 生成覆盖率报告
pytest --cov=ginkgo --cov-report=html
```

## 调试技巧

```python
# 在测试中暂停
def test_something():
    import pytest; pytest.set_trace()

# 打印调试信息
def test_something(capsys):
    print("debug info")
    captured = capsys.readouterr()
    assert "debug info" in captured.out
```

## 常见问题

### Q: 如何测试异常？
```python
with pytest.raises(ValueError) as exc_info:
    raise ValueError("error message")
assert str(exc_info.value) == "error message"
```

### Q: 如何测试日志？
```python
def test_logging(caplog):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("test message")
    assert "test message" in caplog.text
```

### Q: 如何测试临时文件？
```python
def test_with_tmp_path(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("content")
    assert file.read_text() == "content"
```

### Q: 如何模拟时间？
```python
@pytest.fixture
def mock_time(monkeypatch):
    import time
    monkeypatch.setattr(time, 'time', lambda: 12345)

def test_with_mocked_time(mock_time):
    assert time.time() == 12345
```

## 资源

- pytest 文档: https://docs.pytest.org/
- 重构指南: `REFACTORING_GUIDE.md`
- 进度跟踪: `REFACTORING_PROGRESS.md`
