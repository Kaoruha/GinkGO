# 时间窗口批处理系统

## 概述

Ginkgo时间窗口批处理系统是一个先进的信号处理框架，旨在解决传统逐个信号处理导致的资源竞争不真实问题。该系统能够将同一时间窗口内产生的信号进行批量处理，实现更公平、更真实的资源分配。

## 核心问题解决

### 传统方式的问题
- **不公平竞争**: 信号按到达顺序处理，先到先得
- **资源浪费**: 后续信号可能因资金不足被拒绝，即使调整分配可以容纳更多信号
- **时序不准确**: 同一时间点产生的信号应该同时竞争资源，而非按序处理
- **策略单一**: 只能使用简单的先到先得策略

### 批处理方式的优势
- **公平竞争**: 同时间窗口内的信号统一竞争资源
- **资源优化**: 全局优化资金分配，提高利用率
- **时序准确**: 模拟真实市场的时间窗口机制
- **策略多样**: 支持多种优化策略（等权重、优先级、凯利公式等）

## 系统架构

```
signal_processing/
├── __init__.py              # 模块导入
├── batch_processor.py       # 批处理器基类
├── window_processors.py     # 具体窗口处理器
├── resource_optimizer.py    # 资源优化算法
└── README.md               # 本文档
```

## 核心组件

### 1. TimeWindowBatchProcessor (批处理器基类)

负责信号收集、批次管理和处理触发。

```python
from ginkgo.trading.signal_processing import TimeWindowBatchProcessor, WindowType, ProcessingMode

processor = TimeWindowBatchProcessor(
    window_type=WindowType.DAILY,
    processing_mode=ProcessingMode.BACKTEST,
    resource_optimization=True,
    priority_weighting=True
)
```

**关键属性:**
- `window_type`: 时间窗口类型 (DAILY/HOURLY/MINUTELY/IMMEDIATE)
- `processing_mode`: 处理模式 (BACKTEST/LIVE/HYBRID)
- `max_batch_delay`: 最大批处理延迟
- `resource_optimization`: 是否启用资源优化
- `priority_weighting`: 是否考虑信号优先级

### 2. 具体窗口处理器

#### DailyWindowProcessor (日线处理器)
- 适用于基于日线数据的策略
- 兼容T+1交易机制
- 回测模式下严格按天分组

#### HourlyWindowProcessor (小时处理器)
- 适用于日内策略
- 提供相对较短的延迟
- 支持小时级别的批处理

#### MinuteWindowProcessor (分钟处理器)
- 适用于高频策略
- 提供很短的延迟以满足高频需求
- 支持分钟级别的批处理

#### ImmediateProcessor (立即处理器)
- 兼容现有的逐个处理模式
- 主要用于向后兼容

### 3. ResourceOptimizer (资源优化器)

提供多种资源分配策略:

#### 优化策略
- **EQUAL_WEIGHT**: 等权重分配
- **PRIORITY_WEIGHT**: 基于优先级和置信度加权
- **KELLY_CRITERION**: 凯利公式最优分配
- **RISK_PARITY**: 风险平价分配
- **MOMENTUM_WEIGHT**: 动量权重分配

#### 约束条件
```python
from ginkgo.trading.signal_processing import AllocationConstraints

constraints = AllocationConstraints(
    max_total_allocation=0.8,      # 最多使用80%资金
    max_single_position=0.15,      # 单股最多15%仓位
    min_order_value=1000.0,        # 最小订单1000元
    max_positions_count=15,        # 最多15只股票
)
```

## 使用方法

### 1. 启用日线批处理

```python
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest

portfolio = PortfolioT1Backtest()

# 启用日线批处理
portfolio.enable_daily_batch_processing(
    processing_mode="backtest",
    resource_optimization=True,
    priority_weighting=True
)
```

### 2. 启用分钟级批处理

```python
portfolio.enable_minute_batch_processing(
    processing_mode="live",
    max_delay_seconds=10,
    resource_optimization=True
)
```

### 3. 自定义批处理配置

```python
from ginkgo.trading.signal_processing import HourlyWindowProcessor, ProcessingMode

portfolio.configure_custom_batch_processing(
    HourlyWindowProcessor,
    processing_mode=ProcessingMode.HYBRID,
    max_batch_delay=timedelta(minutes=5),
    priority_weighting=True
)
```

### 4. 监控批处理状态

```python
# 获取统计信息
stats = portfolio.get_batch_processing_stats()
print(f"已处理批次: {stats['processed_batches']}")
print(f"待处理信号: {stats['pending_signals']}")

# 强制处理待处理批次（回测结束时）
orders = portfolio.force_process_pending_batches()
```

## 处理模式

### BACKTEST (回测模式)
- 严格按时间窗口进行批处理
- 模拟真实的时序关系
- 适合精确的回测分析

### LIVE (实盘模式)
- 兼顾批处理和即时响应
- 根据延迟阈值触发处理
- 适合实际交易环境

### HYBRID (混合模式)
- 可配置的延迟批处理
- 平衡处理效率和响应速度
- 适合各种特殊需求

## 时间窗口类型

### DAILY (日线窗口)
- 窗口: 每自然日 00:00:00
- 适用: 基于日线数据的策略
- 特点: 兼容T+1机制

### HOURLY (小时窗口)
- 窗口: 每小时整点
- 适用: 日内策略
- 特点: 中等延迟响应

### MINUTELY (分钟窗口)
- 窗口: 每分钟整点
- 适用: 高频策略
- 特点: 短延迟快速响应

### IMMEDIATE (立即处理)
- 窗口: 每个信号独立窗口
- 适用: 兼容现有逻辑
- 特点: 无批处理，立即执行

## 集成说明

### Portfolio集成
批处理系统已完全集成到Portfolio基类中:

```python
# BasePortfolio新增方法:
- enable_batch_processing()          # 启用批处理
- disable_batch_processing()         # 禁用批处理  
- enable_daily_batch_processing()    # 日线批处理快捷配置
- enable_minute_batch_processing()   # 分钟级批处理快捷配置
- enable_hourly_batch_processing()   # 小时级批处理快捷配置
- configure_custom_batch_processing() # 自定义配置
- force_process_pending_batches()    # 强制处理待处理批次
- get_batch_processing_stats()       # 获取统计信息
```

### T+1回测集成
PortfolioT1Backtest已更新以支持批处理:

- 在`on_signal()`中自动检测批处理模式
- 在`on_time_goes_by()`中处理待处理批次
- 完全向后兼容传统T+1逻辑

## 性能考虑

### 内存使用
- 批处理器会缓存待处理信号
- 通过时间窗口分组减少内存占用
- 处理完成后立即释放内存

### 处理效率
- 批量处理比逐个处理更高效
- 资源优化算法复杂度适中
- 支持并发处理多个时间窗口

### 延迟控制
- 可配置的延迟阈值
- 实盘模式优先考虑响应速度
- 回测模式优先考虑准确性

## 最佳实践

### 1. 选择合适的时间窗口
- 日线策略 → DailyWindowProcessor
- 日内策略 → HourlyWindowProcessor  
- 高频策略 → MinuteWindowProcessor
- 兼容模式 → ImmediateProcessor

### 2. 配置优化策略
- 简单策略 → EQUAL_WEIGHT
- 考虑优先级 → PRIORITY_WEIGHT
- 风险考量 → RISK_PARITY
- 统计优化 → KELLY_CRITERION

### 3. 设置约束条件
- 合理的仓位限制
- 适当的最小订单金额
- 符合风控要求的总资金使用比例

### 4. 监控和调试
- 定期检查批处理统计信息
- 在回测结束时强制处理剩余批次
- 记录和分析资源分配效果

## 故障排除

### 常见问题

1. **批处理不生效**
   - 检查是否正确启用批处理
   - 确认Portfolio配置正确
   - 查看错误日志

2. **信号处理延迟过高**
   - 调整max_batch_delay参数
   - 降低min_batch_size阈值
   - 考虑切换到实盘模式

3. **资源分配不合理**
   - 检查AllocationConstraints配置
   - 尝试不同的优化策略
   - 验证Portfolio信息获取函数

4. **内存使用过高**
   - 减少批处理延迟时间
   - 增加批次触发阈值
   - 定期调用force_process_pending_batches()

### 调试工具

```python
# 获取详细状态信息
stats = portfolio.get_batch_processing_stats()

# 检查待处理批次
if stats['pending_batches'] > 0:
    print(f"有 {stats['pending_signals']} 个信号待处理")
    
# 强制清理
portfolio.force_process_pending_batches()
```

## 扩展开发

### 自定义窗口处理器

```python
from ginkgo.trading.signal_processing import TimeWindowBatchProcessor

class CustomWindowProcessor(TimeWindowBatchProcessor):
    def get_window_start(self, timestamp):
        # 实现自定义窗口逻辑
        pass
    
    def should_process_batch(self, window_start, signals):
        # 实现自定义触发逻辑
        pass
```

### 自定义优化策略

```python
from ginkgo.trading.signal_processing import ResourceOptimizer

class CustomOptimizer(ResourceOptimizer):
    def _custom_allocation_strategy(self, signals, max_allocation, portfolio_info):
        # 实现自定义分配策略
        pass
```

## 版本历史

- **v1.0.0**: 初始版本，支持基本的时间窗口批处理
- **v1.1.0**: 添加资源优化算法和多种分配策略
- **v1.2.0**: 完成Portfolio集成和T+1兼容性
- **v1.3.0**: 添加自定义扩展支持和性能优化

## 贡献指南

欢迎贡献代码和反馈！请参考项目的贡献指南。

## 许可证

本模块遵循Ginkgo项目的许可证条款。