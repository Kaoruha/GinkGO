# BarService API契约

**创建日期**: 2025-11-28
**版本**: 1.0.0

## 概述

BarService API定义了数据同步、验证和查询的标准接口，所有方法都返回ServiceResult格式。

## 统一命名规则

### 设计原则
- 面向对象设计：方法名表达动作，避免重复服务名+对象名
- 统一模式：所有Data Service使用相同的方法命名规则
- 清晰语义：通过方法后缀区分不同的同步模式

### 标准方法模式

#### 同步方法
- `sync_range()` - 按日期范围同步
- `sync_batch()` - 批量同步多个对象
- `sync_smart()` - 智能同步（根据已有数据推断范围）
- `sync_date()` - 按指定日期同步（TickService特有）

#### 查询方法
- `get()` - 查询数据
- `count()` - 计数数据

#### 验证方法
- `validate()` - 数据验证
- `check_integrity()` - 完整性检查

## BarService API

### sync_range()

**功能**: 按日期范围智能增量同步Bar数据

```python
def sync_range(
    self,
    code: str,
    start_date: datetime = None,
    end_date: datetime = None,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (必需)
- `start_date`: 开始日期 (可选，默认智能推算)
- `end_date`: 结束日期 (可选，默认当前时间)
- `frequency`: 数据频率 (可选，默认DAY)

**返回**: ServiceResult包含DataSyncResult

### sync_batch()

**功能**: 批量同步多个股票

```python
def sync_batch(
    self,
    codes: List[str],
    start_date: datetime = None,
    end_date: datetime = None,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult
```

**参数**:
- `codes`: 股票代码列表 (必需)
- `start_date`: 开始日期 (可选)
- `end_date`: 结束日期 (可选)
- `frequency`: 数据频率 (可选)

**返回**: ServiceResult包含List[DataSyncResult]

### sync_bars_fast()

**功能**: 快速同步（仅同步最新数据）

```python
def sync_bars_fast(
    self,
    code: str,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (必需)
- `frequency`: 数据频率 (可选)

**返回**: ServiceResult包含DataSyncResult

### get_bars()

**功能**: 查询Bar数据

```python
def get_bars(
    self,
    code: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE,
    page: int = None,
    page_size: int = None,
    order_by: str = "timestamp",
    desc_order: bool = False
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (可选)
- `start_date`: 开始日期 (可选)
- `end_date`: 结束日期 (可选)
- `frequency`: 数据频率 (可选)
- `adjustment_type`: 复权类型 (可选)
- `page`: 页码 (可选)
- `page_size`: 页大小 (可选)
- `order_by`: 排序字段 (可选)
- `desc_order`: 降序 (可选)

**返回**: ServiceResult包含ModelList数据

### count_bars()

**功能**: 计数Bar数据

```python
def count_bars(
    self,
    code: str = None,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
    **filters
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (可选)
- `frequency`: 数据频率 (可选)
- `**filters`: 其他过滤条件

**返回**: ServiceResult包含计数结果

### validate_bars()

**功能**: 验证Bar数据

```python
def validate_bars(
    self,
    bars_data: Union[List[MBar], pd.DataFrame, ModelList]
) -> ServiceResult
```

**参数**:
- `bars_data`: 待验证的Bar数据 (必需)

**返回**: ServiceResult包含DataValidationResult

### check_bars_integrity()

**功能**: 检查数据完整性

```python
def check_bars_integrity(
    self,
    code: str,
    start_date: datetime,
    end_date: datetime,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (必需)
- `start_date`: 开始日期 (必需)
- `end_date`: 结束日期 (必需)
- `frequency`: 数据频率 (可选)

**返回**: ServiceResult包含DataIntegrityCheckResult

## 返回数据结构

### ServiceResult

```python
class ServiceResult:
    success: bool
    error: str
    data: Any
    message: str
```

### DataSyncResult (通用)

```python
class DataSyncResult:
    entity_type: str    # "bars"
    entity_identifier: str  # 股票代码
    sync_range: Tuple[Optional[datetime], Optional[datetime]]
    records_processed: int
    records_added: int
    records_updated: int
    records_skipped: int
    records_failed: int
    sync_duration: float
    is_idempotent: bool
    sync_strategy: str
    errors: List[Tuple[int, str]]
    warnings: List[str]
    metadata: Dict[str, Any]

    # Bar特定的metadata示例
    metadata = {
        "frequency": "DAY",
        "adjustment_type": "fore",
        "trading_day": "2024-01-02"
    }
```

### DataValidationResult (通用)

```python
class DataValidationResult:
    is_valid: bool
    error_count: int
    warning_count: int
    errors: List[str]
    warnings: List[str]
    data_quality_score: float
    validation_timestamp: datetime
    validation_type: str
    entity_type: str  # "bars"
    entity_identifier: str  # 股票代码
    metadata: Dict[str, Any]

    # Bar特定的metadata示例
    metadata = {
        "ohlc_violations": ["High < max(Open, Close)"],
        "frequency": "DAY"
    }
```

### DataIntegrityCheckResult (通用)

```python
class DataIntegrityCheckResult:
    entity_type: str  # "bars"
    entity_identifier: str  # 股票代码
    check_range: Tuple[datetime, datetime]
    total_records: int
    missing_records: int
    duplicate_records: int
    integrity_issues: List[Dict[str, Any]]
    integrity_score: float
    recommendations: List[str]
    check_duration: float
    metadata: Dict[str, Any]

    # Bar特定的metadata示例
    metadata = {
        "frequency": "DAY",
        "missing_dates_count": 5,
        "duplicate_timestamps_count": 0
    }
```

## 错误代码

### 数据源错误 (1000-1099)
- 1001: 网络连接失败
- 1002: API调用超时
- 1003: 数据格式错误
- 1004: API限制

### 数据库错误 (2000-2099)
- 2001: 连接失败
- 2002: 约束违反
- 2003: 权限不足
- 2004: 存储空间不足

### 业务逻辑错误 (3000-3099)
- 3001: OHLC关系违反
- 3002: 时间范围冲突
- 3003: 股票代码不存在
- 3004: 频率不支持

### 系统错误 (4000-4099)
- 4001: 内存不足
- 4002: 处理超时
- 4003: 磁盘空间不足
- 4004: 配置错误

### 数据验证错误 (5000-5099)
- 5001: 数据格式错误
- 5002: 必填字段缺失
- 5003: 数据类型不匹配
- 5004: 业务规则违反

## 使用示例

```python
from ginkgo import service_hub
from ginkgo.enums import FREQUENCY_TYPES
from datetime import datetime

# 获取服务
bar_service = service_hub.data.services.bar_service()

# 同步数据
result = bar_service.sync_bars(code="000001.SZ")

if result.success:
    sync_result = result.data  # DataSyncResult
    print(f"同步完成: {sync_result.records_added}条新增")
    print(f"实体类型: {sync_result.entity_type}")
    print(f"频率: {sync_result.metadata.get('frequency')}")
else:
    print(f"同步失败: {result.error}")

# 验证数据
result = bar_service.validate_bars(bars_data)

if result.success:
    validation_result = result.data  # DataValidationResult
    print(f"验证结果: {validation_result.is_valid}")
    print(f"质量评分: {validation_result.data_quality_score}")
    print(f"OHLC违规: {validation_result.metadata.get('ohlc_violations', [])}")
else:
    print(f"验证失败: {result.error}")
```