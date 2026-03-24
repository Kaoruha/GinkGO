# Quickstart: OKX实盘账号API接入

**Feature**: 014-okx-live-account
**Date**: 2026-03-13
**For**: 开发者和用户

---

## 概述

本文档介绍如何使用Ginkgo的OKX实盘交易功能，包括账号配置、Broker管理、实盘交易等。

---

## 前置条件

1. **OKX账号**: 已注册OKX账号并完成KYC认证
2. **API密钥**: 已在OKX后台创建API密钥（需交易权限）
3. **IP白名单**: 已将服务器IP添加到OKX IP白名单
4. **Ginkgo环境**: Python 3.12.8 + Ginkgo已安装
5. **数据库**: MySQL、ClickHouse、Redis、Kafka已配置

---

## 快速开始

### 1. 安装依赖

```bash
# 安装python-okx SDK
pip install python-okx

# 或使用项目安装脚本
python install.py
```

### 2. 配置加密密钥

```bash
# 生成加密密钥（首次使用）
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 将密钥保存到配置文件
echo "encryption_key: YOUR_BASE64_KEY" >> ~/.ginkgo/secure.yml
```

### 3. 创建实盘账号

**CLI方式**:
```bash
# 启用debug模式（数据库操作必须）
ginkgo system config set --debug on

# 创建实盘账号
ginkgo live account create \
    --name "我的OKX主账号" \
    --exchange okx \
    --api-key "your-api-key" \
    --api-secret "your-api-secret" \
    --passphrase "your-passphrase" \
    --environment testnet  # 测试网

# 验证API凭证
ginkgo live account validate <account-uuid>
```

**API方式**:
```python
from ginkgo import service_hub

account_service = service_hub.data.services.live_account_service()

# 创建账号
account = account_service.create_account(
    user_id="user-uuid",
    exchange="okx",
    environment="testnet",
    name="我的OKX主账号",
    api_key="your-api-key",
    api_secret="your-api-secret",
    passphrase="your-passphrase"
)

# 验证凭证
result = account_service.validate_account(account.uuid)
print(result.valid, result.message)
```

### 4. 绑定到Portfolio

```python
from ginkgo import service_hub

portfolio_service = service_hub.trading.portfolios.portfolio_service()
broker_manager = service_hub.trading.brokers.broker_manager()

# 获取或创建Portfolio
portfolio = portfolio_service.get_portfolio_by_name("我的BTC策略")

# 绑定实盘账号
broker_manager.bind_live_account(
    portfolio_id=portfolio.uuid,
    live_account_id=account.uuid,
    auto_start=True  # 自动启动Broker
)
```

### 5. 启动实盘交易

**启动LiveCore引擎**:
```bash
# 启动实盘引擎
python -m ginkgo.livecore.main live-start

# 或使用CLI
ginkgo-live live-start

# 带调试模式
python -m ginkgo.livecore.main live-start --debug
```

**控制Broker实例**:
```python
from ginkgo import service_hub

broker_manager = service_hub.trading.brokers.broker_manager()

# 启动
broker_manager.start_broker("broker-instance-uuid")

# 暂停
broker_manager.pause_broker("broker-instance-uuid")

# 恢复
broker_manager.resume_broker("broker-instance-uuid")

# 停止
broker_manager.stop_broker("broker-instance-uuid")
```

---

## Web UI使用

### 1. 访问实盘控制面板

```
http://localhost:5173/live/trading
```

### 2. 配置实盘账号

1. 点击「实盘账号」→「添加账号」
2. 填写表单：
   - 账号名称：自定义名称
   - 交易所：选择OKX
   - 环境：生产/测试网
   - API Key：从OKX后台复制
   - API Secret：从OKX后台复制
   - Passphrase：从OKX后台复制
3. 点击「测试连接」验证凭证
4. 点击「保存」

### 3. 绑定到Portfolio

1. 进入Portfolio详情页
2. 点击「绑定实盘账号」
3. 选择已配置的实盘账号
4. 点击「绑定并启动」

### 4. 控制实盘交易

**单Portfolio控制**:
- 启动：开始接收策略信号并执行交易
- 暂停：保持连接，停止新订单
- 恢复：恢复执行新订单
- 停止：断开连接，停止交易

**全局紧急停止**:
- 点击右上角「紧急停止」按钮
- 确认后所有实盘交易立即停止

---

## 交易流程

### 完整事件链路

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Price   │ →  │ Strategy │ →  │  Signal  │ →  │Portfolio │
│  Update  │    │          │    │          │    │          │
└──────────┘    └──────────┘    └────┬─────┘    └─────┬─────┘
                                          │                │
                                          ▼                ▼
                                      ┌──────────┐    ┌──────────┐
                                      │   Order  │ →  │  Broker  │
                                      │          │    │          │
                                      └────┬─────┘    └─────┬─────┘
                                           │                │
                                           ▼                ▼
                                      ┌──────────┐    ┌──────────┐
                                      │   Fill   │ ←  │   OKX    │
                                      │          │    │   API    │
                                      └──────────┘    └──────────┘
```

### 1. 价格更新触发

```python
# Kafka接收价格更新（DataManager发布）
{
    "type": "bar_snapshot",
    "symbol": "BTC-USDT",
    "close": 45000.00,
    "timestamp": "2026-03-13T10:30:00Z"
}
```

### 2. 策略生成信号

```python
class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        # 策略逻辑
        if self.should_buy():
            return Signal(
                code="BTC-USDT",
                direction=DIRECTION_TYPES.LONG,
                volume=0.1
            )
```

### 3. Portfolio生成订单

```python
# Portfolio接收信号，生成Order
order = Order(
    code="BTC-USDT",
    direction=DIRECTION_TYPES.LONG,
    volume=0.1,
    order_type=ORDER_TYPES.MARKET
)
```

### 4. Broker提交到OKX

```python
# OKXBroker.submit_order()
okx_response = okx.trade.place_order(
    instId="BTC-USDT",
    tdMode="cash",
    side="buy",
    ordType="market",
    sz="0.01"  # OKX使用最小交易单位
)
```

### 5. 成交返回

```python
# WebSocket接收成交事件
{
    "data": [{
        "tradeId": "12345",
        "px": "45000.00",
        "sz": "0.1",
        "side": "buy"
    }]
}
```

---

## 数据同步

### WebSocket推送（主）

```python
# OKXBroker订阅WebSocket
public_data.subscribe("tickers", "BTC-USDT")
private_data.subscribe("account", "balance")
private_data.subscribe("trade", "orders")
```

### 定时轮询（备）

```python
# 每30秒全量校验
@schedule(interval=30)
def full_sync():
    balance = okx.account.get_balance()
    positions = okx.account.get_positions()
    orders = okx.trade.get_orders_history()
    # 对比并更新本地状态
```

---

## 风控配置

### Portfolio级别风控

```python
from ginkgo.trading.risk import PositionRatioRisk, LossLimitRisk

portfolio = portfolio_service.get_portfolio(portfolio_id)

# 添加风控
portfolio.add_risk_manager(PositionRatioRisk(
    max_position_ratio=0.2,  # 单股最大20%仓位
    max_total_position_ratio=0.8  # 总仓位最大80%
))

portfolio.add_risk_manager(LossLimitRisk(
    loss_limit=1000.0  # 最大亏损1000 USDT
))
```

### 紧急停止

```python
from ginkgo import service_hub

broker_manager = service_hub.trading.brokers.broker_manager()

# 方式1：停止单个Portfolio
broker_manager.stop_broker_by_portfolio(portfolio_id)

# 方式2：全局紧急停止
broker_manager.emergency_stop_all()

# 方式3：通过Web UI
# 点击「紧急停止」按钮
```

---

## 监控和日志

### 查看Broker状态

```bash
# 查看所有Broker实例
ginkgo live broker list

# 查看Broker详情
ginkgo live broker info <instance-id>

# 查看Broker日志
tail -f logs/live/broker_<instance-id>.log
```

### 查看交易历史

```bash
# 查看成交记录
ginkgo live trades list --account-id <account-id> --limit 100

# 导出CSV
ginkgo live trades export --account-id <account-id> --output trades.csv
```

### 告警通知

```bash
# 配置邮件通知
echo "notifications:
  email:
    enabled: true
    to: your-email@example.com" >> ~/.ginkgo/config.yml

# 配置企业微信通知
echo "notifications:
  wechat_work:
    enabled: true
    webhook: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" >> ~/.ginkgo/config.yml
```

---

## 故障排查

### 常见问题

**1. API凭证验证失败**
```
错误信息：IP not in whitelist
解决：将服务器IP添加到OKX IP白名单
```

**2. WebSocket连接断开**
```
错误信息：WebSocket connection lost
解决：检查网络连接，系统会自动重连
```

**3. 订单提交失败**
```
错误信息：Insufficient balance
解决：检查账户余额是否充足
```

**4. Broker实例崩溃**
```
错误信息：Broker heartbeat timeout
解决：系统会自动重启，检查日志排查原因
```

### 日志位置

```
logs/
├── live/
│   ├── live_engine.log       # LiveCore引擎日志
│   ├── broker_<id>.log        # Broker实例日志
│   ├── data_sync.log          # 数据同步日志
│   └── heartbeat_monitor.log  # 心跳监控日志
└── error.log                  # 全局错误日志
```

---

## 测试网使用

### 为什么使用测试网？

- 无需真实资金
- 完整功能测试
- 验证策略逻辑
- 熟悉操作流程

### 测试网账号

```bash
# 创建测试网账号
ginkgo live account create \
    --name "OKX测试网" \
    --exchange okx \
    --environment testnet \
    --api-key "testnet-api-key" \
    --api-secret "testnet-secret" \
    --passphrase "testnet-pass"
```

### 测试网资源

- OKX测试网文档: https://www.okx.com/docs-v5/testnet/
- 测试网资金领取: 每天可领取测试资金

---

## 生产环境注意事项

### 上线前检查清单

- [ ] 策略经过充分回测验证
- [ ] 在测试网完整运行一周以上
- [ ] API凭证权限最小化（只开必需权限）
- [ ] IP白名单配置正确
- [ ] 风控参数设置合理
- [ ] 监控和告警配置完成
- [ ] 紧急停止流程测试通过
- [ ] 团队成员熟悉操作流程

### 风险控制建议

1. **小额起步**: 首次实盘使用小额资金验证
2. **逐步放大**: 确认稳定后再增加资金
3. **实时监控**: 密切关注系统状态和交易结果
4. **定期检查**: 每日检查交易记录和账户状态
5. **备份预案**: 准备紧急停止和手动接管方案

---

## 下一步

- [ ] 阅读完整API文档: `/contracts/live-account-api.yml`
- [ ] 查看数据模型: `data-model.md`
- [ ] 了解DTO定义: `/contracts/live-trading-dto.md`
- [ ] 参考测试用例: `tests/livecore/`

---

## 技术支持

- GitHub Issues: https://github.com/your-org/ginkgo/issues
- 文档: `/docs`
- 示例代码: `/examples/live-trading/`
