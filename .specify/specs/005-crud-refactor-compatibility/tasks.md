---

description: "Task list for Data Services & CLI Compatibility Fix feature implementation with current progress"
---

# Tasks: Data Services & CLI Compatibility Fix

**Input**: Design documents from `/specs/005-crud-refactor-compatibility/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Tests are included as TDD is required per project constitution - all functionality must have tests

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **Status**: ✅已完成 / 🔄进行中 / ⏳待开始 / ❌需修复
- Include exact file paths in descriptions

## Path Conventions

- **Services**: `src/ginkgo/data/services/`
- **Tests**: `test/data/services/`
- **Results**: Based on actual test results and current progress

<!--

  ============================================================================

  ACTUAL PROGRESS REPORT: Based on running tests and code analysis

  Completed Services (4/13):
  - AdjustfactorService: ✅ 24/24 tests passing (100%)
  - BarService: ✅ 31/31 tests passing (100%)
  - TickService: ✅ 11/11 tests passing (100%)
  - StockinfoService: ✅ 9/9 tests passing (100%)

  ServiceResult Format: ✅ Fully implemented
  Standard Methods: ✅ get/count/validate/check_integrity
  Private Attributes: ✅ _crud_repo, _data_source patterns

  Remaining Services (9/13):
  - Management Services (3): Multi-CRUD dependencies, transaction handling
  - Business Services (2): Cross-service coordination, dependency injection
  - Middleware Services (2): Infrastructure, caching/messaging

  Test Issues Found:
  - FileService: AssertionError - GCONF not available
  - RedisService: AttributeError - missing crud_repo attribute
  - ComponentService: Module import errors, dependency issues
  - EngineService: Architecture problems with dependencies
  - PortfolioService: Similar dependency management issues

  Implementation Strategy:
  - Follow BarService patterns for all services
  - Priority: Management → Business → Middleware Services
  - Each service: analyze → refactor → test → validate
  ============================================================================

-->

## 🎯 **当前重构状态更新** (基于实际进度分析)

### ✅ **已完成的核心Data Services** (4/13 = 30.8%)
- ✅ **AdjustfactorService** - 24/24测试通过 (100%) - 完全标准化
- ✅ **BarService** - 31/31测试通过 (100%) - 参考标准建立
- ✅ **TickService** - 11/11测试通过 (100%) - 架构验证完成
- ✅ **StockinfoService** - 9/9测试通过 (100%) - API标准化完成

### 🔄 **待重构Service分类** (9/13 = 69.2%)

**ManagementService类型 (3个)**:
- 🔄 **FileService** - 搜索功能重构完成 (30/30测试通过)，get_files→get方法标准化完成
- 🔄 **PortfolioService** - 需要重构 (多CRUD依赖)
- 🔄 **EngineService** - 需要重构 (双CRUD依赖)

**BusinessService类型 (2个)**:
- 🔄 **ComponentService** - 需要重构 (依赖注入问题)
- 🔄 **SignalTrackingService** - 需要重构

**MiddlewareService类型 (2个)**:
- 🔄 **RedisService** - 需要重构 (属性架构问题)
- 🔄 **KafkaService** - 需要重构 (消息中间件)

**FactorService**: 暂不重构 (复杂度评估过高)

**总体完成度**: 4/13 Service (30.8%)

---

**Input**: 基于实际测试结果和代码分析更新重构状态
**Current Status**: 核心Data Services完成，Management/Business/Middleware Services待重构
**Next Priority**: Management Services (按复杂度递增顺序)

**Test Results**: 75/75 core tests passing (100%)
**Architecture**: BarService标准已建立并验证

## Phase 1: ✅ 核心Data Services (已完成 - 100%)

### AdjustfactorService - ✅ 完全标准化 (24/24测试通过)

- [x] T001 [✅completed] 标准化AdjustfactorService继承DataService基类 - src/ginkgo/data/services/adjustfactor_service.py
- [x] T002 [✅completed] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/adjustfactor_service.py
- [x] T003 [✅completed] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/adjustfactor_service.py
- [x] T004 [✅completed] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/adjustfactor_service.py
- [x] T005 [✅completed] 私有属性标准化(_crud_repo, _data_source, _stockinfo_service) - src/ginkgo/data/services/adjustfactor_service.py

### BarService - ✅ 完全标准化 (31/31测试通过)

- [x] T006 [✅completed] 方法名标准化(get_bars→get, count_bars→count) - src/ginkgo/data/services/bar_service.py
- [x] T007 [✅completed] validate_bars和check_bars_integrity方法更新 - src/ginkgo/data/services/bar_service.py
- [x] T008 [✅completed] ServiceResult格式包装 - src/ginkgo/data/services/bar_service.py
- [x] T009 [✅completed] 私有属性标准化(_adjustfactor_service) - src/ginkgo/data/services/bar_service.py
- [x] T010 [✅completed] AdjustfactorService调用更新使用新get方法 - src/ginkgo/data/services/bar_service.py

### TickService - ✅ 完全标准化 (11/11测试通过)

- [x] T011 [✅completed] 私有属性调整(adjustfactor_service→_adjustfactor_service) - src/ginkgo/data/services/tick_service.py
- [x] T012 [✅completed] AdjustfactorService调用更新使用新get方法 - src/ginkgo/data/services/tick_service.py
- [x] T013 [✅completed] 标准方法验证(get/count/validate/check_integrity) - src/ginkgo/data/services/tick_service.py
- [x] T014 [✅completed] 文档注释返回类型更新 - src/ginkgo/data/services/tick_service.py

### StockinfoService - ✅ 完全标准化 (9/9测试通过)

- [x] T015 [✅completed] 标准方法验证(get/count/validate/check_integrity) - src/ginkgo/data/services/stockinfo_service.py
- [x] T016 [✅completed] 跨服务API调用更新(get_stockinfo_by_code→get) - src/ginkgo/data/services/bar_service.py, src/ginkgo/data/services/adjustfactor_service.py
- [x] T017 [✅completed] 统一使用标准API，移除向后兼容 - 跨服务调用更新

---

## Phase 2: 🔄 Management Services重构 (3个Service待重构)

### FileService 重构 - 🔄 搜索功能优化完成 (30/30测试通过)

- [x] T018 [✅completed] 实现统一search方法支持单查询多字段OR搜索 - src/ginkgo/data/services/file_service.py:1229
- [x] T019 [✅completed] 重构search_by_name支持数据库级分页 - src/ginkgo/data/services/file_service.py:948
- [x] T020 [✅completed] 重构search_by_description支持模糊匹配 - src/ginkgo/data/services/file_service.py:1045
- [x] T021 [✅completed] 重构search_by_content支持二进制内容搜索 - src/ginkgo/data/services/file_service.py:1141
- [x] T022 [✅completed] 修复数据库事务问题(drivers缺少commit) - src/ginkgo/data/drivers/__init__.py
- [x] T023 [✅completed] 实现get_by_uuid/get_by_name/get_by_type标准方法 - src/ginkgo/data/services/file_service.py
- [x] T024 [✅completed] 重命名get_files方法为标准get方法 - src/ginkgo/data/services/file_service.py:336
- [x] T025 [✅completed] 更新data/__init__.py移除get_files直接接口 - src/ginkgo/data/__init__.py
- [x] T026 [✅completed] 更新data/seeding.py使用新的get方法 - src/ginkgo/data/seeding.py:87,251
- [x] T027 [✅completed] 更新client/backtest_cli.py适配新API - src/ginkgo/client/backtest_cli.py:545
- [x] T028 [✅completed] 更新所有测试用例适配新接口设计 - test/data/services/test_file_service.py

### FileService 下一步计划

- [ ] T029 [🔄pending] 验证FileService完全符合ManagementService标准
- [ ] T030 [🔄pending] 更新CLI命令使用标准get_*方法 (data CLI)

### PortfolioService 重构 - ❌ 需要修复 (多CRUD依赖)

- [ ] T031 [❌blocked] 分析PortfolioService测试架构问题 - test/data/services/test_portfolio_service.py
- [ ] T032 [❌blocked] 分析PortfolioService的3个CRUD依赖关系 - src/ginkgo/data/services/portfolio_service.py
- [ ] T033 [❌blocked] 更新PortfolioService构造函数支持ServiceHub - src/ginkgo/data/services/portfolio_service.py
- [ ] T034 [❌blocked] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/portfolio_service.py
- [ ] T035 [❌blocked] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/portfolio_service.py
- [ ] T036 [❌blocked] 添加@time_logger、@retry装饰器到复杂方法 - src/ginkgo/data/services/portfolio_service.py
- [ ] T037 [❌blocked] 更新多CRUD事务处理和协调逻辑 - src/ginkgo/data/services/portfolio_service.py
- [ ] T038 [❌blocked] 私有属性标准化(_crud_repo_portfolio, etc.) - src/ginkgo/data/services/portfolio_service.py
- [ ] T039 [❌blocked] 创建PortfolioService依赖协调测试 - test/unit/data/services/test_portfolio_service.py

### EngineService 重构 - ❌ 需要修复 (双CRUD依赖)

- [ ] T040 [❌blocked] 分析EngineService测试架构问题 - test/data/services/test_engine_service.py
- [ ] T041 [❌blocked] 分析EngineService的2个CRUD依赖关系 - src/ginkgo/data/services/engine_service.py
- [ ] T042 [❌blocked] 更新EngineService构造函数支持ServiceHub - src/ginkgo/data/services/engine_service.py
- [ ] T043 [❌blocked] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/engine_service.py
- [ ] T044 [❌blocked] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/engine_service.py
- [ ] T045 [❌blocked] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/engine_service.py
- [ ] T046 [❌blocked] 更新双CRUD协调和状态管理 - src/ginkgo/data/services/engine_service.py
- [ ] T047 [❌blocked] 私有属性标准化(_crud_repo_portfolio, _crud_repo_engine) - src/ginkgo/data/services/engine_service.py
- [ ] T048 [❌blocked] 创建EngineService依赖协调测试 - test/unit/data/services/test_engine_service.py

---

## Phase 3: 🔄 Business Services重构 (2个Service待重构)

### ComponentService 重构 - ❌ 需要修复 (依赖注入问题)

- [ ] T049 [❌blocked] 分析ComponentService模块导入失败问题 - test/data/services/test_component_service.py
- [ ] T050 [❌blocked] 修复'No module named ginkgo.trading.sizers.base_sizer'导入 - src/ginkgo/data/services/component_service.py
- [ ] T051 [❌blocked] 更新ComponentService继承BusinessService基类 - src/ginkgo/data/services/component_service.py
- [ ] T052 [❌blocked] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/component_service.py
- [ ] T053 [❌blocked] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/component_service.py
- [ ] T054 [❌blocked] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/component_service.py
- [ ] T055 [❌blocked] 更新跨服务协调和错误处理 - src/ginkgo/data/services/component_service.py
- [ ] T056 [❌blocked] 创建ComponentService协调测试 - test/unit/data/services/test_component_service.py

### SignalTrackingService 重构 - ❌ 需要重构

- [ ] T057 [❌blocked] 分析SignalTrackingService当前实现 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T058 [❌blocked] 更新SignalTrackingService继承BusinessService基类 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T059 [❌blocked] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T060 [❌blocked] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T061 [❌blocked] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T062 [❌blocked] 更新信号跟踪和状态管理逻辑 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T063 [❌blocked] 创建SignalTrackingService测试 - test/unit/data/services/test_signal_tracking_service.py

### FactorService - 🚫 暂不重构

- [ ] T064 [🚫deferred] FactorService标记为暂不重构 - src/ginkgo/data/services/factor_service.py
- [ ] T065 [🚫deferred] 复杂度评估过高，暂不处理 - src/ginkgo/data/services/factor_service.py

---

## Phase 4: 🔄 Middleware Services重构 (2个Service待重构)

### RedisService 重构 - ❌ 需要修复 (属性架构问题)

- [ ] T066 [❌blocked] 修复RedisService AttributeError: 'crud_repo'属性问题 - test/data/services/test_redis_service.py
- [ ] T067 [❌blocked] 分析RedisService当前架构和缓存模式 - src/ginkgo/data/services/redis_service.py
- [ ] T068 [❌blocked] 更新RedisService遵循BarService模式 - src/ginkgo/data/services/redis_service.py
- [ ] T069 [❌blocked] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/redis_service.py
- [ ] T070 [❌blocked] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/redis_service.py
- [ ] T071 [❌blocked] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/redis_service.py
- [ ] T072 [❌blocked] 更新Redis连接和缓存策略 - src/ginkgo/data/services/redis_service.py
- [ ] T073 [❌blocked] 创建RedisService缓存测试 - test/unit/data/services/test_redis_service.py

### KafkaService 重构 - ❌ 需要重构

- [ ] T074 [❌blocked] 分析KafkaService当前架构和消息处理模式 - src/ginkgo/data/services/kafka_service.py
- [ ] T075 [❌blocked] 更新KafkaService遵循BarService模式 - src/ginkgo/data/services/kafka_service.py
- [ ] T076 [❌blocked] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/kafka_service.py
- [ ] T077 [❌blocked] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/kafka_service.py
- [ ] T078 [❌blocked] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/kafka_service.py
- [ ] T079 [❌blocked] 更新Kafka连接和消息处理逻辑 - src/ginkgo/data/services/kafka_service.py
- [ ] T080 [❌blocked] 创建KafkaService消息测试 - test/unit/data/services/test_kafka_service.py

---

## Phase 5: 🔄 CLI 兼容性修复 (所有Service完成后)

**状态**: 🔄 等待所有Service重构完成后开始

### Data CLI 核心修复

- [ ] T081 [🔄pending] 分析所有13个Service的CLI集成模式 - src/ginkgo/client/data_cli.py
- [ ] T082 [🔄pending] 更新data_cli.py统一处理ServiceResult格式 - src/ginkgo/client/data_cli.py
- [ ] T083 [🔄pending] 更新`ginkgo data update`系列命令适配新API - src/ginkgo/client/data_cli.py
- [ ] T084 [🔄pending] 更新`ginkgo data get`查询命令适配新API - src/ginkgo/client/data_cli.py
- [ ] T085 [🔄pending] 更新`ginkgo data count`计数命令适配新API - src/ginkgo/client/data_cli.py

### CLI 错误处理和用户体验

- [ ] T086 [🔄pending] 添加友好错误信息显示，避免内部异常暴露 - src/ginkgo/client/data_cli.py
- [ ] T087 [🔄pending] 添加Rich进度条支持所有批量操作 - src/ginkgo/client/data_cli.py
- [ ] T088 [🔄pending] 添加详细操作统计(成功/失败数量、耗时) - src/ginkgo/client/data_cli.py
- [ ] T089 [🔄pending] 添加输入验证和参数检查 - src/ginkgo/client/data_cli.py
- [ ] T090 [🔄pending] 添加调试模式支持详细日志 - src/ginkgo/client/data_cli.py

### CLI 测试和验证

- [ ] T091 [🔄pending] 测试所有data CLI命令与13个重构Service的兼容性
- [ ] T092 [🔄pending] 验证CLI错误处理显示友好信息
- [ ] T093 [🔄pending] 测试CLI进度条和统计显示准确性
- [ ] T094 [🔄pending] 测试CLI调试模式功能

---

## Phase 6: 🔄 综合测试和验证 (最终阶段)

**状态**: 🔄 等待所有Service重构完成后开始

### Service 集成测试

- [ ] T095 [🔄pending] 运行所有13个重构Service的综合测试
- [ ] T096 [🔄pending] 测试ServiceHub对所有新标准Service的支持
- [ ] T097 [🔄pending] 验证ServiceResult格式跨所有Service的一致性
- [ ] T098 [🔄pending] 测试跨Service依赖和交互(新+旧Service)
- [ ] T099 [🔄pending] 测试ManagementService的多CRUD协调
- [ ] T100 [🔄pending] 测试BusinessService的跨服务协调
- [ ] T101 [🔄pending] 测试MiddlewareService的缓存和消息功能

### 性能和错误恢复测试

- [ ] T102 [🔄pending] 测试所有Service批量处理性能
- [ ] T103 [🔄pending] 验证装饰器开销最小化
- [ ] T104 [🔄pending] 测试所有Service错误恢复机制
- [ ] T105 [🔄pending] 测试网络中断和缓存故障处理
- [ ] T106 [🔄pending] 测试多CRUD事务处理和回滚

### 最终验证和文档

- [ ] T107 [🔄pending] 验证所有13个Service测试覆盖率>90%
- [ ] T108 [🔄pending] 验证所有CLI命令与重构Service完美集成
- [ ] T109 [🔄pending] 更新所有Service接口文档
- [ ] T110 [🔄pending] 创建完整的迁移指南和变更日志
- [ ] T111 [🔄pending] 验证向后兼容性破坏最小化

---

## 当前进度分析报告

### 📊 **完成度统计**

| Service类别 | 总数 | 已完成 | 进行中 | 待开始 | 完成率 |
|------------|------|--------|--------|--------|---------|
| **DataService** | 4 | ✅ 4 | 0 | 0 | **100%** |
| **ManagementService** | 3 | 0 | 0 | 🔄 3 | **0%** |
| **BusinessService** | 2 | 0 | 0 | 🔄 2 | **0%** |
| **MiddlewareService** | 2 | 0 | 0 | 🔄 2 | **0%** |
| **暂不重构** | 1 | 0 | 0 | 🚫 1 | **0%** |
| **总计** | **12** | ✅ **4** | 0 | 🔄 **7** | **33.3%** |

### 🎯 **关键发现**

#### ✅ **成功因素**
1. **核心DataService完成**: 4/4个时序数据服务100%标准化
2. **测试验证充分**: 75/75测试通过 (100%)
3. **架构统一**: BarService标准成功建立并验证
4. **API一致性**: 标准方法集全面实现
5. **FileService优化**: 搜索功能和get_files→get标准化完成

#### ⚠️ **待解决问题**
1. **ManagementService测试架构**: 所有3个Service测试都存在基础架构问题
2. **依赖注入复杂**: PortfolioService(3个CRUD), EngineService(2个CRUD)
3. **模块导入错误**: ComponentService存在'ginkgo.trading.sizers.base_sizer'缺失
4. **属性架构问题**: RedisService缺少私有属性标准化

#### 🔧 **技术债务**
1. **测试依赖问题**: 部分Service测试失败需要基础设施修复
2. **属性命名不一致**: 一些Service仍在使用非标准属性名
3. **错误处理缺失**: 多个Service缺少统一的错误处理机制

### 🚀 **下一步行动计划**

#### **高优先级** (立即开始)
1. **修复测试基础设施**: 解决GCONF配置和导入问题
2. **重构PortfolioService**: 作为最复杂的ManagementService，建立多CRUD协调模式
3. **依赖注入优化**: 统一ServiceHub模式应用

#### **中优先级** (第二阶段)
1. **EngineService**: 管理双CRUD协调
2. **ComponentService**: 修复模块导入和依赖问题
3. **RedisService**: 缓存中间件现代化

#### **低优先级** (第三阶段)
1. **SignalTrackingService**: 信号跟踪和状态管理
2. **KafkaService**: 消息中间件标准化
3. **CLI兼容性**: 统一命令行接口适配

### 📈 **风险缓解**

1. **分阶段重构**: 避免同时重构多个复杂Service
2. **测试先行**: 每个Service重构前建立测试基础
3. **回滚策略**: 保持Git分支策略，可独立回滚每个Service
4. **适配器支持**: 在重构期间提供新旧接口兼容

**当前状态**: 核心重构已完成33.3%，剩余67%按复杂度和优先级分阶段实施。FileService的搜索功能和get_files→get标准化已完成，为ManagementService重构建立了良好基础。