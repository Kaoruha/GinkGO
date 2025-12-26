# Data Service 统一命名规范

**创建日期**: 2025-11-29
**版本**: 1.0.0

## 设计原则

### 1. 面向对象设计原则
- **方法名表达动作**：避免重复服务名+对象名
- **简洁明了**：方法名应清晰表达功能和模式
- **一致性**：所有Data Service使用相同的命名规则

### 2. 避免的反模式
```python
# ❌ 错误：重复服务名+对象名
BarService.sync_bars()
TickService.sync_ticks()

# ❌ 错误：方法名过长
TickService.sync_for_code_on_date()
TickService.sync_for_code_with_date_range()

# ✅ 正确：简洁且表达动作
BarService.sync_range()
TickService.sync_date()
```

## 统一命名规则

### 同步方法模式

所有Data Service的同步方法遵循 `sync_<mode>` 模式：

| 模式 | 方法名 | 功能描述 | 适用服务 |
|------|--------|----------|----------|
| `sync_range()` | 按日期范围同步 | 处理指定日期范围内的数据 | 所有服务 |
| `sync_batch()` | 批量同步 | 同时处理多个对象的数据 | 所有服务 |
| `sync_smart()` | 智能同步 | 根据已有数据智能推断范围 | 所有服务 |
| `sync_date()` | 单日同步 | 处理指定单日的数据 | TickService特有 |

### 查询方法模式

```python
def get(**kwargs) -> ServiceResult:
    """查询数据，返回对象列表"""

def count(**kwargs) -> ServiceResult:
    """计数数据，返回整数数量"""
```

### 验证方法模式

```python
def validate(**kwargs) -> DataValidationResult:
    """验证数据质量和业务规则"""

def check_integrity(**kwargs) -> DataIntegrityCheckResult:
    """检查数据完整性"""
```

## 各服务方法映射

### BarService

| 功能 | 标准方法 | 原方法 | 说明 |
|------|----------|--------|------|
| 按日期范围同步 | `sync_range()` | `sync_by_range()` | 智能增量同步 |
| 批量同步 | `sync_batch()` | `sync_batch_by_range()` | 多股票批量处理 |
| 智能同步 | `sync_smart()` | `sync_for_code()` | 根据最新数据推断 |
| 查询K线 | `get()` | `get_bars()` | 查询bar数据 |
| 计数K线 | `count()` | `count_bars()` | 计数bar数据 |
| 数据验证 | `validate()` | `validate_bars()` | 验证K线质量 |
| 完整性检查 | `check_integrity()` | `check_bars_integrity()` | 检查完整性 |

### TickService

| 功能 | 标准方法 | 原方法 | 说明 |
|------|----------|--------|------|
| 单日同步 | `sync_date()` | `sync_for_code_on_date()` | 同步指定日期数据 |
| 按日期范围同步 | `sync_range()` | `sync_for_code_with_date_range()` | 同步日期范围数据 |
| 智能同步 | `sync_smart()` | `sync_for_code()` | 智能推断同步范围 |
| 批量同步 | `sync_batch()` | 新增 | 多股票批量处理 |
| 查询tick | `get()` | `get_ticks()` | 查询tick数据 |
| 计数tick | `count()` | `count_ticks()` | 计数tick数据 |
| 数据验证 | `validate()` | 新增 | 验证tick质量 |
| 完整性检查 | `check_integrity()` | 新增 | 检查完整性 |

### StockinfoService

| 功能 | 标准方法 | 原方法 | 说明 |
|------|----------|--------|------|
| 批量同步 | `sync_batch()` | `sync_all()` | 同步所有股票信息 |
| 智能同步 | `sync_smart()` | `sync_by_codes()` | 按代码列表同步 |
| 单个同步 | `sync_single()` | `sync()` | 同步单个股票信息 |
| 查询信息 | `get()` | `get_stockinfo()` | 查询股票信息 |
| 计数信息 | `count()` | `count_stockinfo()` | 计数股票数量 |
| 数据验证 | `validate()` | 新增 | 验证信息完整性 |

### AdjustfactorService

| 功能 | 标准方法 | 原方法 | 说明 |
|------|----------|--------|------|
| 按日期范围同步 | `sync_range()` | `sync_adjustfactors()` | 同步复权因子 |
| 批量同步 | `sync_batch()` | `sync_batch_codes()` | 多股票批量同步 |
| 查询因子 | `get()` | `get_adjustfactors()` | 查询复权因子 |
| 计数因子 | `count()` | `count_adjustfactors()` | 计数因子数量 |
| 数据验证 | `validate()` | 新增 | 验证因子数据 |

## 参数语义差异说明

由于不同数据类型的特性差异，某些参数在不同服务中的语义有差异：

### fast_mode 参数差异

| 服务 | fast_mode=True | fast_mode=False | 说明 |
|------|----------------|-----------------|------|
| **BarService** | 智能增量同步（从最新数据+1天开始） | 全量同步（从上市日开始） | 基于timestamp唯一性 |
| **TickService** | 重复检查跳过（检查当天数据是否存在） | 强制重新获取当天数据 | tick时间戳可能重复 |
| **StockinfoService** | 检查信息是否存在则跳过 | 强制重新获取信息 | 相对固定数据 |
| **AdjustfactorService** | 检查因子是否存在则跳过 | 强制重新获取因子 | 相对固定数据 |

## 向后兼容性

### 保留原方法作为别名
```python
class BarService:
    def sync_range(self, *args, **kwargs) -> ServiceResult:
        """新的标准方法"""
        # 新的实现逻辑
        pass

    def sync_by_range(self, *args, **kwargs) -> ServiceResult:
        """向后兼容别名"""
        return self.sync_range(*args, **kwargs)
```

### 迁移指南

1. **推荐使用新方法**：所有新代码使用标准方法名
2. **逐步迁移旧代码**：现有代码可以逐步迁移到新方法名
3. **文档更新**：更新所有相关文档和示例代码
4. **测试更新**：更新测试用例使用新方法名

## 使用示例

### BarService
```python
bar_service = BarService()

# 按日期范围同步
result = bar_service.sync_range("000001.SZ", start_date="20240101", end_date="20240131")

# 批量同步
result = bar_service.sync_batch(["000001.SZ", "000002.SZ"], start_date="20240101")

# 智能同步
result = bar_service.sync_smart("000001.SZ", fast_mode=True)

# 查询数据
bars = bar_service.get(code="000001.SZ", limit=100)

# 计数数据
count = bar_service.count(code="000001.SZ")

# 验证数据
validation = bar_service.validate(code="000001.SZ", start_date="20240101")

# 完整性检查
integrity = bar_service.check_integrity(code="000001.SZ", start_date="20240101", end_date="20240131")
```

### TickService
```python
tick_service = TickService()

# 单日同步
result = tick_service.sync_date("000001.SZ", date="20240101", fast_mode=True)

# 按日期范围同步
result = tick_service.sync_range("000001.SZ", start_date="20240101", end_date="20240101")

# 智能同步
result = tick_service.sync_smart("000001.SZ", fast_mode=True, max_backtrack_days=7)

# 批量同步
result = tick_service.sync_batch(["000001.SZ", "000002.SZ"], start_date="20240101", end_date="20240101")

# 查询数据
ticks = tick_service.get(code="000001.SZ", start_date="20240101", limit=1000)

# 计数数据
count = tick_service.count(code="000001.SZ", start_date="20240101")
```

## 总结

通过统一的命名规则，我们实现了：

1. **简洁性**：方法名清晰表达功能，避免冗余
2. **一致性**：所有服务使用相同的命名模式
3. **可扩展性**：新服务可以遵循相同的规则
4. **向后兼容**：保留旧方法作为过渡期别名
5. **清晰性**：通过方法名即可理解功能和参数需求

这套规范将显著提升Ginkgo数据服务的开发体验和代码质量。