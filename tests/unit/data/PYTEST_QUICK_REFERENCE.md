# Pytest最佳实践快速参考

## 命令参考

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest test_file.py

# 运行特定类
pytest test_file.py::TestClass

# 运行特定方法
pytest test_file.py::TestClass::test_method

# 运行标记的测试
pytest -m unit
pytest -m integration
pytest -m "not slow"

# 详细输出
pytest -v

# 静默模式
pytest -q

# 停在第一个失败
pytest -x

# 失败后继续
pytest --maxfail=3

# 覆盖率
pytest --cov=src --cov-report=html

# 并行运行
pytest -n auto

# 仅收集测试
pytest --collect-only
```

## Fixtures

```python
# 基本fixture
@pytest.fixture
def resource():
    return setup_resource()

# 使用fixture
def test_something(resource):
    assert resource is not None

# fixture作用域
@pytest.fixture(scope="session")
def session_resource():
    return setup()

# fixture参数化
@pytest.fixture(params=[1, 2, 3])
def param_fixture(request):
    return request.param
```

## 参数化

```python
# 基本参数化
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
])
def test_double(input, expected):
    assert double(input) == expected

# 多参数化
@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [3, 4])
def test_multiply(x, y):
    assert x * y > 0
```

## 标记

```python
# 定义标记
@pytest.mark.unit
def test_unit():
    pass

@pytest.mark.integration
def test_integration():
    pass

# 自定义标记
@pytest.mark.slow
def test_slow():
    pass

# 多个标记
@pytest.mark.unit
@pytest.mark.database
def test_db():
    pass
```

## 断言

```python
# 基本断言
assert a == b
assert a in [1, 2, 3]
assert a is not None
assert isinstance(a, str)
assert a > 0

# 异常断言
with pytest.raises(ValueError):
    raise ValueError()

# 异常消息
with pytest.raises(ValueError, match="invalid"):
    raise ValueError("invalid input")

# 警告断言
with pytest.warns(DeprecationWarning):
    deprecated_function()
```

## Mock

```python
# 基本mock
from unittest.mock import Mock, patch

@patch('module.function')
def test_with_mock(mock_func):
    mock_func.return_value = 42
    result = module.function()
    assert result == 42

# fixture mock
@pytest.fixture
def mock_service():
    service = Mock()
    service.call.return_value = "result"
    return service

def test_with_fixture(mock_service):
    result = mock_service.call()
    assert result == "result"
```

## 跳过

```python
# 条件跳过
@pytest.mark.skipif(sys.version_info < (3, 8), reason="需要3.8+")
def test_feature():
    pass

# 始终跳过
@pytest.mark.skip("等待修复")
def test_broken():
    pass

# 跳过异常
@pytest.mark.xfail
def test_known_failure():
    assert False
```

## Hook

```python
# conftest.py

def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line(
        "markers", "unit: 单元测试"
    )

def pytest_collection_modifyitems(config, items):
    """修改收集的测试"""
    for item in items:
        if "slow" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
```

## 最佳实践

### DO ✅

```python
# 使用fixtures
@pytest.fixture
def db():
    return setup_db()

def test_query(db):
    assert db.query() is not None

# 参数化
@pytest.mark.parametrize("x,y", [(1,2), (3,4)])
def test_add(x, y):
    assert x + y > 0

# 描述性名称
def test_user_login_with_invalid_credentials_raises_error():
    pass

# 使用assert
assert result == expected
```

### DON'T ❌

```python
# 不要使用setUp
def setUp(self):
    self.db = setup_db()

# 不要使用unittest断言
self.assertEqual(result, expected)

# 不要模糊命名
def test_1():
    pass

# 不要重复代码
def test_add_1_and_2():
    assert add(1, 2) == 3

def test_add_3_and_4():
    assert add(3, 4) == 7
```

## 常用选项

```bash
# 配置文件
pytest.ini
pyproject.toml
setup.cfg
tox.ini

# 常用addopts
addopts =
    -ra           # 显示额外摘要
    -v           # 详细输出
    -q           # 静默模式
    -x           # 首次失败停止
    --tb=short   # 短回溯
    --strict-markers  # 严格标记
```

## 调试

```bash
# 失败时进入pdb
pytest --pdb

# 失败时进入ipdb
pytest --ipdb

# 测试开始时进入pdb
pytest --trace

# 打印输出
pytest -s

# 捕获日志
pytest --log-cli-level=DEBUG
```

## 性能

```bash
# 最慢10个测试
pytest --durations=10

# 并行运行
pytest -n auto

# 分布测试
pytest --dist=load

# 仅重跑失败
pytest --lf

# 先运行失败
pytest --ff
```
