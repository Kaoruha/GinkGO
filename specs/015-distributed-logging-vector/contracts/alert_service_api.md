# API Contract: AlertService

**Service**: AlertService - 日志告警服务
**Version**: 1.0.0
**Date**: 2026-03-10

## Overview

AlertService 是日志告警服务，基于 ClickHouse 查询的告警规则配置，支持多种告警渠道（钉钉、企业微信、邮件），实现告警抑制机制防止告警风暴。

---

## API Methods

### 1. add_alert_rule

添加告警规则。

**Signature**:
```python
def add_alert_rule(
    rule_name: str,
    pattern: str,
    threshold: int,
    time_window: int,
    alert_channel: str
) -> bool:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| rule_name | str | 是 | 规则名称（唯一标识） |
| pattern | str | 是 | 错误模式（关键词或正则表达式） |
| threshold | int | 是 | 频率阈值（次数） |
| time_window | int | 是 | 时间窗口（分钟） |
| alert_channel | str | 是 | 告警渠道（dingtalk/wechat/email） |

**Returns**:
```python
bool  # 添加成功返回 True
```

**Example**:
```python
# 添加错误日志告警规则：5分钟内ERROR超过10次
alert_service.add_alert_rule(
    rule_name="high_error_rate",
    pattern="ERROR",
    threshold=10,
    time_window=5,
    alert_channel="dingtalk"
)
```

---

### 2. remove_alert_rule

移除告警规则。

**Signature**:
```python
def remove_alert_rule(rule_name: str) -> bool:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| rule_name | str | 是 | 规则名称 |

**Returns**:
```python
bool  # 移除成功返回 True
```

---

### 3. check_error_patterns

检查错误模式是否触发告警。

**Signature**:
```python
def check_error_patterns() -> List[Dict[str, Any]]:
```

**Returns**:
```python
List[Dict[str, Any]]  # 触发的告警列表
```

**Example**:
```python
# 定期检查告警规则（如每分钟执行一次）
alerts = alert_service.check_error_patterns()
for alert in alerts:
    alert_service.send_alert(alert)
```

---

### 4. send_alert

发送告警通知。

**Signature**:
```python
def send_alert(
    alert_message: str,
    alert_channel: str
) -> bool:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| alert_message | str | 是 | 告警消息内容 |
| alert_channel | str | 是 | 告警渠道（dingtalk/wechat/email） |

**Returns**:
```python
bool  # 发送成功返回 True
```

**告警抑制机制**: 相同错误模式 5 分钟内只发送一次告警

---

### 5. get_alert_rules

获取所有告警规则。

**Signature**:
```python
def get_alert_rules() -> List[Dict[str, Any]]:
```

**Returns**:
```python
List[Dict[str, Any]]  # 告警规则列表
```

---

## 告警规则配置

### 规则类型

1. **频率告警**: 在指定时间窗口内，错误次数超过阈值
2. **关键词告警**: 日志包含特定关键词时立即告警

### 规则示例

```python
# 规则 1: ERROR 日志频率告警
{
    "rule_name": "high_error_rate",
    "pattern": "ERROR",
    "threshold": 10,
    "time_window": 5,
    "alert_channel": "dingtalk"
}

# 规则 2: 数据库连接失败关键词告警
{
    "rule_name": "database_connection_failed",
    "pattern": "数据库连接失败",
    "threshold": 1,
    "time_window": 1,
    "alert_channel": "wechat"
}

# 规则 3: CRITICAL 日志告警
{
    "rule_name": "critical_error",
    "pattern": "CRITICAL",
    "threshold": 1,
    "time_window": 1,
    "alert_channel": "email"
}
```

---

## 告警渠道配置

### 钉钉 Webhook

**GCONF 配置**:
```yaml
logging:
  alerts:
    dingtalk:
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
      secret: "SECxxx"
      at_mobiles: ["13800138000"]
      at_all: false
```

---

### 企业微信 Webhook

**GCONF 配置**:
```yaml
logging:
  alerts:
    wechat:
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
      mentioned_list: ["@all"]
```

---

### 邮件 SMTP

**GCONF 配置**:
```yaml
logging:
  alerts:
    email:
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      smtp_user: "alert@ginkgo.com"
      smtp_password: "xxx"
      from_addr: "alert@ginkgo.com"
      to_addrs: ["admin@ginkgo.com", "ops@ginkgo.com"]
```

---

## 告警消息格式

### 钉钉消息格式

```json
{
    "msgtype": "markdown",
    "markdown": {
        "title": "Ginkgo 日志告警",
        "text": "## Ginkgo 日志告警\n\n**告警规则**: high_error_rate\n\n**触发条件**: 5分钟内ERROR超过10次\n\n**时间**: 2026-03-10 12:00:00\n\n**查询日志**: [点击查看](http://logs.ginkgo.com)"
    }
}
```

---

### 企业微信消息格式

```json
{
    "msgtype": "markdown",
    "markdown": {
        "content": "## Ginkgo 日志告警\n\n**告警规则**: high_error_rate\n\n**触发条件**: 5分钟内ERROR超过10次\n\n**时间**: 2026-03-10 12:00:00"
    }
}
```

---

### 邮件消息格式

```
Subject: [Ginkgo 日志告警] high_error_rate

告警规则: high_error_rate
触发条件: 5分钟内ERROR超过10次
时间: 2026-03-10 12:00:00

查看日志: http://logs.ginkgo.com

---
Ginkgo 量化交易系统
```

---

## 告警抑制机制

### 实现方式

使用 Redis 存储告警发送记录，TTL 设置为 5 分钟。

```python
def should_send_alert(rule_name: str) -> bool:
    """检查是否应该发送告警"""
    key = f"alert:{rule_name}"
    if redis_client.exists(key):
        return False
    redis_client.setex(key, 300, "1")  # 5分钟TTL
    return True
```

---

## 错误处理

告警发送失败时记录错误日志，不影响应用运行。

```python
def send_alert(self, alert_message: str, alert_channel: str) -> bool:
    try:
        # 发送告警
        self._do_send_alert(alert_message, alert_channel)
        return True
    except Exception as e:
        GLOG.error(f"告警发送失败: {e}", exc_info=True)
        return False
```

---

## 性能要求

- 告警规则触发后通知发送延迟 < 10 秒
- 告警抑制准确率 100%（5分钟内同类告警只发送一次）
- 告警发送失败不影响应用运行
