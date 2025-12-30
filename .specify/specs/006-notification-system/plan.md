# Implementation Plan: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Created**: 2025-12-30
**Status**: Draft

---

## Summary

创建完整的 MongoDB 基础设施层，使其与 ClickHouse 和 MySQL 并列为 Ginkgo 的第一等公民数据库。同时实现基于 MongoDB 的通知系统，支持 Discord 和 Email 渠道。用户管理使用 MySQL（包括用户核心数据、配置和用户组）。

**核心交付物**:
1. **MMongoBase** - MongoDB 文档模型基类
2. **GinkgoMongo** - MongoDB 驱动（基于 pymongo）
3. **BaseMongoCRUD** - MongoDB CRUD 抽象基类
4. **通知系统** - 基于 MongoDB 的通知记录 + MySQL 的用户管理

---

## Technical Context

### 现有架构
- **MClickBase** - ClickHouse 模型基类（时序数据）
- **MMysqlBase** - MySQL 模型基类（关系数据）
- **BaseCRUD** - 通用 CRUD 抽象类（支持 ClickHouse 和 MySQL）
- **GinkgoClick/GinkgoMySQL** - 数据库驱动
- **依赖注入** - 使用 `dependency_injector` 容器

### 新增组件
- **MMongoBase** - MongoDB 模型基类（文档数据）
- **BaseMongoCRUD** - MongoDB CRUD 抽象类
- **GinkgoMongo** - MongoDB 驱动（基于 pymongo）
- **用户管理** - MySQL（MUser, MUserContact, MUserGroup）
- **通知系统** - NotificationService, DiscordChannel, EmailChannel

---

## Constitution Check

### ✅ 安全与合规原则
- **凭证管理**: MySQL 连接通过 `~/.ginkgo/config.yaml`，MongoDB 连接通过 `~/.ginkgo/secure.yml`（敏感凭证单独存储）
- **敏感信息脱敏**: 日志中自动脱敏敏感字段
- **通知目标管理**: Discord频道和Email用户统一作为数据库中的"通知目标"

### ✅ 架构设计原则
- **一致性**: MMongoBase 与 MClickBase/MMysqlBase 设计风格一致
- **依赖注入**: 通过容器访问服务
- **职责分离**: 模型层、CRUD层、服务层严格分离

### ✅ 代码质量原则
- **装饰器优化**: 使用 `@time_logger`、`@retry`、`@cache_with_expiration`
- **类型注解**: 所有公共 API 提供完整类型注解

### ✅ 测试原则
- **TDD 流程**: 先编写测试用例，再实现功能
- **Mock 测试**: 为 MongoDB/MySQL 操作提供 Mock

### ✅ 数据一致性原则
- **级联软删除**: 用户删除时，级联标记其联系方式(UserContact)和组映射(UserGroupMapping)为 is_del=True
- **通知顺序**: 按 Kafka FIFO 顺序处理，无优先级区分

### ✅ 性能原则
- **连接池**: MongoDB/MySQL 连接池
- **批量操作**: 批量插入
- **TTL 索引**: 自动清理过期通知记录（7天，私人小系统）

### ✅ 代码注释同步原则
- 文件头部包含三行注释（Upstream/Downstream/Role）

---

## Phase 0: Research & Design ✅

**Status**: Completed

**Key Decisions**:
1. **数据库**:
   - MongoDB → 通知记录、通知模板（TTL清理、灵活schema）
   - MySQL → 用户核心数据、联系方式、用户组（事务、关系、一致性）
2. **驱动**: pymongo（MongoDB）+ SQLAlchemy（MySQL）
3. **模板引擎**: Jinja2（可选功能）
4. **异步架构**: GTM Worker + Kafka
5. **消息队列**: Kafka（通知系统通过 Kafka 构建异步发送和失败重试机制）
   - 按渠道分 topic: `notifications-discord`, `notifications-email`
   - Worker 处理时再根据 user_id 区分接收者
6. **通知渠道**: Discord + Email
7. **用户模型**:
   - User = 通知接收者（可以是 person、channel、organization）
   - Contact = 联系方式（Email/Discord 使用枚举存储）
8. **失败重试**: Kafka 异步队列自动重试 + 失败记录到 MongoDB

---

## Phase 1: Design & Contracts

**Status**: In Progress

**Artifacts**:
- `plan.md` - 本文件，实现计划
- `contracts/` - API 接口定义（待生成）

### 目录结构

```
# === MongoDB 基础设施（仅用于通知）===
src/ginkgo/data/models/
├── model_mongobase.py              # MMongoBase 基类
├── model_notification_record.py    # MNotificationRecord (MongoDB)
└── model_notification_template.py  # MNotificationTemplate (MongoDB, 可选)

src/ginkgo/data/drivers/
└── ginkgo_mongo.py                  # GinkgoMongo 驱动

src/ginkgo/data/crud/
├── base_mongo_crud.py               # BaseMongoCRUD 抽象类
├── notification_record_crud.py      # NotificationRecordCRUD (MongoDB)
└── notification_template_crud.py    # NotificationTemplateCRUD (MongoDB, 可选)

# === 用户管理（MySQL）===
src/ginkgo/data/models/
├── model_user.py                    # MUser (通知接收者)
├── model_user_contact.py            # MUserContact (联系方式)
├── model_user_group.py              # MUserGroup (用户组)
└── model_user_group_mapping.py      # MUserGroupMapping (多对多映射，带外键)

src/ginkgo/data/crud/
├── user_crud.py                     # UserCRUD
├── user_contact_crud.py             # UserContactCRUD
├── user_group_crud.py               # UserGroupCRUD
└── user_group_mapping_crud.py       # UserGroupMappingCRUD

src/ginkgo/user/
├── __init__.py
└── services/
    └── user_service.py              # UserService

# === 通知系统业务逻辑 ===
src/ginkgo/notifier/
├── __init__.py
├── core/
│   ├── notification_service.py      # NotificationService (依赖 UserService)
│   ├── template_engine.py           # Jinja2 模板引擎（可选）
│   └── message_queue.py             # Kafka 生产者
├── channels/
│   ├── __init__.py
│   ├── base_channel.py              # INotificationChannel 基类
│   ├── discord_channel.py           # Discord Webhook
│   └── email_channel.py             # Email SMTP
├── templates/                       # 预定义模板（YAML）
│   ├── __init__.py
│   ├── trading_signal.yaml
│   ├── backtest_complete.yaml
│   ├── error_alert.yaml
│   └── system_status.yaml
└── workers/
    └── notification_worker.py       # Kafka 消费者

# === 单元测试 ===
test/unit/data/
├── test_model_mongobase.py
├── test_ginkgo_mongo.py
├── test_notification_record_crud.py
├── test_user_crud.py
├── test_user_contact_crud.py
├── test_user_group_crud.py
└── test_user_group_mapping_crud.py

test/unit/notifier/
├── test_core/
│   ├── test_notification_service.py
│   └── test_template_engine.py
└── test_channels/
    ├── test_discord_channel.py
    └── test_email_channel.py
```

**数据库选型说明**：
| 模块 | 数据库 | 原因 |
|------|--------|------|
| 用户接收者 | MySQL | 事务、关系、唯一约束 |
| 联系方式 | MySQL | 关系查询、事务一致性 |
| 用户组 | MySQL | 关系查询 |
| 通知记录 | MongoDB | TTL自动清理、灵活schema |
| 通知模板 | MongoDB | 动态字段、渠道适配 |

**统一通知模型**：
- **User** = 通知接收者（person/channel/organization）
- **UserContact** = 联系方式（Email/Discord 枚举存储）
  - Email: contact_value = 邮箱地址
  - Discord: contact_value = Webhook URL（频道作为 channel 类型用户）
  - is_primary: 标记默认联系方式（用户有多个同类型联系方式时的主要发送目标）
- **渠道凭证**:
  - Discord Webhook: 存储在 MUserContact.contact_value
  - Email SMTP: 存储在 `~/.ginkgo/secure.yml`（全局配置）

---

## Phase 2: Implementation Plan

### P0 - MongoDB 基础设施（核心优先）

#### Task 1: MMongoBase 模型基类
**File**: `src/ginkgo/data/models/model_mongobase.py`

#### Task 2: GinkgoMongo 驱动
**File**: `src/ginkgo/data/drivers/ginkgo_mongo.py`

#### Task 3: BaseMongoCRUD 抽象类
**File**: `src/ginkgo/data/crud/base_mongo_crud.py`

#### Task 4: 更新 models/__init__.py 和 drivers/__init__.py

#### Task 5: 更新 BaseCRUD 支持 MMongoBase
**File**: `src/ginkgo/data/crud/base_crud.py`

---

### P1 - 用户管理（MySQL）

#### Task 6: 枚举定义
**File**: `src/ginkgo/enums.py`

**Code Structure**:
```python
# 在 src/ginkgo/enums.py 中添加以下枚举类

class USER_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    PERSON = 1          # 个人用户
    CHANNEL = 2         # 频道（如Discord频道）
    ORGANIZATION = 3    # 组织/群组

class CONTACT_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    EMAIL = 1           # 邮箱地址
    DISCORD = 2         # Discord Webhook
```

#### Task 7: MUser 模型
**File**: `src/ginkgo/data/models/model_user.py`

**Requirements**:
- 继承 `MMysqlBase, ModelConversion`
- 字段: `user_type` (TINYINT枚举), `name`, `is_active`
- 使用 `TINYINT` 存储枚举，`validate_input()` 处理转换

**Code Structure**:
```python
# Upstream: NotificationService, UserContact Management
# Downstream: MMysqlBase, USER_TYPES, ModelConversion
# Role: MUser通知接收者模型存储用户/频道/组织信息支持通知系统用户管理

import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, USER_TYPES
from ginkgo.libs import datetime_normalize, base_repr


class MUser(MMysqlBase, ModelConversion):
    """通知接收者模型（用户/频道/组织）"""
    __abstract__ = False
    __tablename__ = "users"

    user_type: Mapped[int] = mapped_column(TINYINT, default=-1)
    name: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(TINYINT(1), default=1)

    def __init__(self, name=None, user_type=None, is_active=True, source=None, **kwargs):
        """Initialize MUser with automatic enum/int handling"""
        super().__init__(**kwargs)

        self.name = name or ""

        if user_type is not None:
            self.user_type = USER_TYPES.validate_input(user_type) or USER_TYPES.PERSON.value
        else:
            self.user_type = USER_TYPES.PERSON.value

        self.is_active = 1 if is_active else 0

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.OTHER.value

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        name: str,
        user_type: Optional[USER_TYPES] = None,
        is_active: Optional[bool] = None,
        *args,
        **kwargs,
    ) -> None:
        self.name = name
        if user_type is not None:
            self.user_type = USER_TYPES.validate_input(user_type) or -1
        if is_active is not None:
            self.is_active = 1 if is_active else 0
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.name = df["name"]
        if "user_type" in df.keys():
            self.user_type = USER_TYPES.validate_input(df["user_type"]) or -1
        if "is_active" in df.keys():
            self.is_active = 1 if df["is_active"] else 0
        self.update_at = datetime.datetime.now()

    # 关系：联系方式列表
    contacts = relationship("MUserContact", back_populates="user")

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
```

#### Task 8: MUserContact 模型
**File**: `src/ginkgo/data/models/model_user_contact.py`

**Requirements**:
- 继承 `MMysqlBase, ModelConversion`
- 字段: `user_id` (FK), `contact_type` (TINYINT枚举), `contact_value`, `is_enabled`, `is_primary`
- 使用 `TINYINT` 存储枚举，`validate_input()` 处理转换

**Code Structure**:
```python
# Upstream: NotificationService
# Downstream: MMysqlBase, CONTACT_TYPES, ModelConversion
# Role: MUserContact联系方式模型存储用户Email/Discord等联系方式支持通知发送

import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, CONTACT_TYPES
from ginkgo.libs import datetime_normalize, base_repr


class MUserContact(MMysqlBase, ModelConversion):
    """联系方式模型"""
    __abstract__ = False
    __tablename__ = "user_contacts"

    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.uuid"), nullable=False, index=True)
    contact_type: Mapped[int] = mapped_column(TINYINT, default=-1)
    contact_value: Mapped[str] = mapped_column(String(500), default="")
    is_enabled: Mapped[bool] = mapped_column(TINYINT(1), default=1)
    is_primary: Mapped[bool] = mapped_column(TINYINT(1), default=0)

    def __init__(self, user_id=None, contact_type=None, contact_value=None,
                 is_enabled=True, is_primary=False, source=None, **kwargs):
        """Initialize MUserContact with automatic enum/int handling"""
        super().__init__(**kwargs)

        self.user_id = user_id or ""
        self.contact_value = contact_value or ""

        if contact_type is not None:
            self.contact_type = CONTACT_TYPES.validate_input(contact_type) or CONTACT_TYPES.EMAIL.value
        else:
            self.contact_type = CONTACT_TYPES.EMAIL.value

        self.is_enabled = 1 if is_enabled else 0
        self.is_primary = 1 if is_primary else 0

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.OTHER.value

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        user_id: str,
        contact_value: str,
        contact_type: Optional[CONTACT_TYPES] = None,
        is_enabled: Optional[bool] = None,
        is_primary: Optional[bool] = None,
        *args,
        **kwargs,
    ) -> None:
        self.user_id = user_id
        self.contact_value = contact_value
        if contact_type is not None:
            self.contact_type = CONTACT_TYPES.validate_input(contact_type) or -1
        if is_enabled is not None:
            self.is_enabled = 1 if is_enabled else 0
        if is_primary is not None:
            self.is_primary = 1 if is_primary else 0
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.user_id = df["user_id"]
        self.contact_value = df["contact_value"]
        if "contact_type" in df.keys():
            self.contact_type = CONTACT_TYPES.validate_input(df["contact_type"]) or -1
        if "is_enabled" in df.keys():
            self.is_enabled = 1 if df["is_enabled"] else 0
        if "is_primary" in df.keys():
            self.is_primary = 1 if df["is_primary"] else 0
        self.update_at = datetime.datetime.now()

    # 关系：所属用户
    user = relationship("MUser", back_populates="contacts")

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
```

#### Task 9: MUserGroup 模型
**File**: `src/ginkgo/data/models/model_user_group.py`

**Requirements**:
- 继承 `MMysqlBase, ModelConversion`
- 字段: `group_id`, `group_name`, `description`, `is_active`
- 不存储成员列表，通过 `MUserGroupMapping` 管理

**Code Structure**:
```python
# Upstream: NotificationService
# Downstream: MMysqlBase, ModelConversion
# Role: MUserGroup用户组模型存储用户组信息支持批量通知发送

import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize, base_repr


class MUserGroup(MMysqlBase, ModelConversion):
    """用户组模型"""
    __abstract__ = False
    __tablename__ = "user_groups"

    group_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True, default="")
    group_name: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[Optional[str]] = mapped_column(String(500), default="")
    is_active: Mapped[bool] = mapped_column(TINYINT(1), default=1)

    def __init__(self, group_id=None, group_name=None, description=None,
                 is_active=True, source=None, **kwargs):
        """Initialize MUserGroup"""
        super().__init__(**kwargs)

        self.group_id = group_id or ""
        self.group_name = group_name or ""
        self.description = description or ""
        self.is_active = 1 if is_active else 0

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.OTHER.value

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        group_id: str,
        group_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        *args,
        **kwargs,
    ) -> None:
        self.group_id = group_id
        if group_name is not None:
            self.group_name = group_name
        if description is not None:
            self.description = description
        if is_active is not None:
            self.is_active = 1 if is_active else 0
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.group_id = df["group_id"]
        self.group_name = df.get("group_name", "")
        self.description = df.get("description", "")
        self.is_active = 1 if df.get("is_active", True) else 0
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
```

#### Task 9.5: MUserGroupMapping 模型
**File**: `src/ginkgo/data/models/model_user_group_mapping.py`

**Requirements**:
- 继承 `MMysqlBase`（不继承 ModelConversion）
- 字段: `user_id` (FK), `group_id` (FK), `user_name`, `group_name`
- **添加外键约束**（与现有 mapping 的区别）
- 参考项目 mapping 模式（如 MEnginePortfolioMapping）

**Code Structure**:
```python
# Upstream: NotificationService
# Downstream: MMysqlBase, MUser, MUserGroup (外键约束)
# Role: MUserGroupMapping用户组映射模型多对多关联支持用户组成员管理

import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr


class MUserGroupMapping(MMysqlBase):
    """用户组映射模型（多对多，带外键约束）"""
    __abstract__ = False
    __tablename__ = "user_group_mapping"

    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.uuid"), default="")
    group_id: Mapped[str] = mapped_column(String(32), ForeignKey("user_groups.uuid"), default="")
    user_name: Mapped[str] = mapped_column(String(100), default="")
    group_name: Mapped[str] = mapped_column(String(100), default="")

    def __init__(self, **kwargs):
        """初始化MUserGroupMapping实例"""
        super().__init__()
        if 'source' in kwargs:
            self.set_source(kwargs['source'])
            del kwargs['source']
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        user_id: str,
        group_id: str,
        user_name: Optional[str] = None,
        group_name: Optional[str] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.user_id = user_id
        self.group_id = group_id
        if user_name is not None:
            self.user_name = user_name
        if group_name is not None:
            self.group_name = group_name
        if source is not None:
            self.set_source(source)
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.user_id = df["user_id"]
        self.group_id = df["group_id"]
        self.user_name = df["user_name"]
        self.group_name = df["group_name"]
        if "source" in df.keys():
            self.set_source(df["source"])
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
```

#### Task 10: UserCRUD, UserContactCRUD, UserGroupCRUD, UserGroupMappingCRUD
**Files**:
- `src/ginkgo/data/crud/user_crud.py`
- `src/ginkgo/data/crud/user_contact_crud.py`
- `src/ginkgo/data/crud/user_group_crud.py`
- `src/ginkgo/data/crud/user_group_mapping_crud.py`

**Requirements**:
- 继承 `BaseCRUD`
- 使用 `@time_logger`, `@retry` 装饰器
- UserContactCRUD 提供 `get_enabled_contacts(user_id)` 方法
- UserGroupMappingCRUD 参考现有 mapping CRUD（如 EnginePortfolioMappingCRUD）

---

### P2 - 通知系统核心功能

#### Task 11: MNotificationRecord 模型
**File**: `src/ginkgo/data/models/model_notification_record.py`

**Requirements**:
- 继承 `MMongoBase`
- 字段: `message_id`, `content`, `content_type`, `channels`, `status`, `channel_results`, `attachments`
- `priority` 字段保留（预留未来扩展，当前按 FIFO 处理）

#### Task 12: NotificationRecordCRUD
**File**: `src/ginkgo/data/crud/notification_record_crud.py`

**Requirements**:
- 继承 `BaseMongoCRUD[MNotificationRecord]`
- 创建 TTL 索引（7天自动清理）

#### Task 13: NotificationService
**File**: `src/ginkgo/notifier/core/notification_service.py`

**Requirements**:
- 依赖 `UserService` (MySQL) 查询用户配置
- 实现 `send()`, `send_to_users()`, `send_to_group()` 方法
- 实现 `send_template()` 方法（可选）
- 实现 `send_sync()` 方法（同步，用于测试）

**Code Structure**:
```python
class NotificationService:
    def __init__(self):
        self.user_crud = container.user_crud()  # MySQL
        self.contact_crud = container.user_contact_crud()  # MySQL
        self.group_crud = container.user_group_crud()  # MySQL
        self.record_crud = container.notification_record_crud()  # MongoDB
        self.discord_channel = DiscordChannel()
        self.email_channel = EmailChannel()

    def send_to_users(self, message: NotificationMessage, user_ids: List[str]):
        """发送通知到指定用户列表"""
        # 1. 从MySQL查询用户的联系方式
        contacts = self.contact_crud.get_enabled_contacts_by_user_ids(user_ids)

        # 2. 按类型分组发送
        for contact in contacts:
            if contact.contact_type == ContactTypeEnum.EMAIL:
                self.email_channel.send(message.content, contact.contact_value)
            elif contact.contact_type == ContactTypeEnum.DISCORD:
                self.discord_channel.send(message.content, contact.contact_value)
```

#### Task 14: Discord Channel
**File**: `src/ginkgo/notifier/channels/discord_channel.py`

#### Task 15: Email Channel
**File**: `src/ginkgo/notifier/channels/email_channel.py`

---

### P3 - 高级功能

#### Task 16: Template Engine (可选)
**File**: `src/ginkgo/notifier/core/template_engine.py`

#### Task 17: Notification Worker
**File**: `src/ginkgo/notifier/workers/notification_worker.py`

---


## 数据库架构总结

**混合数据库架构**:

- **MySQL** (事务、关系、一致性):
  - MUser (用户核心)
  - MUserContact (联系方式)
  - MUserGroup (用户组)

- **MongoDB** (灵活schema、TTL自动清理):
  - MNotificationRecord (通知记录)
  - MNotificationTemplate (通知模板)
  - TTL 索引 (7天自动清理)

**交互流程**:
1. 用户登录 → MySQL 验证
2. 发送通知 → 查询MySQL获取配置 → 发送 → 记录到MongoDB
3. 用户组管理 → MySQL 关系查询

---

## CLI Commands

```bash
# MongoDB 初始化
ginkgo data init --mongo

# ========== 用户管理 ==========
ginkgo user add                    # 添加用户（人/频道/组织）
ginkgo user list                   # 列出所有用户
ginkgo user show <user_id>         # 查看用户详情
ginkgo user update <user_id>       # 更新用户信息
ginkgo user delete <user_id>       # 删除用户

# ========== 联系方式管理 ==========
ginkgo user contact add            # 添加联系方式（email/discord）
ginkgo user contact list           # 列出用户的所有联系方式
ginkgo user contact enable         # 启用/禁用联系方式

# ========== 用户组管理 ==========
ginkgo user group create           # 创建用户组
ginkgo user group list             # 列出所有用户组
ginkgo user group show <group_id>  # 查看用户组详情
ginkgo user group add-user         # 添加用户到组
ginkgo user group remove-user      # 从组中移除用户

# ========== 通知系统 ==========
ginkgo notification init           # 初始化（同步预定义模板）
ginkgo notification test            # 测试渠道连接
ginkgo notification send --content "测试" --channels discord,email
ginkgo notification send-to-users --user-ids user1,user2 --content "测试"
ginkgo notification send-to-group --group-id traders --content "组消息"
```

---

## Next Steps

**Recommended Command**: `/speckit.tasks` - 生成详细的任务分解
