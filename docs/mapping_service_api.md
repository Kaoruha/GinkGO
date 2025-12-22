# MappingService API 文档

## 概述

`MappingService` 是Ginkgo量化交易框架中的映射关系管理服务，统一管理以下映射关系：

- **Engine-Portfolio映射**: 引擎与投资组合的关联
- **Portfolio-File组件映射**: 投资组合与组件文件（策略、选择器、风险管理器等）的绑定
- **Engine-Handler映射**: 引擎与事件处理器的映射
- **参数管理**: 组件实例化的参数配置和存储

## 初始化

```python
from ginkgo.data.containers import container
from ginkgo.data.services.mapping_service import MappingService

# 通过容器获取服务实例
mapping_service = container.mapping_service()
```

## API 参考

### 1. Engine-Portfolio映射管理

#### create_engine_portfolio_mapping

创建Engine与Portfolio的映射关系。

```python
def create_engine_portfolio_mapping(
    engine_uuid: str,
    portfolio_uuid: str,
    engine_name: str = None,
    portfolio_name: str = None
) -> ServiceResult
```

**参数:**
- `engine_uuid`: 引擎唯一标识符
- `portfolio_uuid`: 投资组合唯一标识符
- `engine_name`: 引擎名称（可选）
- `portfolio_name`: 投资组合名称（可选）

**返回:**
- `ServiceResult`: 包含创建的映射对象或错误信息

**示例:**
```python
result = mapping_service.create_engine_portfolio_mapping(
    engine_uuid="engine_123456",
    portfolio_uuid="portfolio_789012",
    engine_name="backtest_engine",
    portfolio_name="test_portfolio"
)

if result.success:
    mapping = result.data
    print(f"映射创建成功: {mapping.uuid}")
else:
    print(f"创建失败: {result.error}")
```

#### get_engine_portfolio_mapping

获取Engine-Portfolio映射关系。

```python
def get_engine_portfolio_mapping(
    engine_uuid: str = None,
    portfolio_uuid: str = None
) -> ServiceResult
```

**参数:**
- `engine_uuid`: 引擎唯一标识符（可选）
- `portfolio_uuid`: 投资组合唯一标识符（可选）

**返回:**
- `ServiceResult`: 包含映射关系列表或错误信息

**示例:**
```python
# 根据引擎ID获取
result = mapping_service.get_engine_portfolio_mapping(engine_uuid="engine_123456")

# 根据投资组合ID获取
result = mapping_service.get_engine_portfolio_mapping(portfolio_uuid="portfolio_789012")
```

### 2. Portfolio-File组件绑定

#### create_portfolio_file_binding

创建Portfolio与File组件的绑定关系。

```python
def create_portfolio_file_binding(
    portfolio_uuid: str,
    file_uuid: str,
    file_name: str,
    file_type: FILE_TYPES
) -> ServiceResult
```

**参数:**
- `portfolio_uuid`: 投资组合唯一标识符
- `file_uuid`: 组件文件唯一标识符
- `file_name`: 组件文件名称
- `file_type`: 文件类型枚举（SELECTOR, STRATEGY, SIZER, RISKMANAGER, ANALYZER）

**返回:**
- `ServiceResult`: 包含创建的绑定对象或错误信息

**示例:**
```python
from ginkgo.enums import FILE_TYPES

result = mapping_service.create_portfolio_file_binding(
    portfolio_uuid="portfolio_789012",
    file_uuid="selector_file_123",
    file_name="fixed_selector",
    file_type=FILE_TYPES.SELECTOR
)
```

#### get_portfolio_file_bindings

获取Portfolio的所有File绑定关系。

```python
def get_portfolio_file_bindings(
    portfolio_uuid: str,
    file_type: FILE_TYPES = None
) -> ServiceResult
```

**参数:**
- `portfolio_uuid`: 投资组合唯一标识符
- `file_type`: 文件类型过滤（可选）

**返回:**
- `ServiceResult`: 包含绑定关系列表或错误信息

**示例:**
```python
# 获取所有绑定
result = mapping_service.get_portfolio_file_bindings("portfolio_789012")

# 获取特定类型的绑定
result = mapping_service.get_portfolio_file_bindings(
    "portfolio_789012",
    FILE_TYPES.SELECTOR
)
```

#### create_preset_bindings

根据规则批量创建预设绑定关系。

```python
def create_preset_bindings(
    engine_uuid: str,
    portfolio_uuid: str,
    binding_rules: Dict[str, List[Dict]]
) -> ServiceResult
```

**参数:**
- `engine_uuid`: 引擎唯一标识符
- `portfolio_uuid`: 投资组合唯一标识符
- `binding_rules`: 绑定规则字典

**返回:**
- `ServiceResult`: 包含创建结果详情

**示例:**
```python
binding_rules = {
    "selectors": [
        {"name": "fixed_selector"},
        {"name": "momentum_selector"}
    ],
    "strategies": [
        {"name": "random_choice"}
    ],
    "sizers": [
        {"name": "fixed_sizer"}
    ],
    "risk_managers": [
        {"name": "position_ratio_risk"}
    ]
}

result = mapping_service.create_preset_bindings(
    engine_uuid="engine_123456",
    portfolio_uuid="portfolio_789012",
    binding_rules=binding_rules
)
```

### 3. 参数管理

#### create_component_parameters

为组件创建参数配置。

```python
def create_component_parameters(
    mapping_uuid: str,
    file_uuid: str,
    parameters: Dict[int, str]
) -> ServiceResult
```

**参数:**
- `mapping_uuid`: 绑定关系唯一标识符
- `file_uuid`: 组件文件唯一标识符
- `parameters`: 参数字典，key为索引，value为参数值

**返回:**
- `ServiceResult`: 包含创建的参数信息

**示例:**
```python
import json

# 为FixedSelector创建参数
parameters = {
    0: "default_selector",
    1: json.dumps(["000001.SZ", "000002.SZ"])
}

result = mapping_service.create_component_parameters(
    mapping_uuid="binding_uuid_123",
    file_uuid="selector_file_123",
    parameters=parameters
)

# 为FixedSizer创建参数
parameters = {
    0: "default_sizer",
    1: "1000"  # volume参数
}

result = mapping_service.create_component_parameters(
    mapping_uuid="binding_uuid_456",
    file_uuid="sizer_file_456",
    parameters=parameters
)
```

#### get_portfolio_parameters

获取Portfolio的所有组件参数。

```python
def get_portfolio_parameters(portfolio_uuid: str) -> ServiceResult
```

**参数:**
- `portfolio_uuid`: 投资组合唯一标识符

**返回:**
- `ServiceResult`: 包含参数列表或错误信息

**示例:**
```python
result = mapping_service.get_portfolio_parameters("portfolio_789012")
if result.success:
    for param in result.data:
        print(f"参数: {param.value} (映射: {param.mapping_uuid})")
```

### 4. 清理和维护

#### cleanup_orphaned_mappings

清理孤立的映射关系（关联对象不存在的映射）。

```python
def cleanup_orphaned_mappings() -> ServiceResult
```

**返回:**
- `ServiceResult`: 包含清理统计信息

**示例:**
```python
result = mapping_service.cleanup_orphaned_mappings()
print(f"清理结果: {result.data}")
```

#### cleanup_by_names

根据名称模式清理相关的所有映射关系。

```python
def cleanup_by_names(name_pattern: str = "present_%") -> ServiceResult
```

**参数:**
- `name_pattern`: 名称模式，默认为"present_%"

**返回:**
- `ServiceResult`: 包含清理统计信息

**示例:**
```python
# 清理所有以"test_"开头的映射关系
result = mapping_service.cleanup_by_names("test_%")
print(f"清理了 {result.data.get('total_cleaned', 0)} 个映射关系")
```

### 5. 工具方法

#### get_component_types_for_portfolio

获取Portfolio绑定的组件类型统计。

```python
def get_component_types_for_portfolio(portfolio_uuid: str) -> Dict[str, int]
```

**参数:**
- `portfolio_uuid`: 投资组合唯一标识符

**返回:**
- `Dict[str, int]`: 组件类型统计字典

**示例:**
```python
stats = mapping_service.get_component_types_for_portfolio("portfolio_789012")
print(f"组件统计: {stats}")
# 输出示例: {'SELECTOR': 1, 'STRATEGY': 1, 'SIZER': 1}
```

## 使用模式

### 典型工作流程

1. **创建投资组合并绑定组件**
```python
# 1. 创建Engine-Portfolio映射
mapping_service.create_engine_portfolio_mapping(
    engine_uuid="engine_123",
    portfolio_uuid="portfolio_456"
)

# 2. 绑定组件到Portfolio
binding_rules = {
    "selectors": [{"name": "fixed_selector"}],
    "strategies": [{"name": "random_choice"}],
    "sizers": [{"name": "fixed_sizer"}]
}

result = mapping_service.create_preset_bindings(
    engine_uuid="engine_123",
    portfolio_uuid="portfolio_456",
    binding_rules=binding_rules
)

# 3. 为组件创建参数
# 这通常在seeding过程中完成
```

2. **查询绑定关系**
```python
# 获取Portfolio的所有组件绑定
bindings = mapping_service.get_portfolio_file_bindings("portfolio_456")

# 获取Portfolio的所有参数
params = mapping_service.get_portfolio_parameters("portfolio_456")

# 获取组件类型统计
stats = mapping_service.get_component_types_for_portfolio("portfolio_456")
```

3. **清理和维护**
```python
# 清理孤立的映射
mapping_service.cleanup_orphaned_mappings()

# 按名称模式清理
mapping_service.cleanup_by_names("demo_%")
```

## 错误处理

所有API方法都返回`ServiceResult`对象，包含以下属性：

- `success: bool` - 操作是否成功
- `data: Any` - 返回的数据（成功时）
- `error: str` - 错误信息（失败时）
- `message: str` - 操作消息

```python
result = mapping_service.create_engine_portfolio_mapping(...)

if result.success:
    mapping = result.data
    print(f"创建成功: {mapping.uuid}")
else:
    print(f"创建失败: {result.error}")
    # 可以在这里添加错误处理逻辑
```

## 配置参数

常用组件的参数配置示例：

### FixedSelector
```python
params = {
    0: "default_selector",  # name参数
    1: json.dumps(["000001.SZ", "000002.SZ"])  # codes参数
}
```

### FixedSizer
```python
params = {
    0: "default_sizer",  # name参数
    1: "1000"  # volume参数（字符串类型）
}
```

### StrategyRandomChoice
```python
params = {
    0: "default_strategy"  # name参数
}
```

### PositionRatioRisk
```python
params = {
    0: "0.2"  # ratio参数（字符串类型）
}
```

## 注意事项

1. **参数类型**: 所有参数值在数据库中都以字符串形式存储，使用时需要适当转换
2. **索引顺序**: 参数的索引（key）必须与组件构造函数的参数顺序一致
3. **事务性**: 创建绑定和参数的操作应该在同一事务中完成，确保数据一致性
4. **清理操作**: 清理操作会删除数据，请谨慎使用，建议在生产环境使用前充分测试