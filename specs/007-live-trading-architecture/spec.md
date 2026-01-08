# Feature Specification: 实盘多Portfolio架构支持

**Feature Branch**: `007-live-trading-architecture`
**Created**: 2026-01-03
**Status**: Draft
**Input**: User description: "按照整个架构设计，增加新的功能，实盘支持"

## Architecture Design

### Clarifications

#### Session 2026-01-04

- **Q: 除了PortfolioProcessor，其他组件是否都严格按照六边形架构约束来设计**
  - **A: 是** - PortfolioProcessor暂时放宽架构约束以快速实现功能，其他所有组件（ExecutionNode、API Gateway、DataManager、TradeGatewayAdapter、Scheduler、Redis、Kafka）都必须严格按照六边形架构边界表中的约束执行。PortfolioProcessor的架构重构推迟到Phase 8（Polish阶段）进行。

- **Q: PortfolioProcessor是否触碰到六边形架构的设计边界**
  - **A: 是，但允许暂时违反** - 当前PortfolioProcessor持有ExecutionNode引用并使用callback机制提交订单，违反了"不能持有ExecutionNode引用"的约束。暂时允许此违反以快速实现功能，Phase 8重构为双队列模式。

- **Q: PortfolioProcessor与ExecutionNode的通信机制**
  - **A: input/output双队列** - PortfolioProcessor使用双队列与ExecutionNode解耦通信：
    - **input_queue**: ExecutionNode → PortfolioProcessor（接收Kafka事件DTO）
    - **output_queue**: PortfolioProcessor → ExecutionNode（发送订单等领域事件）
    - ExecutionNode监听output_queue，序列化事件并发送到Kafka
    - PortfolioProcessor不持有ExecutionNode引用（Phase 8目标）

- **Q: "暂时允许违反架构边界"的具体含义**
  - **A: 增量交付原则** - "暂时允许违反"是指**当前任务先接受部分过界实现，以后再重构**，这是增量开发和架构演进的实践原则：
    - **目标导向**: 优先完成功能任务，允许架构暂时不完美
    - **技术债务记录**: 明确记录违反的部分，承诺在后续阶段重构
    - **分阶段重构**: Phase 3快速实现功能，Phase 8进行架构重构
    - **双队列准备**: Phase 3已经创建output_queue基础，为Phase 8重构做准备
    - **渐进式改进**: 从callback模式 → 双队列模式 → 完全解耦，逐步演进

- **Q: 双队列模式的实际实施状态**
  - **A: 已完成** - 已从callback模式完全切换到双队列模式：
    - ✅ 移除PortfolioProcessor的callback注入逻辑
    - ✅ 移除ExecutionNode.submit_order()方法
    - ✅ Portfolio通过put()发布事件到PortfolioProcessor
    - ✅ PortfolioProcessor._handle_portfolio_event()将事件放入output_queue
    - ✅ ExecutionNode监听output_queue，序列化并发送到Kafka
    - ✅ Portfolio不再持有ExecutionNode引用
    - ✅ 完全符合六边形架构约束（Domain Kernel不依赖Adapter）

- **Q: Portfolio内部的Selector、Sizer、Strategy是否可以访问数据库**
  - **A: 暂时接受架构违反** - Portfolio内部的Selector、Sizer、Strategy可能有数据库查询，这违反了"Domain Kernel不能访问数据库"的六边形架构约束：
    - **当前状态**: 允许Selector/Sizer/Strategy查询数据库（获取历史数据、股票信息等）
    - **架构违反**: Domain Kernel（Portfolio及其组件）不应该直接访问数据库
    - **重构时机**: **本Feature完成后，专门思考如何重构**（不是Phase 8，而是Feature完成后的独立任务）
    - **重构范围**: 需要分析并设计ExecutionNode如何预加载数据并组装完整上下文DTO
    - **技术债务**: 明确记录此违反，作为Feature完成后的架构优化任务

### 六边形架构边界（Hexagonal Architecture）

实盘交易架构采用**六边形架构（端口和适配器）**模式，严格区分领域内核与外部适配器。

| 模块 | 架构层 | 必须做的事 | 禁止做的事 |
|------|--------|-----------|------------|
| **API Gateway** | Driving Adapter | 接收HTTP，鉴权，**转命令事件并发Kafka**（仅ControlCommand） | ❌写业务规则<br>❌碰Redis/DB<br>❌返回聚合根<br>❌发业务计算结果事件 |
| **DataManager** | Driven Adapter | 取行情，发EventPriceUpdate | ❌算信号<br>❌本地缓存<br>❌下单 |
| **TradeGatewayAdapter** | Driven Adapter | 把订单事件→券商API，回报事件发回 | ❌决定交易<br>❌改仓位<br>❌本地存成交 |
| **ExecutionNode** | Runtime Container Adapter | 管理线程与队列，**负责把Processor产出事件发Kafka** | ❌调Processor业务方法<br>❌缓存权重/信号<br>❌直接用Instant.now() |
| **Redis** | Driven Adapter | 只存`<portfolioId,nodeId,ts>`路由映射+TTL | ❌存权重、仓位、信号等业务数据 |
| **Kafka Topics** | Port Contract | 传序列化DTO，带`_v`版本字段 | ❌传原始Entity或类名 |
| **Scheduler** | Application Service | 定时/事件触发→调内核算映射→发schedule事件+写Redis原子 | ❌new PortfolioProcessor<br>❌事务内调外部HTTP<br>❌写业务公式 |
| **PortfolioProcessor** | Domain Kernel | 纯内存：收DTO→算新聚合根+领域事件，**经队列交ExecutionNode发Kafka** | ❌**直接发Kafka**<br>❌开DB/Redis<br>❌依赖Spring<br>❌用Instant.now()（用Clock）<br>❌持有ExecutionNode引用 |

**核心架构原则**：

1. **PortfolioProcessor（领域内核）完全隔离**：
   - 纯内存计算，不依赖外部系统
   - 所有输出通过队列交给ExecutionNode
   - 不能直接访问Kafka、Redis、DB

2. **ExecutionNode（容器适配器）的唯一职责**：
   - 管理Processor生命周期和线程
   - 订阅Kafka并路由DTO到Processor
   - **负责把Processor产出的领域事件序列化为DTO并发到Kafka**
   - 不能调用Processor的业务方法

3. **Redis只做路由存储**：
   - 仅存储`portfolioId -> nodeId`映射关系
   - TTL自动清理过期节点
   - 不存储任何业务数据（仓位、信号、权重等）

4. **Kafka传DTO不传Entity**：
   - 所有消息使用dataclass/pydantic DTO
   - 带`_v`版本字段支持演进
   - 不传输领域Entity或Event对象

### 系统架构概述

实盘交易架构采用**分布式事件驱动架构**，核心设计原则是**无状态组件**和**水平可扩展**。系统分为三大核心容器类型：

#### 1. API Gateway容器（控制层）

**职责**: 提供通用的HTTP API入口，接收外部控制命令和查询请求（支持回测、实盘等所有模块）

**核心功能**:
- **FastAPI应用入口**: 提供RESTful API接口
- **请求路由**: 将控制命令路由到后端服务（通过Kafka/Redis）
- **参数验证**: 验证请求参数合法性
- **调用后端**: 通过Kafka/Redis调用后端服务（LiveCore、回测引擎等）

**设计原则**: 简单优先，核心功能优先。认证、鉴权、限流等功能未来再添加。

**扩展性设计原则**:
- **控制入口抽象**: 控制层不应只限于HTTP API，必须支持CLI、未来Data模块等多种入口
- **零改造成本**: 新增控制入口时（如接入Data模块控制），应通过Kafka Topic发布命令，无需修改现有控制层代码
- **命令统一格式**: 所有控制命令通过`ginkgo.live.control.commands` topic发布，订阅者无需关心命令来源（HTTP/CLI/Data）

**API分类**:
- **引擎控制**: `/api/engine/*` - 启动/停止/状态查询（回测+实盘）
- **调度管理**: `/api/schedule/*` - 负载均衡/迁移/配置（实盘专用）
- **Portfolio管理**: `/api/portfolio/*` - CRUD操作（回测+实盘）
- **Node管理**: `/api/nodes/*` - 查询/禁用节点（实盘专用）
- **数据管理**: `/api/data/*` - 数据更新、查询（通用）
- **监控查询**: `/api/metrics/*` - 性能指标/健康状态（通用）

**部署特点**:
- 独立部署，单实例运行
- 对外暴露HTTP端口（8000）
- 不处理业务逻辑，仅做控制层和路由

#### 2. LiveCore服务容器（业务逻辑层）

**职责**: 提供数据源管理、实盘引擎驱动、交易网关适配和Portfolio调度服务

**线程模型**（多线程容器）:
- **主线程**: LiveCore主入口，管理所有组件生命周期
- **DataManager线程**: 订阅数据源，发布市场数据到Kafka `ginkgo.live.market.data`
- **LiveEngine线程**: 订阅Kafka `ginkgo.live.orders.submission`，调用TradeGateway执行订单
- **Scheduler线程**: 定时执行调度算法，分配Portfolio到ExecutionNode

**组件组成**:
- **main.py**: LiveCore容器主入口，启动和管理所有组件线程
- **DataManager**: 数据源管理器，负责从外部数据源获取实时行情数据并发布到Kafka
- **LiveEngine**: 实盘引擎容器，封装 `trading/engines/engine_live.py`，订阅订单Kafka并处理
- **TradeGatewayAdapter**: 交易网关适配器，封装 `trading/gateway/trade_gateway.py`，提供Kafka订单发布适配
- **Scheduler**: Portfolio调度器，负责Portfolio到ExecutionNode的分配、负载均衡、故障恢复

**目录结构**:
```
src/ginkgo/livecore/
├── main.py                      # LiveCore主入口（多线程容器）
├── data_manager.py              # 数据源管理器
├── live_engine.py               # 实盘引擎容器线程
├── trade_gateway_adapter.py     # 交易网关适配器
└── scheduler.py                 # 调度器
```

**日志输出**:
- 所有组件线程的日志统一输出到主进程GLOG
- GLOG线程安全，支持Rich格式化输出
- 日志格式包含进程ID `P:%(process)d`，可区分不同组件

**部署特点**:
- 单进程多线程部署（统一日志输出）
- **无状态设计**：
  - **Redis只存储路由映射**：`<portfolioId, nodeId, timestamp>` + TTL自动清理
  - **Redis不存储业务数据**：仓位、权重、信号等业务数据存在MySQL/ClickHouse
  - 每次重启从Redis恢复路由映射，从数据库恢复Portfolio配置
  - 支持LiveCore重启后无缝恢复调度
- 业务数据持久化到MySQL/ClickHouse，路由映射存储在Redis
- 通过Kafka与ExecutionNode通信

**Redis数据结构**（仅路由映射）:
```
# Portfolio路由映射
ginkgo:live:portfolio:{portfolio_id}:node -> {node_id, timestamp}
TTL: 60秒

# ExecutionNode心跳
ginkgo:live:node:{node_id}:heartbeat -> {timestamp}
TTL: 30秒

# 调度计划（Scheduler写入）
ginkgo:live:schedule:plan -> {portfolio_assignments: {...}}
TTL: 永久
```

#### 3. ExecutionNode执行节点（Portfolio运行层）

**架构层**: Runtime Container Adapter（运行时容器适配器）

**职责**:
1. **管理PortfolioProcessor生命周期**（创建、启动、停止、销毁、监控）
2. 订阅Kafka并路由DTO到Processor
3. **负责把Processor产出事件序列化为DTO并发到Kafka**

**核心功能**:
- **PortfolioProcessor生命周期管理**:
  - `load_portfolio(portfolio_id)`: 从数据库加载配置，创建Portfolio实例和Processor
  - `unload_portfolio(portfolio_id)`: 优雅停止Processor并清理资源
  - `reload_portfolio(portfolio_id)`: 配置更新时优雅重启Processor
  - 监控Processor健康状态（线程存活、队列深度等）
- **Kafka消息路由**:
  - 订阅Kafka市场数据Topic（Node级别订阅）
  - 反序列化Kafka DTO并路由到PortfolioProcessor
  - 从output_queue取Processor产出的领域事件，序列化为DTO并发到Kafka
- **内部路由机制**:
  - 通过`interest_map`路由消息到PortfolioProcessor
  - 实现backpressure机制防止消息溢出
- **状态上报**:
  - 定时发送心跳到Redis（TTL=30秒）
  - 上报Portfolio状态到Redis（运行中、停止中、已停止等）
  - 订阅Kafka ginkgo.live.schedule.updates topic接收配置更新通知

**关键约束**（六边形架构边界）:
- ✅ **可以**：管理Processor生命周期（创建、启动、停止、销毁）
- ✅ **可以**：管理线程、队列、Kafka Producer/Consumer
- ✅ **可以**：序列化/反序列化DTO
- ✅ **可以**：把Processor产出事件发到Kafka
- ✅ **可以**：监控Processor健康状态（线程、队列等）
- ❌ **禁止**：调用Processor的业务方法（如on_price_update、on_order_filled）
- ❌ **禁止**：修改Portfolio内部状态（持仓、资金等）
- ❌ **禁止**：缓存业务数据（权重、仓位、信号等）
- ❌ **禁止**：执行业务计算（策略、风控逻辑等）
- ❌ **禁止**：直接用Instant.now()（必须传入Clock）

**事件流设计**:
```
Kafka (DTO) → ExecutionNode.deserialize() → Processor.input_queue
                                        ↓
                                 PortfolioProcessor
                                 (纯内存计算)
                                        ↓
                              Processor.output_queue
                                        ↓
                         ExecutionNode.serialize() → Kafka (DTO)
```

**ExecutionNode管理Processor示例**:
```python
class ExecutionNode:
    """Runtime Container Adapter - 管理PortfolioProcessor生命周期"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.processors: Dict[str, PortfolioProcessor] = {}
        self.portfolios: Dict[str, Portfolio] = {}  # ExecutionNode持有唯一实例

    def load_portfolio(self, portfolio_id: str) -> bool:
        """加载Portfolio并创建Processor"""
        # 1. 从数据库加载配置
        portfolio_config = self._load_config_from_db(portfolio_id)

        # 2. 创建Portfolio实例（ExecutionNode持有）
        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            **portfolio_config
        )
        self.portfolios[portfolio_id] = portfolio

        # 3. 创建队列
        input_queue = Queue(maxsize=1000)
        output_queue = Queue(maxsize=1000)

        # 4. 创建Processor（传入Portfolio引用，不持有ExecutionNode引用）
        processor = PortfolioProcessor(
            portfolio=portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            clock=self.clock
        )

        # 5. 启动Processor线程
        processor.start()
        self.processors[portfolio_id] = processor

        # 6. 注册output_queue监听器（ExecutionNode负责序列化并发Kafka）
        self._start_output_queue_listener(output_queue, portfolio_id)

        return True

    def unload_portfolio(self, portfolio_id: str) -> bool:
        """优雅停止Processor"""
        processor = self.processors.get(portfolio_id)
        if not processor:
            return False

        # 1. 优雅停止Processor
        processor.graceful_stop()  # 等待队列清空

        # 2. 清理资源
        del self.processors[portfolio_id]
        del self.portfolios[portfolio_id]

        return True

    def _start_output_queue_listener(self, queue: Queue, portfolio_id: str):
        """监听Processor的output_queue并序列化发Kafka"""
        def listener_thread():
            while self.is_running:
                try:
                    # 从队列取领域事件
                    domain_event = queue.get(timeout=0.1)

                    # 序列化为DTO
                    dto = self._domain_event_to_dto(domain_event)

                    # 发到Kafka
                    self.kafka_producer.send("ginkgo.live.orders.submission", dto)

                except Exception as e:
                    GLOG.error(f"Error processing output_queue: {e}")

        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.start()
```

**队列设计**:
- **input_queue**：Processor从队列取DTO并处理（ExecutionNode放入）
- **output_queue**：Processor把领域事件放入队列（ExecutionNode取出并发Kafka）
- 两个队列解耦Processor和ExecutionNode，确保Processor不依赖Kafka

**InterestMap机制**:
```
ExecutionNode内部数据结构:
interest_map: {
    "000001.SZ": [portfolio_1_uuid, portfolio_3_uuid],
    "000002.SZ": [portfolio_2_uuid],
    ...
}
```

#### 4. PortfolioProcessor处理器线程（领域内核）

**架构层**: Domain Kernel（领域内核）

**职责**: 纯内存计算，接收DTO→计算聚合根状态+生成领域事件→通过output_queue交给ExecutionNode发Kafka

**核心功能**:
- 从input_queue取DTO（ExecutionNode反序列化后放入）
- 调用Portfolio.on_price_update()等业务方法（纯内存计算）
- 生成领域事件（Signal、Order等）
- **把领域事件放入output_queue**（ExecutionNode取出并序列化发Kafka）

**关键约束**（六边形架构边界）:
- ✅ **可以**：纯内存计算、生成领域事件
- ✅ **可以**：访问Portfolio实例（策略、风控、持仓等）
- ✅ **可以**：使用Clock接口获取时间（不能用Instant.now()）
- ❌ **禁止**：**直接发Kafka**（必须通过output_queue）
- ❌ **禁止**：**持有ExecutionNode引用**（解耦）
- ❌ **禁止**：开DB/Redis连接
- ❌ **禁止**：依赖Spring或任何DI框架

**队列设计**:
- **input_queue**: 接收Kafka DTO（ExecutionNode放入）
- **output_queue**: 输出领域事件（ExecutionNode取出并序列化发Kafka）

**线程模型**:
```python
class PortfolioProcessor(threading.Thread):
    def __init__(self, portfolio: Portfolio,
                 input_queue: Queue,
                 output_queue: Queue,
                 clock: Clock):
        self.portfolio = portfolio  # Portfolio实例引用
        self.input_queue = input_queue  # 输入队列（DTO）
        self.output_queue = output_queue  # 输出队列（领域事件）
        self.clock = clock  # 时间接口（不能用Instant.now()）

    def run(self):
        while self.is_running:
            # 从队列取DTO
            dto = self.input_queue.get(timeout=0.1)

            # 转换为领域事件
            event = self.dto_to_event(dto)

            # 调用Portfolio业务方法（纯内存计算）
            self.portfolio.on_price_update(event)

            # Portfolio生成的领域事件通过callback返回
            # Portfolio不直接发Kafka，而是通过output_queue
            # (ExecutionNode监听output_queue并序列化发Kafka)
```

**与ExecutionNode的解耦**:
- PortfolioProcessor不持有ExecutionNode引用
- 通过input_queue/output_queue双向通信
- ExecutionNode负责序列化/反序列化和Kafka通信
- PortfolioProcessor只负责纯内存业务计算

**部署特点**:
- 可水平扩展至10+个实例
- 每个Node独立运行，互不干扰
- 支持动态添加/删除Node
- 配置从数据库加载，无需配置文件

### LiveCore与ExecutionNode关系

**关系定位**:
- **LiveCore**: 中央控制服务容器，负责管理多个ExecutionNode实例
  - **DataManager**: 统一的数据源管理器，为所有ExecutionNode提供市场数据
  - **TradeGatewayAdapter**: 交易网关适配器，封装TradeGateway处理订单执行和回报
  - **Scheduler**: 调度器，负责Portfolio在ExecutionNode之间的分配和迁移

- **ExecutionNode**: Portfolio执行节点，是Portfolio的实际运行环境
  - 运行3-5个Portfolio实例
  - 通过Kafka订阅LiveCore.Data发布的行情数据
  - 通过Kafka向TradeGatewayAdapter提交订单
  - 通过Redis与LiveCore.Scheduler通信（心跳、状态、调度计划）

**通信模式**:
```
┌─────────────────────────────────────────────────────────────────┐
│                         LiveCore (单实例)                        │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐      │
│  │  DataManager │  │TradeGatewayAdapter│  │  Scheduler   │      │
│  │  (数据源)     │  │  (订单执行/回报)   │  │  (调度器)     │      │
│  └──────┬───────┘  └────────┬─────────┘  └──────┬───────┘      │
└─────────┼───────────────────┼───────────────────┼────────────────┘
          │                   │                   │
         Kafka               Kafka               Redis
    (market.data)      (orders.submission/    (心跳/状态)
                         feedback)
          │                   │                   │
    ┌─────┴─────┬────────┬───┴────┬────────┬───┴────┐
    │           │        │         │        │        │
┌───▼────┐  ┌──▼─────┐ ┌▼──────┐ ┌▼──────┐ ┌▼──────┐ ┌▼──────┐
│ Node-1 │  │ Node-2 │ │ Node-3│ │ Node-4│ │Node-5 │ │ Node-6│
│(3-5    │  │(3-5    │ │(3-5   │ │(3-5   │ │(3-5   │ │(3-5   │ │
│ Portf.) │  │ Portf.)│ │ Portf.)│ │ Portf.)│ │ Portf.)│ │ Portf.)│
└────────┘  └────────┘ └───────┘ └───────┘ └───────┘ └───────┘

说明：
1. DataManager → Kafka → ExecutionNode: 单向数据流（行情数据）
2. ExecutionNode → Kafka → LiveEngine: 单向订单流（订单提交）
3. LiveEngine → Kafka → ExecutionNode: 单向反馈流（订单回报）
4. ExecutionNode ↔ Redis ↔ Scheduler: 双向状态同步（心跳、调度）
```

**通信特点**:
- **解耦设计**: LiveCore与ExecutionNode通过Kafka和Redis完全解耦，互不依赖
- **数据隔离**: 每个ExecutionNode独立处理自己的Portfolio，状态完全隔离
- **集中管理**: Scheduler通过Redis统一管理所有ExecutionNode的心跳和调度计划
- **弹性伸缩**: 支持动态添加/删除ExecutionNode，无需修改LiveCore代码

### 消息层设计（Events vs Messages vs DTOs）

Ginkgo实盘交易架构明确区分**事件**、**消息**和**DTO**三个概念：

#### 事件（Events）- `src/ginkgo/trading/events/`
- **用途**: 事件驱动引擎内部流转（领域层）
- **基类**: 继承`EventBase`
- **特点**: 有uuid、event_type、source等完整属性
- **示例**: `EventPriceUpdate`, `EventOrderPartiallyFilled`, `EventSignalGeneration`
- **传输**: 在内存中通过EventEngine分发，不经过Kafka

#### 消息（Messages）- `src/ginkgo/messages/`
- **用途**: Kafka控制命令传输（应用层）
- **基类**: 使用dataclass或普通类，**不继承EventBase**
- **特点**: 轻量级，专注于序列化/反序列化
- **示例**: `ControlCommand`
- **传输**: 通过Kafka JSON序列化传输

#### DTO（Data Transfer Objects）- `src/ginkgo/dtos/`
- **用途**: Kafka业务数据传输（端口适配器层）
- **基类**: 使用Pydantic或dataclass，**带_v版本字段**
- **特点**: 轻量级DTO，支持版本演进
- **示例**: `PriceUpdateDTO_v1`, `OrderSubmissionDTO_v1`
- **传输**: 通过Kafka JSON序列化传输
- **关键约束**:
  - ✅ 每个DTO必须带`_v`版本字段（如`PriceUpdateDTO_v1`）
  - ❌ 禁止传输领域Entity或Event对象
  - ❌ 禁止传输复杂嵌套对象

**DTO设计示例**:
```python
@dataclass
class PriceUpdateDTO_v1:
    """价格更新DTO（版本1）"""
    _v: str = "v1"  # 版本字段（必须）
    code: str
    price: Decimal
    volume: int
    timestamp_iso: str  # ISO格式字符串，不用datetime对象

    def to_domain_event(self) -> EventPriceUpdate:
        """转换为领域事件（ExecutionNode调用）"""
        return EventPriceUpdate(
            code=self.code,
            price=self.price,
            volume=self.volume,
            timestamp=datetime.fromisoformat(self.timestamp_iso)
        )

    @classmethod
    def from_domain_event(cls, event: EventPriceUpdate) -> "PriceUpdateDTO_v1":
        """从领域事件创建DTO（ExecutionNode调用）"""
        return cls(
            code=event.code,
            price=event.price,
            volume=event.volume,
            timestamp_iso=event.timestamp.isoformat()
        )
```

**设计原因**:
- **职责分离**: Event（领域内部）、Message（控制命令）、DTO（业务数据传输）三者职责清晰
- **版本演进**: DTO带`_v`版本字段，支持向后兼容的API演进
- **性能优化**: DTO不包含Event的复杂属性（如context、mixin）
- **解耦**: 领域层不依赖Kafka，通过DTO实现端口适配
- **清晰表达**: 代码结构清晰表达用途（events/ vs messages/）

### 通信架构（Kafka消息总线）

所有组件间通信通过Kafka实现，Topic设计如下（统一命名规范：`ginkgo.live.*` 实盘专用，`ginkgo.*` 全局）：

#### 市场数据Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.live.market.data` | EventPriceUpdate | LiveCore.Data | ExecutionNode | 所有市场行情（A股、港股、美股、期货，通过EventPriceUpdate.market字段区分） |

**设计原因**:
- 避免为每只股票创建Topic（5000股票 vs 1个市场Topic）
- 通过EventPriceUpdate.market字段区分市场类型（CN/HK/US/FUTURES）
- 简化topic管理，提高Consumer Group的分区分配效率

#### 订单Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.live.orders.submission` | EventOrderSubmission | ExecutionNode | LiveEngine | 订单提交 |
| `ginkgo.live.orders.feedback` | EventOrderAck, EventOrderPartiallyFilled, EventOrderCancelAck | LiveEngine | ExecutionNode | 订单回报 |

**流向**: Portfolio生成订单 → ExecutionNode → Kafka(submission) → LiveEngine → TradeGateway → 真实交易所 → LiveEngine → Kafka(feedback) → ExecutionNode → Portfolio

#### 控制命令Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.live.control.commands` | 控制命令JSON | API Gateway, CLI, Data模块 | ExecutionNode, LiveEngine | 组件生命周期控制 |

**扩展性说明**:
- **当前发布者**: API Gateway (HTTP API)
- **未来发布者**: CLI命令行工具、Data模块（接收控制指令）
- **设计原则**: 新增发布者只需实现Kafka Producer发布到同一topic，订阅者无需修改代码，实现零改造成本接入

**支持的命令类型**:

| 命令类型 | 目标组件 | 说明 | 消息格式 |
|---------|---------|------|----------|
| `portfolio.create` | LiveEngine | 创建新Portfolio | 包含完整config |
| `portfolio.delete` | LiveEngine | 删除Portfolio | 仅portfolio_id |
| `portfolio.reload` | ExecutionNode | Portfolio配置更新（优雅重启） | 包含version |
| `portfolio.start` | ExecutionNode | 启动Portfolio | - |
| `portfolio.stop` | ExecutionNode | 停止Portfolio | - |
| `engine.start` | LiveEngine | 启动实盘引擎 | - |
| `engine.stop` | LiveEngine | 停止实盘引擎 | - |

**消息格式** (portfolio.create):
```json
{
  "command_type": "portfolio.create",
  "target_id": "portfolio_001",
  "config": {
    "name": "My Portfolio",
    "strategy": {...},
    "risk_managements": [...],
    "sizer": {...}
  },
  "timestamp": "2026-01-04T10:00:00Z"
}
```

**消息格式** (portfolio.delete):
```json
{
  "command_type": "portfolio.delete",
  "target_id": "portfolio_001",
  "timestamp": "2026-01-04T10:00:00Z"
}
```

**消息格式** (portfolio.reload):
```json
{
  "command_type": "portfolio.reload",
  "target_id": "portfolio_001",
  "version": "v2",
  "reason": "parameter_update",  // parameter_update/strategy_change/risk_change
  "timestamp": "2026-01-04T10:00:00Z"
}
```

**订阅者处理逻辑**:
- **LiveEngine**: 处理所有`portfolio.*`和`engine.*`命令
- **ExecutionNode**: 仅处理与自己相关的Portfolio命令（通过target_id判断），忽略其他命令

#### 调度控制Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.live.schedule.updates` | 调度计划JSON | Scheduler | ExecutionNode | 调度计划更新通知 |

**消息格式**:
```json
{
  "node_id": "execution_node_001",
  "portfolio_ids": ["portfolio_001", "portfolio_002"],
  "timestamp": "2026-01-04T10:00:00Z"
}
```

#### 系统事件Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.live.system.events` | 兴趣集/节点事件JSON | ExecutionNode, Data, Scheduler | ExecutionNode, Data | 系统事件（兴趣集同步、Node离线等） |

**消息类型**:
- `interest.update`: ExecutionNode上报兴趣集
- `interest.sync_request`: Data请求同步
- `node.offline`: Node离线通知

#### 全局通知Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.notifications` | 通知消息JSON | 所有模块 | Notification系统 | 系统通知（跨实盘/回测） |

**说明**: 复用现有的通知系统(006-notification-system)，用于系统通知、告警、日志等场景。不单独创建alerts模块。

---

### Portfolio配置更新流程（优雅重启）
```
1. 用户通过API更新Portfolio配置
   POST /api/portfolio/portfolio_001
   {"strategy_params": {...}, "risk_params": {...}}

2. API Gateway更新数据库
   UPDATE portfolios SET config = {...}, version = version + 1

3. API Gateway发送Kafka通知
   PRODUCE ginkgo.live.control.commands {
     "command_type": "portfolio.reload",
     "target_id": "portfolio_001",
     "version": "v2",
     "reason": "parameter_update"
   }

4. ExecutionNode收到通知
   CONSUME ginkgo.live.control.commands

5. ExecutionNode执行优雅重启流程
   ├─ 检查是否是自己管理的Portfolio
   ├─ 【状态转换1】设置Portfolio为STOPPING状态
   │  └─ Redis SET portfolio:portfolio_001:status {status: "stopping"}
   │
   ├─ 【停止消息推送+缓存】EventEngine检测到STOPPING状态
   │  ├─ 不再向Portfolio Queue发送新消息
   │  └─ 将消息缓存到ExecutionNode内存 buffer[portfolio_id]
   │
   ├─ 【等待消费完成】等待Portfolio Queue消费完所有消息
   │  ├─ 检查Queue.size() == 0
   │  └─ 超时30秒强制进入下一步
   │
   ├─ 【状态转换2】优雅关闭Portfolio实例
   │  ├─ portfolio.on_stop() 清理资源
   │  └─ Redis SET portfolio:portfolio_001:status {status: "stopped"}
   │
   ├─ 【加载新配置】从数据库加载新配置
   │  ├─ SELECT * FROM portfolios WHERE portfolio_id = "portfolio_001"
   │  └─ 验证 version = v2
   │
   ├─ 【状态转换3】重新初始化Portfolio实例
   │  ├─ 创建新Portfolio实例 (新配置)
   │  ├─ 初始化策略、风控、Sizer
   │  └─ Redis SET portfolio:portfolio_001:status {status: "reloading"}
   │
   ├─ 【恢复消息推送+重放缓存】
   │  ├─ EventEngine恢复向Portfolio Queue发送消息
   │  ├─ 将buffer[portfolio_id]中缓存的消息按顺序塞入Queue
   │  └─ 清空buffer[portfolio_id]
   │
   └─ 【状态转换4】标记为运行状态
      └─ Redis SET portfolio:portfolio_001:status {
           "status": "running",
           "version": "v2",
           "node": "node_001",
           "restarted_at": "2026-01-04T10:05:00Z"
         }
```

**Portfolio状态枚举**:
```python
class PORTFOLIO_RUNSTATE_TYPES(Enum):
    RUNNING = "RUNNING"       # 正常运行，接收事件
    STOPPING = "STOPPING"     # 停止中，不接收新事件，等待Queue清空
    STOPPED = "STOPPED"       # 已停止，不处理事件
    RELOADING = "RELOADING"   # 重载中，加载新配置
    MIGRATING = "MIGRATING"   # 迁移中，迁移到其他节点
```

**EventEngine停止推送+缓存逻辑**:
```python
# ExecutionNode内部的缓存buffer
event_buffer = {}  # {portfolio_id: [event1, event2, ...]}

# EventEngine发送事件前检查状态
def send_event_to_portfolio(portfolio_id, event):
    status_key = f"portfolio:{portfolio_id}:status"
    status = redis.hget(status_key, "status")

    # STOPPING状态：缓存消息，不发送到Queue
    if status == PORTFOLIO_RUNSTATE_TYPES.STOPPING:
        GLOG.INFO(f"Portfolio {portfolio_id} is STOPPING, buffering event")
        buffer[portfolio_id].append(event)
        return True

    # STOPPED/RELOADING状态：缓存消息，不发送到Queue
    if status in [PORTFOLIO_RUNSTATE_TYPES.STOPPED, PORTFOLIO_RUNSTATE_TYPES.RELOADING]:
        GLOG.WARN(f"Portfolio {portfolio_id} is {status}, buffering event")
        buffer[portfolio_id].append(event)
        return True

    # ERROR状态：缓存消息，不发送到Queue
    if status == PORTFOLIO_RUNSTATE_TYPES.MIGRATING:  # 迁移状态作为错误状态处理
        GLOG.ERROR(f"Portfolio {portfolio_id} is ERROR, buffering event")
        buffer[portfolio_id].append(event)
        return True

    # 正常RUNNING状态：发送到Queue
    queue = portfolio_queues[portfolio_id]
    queue.put(event)
    return True

# Portfolio重启后重放缓存消息
def replay_buffered_events(portfolio_id):
    if portfolio_id in event_buffer and event_buffer[portfolio_id]:
        GLOG.INFO(f"Replaying {len(event_buffer[portfolio_id])} buffered events for {portfolio_id}")
        queue = portfolio_queues[portfolio_id]

        # 按顺序重放所有缓存消息
        for event in event_buffer[portfolio_id]:
            queue.put(event)

        # 清空缓存
        del event_buffer[portfolio_id]
        GLOG.INFO(f"Buffer cleared for {portfolio_id}")
```

**缓存Buffer设计要点**:

1. **内存保护** - 防止buffer无限增长:
```python
MAX_BUFFER_SIZE = 1000  # 每个Portfolio最多缓存1000条消息

def send_event_to_portfolio(portfolio_id, event):
    # ... 状态检查 ...

    # 缓存消息时检查上限
    if status != PORTFOLIO_RUNSTATE_TYPES.RUNNING:
        buffer_size = len(event_buffer.get(portfolio_id, []))
        if buffer_size >= MAX_BUFFER_SIZE:
            GLOG.ERROR(f"Buffer full for {portfolio_id} ({buffer_size} events), dropping event")
            return False  # 丢弃消息，记录告警

        event_buffer[portfolio_id].append(event)
        return True
```

2. **缓存状态监控** - Redis记录缓存大小:
```python
# 更新Portfolio状态时同时记录buffer大小
redis.hset(f"portfolio:{portfolio_id}:status", {
    "status": "stopping",
    "buffer_size": len(event_buffer.get(portfolio_id, 0)),
    "buffer_timestamp": datetime.now().isoformat()
})
```

3. **告警机制** - 缓存积压告警:
```python
# 定时检查buffer大小，超过阈值告警
BUFFER_WARNING_THRESHOLD = 500  # 500条消息告警

def check_buffer_health():
    for portfolio_id, events in event_buffer.items():
        if len(events) > BUFFER_WARNING_THRESHOLD:
            GLOG.WARN(f"Portfolio {portfolio_id} buffer has {len(events)} events, may indicate issues")
            # 发送通知（使用现有notification系统）
            send_notification(f"Portfolio {portfolio_id} buffer accumulation")
```

4. **Node重启保护** - 防止缓存丢失:
```python
# Node重启时，如果有未处理的缓存消息需要处理
# 方案1: Node启动时检查Redis状态，发现STOPPING状态的Portfolio需要处理
# 方案2: 将buffer持久化到Redis（简单场景可用）
# 方案3: 接受小概率丢失（业务允许范围内）
```

**缓存生命周期**:
```
1. Portfolio RUNNING → buffer为空，正常接收
2. Portfolio STOPPING → 开始缓存，不推送到Queue
3. Portfolio STOPPED → 继续缓存
4. Portfolio RELOADING → 继续缓存
5. Portfolio RUNNING → 重放缓存消息到Queue，清空buffer
```

**状态上报（Redis直接写入，不通过Kafka）**:
- **心跳上报**: ExecutionNode每10秒写Redis `heartbeat:node:{node_id}` (EX 30)
- **可用节点**: Scheduler通过Redis SMEMBERS `nodes:active` 获取当前活跃节点列表
- **Portfolio状态**: ExecutionNode更新Redis `portfolio:{portfolio_id}:status`

#### 兴趣集Topics
| **Topic** | **消息类型** | **发布者** | **订阅者** | **说明** |
|-----------|------------|-----------|-----------|----------|
| `ginkgo.live.system.events` | 兴趣集变更事件 | ExecutionNode | LiveCore.Data | Portfolio订阅股票变更 |

**消息格式**:
```json
{
  "node_id": "node_001",
  "interest_set": ["000001.SZ", "000002.SZ", ...],
  "timestamp": "2026-01-04T10:00:00Z"
}
```

#### 模块订阅/发布关系汇总表

| **模块** | **订阅Topics** | **发布Topics** | **Redis读写** | **说明** |
|---------|---------------|---------------|--------------|----------|
| **API Gateway** | 无 | `ginkgo.live.control.commands` | 读: 查询状态 | 发布控制命令 |
| **LiveCore.Data** | `ginkgo.live.system.events` | `ginkgo.live.market.data*` | 无 | 获取行情，发布兴趣集事件 |
| **LiveCore.TradeGatewayAdapter** | `ginkgo.live.orders.submission`<br>`ginkgo.live.control.commands` | `ginkgo.live.orders.feedback` | 无 | 订阅订单提交，执行订单，发布订单回报 |
| **LiveCore.Scheduler** | 无（定时任务） | `ginkgo.live.schedule.updates` | 读: 获取节点心跳<br>写: 更新调度计划 | 定时调度，读取节点状态 |
| **ExecutionNode** | `ginkgo.live.market.data*`<br>`ginkgo.live.schedule.updates`<br>`ginkgo.live.control.commands`<br>`ginkgo.live.system.events`<br>`ginkgo.live.orders.feedback` | `ginkgo.live.orders.submission`<br>`ginkgo.live.system.events`<br>`ginkgo.notifications` | 写: 心跳上报<br>写: Portfolio状态 | 订阅行情、订单回报、配置更新，发布订单和兴趣集 |
| **Notification系统** | `ginkgo.notifications` | 无 | 无 | 接收通知并发送通知 |

**数据流向图**:
```
市场数据源 → LiveCore.Data → Kafka(ginkgo.live.market.data*) → ExecutionNode
    ↓
Portfolio策略 → ExecutionNode → Kafka(ginkgo.live.orders.submission) → TradeGatewayAdapter → TradeGateway → 真实交易所
    ↓
真实交易所 → TradeGatewayAdapter → Kafka(ginkgo.live.orders.feedback) → ExecutionNode → Portfolio
    ↓
ExecutionNode心跳 → Redis(heartbeat:node:{id}) → Scheduler读取
    ↓
ExecutionNode状态 → Redis(portfolio:{id}:status) → 查询API读取
    ↓
Portfolio配置更新 → API Gateway → Kafka(ginkgo.live.control.commands) + 数据库轮询 → ExecutionNode优雅重启
    ↓
兴趣集变更 → ExecutionNode → Kafka(ginkgo.live.system.events) → LiveCore.Data
    ↓
API控制 → API Gateway → Kafka(ginkgo.live.control.commands) → TradeGatewayAdapter/ExecutionNode
    ↓
Scheduler调度 → Redis读取节点状态 → 计算分配方案 → Redis写入调度计划 → Kafka(ginkgo.live.schedule.updates) → ExecutionNode
    ↓
系统通知 → 所有模块 → Kafka(ginkgo.notifications) → Notification系统
```

### API Gateway与LiveCore交互架构

#### 交互方式

**方式1: Kafka命令（异步控制）**
```
API Gateway → Kafka(ginkgo.live.control.commands) → TradeGatewayAdapter/ExecutionNode
适用场景: 启动/停止引擎、批量操作
```

**方式2: Redis同步（状态查询）**
```
API Gateway → Redis(读写) ← TradeGatewayAdapter/ExecutionNode
适用场景: 查询引擎状态、Node状态、调度方案
TradeGatewayAdapter/ExecutionNode定期更新Redis状态，API Gateway实时读取
```

**方式3: HTTP RPC（直接调用，可选）**
```
API Gateway → HTTP → LiveCore内部接口
适用场景: 需要同步返回结果的操作
```

#### API调用流程示例

**场景1: 启动实盘引擎**
```
1. 用户请求: POST /api/engine/start {"engine_id": "live_001"}
2. API Gateway发送命令到Kafka: ginkgo.live.control.commands
   {"type": "start", "engine_id": "live_001", "timestamp": "..."}
3. LiveEngine订阅并处理命令
4. LiveEngine更新Redis: engine:live_001:status = "running"
5. 用户查询: GET /api/engine/status
6. API Gateway从Redis读取并返回状态
```

**场景2: 手动触发负载均衡**
```
1. 用户请求: POST /api/schedule/rebalance
2. API Gateway发送Kafka命令或直接调用HTTP
3. Scheduler立即执行调度循环:
   - 从Redis读取活跃Node列表
   - 从数据库读取待分配Portfolio
   - 计算新的分配方案
   - 更新Redis (schedule:plan:{node_id})
   - 发送Kafka通知 (ginkgo.live.schedule.updates)
5. API Gateway返回新分配方案
```

### Node启动和恢复流程

1. **Node启动**:
   - 初始化Kafka Consumer订阅市场数据Topic
   - 订阅ginkgo.live.schedule.updates topic接收配置更新
   - 从Redis获取计划状态（SMEMBERS schedule:plan:node_id）

2. **启动心跳**:
   - 每10秒刷新Redis心跳（SET heartbeat:node:node_id "alive" EX 30）
   - 添加到活跃节点集合（SADD nodes:active node_id）

3. **从数据库加载Portfolio**:
   - 根据portfolio_id从数据库查询配置
   - 加载策略、风控、Sizer等组件
   - 创建Portfolio实例和PortfolioProcessor线程

4. **兴趣集上报**:
   - Node汇总所有Portfolio的兴趣集
   - 通过Kafka发送INTEREST_UPDATE消息到LiveEngine
   - DataFeeder更新订阅并推送相关行情数据

### Scheduler调度流程（Redis驱动）

**每30秒执行一次调度循环**:

```
1. Redis读取阶段
   ├─ SMEMBERS nodes:active → 获取当前活跃Node列表
   ├─ 检查心跳: heartbeat:node:{node_id} (TTL=30)
   └─ 过期Node从nodes:active移除

2. 发现需要迁移的Portfolio
   ├─ 所在Node心跳过期 → 标记需要迁移
   ├─ 负载不均衡 → 触发rebalance
   └─ 手动迁移请求 → API触发

3. 计算新的分配方案
   ├─ 读取所有待分配Portfolio (从数据库)
   ├─ 读取当前Node负载 (Portfolio数量/资源)
   └─ 执行调度算法 (负载均衡、故障恢复)

4. 更新Redis调度计划
   ├─ DEL schedule:plan:{node_id} (清空旧计划)
   └─ SADD schedule:plan:{node_id} portfolio_id1 portfolio_id2 ...

5. 发送Kafka通知
   └─ PRODUCE ginkgo.live.schedule.updates {"node_id": "...", "portfolio_ids": [...], "timestamp": "..."}

6. Node收到通知
   └─ 从Redis SMEMBERS schedule:plan:{node_id} 拉取最新配置
```

**Redis数据结构**:
```
# 心跳 (每10秒刷新，TTL=30)
heartbeat:node:node_001 → "alive" (EX 30)

# 活跃节点集合
nodes:active → SET{node_001, node_002, node_003}

# 调度计划
schedule:plan:node_001 → SET{portfolio_001, portfolio_002}
schedule:plan:node_002 → SET{portfolio_003, portfolio_004}

# Portfolio状态
portfolio:portfolio_001:status → HASH{status: "running", node: "node_001", ...}
```

### Redis状态管理

**计划状态存储**（使用Redis Set）:
```
# Key: schedule:plan:node_id
# Value: Set of portfolio_ids
SADD schedule:plan:node_001 "portfolio_001" "portfolio_002" "portfolio_003"
SADD schedule:plan:node_002 "portfolio_004" "portfolio_005"

# Node查询自己的Portfolio列表
SMEMBERS schedule:plan:node_001
→ {portfolio_001, portfolio_002, portfolio_003}

# Scheduler迁移Portfolio
SREM schedule:plan:node_001 "portfolio_003"
SADD schedule:plan:node_002 "portfolio_003"
```

**心跳机制**（使用Redis TTL）:
```
# Node心跳
SET heartbeat:node:node_001 "alive" EX 30
# 30秒无刷新则自动过期，Scheduler检测到超时
```

**实际状态存储**（可选，用于监控）:
```
# Set: Node实际运行的Processor列表
SADD node:node_001:processors "portfolio_001" "portfolio_002"

# Hash: Processor详细状态
HSET processor:portfolio_001 node_id node_001 status RUNNING queue_size 50
```

**状态同步机制**（Kafka通知 + 定期拉取）:
```
Node同步触发条件:
1. 收到Kafka消息（ginkgo.live.schedule.updates topic）→ 立即同步
2. 定期拉取（每30秒）→ 兜底机制

同步逻辑:
1. planned = SMEMBERS schedule:plan:node_001
2. actual = 获取实际运行的Processor列表
3. 对比差异:
   - planned - actual: 需要启动
   - actual - planned: 需要停止
4. 同步差异

优势: 无需version号，直接对比内容差异；推送+拉取混合模式兼顾实时性和可靠性
```

### 状态持久化策略

**数据库持久化**:
- Portfolio状态（资金、持仓、订单）立即写入MySQL
- 策略参数存储（Portfolio_id + Strategy_id == Mapping_id）
- ExecutionNode注册信息和状态
- Scheduler调度记录

**Redis缓存**:
- ExecutionNode实时状态（心跳时间、负载指标）
- Portfolio状态缓存（快速查询）
- 兴趣集缓存（快速路由决策）
- 热数据缓存（减少数据库查询）

**设计原则**:
- 所有组件无状态，状态存储在数据库/Redis
- 组件崩溃后可从数据库恢复状态
- 支持快速水平扩展

### Backpressure机制

**问题**: 当Portfolio处理速度 < Kafka消息到达速度时，消息会积压

**解决方案**:
1. **有界队列**: 每个Portfolio的message_queue设置maxsize=1000
2. **监控告警**: 监控队列大小，超过阈值（800）触发告警
3. **优雅降级**: 队列满时丢弃旧消息或暂停消费

**实现**:
```python
from queue import Queue

class PortfolioMessageQueue:
    def __init__(self, maxsize=1000):
        self.queue = Queue(maxsize=maxsize)
        self.alert_threshold = int(maxsize * 0.8)

    def put(self, message):
        if self.queue.qsize() >= self.alert_threshold:
            send_notification("Portfolio message queue nearly full")  # 使用现有notification系统
        self.queue.put(message, block=False)  # 满时抛出异常
```

### 动态调度流程

**正常流程**:
1. ExecutionNode定时发送心跳（每10秒）
2. Scheduler更新ExecutionNode最后活跃时间
3. 调度算法评估负载分布
4. 必要时发送迁移命令

**故障恢复**:
1. Scheduler检测到ExecutionNode心跳超时（>30秒）
2. 标记ExecutionNode为故障状态
3. 将故障ExecutionNode的Portfolio重新分配到健康ExecutionNode
4. 新ExecutionNode从数据库加载Portfolio状态并启动

**Portfolio迁移**:
1. 发送STOP命令到源ExecutionNode
2. 源ExecutionNode保存Portfolio状态到数据库
3. 发送START命令到目标ExecutionNode
4. 目标ExecutionNode从数据库加载状态并启动
5. 全流程应在30秒内完成

### 架构优势

1. **水平扩展**: LiveCore和ExecutionNode都可独立扩展
2. **故障隔离**: ExecutionNode故障不影响其他ExecutionNode
3. **资源优化**: 单ExecutionNode运行多Portfolio提高资源利用率
4. **灵活调度**: 支持动态迁移Portfolio实现负载均衡
5. **高可靠性**: 无状态设计 + 数据库持久化保证数据安全

### 关键设计决策记录

| 决策点 | 方案选择 | 原因 |
|--------|---------|------|
| 服务容器 | API Gateway (单实例) + LiveCore (单实例) | API Gateway统一入口，LiveCore业务逻辑层有状态单实例 |
| Portfolio部署 | ExecutionNode内多Portfolio（3-5个） | 减少网络开销，降低部署成本 |
| Kafka订阅 | ExecutionNode级别订阅，内部路由 | 避免网络流量随Portfolio数量线性增长 |
| Topic设计 | 市场级别Topic（ginkgo.live.market.data） | 避免创建5000个股票Topic |
| 控制通道 | Kafka命令Topic + Redis状态查询 | API Gateway通过Kafka控制LiveCore，通过Redis查询状态 |
| 状态管理 | 数据库持久化 + Redis缓存 | 支持快速恢复和水平扩展 |
| Backpressure | 有界Queue（maxsize=1000）+ 监控告警 | 防止内存溢出，保证系统稳定性 |
| 部署方式 | Docker Compose + Service名称 | Docker DNS自动解析IP变化，无需手动配置更新 |
| 容错机制 | Redis操作失败重试 + 连接池 | Redis重启后Node和Scheduler自动恢复，不中断服务 |

### Docker Compose部署架构

**服务发现设计**: 使用Docker Compose service名称和Docker内置DNS实现服务发现，无需额外的服务注册中心。

**docker-compose.yml配置**:
```yaml
version: '3.8'

services:
  # Redis服务
  redis:
    image: redis:7-alpine
    container_name: ginkgo-redis
    ports:
      - "6379:6379"
    networks:
      - ginkgo-network
    restart: unless-stopped

  # API Gateway服务（通用HTTP API控制层）
  api-gateway:
    build: ./src/ginkgo/api
    container_name: ginkgo-api-gateway
    ports:
      - "8000:8000"
    environment:
      - LIVECORE_URL=http://livecore:8080  # LiveCore内部接口
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - KAFKA_BROKERS=kafka1:9092
    networks:
      - ginkgo-network
    depends_on:
      - redis
      - livecore
      - kafka1
    restart: unless-stopped

  # LiveCore服务（包含Data、TradeGateway、LiveEngine、Scheduler）
  livecore:
    build: ./src/ginkgo/trading/livecore
    container_name: ginkgo-livecore
    environment:
      - REDIS_HOST=redis        # 使用service名称，Docker DNS解析
      - REDIS_PORT=6379
      - KAFKA_BROKERS=kafka1:9092
    networks:
      - ginkgo-network
    depends_on:
      - redis
      - kafka1
    restart: unless-stopped

  # ExecutionNode服务
  execution-node:
    build: ./src/ginkgo/trading/nodes
    environment:
      - REDIS_HOST=redis        # 使用service名称
      - REDIS_PORT=6379
    networks:
      - ginkgo-network
    depends_on:
      - redis
    deploy:
      replicas: 3               # 启动3个Node实例

networks:
  ginkgo-network:
    driver: bridge
```

**代码配置**:
```python
import os
import redis

# 从环境变量读取Redis配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

class ExecutionNode:
    def __init__(self):
        # 使用连接池，支持自动重连
        self.redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,      # 'redis' (service名称)
            port=REDIS_PORT,
            retry_on_timeout=True,
            socket_connect_timeout=5
        )
        self.redis_client = redis.Redis(connection_pool=self.redis_pool)
```

**Docker DNS工作机制**:
```
容器启动时:
1. Docker为每个service分配内部IP（动态）
2. Docker内置DNS自动创建记录: redis → 172.18.0.2

容器通信时:
1. ExecutionNode访问 "redis:6379"
2. Docker DNS解析 "redis" → 当前IP
3. 连接到Redis

Redis重启IP变化后:
1. Redis重新启动，获得新IP（如172.18.0.3）
2. Docker DNS自动更新记录: redis → 172.18.0.3
3. ExecutionNode下次连接时自动使用新IP
4. ✅ 无需修改任何配置，自动恢复
```

**优势**:
- ✅ **零配置**: 使用service名称，无需关心IP地址
- ✅ **自动更新**: Redis重启后IP变化，Docker DNS自动更新
- ✅ **简化运维**: 无需手动修改配置文件或重启容器
- ✅ **开发友好**: 本地开发和生产环境使用相同配置

### ExecutionNode内部并发处理模型

**核心设计**: ExecutionNode采用单Kafka消费线程 + 多PortfolioProcessor处理线程的并发模型，实现高性能消息路由和处理。

#### 线程架构

```
ExecutionNode进程内部结构:
┌────────────────────────────────────────────────────────────┐
│  Kafka消费线程（单线程）                                     │
│  - 订阅 ginkgo.live.market.data Topic                               │
│  - 快速消费消息（从Kafka拉取）                               │
│  - 根据interest_map路由消息到Processor Queue                │
│  - 非阻塞操作（只做Queue.put，不等待处理完成）              │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  interest_map查找（O(1)操作）                               │
│  interest_map["000001.SZ"] = [portfolio_a, portfolio_c]    │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  PortfolioProcessor线程池（每个Portfolio一个独立线程）     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Thread-A    │  │ Thread-B    │  │ Thread-C    │        │
│  │ Queue(1000) │  │ Queue(1000) │  │ Queue(1000) │        │
│  │ while:      │  │ while:      │  │ while:      │        │
│  │  q.get()    │  │  q.get()    │  │  q.get()    │        │
│  │  process()  │  │  process()  │  │  process()  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│     并行运行          并行运行          并行运行             │
└────────────────────────────────────────────────────────────┘
```

#### 并发处理的三个关键特性

**1. 快速分发（非阻塞）**
```python
def route_message(self, event: EventPriceUpdate):
    """Kafka消费线程调用此方法"""
    code = event.code

    # 查找订阅的Portfolio（O(1)）
    with self.interest_map_lock:
        portfolio_ids = self.interest_map.get(code, []).copy()

    # 快速分发到各Processor Queue（微秒级）
    for pid in portfolio_ids:
        processor = self.processors[pid]
        if not processor.queue.full():
            processor.queue.put(event, block=False)  # 非阻塞
```

**2. 并行处理（互不阻塞）**
```python
class PortfolioProcessor(threading.Thread):
    """每个Portfolio的独立处理线程"""
    def run(self):
        while True:
            # 每个线程独立从自己的Queue取消息
            event = self.queue.get(timeout=0.1)
            # 调用Portfolio实例处理（单线程访问，无需锁）
            self.portfolio.on_event(event)
```

**3. 实例一致性**
- **ExecutionNode持有唯一Portfolio实例**: `self.portfolios[portfolio_id] = Portfolio(...)`
- **PortfolioProcessor引用同一实例**: `self.portfolio = portfolio`（不是重新创建）
- **线程安全**: 每个Portfolio只被一个PortfolioProcessor线程访问，无需额外锁

#### 消息处理完整流程（5000条/秒场景）

```
T0: Data模块推送5000条消息到Kafka (ginkgo.live.market.data)
    ↓
T1: Kafka Consumer Group自动分配给10个ExecutionNode
    Node-1: ~500条
    Node-2: ~500条
    ...
    Node-10: ~500条
    ↓
T2: 每个ExecutionNode的Kafka消费线程快速路由（~10ms）
    查interest_map: 500次 × O(1)
    Queue.put: 500条 × 平均2.5个Portfolio = 1250次
    ↓
T3: PortfolioProcessor线程并行处理（每个Portfolio独立线程）
    Portfolio-A: 处理~300条，每条20ms = 6000ms
    Portfolio-B: 处理~250条，每条20ms = 5000ms
    Portfolio-C: 处理~200条，每条20ms = 4000ms
    （三个线程同时运行，总时间 = max(6000, 5000, 4000) = 6000ms）
    ↓
T4: 处理完成，生成订单提交到Kafka ginkgo.live.orders.submission

端到端延迟: T0 → T4 ≈ 100-200ms
```

### 动态调整Portfolio的线程生命周期管理

**问题**: 当需要动态添加/删除/迁移Portfolio时，如何管理PortfolioProcessor线程的生命周期？

**解决方案**: 带生命周期状态的PortfolioProcessor线程

#### 线程状态机

```python
class PortfolioState(Enum):
    STARTING = "starting"      # 启动中
    RUNNING = "running"        # 运行中
    STOPPING = "stopping"      # 停止中（等待队列清空）
    STOPPED = "stopped"        # 已停止
    MIGRATING = "migrating"    # 迁移中
```

#### 优雅停止流程

```python
class PortfolioProcessor(threading.Thread):
    def graceful_stop(self):
        """优雅停止：处理完队列中剩余消息"""
        self.state = PortfolioState.STOPPING
        self.stop_event.set()
        # 等待线程结束（最多30秒）
        self.join(timeout=30)
        # 最终状态持久化
        self.save_state()
```

#### Portfolio迁移流程（Scheduler协调）

```
时间线:
T1: Scheduler决定迁移Portfolio-A (Node-1 → Node-2)
T2: 发送MIGRATE_OUT命令到Node-1
T3: Node-1从interest_map移除Portfolio-A（停止接收新消息）
T4: Node-1优雅停止Portfolio-A线程（处理完Queue中消息）
T5: Node-1保存Portfolio-A状态到数据库
T6: Scheduler发送MIGRATE_IN命令到Node-2
T7: Node-2从数据库加载Portfolio-A状态
T8: Node-2创建Portfolio-A实例和线程
T9: Node-2更新interest_map（开始接收新消息）

总耗时: < 30秒
消息不丢失: T3-T9期间的消息暂存在Kafka，Node-2启动后消费
```

### Backpressure反压机制详解

**定义**: 当消费者处理速度 < 生产者生产速度时，告诉生产者"慢一点"或"停下来"的机制，防止系统崩溃。

#### 三种实现方式

**方式1: 丢弃消息（激进反压）**
- **触发**: Queue满（1000条）
- **行为**: 拒绝接收新消息，直接丢弃
- **优点**: ExecutionNode不会被阻塞，内存不会溢出
- **缺点**: 会丢失数据
- **适用**: 允许部分数据丢失的场景

**方式2: 阻塞等待（温和反压）**
- **触发**: Queue满
- **行为**: 阻塞等待Queue有空间（最长1秒）
- **优点**: 不丢失数据（短期）
- **缺点**: ExecutionNode会被阻塞，影响其他Portfolio
- **适用**: 数据完整性要求高的场景

**方式3: 监控告警 + 优雅降级（推荐）⭐**
- **触发**: Queue使用率超过70%
- **行为**:
  - 70-90%: 触发告警，记录慢日志
  - >90%: 丢弃消息，触发严重告警
- **优点**: 兼顾性能和可靠性
- **适用**: 生产环境推荐方案

#### 推荐方案实现

```python
class PortfolioProcessor(threading.Thread):
    def __init__(self, portfolio_id, portfolio, node):
        super().__init__(daemon=True)
        self.queue = queue.Queue(maxsize=1000)
        self.alert_threshold = int(1000 * 0.8)  # 80%触发告警
        self.critical_threshold = int(1000 * 0.9)  # 90%丢弃消息

def route_message(self, event):
    thread = self.portfolio_threads[portfolio_id]
    queue_size = thread.queue.qsize()
    queue_usage = queue_size / thread.queue.maxsize

    if queue_usage >= 0.9:
        # 严重：丢弃消息
        print(f"🔴 Portfolio {portfolio_id} critical (90% full), dropping {event.code}")
        return
    elif queue_usage >= 0.7:
        # 警告：记录日志
        print(f"🟡 Portfolio {portfolio_id} warning (70% full), {event.code} delayed")
        thread.queue.put(event, block=False)
    else:
        # 正常：直接放入
        thread.queue.put(event, block=False)
```

#### Backpressure效果对比

| 指标 | 无反压 | 有反压 |
|------|--------|--------|
| Queue大小 | 无限增长 | 有界（1000） |
| 内存使用 | 最终溢出 | 稳定 |
| ExecutionNode阻塞 | 可能阻塞 | 不阻塞 |
| 数据丢失 | 可能全部 | 可控丢弃 |
| 系统稳定性 | 崩溃 | 稳定运行 |

## Clarifications

### Session 2026-01-04

**Q11: 控制入口是否只限于HTTP API？未来Data模块等组件如何接入控制层？**
→ A: 控制入口设计必须支持扩展性，不仅限于HTTP API，还包括CLI和未来Data模块等多种入口。设计原则：
  1. **控制入口抽象**: 所有控制命令统一通过`ginkgo.live.control.commands` Kafka Topic发布
  2. **零改造成本**: 新增控制入口（如CLI、Data模块）时，只需实现Kafka Producer发布命令，订阅者（ExecutionNode、LiveEngine）无需修改代码
  3. **命令来源透明**: 订阅者无需关心命令来源（HTTP/CLI/Data），只需处理命令类型和目标ID
  4. **当前实现**: API Gateway (HTTP) 作为第一个发布者，未来CLI和Data模块可作为额外发布者接入

**Q12: CLI如何启动ExecutionNode？**
→ A: 复用现有的`ginkgo worker start`命令，通过参数指定worker类型为execution_node，**仅支持前台运行模式**。设计要求：
  1. **命令模式**: `ginkgo worker start --type execution_node --node-id execution_node_001` 在前台运行
  2. **运行行为**: 与Docker容器内的ExecutionNode运行行为完全一致（初始化、事件处理、生命周期管理）
  3. **日志输出**: 所有日志（启动过程、事件处理、错误）实时输出到stdout，便于开发调试
  4. **信号处理**: 支持SIGINT (Ctrl+C)优雅停止（等待Queue清空后退出）
  5. **使用场景**:
     - **开发调试**: 在本地环境测试策略逻辑、风控模块、订单提交流程
     - **问题排查**: 前台运行时实时观察日志，定位Kafka连接、数据库操作等问题
     - **高可用测试**: 模拟ExecutionNode上线/下线，验证Scheduler心跳检测和Portfolio自动迁移（< 60秒）
       - 启动Node：`ginkgo worker start --type execution_node --node-id test_node_001`
       - 观察Scheduler检测到新Node并分配Portfolio
       - 停止Node：Ctrl+C模拟故障，观察Portfolio自动迁移到其他Node
  6. **无需后台模式**: CLI命令不管理后台进程，后台运行通过Docker/Supervisor等进程管理工具实现

### Session 2026-01-03

本节记录架构讨论过程中明确的关键设计决策和澄清。

**Q1: ExecutionNode内部如何实现并发处理Portfolio？**
→ A: 采用单Kafka消费线程 + 多PortfolioProcessor处理线程模型。Kafka消费线程专注快速消费和路由消息，每个Portfolio有独立的处理线程和Queue，实现完全并行处理，互不阻塞。

**Q2: ExecutionNode和PortfolioProcessor持有的Portfolio实例是同一个吗？**
→ A: 是。ExecutionNode持有唯一的Portfolio实例（存储在`self.portfolios`字典中），PortfolioProcessor持有该实例的引用（不是重新创建）。每个Portfolio实例只被一个PortfolioProcessor线程访问，保证线程安全，无需额外锁。

**Q3: 如何根据interest_map分发消息到Portfolio？**
→ A: ExecutionNode收到Kafka消息后，根据股票代码查询interest_map获取订阅该股票的Portfolio ID列表，然后将消息放入每个PortfolioProcessor线程的Queue中（非阻塞操作）。Queue解耦了消息接收和处理。

**Q4: 如何动态调整Portfolio（添加/删除/迁移）？**
→ A: 通过线程生命周期管理。添加Portfolio时创建新线程并更新interest_map；删除时调用graceful_stop()等待队列清空后停止线程；迁移时源ExecutionNode优雅停止并保存状态，目标ExecutionNode从数据库加载状态并启动新线程。全流程<30秒，消息不丢失（暂存在Kafka）。

**Q5: 什么是Backpressure反压机制？**
→ A: 当消费者处理速度 < 生产者生产速度时的流量控制机制。通过有界队列（maxsize=1000）+ 监控告警实现：70-90%触发告警，>90%丢弃新消息。防止消息无限积压导致内存溢出，保证系统稳定运行。

**Q6: ExecutionNode与Scheduler之间的心跳机制参数如何配置？**
→ A: 心跳间隔10秒，超时阈值30秒（3倍心跳间隔）。ExecutionNode每10秒向Scheduler发送心跳，Scheduler若30秒内未收到心跳则判定ExecutionNode故障，触发重新分配Portfolio。快速检测机制，适合实盘交易的高可用性要求。

**Q7: 组件命名如何避免与现有DI Container和Worker冲突？**
→ A: 使用Node替代Worker，避免命名冲突。组件命名：ExecutionNode（执行节点）+ PortfolioProcessor（Portfolio处理器）。原因：现有代码已有Container（DI容器）和Worker（通知Worker），使用Node作为运行单元的命名更清晰，符合分布式系统的节点概念。

**Q8: Node与Processor的配置关系如何存储？**
→ A: 不使用配置文件，使用Redis Set存储。计划状态：`schedule:plan:node_id`为Set，存储分配给该Node的Processor ID列表。Processor配置从数据库加载（根据portfolio_id查找策略、风控、参数）。Node启动时从Redis获取应该运行的Processor列表，从数据库加载配置并启动。

**Q9: 计划状态同步机制如何设计？**
→ A: 使用Kafka通知 + 定期拉取的混合模式。Scheduler更新计划后发送Kafka消息到`ginkgo.live.schedule.updates` topic，所有Node订阅该Topic。收到消息后立即触发同步。同时Node每30秒定期拉取计划并对比，作为兜底机制防止消息丢失。不需要version号，直接对比内容差异。

**Q10: Redis数据结构如何使用Set存储Node-Processor关系？**
→ A: 使用Redis Set存储：`SADD schedule:plan:node_001 "portfolio_001" "portfolio_002"`。Node查询使用`SMEMBERS schedule:plan:node_001`获取所有Processor列表。使用Set而非List的原因：自动去重、O(1)查找和删除、支持集合运算检测异常配置。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 单Portfolio实盘运行 (Priority: P1)

作为交易者，我希望在实盘环境中运行单个投资组合，策略能够接收实时行情、生成信号并自动执行交易。

**Why this priority**: 这是实盘交易的最小可用产品(MVP)，验证整个实盘架构的基础功能。

**Independent Test**: 可以通过启动单个ExecutionNode，订阅实时行情数据，验证信号生成和订单提交流程。

**Acceptance Scenarios**:

1. **Given** 一个配置好的ExecutionNode，**When** 接收到EventPriceUpdate事件，**Then** 策略应该生成交易信号
2. **Given** 生成的交易信号，**When** 通过Sizer计算订单大小，**Then** 应该生成Order并提交到Kafka订单Topic
3. **Given** 提交的订单，**When** 接收到EventOrderPartiallyFilled事件，**Then** Portfolio应该更新持仓和资金状态
4. **Given** Portfolio状态变化，**When** 状态写入数据库，**Then** 数据库应该包含最新的持仓和资金信息

---

### User Story 2 - 多Portfolio并行运行 (Priority: P2)

作为基金经理，我希望在同一个ExecutionNode容器内运行多个独立的Portfolio，每个Portfolio使用不同的策略和参数。

**Why this priority**: 提高资源利用率，降低部署成本，同时支持多策略组合交易。

**Independent Test**: 可以在单个ExecutionNode内启动3-5个Portfolio，验证它们之间的独立性（状态隔离、消息路由正确）。

**Acceptance Scenarios**:

1. **Given** 一个ExecutionNode包含3个Portfolio，**When** Kafka接收到市场数据，**Then** 每个Portfolio应该只接收其订阅股票的消息
2. **Given** Portfolio A和B订阅相同股票，**When** 接收到该股票的EventPriceUpdate，**Then** 两个Portfolio都应该独立处理并可能生成不同信号
3. **Given** Portfolio A生成订单，**When** 订单写入数据库，**Then** Portfolio B的状态不应受到影响
4. **Given** ExecutionNode内多个Portfolio同时处理消息，**When** 处理时间超过阈值，**Then** 应该触发backpressure机制防止消息溢出

---

### User Story 3 - Portfolio动态调度 (Priority: P3)

作为系统管理员，我希望能够动态添加、删除、迁移Portfolio到不同的ExecutionNode，实现负载均衡和故障恢复。

**Why this priority**: 提高系统可用性和可扩展性，支持Portfolio的弹性伸缩。

**Independent Test**: 可以通过Scheduler发送控制命令，验证Portfolio的注册、更新、迁移流程。

**Acceptance Scenarios**:

1. **Given** 运行中的ExecutionNode，**When** 新Portfolio启动并发送注册消息，**Then** Scheduler应该记录ExecutionNode信息并在数据库中创建Portfolio记录
2. **Given** ExecutionNode内Portfolio更新兴趣集，**When** 发送INTEREST_UPDATE消息到LiveEngine，**Then** DataFeeder应该更新订阅并推送相关行情数据
3. **Given** ExecutionNode A负载过高，**When** Scheduler决定迁移Portfolio到ExecutionNode B，**Then** 应该发送停止命令到A，启动命令到B，Portfolio从B恢复运行
4. **Given** ExecutionNode故障，**When** Scheduler检测到心跳超时，**Then** 应将该ExecutionNode的Portfolio重新分配到健康ExecutionNode

---

### User Story 4 - 实时风控执行 (Priority: P2)

作为风控管理员，我希望实盘中能够实时监控Portfolio状态，在触发风控条件时自动拦截订单或生成平仓信号。

**Why this priority**: 风控是实盘交易的核心保障，必须与信号生成并行处理。

**Independent Test**: 可以配置LossLimitRisk和PositionRatioRisk，验证在触发条件时的订单拦截和平仓信号生成。

**Acceptance Scenarios**:

1. **Given** Portfolio配置止损风控，**When** 持仓亏损超过10%，**Then** 风控应该生成平仓信号而非策略信号
2. **Given** Portfolio配置仓位风控，**When** 订单会导致单股仓位超过20%，**Then** 风控应该调整订单量到允许范围
3. **Given** 多个风控模块，**When** 信号生成后，**Then** 应该依次通过所有风控模块处理，任何一个都可以拦截订单
4. **Given** 风控拦截订单，**When** 拦截发生，**Then** 应该记录日志并可选发送通知

---

### User Story 5 - 系统监控和告警 (Priority: P3)

作为运维人员，我希望能够监控所有ExecutionNode和Portfolio的运行状态，在异常时接收告警通知。

**Why this priority**: 确保系统稳定运行，及时发现和处理问题。

**Independent Test**: 可以通过查询数据库状态和Kafka消息积压情况，验证监控指标收集和告警触发。

**Acceptance Scenarios**:

1. **Given** ExecutionNode正常运行，**When** 定时报告心跳，**Then** Scheduler应该更新最后活跃时间
2. **Given** Portfolio消息队列积压，**When** 队列大小超过阈值，**Then** 应该触发告警并记录到日志
3. **Given** 数据库写入失败，**When** 异常发生，**Then** 应该记录错误日志并可选重试
4. **Given** 系统正常运行，**When** 查询监控接口，**Then** 应该返回ExecutionNode列表、Portfolio状态、性能指标等信息

---

### Edge Cases

- **网络分区**: 当Kafka集群网络分区时，Producer和Consumer如何处理？
- **消息顺序**: 同一股票的EventPriceUpdate消息如何保证顺序处理？
- **重复消费**: Kafka消息重复投递时，Portfolio如何幂等处理？
- **崩溃恢复**: ExecutionNode崩溃后，如何从数据库恢复Portfolio状态？
- **消息溢出**: 当Portfolio处理速度慢于消息到达速度，backpressure机制如何工作？
- **参数更新**: Portfolio运行时如何动态更新策略参数？
- **兴趣集冲突**: 多个ExecutionNode订阅相同股票，DataFeeder如何高效推送？
- **时钟同步**: 分布式环境下如何保证事件时间戳一致性？
- **数据库连接池**: 高并发写入时如何管理数据库连接？
- **内存管理**: 长时间运行如何避免内存泄漏？
- **Redis重启恢复**: Redis服务重启后，Node心跳上报和Scheduler状态获取如何自动恢复？

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- **FR-002**: System MUST 使用ServiceHub模式，通过`from ginkgo import service_hub`访问服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、分析层和服务层职责
- **FR-004**: System MUST 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器进行优化
- **FR-005**: System MUST 提供类型注解，支持静态类型检查

**实盘架构特有需求**:
- **FR-006**: System MUST 实现API Gateway容器（HTTP API入口 + 请求路由）
- **FR-007**: System MUST 实现LiveCore服务容器（Data + TradeGateway + LiveEngine + Scheduler）
- **FR-008**: System MUST 实现ExecutionNode执行节点，支持运行多个Portfolio实例
- **FR-009**: System MUST 使用Kafka作为所有组件间通信总线（市场数据、订单、控制命令）
- **FR-010**: System MUST 实现无状态架构，所有状态持久化到数据库（Redis缓存热数据）
- **FR-011**: System MUST 支持ExecutionNode级别的Kafka订阅，内部通过interest_map路由到Portfolio
- **FR-012**: System MUST 实现backpressure机制（有界Queue maxsize=1000 + 监控通知）
- **FR-013**: System MUST 支持Portfolio兴趣集动态注册和更新
- **FR-014**: System MUST 实现Scheduler的Portfolio-ExecutionNode调度算法
- **FR-015**: System MUST 支持ExecutionNode横向扩展（多实例部署）

**API Gateway需求**:
- **FR-016**: [FUTURE] API Gateway实现JWT认证或API Key验证（未来功能）
- **FR-017**: System MUST API Gateway通过Kafka异步控制LiveEngine（启动/停止/重启）
- **FR-018**: System MUST API Gateway通过Redis查询LiveEngine和Scheduler状态
- **FR-019**: [FUTURE] API Gateway实现Rate Limiting防止API滥用（未来功能）
- **FR-020**: System MUST API Gateway提供完整的RESTful API接口（引擎、调度、Portfolio、Node、监控）
- **FR-021**: System MUST API Gateway支持CORS配置，允许Web前端调用

**Kafka Topic设计**:
- **FR-022**: System MUST 使用市场级别Topic（如ginkgo.live.market.data）而非每股票一个Topic
- **FR-023**: System MUST 订单使用Topic（如ginkgo.live.orders.submission/feedback）发送到Broker执行
- **FR-024**: System MUST 控制命令使用Topic（如ginkgo.live.control.commands, ginkgo.live.schedule.updates）
- **FR-025**: System MUST API Gateway通过Kafka发送LiveEngine控制命令到ginkgo.live.control.commands topic
- **FR-026**: System MUST Portfolio兴趣集更新通过Kafka发送给LiveCore.Data (ginkgo.live.system.events)

**数据持久化**:
- **FR-027**: System MUST Portfolio状态（资金、持仓、订单）立即写入数据库
- **FR-028**: System MUST 策略参数存储在数据库（Portfolio_id + Strategy_id == Mapping_id）
- **FR-029**: System MUST Redis缓存热数据（ExecutionNode状态、Portfolio状态、兴趣集）
- **FR-030**: System MUST Kafka Producer配置幂等性（enable.idempotence=true）

**性能与可靠性**:
- **FR-031**: System MUST ExecutionNode内Portfolio处理时间 < 100ms per message（避免队列积压）
- **FR-032**: System MUST 数据库操作使用连接池和批处理
- **FR-033**: System MUST 关键操作使用`@retry`装饰器处理临时故障
- **FR-034**: System MUST 所有组件支持水平扩展（无状态设计）

**Redis容错与部署**:
- **FR-035**: System MUST Redis连接使用ConnectionPool配置自动重连（retry_on_timeout=True）
- **FR-036**: System MUST ExecutionNode心跳发送失败时捕获异常并重试，不退出进程
- **FR-037**: System MUST Scheduler Redis操作失败时捕获异常，返回空值继续运行
- **FR-038**: System MUST 使用Docker Compose service名称配置Redis地址（REDIS_HOST=redis），利用Docker DNS自动解析IP变化
- **FR-039**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-040**: File updates MUST synchronize header descriptions with actual code functionality
- **FR-041**: Header updates MUST be verified during code review process
- **FR-042**: CI/CD pipeline MUST include header accuracy verification

### Key Entities

- **API Gateway**: HTTP API入口，提供RESTful API接口，通过Kafka/Redis与LiveCore通信
- **LiveCore**: 业务逻辑层服务容器，包含Data（数据源管理）、TradeGateway（订单路由到交易所）、LiveEngine（实盘引擎驱动）、Scheduler（Portfolio调度）
- **ExecutionNode**: Portfolio执行节点，负责运行多个Portfolio实例，订阅Kafka市场数据，内部通过interest_map路由消息到PortfolioProcessor
- **PortfolioProcessor**: Portfolio处理器线程（每个Portfolio一个独立线程），持有Portfolio实例引用，从Queue取消息并调用Portfolio.on_event()处理
- **Portfolio**: 投资组合实例，包含策略、风控、Sizer、持仓、资金管理，响应事件驱动信号。ExecutionNode持有唯一实例，PortfolioProcessor引用该实例
- **InterestSet**: Portfolio订阅的股票代码集合，ExecutionNode汇总后上报给LiveEngine
- **InterestMap**: ExecutionNode内部的数据结构（字典），映射股票代码到订阅的Portfolio ID列表
- **Scheduler**: 调度器，负责Portfolio到ExecutionNode的分配、负载均衡、故障恢复
- **KafkaMessageBus**: 消息总线，承载市场数据（ginkgo.live.market.data*）、订单（ginkgo.live.orders.*）、控制通知（ginkgo.live.control.commands, ginkgo.live.schedule.updates）、系统事件（ginkgo.live.system.events）、系统通知（ginkgo.notifications）
- **BackpressureMonitor**: 反压监控器，监控ExecutionNode内Portfolio消息队列大小，触发通知
- **RedisStateStore**: Redis状态存储，维护计划状态（schedule:plan:node_id为Set）、Node注册信息（node:register:node_id）和心跳状态（heartbeat:node:node_id）。支持组件重启恢复，Redis重启后通过ConnectionPool自动重连，服务发现使用Docker Compose service名称（redis）由Docker DNS自动解析IP变化

## Success Criteria *(mandatory)*

### Measurable Outcomes

**实盘架构性能指标**:
- **SC-001**: 单ExecutionNode支持3-5个Portfolio并行运行
- **SC-002**: ExecutionNode消息处理延迟 < 100ms per message
- **SC-003**: Kafka消息吞吐量 > 50000 messages/sec（5000股票 × 10个Portfolio）
- **SC-004**: ExecutionNode注册响应时间 < 1秒
- **SC-005**: Portfolio状态写入延迟 < 50ms

**可扩展性指标**:
- **SC-006**: 支持横向扩展到10+个ExecutionNode实例
- **SC-007**: 支持运行50+个Portfolio实例
- **SC-008**: 支持动态添加/删除ExecutionNode而不影响运行中的Portfolio
- **SC-009**: 支持Portfolio在不同ExecutionNode间迁移（< 30秒切换时间）

**可靠性指标**:
- **SC-010**: ExecutionNode故障恢复时间 < 60秒（自动重新分配Portfolio）
- **SC-011**: 消息处理可靠性 99.9%（Kafka幂等性 + 数据库事务）
- **SC-012**: 系统连续运行时间 > 7天无重启
- **SC-013**: 内存使用稳定（长时间运行无内存泄漏）

**业务功能指标**:
- **SC-014**: 策略信号生成延迟 < 200ms（从接收PriceUpdate到生成Signal）
- **SC-015**: 风控响应时间 < 50ms（从Signal到Order/拦截）
- **SC-016**: 订单提交延迟 < 100ms（从Order到Kafka订单Topic）
- **SC-017**: 支持多策略组合（每个Portfolio独立策略参数）

**代码质量指标**:
- **SC-018**: 单元测试覆盖率 > 80%
- **SC-019**: 集成测试覆盖核心流程（注册、消息路由、状态持久化、故障恢复）
- **SC-020**: 代码文档完整性 > 90%（核心API文档覆盖率）
- **SC-021**: 所有文件包含准确的代码头注释

