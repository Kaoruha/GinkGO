# CLAUDE.md
输出内容控制在一屏内,不要滚动。

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Chat in madarin.

## Project Overview

Ginkgo is a Python quantitative trading library featuring:
- **Event-driven backtesting engine** with multi-database support (ClickHouse, MySQL, MongoDB, Redis)
- **Multiple data sources** (Tushare, Yahoo, AKShare, BaoStock, TDX)
- **Complete risk control system** with position management and stop-loss/profit mechanisms
- **CLI interface** using Typer with rich formatting
- **Unified services architecture** with dependency injection containers

## 核心设计理念

### 架构原则
- **事件驱动**: 回测引擎采用 `PriceUpdate → Strategy → Signal → Portfolio → Order → Fill` 事件链路
- **依赖注入**: 通过 `from ginkgo import services` 统一访问所有服务
- **装饰器优化**: 使用 `@time_logger`、`@retry`、`@cache_with_expiration` 进行性能优化
- **多数据库支持**: 统一接口访问 ClickHouse、MySQL、MongoDB、Redis

### 全局实例
- **`GLOG`**: 日志记录，支持Rich格式化
- **`GCONF`**: 配置管理，分层配置系统 (环境变量 → 配置文件 → 默认值)
- **`GTM`**: 线程管理，Kafka驱动的分布式worker系统

## 常用开发模式

### 服务访问模式
```python
from ginkgo import services

# 数据服务
bar_crud = services.data.cruds.bar()
stockinfo_service = services.data.services.stockinfo_service()

# 回测服务
engine = services.trading.engines.historic()
portfolio = services.trading.portfolios.base()
```

### 策略开发模式
```python
class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        # 获取当前价格数据
        bars = self.data_feeder.get_bars(code, start, end)
        
        # 策略逻辑实现
        if self.should_buy(bars):
            return [Signal(code=code, direction=DIRECTION_TYPES.LONG)]
        
        return []
```

### CRUD扩展模式  
```python
class MyDataCRUD(BaseCRUD):
    """继承BaseCRUD，自动获得装饰器和标准方法"""
    
    @time_logger  # 自动性能监控
    @retry(max_try=3)  # 自动重试
    def get_my_data_filtered(self, **filters) -> List:
        # 实现数据查询逻辑
        pass
    
    # 自动服务注册，通过 services.data.cruds.mydata() 访问
```

### 风控开发模式
```python
class MyRiskManager(BaseRiskManagement):
    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """订单风控检查 - 被动拦截"""
        if self.exceeds_position_limit(portfolio_info, order):
            order.volume = self.adjust_volume(order)
        return order
        
    def generate_signals(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """主动风控信号生成"""
        if self.should_stop_loss(portfolio_info, event):
            return [Signal(direction=DIRECTION_TYPES.SHORT, reason="Stop Loss")]
        return []
```

## 关键API速查

### 数据操作
```python
# K线数据
bars = bar_crud.get_bars_page_filtered(code="000001.SZ", start="20230101", end="20231231")
bar_crud.add_bars([bar1, bar2])  # 批量添加

# 股票信息  
stocks = stockinfo_service.get_stockinfos()
stockinfo_service.sync_all()  # 同步所有股票信息

# Tick数据
ticks = tick_crud.get_ticks_page_filtered(code="000001.SZ", limit=1000)
```

### 回测操作
```python
# 创建回测引擎
engine = EngineAssemblerFactory().create_engine(engine_type="historic")

# 组件装配
portfolio.add_strategy(strategy)
portfolio.add_risk_manager(PositionRatioRisk(max_position_ratio=0.2))
portfolio.add_risk_manager(LossLimitRisk(loss_limit=10.0))

# 运行回测
result = engine.run()
```

### 配置和日志操作
```python
# 配置管理
GCONF.get("database.host")  # 获取配置
GCONF.set_debug(True)  # 设置调试模式
GCONF.DEBUGMODE  # 检查调试状态

# 日志记录
GLOG.info("Processing data...")  # 信息日志
GLOG.ERROR("Database connection failed")  # 错误日志
```

### Worker管理操作  
```python
# Worker管理
GTM.start_multi_worker(count=4)  # 启动4个worker
worker_status = GTM.get_workers_status()  # 获取worker状态
GTM.reset_all_workers()  # 停止所有worker
```

## 风控体系

### 风控类型
- **`PositionRatioRisk`**: 持仓比例控制，支持单股和总持仓限制，智能调整订单量
- **`LossLimitRisk`**: 止损控制，监控持仓亏损自动生成平仓信号  
- **`ProfitLimitRisk`**: 止盈控制，监控持仓盈利自动生成平仓信号
- **`NoRiskManagement`**: 无风控实现，用于测试对比

### 风控机制
- **双重机制**: 被动订单拦截(`cal`) + 主动风控信号生成(`generate_signals`)
- **事件驱动**: 响应`EventPriceUpdate`事件进行实时风控监控
- **智能调整**: 调整订单量而非简单拒绝，最大化交易执行

### 风控集成示例
```python
# 在Portfolio中集成多个风控管理器
portfolio.add_risk_manager(PositionRatioRisk(
    max_position_ratio=0.2,  # 单股最大20%仓位
    max_total_position_ratio=0.8  # 总仓位最大80%
))
portfolio.add_risk_manager(LossLimitRisk(loss_limit=10.0))  # 10%止损
portfolio.add_risk_manager(ProfitLimitRisk(profit_limit=20.0))  # 20%止盈
```

## 数据库设计约定

### 模型命名约定
- **`MBar`** - K线数据模型 (ClickHouse存储)
- **`MTick`** - Tick数据模型 (ClickHouse存储)  
- **`MStockInfo`** - 股票信息模型 (MySQL存储)
- **`MAdjustFactor`** - 复权因子模型
- 所有ClickHouse模型继承 `MClickBase`，MySQL模型继承 `MMysqlBase`

### CRUD操作命名约定
```python
# 创建操作
add_bar(data)           # 单条添加
add_bars([data1, data2]) # 批量添加

# 查询操作  
get_bars_page_filtered(code="000001.SZ", start="20230101", limit=1000)
get_bar_by_uuid(uuid)   # 按UUID查询

# 更新操作
update_bar(uuid, new_data)

# 删除操作  
delete_bars_filtered(code="000001.SZ", start="20230101", end="20231231")
```

### 数据库选择原则
- **ClickHouse**: 时序数据存储 (K线、Tick、因子数据)，支持高效的分析查询
- **MySQL**: 关系数据存储 (股票信息、系统配置、用户数据)，支持事务
- **Redis**: 缓存和任务状态 (Worker状态、临时数据、分布式锁)
- **MongoDB**: 文档数据存储 (策略配置、复杂结果数据)

## Key Commands

### Environment Setup
```bash
# Create virtual environment and install
python3 -m virtualenv venv && source venv/bin/activate
python ./install.py

# Or with conda
conda create -n ginkgo python=3.12.8
conda activate ginkgo
python ./install.py
```

### Core CLI Commands
```bash
# System management
ginkgo version
ginkgo status                              # Quick system status
ginkgo system config set --debug on       # Enable debug mode (REQUIRED for database operations)

# Data management  
ginkgo data init                           # Initialize database tables
ginkgo data update --stockinfo             # Update stock information
ginkgo data update day --code 000001.SZ    # Update daily bar data
ginkgo data list stockinfo --page 50       # List stock info

# Backtesting
ginkgo backtest run {engine_id}            # Run specific backtest
ginkgo backtest component list strategy    # List strategies

# Worker management
ginkgo worker status                       # Show worker processes (detailed table)
ginkgo worker start --count 4              # Start 4 workers
ginkgo worker run --debug                  # Run single worker in foreground
```

### Testing Requirements
**CRITICAL**: Always enable debug mode before database operations:
```bash
ginkgo system config set --debug on    # Required for database operations
# Perform database operations or tests...
ginkgo system config set --debug off   # Disable after operations
```

## 开发最佳实践

### 性能优化
- 使用 **`@time_logger`** 监控方法执行时间，识别性能瓶颈
- 使用 **`@cache_with_expiration(60)`** 缓存频繁访问的数据  
- 使用 **`@retry(max_try=3)`** 处理网络不稳定和临时故障
- 使用 **`@skip_if_ran`** Redis去重机制避免重复执行

### 数据库操作准则
- **必须先开启调试模式**: `ginkgo system config set --debug on`
- **批处理优先**: 使用 `add_bars([])` 而非逐条插入，提高性能
- **合理分页**: 使用 `limit=1000` 参数避免大结果集内存问题
- **事务管理**: 重要操作在事务中执行，确保数据一致性

### 错误处理模式
- 使用 **`ServiceResult`** 标准化返回结果，统一错误处理
- 重要操作记录日志: `GLOG.info()` (信息) 或 `GLOG.ERROR()` (错误)
- 数据库异常自动重试，网络异常需要手动处理
- 使用 `try-except` 捕获特定异常，避免程序崩溃

### 模块扩展指南
- **策略扩展**: 继承 `BaseStrategy` 实现 `cal(portfolio_info, event)` 方法
- **数据源扩展**: 实现 `GinkgoSourceBase` 接口，支持新的数据提供商
- **风控扩展**: 继承 `BaseRiskManagement` 实现双重风控机制
- **分析器扩展**: 继承 `BaseAnalyzer` 实现 `_do_activate()` 和 `_do_record()` 模板方法
- **CRUD扩展**: 继承 `BaseCRUD` 自动获得装饰器支持和服务容器注册

## Configuration

**Key Config Files:**
- `~/.ginkgo/config.yaml` - Main configuration  
- `~/.ginkgo/secure.yml` - Sensitive credentials
- Environment variables override config files

**Global Access:**
```python
from ginkgo.libs import GLOG, GCONF, GTM
```

## TDD测试框架设计流程

### 标准化TDD测试设计方法

#### 第一阶段：实体分析和架构理解

**步骤1：源码分析**
- 使用`Read`工具分析现有实体实现
- 识别核心属性、方法和业务逻辑
- 理解继承关系和依赖模式

**步骤2：架构组件分析**
- 分析项目整体架构职责分离
- 明确各组件边界（Strategy/Sizer/RiskManagement等）
- 避免跨职责的功能设计

#### 第二阶段：测试边界确定

**边界原则：**
- **保留**：实体自身的核心功能和属性管理
- **删除**：属于其他专门组件的功能
- **扩展**：基于量化交易需求的合理增强

**确认流程：**
- 逐一与用户确认每个测试类别
- 说明作用、业务价值和具体测试场景
- 根据用户反馈调整或删除不合适的类别

#### 第三阶段：测试用例设计模式

**基础功能测试模式（7个标准类别）：**
1. **Construction** - 构造和初始化测试
2. **Properties** - 属性访问测试
3. **DataSetting** - 数据设置测试（singledispatchmethod）
4. **Validation** - 参数/业务规则验证测试
5. **StateManagement** - 状态管理测试
6. **BusinessLogic** - 核心业务逻辑测试
7. **Constraints** - 约束检查测试（如枚举类型）

**扩展功能测试模式：**
- 基于量化交易特有需求设计
- 每个扩展模块包含5-8个测试方法
- 使用`@pytest.mark.financial`标记

#### 第四阶段：测试文件生成规范

**文件结构标准：**
```python
# 1. 文档字符串 - 说明测试目的和覆盖范围
# 2. 导入声明 - 路径设置和依赖导入（TODO标记）
# 3. 测试类 - 按功能模块分组，使用@pytest.mark.tdd标记
# 4. 测试方法 - 详细TODO注释 + assert False占位
```

**命名规范：**
- 测试类：`TestEntityFunctionality`
- 测试方法：`test_specific_scenario()`
- 文件：`test_entity.py`

**标记策略：**
- `@pytest.mark.tdd` - 所有TDD测试
- `@pytest.mark.financial` - 量化交易特有功能

#### 第五阶段：质量控制

**Red阶段验证：**
- 运行单个测试确认失败
- 统计测试用例总数
- 验证pytest配置正确

**一致性检查：**
- TODO注释格式统一
- 错误消息格式："TDD Red阶段：测试用例尚未实现"
- 测试方法命名符合规范

### 成功案例

**已完成的实体测试框架：**
- **Position** - 11个测试类，70个测试方法
- **Signal** - 9个测试类，62个测试方法
- **Order** - 10个测试类，70个测试方法

**方法优势：**
- **系统性**：完整的分析到实现流程
- **可重复**：标准化模式适用于任何实体
- **用户驱动**：每个决策都经过用户确认
- **边界清晰**：职责分离原则确保设计合理

## Important Notes

- Python 3.12.8 required
- **Debug mode required** for all database operations and testing
- Event-driven architecture for backtesting with complete risk control
- Rich library integration for beautiful CLI output
- Lazy-loading and caching for performance optimization

## Active Technologies
- Python 3.12.8 + ast (标准库), pathlib, re, typing (003-code-context-headers)
- 无需数据库操作（仅文件系统） (003-code-context-headers)

## Recent Changes
- 003-code-context-headers: Added Python 3.12.8 + ast (标准库), pathlib, re, typing
