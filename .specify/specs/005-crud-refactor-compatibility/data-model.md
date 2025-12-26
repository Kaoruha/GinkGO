# BarService数据模型设计

**创建日期**: 2025-11-28
**目标**: 定义BarService重构的通用数据结构和验证规则

## 核心数据结构

### 1. DataValidationResult (通用数据验证结果)

```python
from dataclasses import dataclass, field
from typing import List, Any
from datetime import datetime

@dataclass
class DataValidationResult:
    """通用数据验证结果"""
    is_valid: bool
    error_count: int
    warning_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data_quality_score: float  # 0-100
    validation_timestamp: datetime
    validation_type: str  # "business_rules", "data_quality", "integrity"
    entity_type: str    # "bars", "ticks", "stockinfo", "orders" 等
    entity_identifier: str  # 具体实体标识，如股票代码
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 通用方法
    def add_error(self, error_message: str):
        """添加错误信息"""
        self.errors.append(error_message)
        self.error_count = len(self.errors)

    def add_warning(self, warning_message: str):
        """添加警告信息"""
        self.warnings.append(warning_message)
        self.warning_count = len(self.warnings)

    def set_metadata(self, key: str, value: Any):
        """设置实体特定的元数据"""
        self.metadata[key] = value
```

### 2. DataIntegrityCheckResult (通用完整性检查结果)

```python
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

@dataclass
class DataIntegrityCheckResult:
    """通用数据完整性检查结果"""
    entity_type: str    # "bars", "ticks", "stockinfo" 等
    entity_identifier: str  # 具体实体标识
    check_range: Tuple[datetime, datetime]
    total_records: int
    missing_records: int
    duplicate_records: int
    integrity_issues: List[Dict[str, Any]] = field(default_factory=list)
    integrity_score: float  # 0-100
    recommendations: List[str] = field(default_factory=list)
    check_duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue_type: str, description: str, location: Any = None):
        """添加完整性问题"""
        issue = {
            "type": issue_type,
            "description": description,
            "location": location,
            "timestamp": datetime.now()
        }
        self.integrity_issues.append(issue)

    def set_metadata(self, key: str, value: Any):
        """设置实体特定的元数据"""
        self.metadata[key] = value
```

### 3. DataSyncResult (通用数据同步结果)

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class DataSyncResult:
    """通用数据同步结果"""
    entity_type: str    # "bars", "ticks", "stockinfo", "orders" 等
    entity_identifier: str  # 具体实体标识，如股票代码
    sync_range: Tuple[Optional[datetime], Optional[datetime]]
    records_processed: int
    records_added: int
    records_updated: int
    records_skipped: int  # 已存在，跳过
    records_failed: int
    sync_duration: float
    is_idempotent: bool
    sync_strategy: str  # "full", "incremental", "fast"
    errors: List[Tuple[int, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 通用方法
    def add_error(self, row_index: int, error_message: str):
        """添加错误信息"""
        self.errors.append((row_index, error_message))

    def add_warning(self, warning_message: str):
        """添加警告信息"""
        self.warnings.append(warning_message)

    def set_metadata(self, key: str, value: Any):
        """设置实体特定的元数据"""
        self.metadata[key] = value

    def get_success_rate(self) -> float:
        """计算成功率"""
        if self.records_processed == 0:
            return 0.0
        return (self.records_added + self.records_updated) / self.records_processed
```

## 标准化方法签名

### CRUD标准方法（新命名）

1. **sync_bars()**: 智能增量同步（主要方法）
2. **sync_bars_batch()**: 批量同步
3. **sync_bars_fast()**: 快速同步
4. **get_bars()**: 查询数据
5. **count_bars()**: 计数
6. **validate_bars()**: 数据验证（新增）
7. **check_bars_integrity()**: 完整性检查（新增）

### 方法签名

```python
def sync_bars(
    self,
    code: str,
    start_date: datetime = None,
    end_date: datetime = None,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult:
    """
    智能增量同步Bar数据

    Returns:
        ServiceResult.data = DataSyncResult (通用)
    """

def sync_bars_batch(
    self,
    codes: List[str],
    start_date: datetime = None,
    end_date: datetime = None,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult:
    """
    批量同步多个股票的Bar数据

    Returns:
        ServiceResult.data = List[DataSyncResult] (通用)
    """

def validate_bars(
    self,
    bars_data: Union[List[MBar], pd.DataFrame, ModelList]
) -> ServiceResult:
    """
    验证Bar数据的基础业务规则

    Returns:
        ServiceResult.data = DataValidationResult (通用)
    """

def check_bars_integrity(
    self,
    code: str,
    start_date: datetime,
    end_date: datetime,
    frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY
) -> ServiceResult:
    """
    检查指定时间范围内的数据完整性

    Returns:
        ServiceResult.data = DataIntegrityCheckResult (通用)
    """
```

## 使用示例

### Bars数据示例

```python
# 数据同步结果
bars_sync_result = DataSyncResult(
    entity_type="bars",
    entity_identifier="000001.SZ",
    sync_range=(start_date, end_date),
    records_processed=1000,
    records_added=800,
    records_skipped=200,
    sync_duration=5.2,
    is_idempotent=True,
    sync_strategy="incremental"
)

# 添加Bars特定的元数据
bars_sync_result.set_metadata("frequency", "DAY")
bars_sync_result.set_metadata("data_source", "tushare")
bars_sync_result.set_metadata("adjustment_type", "fore")

# 数据验证结果
bars_validation = DataValidationResult(
    is_valid=False,
    error_count=2,
    entity_identifier="000001.SZ",
    entity_type="bars",
    validation_type="business_rules",
    errors=["OHLC relationship violation at 2024-01-02"],
    warnings=["High volatility detected"],
    validation_timestamp=datetime.now()
)

# 添加Bars特定的验证信息到metadata
bars_validation.set_metadata("ohlc_violations", ["High < max(Open, Close)"])
bars_validation.set_metadata("frequency", "DAY")
bars_validation.set_metadata("trading_day", "2024-01-02")
```

### Ticks数据示例

```python
# 使用相同的DataSyncResult处理Ticks
ticks_sync_result = DataSyncResult(
    entity_type="ticks",
    entity_identifier="000001.SZ",
    sync_range=(start_date, end_date),
    records_processed=50000,
    records_added=45000,
    records_skipped=5000,
    sync_duration=12.3,
    is_idempotent=True,
    sync_strategy="incremental"
)

# 添加Ticks特定的元数据
ticks_sync_result.set_metadata("tick_frequency", "1min")
ticks_sync_result.set_metadata("trading_day", "2024-01-02")
ticks_sync_result.set_metadata("market", "SZSE")

# 使用相同的DataValidationResult处理Ticks
ticks_validation = DataValidationResult(
    is_valid=True,
    error_count=0,
    entity_identifier="000001.SZ",
    entity_type="ticks",
    validation_type="business_rules",
    warnings=["Unusual volume spike detected"],
    validation_timestamp=datetime.now()
)

# 添加Ticks特定的验证信息到metadata
ticks_validation.set_metadata("price_anomalies", [])
ticks_validation.set_metadata("volume_anomalies", ["Volume spike at 09:30"])
ticks_validation.set_metadata("tick_frequency", "1min")
```

### StockInfo数据示例

```python
# 使用相同的DataSyncResult处理StockInfo
stockinfo_sync_result = DataSyncResult(
    entity_type="stockinfo",
    entity_identifier="000001.SZ",
    sync_range=(None, None),  # 全量同步
    records_processed=1,
    records_added=0,
    records_updated=1,
    records_skipped=0,
    sync_duration=0.5,
    is_idempotent=True,
    sync_strategy="full"
)

# 添加StockInfo特定的元数据
stockinfo_sync_result.set_metadata("info_type", "basic")
stockinfo_sync_result.set_metadata("update_source", "exchange")
stockinfo_sync_result.set_metadata("last_updated", datetime.now())
```

## 元数据规范

### 通用元数据字段
```python
# 所有Result都可以使用的通用元数据
common_metadata = {
    "data_source": "tushare",        # 数据源
    "sync_version": "1.0",          # 同步版本
    "created_by": "system",         # 创建者
    "batch_id": "batch_001",        # 批次ID（如果适用）
    "operation_id": "op_123456",     # 操作ID
}
```

### 实体特定元数据示例
```python
# Bars特定元数据
bars_metadata = {
    "frequency": "DAY",             # 数据频率
    "adjustment_type": "fore",      # 复权类型
    "trading_day": "2024-01-02",    # 交易日
    "market": "SZSE"                # 市场
}

# Ticks特定元数据
ticks_metadata = {
    "tick_frequency": "1min",       # Tick频率
    "trading_session": "continuous", # 交易时段
    "price_precision": 0.01,        # 价格精度
    "market": "SZSE"
}

# StockInfo特定元数据
stockinfo_metadata = {
    "info_type": "basic",           # 信息类型
    "update_source": "exchange",   # 更新来源
    "last_updated": "2024-01-02",   # 最后更新时间
    "market": "SZSE"
}
```

## 数据验证规则

### 基础业务规则
- High >= max(Open, Close)
- Low <= min(Open, Close)
- 所有价格 >= 0
- Volume >= 0
- 时间戳递增且唯一

### 完整性规则
- 工作日数据连续性
- 数据密度 >= 95%
- 无重复记录
- OHLC关系正确

## 错误分类
- 1000-1099: 数据源错误
- 2000-2099: 数据库错误
- 3000-3099: 业务逻辑错误
- 4000-4099: 系统错误
- 5000-5099: 数据验证错误