# Data Model: OKX实盘账号API接入

**Feature**: 014-okx-live-account
**Date**: 2026-03-13
**Status**: Complete

## 数据模型概览

本功能新增3个核心实体，扩展1个现有实体，复用2个现有实体：

| 实体 | 类型 | 数据库 | 说明 |
|------|------|--------|------|
| LiveAccount | 新增 | MySQL | 实盘账号配置信息 |
| BrokerInstance | 新增 | MySQL | Broker实例运行时状态 |
| TradeRecord | 新增 | ClickHouse | 实盘交易记录（仅审计） |
| MPortfolio | 扩展 | MySQL | 添加live_account_id外键 |
| Position | 复用 | MySQL | 持仓信息（回测+实盘） |
| Order | 复用 | MySQL | 订单信息（回测+实盘） |

---

## 1. LiveAccount (实盘账号配置)

### 实体定义

```python
# src/ginkgo/data/models/model_live_account.py

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from ginkgo.data.models.model_mysql_base import MMysqlBase

class MLiveAccount(MMysqlBase):
    """实盘账号配置信息

    Upstream: Web UI (用户配置), CLI (导入配置)
    Downstream: BrokerManager (创建Broker实例), LiveAccountService (业务逻辑)
    Role: 实盘账号数据模型，存储加密的API凭证和账号元数据
    """

    __tablename__ = "live_accounts"

    # 主键
    uuid = Column(String(36), primary_key=True, comment="账号ID (UUID)")

    # 用户关联
    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")

    # 交易所信息
    exchange = Column(
        SQLEnum("okx", "binance", name="live_account_exchange"),
        nullable=False,
        default="okx",
        comment="交易所类型"
    )
    environment = Column(
        SQLEnum("production", "testnet", name="live_account_environment"),
        nullable=False,
        default="production",
        comment="环境类型"
    )

    # API凭证（加密存储）
    api_key = Column(String(512), nullable=False, comment="加密的API Key")
    api_secret = Column(String(512), nullable=False, comment="加密的API Secret")
    passphrase = Column(String(512), nullable=True, comment="加密的API Passphrase (OKX需要)")

    # 账号状态
    status = Column(
        SQLEnum("enabled", "disabled", "connecting", "disconnected", name="live_account_status"),
        nullable=False,
        default="enabled",
        comment="账号状态"
    )

    # 账号标签和描述
    name = Column(String(100), nullable=False, comment="账号名称（用户自定义）")
    description = Column(String(500), nullable=True, comment="账号描述")

    # 最后验证信息
    last_validated_at = Column(DateTime, nullable=True, comment="最后验证时间")
    validation_status = Column(String(50), nullable=True, comment="验证状态")
    validation_message = Column(String(500), nullable=True, comment="验证消息")

    # 时间戳
    create_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    update_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_live_account_user_exchange', 'user_id', 'exchange'),
        Index('idx_live_account_status', 'status'),
    )
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| uuid | String(36) | ✅ | 唯一标识符 |
| user_id | String(36) | ✅ | 所属用户ID |
| exchange | Enum | ✅ | 交易所类型（okx/binance） |
| environment | Enum | ✅ | 环境（production/testnet） |
| api_key | String(512) | ✅ | 加密的API Key |
| api_secret | String(512) | ✅ | 加密的API Secret |
| passphrase | String(512) | ❌ | 加密的Passphrase（OKX需要） |
| status | Enum | ✅ | 账号状态 |
| name | String(100) | ✅ | 用户定义的账号名称 |
| description | String(500) | ❌ | 账号描述 |
| last_validated_at | DateTime | ❌ | 最后验证时间 |
| validation_status | String(50) | ❌ | 验证状态 |
| validation_message | String(500) | ❌ | 验证消息 |
| create_at | DateTime | ✅ | 创建时间（自动） |
| update_at | DateTime | ✅ | 更新时间（自动） |

### 状态枚举

**status字段**:
- `enabled`: 账号已启用，可以使用
- `disabled`: 账号已禁用，不能使用
- `connecting`: 正在连接中
- `disconnected`: 连接已断开

**environment字段**:
- `production`: 生产环境（真实交易）
- `testnet`: 测试网环境（模拟交易）

### 验证规则

1. API凭证字段必须非空
2. exchange必须是支持的类型
3. status只能在允许的状态间转换
4. user_id必须有效关联到用户表

---

## 2. BrokerInstance (Broker实例运行时状态)

### 实体定义

```python
# src/ginkgo/data/models/model_broker_instance.py

from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from ginkgo.data.models.model_mysql_base import MMysqlBase

class MBrokerInstance(MMysqlBase):
    """Broker实例运行时配置

    Upstream: BrokerManager (生命周期管理)
    Downstream: HeartbeatMonitor (心跳检测), LiveEngine (状态查询)
    Role: Broker实例运行时状态，记录实例生命周期和健康状态
    """

    __tablename__ = "broker_instances"

    # 主键
    uuid = Column(String(36), primary_key=True, comment="实例ID (UUID)")

    # 关联关系
    portfolio_id = Column(String(36), ForeignKey('portfolios.uuid'), nullable=False, index=True, comment="关联的Portfolio ID")
    live_account_id = Column(String(36), ForeignKey('live_accounts.uuid'), nullable=False, index=True, comment="关联的LiveAccount ID")

    # 实例状态
    status = Column(
        SQLEnum(
            "uninitialized",
            "initializing",
            "running",
            "paused",
            "stopped",
            "error",
            "recovering",
            name="broker_instance_status"
        ),
        nullable=False,
        default="uninitialized",
        comment="实例状态"
    )

    # 进程信息（如果是独立进程）
    process_id = Column(Integer, nullable=True, comment="进程ID")
    thread_id = Column(String(36), nullable=True, comment="线程ID")

    # 心跳信息
    last_heartbeat_at = Column(DateTime, nullable=True, comment="最后心跳时间")
    heartbeat_count = Column(Integer, default=0, comment="心跳计数")

    # 错误信息
    last_error_at = Column(DateTime, nullable=True, comment="最后错误时间")
    last_error_message = Column(String(1000), nullable=True, comment="最后错误消息")
    error_count = Column(Integer, default=0, comment="错误次数")

    # 统计信息
    total_orders_submitted = Column(Integer, default=0, comment="提交订单总数")
    total_orders_filled = Column(Integer, default=0, comment="成交订单总数")
    total_volume_traded = Column(String(50), nullable=True, comment="成交总金额")

    # 时间戳
    create_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    update_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    # 索引
    __table_args__ = (
        Index('idx_broker_instance_portfolio', 'portfolio_id'),
        Index('idx_broker_instance_live_account', 'live_account_id'),
        Index('idx_broker_instance_status', 'status'),
        UniqueConstraint('portfolio_id', name='uc_broker_instance_portfolio'),  # 一个Portfolio只有一个实例
    )
```

### 状态机

```
                    [系统启动]
                        │
                        ▼
                  UNINITIALIZED
                        │
                 [初始化请求]
                        ▼
                  INITIALIZING
                        │
            ┌───────────┴───────────┐
            │                       │
        [成功]                   [失败]
            │                       │
            ▼                       ▼
          RUNNING                 ERROR
            │                       │
       [暂停]                   [恢复]
            │                       │
            ▼                       ▼
          PAUSED              RECOVERING
            │                       │
            └───────────┬───────────┘
                        │
                   [手动停止]
                        │
                        ▼
                     STOPPED
                        │
                   [销毁]
                        ▼
                   TERMINATED
```

### 心跳机制

- **心跳间隔**: 10秒
- **超时阈值**: 60秒（6次心跳未更新视为超时）
- **存储位置**: Redis (broker:heartbeat:{instance_uuid})
- **心跳内容**:
  ```json
  {
    "instance_uuid": "xxx",
    "status": "running",
    "timestamp": "2026-03-13T10:30:00Z",
    "uptime_seconds": 3600,
    "memory_mb": 128,
    "cpu_percent": 5.2
  }
  ```

---

## 3. TradeRecord (实盘交易记录)

### 实体定义

```python
# src/ginkgo/data/models/model_trade_record.py

from sqlalchemy import Column, String, DateTime, Decimal
from ginkgo.data.models.model_click_base import MClickBase

class MTradeRecord(MClickBase):
    """实盘交易记录（仅用于审计和分析）

    Upstream: BrokerInstance (交易执行后记录)
    Downstream: DataAnalysis (统计分析), WebUI (历史查询)
    Role: 实盘交易审计日志，记录所有成交明细
    """

    __tablename__ = "trade_records"

    # 主键
    uuid = Column(String(36), primary_key=True, comment="交易ID (UUID)")

    # 账户关联
    account_id = Column(String(36), nullable=False, index=True, comment="LiveAccount ID")

    # 交易基本信息
    exchange = Column(String(20), nullable=False, comment="交易所")
    symbol = Column(String(20), nullable=False, index=True, comment="交易对")
    side = Column(String(10), nullable=False, comment="交易方向 (buy/sell)")

    # 成交信息
    price = Column(Decimal(20, 8), nullable=False, comment="成交价格")
    quantity = Column(Decimal(20, 8), nullable=False, comment="成交数量")
    quote_quantity = Column(Decimal(20, 8), nullable=False, comment="成交金额 (base*price)")

    # 手续费
    fee = Column(Decimal(20, 8), nullable=False, comment="手续费金额")
    fee_currency = Column(String(10), nullable=False, comment="手续费币种")

    # 订单关联
    order_uuid = Column(String(36), nullable=True, comment="内部订单UUID")
    exchange_order_id = Column(String(100), nullable=True, comment="交易所订单ID")
    trade_id = Column(String(100), nullable=True, comment="交易所成交ID")

    # 时间戳
    trade_time = Column(DateTime, nullable=False, comment="成交时间（交易所时间）")
    create_at = Column(DateTime, server_default=func.now(), comment="记录创建时间")

    # 分区键（按月分区）
    partition_key = Column(String(10), nullable=False, comment="分区键 (YYYY-MM)")
```

### ClickHouse分区策略

```sql
-- 按月分区，便于查询和清理历史数据
PARTITION BY toYYYYMM(trade_time)

-- 索引
ORDER BY (account_id, trade_time)
SETTINGS index_granularity = 8192
```

### 与Order实体的关系

| 实体 | 用途 | 保留时长 |
|------|------|----------|
| Order | 运行时订单状态 | 运行期间 |
| TradeRecord | 审计和历史查询 | 永久保留 |

---

## 4. MPortfolio (扩展)

### 新增字段

```python
# src/ginkgo/data/models/model_portfolio.py (扩展)

class MPortfolio(MMysqlBase):
    # ... 现有字段 ...

    # NEW: 实盘账号关联（一对一）
    live_account_id = Column(
        String(36),
        ForeignKey('live_accounts.uuid'),
        nullable=True,
        unique=True,  # 强制一对一
        index=True,
        comment="绑定的实盘账号ID（mode=2时必填）"
    )

    # NEW: 实盘模式状态
    live_status = Column(
        SQLEnum("not_running", "starting", "running", "paused", "stopping", "error", name="portfolio_live_status"),
        nullable=True,
        comment="实盘运行状态（仅mode=2时有效）"
    )
```

### 约束说明

1. **一对一绑定**: `unique=True` 确保一个LiveAccount只能被一个Portfolio绑定
2. **可选关联**: `nullable=True` 允许回测模式（mode=0/1）的Portfolio不绑定实盘账号
3. **状态一致性**: live_status仅在mode=2（实盘模式）时有效
4. **绑定验证**:
   - 绑定前检查LiveAccount未被其他Portfolio使用
   - 解绑时检查Broker实例已停止
   - 删除Portfolio时先解绑并停止Broker

---

## 5. Position与Order (复用扩展)

### Position扩展

```python
class MPosition(MMysqlBase):
    # ... 现有字段 ...

    # NEW: 实盘扩展字段（可选）
    live_account_id = Column(String(36), nullable=True, index=True, comment="实盘账号ID（实盘模式时非空）")
    exchange_position_id = Column(String(100), nullable=True, comment="交易所持仓ID")
```

### Order扩展

```python
class MOrder(MMysqlBase):
    # ... 现有字段 ...

    # NEW: 实盘扩展字段（可选）
    live_account_id = Column(String(36), nullable=True, index=True, comment="实盘账号ID（实盘模式时非空）")
    exchange_order_id = Column(String(100), nullable=True, index=True, comment="交易所订单ID")
    submit_time = Column(DateTime, nullable=True, comment="提交到交易所的时间")
    exchange_response = Column(Text, nullable=True, comment="交易所原始响应JSON")
```

### 复用策略

**优点**:
- 策略代码无需修改
- 风控逻辑完全复用
- 数据库迁移简单
- UI组件统一

**区分方式**:
- 回测订单: `live_account_id IS NULL`
- 实盘订单: `live_account_id IS NOT NULL`

---

## 数据库迁移脚本

### MySQL迁移

```sql
-- 创建 live_accounts 表
CREATE TABLE live_accounts (
    uuid VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'okx',
    environment VARCHAR(20) NOT NULL DEFAULT 'production',
    api_key VARCHAR(512) NOT NULL,
    api_secret VARCHAR(512) NOT NULL,
    passphrase VARCHAR(512),
    status VARCHAR(20) NOT NULL DEFAULT 'enabled',
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    last_validated_at DATETIME,
    validation_status VARCHAR(50),
    validation_message VARCHAR(500),
    create_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_live_account_user_exchange (user_id, exchange),
    INDEX idx_live_account_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建 broker_instances 表
CREATE TABLE broker_instances (
    uuid VARCHAR(36) PRIMARY KEY,
    portfolio_id VARCHAR(36) NOT NULL,
    live_account_id VARCHAR(36) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'uninitialized',
    process_id INT,
    thread_id VARCHAR(36),
    last_heartbeat_at DATETIME,
    heartbeat_count INT DEFAULT 0,
    last_error_at DATETIME,
    last_error_message VARCHAR(1000),
    error_count INT DEFAULT 0,
    total_orders_submitted INT DEFAULT 0,
    total_orders_filled INT DEFAULT 0,
    total_volume_traded VARCHAR(50),
    create_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_broker_instance_portfolio (portfolio_id),
    INDEX idx_broker_instance_live_account (live_account_id),
    INDEX idx_broker_instance_status (status),
    UNIQUE KEY uc_broker_instance_portfolio (portfolio_id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(uuid) ON DELETE CASCADE,
    FOREIGN KEY (live_account_id) REFERENCES live_accounts(uuid) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 扩展 portfolios 表
ALTER TABLE portfolios
ADD COLUMN live_account_id VARCHAR(36) UNIQUE AFTER mode,
ADD COLUMN live_status VARCHAR(20) AFTER live_account_id,
ADD INDEX idx_portfolio_live_account (live_account_id),
ADD FOREIGN KEY (live_account_id) REFERENCES live_accounts(uuid) ON DELETE SET NULL;

-- 扩展 positions 表
ALTER TABLE positions
ADD COLUMN live_account_id VARCHAR(36) AFTER portfolio_id,
ADD COLUMN exchange_position_id VARCHAR(100) AFTER live_account_id,
ADD INDEX idx_position_live_account (live_account_id);

-- 扩展 orders 表
ALTER TABLE orders
ADD COLUMN live_account_id VARCHAR(36) AFTER portfolio_id,
ADD COLUMN exchange_order_id VARCHAR(100) AFTER live_account_id,
ADD COLUMN submit_time DATETIME AFTER exchange_order_id,
ADD COLUMN exchange_response TEXT AFTER submit_time,
ADD INDEX idx_order_live_account (live_account_id),
ADD INDEX idx_order_exchange_order_id (exchange_order_id);
```

### ClickHouse迁移

```sql
-- 创建 trade_records 表
CREATE TABLE trade_records (
    uuid String,
    account_id String,
    exchange String,
    symbol String,
    side String,
    price Decimal(20, 8),
    quantity Decimal(20, 8),
    quote_quantity Decimal(20, 8),
    fee Decimal(20, 8),
    fee_currency String,
    order_uuid String,
    exchange_order_id String,
    trade_id String,
    trade_time DateTime,
    create_at DateTime DEFAULT now(),
    partition_key String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_time)
ORDER BY (account_id, trade_time)
SETTINGS index_granularity = 8192;
```

---

## 数据字典

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| live_accounts | 实盘账号配置 | uuid, exchange, api_key_encrypted |
| broker_instances | Broker实例状态 | uuid, portfolio_id, live_account_id, status |
| trade_records | 交易审计记录 | uuid, account_id, symbol, price, quantity |
| portfolios | 投资组合 | uuid, live_account_id (新增), live_status (新增) |
| positions | 持仓 | uuid, live_account_id (新增), exchange_position_id (新增) |
| orders | 订单 | uuid, live_account_id (新增), exchange_order_id (新增) |

---

## ER图

```
┌─────────────────┐         ┌─────────────────┐
│   LiveAccount   │1       1│   MPortfolio    │
│─────────────────├─────────┤─────────────────│
│ uuid (PK)       │         │ uuid (PK)       │
│ exchange        │         │ live_account_id │
│ api_key_enc     │         │ live_status     │
│ status          │         │ mode            │
└─────────────────┘         └────────┬────────┘
                                     │
                                     │ 1
                                     │
                                     │ 1
                                     ▼
                           ┌─────────────────┐
                           │ BrokerInstance  │
                           │─────────────────│
                           │ uuid (PK)       │
                           │ portfolio_id    │
                           │ live_account_id │
                           │ status          │
                           │ last_heartbeat  │
                           └─────────────────┘

┌─────────────────┐         ┌─────────────────┐
│     Order       │         │    Position     │
│─────────────────┤         │─────────────────│
│ uuid (PK)       │         │ uuid (PK)       │
│ live_account_id │◄──────┐ │ live_account_id │
│ exchange_order_id│       │ exchange_pos_id │
└─────────────────┘       │                 │
                          └─────────────────┘

┌─────────────────┐
│   TradeRecord   │
│─────────────────│
│ uuid (PK)       │
│ account_id      │───→ LiveAccount
│ symbol          │
│ price           │
│ quantity        │
│ trade_time      │
└─────────────────┘
```
