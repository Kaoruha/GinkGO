# Implementation Plan: OKX实盘账号API接入

**Branch**: `014-okx-live-account` | **Date**: 2026-03-13 | **Spec**: [spec.md](../specs/014-okx-live-account/spec.md)
**Input**: Feature specification from `/specs/014-okx-live-account/spec.md`

## Summary

本功能实现OKX交易所实盘账号API接入，支持用户配置API凭证、绑定到Portfolio、自动化实盘交易。核心特性包括：

1. **实盘账号管理**：LiveAccount实体存储加密的API凭证，支持OKX/Binance等交易所
2. **Portfolio-LiveAccount绑定**：MPortfolio添加live_account_id外键，实现强制一对一绑定
3. **Broker实例管理**：系统启动时批量创建Broker实例，支持动态生命周期管理和崩溃恢复
4. **实时数据同步**：混合模式（WebSocket推送 + 30秒定时全量校验）
5. **实盘交易执行**：复用回测数据模型（Bar/Position/Order），通过扩展字段区分实盘属性
6. **风控与告警**：Portfolio级别风控配置，支持紧急停止
7. **Web UI控制面板**：支持启动/停止/暂停/恢复，单Portfolio独立控制和全局紧急停止

**技术方案**：
- 使用python-okx SDK集成OKX V5 API
- WebSocket实时推送 + 定时轮询备选
- API凭证加密存储（AES-256）
- DTO模式封装Kafka消息
- 遵循事件驱动架构（PriceUpdate → Strategy → Signal → Portfolio → Order → Fill）

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**:
- python-okx (OKX V5 API SDK)
- ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存/心跳)
- Kafka (消息队列), WebSocket (实时推送)
- Pydantic (DTO验证), Typer (CLI), Rich (终端输出)

**Storage**:
- ClickHouse: K线数据、Tick数据、实盘成交记录
- MySQL: LiveAccount、MPortfolio扩展、BrokerInstance、风控配置
- Redis: Broker心跳、缓存、分布式锁
- MongoDB: 策略配置、复杂结果数据

**Testing**: pytest with TDD workflow, unit/integration/database/network标记分类

**Target Platform**: Linux server (量化交易后端)

**Project Type**: single (Python量化交易库)

**Performance Goals**:
- 订单提交延迟 < 500ms
- 账户信息同步延迟 < 2s
- API调用成功率 > 99%
- 支持 >= 10个并发实盘账号

**Constraints**:
- 必须启用debug模式进行数据库操作
- 遵循事件驱动架构
- 支持分布式worker
- API凭证必须加密存储
- 所有Kafka消息使用DTO包装

**Scale/Scope**:
- 支持多策略并行实盘交易
- 处理实时WebSocket推送
- 实时风控监控
- 崩溃自动恢复

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理
- [x] 敏感配置文件已添加到.gitignore
- [ ] API凭证加密存储实现（Phase 1设计后确认）

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import service_hub`访问服务组件
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责
- [ ] DTO消息队列规范实现（Phase 1设计后确认）

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [x] 提供类型注解，支持静态类型检查
- [x] 禁止使用hasattr等反射机制回避类型错误
- [x] 遵循既定命名约定 (CRUD前缀、模型继承等)

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能
- [x] 测试按unit、integration、database、network标记分类
- [x] 数据库测试使用测试数据库，避免影响生产数据
- [ ] 真实环境测试策略设计（OKX测试网支持）

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法 (如add_bars) 而非单条操作
- [x] 合理使用多级缓存 (Redis + Memory + Method级别)
- [x] 使用懒加载机制优化启动时间

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确，高优先级任务优先显示
- [x] 任务状态实时更新，确保团队协作效率

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [x] 核心API提供详细使用示例和参数说明
- [ ] 重要组件有清晰的架构说明和设计理念文档（Phase 0研究后补充）

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述
- [x] 代码审查过程中检查头部信息的准确性
- [ ] 定期运行`scripts/verify_headers.py`检查头部一致性（CI/CD集成）
- [ ] CI/CD流程包含头部准确性检查
- [ ] 使用`scripts/generate_headers.py --force`批量更新头部

### 验证完整性原则 (Verification Integrity)
- [x] 配置类功能验证包含配置文件检查（不仅检查返回值）
- [x] 验证配置文件包含对应配置项（如 grep config.yml notifications.timeout）
- [x] 验证值从配置文件读取，而非代码默认值（打印原始配置内容）
- [x] 验证用户可通过修改配置文件改变行为（修改配置后重新运行）
- [x] 验证缺失配置时降级到默认值（删除配置项后验证）
- [x] 外部依赖验证包含存在性、正确性、版本兼容性检查
- [x] 禁止仅因默认值/Mock使测试通过就认为验证完成

### DTO消息队列原则 (DTO Message Pattern)
- [x] 所有Kafka消息发送使用DTO包装（ControlCommandDTO等）
- [x] 发送端使用DTO.model_dump_json()序列化
- [x] 接收端使用DTO(**data)反序列化
- [x] 使用DTO.Commands常量类定义命令/事件类型
- [x] 使用DTO.is_xxx()方法进行类型判断
- [x] 禁止直接发送字典或裸JSON字符串到Kafka
- [x] DTO使用Pydantic BaseModel实现类型验证
- [ ] 实盘交易相关DTO定义（Phase 1设计）

**Constitution Gate Status**: ✅ PASS (设计阶段确认所有原则可满足)

## Project Structure

### Documentation (this feature)

```text
.specify/specs/014-default/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
    ├── live-account-api.yml    # LiveAccount CRUD API
    ├── broker-control-api.yml  # Broker控制API
    └── live-trading-dto.md     # Kafka DTO定义
```

### Source Code (repository root)

```text
src/ginkgo/
├── data/
│   ├── models/
│   │   ├── model_live_account.py       # NEW: LiveAccount数据模型
│   │   ├── model_broker_instance.py    # NEW: BrokerInstance数据模型
│   │   ├── model_trade_record.py       # NEW: TradeRecord数据模型
│   │   └── model_portfolio.py          # EXTEND: 添加live_account_id字段
│   ├── cruds/
│   │   ├── live_account_crud.py        # NEW: LiveAccount CRUD
│   │   ├── broker_instance_crud.py     # NEW: BrokerInstance CRUD
│   │   └── trade_record_crud.py        # NEW: TradeRecord CRUD
│   └── services/
│       ├── live_account_service.py      # NEW: LiveAccount业务服务
│       └── encryption_service.py        # NEW: API凭证加密服务
├── trading/
│   ├── brokers/
│   │   ├── okx_broker.py               # NEW/UPDATE: OKX实盘Broker实现
│   │   └── broker_manager.py           # NEW: Broker实例生命周期管理器
│   └── interfaces/
│       └── dtos/
│           ├── live_trading_dto.py     # NEW: 实盘交易相关DTO
│           └── broker_control_dto.py   # NEW: Broker控制DTO
├── livecore/
│   ├── live_engine.py                  # NEW: 实盘引擎入口
│   ├── data_sync_service.py            # NEW: WebSocket数据同步服务
│   └── heartbeat_monitor.py            # NEW: Broker心跳监控服务
└── interfaces/
    └── dtos/
        ├── dto_base.py                  # EXTEND: DTO基类
        └── control_dto.py               # EXTEND: 控制命令DTO

tests/
├── unit/
│   ├── data/
│   │   ├── test_model_live_account.py
│   │   ├── test_live_account_crud.py
│   │   └── test_encryption_service.py
│   ├── trading/
│   │   ├── test_okx_broker.py
│   │   └── test_broker_manager.py
│   └── livecore/
│       ├── test_live_engine.py
│       └── test_data_sync_service.py
├── integration/
│   ├── test_okx_integration.py         # OKX API集成测试
│   └── test_broker_lifecycle.py        # Broker生命周期集成测试
└── network/
    └── test_okx_websocket.py           # OKX WebSocket网络测试

web-ui/                                  # Vue 3前端
├── src/views/live/
│   ├── AccountConfig.vue               # NEW: 实盘账号配置页面
│   ├── AccountInfo.vue                 # NEW: 账户信息展示页面
│   ├── TradeHistory.vue                # NEW: 交易历史查询页面
│   ├── RiskControl.vue                 # NEW: 风控配置页面
│   └── TradingControl.vue              # NEW: 实盘交易控制面板
```

**Structure Decision**: 复用现有Ginkgo项目结构，在数据层添加LiveAccount相关模型和服务，在交易层扩展OKX Broker，在LiveCore添加实盘引擎和同步服务。

## Complexity Tracking

> **No constitution violations requiring justification**

本功能设计严格遵循Ginkgo项目章程，所有架构决策都符合现有原则，无需额外复杂度说明。
