# Research: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Created**: 2025-12-31
**Status**: Draft

## 1. MongoDB 集成最佳实践

### 1.1 PyMongo 连接池配置

**推荐配置**:
```python
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

class GinkgoMongo:
    """Ginkgo MongoDB 驱动 - 连接池管理"""

    def __init__(self, host: str = "localhost", port: int = 27017,
                 username: str = None, password: str = None,
                 database: str = "ginkgo", max_pool_size: int = 10,
                 min_pool_size: int = 2, max_idle_time_ms: int = 10000,
                 connect_timeout_ms: int = 5000, server_selection_timeout_ms: int = 5000):
        """
        初始化 MongoDB 连接池

        连接池参数说明:
        - max_pool_size: 最大连接数，默认 10
        - min_pool_size: 最小连接数，默认 2（保持热连接）
        - max_idle_time_ms: 连接最大空闲时间，超过后释放，默认 10s
        - connect_timeout_ms: 连接超时，默认 5s
        - server_selection_timeout_ms: 服务器选择超时，默认 5s

        理由:
        - 连接池避免频繁建立/断开连接的开销
        - 最小连接数保持热连接，提高响应速度
        - 空闲超时释放不活跃连接，节省资源
        """
        self._client = MongoClient(
            host=host,
            port=port,
            username=username,
            password=password,
            maxPoolSize=max_pool_size,
            minPoolSize=min_pool_size,
            maxIdleTimeMS=max_idle_time_ms,
            connectTimeoutMS=connect_timeout_ms,
            serverSelectionTimeoutMS=server_selection_timeout_ms,
            retryWrites=True,  # 自动重试写入
            w="majority"  # 写确认级别：多数节点确认
        )
        self._database = self._client[database]

    @property
    def database(self):
        """获取数据库实例（懒加载）"""
        return self._database

    def ping(self) -> bool:
        """检查连接状态"""
        try:
            self._client.admin.command('ping')
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError):
            return False
```

**关键设计决策**:
- **连接池**: 避免每次操作都创建新连接，提高性能
- **自动重试写入**: `retryWrites=True` 确保网络临时故障时自动重试
- **写确认级别**: `w="majority"` 确保数据持久化到多数节点
- **超时配置**: 连接超时 5s，避免长时间阻塞

### 1.2 Pydantic ODM 模式

**推荐模式**: 使用 Pydantic 模型 + PyMongo 手动映射

```python
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import uuid4

class MMongoBase(BaseModel):
    """MongoDB 文档模型基类"""

    uuid: str = Field(default_factory=lambda: str(uuid4()))
    create_time: datetime = Field(default_factory=datetime.utcnow)
    update_time: datetime = Field(default_factory=datetime.utcnow)
    is_del: bool = False

    class Config:
        arbitrary_types_allowed = True  # 允许任意类型（如 ObjectId）

    def to_mongo(self) -> Dict[str, Any]:
        """转换为 MongoDB 文档格式"""
        data = self.model_dump(exclude_none=True)
        # Pydantic v3 使用 model_dump() 而非 dict()
        return data

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "MMongoBase":
        """从 MongoDB 文档创建实例"""
        return cls(**data)
```

**为什么不使用 MongoEngine / Beanie ODM**:
- **轻量级**: 直接使用 Pydantic + PyMongo，减少依赖和学习成本
- **灵活性**: 手动映射更灵活，易于与现有 CRUD 系统集成
- **性能**: 避免 ODM 的额外抽象层开销
- **一致性**: 与现有 ClickHouse/MySQL 模型设计保持一致

### 1.3 TTL 索引使用

**通知记录自动清理**:
```python
def init_notification_ttl(db, collection_name: str = "notifications", ttl_days: int = 7):
    """
    创建 TTL 索引，自动清理过期通知记录

    索引规则:
    - 在 create_time 字段创建索引
    - TTL 设置为 7 天（60 * 60 * 24 * 7 秒）
    - MongoDB 后台线程每 60 秒检查一次过期文档

    注意事项:
    - TTL 索引字段必须是 date 类型或包含 date 值的数组
    - TTL 索引是单字段索引，不能是复合索引
    - TTL 清理有一定延迟（最多 60 秒）
    """
    collection = db[collection_name]
    ttl_seconds = ttl_days * 24 * 60 * 60

    # 创建 TTL 索引
    collection.create_index(
        [("create_time", 1)],
        name="ttl_index",
        expireAfterSeconds=ttl_seconds
    )
```

**TTL 最佳实践**:
- **选择合适的时间字段**: 使用 `create_time` 而非 `update_time`，避免更新后延长生命周期
- **合理设置 TTL**: 7 天平衡查询需求和存储成本
- **监控清理延迟**: TTL 清理有 60 秒延迟，不应依赖实时性

---

## 2. Kafka 异步处理模式

### 2.1 Kafka-Python Producer 配置

**推荐配置**:
```python
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json

class NotificationProducer:
    """通知发送 Kafka 生产者"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        """
        初始化 Kafka 生产者

        可靠性配置:
        - acks=all: 等待所有副本确认（最高可靠性）
        - retries=3: 自动重试 3 次
        - max_in_flight_requests_per_connection=1: 禁止并发请求，保证顺序
        - enable_idempotence=True: 幂等性写入，防止重复
        """
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # 可靠性配置
            acks='all',  # 等待所有副本确认
            retries=3,  # 自动重试次数
            max_in_flight_requests_per_connection=1,  # 保证顺序
            enable_idempotence=True,  # 幂等性
            # 性能配置
            compression_type='snappy',  # 压缩算法
            linger_ms=10,  # 批量发送延迟 10ms
            batch_size=16384,  # 批量大小 16KB
            # 超时配置
            request_timeout_ms=30000,  # 请求超时 30s
            metadata_max_age_ms=300000,  # 元数据刷新间隔 5min
        )

    def send_notification(self, topic: str, notification: dict) -> bool:
        """
        发送通知到 Kafka

        降级策略:
        - 如果 Kafka 连接失败，自动降级为同步发送
        - 记录降级事件到日志（WARNING 级别）
        """
        try:
            future = self._producer.send(topic, value=notification)
            record_metadata = future.get(timeout=10)
            return True
        except KafkaError as e:
            GLOG.WARNING(f"Kafka 发送失败，降级为同步发送: {e}")
            # 降级为同步发送（直接调用 DiscordChannel/EmailChannel）
            return self._send_sync(notification)
```

**关键设计决策**:
- **可靠性优先**: `acks=all` 确保消息不丢失
- **幂等性**: `enable_idempotence=True` 防止网络重试导致重复
- **顺序保证**: `max_in_flight_requests_per_connection=1` 确保单用户通知顺序
- **降级机制**: Kafka 不可用时自动降级为同步发送

### 2.2 Topic 分离策略

**Topic 设计**:
```text
notifications-discord  # Discord 通知队列
notifications-email    # Email 通知队列
```

**分离理由**:
1. **消费速率差异**: Discord Webhook 响应快（<1s），Email SMTP 慢（>1s）
2. **重试策略差异**: Discord 超时 3s，Email 超时 10s
3. **优先级控制**: 可以为不同渠道设置不同的消费者数量
4. **故障隔离**: Email 慢速不影响 Discord 实时性

### 2.3 Worker 消费者组设计

**推荐配置**:
```python
from kafka import KafkaConsumer
import threading

class NotificationWorker:
    """通知处理 Worker"""

    def __init__(self, bootstrap_servers: str, group_id: str = "notification-workers"):
        """
        初始化 Kafka 消费者

        消费者组配置:
        - group_id: 消费者组 ID，多个 Worker 共享负载
        - auto_offset_reset='latest': 从最新消息开始消费
        - enable_auto_commit=False: 手动提交 offset，确保处理成功后再提交
        - max_poll_records=100: 单次拉取最多 100 条消息
        """
        self._consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False,
            max_poll_records=100,
            session_timeout_ms=30000,  # Session 超时 30s
            heartbeat_interval_ms=10000,  # 心跳间隔 10s
        )

    def start(self):
        """启动 Worker 消费循环"""
        for message in self._consumer:
            try:
                # 处理通知
                notification = message.value
                self._process_notification(notification)

                # 处理成功后手动提交 offset
                self._consumer.commit()
            except Exception as e:
                GLOG.ERROR(f"通知处理失败: {e}")
                # 不提交 offset，Kafka 会重新投递
```

**关键设计决策**:
- **消费者组**: 多个 Worker 共享负载，Kafka 自动分区分配
- **手动提交 offset**: 处理成功后再提交，确保不丢失消息
- **失败重试**: 处理失败不提交 offset，Kafka 重新投递
- **Session 超时**: 30s 超时，避免长时间处理导致消费者被踢出

---

## 3. Jinja2 模板引擎

### 3.1 变量替换最佳实践

**模板示例**:
```jinja2
# Discord 交易信号模板
{# Discord: Trading Signal Template #}
**交易信号**: {{ signal_type }}

**代码**: {{ symbol }}
**价格**: {{ price }}
**时间**: {{ timestamp }}

{% if stop_loss %}
**止损**: {{ stop_loss }}
{% endif %}

{% if take_profit %}
**止盈**: {{ take_profit }}
{% endif %}
```

**模板变量定义**:
```python
variables = {
    "signal_type": {
        "type": "string",
        "default": "",
        "description": "信号类型（买入/卖出）"
    },
    "symbol": {
        "type": "string",
        "default": "",
        "description": "交易代码"
    },
    "price": {
        "type": "float",
        "default": 0.0,
        "description": "价格"
    },
    "timestamp": {
        "type": "string",
        "default": "",
        "description": "时间戳"
    },
    "stop_loss": {
        "type": "float",
        "default": None,
        "description": "止损价（可选）"
    },
    "take_profit": {
        "type": "float",
        "default": None,
        "description": "止盈价（可选）"
    }
}
```

### 3.2 错误处理策略

```python
from jinja2 import Template, Environment, StrictUndefined
from jinja2.exceptions import TemplateError, UndefinedError

class TemplateRenderer:
    """模板渲染器"""

    def __init__(self):
        # 使用 StrictUndefined 模式，变量未定义时抛出异常
        self._env = Environment(undefined=StrictUndefined)

    def render(self, template_content: str, variables: dict) -> str:
        """
        渲染模板

        错误处理策略:
        - 变量未定义: 抛出 UndefinedError，记录 WARNING 日志
        - 模板语法错误: 抛出 TemplateError，记录 ERROR 日志
        - 渲染失败时: 回退到原始模板内容，记录 ERROR 日志
        """
        try:
            template = self._env.from_string(template_content)
            return template.render(**variables)
        except UndefinedError as e:
            GLOG.WARNING(f"模板变量未定义: {e}")
            # 使用默认值重新渲染
            return self._render_with_defaults(template_content, variables)
        except TemplateError as e:
            GLOG.ERROR(f"模板渲染失败: {e}")
            # 回退到原始模板内容
            return template_content

    def _render_with_defaults(self, template_content: str, variables: dict) -> str:
        """使用默认值重新渲染"""
        env = Environment(undefined=None)  # 允许未定义变量，返回空字符串
        template = env.from_string(template_content)
        return template.render(**variables)
```

**错误处理原则**:
1. **严格模式优先**: 使用 `StrictUndefined` 捕获变量缺失
2. **默认值回退**: 变量缺失时尝试使用默认值
3. **原始内容回退**: 渲染完全失败时返回原始模板
4. **分级日志**: WARNING 记录变量缺失，ERROR 记录模板错误

---

## 4. Discord/Email 渠道

### 4.1 Discord Webhook 超时配置

```python
import requests
from requests.exceptions import Timeout, RequestException

class DiscordChannel:
    """Discord 通知渠道"""

    def __init__(self, webhook_url: str, timeout: int = 3):
        """
        初始化 Discord 渠道

        超时配置:
        - timeout: 请求超时时间（秒），默认 3s
        - 理由: Discord Webhook 通常 < 1s 响应，3s 足够
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, content: str, embed: dict = None) -> bool:
        """
        发送 Discord 通知

        超时处理:
        - 超过 timeout 秒未响应，抛出 Timeout 异常
        - Kafka Worker 会捕获异常并重试
        """
        payload = {"content": content}
        if embed:
            payload["embeds"] = [embed]

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except Timeout:
            GLOG.ERROR(f"Discord Webhook 超时（>{self.timeout}s）")
            return False
        except RequestException as e:
            GLOG.ERROR(f"Discord Webhook 请求失败: {e}")
            return False
```

### 4.2 Email SMTP 超时和重试

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailChannel:
    """Email 通知渠道"""

    def __init__(self, smtp_host: str, smtp_port: int,
                 username: str, password: str, timeout: int = 10):
        """
        初始化 Email 渠道

        超时配置:
        - timeout: SMTP 超时时间（秒），默认 10s
        - 理由: Email SMTP 可能较慢，10s 提供足够时间
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.timeout = timeout

    def send(self, to: str, subject: str, content: str) -> bool:
        """
        发送 Email 通知

        超时处理:
        - 连接超时: 抛出 smtplib.SMTPConnectError
        - 发送超时: 抛出 smtplib.SMTPException
        - Kafka Worker 会捕获异常并重试
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(content, 'plain'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port,
                             timeout=self.timeout) as server:
                server.starttls()  # 启用 TLS
                server.login(self.username, self.password)
                server.send_message(msg)
                return True
        except smtplib.SMTPConnectError as e:
            GLOG.ERROR(f"Email SMTP 连接超时: {e}")
            return False
        except smtplib.SMTPException as e:
            GLOG.ERROR(f"Email SMTP 发送失败: {e}")
            return False
```

**渠道差异化超时**:
- **Discord**: 3s 超时（快速响应，适合实时通知）
- **Email**: 10s 超时（慢速协议，适合详细报告）
- **配置化**: 在 `~/.ginkgo/config.yaml` 中定义，支持动态调整

---

## 5. 分级日志策略

根据规格 SC-016，定义分级日志策略：

### 5.1 日志级别定义

| 级别 | 用途 | 示例场景 |
|------|------|----------|
| **ERROR** | 严重错误，需要人工介入 | Discord Webhook 失效、SMTP 连接断开、MongoDB 写入失败 |
| **WARNING** | 降级/重试，系统自动处理 | Kafka 不可用降级为同步发送、Webhook 超时重试、模板变量缺失 |
| **INFO** | 关键操作，状态变更 | 通知发送成功、Worker 启动/停止、用户创建/删除 |
| **DEBUG** | 详细追踪，问题排查 | Kafka 消息详情、模板渲染中间状态、数据库查询参数 |

### 5.2 日志使用示例

```python
from ginkgo.libs import GLOG

# ERROR: 严重错误
GLOG.ERROR(f"Discord Webhook 返回 404: {webhook_url}")
GLOG.ERROR(f"MongoDB 连接失败: {str(e)}")

# WARNING: 降级/重试
GLOG.WARNING(f"Kafka 不可用，降级为同步发送")
GLOG.WARNING(f"Webhook 超时（>{timeout}s），将在 {retry_after}s 后重试")
GLOG.WARNING(f"模板变量缺失: {missing_var}，使用默认值")

# INFO: 关键操作
GLOG.info(f"通知发送成功: message_id={message_id}, user_id={user_id}")
GLOG.info(f"Worker 启动: group_id={group_id}, topics={topics}")

# DEBUG: 详细追踪
GLOG.DEBUG(f"Kafka 消息内容: {notification}")
GLOG.DEBUG(f"模板渲染结果: {rendered_content}")
```

---

## 6. 配置文件设计

### 6.1 `~/.ginkgo/secure.yml`

```yaml
# MongoDB 凭证
mongodb:
  username: "ginkgo_user"
  password: "secure_password_here"

# Email SMTP 凭证
email:
  smtp_host: "smtp.example.com"
  smtp_port: 587
  username: "notifications@example.com"
  password: "smtp_password_here"
```

### 6.2 `~/.ginkgo/config.yaml`

```yaml
# MongoDB 配置
mongodb:
  host: "localhost"
  port: 27017
  database: "ginkgo"
  max_pool_size: 10
  min_pool_size: 2
  connect_timeout_ms: 5000

# Kafka 配置
kafka:
  bootstrap_servers: "localhost:9092"
  notification_discord_topic: "notifications-discord"
  notification_email_topic: "notifications-email"
  producer_group_id: "notification-producers"
  worker_group_id: "notification-workers"

# 通知渠道超时配置
notifications:
  discord:
    timeout: 3  # 3秒超时
    max_retries: 3
  email:
    timeout: 10  # 10秒超时
    max_retries: 3

# 通知记录 TTL 配置
notifications:
  record_ttl_days: 7  # 7天自动清理
```

---

## 7. 技术决策总结

| 技术点 | 决策 | 理由 |
|--------|------|------|
| **MongoDB 连接池** | PyMongo 连接池（max=10, min=2） | 避免频繁连接开销，保持热连接 |
| **ODM 模式** | Pydantic + PyMongo 手动映射 | 轻量级、灵活、与现有系统一致 |
| **TTL 索引** | 7 天自动清理 | 平衡查询需求和存储成本 |
| **Kafka 可靠性** | acks=all + 幂等性 + 手动提交 offset | 最高可靠性，确保消息不丢失 |
| **Topic 分离** | notifications-discord / notifications-email | 消费速率差异、重试策略差异、故障隔离 |
| **降级策略** | Kafka 不可用时同步发送 | 保证关键通知送达 |
| **模板引擎** | Jinja2 + StrictUndefined | 捕获变量缺失，支持复杂逻辑 |
| **渠道超时** | Discord 3s / Email 10s | 差异化超时，平衡实时性和可靠性 |
| **日志策略** | 分级日志（ERROR/WARNING/INFO/DEBUG） | 清晰的问题追踪和状态监控 |

---

**Research 完成**: 本文档记录了 MongoDB 基础设施与通知系统的关键技术决策和最佳实践，为后续设计和实现提供技术指导。
