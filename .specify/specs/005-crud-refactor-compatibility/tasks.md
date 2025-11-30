---

description: "完整Data Services重构 - 13个Service全面标准化"
---

# Tasks: Data Services 标准化重构

## 🎯 项目重构范围概览 (更新时间: 2025-12-01)

### 📋 Data下所有Service重构目标 (13个Service)

**DataService类型 (核心时序数据服务)**:
- ✅ AdjustfactorService - 24/24测试通过 (100%) - 已完成
- ✅ BarService - 31/31测试通过 (100%) - 已完成
- ✅ TickService - 11/11测试通过 (100%) - 已完成
- ✅ StockinfoService - 9/9测试通过 (100%) - 已完成

**ManagementService类型 (业务管理服务)**:
- 🔄 FileService - 文件管理服务 (1个CRUD依赖)
- 🔄 PortfolioService - 投资组合服务 (3个CRUD依赖)
- 🔄 EngineService - 引擎管理服务 (2个CRUD依赖)

**BusinessService类型 (业务协调服务)**:
- 🔄 ComponentService - 组件管理服务
- 🔄 SignalTrackingService - 信号跟踪服务
- 🔄 FactorService - 因子管理服务 (暂不重构)

**MiddlewareService类型 (中间件服务)**:
- 🔄 RedisService - Redis缓存服务
- 🔄 KafkaService - Kafka消息服务

**总计**: 13个Service，其中4个已完成，9个待重构

---

**Input**: 基于用户反馈，重构并未完成，需要包含Data下所有13个Service
**Prerequisites**: 4个核心Service已完成，为剩余9个Service提供参考标准

**Tests**: TDD approach with real environment testing required

**Organization**: Tasks organized by service complexity and dependency order

## Format: `[ID] [P?] [Phase] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Phase]**: Service type and complexity indicator
- Include exact file paths for all tasks

## Path Conventions

- **Services**: `src/ginkgo/data/services/`
- **Tests**: `test/unit/data/services/`

<!--

  ============================================================================
  IMPORTANT: This is a comprehensive refactor of ALL 13 Data Services to BarService standard

  All services must follow BarService patterns:
  - ServiceResult return format for all methods
  - @time_logger, @retry decorators
  - Private attributes (_crud_repo, _data_source, etc.)
  - ServiceHub dependency injection
  - TDD workflow with real environment testing
  - Standard methods: get, count, validate, check_integrity

  Refactor Order: Core Data Services → Management Services → Business Services → Middleware Services
  ============================================================================

-->

## Phase 1: ✅ 核心Data Services (已完成 - 参考标准)

### AdjustfactorService - ✅ 已完成 (24/24测试通过)
- [x] T001 [✅completed] 标准化AdjustfactorService继承DataService基类 - src/ginkgo/data/services/adjustfactor_service.py
- [x] T002 [✅completed] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/adjustfactor_service.py
- [x] T003 [✅completed] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/adjustfactor_service.py
- [x] T004 [✅completed] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/adjustfactor_service.py
- [x] T005 [✅completed] 私有属性标准化(_crud_repo, _data_source, _stockinfo_service) - src/ginkgo/data/services/adjustfactor_service.py

### BarService - ✅ 已完成 (31/31测试通过)
- [x] T006 [✅completed] 方法名标准化(get_bars→get, count_bars→count) - src/ginkgo/data/services/bar_service.py
- [x] T007 [✅completed] validate_bars和check_bars_integrity方法更新 - src/ginkgo/data/services/bar_service.py
- [x] T008 [✅completed] ServiceResult格式包装 - src/ginkgo/data/services/bar_service.py
- [x] T009 [✅completed] 私有属性标准化(_adjustfactor_service) - src/ginkgo/data/services/bar_service.py

### TickService - ✅ 已完成 (11/11测试通过)
- [x] T010 [✅completed] 私有属性调整(adjustfactor_service→_adjustfactor_service) - src/ginkgo/data/services/tick_service.py
- [x] T011 [✅completed] AdjustfactorService调用更新使用新get方法 - src/ginkgo/data/services/tick_service.py
- [x] T012 [✅completed] 标准方法验证(get/count/validate/check_integrity) - src/ginkgo/data/services/tick_service.py

### StockinfoService - ✅ 已完成 (9/9测试通过)
- [x] T013 [✅completed] 标准方法验证(get/count/validate/check_integrity) - src/ginkgo/data/services/stockinfo_service.py
- [x] T014 [✅completed] 跨服务API调用更新(get_stockinfo_by_code→get) - src/ginkgo/data/services/bar_service.py, src/ginkgo/data/services/adjustfactor_service.py

---

## Phase 2: 🔄 Management Services重构 (管理服务)

### FileService 重构 (简单ManagementService - 1个CRUD依赖)

- [ ] T015 [ManagementService] 分析FileService当前实现和CRUD依赖 - src/ginkgo/data/services/file_service.py
- [ ] T016 [ManagementService] 更新FileService继承ManagementService基类 - src/ginkgo/data/services/file_service.py
- [ ] T017 [ManagementService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/file_service.py
- [ ] T018 [ManagementService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/file_service.py
- [ ] T019 [ManagementService] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/file_service.py
- [ ] T020 [ManagementService] 私有属性标准化(_crud_repo, _data_source) - src/ginkgo/data/services/file_service.py
- [ ] T021 [ManagementService] 更新错误处理和日志记录 - src/ginkgo/data/services/file_service.py
- [ ] T022 [ManagementService] 创建FileService标准化测试 - test/unit/data/services/test_file_service.py

### PortfolioService 重构 (复杂ManagementService - 3个CRUD依赖)

- [ ] T023 [ManagementService] 分析PortfolioService的3个CRUD依赖关系 - src/ginkgo/data/services/portfolio_service.py
- [ ] T024 [ManagementService] 更新PortfolioService构造函数支持ServiceHub - src/ginkgo/data/services/portfolio_service.py
- [ ] T025 [ManagementService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/portfolio_service.py
- [ ] T026 [ManagementService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/portfolio_service.py
- [ ] T027 [ManagementService] 添加@time_logger、@retry装饰器到复杂方法 - src/ginkgo/data/services/portfolio_service.py
- [ ] T028 [ManagementService] 更新多CRUD事务处理和协调逻辑 - src/ginkgo/data/services/portfolio_service.py
- [ ] T029 [ManagementService] 私有属性标准化(_crud_repo1, _crud_repo2, _crud_repo3) - src/ginkgo/data/services/portfolio_service.py
- [ ] T030 [ManagementService] 创建PortfolioService复杂依赖测试 - test/unit/data/services/test_portfolio_service.py

### EngineService 重构 (复杂ManagementService - 2个CRUD依赖)

- [ ] T031 [ManagementService] 分析EngineService的2个CRUD依赖关系 - src/ginkgo/data/services/engine_service.py
- [ ] T032 [ManagementService] 更新EngineService构造函数支持ServiceHub - src/ginkgo/data/services/engine_service.py
- [ ] T033 [ManagementService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/engine_service.py
- [ ] T034 [ManagementService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/engine_service.py
- [ ] T035 [ManagementService] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/engine_service.py
- [ ] T036 [ManagementService] 更新双CRUD协调和状态管理 - src/ginkgo/data/services/engine_service.py
- [ ] T037 [ManagementService] 私有属性标准化(_crud_repo_portfolio, _crud_repo_engine) - src/ginkgo/data/services/engine_service.py
- [ ] T038 [ManagementService] 创建EngineService依赖协调测试 - test/unit/data/services/test_engine_service.py

---

## Phase 3: 🔄 Business Services重构 (业务协调服务)

### ComponentService 重构 (业务协调服务)

- [ ] T039 [P] [BusinessService] 分析ComponentService当前架构和依赖 - src/ginkgo/data/services/component_service.py
- [ ] T040 [P] [BusinessService] 更新ComponentService继承BusinessService基类 - src/ginkgo/data/services/component_service.py
- [ ] T041 [P] [BusinessService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/component_service.py
- [ ] T042 [P] [BusinessService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/component_service.py
- [ ] T043 [P] [BusinessService] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/component_service.py
- [ ] T044 [P] [BusinessService] 更新跨服务协调和错误处理 - src/ginkgo/data/services/component_service.py
- [ ] T045 [P] [BusinessService] 创建ComponentService协调测试 - test/unit/data/services/test_component_service.py

### SignalTrackingService 重构 (业务协调服务)

- [ ] T046 [P] [BusinessService] 分析SignalTrackingService当前实现 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T047 [P] [BusinessService] 更新SignalTrackingService继承BusinessService基类 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T048 [P] [BusinessService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T049 [P] [BusinessService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T050 [P] [BusinessService] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T051 [P] [BusinessService] 更新信号跟踪和状态管理逻辑 - src/ginkgo/data/services/signal_tracking_service.py
- [ ] T052 [P] [BusinessService] 创建SignalTrackingService测试 - test/unit/data/services/test_signal_tracking_service.py

### FactorService 重构 (暂不重构)
- [ ] T053 [BusinessService] FactorService暂不重构标记 - src/ginkgo/data/services/factor_service.py

---

## Phase 4: 🔄 Middleware Services重构 (中间件服务)

### RedisService 重构 (缓存中间件服务)

- [ ] T054 [P] [MiddlewareService] 分析RedisService当前架构和使用模式 - src/ginkgo/data/services/redis_service.py
- [ ] T055 [P] [MiddlewareService] 更新RedisService遵循BarService模式 - src/ginkgo/data/services/redis_service.py
- [ ] T056 [P] [MiddlewareService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/redis_service.py
- [ ] T057 [P] [MiddlewareService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/redis_service.py
- [ ] T058 [P] [MiddlewareService] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/redis_service.py
- [ ] T059 [P] [MiddlewareService] 更新Redis连接和缓存策略 - src/ginkgo/data/services/redis_service.py
- [ ] T060 [P] [MiddlewareService] 创建RedisService缓存测试 - test/unit/data/services/test_redis_service.py

### KafkaService 重构 (消息中间件服务)

- [ ] T061 [P] [MiddlewareService] 分析KafkaService当前架构和生产者/消费者模式 - src/ginkgo/data/services/kafka_service.py
- [ ] T062 [P] [MiddlewareService] 更新KafkaService遵循BarService模式 - src/ginkgo/data/services/kafka_service.py
- [ ] T063 [P] [MiddlewareService] 实现标准方法集(get/count/validate/check_integrity) - src/ginkgo/data/services/kafka_service.py
- [ ] T064 [P] [MiddlewareService] 所有方法返回ServiceResult格式 - src/ginkgo/data/services/kafka_service.py
- [ ] T065 [P] [MiddlewareService] 添加@time_logger、@retry装饰器 - src/ginkgo/data/services/kafka_service.py
- [ ] T066 [P] [MiddlewareService] 更新Kafka连接和消息处理逻辑 - src/ginkgo/data/services/kafka_service.py
- [ ] T067 [P] [MiddlewareService] 创建KafkaService消息测试 - test/unit/data/services/test_kafka_service.py

---

## Phase 5: 🔄 CLI 兼容性修复 (所有Service完成后)

### Data CLI 核心修复

- [ ] T068 [CLI] 分析所有13个Service的CLI集成模式 - src/ginkgo/client/data_cli.py
- [ ] T069 [CLI] 更新data_cli.py统一处理ServiceResult格式 - src/ginkgo/client/data_cli.py
- [ ] T070 [CLI] 更新`ginkgo data update`系列命令适配新API - src/ginkgo/client/data_cli.py
- [ ] T071 [CLI] 更新`ginkgo data get`查询命令适配新API - src/ginkgo/client/data_cli.py
- [ ] T072 [CLI] 更新`ginkgo data count`计数命令适配新API - src/ginkgo/client/data_cli.py

### CLI 错误处理和用户体验

- [ ] T073 [CLI] 添加友好错误信息显示，避免内部异常暴露 - src/ginkgo/client/data_cli.py
- [ ] T074 [CLI] 添加Rich进度条支持所有批量操作 - src/ginkgo/client/data_cli.py
- [ ] T075 [CLI] 添加详细操作统计(成功/失败数量、耗时) - src/ginkgo/client/data_cli.py
- [ ] T076 [CLI] 添加输入验证和参数检查 - src/ginkgo/client/data_cli.py
- [ ] T077 [CLI] 添加调试模式支持详细日志 - src/ginkgo/client/data_cli.py

### CLI 测试和验证

- [ ] T078 [CLI] 测试所有data CLI命令与13个重构Service的兼容性
- [ ] T079 [CLI] 验证CLI错误处理显示友好信息
- [ ] T080 [CLI] 测试CLI进度条和统计显示准确性
- [ ] T081 [CLI] 测试CLI调试模式功能

---

## Phase 6: 🔄 综合测试和验证 (最终阶段)

### Service 集成测试

- [ ] T082 [Integration] 运行所有13个重构Service的综合测试
- [ ] T083 [Integration] 测试ServiceHub对所有新标准Service的支持
- [ ] T084 [Integration] 验证ServiceResult格式跨所有Service的一致性
- [ ] T085 [Integration] 测试跨Service依赖和交互(新+旧Service)
- [ ] T086 [Integration] 测试ManagementService的多CRUD协调
- [ ] T087 [Integration] 测试BusinessService的跨服务协调
- [ ] T088 [Integration] 测试MiddlewareService的缓存和消息功能

### 性能和错误恢复测试

- [ ] T089 [Performance] 测试所有Service批量处理性能
- [ ] T090 [Performance] 验证装饰器开销最小化
- [ ] T091 [Resilience] 测试所有Service错误恢复机制
- [ ] T092 [Resilience] 测试网络中断和缓存故障处理
- [ ] T093 [Resilience] 测试多CRUD事务处理和回滚

### 最终验证和文档

- [ ] T094 [Final] 验证所有13个Service测试覆盖率>90%
- [ ] T095 [Final] 验证所有CLI命令与重构Service完美集成
- [ ] T096 [Final] 更新所有Service接口文档
- [ ] T097 [Final] 创建完整的迁移指南和变更日志
- [ ] T098 [Final] 验证向后兼容性破坏最小化

---

## Dependencies & Execution Order

### Service Dependencies (必须按顺序)

1. **Core Data Services First**: ✅ 已完成 (4个Service)
   - AdjustfactorService, BarService, TickService, StockinfoService
   - 这些提供基础数据能力，是其他Service的依赖基础

2. **Management Services Second**: 🔄 进行中 (3个Service)
   - FileService → PortfolioService → EngineService (按复杂度递增)
   - 依赖稳定的Data Services，管理业务实体

3. **Business Services Third**: 🔄 进行中 (2个Service)
   - ComponentService, SignalTrackingService (可并行)
   - 协调其他Service之间的交互

4. **Middleware Services Fourth**: 🔄 进行中 (2个Service)
   - RedisService, KafkaService (可并行)
   - 提供缓存和消息传递能力

5. **CLI Integration Final**: 🔄 待开始
   - 必须等待所有Service重构完成

### Parallel Execution Opportunities

- **Management Services Phase**: T015-T022 可在T014完成后并行开始
- **Business Services Phase**: T039-T052 可在T038完成后并行开始
- **Middleware Services Phase**: T054-T067 可在T052完成后并行开始

### Critical Path (关键路径)

T001-T014 (✅ 已完成) → T023-T038 (Management Services) → T068-T081 (CLI Integration) → T098 (Final Validation)

---

## Implementation Strategy

### Focus Areas

1. **ServiceResult Standardization**: 所有Service方法统一返回格式
2. **Decorator Optimization**: @time_logger, @retry 100%覆盖
3. **Dependency Injection**: ServiceHub模式全面应用
4. **Error Handling**: 统一、用户友好的错误信息
5. **Private Attributes**: _crud_repo, _data_source 模式一致性

### Quality Gates

- **Code Coverage**: 所有Service > 90% 测试覆盖
- **Performance**: 装饰器开销 < 5%
- **Error Handling**: 所有异常优雅处理
- **Integration**: CLI与所有Service无缝集成
- **Consistency**: 所有Service接口100%统一

### Success Metrics

- **13/13 Service重构完成**: 包含4个已完成 + 9个待重构
- **100%测试通过**: 所有Service测试套件
- **CLI完美集成**: 所有命令工作正常
- **架构统一**: 完全遵循BarService标准

---

## Risk Mitigation

### High-Risk Areas

1. **复杂Management Services**: PortfolioService(3个CRUD), EngineService(2个CRUD)
   - 缓解: 逐步重构，保持事务完整性

2. **跨Service依赖**: 新旧Service并存期间的兼容性
   - 缓解: 详细测试，提供适配器

3. **CLI兼容性**: 13个Service的统一适配
   - 缓解: 分阶段适配，充分测试

### Rollback Strategy

- 保持Git分支策略，每个Service重构后可独立回滚
- 提供新旧接口并存期间的适配器支持
- 详细的变更日志和迁移指南

---

**Total Task Count**: 98 tasks
**Estimated Timeline**: 4-5 weeks for complete refactor
**Critical Path**: 28 core tasks for main refactoring effort

**Note**: 这是包含所有13个Data Services的全面系统重构，以BarService为统一标准，确保整个数据服务层的架构一致性和可维护性。

**项目状态**: 4/13 Service已完成 (30.8%)，9/13 Service待重构 (69.2%)