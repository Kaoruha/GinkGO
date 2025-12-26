# Ginkgo 量化交易库开发指南

Auto-generated from all feature plans. Last updated: 2025-11-28

## Active Technologies

**核心技术栈**:
- Python 3.12.8 (主要开发语言)
- ClickHouse (时序数据存储 - K线、Tick、因子数据)
- MySQL (关系数据存储 - 股票信息、系统配置、用户数据)
- Redis (缓存和任务状态 - Worker状态、临时数据、分布式锁)
- MongoDB (文档数据存储 - 策略配置、复杂结果数据)
- Kafka (分布式worker消息队列)

**主要框架和库**:
- Typer (CLI框架)
- Rich (终端美化)
- Pydantic (数据验证)
- pytest (测试框架)
- SQLAlchemy (ORM)

## Project Structure

```text
src/
├── ginkgo/                          # 主要库代码
│   ├── core/                        # 核心组件
│   │   ├── engines/                 # 回测引擎 (EngineHistoric, EngineTimeControlled)
│   │   ├── events/                  # 事件系统 (EventPriceUpdate, EventSignal等)
│   │   ├── portfolios/              # 投资组合管理
│   │   ├── risk/                    # 风险管理 (PositionRatioRisk, LossLimitRisk等)
│   │   └── strategies/              # 策略基类 (BaseStrategy)
│   ├── data/                        # 数据层
│   │   ├── models/                  # 数据模型 (MBar, MTick, MStockInfo, MAdjustFactor)
│   │   ├── sources/                 # 数据源适配器 (Tushare, Yahoo, AKShare等)
│   │   ├── services/                # 数据服务 (BarService, StockInfoService等)
│   │   └── cruds/                   # CRUD操作 (继承BaseCRUD)
│   ├── trading/                     # 交易执行层
│   ├── analysis/                    # 分析模块
│   ├── client/                      # CLI客户端 (ginkgo命令)
│   └── libs/                        # 工具库 (GLOG, GCONF, GTM, 装饰器等)

tests/                               # 测试目录
├── unit/                            # 单元测试 (@pytest.mark.unit)
├── integration/                     # 集成测试 (@pytest.mark.integration)
├── database/                        # 数据库测试 (@pytest.mark.database)
└── network/                         # 网络测试 (@pytest.mark.network)
```

## Commands

**系统管理命令**:
```bash
ginkgo system config set --debug on    # 必须开启debug模式才能进行数据库操作
ginkgo version                        # 查看版本信息
ginkgo status                         # 快速系统状态检查
```

**数据管理命令**:
```bash
ginkgo data init                      # 初始化数据库表
ginkgo data update --stockinfo        # 更新股票信息
ginkgo data update day --code 000001.SZ  # 更新日频K线数据
ginkgo data list stockinfo --page 50  # 列出股票信息
```

**回测命令**:
```bash
ginkgo backtest run {engine_id}       # 运行指定回测
ginkgo backtest component list strategy  # 列出可用策略
```

**Worker管理命令**:
```bash
ginkgo worker status                  # 显示worker进程状态
ginkgo worker start --count 4         # 启动4个worker
ginkgo worker run --debug             # 前台运行单个worker
```

## Code Style

**Ginkgo 特定代码规范**:

**1. 服务访问模式**:
```python
# 推荐使用ServiceHub
from ginkgo import service_hub
bar_crud = service_hub.data.cruds.bar()
stockinfo_service = service_hub.data.services.stockinfo_service()

# 向后兼容方式 (仍然支持但建议迁移)
from ginkgo import services
bar_crud = services.data.cruds.bar()
```

**2. 装饰器使用**:
```python
from ginkgo.libs.decorators import time_logger, retry, cache_with_expiration

class MyDataCRUD(BaseCRUD):
    @time_logger          # 性能监控
    @retry(max_try=3)     # 自动重试
    @cache_with_expiration(60)  # 缓存1分钟
    def get_data_filtered(self, **filters):
        pass
```

**3. 模型继承规范**:
```python
# ClickHouse模型
class MBar(BaseModel, MClickBase):
    pass

# MySQL模型
class MStockInfo(BaseModel, MMysqlBase):
    pass
```

**4. CRUD操作命名**:
```python
# 创建操作
add_bar(data)                    # 单条添加
add_bars([data1, data2])         # 批量添加 (推荐)

# 查询操作
get_bars_page_filtered(code="000001.SZ", limit=1000)
get_bar_by_uuid(uuid)

# 更新/删除操作
update_bar(uuid, new_data)
delete_bars_filtered(code="000001.SZ", start="20230101")
```

**5. 事件驱动架构**:
```python
class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        if isinstance(event, EventPriceUpdate):
            # 策略逻辑实现
            bars = self.data_feeder.get_bars(event.code, start, end)
            return [Signal(code=event.code, direction=DIRECTION_TYPES.LONG)]
        return []
```

## Recent Changes

**最近3个功能更新**:

1. **ServiceHub重构** - 统一服务访问协调器，提供懒加载和错误处理
2. **TDD测试框架** - 标准化测试设计方法，支持entity级别的完整测试覆盖
3. **装饰器优化体系** - 完善的性能监控、重试和缓存装饰器支持

## 最佳实践提醒

**必须记住**:
- 数据库操作前必须: `ginkgo system config set --debug on`
- 批量操作优先: 使用`add_bars([])`而非逐条插入
- 遵循TDD流程: 先写测试再实现功能
- 事件驱动设计: PriceUpdate → Strategy → Signal → Portfolio → Order → Fill
- 正确的错误处理: 禁止使用hasattr，基于明确异常类型

<!-- MANUAL ADDITIONS START -->
<!-- 可以在这里添加项目特定的开发指导 -->
<!-- MANUAL ADDITIONS END -->
