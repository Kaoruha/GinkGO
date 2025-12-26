# AdjustfactorService重构Checklist

**目标**: 按照BarService标准重构AdjustfactorService
**参考标准**: BarService (已完成) + TickService (已验证)
**预计工作量**: 2-3小时

## 📋 重构任务清单

### Phase 1: 代码分析和现状评估
- [ ] AF001 分析AdjustfactorService当前架构和接口
- [ ] AF002 确定复权数据的特性 (时序数据还是基础信息)
- [ ] AF003 识别需要重构的具体方法和接口
- [ ] AF004 确认依赖注入模式

### Phase 2: 核心重构实施
- [ ] AF005 更新导入语句 - 添加ServiceResult、装饰器等
- [ ] AF006 重构构造函数 - 移除硬编码依赖
- [ ] AF007 重命名方法 - 遵循简洁命名原则
- [ ] AF008 更新所有方法返回ServiceResult格式
- [ ] AF009 添加@time_logger和@retry装饰器
- [ ] AF010 实现get、count、validate、check_integrity方法
- [ ] AF011 更新私有属性使用 (_crud_repo, _data_source)

### Phase 3: 复权业务逻辑优化
- [ ] AF012 实现完整的错误处理机制
- [ ] AF013 优化复权计算逻辑
- [ ] AF014 添加复权因子验证规则
- [ ] AF015 实现智能复权数据同步

### Phase 4: 测试和验证
- [ ] AF016 运行AdjustfactorService单元测试
- [ ] AF017 验证ServiceResult返回格式
- [ ] AF018 测试复权计算准确性
- [ ] AF019 检查装饰器应用
- [ ] AF020 验证与service_hub集成

## 🎯 完成标准

### ✅ 重构完成标志
- [ ] 所有方法返回ServiceResult格式
- [ ] 方法命名遵循简洁原则
- [ ] 使用正确装饰器
- [ ] 私有属性使用(_前缀)
- [ ] 复权计算逻辑准确
- [ ] 所有测试通过

### 📊 质量指标
- [ ] 测试覆盖率 > 90%
- [ ] 复权计算准确率 > 99.9%
- [ ] 性能指标达标
- [ ] 错误处理完整

## 🔍 验证清单

### 功能验证
- [ ] 复权因子同步功能正常
- [ ] get方法返回正确复权数据
- [ ] count方法计数准确
- [ ] validate方法验证复权数据
- [ ] check_integrity检查数据完整性
- [ ] 前复权/后复权计算准确

### 架构验证
- [ ] 继承正确的BaseService基类
- [ ] 使用ServiceHub依赖注入
- [ ] 遵循Ginkgo编码规范
- [ ] 装饰器正确应用

## 📝 复权数据特性分析

**复权数据特点**:
- 按股票代码组织的时序数据
- 相对稳定，不频繁变更
- 需要精确的计算逻辑
- 支持前复权、后复权等算法

**可能需要的方法**:
- `sync()` - 同步复权因子数据
- `sync_range()` - 按日期范围同步 (如果是时序数据)
- `get()` - 查询复权因子
- `validate()` - 验证复权数据
- `check_integrity()` - 检查数据完整性

---
**注意**: 需要先分析AdjustfactorService的当前实现，确定其数据特性后制定具体的重构策略。