# BarService重构使用指南

**创建日期**: 2025-11-28
**目标**: BarService重构后的使用方法

## 核心变更

### 方法重命名
- `sync_for_code_with_date_range()` → `sync_bars()`
- `sync_batch_codes_with_date_range()` → `sync_bars_batch()`
- `sync_for_code()` → `sync_bars_fast()`

### 新增方法
- `validate_bars()`: 数据验证
- `check_bars_integrity()`: 完整性检查

## 基础使用

```python
from ginkgo import service_hub
from ginkgo.enums import FREQUENCY_TYPES
from datetime import datetime

# 通过service_hub获取BarService
bar_service = service_hub.data.services.bar_service()

# 数据同步
result = bar_service.sync_bars(
    code="000001.SZ",
    start_date=datetime(2024, 1, 1),
    end_date=datetime.now()
)

# 批量同步
result = bar_service.sync_bars_batch(
    codes=["000001.SZ", "000002.SZ"],
    start_date=datetime(2024, 1, 1),
    end_date=datetime.now()
)

# 数据验证
result = bar_service.validate_bars(bars_data)

# 完整性检查
result = bar_service.check_bars_integrity(
    code="000001.SZ",
    start_date=datetime(2024, 1, 1),
    end_date=datetime.now())
```

## 返回格式

所有方法返回ServiceResult，包含：
- `success`: bool
- `data`: 具体结果数据
- `error`: str (失败时)
- `message`: str