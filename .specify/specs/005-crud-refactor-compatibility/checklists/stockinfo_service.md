# StockinfoService重构Checklist

**目标**: 按照BarService标准重构StockinfoService
**参考标准**: BarService (已完成) + TickService (已验证)
**预计工作量**: 2-3小时

## 📋 重构任务清单

### Phase 1: 代码分析和现状评估
- [ ] SS001 分析StockinfoService当前架构和接口
- [ ] SS002 对比BarService和TickService的成功模式
- [ ] SS003 识别需要重构的具体方法和接口
- [ ] SS004 确认依赖注入模式和私有属性使用

### Phase 2: 核心重构实施
- [ ] SS005 更新导入语句 - 添加ServiceResult、装饰器等
- [ ] SS006 重构构造函数 - 移除硬编码依赖，使用service_hub
- [ ] SS007 重命名方法 - sync_all → sync (简洁命名)
- [ ] SS008 更新所有方法返回ServiceResult格式
- [ ] SS009 添加@time_logger和@retry装饰器
- [ ] SS010 实现get、count、validate方法 (简洁命名)
- [ ] SS011 实现check_integrity方法
- [ ] SS012 更新私有属性使用 (_crud_repo, _data_source)

### Phase 3: 错误处理和业务逻辑
- [ ] SS013 实现完整的错误处理机制 - 使用ServiceResult.failure/error
- [ ] SS014 添加数据验证和参数检查
- [ ] SS015 优化同步逻辑 - 基于BarService的成功模式
- [ ] SS016 完善重试机制

### Phase 4: 测试和验证
- [ ] SS017 运行StockinfoService单元测试
- [ ] SS018 验证ServiceResult返回格式正确性
- [ ] SS019 检查装饰器是否正确应用
- [ ] SS020 测试错误处理机制
- [ ] SS021 验证与service_hub的集成

## 🎯 完成标准

### ✅ 重构完成标志
- [ ] 所有方法返回ServiceResult格式
- [ ] 方法命名遵循简洁原则 (sync, get, count, validate, check_integrity)
- [ ] 使用正确的装饰器(@time_logger, @retry)
- [ ] 私有属性使用(_前缀)
- [ ] 错误处理完整且友好
- [ ] 所有测试通过

### 📊 质量指标
- [ ] 测试覆盖率 > 90%
- [ ] 代码风格符合BarService模式
- [ ] 性能指标达标
- [ ] 错误处理覆盖所有异常情况

## 🔍 验证清单

### 功能验证
- [ ] sync方法正常工作 (原sync_all功能)
- [ ] get方法返回正确数据 (原get_stockinfos功能)
- [ ] count方法计数准确
- [ ] validate方法验证数据完整性
- [ ] check_integrity检查数据质量
- [ ] 业务特定方法正常工作:
  - get_stockinfo_codes_set
  - is_code_in_stocklist
  - get_stockinfo_by_code
  - retry_failed_records

### 架构验证
- [ ] 继承DataService基类
- [ ] 使用ServiceHub依赖注入
- [ ] 遵循事件驱动架构原则
- [ ] 符合Ginkgo编码规范

### 集成验证
- [ ] 与现有系统无冲突
- [ ] CLI命令兼容性
- [ ] 数据库操作正确
- [ ] 日志记录完整

## 📝 方法重命名对照表

| 当前方法名 | 目标方法名 | 说明 |
|-----------|-----------|------|
| sync_all | sync | 简洁命名，保持功能不变 |
| get_stockinfos | get | 统一查询接口命名 |
| (新增) | count | 添加计数功能 |
| (新增) | validate | 添加验证功能 |
| (新增) | check_integrity | 添加完整性检查 |
| get_stockinfo_codes_set | 保持 | 业务特定，无需重命名 |
| is_code_in_stocklist | 保持 | 业务特定，无需重命名 |
| get_stockinfo_by_code | 保持 | 业务特定，无需重命名 |
| retry_failed_records | 保持 | 业务特定，无需重命名 |

## 📋 ServiceResult返回格式规范

### 同步方法 (sync)
```python
return ServiceResult.success(
    data=DataSyncResult(...),
    message="股票信息同步成功"
)
```

### 查询方法 (get, count)
```python
return ServiceResult.success(
    data=query_result,  # ModelList或数字
    message="查询成功"
)
```

### 验证方法 (validate, check_integrity)
```python
return ServiceResult.success(
    data=DataValidationResult(...) 或 DataIntegrityCheckResult(...),
    message="验证完成"
)
```

---
**注意**: StockinfoService是基础信息服务，不需要时序数据的range/batch/smart方法，重点在于统一返回格式和错误处理。