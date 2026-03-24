# OKX Broker 网络错误重试机制

**日期**: 2026-03-23
**文件**: `src/ginkgo/trading/brokers/okx_broker.py`

## 问题背景

OKX API 在不稳定网络环境下经常出现以下错误：

| 错误类型 | 错误信息 | 原因 |
|---------|---------|------|
| SSL握手超时 | `_ssl.c:983: The handshake operation timed out` | 网络延迟高 |
| SSL连接中断 | `[SSL: UNEXPECTED_EOF_WHILE_READING]` | 连接被服务端关闭 |
| 连接被拒绝 | `[Errno 111] Connection refused` | 端口无法访问 |
| 连接被重置 | `[Errno 104] Connection reset by peer` | API限流或网络问题 |

## 解决方案

### 1. 网络错误分类

```python
class NetworkErrorType(Enum):
    """网络错误类型"""
    SSL_TIMEOUT = "SSL handshake timeout"
    SSL_EOF = "SSL unexpected EOF"
    CONNECTION_REFUSED = "Connection refused"
    CONNECTION_RESET = "Connection reset by peer"
    TIMEOUT = "Request timeout"
    UNKNOWN = "Unknown network error"
```

### 2. 重试配置

```python
class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,          # 最大重试次数
        base_delay: float = 1.0,        # 基础延迟（秒）
        max_delay: float = 60.0,        # 最大延迟（秒）
        exponential_base: float = 2.0,  # 指数退避基数
        jitter: bool = True             # 是否添加随机抖动
    )
```

**默认配置**:
- 最多重试 3 次
- 延迟序列: 1s → 2s → 4s (指数增长)
- 最大延迟 30 秒
- ±20% 随机抖动避免雷击效应

### 3. 核心重试方法

```python
def _execute_with_retry(
    self,
    func: Callable,
    *args,
    operation_name: str = "API call",
    **kwargs
) -> Any:
    """执行API调用并自动重试"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not self._is_retryable_error(e):
                raise

            if attempt < max_retries - 1:
                delay = self._calculate_delay(attempt, config)
                time.sleep(delay)
    raise last_exception
```

### 4. 错误统计

跟踪各类网络错误的发生次数：

```python
broker.get_error_stats()
# {
#     "ssl_timeout": 15,
#     "ssl_eof": 8,
#     "connection_refused": 2,
#     "connection_reset": 5,
#     "timeout": 10,
#     "other": 3
# }
```

## 已更新的方法

以下方法已添加重试机制：

1. ✅ `connect()` - 连接OKX API
2. ✅ `get_account_balance()` - 获取账户余额
3. ✅ `get_positions()` - 获取持仓信息
4. ✅ `get_open_orders()` - 获取挂单信息
5. ✅ `get_ticker()` - 获取交易对行情（新增）
6. ✅ `get_top_volume_pairs()` - 获取高成交量交易对（新增）

## 使用示例

### 基本使用

```python
# 使用默认重试配置
broker = OKXBroker(
    broker_uuid="xxx",
    portfolio_id="yyy",
    live_account_id="zzz",
    api_key=encrypted_key,
    api_secret=encrypted_secret,
    passphrase=encrypted_passphrase
)

# 连接时会自动重试
if broker.connect():
    balance = broker.get_account_balance()  # 自动重试
```

### 自定义重试配置

```python
# 自定义重试配置
custom_config = RetryConfig(
    max_retries=5,           # 增加重试次数
    base_delay=2.0,          # 增加基础延迟
    max_delay=120.0,         # 增加最大延迟
    exponential_base=3.0,    # 更快的指数增长
    jitter=True
)

broker = OKXBroker(
    ...,
    retry_config=custom_config
)
```

## 日志示例

**成功重试**:
```
WARNING: [57ef4e53] Get account balance failed (attempt 1/3): [SSL: UNEXPECTED_EOF_WHILE_READING]. Retrying in 1.2s...
INFO: [57ef4e53] Get account balance succeeded after 1 retries (error was: SSL unexpected EOF)
```

**重试耗尽**:
```
WARNING: [57ef4e53] Get ticker failed (attempt 2/3): Timeout. Retrying in 2.5s...
WARNING: [57ef4e53] Get ticker failed (attempt 3/3): Connection reset. Retrying in 5.1s...
ERROR: [57ef4e53] Get ticker failed after 3 attempts. Final error: Connection reset by peer (Connection reset)
```

## 性能影响

| 场景 | 无重试 | 有重试 |
|-----|-------|-------|
| 正常调用 | 100ms | 100ms |
| 单次重试 | 失败 | ~1.1s |
| 两次重试 | 失败 | ~3.2s |
| 三次重试 | 失败 | ~7.3s |

## 未来改进

- [ ] 添加断路器模式，连续失败时暂停请求
- [ ] 实现请求队列和批处理
- [ ] 添加请求缓存，避免频繁查询相同数据
- [ ] 支持WebSocket实时数据推送，减少轮询
