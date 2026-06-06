# Ginkgo 开发参考文档

> 从 CLAUDE.md 迁出的详细参考材料。按需查阅，不每轮加载。

## 常用开发模式

### 服务访问
```python
from ginkgo import services
bar_crud = services.data.cruds.bar()
stockinfo_service = services.data.services.stockinfo_service()
engine = services.trading.engines.historic()
portfolio = services.trading.portfolios.base()
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
bars = bar_crud.get_bars_page_filtered(code="000001.SZ", start="20230101", end="20231231")
bar_crud.add_bars([bar1, bar2])
stocks = stockinfo_service.get_stockinfos()
ticks = tick_crud.get_ticks_page_filtered(code="000001.SZ", limit=1000)
```

### 回测操作
```python
engine = EngineAssemblerFactory().create_engine(engine_type="historic")
portfolio.add_strategy(strategy)
portfolio.add_risk_manager(PositionRatioRisk(max_position_ratio=0.2))
result = engine.run()
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

### 运行模式（SOURCE_TYPES）
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
- `clock_now()` — 全局时间入口
- `EngineContext` — 引擎级上下文（engine_id/run_id/source_type）

### 偏差检测
链路：`BacktestEvaluator → baseline → LiveDeviationDetector → DeviationChecker`
Redis keys：`deviation:source/baseline/config:{portfolio_id}`

### 风控类型
- `PositionRatioRisk` — 持仓比例控制
- `LossLimitRisk` — 止损
- `ProfitLimitRisk` — 止盈
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
GLOG.set_trace_id("trace-123")
GLOG.bind_context(portfolio_id=portfolio.uuid)
GLOG.INFO("回测任务启动")
with GLOG.with_span_id("span-456"):
    GLOG.DEBUG("计算信号中...")
GLOG.clear_context()
```

## 数据库约定

### 模型命名
- `MBar` (ClickHouse) | `MTick` (ClickHouse) | `MStockInfo` (MySQL) | `MAdjustFactor`
- ClickHouse 继承 `MClickBase`，MySQL 继承 `MMysqlBase`

### CRUD 命名
- `add_bar` / `add_bars` — 添加
- `get_bars_page_filtered` — 分页查询
- `get_bar_by_uuid` — UUID 查询
- `delete_bars_filtered` — 删除

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
