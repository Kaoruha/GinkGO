# Ginkgo 开发参考文档

> 从 CLAUDE.md 迁出的详细参考材料。按需查阅，不每轮加载。

## 常用开发模式

### 服务访问
```python
from ginkgo import services
bar_crud = services.data.cruds.bar()
stockinfo_service = services.data.services.stockinfo_service()
engine = services.trading.engines.time_controlled()
portfolio = services.trading.portfolios.t1()
```

### 策略开发
```python
class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        bars = self.data_feeder.get_bars(code, start, end)
        if self.should_buy(bars):
            return [Signal(code=code, direction=DIRECTION_TYPES.LONG)]
        return []
```

### CRUD 扩展
```python
class MyDataCRUD(BaseCRUD):
    @time_logger
    @retry(max_try=3)
    def get_my_data_filtered(self, **filters) -> List:
        pass
```

### 风控开发
```python
class MyRiskManager(BaseRiskManagement):
    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        if self.exceeds_position_limit(portfolio_info, order):
            order.volume = self.adjust_volume(order)
        return order

    def generate_signals(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        if self.should_stop_loss(portfolio_info, event):
            return [Signal(direction=DIRECTION_TYPES.SHORT, reason="Stop Loss")]
        return []
```

## 关键 API 速查

### 数据操作
```python
# BarCRUD 真实方法
bars = bar_crud.find_by_code_and_date_range(code="000001.SZ", start_date="20230101", end_date="20231231")
latest_bars = bar_crud.get_latest_bars(code="000001.SZ", limit=10)
all_codes = bar_crud.get_all_codes(limit=1000)

# TickCRUD 真实方法（需要 code 过滤）
ticks = tick_crud.find({"code": "000001.SZ", "timestamp__gte": "2023-01-01"}, page_size=1000)
tick_crud.add(tick_obj)  # 单个
tick_crud.add_batch([tick1, tick2])  # 批量
count = tick_crud.count({"code": "000001.SZ"})
tick_crud.modify({"code": "000001.SZ", "timestamp": "..."}, {"volume": 1000})
tick_crud.remove({"code": "000001.SZ", "timestamp__lt": "2023-01-01"})

stocks = stockinfo_service.get_stockinfos()
```

### 回测操作
```python
# 通过 services.trading 访问引擎装配服务
engine_service = services.trading.services.engine_assembly_service()
# 或通过 container
from ginkgo.trading.core.containers import container
engine_service = container.services.engine_assembly_service()

portfolio.add_strategy(strategy)
portfolio.add_risk_manager(PositionRatioRisk(max_position_ratio=0.2))
```

### 配置和日志
```python
GCONF.get("database.host")
GCONF.set_debug(True)
GCONF.DEBUGMODE
GLOG.info("Processing data...")
GLOG.ERROR("Database connection failed")
```

## 风控体系

### 数据来源（SOURCE_TYPES）
- `BACKTEST=15` — 回测引擎产出
- `PAPER_REPLAY=18` — 历史数据模拟
- `PAPER_LIVE=19` — 实盘模拟

```python
from ginkgo.enums import SOURCE_TYPES
analyzer_crud.find(filters={"source": SOURCE_TYPES.PAPER_REPLAY.value})
```

### 时间体系
- `LogicalTimeProvider` — 回测用，可控逻辑时间
- `SystemTimeProvider` — 实盘用，系统实时时间
- `clock.now()` — 全局时钟入口 (`from ginkgo.trading.time.clock import now as clock_now`)
- `TimeProvider` — 时间提供者接口（支持注入）
- `EngineContext` — 引擎级上下文（engine_id/run_id/source_type）

### 偏差检测
链路：`BacktestEvaluator → baseline → LiveDeviationDetector → DeviationChecker`
Redis keys：`deviation:source/baseline/config:{portfolio_id}`

### 风控类型
- `PositionRatioRisk` — 持仓比例控制
- `LossLimitRisk` — 止损
- `ProfitTargetRisk` — 止盈
- `NoRiskManagement` — 无风控（测试用）

双重机制：被动订单拦截(`cal`) + 主动信号生成(`generate_signals`)

## 分布式日志系统

### 架构
GLOG (structlog) → 文件 → Vector → ClickHouse（三表：backtest/component/performance）

### 服务访问
```python
log_service = services.logging.log_service()
logs = log_service.query_backtest_logs(portfolio_id="xxx", level="ERROR", limit=50)
trace_logs = log_service.query_by_trace_id("trace-123")
```

### CLI 管理
```bash
ginkgo logging whitelist
ginkgo logging set-level backtest DEBUG
ginkgo logging get-level
ginkgo logging reset-level
```

### 追踪上下文
```python
# set_trace_id 返回 Token，用于恢复上下文
token = GLOG.set_trace_id("trace-123")
GLOG.bind_context(engine_context=engine.ctx)  # 绑定 EngineContext/PortfolioContext
GLOG.INFO("回测任务启动")
with GLOG.with_span_id("span-456"):  # 临时 span（context manager）
    GLOG.DEBUG("计算信号中...")
GLOG.clear_trace_id(token)  # 恢复 trace_id
GLOG.clear_context()  # 清除业务上下文
```

## 数据库约定

### 模型命名
- `MBar` (ClickHouse) | `MTick` (ClickHouse) | `MStockInfo` (MySQL) | `MAdjustFactor`
- ClickHouse 继承 `MClickBase`，MySQL 继承 `MMysqlBase`

### CRUD 命名
- `add` — 添加单个（继承自 BaseCRUD）
- `add_batch` — 批量添加
- `find` — 查询（支持 filters/page/page_size/order_by/distinct_field）
- `remove` — 删除
- `count` — 统计
- `exists` — 存在性检查

### 数据库选择
- ClickHouse: 时序数据 | MySQL: 关系数据 | Redis: 缓存/状态 | MongoDB: 文档数据

## 实盘交易架构

### 组件
- `LiveEngine` — 生命周期管理
- `OKXBroker` — OKX 适配器
- `BrokerManager` — 实例管理
- `HeartbeatMonitor` — 心跳监控
- `DataSyncService` — 数据同步

### Broker 状态机
```
uninitialized → initializing → running → paused → stopped
                     ↓             ↓
                   error      recovering
```

### 账号管理
```python
from ginkgo.data.containers import container
service = container.live_account_service()
result = service.create_account(user_id="user123", exchange="okx", ...)
result = service.validate_account(account_uuid)
result = service.get_account_balance(account_uuid)
```

### Broker 控制
```python
from ginkgo.trading.brokers.broker_manager import get_broker_manager
manager = get_broker_manager()
manager.start_broker(portfolio_id)
manager.pause_broker(portfolio_id)
manager.emergency_stop_all()
```

## TDD 测试框架设计流程

### 标准化方法

1. **源码分析** — 识别核心属性、方法、继承关系
2. **架构分析** — 明确组件边界，避免跨职责设计
3. **测试边界** — 与用户确认每个类别
4. **测试设计** — 7 类标准测试 + 扩展功能测试
5. **质量控制** — Red 阶段验证 + 一致性检查

### 7 类标准测试
1. Construction — 构造和初始化
2. Properties — 属性访问
3. DataSetting — 数据设置（singledispatchmethod）
4. Validation — 参数/业务规则验证
5. StateManagement — 状态管理
6. BusinessLogic — 核心业务逻辑
7. Constraints — 约束检查

### 命名规范
- 类：`TestEntityFunctionality`
- 方法：`test_specific_scenario()`
- 标记：`@pytest.mark.tdd` / `@pytest.mark.financial`
