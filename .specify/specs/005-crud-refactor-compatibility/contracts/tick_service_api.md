# TickService API契约

**创建日期**: 2025-11-29
**版本**: 1.0.0

## 概述

TickService API遵循统一的命名规则，提供tick数据的同步、验证和查询功能，所有方法都返回ServiceResult格式。

## 统一命名规则（与BarService一致）

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

## TickService API

### sync_date()

**功能**: 按指定日期同步tick数据（单日同步）

```python
def sync_date(
    self,
    code: str,
    date: datetime,
    fast_mode: bool = False
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (必需)
- `date`: 同步的特定日期 (必需)
- `fast_mode`: True时检查当天数据存在则跳过，False时强制重新获取 (可选，默认False)

**返回**: ServiceResult包含DataSyncResult

**注意**: fast_mode语义与BarService不同，Tick数据无法精确增量同步

### sync_range()

**功能**: 按日期范围同步tick数据

```python
def sync_range(
    self,
    code: str,
    start_date: datetime,
    end_date: datetime,
    fast_mode: bool = True
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (必需)
- `start_date`: 开始日期 (必需)
- `end_date`: 结束日期 (必需)
- `fast_mode`: True时检查每天数据存在则跳过，False时强制重新获取 (可选，默认True)

**返回**: ServiceResult包含DataSyncResult

### sync_smart()

**功能**: 智能同步tick数据（根据最新数据推断日期范围）

```python
def sync_smart(
    self,
    code: str,
    fast_mode: bool = True,
    max_backtrack_days: int = 0
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (必需)
- `fast_mode`: True时从最新tick时间开始，False时从默认日期开始 (可选，默认True)
- `max_backtrack_days`: 最大回溯天数 (可选，默认0)

**返回**: ServiceResult包含DataSyncResult

### sync_batch()

**功能**: 批量同步多个股票的tick数据

```python
def sync_batch(
    self,
    codes: List[str],
    start_date: datetime,
    end_date: datetime,
    fast_mode: bool = True
) -> ServiceResult
```

**参数**:
- `codes`: 股票代码列表 (必需)
- `start_date`: 开始日期 (必需)
- `end_date`: 结束日期 (必需)
- `fast_mode`: True时检查数据存在则跳过，False时强制重新获取 (可选，默认True)

**返回**: ServiceResult包含DataSyncResult

### get()

**功能**: 查询tick数据

```python
def get(
    self,
    **kwargs
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (可选)
- `start_date`: 开始日期 (可选)
- `end_date`: 结束日期 (可选)
- `limit`: 限制数量 (可选)
- `order_by`: 排序字段 (可选)

**返回**: ServiceResult包含ModelList或tick对象列表

### count()

**功能**: 计数tick数据

```python
def count(
    self,
    **kwargs
) -> ServiceResult
```

**参数**:
- `code`: 股票代码 (可选)
- `start_date`: 开始日期 (可选)
- `end_date`: 结束日期 (可选)

**返回**: ServiceResult包含整数计数

### validate()

**功能**: 验证tick数据质量和业务规则

```python
def validate(
    self,
    code: str,
    start_date: datetime = None,
    end_date: datetime = None
) -> DataValidationResult
```

**参数**:
- `code`: 股票代码 (必需)
- `start_date`: 开始日期 (可选)
- `end_date`: 结束日期 (可选)

**返回**: DataValidationResult包含验证结果和评分

### check_integrity()

**功能**: 检查tick数据完整性

```python
def check_integrity(
    self,
    code: str,
    start_date: datetime,
    end_date: datetime
) -> DataIntegrityCheckResult
```

**参数**:
- `code`: 股票代码 (必需)
- `start_date`: 开始日期 (必需)
- `end_date`: 结束日期 (必需)

**返回**: DataIntegrityCheckResult包含完整性检查结果

## 映射关系（向后兼容）

| 原方法名 | 新方法名 | 说明 |
|---------|---------|------|
| `sync_for_code_on_date` | `sync_date` | 单日同步 |
| `sync_for_code_with_date_range` | `sync_range` | 日期范围同步 |
| `sync_for_code` | `sync_smart` | 智能同步 |
| 新增 | `sync_batch` | 批量同步 |
| `get_ticks` | `get` | 查询数据 |
| `count_ticks` | `count` | 计数数据 |
| 新增 | `validate` | 数据验证 |
| 新增 | `check_integrity` | 完整性检查 |

## 参数语义差异说明

由于数据特性不同，某些参数在不同服务中的语义有差异：

- **fast_mode**:
  - BarService: 智能增量同步（从最新数据+1天开始）
  - TickService: 重复检查跳过（检查当天数据是否已存在）

建议在使用时参考各服务的具体文档说明。