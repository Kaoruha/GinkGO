# Data Model: Trading Framework Enhancement

**Branch**: 001-trading-framework-enhancement | **Date**: 2025-01-18
**Purpose**: Define core entities and their relationships for the enhanced trading framework

## Executive Summary

基于Protocol + Mixin架构设计，定义了量化交易框架的核心数据模型。所有实体都采用现代Python设计模式，优先考虑业务可读性和架构最优性。

## Core Entities

### 1. Market Data Entities

#### MarketData
统一的市场数据结构，支持多种数据源和时间周期。

```python
@dataclass
class MarketData:
    """统一市场数据结构"""
    symbol: str                    # 标准化股票代码 (e.g., "000001.SZ")
    timestamp: datetime            # 数据时间戳
    price: float                   # 价格 (开盘/收盘/最新价)
    volume: float                  # 成交量
    high: Optional[float] = None   # 最高价 (K线数据)
    low: Optional[float] = None    # 最低价 (K线数据)
    open: Optional[float] = None   # 开盘价 (K线数据)
    close: Optional[float] = None  # 收盘价 (K线数据)
    data_type: DataType = DataType.TICK  # 数据类型 (TICK/BAR)
    period: Optional[Period] = None  # 时间周期 (仅Bar数据)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Validation Rules**:
- `symbol`: 必须符合标准化格式 (e.g., "000001.SZ", "600000.SH")
- `timestamp`: 不能为空，必须是有效的datetime对象
- `price`: 必须 > 0
- `volume`: 必须 >= 0
- `data_type`: 必须是有效的DataType枚举值

#### MarketAnalysis
市场分析结果，包含技术指标和趋势判断。

```python
@dataclass
class MarketAnalysis:
    """市场分析结果"""
    symbol: str                    # 分析标的
    timestamp: datetime            # 分析时间
    indicators: Dict[str, Any]     # 技术指标结果
    trend: TrendDirection          # 趋势方向 (UP/DOWN/SIDEWAYS)
    volatility: VolatilityLevel    # 波动性等级 (LOW/MEDIUM/HIGH)
    liquidity: LiquidityLevel      # 流动性等级 (LOW/MEDIUM/HIGH)
    confidence: float              # 分析置信度 (0-1)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2. Trading Signal Entities

#### TradingSignal
标准化的交易信号结构，支持多种策略和风控规则。

```python
@dataclass
class TradingSignal:
    """交易信号"""
    strategy_id: str               # 策略唯一标识
    symbol: str                    # 交易标的
    direction: SignalDirection     # 信号方向 (LONG/SHORT/CLOSE)
    strength: float                # 信号强度 (0-1)
    reason: str                    # 信号生成原因
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None  # 建议价格
    quantity: Optional[int] = None # 建议数量
    timeframe: Timeframe = Timeframe.DAY  # 时间框架
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Validation Rules**:
- `strategy_id`: 必须是有效的UUID或标识符
- `direction`: 必须是有效的SignalDirection枚举值
- `strength`: 必须在 [0, 1] 范围内
- `reason`: 不能为空字符串

#### SignalBatch
批量信号处理，支持多标的组合策略。

```python
@dataclass
class SignalBatch:
    """批量交易信号"""
    batch_id: str                 # 批次唯一标识
    signals: List[TradingSignal]  # 信号列表
    timestamp: datetime           # 批次生成时间
    strategy_id: str              # 生成策略
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3. Strategy Configuration Entities

#### StrategyConfig
策略配置参数，支持灵活的策略定制。

```python
@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str              # 策略唯一标识
    name: str                     # 策略名称
    version: str                  # 策略版本
    parameters: Dict[str, Any]    # 策略参数
    risk_limits: RiskLimits       # 风险限制
    data_requirements: DataRequirements  # 数据需求
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### RiskLimits
风险控制参数配置。

```python
@dataclass
class RiskLimits:
    """风险限制配置"""
    max_position_ratio: float = 0.2        # 单股最大仓位比例
    max_total_position_ratio: float = 0.8   # 总仓位最大比例
    max_drawdown_limit: float = 0.15       # 最大回撤限制
    max_daily_loss_limit: float = 0.05     # 单日最大亏损限制
    max_consecutive_losses: int = 5        # 最大连续亏损次数
    stop_loss_ratio: float = 0.05          # 止损比例
    take_profit_ratio: float = 0.1         # 止盈比例
```

### 4. Portfolio and Position Entities

#### PortfolioInfo
投资组合信息，用于策略计算。

```python
@dataclass
class PortfolioInfo:
    """投资组合信息"""
    portfolio_id: str             # 投资组合ID
    total_value: float            # 总资产价值
    available_cash: float         # 可用现金
    positions: Dict[str, Position]  # 持仓信息 {symbol: Position}
    total_pnl: float              # 总盈亏
    daily_pnl: float              # 日盈亏
    max_drawdown: float           # 最大回撤
    risk_metrics: RiskMetrics     # 风险指标
    timestamp: datetime           # 信息时间戳
```

#### Position
持仓信息结构。

```python
@dataclass
class Position:
    """持仓信息"""
    symbol: str                   # 标的代码
    quantity: int                 # 持仓数量
    avg_price: float              # 平均成本价
    current_price: float          # 当前价格
    market_value: float           # 市值
    unrealized_pnl: float         # 浮动盈亏
    realized_pnl: float           # 已实现盈亏
    position_type: PositionType   # 持仓类型 (LONG/SHORT)
    open_timestamp: datetime      # 开仓时间
    last_update: datetime         # 最后更新时间
```

### 5. Performance and Analytics Entities

#### StrategyPerformance
策略绩效指标。

```python
@dataclass
class StrategyPerformance:
    """策略绩效指标"""
    strategy_id: str              # 策略ID
    period: AnalysisPeriod        # 分析周期
    total_return: float           # 总收益率
    annualized_return: float      # 年化收益率
    sharpe_ratio: float           # 夏普比率
    max_drawdown: float           # 最大回撤
    win_rate: float               # 胜率
    profit_factor: float          # 盈利因子
    total_trades: int             # 总交易次数
    profitable_trades: int        # 盈利交易次数
    losing_trades: int            # 亏损交易次数
    avg_trade_return: float       # 平均交易收益
    volatility: float             # 波动率
    calculated_at: datetime       # 计算时间
```

## Enum Definitions

### Core Enums

```python
class SignalDirection(Enum):
    """信号方向"""
    LONG = "long"
    SHORT = "short"
    CLOSE = "close"
    HOLD = "hold"

class TrendDirection(Enum):
    """趋势方向"""
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"

class VolatilityLevel(Enum):
    """波动性等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LiquidityLevel(Enum):
    """流动性等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DataType(Enum):
    """数据类型"""
    TICK = "tick"
    BAR_1MIN = "bar_1min"
    BAR_5MIN = "bar_5min"
    BAR_15MIN = "bar_15min"
    BAR_30MIN = "bar_30min"
    BAR_1HOUR = "bar_1hour"
    BAR_1DAY = "bar_1day"
    BAR_1WEEK = "bar_1week"

class Timeframe(Enum):
    """时间框架"""
    INTRADAY = "intraday"
    DAY = "day"
    SWING = "swing"
    POSITION = "position"

class PositionType(Enum):
    """持仓类型"""
    LONG = "long"
    SHORT = "short"
```

## Entity Relationships

### Relationship Diagram

```
Strategy (1) -----> (N) TradingSignal
    |
    v
StrategyConfig (1) -----> (1) RiskLimits
    |
    v
DataRequirements

Portfolio (1) -----> (N) Position
    |
    v
PortfolioInfo -----> RiskMetrics

MarketData (N) -----> (1) MarketAnalysis
    |
    v
SignalGeneration -----> TradingSignal

TradingSignal (N) -----> (1) StrategyPerformance
```

### Key Relationships

1. **Strategy → TradingSignal**: 一对多关系
   - 一个策略可以生成多个信号
   - 每个信号必须关联到特定策略

2. **Portfolio → Position**: 一对多关系
   - 一个投资组合包含多个持仓
   - 每个持仓属于特定投资组合

3. **MarketData → MarketAnalysis**: 多对一关系
   - 多个市场数据点用于生成一个分析结果
   - 分析结果基于特定时间段的数据

4. **Strategy → StrategyPerformance**: 一对多关系
   - 一个策略可以有多个不同周期的绩效分析
   - 每个绩效分析对应特定时间段

## State Transitions

### Signal State Flow

```
Signal Generation → Signal Validation → Risk Check → Order Creation → Execution
```

### Position State Flow

```
Opening → Active → Partial Close → Full Close → Closed
```

### Strategy State Flow

```
Initialization → Configuration → Running → Paused → Stopped → Error
```

## Data Validation Rules

### Business Rule Validation

1. **Signal Strength Validation**: 信号强度必须在0-1范围内
2. **Position Size Validation**: 持仓数量必须是正整数
3. **Price Validation**: 价格必须大于0
4. **Ratio Validation**: 所有比例值必须在0-1范围内
5. **Timestamp Validation**: 时间戳不能为未来时间

### Consistency Validation

1. **Signal-Strategy Consistency**: 信号的strategy_id必须与策略匹配
2. **Position-Portfolio Consistency**: 持仓必须属于有效的投资组合
3. **MarketData Completeness**: 市场数据必须包含必需字段
4. **Configuration Validation**: 策略配置必须包含所有必需参数

## Integration with Existing Data Models

### Mapping to Current Models

| New Entity | Existing Model | Mapping Strategy |
|------------|----------------|------------------|
| MarketData | MBar | 扩展支持多种数据类型 |
| TradingSignal | MSignal | 增强字段和验证 |
| StrategyConfig | ModelParam | 统一配置管理 |
| Position | MPosition | 增加实时计算字段 |
| PortfolioInfo | MPortfolio | 扩展分析功能 |

### Database Integration

- **ClickHouse**: 市场数据、信号数据 (时序数据)
- **MySQL**: 策略配置、投资组合信息 (关系数据)
- **Redis**: 实时缓存、状态管理 (临时数据)

## Performance Considerations

### Data Access Patterns

1. **Batch Processing**: 批量读取市场数据进行分析
2. **Streaming Updates**: 实时更新持仓和绩效信息
3. **Caching Strategy**: 缓存频繁访问的配置和分析结果
4. **Lazy Loading**: 按需加载详细的历史数据

### Scalability Design

1. **Horizontal Scaling**: 支持多策略并行运行
2. **Data Partitioning**: 按时间和标的分区存储
3. **Async Processing**: 异步处理信号生成和执行
4. **Memory Management**: 大数据集的流式处理

## Security and Compliance

### Data Security

1. **Encryption**: 敏感配置数据加密存储
2. **Access Control**: 基于角色的数据访问控制
3. **Audit Trail**: 完整的操作日志记录
4. **Data Privacy**: 个人和敏感信息保护

### Compliance Requirements

1. **Trade Recording**: 完整的交易记录保存
2. **Risk Reporting**: 定期风险报告生成
3. **Performance Attribution**: 详细的绩效归因分析
4. **Regulatory Reporting**: 监管要求的报表生成

## Future Extensibility

### Extension Points

1. **Custom Signal Types**: 支持自定义信号类型
2. **Alternative Data**: 支持另类数据源
3. **Multi-Asset Support**: 扩展到多资产类别
4. **Advanced Analytics**: 机器学习和AI分析功能

### Plugin Architecture

1. **Strategy Plugins**: 可插拔的策略组件
2. **Data Source Plugins**: 可扩展的数据源
3. **Risk Management Plugins**: 自定义风控模块
4. **Reporting Plugins**: 定制化报表功能

## Conclusion

本数据模型设计基于现代Python最佳实践，以架构最优和功能优先为原则。通过清晰的实体定义、完整的验证规则和灵活的扩展机制，为量化交易框架提供了坚实的数据基础。

**Next Steps**: 基于这些数据模型，继续生成API合约和快速开始指南。