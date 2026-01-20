# LiveDataFeeder接口契约

**Component**: LiveDataFeeder (Abstract Base Class)
**Module**: `src/ginkgo/livecore/data_feeders/base_feeder.py`
**Version**: 1.0.0
**Date**: 2026-01-09

## 一、组件概述

### 1.1 职责定义

LiveDataFeeder是数据源适配器抽象基类，定义统一的数据源接口，负责：

1. **连接管理**: 建立和维护与数据源的连接（WebSocket/HTTP）
2. **订阅管理**: 动态添加/删除订阅标的（增量更新）
3. **数据接收**: 接收实时Tick数据并发布到Queue
4. **异常处理**: 实现断线重连和心跳检测机制

### 1.2 架构定位

```
DataManager → LiveDataFeeder → Queue → TickConsumer → Kafka
```

**六边形架构定位**: LiveDataFeeder作为 **Driven Adapter**，负责外部数据源（WebSocket/HTTP）与系统内部（Queue）的适配。

### 1.3 依赖关系

**Upstream**:
- `queue.Queue` - Tick数据队列（线程安全）
- `ginkgo.interfaces.kafka_topics` - Kafka Topic常量定义

**Downstream**:
- `Queue` - Tick数据队列（生产者）
- `WebSocket/HTTP` - 数据源连接（具体实现）

---

## 二、公共接口定义

### 2.1 抽象基类定义

```python
from abc import ABC, abstractmethod
from threading import Thread, Event
from typing import Set, Optional
from queue import Queue
import asyncio
import websockets

class LiveDataFeeder(ABC):
    """
    数据源适配器抽象基类

    职责：
    1. 建立和维护与数据源的连接（WebSocket/HTTP）
    2. 动态添加/删除订阅标的（增量更新）
    3. 接收实时Tick数据并发布到Queue
    4. 实现断线重连和心跳检测机制

    线程模型：
    - 主线程：调用set_symbols()更新订阅
    - 子线程：运行异步事件循环（WebSocket连接）或HTTP轮询循环

    实现要求：
    - 必须实现抽象方法：_connect(), _subscribe(), _unsubscribe()
    - 必须支持增量订阅（to_add, to_remove）
    - 必须实现断线重连机制（指数退避）
    - 必须支持异步停止（stop()等待线程结束）

    示例实现：
    - EastMoneyFeeder: WebSocket连接（A股）
    - FuShuFeeder: HTTP轮询（港股）
    - AlpacaFeeder: WebSocket连接（美股）
    """

    def __init__(self, queue: Queue, market: str):
        """
        初始化LiveDataFeeder

        Args:
            queue: Tick数据队列（线程安全）
            market: 市场标识（"cn", "hk", "us"）

        初始化状态：
        - all_symbols: 空集合
        - loop: None（在start()时创建）
        - thread: None（在start()时创建）
        - websocket: None（在_connect()时创建）
        - _stop_event: 未设置状态
        """
        self.queue = queue
        self.market = market
        self.all_symbols: Set[str] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[Thread] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._stop_event = Event()
        self._reconnect_event = asyncio.Event()

    # ========================================
    # 公共接口（由DataManager调用）
    # ========================================

    def set_symbols(self, symbols: Set[str]) -> None:
        """
        增量更新订阅标的

        Args:
            symbols: 新的订阅标的集合

        执行步骤：
        1. 计算增量：to_add = symbols - self.all_symbols
        2. 计算减量：to_remove = self.all_symbols - symbols
        3. 更新all_symbols
        4. 如果已连接，触发订阅更新（异步调用_subscribe/_unsubscribe）

        线程安全：
        - 如果已连接，使用asyncio.run_coroutine_threadsafe()安全调用异步方法
        - 更新all_symbols无需加锁（只在主线程调用）

        异常处理：
        - WebSocket未连接：仅更新all_symbols，等待连接后订阅
        - 订阅失败：记录错误日志，继续处理其他标的

        示例：
            feeder = EastMoneyFeeder(queue, "cn")
            feeder.set_symbols({"000001.SZ", "600000.SH"})  # 初始订阅
            feeder.set_symbols({"000001.SZ", "600000.SH", "00700.HK"})  # 增加订阅
            feeder.set_symbols({"000001.SZ"})  # 减少订阅
        """
        pass

    def start(self) -> None:
        """
        启动Feeder（在独立线程运行事件循环）

        执行步骤：
        1. 创建子线程
        2. 启动子线程（target=self._run_event_loop）
        3. 子线程创建新的事件循环（asyncio.new_event_loop()）
        4. 子线程运行异步主循环（_auto_reconnect()）

        异常处理：
        - 线程创建失败：记录错误日志，抛出FeederException
        - 事件循环创建失败：记录错误日志，抛出FeederException

        线程安全：无需加锁（start()仅在主线程调用一次）

        示例：
            feeder = EastMoneyFeeder(queue, "cn")
            feeder.start()
            # WebSocket连接在后台线程建立
        """
        pass

    def stop(self) -> None:
        """
        停止Feeder（等待线程结束）

        执行步骤：
        1. 设置_stop_event标志（通知事件循环退出）
        2. 如果WebSocket已连接，关闭连接（异步调用websocket.close()）
        3. 等待子线程结束（thread.join(timeout=5)）
        4. 清理资源（关闭事件循环）

        超时处理：
        - 线程join超时（5秒）：记录警告日志，强制关闭

        线程安全：无需加锁（stop()仅在主线程调用一次）

        示例：
            feeder.stop()
            # 等待WebSocket连接关闭和线程结束
        """
        pass

    # ========================================
    # 抽象方法（子类必须实现）
    # ========================================

    @abstractmethod
    async def _connect(self) -> None:
        """
        建立数据源连接（抽象方法）

        功能：
        - WebSocket实现：建立WebSocket连接（websockets.connect()）
        - HTTP实现：发送HTTP请求验证连接

        异常处理：
        - 连接失败：抛出ConnectionError（由_auto_reconnect()捕获并重连）

        线程安全：在事件循环线程中执行，无需加锁

        示例（WebSocket）：
            async def _connect(self):
                uri = "wss://push2.eastmoney.com/ws/qt/stock/klt.min"
                self.websocket = await websockets.connect(
                    uri,
                    ping_interval=30,
                    ping_timeout=60,
                    close_timeout=10
                )

        示例（HTTP）:
            async def _connect(self):
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.http_uri) as resp:
                        if resp.status != 200:
                            raise ConnectionError(f"HTTP {resp.status}")
        """
        pass

    @abstractmethod
    async def _subscribe(self, symbols: Set[str]) -> None:
        """
        订阅标的（抽象方法）

        Args:
            symbols: 要订阅的标的集合

        功能：
        - WebSocket实现：发送订阅消息到WebSocket（如{"cmd": "sub", "symbols": [...]}）
        - HTTP实现：订阅在连接时已确定，此方法为空操作

        异常处理：
        - 订阅失败：记录错误日志，继续处理其他标的

        线程安全：在事件循环线程中执行，无需加锁

        示例（WebSocket）：
            async def _subscribe(self, symbols):
                msg = {
                    "cmd": "sub",
                    "param": {"symbols": list(symbols)}
                }
                await self.websocket.send(json.dumps(msg))

        示例（HTTP）:
            async def _subscribe(self, symbols):
                # HTTP订阅在连接时确定，无需额外操作
                pass
        """
        pass

    @abstractmethod
    async def _unsubscribe(self, symbols: Set[str]) -> None:
        """
        取消订阅（抽象方法）

        Args:
            symbols: 要取消订阅的标的集合

        功能：
        - WebSocket实现：发送取消订阅消息到WebSocket（如{"cmd": "unsub", "symbols": [...]}）
        - HTTP实现：订阅在连接时已确定，此方法为空操作

        异常处理：
        - 取消订阅失败：记录错误日志，继续处理其他标的

        线程安全：在事件循环线程中执行，无需加锁

        示例（WebSocket）：
            async def _unsubscribe(self, symbols):
                msg = {
                    "cmd": "unsub",
                    "param": {"symbols": list(symbols)}
                }
                await self.websocket.send(json.dumps(msg))

        示例（HTTP）:
            async def _unsubscribe(self, symbols):
                # HTTP订阅在连接时确定，无需额外操作
                pass
        """
        pass

    # ========================================
    # 内部方法（可选重写）
    # ========================================

    async def _auto_reconnect(self, max_attempts: int = 5, base_delay: int = 2) -> None:
        """
        自动重连逻辑（可选重写）

        Args:
            max_attempts: 最大重试次数
            base_delay: 基础退避延迟（秒）

        功能：
        - 循环调用_connect()，直到连接成功或达到最大重试次数
        - 指数退避：delay = base_delay ^ attempt（最大60秒）
        - 连接成功后，订阅初始标的，进入接收循环

        异常处理：
        - 所有重试失败：记录错误日志，抛出ConnectionError

        线程安全：在事件循环线程中执行，无需加锁
        """
        pass

    async def _connect_and_receive(self) -> None:
        """
        连接并接收消息（可选重写）

        功能：
        - 调用_connect()建立连接
        - 调用_subscribe(self.all_symbols)订阅初始标的
        - 进入消息接收循环，直到连接断开或_stop_event设置

        异常处理：
        - 连接断开：退出函数（由_auto_reconnect()捕获并重连）
        - 消息解析失败：记录错误日志，继续接收下一条消息

        线程安全：在事件循环线程中执行，无需加锁
        """
        pass

    def _run_event_loop(self) -> None:
        """
        运行异步事件循环（在子线程中执行）

        执行步骤：
        1. 创建新的事件循环（asyncio.new_event_loop()）
        2. 设置为当前线程的事件循环（asyncio.set_event_loop()）
        3. 运行_auto_reconnect()（loop.run_until_complete()）
        4. 关闭事件循环

        线程安全：在子线程中执行，无需加锁
        """
        pass
```

### 2.2 具体实现示例

#### EastMoneyFeeder (WebSocket实现)

```python
class EastMoneyFeeder(LiveDataFeeder):
    """东方财富数据源（A股，WebSocket）"""

    def __init__(self, queue: Queue):
        super().__init__(queue, market="cn")
        self.websocket_uri = "wss://push2.eastmoney.com/ws/qt/stock/klt.min"

    async def _connect(self) -> None:
        """建立WebSocket连接"""
        self.websocket = await websockets.connect(
            self.websocket_uri,
            ping_interval=30,  # 30秒发送一次ping
            ping_timeout=60,   # 60秒未收到pong则断开
            close_timeout=10
        )

    async def _subscribe(self, symbols: Set[str]) -> None:
        """订阅标的"""
        if not symbols:
            return

        # 东方财富订阅格式
        msg = {
            "cmd": "sub",
            "param": {
                "symbols": [s.replace(".SZ", "").replace(".SH", "") for s in symbols]
            }
        }

        await self.websocket.send(json.dumps(msg))

    async def _unsubscribe(self, symbols: Set[str]) -> None:
        """取消订阅"""
        if not symbols:
            return

        msg = {
            "cmd": "unsub",
            "param": {
                "symbols": [s.replace(".SZ", "").replace(".SH", "") for s in symbols]
            }
        }

        await self.websocket.send(json.dumps(msg))

    async def _connect_and_receive(self) -> None:
        """连接并接收消息"""
        await self._connect()
        await self._subscribe(self.all_symbols)

        # 消息接收循环
        while not self._stop_event.is_set():
            try:
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=1.0
                )
                await self._handle_message(message)

            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break

    async def _handle_message(self, message: str) -> None:
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            tick = self._parse_tick(data)
            self.queue.put(tick)
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    def _parse_tick(self, data: dict) -> Tick:
        """解析Tick数据"""
        return Tick(
            code=data['code'] + ".SZ",  # 添加市场后缀
            price=float(data['price']),
            volume=int(data['volume']),
            timestamp=datetime.now()
        )
```

#### FuShuFeeder (HTTP轮询实现)

```python
class FuShuFeeder(LiveDataFeeder):
    """FuShu数据源（港股，HTTP轮询）"""

    def __init__(self, queue: Queue):
        super().__init__(queue, market="hk")
        self.http_uri = "https://api.fushu.com/v1/tick"
        self.poll_interval = 5  # 5秒轮询间隔

    async def _connect(self) -> None:
        """验证HTTP连接"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.http_uri) as resp:
                if resp.status != 200:
                    raise ConnectionError(f"HTTP {resp.status}")

    async def _subscribe(self, symbols: Set[str]) -> None:
        """订阅标的（HTTP轮询模式，订阅在请求参数中）"""
        # HTTP模式订阅在请求参数中，此处无需额外操作
        pass

    async def _unsubscribe(self, symbols: Set[str]) -> None:
        """取消订阅（HTTP轮询模式，无需额外操作）"""
        pass

    async def _connect_and_receive(self) -> None:
        """连接并接收消息（HTTP轮询模式）"""
        await self._connect()

        # 轮询循环
        while not self._stop_event.is_set():
            try:
                # 构建请求参数
                params = {
                    "symbols": ",".join(self.all_symbols)
                }

                # 发送HTTP请求
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.http_uri, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            await self._handle_message(data)

                # 等待下次轮询
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"HTTP poll error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _handle_message(self, data: dict) -> None:
        """处理接收到的消息"""
        try:
            for item in data['data']:
                tick = self._parse_tick(item)
                self.queue.put(tick)
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    def _parse_tick(self, data: dict) -> Tick:
        """解析Tick数据"""
        return Tick(
            code=data['code'] + ".HK",
            price=float(data['price']),
            volume=int(data['volume']),
            timestamp=datetime.now()
        )
```

---

## 三、输入输出契约

### 3.1 输入契约

**set_symbols()输入**:
```python
symbols: Set[str]  # 标的集合
# 示例：{"000001.SZ", "600000.SH", "00700.HK"}
```

**标的格式**:
- A股: `{code}.SZ` 或 `{code}.SH`（如"000001.SZ", "600000.SH"）
- 港股: `{code}.HK`（如"00700.HK"）
- 美股: `{code}`（如"AAPL", "TSLA"）

### 3.2 输出契约

**Queue输出** (Tick对象):
```python
Tick(
    code="000001.SZ",
    price=10.50,
    volume=10000,
    amount=105000.0,
    timestamp=datetime(2026, 1, 9, 9, 30, 0)
)
```

**字段说明**:
- `code` (str, required): 标的代码（带市场后缀）
- `price` (float, required): 最新价格
- `volume` (int, required): 成交量
- `amount` (float, optional): 成交额
- `timestamp` (datetime, required): Tick时间戳

---

## 四、错误处理契约

### 4.1 异常定义

```python
class FeederException(Exception):
    """LiveDataFeeder基础异常"""
    pass

class FeederConnectionException(FeederException):
    """连接异常"""
    pass

class FeederSubscriptionException(FeederException):
    """订阅异常"""
    pass
```

### 4.2 异常处理策略

| 异常场景 | 处理策略 | 日志级别 | 告警 |
|---------|---------|---------|-----|
| WebSocket连接失败 | 指数退避重连（最大5次） | WARNING | 不告警 |
| WebSocket连接断开 | 自动重连（最大5次） | WARNING | 不告警 |
| 订阅失败 | 记录错误日志，跳过该标的 | ERROR | 不告警 |
| 消息解析失败 | 记录错误日志，跳过该消息 | WARNING | 不告警 |
| 所有重试失败 | 记录错误日志，抛出ConnectionError | ERROR | 发送告警 |
| HTTP请求失败 | 等待下次轮询（5秒后重试） | WARNING | 不告警 |

---

## 五、性能约束

### 5.1 延迟约束

- **WebSocket心跳延迟**: < 100ms（ping/pong）
- **数据接收延迟**: < 50ms（从数据源发送到Queue.put()）

### 5.2 吞吐量约束

- **支持并发订阅**: >= 1000个标的
- **消息处理速率**: > 1000 messages/sec

---

## 六、测试契约

### 6.1 单元测试

**注意**: LiveDataFeeder不需要编写具体测试（由实际使用验证）

### 6.2 集成测试

**测试类**: `tests/network/livecore/test_live_data_feeder_integration.py`

**测试用例**:
1. `test_websocket_connection` - 测试WebSocket连接
2. `test_subscription_update` - 测试订阅更新
3. `test_auto_reconnect` - 测试自动重连
4. `test_tick_to_queue` - 测试Tick数据发布到Queue

---

## 七、配置契约

### 7.1 环境变量

| 变量名 | 类型 | 必需 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `EASTMONEY_TOKEN` | str | 否 | - | 东方财富API Token |
| `FUSHU_TOKEN` | str | 否 | - | FuShu API Token |
| `ALPACA_API_KEY` | str | 否 | - | Alpaca API Key |
| `ALPACA_API_SECRET` | str | 否 | - | Alpaca API Secret |

### 7.2 配置文件

**路径**: `~/.ginkgo/data_sources.yml`

```yaml
data_sources:
  eastmoney:
    websocket_uri: "wss://push2.eastmoney.com/ws/qt/stock/klt.min"
    ping_interval: 30
    ping_timeout: 60

  fushu:
    http_uri: "https://api.fushu.com/v1/tick"
    poll_interval: 5

  alpaca:
    websocket_uri: "wss://stream.data.alpaca.markets/v2/iex"
```

---

## 八、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2026-01-09 | 初始版本 |
