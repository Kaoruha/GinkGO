# 测试文件重构总结

## 重构完成的文件

### 1. test_tick_service.py ✅
- **重构要点**:
  - 使用 `@pytest.fixture` 替代 `setUp`/`tearDown`
  - 使用 `@pytest.mark.parametrize` 进行参数化测试
  - 按功能分组测试类（Construction、Sync、Query、Count、Validation、ErrorHandling、Health、Integration）
  - 使用 `@pytest.mark.unit` 和 `@pytest.mark.db_cleanup` 标记

- **测试类别**:
  - TestTickServiceConstruction: 构造和初始化
  - TestTickServiceSync: 数据同步
  - TestTickServiceQuery: 数据查询
  - TestTickServiceCount: 数据计数
  - TestTickServiceValidation: 数据验证
  - TestTickServiceErrorHandling: 错误处理
  - TestTickServiceHealth: 健康检查
  - TestTickServiceIntegration: 集成测试

### 2. test_engine_service.py ✅
- **重构要点**:
  - 完全从 unittest.TestCase 迁移到 pytest
  - 使用 fixtures 共享 engine_service 实例和 unique_name
  - 参数化测试引擎状态和无效名称
  - 添加状态转换工作流测试

- **测试类别**:
  - TestEngineCRUD: CRUD操作
  - TestEngineStatusManagement: 状态管理
  - TestEnginePortfolioMapping: Portfolio映射
  - TestEngineValidation: 数据验证
  - TestEngineServiceHealth: 健康检查
  - TestEngineServiceIntegration: 集成测试

### 3. test_file_service.py ✅
- **重构要点**:
  - 使用 fixtures 管理文件生命周期
  - 参数化测试不同文件类型和无效数据
  - 测试文件克隆和搜索功能

- **测试类别**:
  - TestFileServiceCRUD: CRUD操作
  - TestFileServiceContent: 内容管理
  - TestFileServiceClone: 克隆功能
  - TestFileServiceSearch: 搜索功能
  - TestFileServiceValidation: 数据验证
  - TestFileServiceHealth: 健康检查
  - TestFileServiceIntegration: 集成测试

## 待重构的文件

### 4. test_redis_service.py
**当前问题**:
- 使用 unittest.TestCase
- setUp/tearDown 方法需要转换为 fixtures
- 缺少参数化测试

**重构计划**:
```python
@pytest.fixture
def redis_service():
    return RedisService()

@pytest.mark.unit
class TestRedisServiceConstruction:
    def test_redis_initialization(self, redis_service):
        assert isinstance(redis_service, RedisService)
```

### 5. test_bar_service.py
**当前问题**:
- 已使用 pytest，但结构不够清晰
- 缺少固定的 fixture 定义
- 测试类命名和组织需要改进

**重构计划**:
- 整合测试类结构
- 添加统一的 fixtures
- 使用参数化减少重复测试

### 6. test_adjustfactor_service.py
**当前问题**:
- 需要检查当前实现
- 可能使用 unittest

**重构计划**:
- 迁移到 pytest
- 添加复权因子特有测试

### 7. test_stockinfo_service.py
**当前问题**:
- 使用 unittest.TestCase
- setUp/tearDown 需要转换

**重构计划**:
```python
@pytest.fixture
def stockinfo_service():
    return container.stockinfo_service()

@pytest.fixture
def sample_stock(stockinfo_service):
    result = stockinfo_service.add(...)
    uuid = result.data["uuid"]
    yield uuid
    stockinfo_service.delete(uuid)
```

### 8. test_signal_tracking_service.py
**当前问题**:
- 需要检查当前实现

**重构计划**:
- 迁移到 pytest
- 添加信号追踪特有测试

### 9. test_param_service.py
**当前问题**:
- 需要检查当前实现

**重构计划**:
- 迁移到 pytest
- 添加参数管理特有测试

### 10. test_kafka_service.py
**当前问题**:
- 需要检查当前实现

**重构计划**:
- 迁移到 pytest
- 添加 Kafka 特有测试

## 重构模式总结

### Fixtures 模式
```python
@pytest.fixture
def service_fixture():
    """获取服务实例"""
    return container.service()

@pytest.fixture
def unique_name():
    """生成唯一名称"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f"test_{timestamp}"

@pytest.fixture
def sample_resource(service_fixture, unique_name):
    """创建示例资源"""
    result = service_fixture.add(name=unique_name)
    assert result.is_success()
    uuid = result.data["uuid"]
    yield uuid
    # 清理
    service_fixture.delete(uuid)
```

### 参数化测试模式
```python
VALID_DATA = [
    (VALUE1, "description1"),
    (VALUE2, "description2"),
]

@pytest.mark.parametrize("value, description", VALID_DATA)
def test_with_valid_data(self, service, value, description):
    result = service.method(value)
    assert result.is_success()
```

### 测试类组织模式
```python
@pytest.mark.unit
@pytest.mark.db_cleanup
class TestServiceCRUD:
    """CRUD操作测试"""
    CLEANUP_CONFIG = {'resource': {'name__like': 'test_%'}}

    def test_create_success(self):
        pass

    def test_read_success(self):
        pass

    def test_update_success(self):
        pass

    def test_delete_success(self):
        pass
```

## 注意事项

1. **DEBUG 模式**: 所有数据库操作前需要 `GCONF.set_debug(True)`
2. **清理机制**: 使用 `CLEANUP_CONFIG` 和 `@pytest.mark.db_cleanup`
3. **测试标记**: 使用 `@pytest.mark.unit`、`@pytest.mark.integration` 等
4. **错误处理**: 使用 `pytest.raises()` 而非 try/except
5. **断言风格**: 使用 pytest 的 `assert` 而非 unittest 的 `assertEqual`
