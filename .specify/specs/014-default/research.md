# Research: OKX实盘账号API接入

**Feature**: 014-okx-live-account
**Date**: 2026-03-13
**Status**: Complete

## 研究目标

本章节记录OKX实盘接入功能的技术决策和最佳实践研究，为后续设计提供依据。

---

## 1. python-okx SDK研究

### 决策：使用python-okx (okxapi/python-okx)

**理由**:
- 官方推荐SDK，维护活跃
- 完整的V5 API覆盖
- 内置签名、限流、重试处理
- 支持WebSocket和测试网

**关键发现**:
```python
from okx import OkxAPI

# 初始化（支持测试网）
okx = OkxAPI(
    api_key="your-key",
    secret="your-secret",
    password="your-passphrase",
    flag="1"  # 0=生产, 1=测试网
)

# 账户余额
balance = okx.account.get_balance()

# 下单
order = okx.trade.place_order(
    instId="BTC-USDT",
    tdMode="cash",
    side="buy",
    ordType="market",
    sz="100"
)

# WebSocket订阅
from okx import PublicData
ws = PublicData(
    url="wss://wspap.okx.com:8443/ws/v5/public",
    callback=lambda data: print(data)
)
ws.subscribe("tickers", "BTC-USDT")
```

**替代方案评估**:
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| python-okx | 官方支持，功能完整 | 仅支持OKX | ✅ 选用 |
| CCXT | 支持多交易所 | OKX更新不及时，抽象层增加复杂度 | ❌ 不选 |

---

## 2. API凭证加密存储方案

### 决策：使用cryptography库的Fernet对称加密

**理由**:
- 加密强度高（AES-128-CBC + HMAC）
- 简单易用，自动处理IV
- 支持密钥轮换
- Python生态标准库

**实现方案**:
```python
from cryptography.fernet import Fernet
import os

# 密钥管理：从环境变量或配置文件获取
ENCRYPTION_KEY = os.getenv('GINKGO_ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    # 首次生成时需要保存到配置文件

cipher = Fernet(ENCRYPTION_KEY)

# 加密API凭证
def encrypt_credential(plain_text: str) -> str:
    return cipher.encrypt(plain_text.encode()).decode()

# 解密API凭证
def decrypt_credential(cipher_text: str) -> str:
    return cipher.decrypt(cipher_text.encode()).decode()

# 使用示例
api_key = encrypt_credential("your-api-key")
# 存储: cipher_text
# 读取: decrypt_credential(cipher_text) -> "your-api-key"
```

**密钥存储**:
- 生产环境: `~/.ginkgo/secure.yml` (已加入.gitignore)
- 测试环境: 环境变量 `GINKGO_ENCRYPTION_KEY`
- 格式: `encryption_key: base64_encoded_key`

**替代方案评估**:
| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| Fernet | 简单，标准库 | 对称加密，密钥泄露风险 | ✅ 选用 |
| AWS KMS | 高安全性 | 依赖云服务，增加复杂度 | ❌ 过度设计 |
| hashlib+salt | 自主可控 | 需要自己管理很多细节 | ❌ 重复造轮子 |

---

## 3. WebSocket数据同步架构

### 决策：混合模式（WebSocket推送 + 定时轮询备选）

**架构设计**:
```
┌─────────────────────────────────────────────────────────────┐
│                     BrokerInstance                           │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  WebSocketClient │         │  PollingService  │          │
│  │  (主数据源)       │         │  (备用数据源)     │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
│           │                             │                     │
│           ▼                             ▼                     │
│  ┌──────────────────────────────────────────────────┐       │
│  │           DataAggregator (数据聚合器)            │       │
│  │  - 合并WebSocket和轮询数据                        │       │
│  │  - 去重和冲突解决                                │       │
│  │  - 数据完整性校验（每30秒全量对比）                │       │
│  └─────────────────────┬────────────────────────────┘       │
│                        │                                     │
│                        ▼                                     │
│              ┌─────────────────┐                            │
│              │ Portfolio同步   │                            │
│              │ - 余额更新       │                            │
│              │ - 持仓更新       │                            │
│              │ - 订单状态更新   │                            │
│              └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

**WebSocket断线处理流程**:
1. 检测断线（心跳超时或连接异常）
2. 切换到轮询模式（5秒间隔）
3. 尝试重连WebSocket（指数退避）
4. 重连成功后，进行全量数据校验
5. 切回WebSocket主模式

**数据一致性保证**:
- WebSocket推送: 实时性优先，接受短暂延迟
- 定时全量校验: 每30秒一次，确保最终一致性
- 订单状态: 以交易所返回的最终状态为准

---

## 4. Broker实例生命周期管理

### 决策：集中式管理器 + 心跳监控

**架构设计**:
```
┌─────────────────────────────────────────────────────────────┐
│                    LiveEngine (实盘引擎)                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           BrokerManager (Broker管理器)                 │  │
│  │  - 启动时批量创建Broker实例                            │  │
│  │  - 监听live_account_id变更事件                         │  │
│  │  - 动态创建/销毁/重启Broker                            │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │         HeartbeatMonitor (心跳监控器)                  │  │
│  │  - 定期检查Broker心跳（Redis存储）                     │  │
│  │  - 检测超时实例，触发恢复流程                          │  │
│  │  - 记录崩溃历史和分析                                  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

每个BrokerInstance:
├── Portfolio ID
├── LiveAccount ID
├── 状态 (RUNNING/STOPPED/ERROR)
├── 心跳时间戳 (Redis)
└── 进程/线程引用
```

**生命周期状态机**:
```
     [启动]
        │
        ▼
    UNINITIALIZED ──→ INITIALIZING ──→ RUNNING
        │                  │               │
        │                  │               │ (心跳超时)
        │                  │               ▼
        │                  │          RECOVERING
        │                  │               │
        │                  │               ▼
        │                  │            RUNNING
        │                  │               │
        │                  │          (手动停止)
        │                  │               ▼
        │                  └────────→ STOPPED
        │
    (销毁)
        ▼
    TERMINATED
```

**恢复流程**:
1. 检测到心跳超时（>60秒无更新）
2. 标记Broker状态为RECOVERING
3. 停止旧实例（如果进程存在）
4. 全量数据同步（从交易所获取最新状态）
5. 创建新Broker实例
6. 验证连接和权限
7. 切换回RUNNING状态

---

## 5. OKX测试网支持

### 决策：支持测试网模式，便于开发测试

**实现方式**:
```python
class LiveAccount:
    exchange: str = "okx"
    environment: str = "production"  # or "testnet"
    api_key: str (encrypted)
    api_secret: str (encrypted)
    passphrase: str (encrypted)

    def get_okx_client(self):
        flag = "1" if self.environment == "testnet" else "0"
        return OkxAPI(
            api_key=self.decrypt(self.api_key),
            secret=self.decrypt(self.api_secret),
            password=self.decrypt(self.passphrase),
            flag=flag
        )
```

**测试网特点**:
- 无需真实资金
- API与生产环境完全一致
- 支持所有交易功能
- 数据环境独立

**开发建议**:
- 所有单元测试使用测试网
- CI/CD流程使用测试网进行集成测试
- 生产部署前在测试网验证完整流程

---

## 6. 实盘与回测数据模型复用策略

### 决策：扩展字段模式（Optional字段）

**设计原则**:
- 复用现有实体（Bar、Position、Order）
- 添加Optional扩展字段
- 回测和实盘使用相同代码路径

**示例**:
```python
class MOrder(MMysqlBase):
    # 基础字段（回测和实盘共用）
    uuid: str
    code: str
    direction: DIRECTION_TYPES
    volume: Decimal
    price: Optional[Decimal]
    order_type: ORDER_TYPES
    status: ORDERSTATUS_TYPES

    # 实盘扩展字段（Optional，回测时为None）
    account_id: Optional[str] = None  # 关联LiveAccount
    exchange_order_id: Optional[str] = None  # 交易所订单ID
    submit_time: Optional[datetime] = None  # 提交时间
    exchange_response: Optional[str] = None  # 交易所原始响应
```

**好处**:
- 策略代码无需修改
- 风控逻辑复用
- 数据库迁移成本低
- UI组件统一

---

## 技术债务与未来改进

1. **多交易所支持**: 当前设计为OKX，架构支持扩展到Binance等
2. **子账户支持**: 未来可支持OKX统一账户和子账户
3. **高级订单类型**: 未来支持条件单、冰山单、OCO等
4. **费率优化**: 未来支持VIP费率配置和费率回扣
5. **多签钱包**: 未来考虑支持多重签名安全

---

## 参考资源

- [python-okx GitHub](https://github.com/okxapi/python-okx)
- [OKX V5 API文档](https://www.okx.com/docs-v5/)
- [OKX WebSocket文档](https://www.okx.com/docs-v5/ws/)
- [Ginkgo项目架构文档](/docs/architecture.md)
