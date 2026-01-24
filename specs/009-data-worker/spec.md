# Feature Specification: Data Worker容器化部署

**Feature Branch**: `009-data-worker`
**Created**: 2025-01-23
**Status**: Draft
**Input**: User description: "构建data worker，容器化部署"

## Clarifications

### Session 2025-01-23

- **Q**: 数据源配置是否需要独立的DataSourceConfig实体？
  **A**: 否 - 数据源已集成在现有CRUD方法内（如`BarCRUD.get_bars()`），通过GCONF管理
- **Q**: 告警阈值的具体数值是多少？
  **A**: 缺失率>20%触发ERROR，>5%触发WARNING；延迟>10分钟ERROR，>5分钟WARNING
- **Q**: DataQualityReport是否需要实现？
  **A**: 是 - 保留设计作为未来扩展功能（监控告警）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 数据采集Worker容器化部署 (Priority: P1)

系统管理员需要部署数据采集Worker，用于定时从外部数据源获取市场数据并更新到数据库中。

**Why this priority**: 这是核心功能，数据采集是量化交易的基础。没有数据就无法进行策略回测和实时交易。

**Independent Test**: 可以独立测试数据采集功能 - 启动容器后验证数据能够正确从数据源获取并存储到数据库，Worker状态可以通过Redis心跳监控。

**Acceptance Scenarios**:

1. **Given** Docker环境已配置Kafka、Redis、ClickHouse连接，**When** 启动data-worker容器，**Then** Worker成功注册到Redis心跳系统，状态为running
2. **Given** Worker正在运行，**When** 接收到bar_snapshot控制命令，**Then** 从配置的数据源获取最新K线数据并写入ClickHouse
3. **Given** 数据源连接失败，**When** 执行数据采集任务，**Then** 记录错误日志，发送通知，并在下次调度时重试
4. **Given** 容器运行中，**When** 发送stop命令或优雅关闭信号，**Then** Worker完成当前任务后退出，释放所有资源

---

### User Story 2 - 配置热重载 (Priority: P2)

开发者需要支持配置热重载功能，避免频繁重启容器。

**Why this priority**: 灵活的配置管理使系统能够适应不同环境，热重载功能避免频繁重启容器。

**Independent Test**: 可以独立测试配置系统 - 修改配置文件后验证Worker能够热重载配置并立即生效。

**Acceptance Scenarios**:

1. **Given** 配置文件中定义了Worker参数，**When** Worker启动，**Then** 配置加载成功
2. **Given** Worker运行中修改配置文件，**When** 发送reload命令，**Then** 新配置生效，无需重启容器
3. **Given** 配置文件格式错误，**When** Worker尝试加载配置，**Then** 返回友好错误提示，使用默认值继续运行
4. **Given** 配置文件丢失，**When** Worker启动，**Then** 使用硬编码的默认值启动，并记录警告日志

---

### User Story 3 - 数据质量监控与告警 (Priority: P3)

运维人员需要监控数据采集质量，及时发现数据缺失、延迟或异常情况。

**Why this priority**: 数据质量直接影响策略表现，监控告警能够及时发现问题，减少潜在损失。

**Independent Test**: 可以独立测试监控功能 - 模拟数据缺失或异常场景，验证告警通知能够正确发送。

**Acceptance Scenarios**:

1. **Given** 数据采集任务完成，**When** 检测到数据缺失（如预期100条只收到80条），**Then** 发送缺失告警通知
2. **Given** 数据采集延迟超过阈值，**When** 监控系统检查，**Then** 发送延迟告警通知
3. **Given** 检测到异常数据（如价格为负、成交量异常），**When** 数据验证器检查，**Then** 记录异常并跳过该条数据
4. **Given** Worker正常运行，**When** 生成数据质量报告，**Then** 报告包含采集量、成功率、异常统计等指标

---

### Edge Cases

- 网络中断时如何保证数据不丢失（Kafka消息持久化，consumer重试）
- 数据源API限流时的处理策略（延迟重试、降低频率）
- 容器意外崩溃后的状态恢复（Redis心跳TTL自动检测，Kafka rebalance）
- 多个Worker实例的任务分配（Kafka consumer group自动负载均衡）
- 数据库写入失败时的重试和告警机制
- 配置文件语法错误时的降级处理
- 时区差异导致的数据重复采集

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

**Data Worker核心功能**:
- **FR-011**: Data Worker MUST 作为独立容器运行，支持Docker Compose部署
- **FR-012**: Data Worker MUST 订阅Kafka控制命令主题 (ginkgo.live.control.commands)
- **FR-013**: Data Worker MUST 向Redis发送心跳信号，TTL为30秒
- **FR-014**: Data Worker MUST 支持以下控制命令: bar_snapshot, update_selector, update_data, heartbeat_test
- **FR-015**: Data Worker MUST 采用Kafka事件驱动架构，调度由TaskTimer负责
- **FR-016**: Data Worker MUST 支持配置热重载，无需重启容器
- **FR-017**: Data Worker MUST 使用GLOG记录所有操作和错误日志

**数据采集功能**:
- **FR-018**: Data Worker MUST 使用现有CRUD方法获取数据（数据源已集成在方法内，通过GCONF配置）
- **FR-019**: Data Worker MUST 批量写入ClickHouse，单次至少1000条记录
- **FR-020**: Data Worker MUST 在数据采集失败时自动重试，最多3次
- **FR-021**: Data Worker MUST 在数据验证失败时跳过异常数据并记录
- **FR-022**: Data Worker MUST 支持增量更新和全量同步两种模式

**监控与告警**:
- **FR-023**: Data Worker MUST 统计采集量、成功率、失败率等指标
- **FR-024**: Data Worker MUST 在数据缺失超过阈值时发送告警通知（缺失率>20%触发ERROR，>5%触发WARNING）
- **FR-025**: Data Worker MUST 在数据采集延迟超过阈值时发送告警通知（延迟>10分钟触发ERROR，>5分钟触发WARNING）
- **FR-026**: Data Worker MUST 定期生成数据质量报告并推送到ginkgo.notifications主题

**容器化部署**:
- **FR-027**: Data Worker MUST 提供Dockerfile，基于python:3.12.11-slim-bookworm
- **FR-028**: Data Worker MUST 支持环境变量配置数据库连接 (KAFKA_HOST, REDIS_HOST, CLICKHOUSE_HOST等)
- **FR-029**: Data Worker MUST 在docker-compose.yml中定义资源限制 (CPU, 内存)
- **FR-030**: Data Worker MUST 支持容器健康检查 (healthcheck)
- **FR-031**: Data Worker MUST 使用restart: always策略确保自动重启
- **FR-032**: Data Worker MUST 采用"容器即进程"模式，每个容器运行一个Worker进程
- **FR-033**: Data Worker MUST 默认配置4个容器实例，通过docker-compose scale调整
- **FR-034**: Data Worker MUST 使用Kafka consumer group实现多实例负载均衡

**配置管理**:
- **FR-035**: Data Worker MUST 支持通过GCONF读取配置（数据源配置已集成在CRUD方法内）
- **FR-036**: Data Worker MUST 支持环境变量优先级最高
- **FR-037**: Data Worker MUST 在配置缺失时使用合理默认值
- **FR-038**: Data Worker MUST 在配置文件格式错误时返回友好错误提示

**代码维护与文档需求**:
- **FR-039**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-040**: File updates MUST synchronize header descriptions with actual code functionality
- **FR-041**: Header updates MUST be verified during code review process
- **FR-042**: CI/CD pipeline MUST include header accuracy verification

**配置验证需求**:
- **FR-043**: 配置类功能验证 MUST 包含配置文件存在性检查（不仅检查返回值）
- **FR-044**: 配置类验证 MUST 确认值从配置文件读取，而非代码默认值
- **FR-045**: 配置类验证 MUST 确认用户可通过修改配置文件改变行为
- **FR-046**: 配置类验证 MUST 确认缺失配置时降级到默认值
- **FR-047**: 外部依赖验证 MUST 包含存在性、正确性、版本兼容性三维度检查
- **FR-048**: 禁止仅因默认值/Mock使测试通过就认为验证完成（假阳性预防）

### Key Entities

- **DataWorker**: 数据采集Worker主类，继承自threading.Thread，订阅Kafka消费控制命令
  - 位置: `src/ginkgo/data/worker/worker.py`
  - 与data模块内聚，属于数据采集功能的一部分

- **DataQualityReport**: 数据质量报告实体，包含采集量、成功率、异常统计
  - 位置: `src/ginkgo/data/worker/models.py`

- **WorkerStatus**: Worker状态实体，包含运行状态、最后心跳时间、任务执行统计
  - 位置: `src/ginkgo/data/worker/models.py`

**架构决策**: 采用方案2 - 各自模块的worker子目录
```
src/ginkgo/
├── data/
│   ├── worker/                       # 数据采集Worker (本功能)
│   │   ├── worker.py                # DataWorker主类
│   │   └── models.py                # WorkerStatus, DataQualityReport
│   ├── crud/                         # 数据CRUD (BarCRUD等)
│   └── services/                     # 数据服务
├── notifier/
│   └── worker/                       # 通知Worker (已存在)
│       └── worker.py                # NotificationWorker
└── livecore/                         # 实盘交易核心 (TaskTimer等)
```

**Note**: 数据源配置已集成在现有CRUD方法中（如`BarCRUD.get_bars()`），通过GCONF管理，无需额外实体

## Success Criteria *(mandatory)*

### Measurable Outcomes

**性能与响应指标**:
- **SC-001**: 数据采集任务调度延迟 < 5秒（从调度时间到任务开始）
- **SC-002**: 批量数据写入 > 10,000 records/sec（ClickHouse批量插入）
- **SC-003**: 单次数据采集任务完成时间 < 60秒（1000只股票日频数据）
- **SC-004**: 容器启动时间 < 30秒

**数据质量指标**:
- **SC-005**: 数据采集成功率 > 99%（重试后）
- **SC-006**: 数据验证通过率 > 99.9%（异常数据自动过滤）
- **SC-007**: 数据延迟 < 10分钟（从市场收盘到数据可用）
- **SC-008**: 历史数据回填支持 >= 5年日频数据，>= 1年分钟频数据

**系统可靠性指标**:
- **SC-009**: Worker心跳丢失率 < 1%（监控期内）
- **SC-010**: 容器自动恢复成功率 = 100%（restart: always策略）
- **SC-011**: 配置热重载成功率 > 95%
- **SC-012**: 零安全漏洞（所有敏感信息检查通过）

**业务与运维指标**:
- **SC-013**: 告警通知准确率 > 95%（误报率 < 5%）
- **SC-014**: 数据质量报告生成时间 < 10秒
- **SC-015**: 默认部署4个Worker容器实例，支持动态扩缩容

**测试覆盖指标**:
- **SC-016**: 单元测试覆盖率 > 80%
- **SC-017**: 集成测试覆盖所有数据源类型
- **SC-018**: 包含容器部署的端到端测试

## Dependencies & Assumptions

### Dependencies
- Docker和Docker Compose已安装并配置
- Kafka集群正常运行，主题已创建
- Redis集群正常运行，用于心跳和状态存储
- ClickHouse数据库已初始化，表结构已创建
- 网络连接稳定，可访问外部数据源API

### Assumptions
- 数据源API提供稳定的接口，QPS限制在合理范围内
- 时区统一使用UTC或Asia/Shanghai
- 配置文件存储在容器可访问的路径或挂载卷中
- 日志通过标准输出输出，由Docker日志驱动收集
- 用户已配置数据源API密钥等敏感信息

## Out of Scope

以下功能明确不包含在本版本中：
- 实时行情推送（由ExecutionNode负责）
- 策略回测功能（由EngineHistoric负责）
- Web管理界面（未来版本考虑）
- 数据清洗和复权计算（由数据处理模块负责）
- 多云部署支持（仅支持单数据中心）
- 数据导出功能（直接查询数据库）
