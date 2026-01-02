# Quickstart: MongoDB 基础设施与通知系统

**Feature Branch**: `006-notification-system`
**Created**: 2025-12-31
**Status**: Draft

## 前置条件

### 1. 环境准备

确保已安装以下依赖：

```bash
# MongoDB 4.4+
sudo apt-get install mongodb

# Kafka 2.8+
# 下载并解压 Kafka
wget https://downloads.apache.org/kafka/2.8.2/kafka_2.13-2.8.2.tgz
tar -xzf kafka_2.13-2.8.2.tgz
cd kafka_2.13-2.8.2

# 启动 Zookeeper 和 Kafka
bin/zookeeper-server-start.sh config/zookeeper.properties &
bin/kafka-server-start.sh config/server.properties &
```

### 2. 配置文件设置

**`~/.ginkgo/secure.yml`** (敏感凭证):
```yaml
# MongoDB 凭证
mongodb:
  username: "ginkgo_user"
  password: "your_secure_password"

# Email SMTP 凭证
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  username: "your_email@gmail.com"
  password: "your_app_password"
```

**`~/.ginkgo/config.yaml`** (系统配置):
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

## Phase 1: 初始化数据库

### 1.1 启用调试模式（必需）

```bash
ginkgo system config set --debug on
```

**注意**: 所有数据库操作必须先启用调试模式。

### 1.2 初始化 MySQL 和 MongoDB

```bash
# 初始化所有数据库（包括 MySQL 和 MongoDB）
ginkgo data init
```

**执行内容**:
- 创建 MySQL 数据表（users, user_contacts, user_groups, user_group_mappings）
- 创建 MongoDB 集合（notification_templates, notification_records）
- 创建 MongoDB 索引（唯一索引、TTL 索引）

### 1.3 验证 MongoDB 连接

```bash
# 检查 MongoDB 连接状态
ginkgo mongo status
```

**预期输出**:
```
MongoDB Status:
  Host: localhost:27017
  Database: ginkgo
  Connection: OK
  Collections: 2 (notification_templates, notification_records)
  Indexes: 5
```

---

## Phase 2: 用户管理

### 2.1 创建用户

#### 创建个人用户（Person）

```bash
# 创建个人用户
ginkgo users create \
  --type person \
  --name "张三" \
  --active
```

#### 创建 Discord 频道用户（Channel）

```bash
# 创建 Discord 频道用户
ginkgo users create \
  --type channel \
  --name "交易信号频道" \
  --active
```

**Python API**:
```python
from ginkgo import services
from ginkgo.data.models import MUser
from ginkgo.data.enums import USER_TYPES

# 获取用户 CRUD
user_crud = services.data.cruds.user()

# 创建个人用户
user = MUser(
    user_type=USER_TYPES.PERSON,
    name="张三",
    is_active=True
)
user_crud.add_user(user)

# 创建 Discord 频道用户
channel = MUser(
    user_type=USER_TYPES.CHANNEL,
    name="交易信号频道",
    is_active=True
)
user_crud.add_user(channel)
```

### 2.2 添加联系方式

#### 添加 Email 联系方式

```bash
# 为用户添加 Email
ginkgo users contacts add \
  --user-id <user_uuid> \
  --type email \
  --value "zhangsan@example.com" \
  --enabled \
  --primary
```

#### 添加 Discord Webhook 联系方式

```bash
# 为频道用户添加 Discord Webhook
ginkgo users contacts add \
  --user-id <channel_uuid> \
  --type discord \
  --value "https://discord.com/api/webhooks/123/abc" \
  --enabled
```

**Python API**:
```python
from ginkgo import services
from ginkgo.data.models import MUserContact
from ginkgo.data.enums import CONTACT_TYPES

# 获取联系方式 CRUD
contact_crud = services.data.cruds.user_contact()

# 添加 Email 联系方式
email_contact = MUserContact(
    user_id=user.uuid,
    contact_type=CONTACT_TYPES.EMAIL,
    contact_value="zhangsan@example.com",
    is_enabled=True,
    is_primary=True
)
contact_crud.add_user_contact(email_contact)

# 添加 Discord Webhook 联系方式
discord_contact = MUserContact(
    user_id=channel.uuid,
    contact_type=CONTACT_TYPES.DISCORD,
    contact_value="https://discord.com/api/webhooks/123/abc",
    is_enabled=True
)
contact_crud.add_user_contact(discord_contact)
```

### 2.3 列出用户和联系方式

```bash
# 列出所有用户
ginkgo users list --page 20

# 列出用户的联系方式
ginkgo users contacts list --user-id <user_uuid>
```

**Python API**:
```python
# 查询用户
users = user_crud.get_users_page_filtered(limit=20)

# 查询用户的联系方式
contacts = contact_crud.get_user_contacts_page_filtered(
    user_id=user.uuid,
    is_enabled=True
)
```

---

## Phase 3: 用户组管理

### 3.1 创建用户组

```bash
# 创建用户组
ginkgo groups create \
  --group-id "trading-team" \
  --name "交易团队" \
  --description "负责日常交易操作的团队" \
  --active
```

**Python API**:
```python
from ginkgo import services
from ginkgo.data.models import MUserGroup

# 获取用户组 CRUD
group_crud = services.data.cruds.user_group()

# 创建用户组
group = MUserGroup(
    group_id="trading-team",
    group_name="交易团队",
    description="负责日常交易操作的团队",
    is_active=True
)
group_crud.add_user_group(group)
```

### 3.2 添加用户到用户组

```bash
# 添加用户到用户组
ginkgo groups add-user \
  --group-id "trading-team" \
  --user-id <user_uuid>
```

**Python API**:
```python
from ginkgo import services
from ginkgo.data.models import MUserGroupMapping

# 获取用户组映射 CRUD
mapping_crud = services.data.cruds.user_group_mapping()

# 添加用户到用户组
mapping = MUserGroupMapping(
    user_id=user.uuid,
    group_id=group.uuid,
    user_name=user.name,
    group_name=group.group_name
)
mapping_crud.add_user_group_mapping(mapping)
```

### 3.3 列出用户组

```bash
# 列出所有用户组
ginkgo groups list --page 20

# 列出用户组的成员
ginkgo groups list-members --group-id "trading-team"
```

---

## Phase 4: 通知模板管理

### 4.1 创建通知模板

#### 创建交易信号模板（Markdown）

```bash
# 创建交易信号模板
ginkgo templates create \
  --template-id "trading_signal_v1" \
  --name "交易信号通知" \
  --type markdown \
  --subject "交易信号: {{ symbol }}" \
  --content "**交易信号**: {{ signal_type }}\n\n**代码**: {{ symbol }}\n**价格**: {{ price }}" \
  --variables '{"signal_type": {"type": "string", "default": "", "description": "信号类型"}, "symbol": {"type": "string", "default": "", "description": "交易代码"}, "price": {"type": "float", "default": 0.0, "description": "价格"}}'
```

#### 创建错误告警模板（Text）

```bash
# 创建错误告警模板
ginkgo templates create \
  --template-id "error_alert_v1" \
  --name "错误告警通知" \
  --type text \
  --subject "[ERROR] 系统告警" \
  --content "系统发生错误: {{ error_message }}\n时间: {{ timestamp }}" \
  --variables '{"error_message": {"type": "string", "default": "", "description": "错误信息"}, "timestamp": {"type": "string", "default": "", "description": "时间戳"}}'
```

**Python API**:
```python
from ginkgo import services
from ginkgo.data.models import MNotificationTemplate
from ginkgo.data.enums import TEMPLATE_TYPES

# 获取模板 CRUD
template_crud = services.data.cruds.notification_template()

# 创建交易信号模板
template = MNotificationTemplate(
    template_id="trading_signal_v1",
    template_name="交易信号通知",
    template_type=TEMPLATE_TYPES.MARKDOWN,
    subject="交易信号: {{ symbol }}",
    content="""**交易信号**: {{ signal_type }}

**代码**: {{ symbol }}
**价格**: {{ price }}
""",
    variables={
        "signal_type": {"type": "string", "default": "", "description": "信号类型"},
        "symbol": {"type": "string", "default": "", "description": "交易代码"},
        "price": {"type": "float", "default": 0.0, "description": "价格"}
    },
    is_active=True
)
template_crud.add_notification_template(template)
```

### 4.2 列出模板

```bash
# 列出所有模板
ginkgo templates list --page 20

# 查看模板详情
ginkgo templates show --template-id "trading_signal_v1"
```

---

## Phase 5: 发送通知

### 5.1 启动通知 Worker

```bash
# 启动通知 Worker（后台运行）
ginkgo worker start --notification --count 2

# 启动单个 Worker（前台运行，用于调试）
ginkgo worker run --notification --debug
```

**Worker 功能**:
- 从 Kafka 消费通知消息
- 根据用户 ID 查询联系方式
- 调用 DiscordChannel 或 EmailChannel 发送通知
- 记录发送结果到 MongoDB

### 5.2 发送简单文本通知

```bash
# 发送文本消息到单个用户
ginkgo notify send \
  --user-id <user_uuid> \
  --message "Hello, World!" \
  --channels discord email
```

**Python API**:
```python
from ginkgo import services

# 获取通知服务
notification_service = services.data.services.notification_service()

# 发送通知
notification_service.send_notification(
    user_ids=[user.uuid],
    content="Hello, World!",
    content_type=TEMPLATE_TYPES.TEXT,
    channels=["discord", "email"]
)
```

### 5.3 使用模板发送通知

```bash
# 使用模板发送通知
ginkgo notify send \
  --user-id <user_uuid> \
  --template "trading_signal_v1" \
  --var signal_type="买入" \
  --var symbol="AAPL" \
  --var price="150.0" \
  --channels discord
```

**Python API**:
```python
from ginkgo import services

# 获取通知服务
notification_service = services.data.services.notification_service()

# 使用模板发送通知
notification_service.send_notification_by_template(
    user_ids=[user.uuid],
    template_id="trading_signal_v1",
    template_variables={
        "signal_type": "买入",
        "symbol": "AAPL",
        "price": 150.0
    },
    channels=["discord"]
)
```

### 5.4 发送到用户组

```bash
# 发送通知到用户组
ginkgo notify send \
  --group-id "trading-team" \
  --message "交易会议将在10分钟后开始" \
  --channels discord
```

**Python API**:
```python
from ginkgo import services

# 获取用户组 CRUD
group_crud = services.data.cruds.user_group()

# 获取用户组成员
group = group_crud.get_user_group_by_id("trading-team")
mappings = group_crud.get_mappings_by_group_id(group.uuid)
user_ids = [m.user_id for m in mappings]

# 发送通知到用户组
notification_service.send_notification(
    user_ids=user_ids,
    content="交易会议将在10分钟后开始",
    content_type=TEMPLATE_TYPES.TEXT,
    channels=["discord"]
)
```

---

## Phase 6: 查询通知记录

### 6.1 查询用户的通知记录

```bash
# 查询用户最近的通知记录
ginkgo notify list --user-id <user_uuid> --limit 50

# 查询所有通知记录
ginkgo notify list --limit 100
```

**Python API**:
```python
from ginkgo import services

# 获取通知记录 CRUD
record_crud = services.data.cruds.notification_record()

# 查询用户的通知记录
records = record_crud.get_records_page_filtered(
    user_id=user.uuid,
    limit=50
)

# 查询所有通知记录
all_records = record_crud.get_records_page_filtered(limit=100)
```

### 6.2 查看通知详情

```bash
# 查看通知详情
ginkgo notify show --message-id "msg_20251231_001"
```

**Python API**:
```python
# 获取单条通知记录
record = record_crud.get_record_by_message_id("msg_20251231_001")

# 打印发送结果
for result in record.channel_results:
    print(f"渠道: {result.channel}")
    print(f"状态: {result.status}")
    print(f"重试次数: {result.retry_count}")
    if result.error_message:
        print(f"错误: {result.error_message}")
```

---

## Phase 7: 清理和调试

### 7.1 禁用调试模式（完成后）

```bash
# 数据库操作完成后，禁用调试模式
ginkgo system config set --debug off
```

### 7.2 查看 Worker 状态

```bash
# 查看 Worker 进程状态
ginkgo worker status
```

**预期输出**:
```
Worker Status:
┌─────────┬───────────────┬──────────┬────────────┐
│ PID     │ Type          │ Status   │ Uptime     │
├─────────┼───────────────┼──────────┼────────────┤
│ 12345   │ Notification  │ Running  │ 00:15:30   │
│ 12346   │ Notification  │ Running  │ 00:15:30   │
└─────────┴───────────────┴──────────┴────────────┘
```

### 7.3 查看 Kafka Topic

```bash
# 查看 Kafka Topic 列表
kafka-topics.sh --list --bootstrap-server localhost:9092

# 查看 Topic 消息
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic notifications-discord \
  --from-beginning
```

### 7.4 查看 MongoDB 数据

```bash
# 连接到 MongoDB
mongo ginkgo

# 查看通知模板
db.notification_templates.find().pretty()

# 查看通知记录
db.notification_records.find().pretty()

# 查看通知记录统计
db.notification_records.count()
db.notification_records.aggregate([
  { $group: { _id: "$status", count: { $sum: 1 } } }
])
```

---

## 完整示例流程

### 场景：交易信号通知系统

```bash
# 1. 初始化数据库
ginkgo system config set --debug on
ginkgo data init

# 2. 创建交易团队用户组
ginkgo groups create \
  --group-id "trading-team" \
  --name "交易团队" \
  --active

# 3. 创建交易员用户
USER_UUID=$(ginkgo users create --type person --name "交易员A" --active)

# 4. 添加联系方式（Discord 和 Email）
ginkgo users contacts add \
  --user-id $USER_UUID \
  --type discord \
  --value "https://discord.com/api/webhooks/123/abc" \
  --enabled

ginkgo users contacts add \
  --user-id $USER_UUID \
  --type email \
  --value "trader@example.com" \
  --enabled

# 5. 将用户添加到交易团队
ginkgo groups add-user --group-id "trading-team" --user-id $USER_UUID

# 6. 创建交易信号模板
ginkgo templates create \
  --template-id "trading_signal" \
  --name "交易信号通知" \
  --type markdown \
  --content "**交易信号**: {{ signal_type }}\n\n**代码**: {{ symbol }}\n**价格**: {{ price }}" \
  --variables '{"signal_type": {"type": "string"}, "symbol": {"type": "string"}, "price": {"type": "float"}}'

# 7. 启动通知 Worker
ginkgo worker start --notification --count 2

# 8. 发送交易信号通知
ginkgo notify send \
  --user-id $USER_UUID \
  --template "trading_signal" \
  --var signal_type="买入" \
  --var symbol="AAPL" \
  --var price="150.0" \
  --channels discord email

# 9. 查询通知记录
ginkgo notify list --user-id $USER_UUID --limit 10

# 10. 清理
ginkgo system config set --debug off
```

---

## 常见问题排查

### Q1: MongoDB 连接失败

**症状**: `ginkgo mongo status` 显示连接失败

**解决方案**:
```bash
# 检查 MongoDB 服务状态
sudo systemctl status mongodb

# 启动 MongoDB
sudo systemctl start mongodb

# 检查端口占用
sudo netstat -tlnp | grep 27017
```

### Q2: Kafka Worker 不消费消息

**症状**: Worker 启动但不处理通知

**解决方案**:
```bash
# 检查 Kafka 服务状态
jps | grep Kafka

# 检查 Topic 是否创建
kafka-topics.sh --list --bootstrap-server localhost:9092

# 手动创建 Topic
kafka-topics.sh \
  --create \
  --bootstrap-server localhost:9092 \
  --topic notifications-discord \
  --partitions 3 \
  --replication-factor 1
```

### Q3: Discord Webhook 返回 404

**症状**: 通知记录显示 `FAILED: Webhook 返回 404`

**解决方案**:
- 检查 Webhook URL 是否正确
- 确认 Discord 频道存在且 Webhook 未被删除
- 使用 `curl` 测试 Webhook:
  ```bash
  curl -X POST \
    -H "Content-Type: application/json" \
    -d '{"content": "测试消息"}' \
    <your_webhook_url>
  ```

### Q4: Email 发送失败

**症状**: 通知记录显示 `FAILED: SMTP 连接超时`

**解决方案**:
- 检查 SMTP 配置是否正确
- 确认邮箱是否开启了"应用专用密码"（Gmail 需要启用）
- 使用 `telnet` 测试 SMTP 连接:
  ```bash
  telnet smtp.gmail.com 587
  ```

---

**Quickstart 完成**: 本文档提供了 MongoDB 基础设施与通知系统的快速开始指南，涵盖环境准备、数据库初始化、用户管理、模板管理、通知发送和常见问题排查。
