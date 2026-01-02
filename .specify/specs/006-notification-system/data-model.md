# Data Model: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Created**: 2025-12-31
**Status**: Draft

## 1. 实体定义

### 1.1 MySQL 数据模型（用户管理）

#### MUser - 用户模型

**职责**: 存储通知接收者（person 个人用户 / channel 频道 / organization 组织）

**数据表**: `users`

```sql
CREATE TABLE users (
    uuid CHAR(36) PRIMARY KEY,
    user_type INT NOT NULL DEFAULT 0,  -- USER_TYPES 枚举
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_del BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_user_type (user_type),
    INDEX idx_is_active (is_active),
    INDEX idx_is_del (is_del)
);
```

**属性说明**:
- `uuid`: 用户唯一标识（主键）
- `user_type`: 用户类型枚举（VOID=-1, OTHER=0, PERSON=1, CHANNEL=2, ORGANIZATION=3）
- `name`: 用户名称（个人用户姓名 / 频道名称 / 组织名称）
- `is_active`: 是否激活（禁用用户不会发送通知）
- `is_del`: 软删除标记

**业务规则**:
- 用户删除（`is_del=True`）时，级联标记其联系方式和组映射为 `is_del=True`
- `user_type=CHANNEL` 时，`name` 存储 Discord 频道名称

---

#### MUserContact - 用户联系方式模型

**职责**: 存储用户的联系方式（Email / Discord Webhook）

**数据表**: `user_contacts`

```sql
CREATE TABLE user_contacts (
    uuid CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    contact_type INT NOT NULL,  -- CONTACT_TYPES 枚举
    contact_value VARCHAR(512) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_del BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_contact_type (contact_type),
    INDEX idx_is_enabled (is_enabled),
    INDEX idx_is_del (is_del)
);
```

**属性说明**:
- `uuid`: 联系方式唯一标识（主键）
- `user_id`: 外键引用 `users.uuid`
- `contact_type`: 联系方式类型枚举（VOID=-1, OTHER=0, EMAIL=1, DISCORD=2）
- `contact_value`: 联系方式值（Email 地址 / Discord Webhook URL）
- `is_enabled`: 是否启用（禁用的联系方式不会发送通知）
- `is_primary`: 是否为主要联系方式（预留字段，未来用于默认渠道选择）

**业务规则**:
- `contact_type=EMAIL` 时，`contact_value` 存储邮箱地址（如 `user@example.com`）
- `contact_type=DISCORD` 时，`contact_value` 存储 Discord Webhook URL（如 `https://discord.com/api/webhooks/...`）
- 用户删除时，级联软删除所有联系方式（触发器或应用层处理）
- 同一用户可以有多个联系方式（多个 Email / 多个 Discord Webhook）

---

#### MUserGroup - 用户组模型

**职责**: 管理用户组（用于批量通知）

**数据表**: `user_groups`

```sql
CREATE TABLE user_groups (
    uuid CHAR(36) PRIMARY KEY,
    group_id VARCHAR(64) UNIQUE NOT NULL,  -- 用户组唯一标识
    group_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_del BOOLEAN NOT NULL DEFAULT FALSE,
    INDEX idx_group_id (group_id),
    INDEX idx_is_active (is_active),
    INDEX idx_is_del (is_del)
);
```

**属性说明**:
- `uuid`: 用户组唯一标识（主键）
- `group_id`: 用户组唯一标识（业务键，如 `trading-team`, `admin-group`）
- `group_name`: 用户组名称（显示名称）
- `description`: 用户组描述
- `is_active`: 是否激活（禁用用户组不会发送通知）

---

#### MUserGroupMapping - 用户组成员映射模型

**职责**: 多对多映射（用户 ↔ 用户组）

**数据表**: `user_group_mappings`

```sql
CREATE TABLE user_group_mappings (
    uuid CHAR(36) PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    group_id CHAR(36) NOT NULL,
    user_name VARCHAR(255) NOT NULL,  -- 冗余存储，便于查询
    group_name VARCHAR(255) NOT NULL,  -- 冗余存储，便于查询
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_del BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(uuid) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES user_groups(uuid) ON DELETE CASCADE,
    UNIQUE KEY uk_user_group (user_id, group_id),
    INDEX idx_user_id (user_id),
    INDEX idx_group_id (group_id),
    INDEX idx_is_del (is_del)
);
```

**属性说明**:
- `uuid`: 映射唯一标识（主键）
- `user_id`: 外键引用 `users.uuid`
- `group_id`: 外键引用 `user_groups.uuid`
- `user_name`: 冗余存储用户名称（便于查询和日志）
- `group_name`: 冗余存储用户组名称（便于查询和日志）

**业务规则**:
- 唯一约束 `uk_user_group` 确保同一用户不能重复加入同一组
- 用户删除时，级联删除所有映射关系
- 用户组删除时，级联删除所有映射关系

---

### 1.2 MongoDB 数据模型（通知记录和模板）

#### MNotificationTemplate - 通知模板模型

**职责**: 存储通知模板（支持 Jinja2 变量替换）

**Collection**: `notification_templates`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class MNotificationTemplate(BaseModel):
    """通知模板模型（MongoDB）"""

    # 主键
    template_id: str = Field(..., description="模板唯一标识")
    template_name: str = Field(..., description="模板名称")

    # 模板内容
    template_type: int = Field(default=1, description="模板类型（TEXT=1, MARKDOWN=2, EMBEDDED=3）")
    subject: Optional[str] = Field(None, description="邮件主题（仅 Email 使用）")
    content: str = Field(..., description="模板内容（Jinja2 语法）")

    # 模板变量定义
    variables: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="模板变量定义，格式: {\"var_name\": {\"type\": \"string\", \"default\": \"\", \"description\": \"描述\"}}"
    )

    # 状态管理
    is_active: bool = Field(default=True, description="是否激活")

    # 元数据
    create_time: datetime = Field(default_factory=datetime.utcnow)
    update_time: datetime = Field(default_factory=datetime.utcnow)
```

**示例数据**:
```python
{
    "template_id": "trading_signal_v1",
    "template_name": "交易信号通知",
    "template_type": 2,  # MARKDOWN
    "subject": "交易信号: {{ symbol }}",
    "content": """
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
""",
    "variables": {
        "signal_type": {"type": "string", "default": "", "description": "信号类型（买入/卖出）"},
        "symbol": {"type": "string", "default": "", "description": "交易代码"},
        "price": {"type": "float", "default": 0.0, "description": "价格"},
        "timestamp": {"type": "string", "default": "", "description": "时间戳"},
        "stop_loss": {"type": "float", "default": None, "description": "止损价（可选）"},
        "take_profit": {"type": "float", "default": None, "description": "止盈价（可选）"}
    },
    "is_active": True,
    "create_time": "2025-12-31T00:00:00Z",
    "update_time": "2025-12-31T00:00:00Z"
}
```

**业务规则**:
- `template_id` 全局唯一，用于快速查找模板
- `template_type` 决定渲染格式（TEXT 纯文本 / MARKDOWN Markdown / EMBEDDED Discord Embed）
- `variables` 定义模板所需的变量及其类型、默认值、描述
- `subject` 仅用于 Email 渠道，Discord 渠道忽略此字段

---

#### MNotificationRecord - 通知记录模型

**职责**: 存储通知发送记录（支持 TTL 自动清理）

**Collection**: `notification_records`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ChannelResult(BaseModel):
    """单渠道发送结果"""
    channel: str  # "discord" / "email"
    user_id: str
    contact_value: str  # Email 地址 / Webhook URL
    status: int  # NOTIFICATION_STATUS_TYPES (PENDING=0, SENT=1, FAILED=2, RETRYING=3)
    error_message: Optional[str] = None
    retry_count: int = 0
    sent_time: Optional[datetime] = None

class MNotificationRecord(BaseModel):
    """通知记录模型（MongoDB）"""

    # 主键
    message_id: str = Field(..., description="消息唯一标识")

    # 消息内容
    content: str = Field(..., description="通知内容")
    content_type: int = Field(default=1, description="内容类型（TEXT=1, MARKDOWN=2, EMBEDDED=3）")

    # 发送目标
    channels: List[str] = Field(..., description="发送渠道列表（如 ['discord', 'email']）")
    user_ids: List[str] = Field(..., description="接收用户 UUID 列表")

    # 发送状态
    status: int = Field(default=0, description="总体状态（PENDING=0, SENT=1, FAILED=2, RETRYING=3）")
    channel_results: List[ChannelResult] = Field(default_factory=list, description="各渠道发送结果")

    # 优先级（预留字段，当前按 FIFO 处理）
    priority: int = Field(default=0, description="优先级（0=普通，1=高，2=紧急）")

    # 元数据
    create_time: datetime = Field(default_factory=datetime.utcnow)
    update_time: datetime = Field(default_factory=datetime.utcnow)
```

**示例数据**:
```python
{
    "message_id": "msg_20251231_001",
    "content": "**交易信号**: 买入\n\n**代码**: AAPL\n**价格**: 150.0",
    "content_type": 2,  # MARKDOWN
    "channels": ["discord", "email"],
    "user_ids": ["user_uuid_1", "user_uuid_2"],
    "status": 1,  # SENT
    "channel_results": [
        {
            "channel": "discord",
            "user_id": "user_uuid_1",
            "contact_value": "https://discord.com/api/webhooks/...",
            "status": 1,  # SENT
            "error_message": None,
            "retry_count": 0,
            "sent_time": "2025-12-31T00:00:05Z"
        },
        {
            "channel": "email",
            "user_id": "user_uuid_1",
            "contact_value": "user@example.com",
            "status": 1,  # SENT
            "error_message": None,
            "retry_count": 0,
            "sent_time": "2025-12-31T00:00:06Z"
        },
        {
            "channel": "discord",
            "user_id": "user_uuid_2",
            "contact_value": "https://discord.com/api/webhooks/...",
            "status": 2,  # FAILED
            "error_message": "Webhook 返回 404",
            "retry_count": 3,
            "sent_time": None
        }
    ],
    "priority": 0,
    "create_time": "2025-12-31T00:00:00Z",
    "update_time": "2025-12-31T00:00:06Z"
}
```

**业务规则**:
- `message_id` 全局唯一，用于追踪消息状态
- `status` 是总体状态，只要有一个渠道成功则为 SENT
- `channel_results` 记录每个渠道的发送结果（包含重试信息）
- TTL 索引在 `create_time` 字段，7 天后自动删除

---

## 2. 关系图（ER Diagram）

### 2.1 MySQL 关系图

```text
┌─────────────────────┐
│      MUser          │
├─────────────────────┤
│ uuid (PK)           │
│ user_type           │
│ name                │
│ is_active           │
│ create_time         │
│ update_time         │
│ is_del              │
└─────────┬───────────┘
          │ 1
          │
          │ N
┌─────────▼───────────┐
│   MUserContact      │
├─────────────────────┤
│ uuid (PK)           │
│ user_id (FK)        │───┐
│ contact_type        │   │
│ contact_value       │   │
│ is_enabled          │   │
│ is_primary          │   │
│ create_time         │   │
│ update_time         │   │
│ is_del              │   │
└─────────────────────┘   │
                           │ 级联软删除
                           │
┌─────────▼───────────┐   │
│ MUserGroupMapping   │   │
├─────────────────────┤   │
│ uuid (PK)           │   │
│ user_id (FK)        │───┘
│ group_id (FK)       │───┐
│ user_name           │   │
│ group_name          │   │
│ create_time         │   │
│ update_time         │   │
│ is_del              │   │
└─────────────────────┘   │
                           │
┌─────────▼───────────┐   │
│    MUserGroup       │   │
├─────────────────────┤   │
│ uuid (PK)           │   │
│ group_id (UNIQUE)   │   │
│ group_name          │   │
│ description         │   │
│ is_active           │   │
│ create_time         │   │
│ update_time         │   │
│ is_del              │   │
└─────────────────────┘   │
                           │
级联删除（ON DELETE CASCADE）  │
```

### 2.2 MongoDB 关系图

```text
┌─────────────────────────────┐
│  MNotificationTemplate      │
├─────────────────────────────┤
│ _id (ObjectId, PK)          │
│ template_id (UNIQUE)        │
│ template_name               │
│ template_type               │
│ subject                     │
│ content                     │
│ variables (JSON)            │
│ is_active                   │
│ create_time                 │
│ update_time                 │
└─────────────────────────────┘
           │ 引用
           │ (template_id)
           │
           ▼
┌─────────────────────────────┐
│  MNotificationRecord        │
├─────────────────────────────┤
│ _id (ObjectId, PK)          │
│ message_id (UNIQUE)         │
│ content                     │
│ content_type                │
│ channels[]                  │
│ user_ids[]                  │
│ status                      │
│ channel_results[]           │
│ priority                    │
│ create_time (TTL 索引)      │ ← 7 天后自动删除
│ update_time                 │
└─────────────────────────────┘
```

### 2.3 跨数据库关系

```text
MySQL (用户管理)                 MongoDB (通知记录)
─────────────────                ─────────────────
MUser.uuid ────────────────────> MNotificationRecord.user_ids[]
    │                                 │
    │ 1                               │ N
    │                                 │
    ▼                                 │
MUserContact.contact_value ─────────> MNotificationRecord.channel_results[].contact_value
    │                                 │
    │ 引用                            │ 记录
    │                                 │
    ▼                                 ▼
DiscordChannel.send()          MNotificationRecord (发送结果)
EmailChannel.send()
```

**关系说明**:
- MySQL 存储用户信息和联系方式（结构化数据，支持事务和外键）
- MongoDB 存储通知记录和模板（灵活文档，支持 TTL 和复杂嵌套）
- `MNotificationRecord.user_ids` 引用 MySQL 的 `MUser.uuid`
- `MNotificationRecord.channel_results[].contact_value` 记录实际使用的联系方式

---

## 3. 枚举类型

### 3.1 USER_TYPES（用户类型）

```python
from enum import IntEnum

class USER_TYPES(IntEnum):
    """用户类型枚举"""
    VOID = -1        # 无效类型
    OTHER = 0        # 其他类型
    PERSON = 1       # 个人用户
    CHANNEL = 2      # 频道/群组（如 Discord 频道）
    ORGANIZATION = 3 # 组织/公司
```

### 3.2 CONTACT_TYPES（联系方式类型）

```python
class CONTACT_TYPES(IntEnum):
    """联系方式类型枚举"""
    VOID = -1   # 无效类型
    OTHER = 0   # 其他类型
    EMAIL = 1   # Email 邮箱
    DISCORD = 2 # Discord Webhook URL
```

### 3.3 NOTIFICATION_STATUS_TYPES（通知状态）

```python
class NOTIFICATION_STATUS_TYPES(IntEnum):
    """通知状态枚举"""
    PENDING = 0   # 待发送（已入队）
    SENT = 1      # 已发送（至少一个渠道成功）
    FAILED = 2    # 发送失败（所有渠道失败）
    RETRYING = 3  # 重试中（Kafka 自动重试）
```

### 3.4 TEMPLATE_TYPES（模板类型）

```python
class TEMPLATE_TYPES(IntEnum):
    """模板类型枚举"""
    VOID = -1       # 无效类型
    OTHER = 0       # 其他类型
    TEXT = 1        # 纯文本
    MARKDOWN = 2    # Markdown 格式
    EMBEDDED = 3    # Discord Embed 格式
```

---

## 4. 索引策略

### 4.1 MySQL 索引

| 表名 | 索引名 | 字段 | 类型 | 用途 |
|------|--------|------|------|------|
| `users` | `idx_user_type` | `user_type` | 普通索引 | 按用户类型查询 |
| `users` | `idx_is_active` | `is_active` | 普通索引 | 查询激活用户 |
| `users` | `idx_is_del` | `is_del` | 普通索引 | 过滤已删除用户 |
| `user_contacts` | `idx_user_id` | `user_id` | 普通索引 | 查询用户的联系方式 |
| `user_contacts` | `idx_contact_type` | `contact_type` | 普通索引 | 按联系方式类型查询 |
| `user_contacts` | `idx_is_enabled` | `is_enabled` | 普通索引 | 查询启用的联系方式 |
| `user_contacts` | `idx_is_del` | `is_del` | 普通索引 | 过滤已删除联系方式 |
| `user_groups` | `idx_group_id` | `group_id` | 唯一索引 | 用户组唯一标识 |
| `user_groups` | `idx_is_active` | `is_active` | 普通索引 | 查询激活用户组 |
| `user_groups` | `idx_is_del` | `is_del` | 普通索引 | 过滤已删除用户组 |
| `user_group_mappings` | `uk_user_group` | `user_id, group_id` | 唯一索引 | 防止重复映射 |
| `user_group_mappings` | `idx_user_id` | `user_id` | 普通索引 | 查询用户所属组 |
| `user_group_mappings` | `idx_group_id` | `group_id` | 普通索引 | 查询用户组成员 |

### 4.2 MongoDB 索引

| Collection | 索引名 | 字段 | 类型 | 用途 |
|-----------|--------|------|------|------|
| `notification_templates` | `idx_template_id` | `template_id` | 唯一索引 | 模板唯一标识 |
| `notification_templates` | `idx_is_active` | `is_active` | 普通索引 | 查询激活模板 |
| `notification_records` | `idx_message_id` | `message_id` | 唯一索引 | 消息唯一标识 |
| `notification_records` | `idx_create_time_ttl` | `create_time` | TTL 索引 | 7 天自动清理 |
| `notification_records` | `idx_status` | `status` | 普通索引 | 按状态查询 |
| `notification_records` | `idx_user_ids` | `user_ids` | 普通索引 | 按用户查询通知记录 |

---

## 5. 数据迁移策略

### 5.1 MySQL 初始化

```bash
# 创建数据库和表
ginkgo system config set --debug on
ginkgo data init
```

### 5.2 MongoDB 初始化

```python
# 创建 TTL 索引
def init_mongodb_indexes(db):
    # 通知模板索引
    db.notification_templates.create_index("template_id", unique=True)
    db.notification_templates.create_index("is_active")

    # 通知记录索引
    db.notification_records.create_index("message_id", unique=True)
    db.notification_records.create_index("create_time", name="ttl_index",
                                         expireAfterSeconds=7*24*60*60)
    db.notification_records.create_index("status")
    db.notification_records.create_index("user_ids")
```

### 5.3 测试数据准备

```python
# 创建测试用户
user = MUser(
    uuid="test_user_uuid",
    user_type=USER_TYPES.PERSON,
    name="测试用户",
    is_active=True
)

# 创建测试联系方式
contact = MUserContact(
    uuid="test_contact_uuid",
    user_id="test_user_uuid",
    contact_type=CONTACT_TYPES.EMAIL,
    contact_value="test@example.com",
    is_enabled=True
)

# 创建测试模板
template = MNotificationTemplate(
    template_id="test_template",
    template_name="测试模板",
    template_type=TEMPLATE_TYPES.TEXT,
    content="Hello, {{ name }}!",
    variables={"name": {"type": "string", "default": "Guest"}}
)
```

---

**Data Model 完成**: 本文档定义了 MySQL 和 MongoDB 的数据模型、关系图、枚举类型和索引策略，为后续实现提供清晰的数据结构设计。
