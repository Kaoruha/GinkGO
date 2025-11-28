# Feature Specification: Data Services & CLI Compatibility Fix

**Feature Branch**: `[006-data-service-cli-fix]`
**Created**: 2025-11-28
**Status**: Draft
**Input**: User description: "参考bar_service, 修复所有data 相关service，并修复ginkgo cli相关命令"

## Clarifications

### Session 2025-11-28

- Q: Service方法完整性策略 → A: 定义核心方法集合，各service可根据需要扩展，但同样功能的方法名称也需要统一
- Q: 向后兼容性策略 → A: 允许破坏性更改，但必须提供迁移指南和废弃警告
- Q: Service修复实施优先级 → A: 按依赖关系优先级，先修复基础service，再修复依赖它的service
- Q: 核心方法集合定义 → A: 标准CRUD方法：sync_*（同步）、get_*（查询）、count_*（计数）、validate_*（验证）
- Q: 数据同步幂等性策略 → A: 智能增量同步，基于业务标识符确保幂等性
- Q: 数据完整性检查机制 → A: 多层次检查机制，包括基础记录数检查、业务规则验证和数据质量评分

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 统一Data Service架构 (Priority: P1)

量化开发者在使用不同的data service时，希望所有service都遵循一致的接口规范和错误处理模式，就像BarService一样提供ServiceResult返回和完整的错误处理机制。

**Why this priority**: 统一的service架构是系统稳定性和可维护性的基础，影响所有数据操作的可靠性

**Independent Test**: 可以通过单独修复任何一个data service（如TickService）来验证新架构的可行性，修复后该service应该能正常工作并通过所有测试

**Acceptance Scenarios**:

1. **Given** 现有的TickService返回不一致的数据格式, **When** 调用tick service的任何方法, **Then** 返回统一的ServiceResult格式，包含success、error、data和message字段
2. **Given** StockinfoService缺少错误处理, **When** 数据源出现异常, **Then** 服务应该优雅地处理错误并返回ServiceResult.error，而不是崩溃
3. **Given** AdjustfactorService缺少复权计算支持, **When** 需要进行价格复权, **Then** 服务应该提供完整的前复权、后复权功能

---

### User Story 2 - 修复CLI命令兼容性 (Priority: P1)

用户在使用`ginkgo data update`或`ginkgo get bars`等CLI命令时，希望命令能正常工作并与修复后的data service兼容，提供一致的用户体验。

**Why this priority**: CLI是用户与系统交互的主要界面，命令不可用会严重影响用户体验

**Independent Test**: 可以单独测试一个CLI命令（如`ginkgo data update day --code 000001.SZ`）来验证CLI与service的集成是否正常工作

**Acceptance Scenarios**:

1. **Given** CLI命令使用了旧的service接口, **When** 执行`ginkgo data update day`, **Then** 命令应该能正确处理新的ServiceResult返回格式
2. **Given** CLI缺少错误处理, **When** service操作失败, **Then** CLI应该显示友好的错误信息而不是堆栈跟踪
3. **Given** 用户需要查看数据同步结果, **When** 命令执行完成, **Then** 应该显示详细的同步统计信息（成功数量、失败数量、耗时等）

---

### User Story 3 - 性能优化和错误恢复 (Priority: P2)

系统管理员在生产环境中运行数据同步时，希望系统具有良好的性能和自动恢复能力，能够处理大数据量和网络中断等情况。

**Why this priority**: 生产环境的稳定性和性能直接影响系统的可用性

**Independent Test**: 可以通过模拟网络中断或大数据量场景来测试错误恢复机制和性能优化效果

**Acceptance Scenarios**:

1. **Given** 网络连接不稳定, **When** 批量同步数据, **Then** 系统应该自动重试失败的记录，而不是整个任务失败
2. **Given** 需要处理大量历史数据, **When** 执行批量同步, **Then** 系统应该使用批处理和进度条显示，处理速度应该>= 1000 records/sec
3. **Given** 数据同步过程中断, **When** 重新运行同步任务, **Then** 系统应该能够从断点继续，避免重复处理已有数据

---

### Edge Cases

- 当外部数据源返回空数据或格式异常时，service应该如何处理？
- 当数据库连接失败时，CLI命令应该给出什么提示信息？
- 大批量数据操作时，如何避免内存溢出？
- 多用户并发执行CLI命令时，如何避免数据冲突？

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- **FR-002**: System MUST 使用ServiceHub模式，通过`from ginkgo import services`访问服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、分析层和服务层职责
- **FR-004**: System MUST 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器进行优化
- **FR-005**: System MUST 提供类型注解，支持静态类型检查

**量化交易特有需求**:
- **FR-006**: System MUST 支持多数据源接入 (ClickHouse/MySQL/MongoDB/Redis)
- **FR-007**: System MUST 支持批量数据操作 (如add_bars而非单条插入)
- **FR-008**: System MUST 集成风险管理系统 (PositionRatioRisk, LossLimitRisk等)
- **FR-009**: System MUST 支持多策略并行回测和实时风控
- **FR-010**: System MUST 遵循TDD开发流程，先写测试再实现功能

**Data Service统一化需求**:
- **FR-011**: 所有data service MUST继承相应的BaseService基类（DataService/ManagementService/BusinessService）
- **FR-012**: 所有data service方法 MUST返回ServiceResult对象，而不是原始数据或字典
- **FR-013**: 所有data service MUST使用@retry装饰器处理网络和数据源异常
- **FR-014**: 所有data service MUST使用@time_logger装饰器监控性能
- **FR-015**: 所有data service MUST提供详细的错误信息和操作状态反馈
- **FR-016**: 所有data service MUST实现标准CRUD方法集合：sync_*（同步）、get_*（查询）、count_*（计数）、validate_*（验证）
- **FR-017**: 同样功能的方法名称在所有service中必须保持一致
- **FR-018**: Service可以扩展特定的业务方法，但核心CRUD方法必须实现

**CLI兼容性需求**:
- **FR-019**: CLI命令 MUST正确处理ServiceResult返回格式
- **FR-020**: CLI命令 MUST提供友好的错误信息，不暴露内部异常堆栈
- **FR-021**: CLI命令 MUST支持Rich进度条显示，特别是批量操作
- **FR-022**: CLI命令 MUST提供详细的操作结果统计（成功/失败数量、耗时等）
- **FR-023**: CLI命令 MUST支持调试模式，提供详细的执行日志

**迁移和兼容性需求**:
- **FR-024**: System MUST允许破坏性更改，但必须提供迁移指南和废弃警告
- **FR-025**: System MUST在新旧接口并存期间提供适配器支持

**错误处理和恢复需求**:
- **FR-026**: System MUST实现容错机制，单个记录失败不影响整体批量操作
- **FR-027**: System MUST支持断点续传，避免重复处理已有数据
- **FR-028**: System MUST提供详细的错误报告，包含失败记录的具体原因
- **FR-029**: System MUST支持数据验证，拒绝不符合业务规则的数据
- **FR-030**: System MUST支持事务处理，确保数据一致性

**实施优先级需求**:
- **FR-031**: System MUST按依赖关系优先级修复，先修复基础service（如StockinfoService），再修复依赖它的service

**数据同步幂等性需求**:
- **FR-032**: 同步方法 MUST实现智能增量同步，基于业务标识符确保幂等性
- **FR-033**: 同步方法 MUST能够处理数据库已有数据、部分数据、无数据三种情况
- **FR-034**: 重复执行同步操作 MUST产生一致的结果，不产生重复数据
- **FR-035**: 同步操作 MUST支持断点续传，避免从零开始重复处理

**数据完整性检查需求**:
- **FR-036**: System MUST实现多层次数据检查机制
- **FR-037**: 基础检查 MUST验证记录数量、时间范围和数据完整性
- **FR-038**: 业务规则检查 MUST验证OHLC关系、价格合理性等业务逻辑
- **FR-039**: 数据质量评分 MUST提供量化指标，评估数据可信度
- **FR-040**: 检查结果 MUST包含详细的问题报告和修复建议

### Key Entities *(include if feature involves data)*

- **ServiceResult**: 统一的服务返回格式，包含success、error、data、message、warnings等字段
- **DataService**: 数据同步服务的基类，提供通用的数据获取和保存方法
- **BaseService**: 所有服务的抽象基类，提供依赖注入、日志记录、健康检查等基础功能
- **CLICommand**: CLI命令的抽象封装，处理参数解析、结果格式化、错误显示等
- **ErrorRecovery**: 错误恢复机制，支持重试、断点续传、容错处理
- **DataIntegrityChecker**: 数据完整性检查器，提供多层次数据验证功能
- **SyncStateManager**: 同步状态管理器，跟踪同步进度和确保幂等性
- **BusinessRuleValidator**: 业务规则验证器，验证OHLC关系、价格合理性等量化数据特有规则

## Success Criteria *(mandatory)*

### Measurable Outcomes

**性能与响应指标**:
- **SC-001**: 数据同步操作响应时间 < 5秒（小批量<1000条记录）
- **SC-002**: 批量数据处理速度 > 1,000 records/sec
- **SC-003**: CLI命令启动时间 < 2秒
- **SC-004**: 错误恢复时间 < 30秒（自动重试机制）

**系统可靠性指标**:
- **SC-005**: Data service方法测试覆盖率 > 85%
- **SC-006**: CLI命令测试覆盖率 > 80%
- **SC-007**: 所有data service MUST通过现有测试套件
- **SC-008**: 零数据丢失或损坏（数据完整性检查通过）

**用户体验指标**:
- **SC-009**: CLI命令错误信息清晰度评分 > 90%（用户调研）
- **SC-010**: 批量操作进度显示准确性 100%
- **SC-011**: 用户操作成功率 > 95%（首次使用成功率）
- **SC-012**: 系统故障自动恢复率 > 90%

**代码质量指标**:
- **SC-013**: 所有data service MUST符合BarService的代码规范
- **SC-014**: 所有CLI命令 MUST遵循统一的错误处理模式
- **SC-015**: 代码复用率 > 70%（通过BaseService继承）
- **SC-016**: 技术债务减少 > 50%（通过统一架构重构）

**接口一致性指标**:
- **SC-017**: 核心CRUD方法命名一致性 100%
- **SC-018**: ServiceResult返回格式标准化 100%
- **SC-019**: 装饰器使用覆盖率 > 95%（@time_logger、@retry）
- **SC-020**: 迁移指南完整性 100%（所有破坏性更改）

**数据同步幂等性指标**:
- **SC-021**: 重复同步操作结果一致性 100%
- **SC-022**: 智能增量同步准确率 > 99.5%
- **SC-023**: 断点续传成功率 > 98%
- **SC-024**: 同步状态跟踪准确性 100%

**数据完整性检查指标**:
- **SC-025**: 数据问题检测率 > 95%
- **SC-026**: 业务规则验证准确率 > 99%
- **SC-027**: 数据质量评分与实际情况相关性 > 90%
- **SC-028**: 检查报告完整性 100%