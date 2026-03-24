# Ginkgo 回测到实盘自动运行 - 差距分析

**分析日期**: 2026-03-23
**项目**: Ginkgo 量化交易库
**目标**: 实现从回测策略到实盘自动运行的完整流程

## 目录

- [当前架构现状](#当前架构现状)
- [缺失的关键环节](#缺失的关键环节)
- [实施路线图](#实施路线图)
- [立即可以开始的工作](#立即可以开始的工作)

---

## 当前架构现状

### 已实现的核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                      Ginkgo 架构                             │
├─────────────────────────────────────────────────────────────┤
│ 回测层:  EngineHistoric + BacktestConfig                    │
│ 策略层:  BaseStrategy + 15种内置策略                         │
│ 风控层:  PositionRatioRisk, LossLimitRisk...                │
│ 实盘层:  LiveEngine + BrokerManager + OKXBroker             │
│ 数据层:  DataManager + ClickHouse/MySQL/Redis               │
│ API层:   FastAPI + 实盘账号CRUD                              │
└─────────────────────────────────────────────────────────────┘
```

### 架构设计原则

根据 `T5_UNIFIED_ARCHITECTURE.md`，项目遵循以下设计：

- **单一时间权威**: 统一时间语义，支持逻辑时间(回测)和系统时间(实盘)
- **事件驱动**: 完整的 `PriceUpdate → Strategy → Signal → Portfolio → Order → Fill` 事件链路
- **接口抽象**: Broker接口抽象支持模拟、纸质交易和实盘交易
- **智能路由**: 企业级事件路由系统，支持负载均衡和容错机制

### 核心设计模式

```python
# 时间控制
from ginkgo.trading.time import SystemTimeProvider, LogicalTimeProvider

# 回测使用逻辑时间
logical_provider = LogicalTimeProvider(datetime(2023, 1, 1, 9, 30, 0))

# 实盘使用系统时间
system_provider = SystemTimeProvider()

# Broker接口统一
from ginkgo.trading.brokers.interfaces import IBroker
# 支持: BaseBroker (模拟) / OKXBroker (实盘) / PaperBroker (模拟盘)
```

---

## 缺失的关键环节

### 1. 策略配置序列化 ⚠️ 高优先级

**问题描述：**
当前策略对象无法直接保存到数据库，策略配置与代码耦合。

**现状：**
```python
# 策略参数硬编码在代码中
class MovingAverageCrossover(BaseStrategy):
    def __init__(self, short_window=5, long_window=20, **kwargs):
        self.short_window = short_window
        self.long_window = long_window
        # 参数无法序列化到数据库
```

**需要实现：**
```python
# 策略配置数据模型
class StrategyConfig(MysqlBase):
    __tablename__ = "strategy_config"

    uuid: str
    name: str
    strategy_type: str  # "MovingAverageCrossover"
    parameters: JSON  # {"short_window": 5, "long_window": 20}
    version: int
    created_at: datetime
    is_active: bool

# 策略工厂
class StrategyFactory:
    @staticmethod
    def create_from_config(config: StrategyConfig) -> BaseStrategy:
        strategy_class = STRATEGY_REGISTRY[config.strategy_type]
        return strategy_class(**config.parameters)
```

**实施要点：**
- 策略参数的序列化方案
- 策略配置的版本管理
- 策略模板系统
- 策略注册表（`STRATEGY_REGISTRY`）

---

### 2. 回测到实盘的配置转换 ⚠️ 高优先级

**问题描述：**
回测配置和实盘配置使用不同的数据结构，无法直接转换。

**现状：**
```python
# 回测配置
@dataclass
class BacktestConfig:
    name: str
    start_date: date
    end_date: date
    initial_capital: float
    data_frequency: DataFrequency
    # ... 更多回测特定参数

# 实盘配置（缺失统一模型）
# 目前实盘配置散落在多个表中
```

**需要实现：**
```python
class LiveConfig:
    """实盘配置模型"""
    strategy_config_id: str  # 关联策略配置
    live_account_id: str     # 关联实盘账号
    capital: Decimal
    risk_config: RiskConfig
    schedule: ScheduleConfig  # 交易时段
    notification_config: NotificationConfig

def backtest_to_live_config(
    backtest_result: BacktestResult,
    live_account_id: str,
    capital: Decimal
) -> LiveConfig:
    """将回测结果转换为实盘配置"""
    # 1. 提取策略配置
    strategy_config = extract_strategy_config(backtest_result)

    # 2. 验证资金要求
    if capital < backtest_result.min_required_capital:
        raise ValueError("Insufficient capital")

    # 3. 生成实盘配置
    return LiveConfig(
        strategy_config_id=strategy_config.uuid,
        live_account_id=live_account_id,
        capital=capital,
        risk_config=backtest_result.risk_config,
        schedule=ScheduleConfig(
            timezone="Asia/Shanghai",
            trading_sessions=["09:30-11:30", "13:00-15:00"]
        )
    )
```

---

### 3. 策略验证和沙盒测试 ⚠️ 中优先级

**问题描述：**
缺少实盘前的策略验证环节，风险高。

**需要实现：**

#### 模拟盘测试阶段
```python
class PaperTradingPhase:
    """模拟盘测试阶段"""

    async def run_paper_test(
        self,
        live_config: LiveConfig,
        duration: timedelta = timedelta(days=7)
    ) -> PaperTestResult:
        """
        运行模拟盘测试

        验证点：
        - 策略是否正常生成信号
        - 订单是否正确执行
        - 风控是否正常工作
        - 性能指标是否达标
        """
        # 使用 PaperBroker 而非真实 Broker
        # 返回测试报告和通过/失败判定
```

#### 策略参数敏感性分析
```python
class ParameterSensitivityAnalyzer:
    """参数敏感性分析"""

    def analyze(
        self,
        strategy_config: StrategyConfig,
        param_ranges: Dict[str, Tuple[float, float]]
    ) -> SensitivityReport:
        """
        分析策略参数敏感性

        检测：
        - 参数微小变化是否导致策略表现剧烈波动
        - 参数是否存在过拟合风险
        """
```

#### 极端场景压力测试
```python
class StressTestRunner:
    """压力测试运行器"""

    scenarios = [
        "闪崩场景",  # 单日大跌 > 7%
        "暴涨场景",  # 单日大涨 > 7%
        "低流动性",  # 成交量 < 正常20%
        "连续跌停",  # 3日连续跌停
    ]
```

---

### 4. 自动化部署流程 ⚠️ 高优先级

**问题描述：**
当前需要手动配置实盘，缺少一键部署功能。

**目标流程：**
```
回测完成 → 验证通过 → 模拟盘测试 → 通过审核 → 一键部署实盘
```

**需要实现的API：**
```python
# API Router
@router.post("/portfolio/{backtest_id}/deploy")
async def deploy_to_live(
    backtest_id: str,
    deployment_request: DeploymentRequest,
    current_user: User = Depends(get_current_user)
) -> DeploymentResponse:
    """
    一键部署到实盘

    流程：
    1. 验证回测结果存在
    2. 提取策略配置
    3. 创建实盘配置
    4. 运行预部署检查
    5. 创建 Portfolio 实例
    6. 启动 Broker
    7. 开始接收实时数据
    """
    result = await deployment_service.deploy(
        backtest_id=backtest_id,
        live_account_id=deployment_request.live_account_id,
        capital=deployment_request.capital,
        user_id=current_user.id
    )
    return result

class DeploymentService:
    """部署服务"""

    async def deploy(
        self,
        backtest_id: str,
        live_account_id: str,
        capital: Decimal,
        user_id: str
    ) -> DeploymentResult:
        """执行部署流程"""

        # 1. 获取回测结果
        backtest_result = await self.get_backtest_result(backtest_id)

        # 2. 策略配置序列化
        strategy_config = await self.serialize_strategy(
            backtest_result.strategy
        )

        # 3. 创建实盘配置
        live_config = backtest_to_live_config(
            backtest_result,
            live_account_id,
            capital
        )

        # 4. 预部署检查
        check_result = await self.pre_deployment_check(live_config)
        if not check_result.passed:
            raise DeploymentFailedError(check_result.errors)

        # 5. 创建 Portfolio
        portfolio = await self.create_portfolio(live_config, user_id)

        # 6. 启动交易
        await self.start_trading(portfolio.uuid)

        return DeploymentResult(
            portfolio_id=portfolio.uuid,
            status="deployed",
            deployed_at=datetime.now()
        )
```

---

### 5. 策略监控和调整 ⚠️ 中优先级

**问题描述：**
策略上线后缺少实时监控和自动调整机制。

**需要实现：**

#### 实时策略性能追踪
```python
class StrategyPerformanceTracker:
    """策略性能追踪器"""

    metrics = [
        "实时PnL",
        "当日收益率",
        "最大回撤",
        "胜率",
        "夏普比率",
        "交易次数",
        "平均持仓时间"
    ]

    async def track(self, portfolio_id: str):
        """追踪策略性能"""
        while True:
            # 从数据库/Redis获取最新数据
            # 计算性能指标
            # 发送到监控系统
            # 检查是否触发告警
            await asyncio.sleep(10)
```

#### 策略漂移检测
```python
class StrategyDriftDetector:
    """策略漂移检测"""

    async def detect_drift(
        self,
        portfolio_id: str,
        baseline: BacktestResult
    ) -> DriftReport:
        """
        检测策略是否发生漂移

        比较维度：
        - 收益率分布变化
        - 最大回撤是否超出预期
        - 交易频率变化
        - 胜率下降
        """
```

#### 自动止损/暂停机制
```python
class AutoStopManager:
    """自动停止管理器"""

    conditions = {
        "max_daily_loss": -0.05,      # 单日亏损 > 5%
        "max_drawdown": -0.15,         # 最大回撤 > 15%
        "consecutive_losses": 5,       # 连续亏损 > 5次
        "system_error_count": 10,      # 系统错误 > 10次
    }

    async def check_and_stop(self, portfolio_id: str):
        """检查并触发停止"""
        if any(condition_met for condition in self.conditions.values()):
            await self.emergency_stop(portfolio_id)
```

---

## 实施路线图

### Phase 1: 策略配置系统 (2-3周)

**目标**: 建立策略配置的数据模型和序列化机制

**任务清单**:
- [ ] 创建 `strategy_config` 数据表
- [ ] 实现策略参数序列化/反序列化
- [ ] 建立策略注册表（`STRATEGY_REGISTRY`）
- [ ] 实现策略工厂（`StrategyFactory`）
- [ ] 创建策略模板管理界面
- [ ] 编写单元测试

**验收标准**:
- 策略配置可以保存到数据库
- 可以从数据库恢复策略对象
- 支持策略配置的版本管理

---

### Phase 2: 配置转换机制 (1-2周)

**目标**: 实现回测配置到实盘配置的自动转换

**任务清单**:
- [ ] 设计 `LiveConfig` 数据模型
- [ ] 实现 `backtest_to_live_config()` 转换函数
- [ ] 实现配置验证和校验
- [ ] 开发配置差异对比工具
- [ ] 添加配置转换API
- [ ] 集成测试

**验收标准**:
- 回测结果可以转换为实盘配置
- 配置验证能发现潜在问题
- 配置差异可视化

---

### Phase 3: 模拟盘阶段 (2-3周)

**目标**: 建立模拟盘测试环境

**任务清单**:
- [ ] 完善 `PaperBroker` 实现
- [ ] 实现模拟盘测试流程
- [ ] 开发参数敏感性分析工具
- [ ] 实现极端场景压力测试
- [ ] 创建模拟盘测试报告
- [ ] 集成到 Web UI

**验收标准**:
- 模拟盘可以稳定运行7天以上
- 参数敏感性分析有效
- 压力测试能发现问题

---

### Phase 4: 一键部署 (1-2周)

**目标**: 实现从回测到实盘的一键部署

**任务清单**:
- [ ] 开发部署服务（`DeploymentService`）
- [ ] 实现部署API端点
- [ ] 开发预部署检查流程
- [ ] 实现部署状态监控
- [ ] 创建部署日志和审计
- [ ] Web UI 部署界面

**验收标准**:
- 可以通过 API 一键部署
- 部署流程有完整日志
- 部署失败能回滚

---

### Phase 5: 监控和运维 (持续)

**目标**: 建立完整的监控和运维体系

**任务清单**:
- [ ] 实现实时性能追踪
- [ ] 开发策略漂移检测
- [ ] 实现自动止损/暂停机制
- [ ] 创建监控 Dashboard
- [ ] 配置告警通知
- [ ] 建立运维手册

**验收标准**:
- 监控指标实时更新
- 告警及时准确
- 自动止损可靠

---

## 立即可以开始的工作

如果现在就要实现这个目标，建议按以下顺序开始：

### 第一步：策略配置数据模型

```python
# 文件: src/ginkgo/data/models/model_strategy_config.py

class MStrategyConfig(MMysqlBase):
    """策略配置模型"""
    __tablename__ = "strategy_config"

    uuid: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    strategy_type: Mapped[str] = mapped_column(String(64))  # 策略类型
    parameters: Mapped[JSON] = mapped_column(JSON)  # 策略参数
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(32))  # user_id
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
```

### 第二步：策略注册表

```python
# 文件: src/ginkgo/trading/strategies/registry.py

from typing import Dict, Type
from ginkgo.trading.strategies.base_strategy import BaseStrategy

# 策略注册表
STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {}

def register_strategy(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    """策略注册装饰器"""
    STRATEGY_REGISTRY[cls.__name__] = cls
    return cls

# 使用示例
@register_strategy
class MovingAverageCrossover(BaseStrategy):
    pass
```

### 第三步：配置转换函数

```python
# 文件: src/ginkgo/services/config_conversion.py

from ginkgo.trading.engines.config.backtest_config import BacktestConfig
from ginkgo.data.models.model_strategy_config import MStrategyConfig

def backtest_to_strategy_config(
    backtest_config: BacktestConfig,
    strategy_instance: BaseStrategy
) -> MStrategyConfig:
    """从回测配置生成策略配置"""

    # 提取策略参数
    parameters = {
        k: v for k, v in strategy_instance.__dict__.items()
        if not k.startswith('_') and not callable(v)
    }

    return MStrategyConfig(
        name=f"{backtest_config.name}_strategy",
        strategy_type=strategy_instance.__class__.__name__,
        parameters=parameters,
        created_by=backtest_config.user_id,
    )
```

### 第四步：部署API

```python
# 文件: api/routers/deployment.py

@router.post("/deploy/{backtest_id}")
async def deploy_to_live(
    backtest_id: str,
    request: DeploymentRequest,
    current_user = Depends(get_current_user)
):
    """部署回测到实盘"""

    # 1. 获取回测结果
    backtest_result = await backtest_service.get_result(backtest_id)

    # 2. 创建策略配置
    strategy_config = await create_strategy_config(backtest_result)

    # 3. 创建实盘 Portfolio
    portfolio = await portfolio_service.create_live_portfolio(
        strategy_config_id=strategy_config.uuid,
        live_account_id=request.live_account_id,
        capital=request.capital,
        user_id=current_user.id
    )

    # 4. 启动实盘交易
    await live_engine.start_portfolio(portfolio.uuid)

    return {"portfolio_id": portfolio.uuid, "status": "deployed"}
```

---

## 总结

Ginkgo 项目已经具备了完整的架构基础，但距离"回测→实盘自动运行"还需要实现：

1. **策略配置序列化** - 建立策略与数据库的桥梁
2. **配置转换机制** - 连接回测和实盘配置
3. **模拟盘测试** - 降低实盘风险
4. **一键部署功能** - 提升用户体验
5. **监控运维体系** - 保障稳定运行

预计总开发时间：**8-12周**

关键成功因素：
- 严格的测试覆盖
- 渐进式部署流程
- 完善的监控告警
- 详细的文档和手册
