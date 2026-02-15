# Interfaces 测试重构总结

## 已完成的重构

### 1. conftest.py - 共享配置
- **状态**: 已完成
- **特点**:
  - 提供共享的 pytest fixtures
  - 包含 sample_bar_data、sample_portfolio_data、event_factory、portfolio_factory 等
  - 提供协议测试工厂 protocol_factory
  - 提供模拟引擎 mock_engine

### 2. test_mixins/test_event_mixin.py - EventMixin测试
- **状态**: 已完成
- **重构内容**:
  - 使用 @pytest.mark.unit 标记
  - 使用 @pytest.mark.parametrize 参数化测试
  - 清晰的测试类分组
  - 使用 conftest.py 中的共享 fixtures
- **测试类**:
  - TestEventMixinInitialization - 初始化测试
  - TestEventMixinTraceProperties - 追踪属性测试
  - TestEventMixinRelationships - 关联关系测试
  - TestEventMixinProcessingChain - 处理链路测试
  - TestEventMixinTagsAndCategories - 标签和分类测试
  - TestEventMixinPriorityAndWeight - 优先级和权重测试
  - TestEventMixinDebugSupport - 调试支持测试
  - TestEventMixinSummary - 摘要测试
  - TestEventStaticMethods - 静态方法测试
  - TestEventMixinConcurrency - 并发测试
  - TestEventMixinEdgeCases - 边界情况测试

### 3. test_mixins/test_engine_mixin.py - EngineMixin测试
- **状态**: 已完成
- **重构内容**:
  - 完全使用 pytest 风格（移除 unittest）
  - 添加共享 fixtures（mock_engine_base, sample_event）
  - 使用参数化测试
  - 清晰的测试类分组
- **测试类**:
  - TestEngineMixinInitialization - 初始化测试
  - TestEngineMixinEventTracking - 事件追踪测试
  - TestEngineMixinPerformanceMetrics - 性能指标测试
  - TestEngineMixinErrorTracking - 错误追踪测试
  - TestEngineMixinMonitoringThread - 监控线程测试
  - TestEngineMixinDebugMode - 调试模式测试
  - TestEngineMixinEventHandling - 事件处理测试
  - TestEngineMixinStatistics - 统计信息测试
  - TestEngineMixinConcurrency - 并发测试
  - TestEngineMixinResourceManagement - 资源管理测试

### 4. test_protocols/test_portfolio_protocol.py - IPortfolio测试
- **状态**: 已完成
- **重构内容**:
  - 使用 pytest 风格
  - 移除 unittest.TestCase 继承
  - 使用 Mock 对象创建模拟投资组合
  - 参数化测试
- **测试类**:
  - TestIPortfolioProtocolBasic - 基础功能测试
  - TestIPortfolioProtocolValidation - 验证测试
  - TestIPortfolioProtocolComponents - 组件管理测试
  - TestIPortfolioProtocolEdgeCases - 边界情况测试

## 重构模式总结

### 1. Fixtures 使用模式
```python
# 在测试文件中定义特定 fixtures
@pytest.fixture
def custom_fixture():
    return setup_data()

# 使用 conftest.py 中的共享 fixtures
def test_something(sample_bar_data, event_factory):
    event = event_factory.create_price_update_event()
    assert event.code == "000001.SZ"
```

### 2. 参数化测试模式
```python
@pytest.mark.parametrize("param1,param2,expected", [
    (value1, value2, result1),
    (value3, value4, result2),
])
def test_parameterized(self, param1, param2, expected):
    assert calculate(param1, param2) == expected
```

### 3. 测试类组织
```python
@pytest.mark.unit  # 或 @pytest.mark.integration
class TestFeature:
    """功能描述"""

    def test_basic_case(self):
        pass

    def test_edge_case(self):
        pass
```

### 4. Mock 对象使用
```python
from unittest.mock import Mock

def test_with_mock():
    mock_obj = Mock(name="TestMock", method=Mock(return_value=True))
    result = mock_obj.method()
    assert result is True
```

## 待完成的重构

### 1. test_protocols/test_engine_protocol.py
- 需要移除内联工厂类
- 使用 conftest.py 中的共享 fixtures
- 简化 MockEngine 实现

### 2. test_protocols/test_risk_management_protocol.py
- 使用 conftest.py 中的 protocol_factory
- 统一使用 pytest.mark.unit 标记
- 移除重复的 tdd_phase 装饰器

### 3. test_protocols/test_strategy_protocol.py
- 修复导入错误（protocols -> protocols）
- 使用共享 fixtures
- 统一测试风格

## 测试运行

### 运行所有接口测试
```bash
pytest test/interfaces/ -v
```

### 运行特定类型测试
```bash
# 只运行单元测试
pytest test/interfaces/ -m unit -v

# 只运行协议测试
pytest test/interfaces/test_protocols/ -v
```

### 运行特定测试类
```bash
pytest test/interfaces/test_mixins/test_event_mixin.py::TestEventMixinInitialization -v
```

## 最佳实践

### 1. 命名规范
- 测试文件: `test_<module>.py`
- 测试类: `Test<Feature>`
- 测试方法: `test_<specific_scenario>`
- Fixtures: 描述性名称，如 `sample_portfolio_data`

### 2. 标记使用
- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.tdd`: TDD测试
- `@pytest.mark.financial`: 金融业务测试

### 3. 断言风格
```python
# 使用 pytest 原生断言
assert result == expected
assert len(items) > 0
assert "key" in dict

# 使用 pytest.raises 测试异常
with pytest.raises(ValueError):
    function_that_raises()
```

### 4. 文档字符串
每个测试类和测试方法都应有清晰的文档字符串，说明测试目的和场景。

## 重构前后对比

### 重构前（unittest 风格）
```python
class TestEventMixin:
    def setUp(self):
        self.event = TestEvent()

    def test_correlation_id(self):
        event = TestEvent(correlation_id="test")
        assert event.correlation_id == "test"

    def test_causation_id(self):
        event = TestEvent()
        event.causation_id = "cause_123"
        assert event.causation_id == "cause_123"
```

### 重构后（pytest 风格）
```python
@pytest.mark.unit
class TestEventMixinTraceProperties:
    @pytest.mark.parametrize("correlation_id,session_id", [
        ("corr_789", None),
        ("corr_999", "session_123"),
        (None, "session_456"),
        ("corr_multi", "session_multi")
    ])
    def test_correlation_id_management(self, mock_event_base, correlation_id, session_id):
        """测试关联ID管理 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent(correlation_id=correlation_id, session_id=session_id)

        if correlation_id:
            assert event.correlation_id == correlation_id
        if session_id:
            assert event.session_id == session_id
```

## 优势总结

1. **更简洁的代码** - 移除了 setUp/tearDown 样板代码
2. **更好的可读性** - 使用 fixtures 和参数化测试，意图更清晰
3. **更容易维护** - 测试独立运行，不依赖执行顺序
4. **更灵活** - 参数化测试减少重复代码
5. **标准化** - 所有测试遵循相同的 pytest 模式
