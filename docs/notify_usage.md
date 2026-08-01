# 全局notify函数使用指南

## 简介

`notify()` 是一个简化版的全局通知函数，可以在代码任何地方直接调用，自动发送系统通知到Discord。支持同步和异步两种模式。

## 导入

```python
from ginkgo.notifier.core.notification_service import notify
```

## 模板系统说明

> **重要**：顶层 `notify()` 函数**不支持**模板参数（如 `template_id`）。如需模板渲染，请使用 `NotificationService` 类方法或 CLI。

### 类级模板 API

模板系统真实存在于 `NotificationService` 类中：
- `render_from_template_id(template_id: str, **variables)` - 渲染模板预览
- `send_template(template_id, target, **variables)` - 发送模板通知
- `preview_template(template_id)` - 预览模板内容

```python
from ginkgo.notifier.core.notification_service import NotificationService

# 类级使用示例
service = NotificationService()
service.send_template(
    template_id="trading_signal",
    target="user_uuid_or_group_id",
    direction="LONG",
    code="000001.SZ",
    price=15.50
)
```

### CLI 模板管理

```bash
# 列出所有模板
ginkgo notify template list

# 创建自定义模板
ginkgo notify template create --id "my_template" --name "我的模板" --content '{...}'

# 预览模板
ginkgo notify template preview my_template
```

## 基本用法

### 1. 简单通知

```python
# 最简单的用法（异步发送，默认不阻塞）
notify("任务完成")

# 指定级别
notify("系统警告", level="WARNING")

# 带详细信息
notify(
    "K线数据更新完成",
    level="INFO",
    details={
        "代码": "000001.SZ",
        "记录数": "5000"
    },
    module="DataManager"
)
```

### 2. 同步模式

```python
# 异步发送（默认，不阻塞）
notify("任务完成", async_mode=True)

# 同步发送（阻塞，等待结果）
notify("系统警告", level="WARN", async_mode=False)
```

### 3. 错误通知

```python
notify("连接失败", level="ERROR", details={"重试": "3次"})
```

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| content | str | ✅ | - | 通知内容 |
| level | str | ❌ | "INFO" | 等级（INFO/WARN/ERROR/SUCCESS/ALERT） |
| details | dict | ❌ | None | 详细信息字典 |
| module | str | ❌ | "System" | 模块名称 |
| async_mode | bool | ❌ | True | 异步模式（True=经Kafka Worker，False=同步阻塞） |

**注意**：无 `template_id` 参数，无 `**template_vars` 参数。模板功能请使用 `NotificationService` 类。

## 返回值

- `True`: 发送成功
- `False`: 发送失败

## 实际应用示例

### 1. 数据管理通知

```python
class DataSync:
    def sync_stock_data(self, code: str):
        try:
            count = self.fetch_data(code)

            notify(
                f"数据同步完成",
                level="INFO",
                details={
                    "代码": code,
                    "记录数": str(count),
                    "耗时": f"{self.elapsed_time:.2f}秒"
                },
                module="DataSync"
            )

        except Exception as e:
            notify(
                f"数据同步失败: {str(e)}",
                level="ERROR",
                details={"代码": code, "错误": type(e).__name__},
                module="DataSync"
            )
```

### 2. 风控警告

```python
class RiskMonitor:
    def check_position_limit(self, portfolio):
        if portfolio.position_ratio > 0.9:
            notify(
                f"仓位接近上限",
                level="WARNING",
                details={
                    "当前仓位": f"{portfolio.position_ratio*100:.1f}%",
                    "上限": "90%",
                    "建议": "降低仓位"
                },
                module="RiskControl"
            )
```

### 3. 订单执行通知（使用类级模板）

> 以下示例使用 `NotificationService` 类的模板功能，非顶层 `notify()` 函数。

```python
from ginkgo.notifier.core.notification_service import NotificationService

def on_order_filled(self, order):
    service = NotificationService()
    service.send_template(
        template_id="order_filled",
        target="system_group_id",  # 或具体用户 UUID
        order_id=order.uuid,
        symbol=order.code,
        side=order.direction,
        quantity=order.volume,
        price=order.price
    )
```

## 级别选择建议

```python
# INFO - 正常信息
notify("任务完成", level="INFO")

# WARNING - 警告但不影响运行
notify("内存使用率80%", level="WARNING")

# ERROR - 错误但可恢复
notify("API请求失败，已重试", level="ERROR")

# ALERT - 告警，需要关注
notify("数据库连接断开", level="ALERT")

# SUCCESS - 操作成功
notify("配置已更新", level="SUCCESS")
```

## 异步模式说明

```python
# 默认异步模式（推荐用于大多数场景）
notify("数据更新完成", async_mode=True)
# → 通过 Kafka Worker 异步发送，不阻塞业务流程

# 同步模式（用于需要确认发送结果的场景）
notify("关键错误", async_mode=False)
# → 同步发送，阻塞直到发送完成或失败
```

## 与GLOG配合

```python
from ginkgo.libs import GLOG
from ginkgo.notifier.core.notification_service import notify

def process_order(order):
    GLOG.info(f"Processing order: {order.uuid}")

    try:
        # 处理订单
        result = execute_order(order)

        # 记录日志
        GLOG.info(f"Order executed: {order.uuid}")

        # 重要事件发送通知
        notify(
            "订单成交",
            details={
                "订单ID": str(order.uuid),
                "代码": order.code,
                "数量": str(order.volume)
            },
            level="INFO"
        )

        return result

    except Exception as e:
        # 记录错误
        GLOG.ERROR(f"Order failed: {e}")

        # 发送错误通知
        notify(
            f"订单执行失败",
            level="ERROR",
            details={
                "订单ID": str(order.uuid),
                "错误": str(e)
            },
            module="OrderExecution"
        )

        raise
```

## 注意事项

1. **自动发送到System组** - 不需要指定接收者
2. **线程安全** - 可以在多线程环境中使用
3. **异常安全** - 函数内部已处理异常，不会抛出异常影响业务
4. **单例模式** - 使用单例模式，第一次调用时会初始化服务
5. **异步默认** - 默认 `async_mode=True`，经 Kafka Worker 异步发送
6. **模板功能** - 如需自定义模板，使用 `NotificationService` 类或 CLI

## 完整示例：类级模板创建与使用

### 步骤1：创建模板（CLI）

```bash
ginkgo notify template create \
  --id "trading_signal" \
  --name "交易信号通知" \
  --type "embedded" \
  --content '{
    "title": "📈 交易信号 - {{ direction }}",
    "description": "{{ message }}",
    "color": 3066993,
    "fields": [
      {"name": "方向", "value": "{{ direction }}"},
      {"name": "代码", "value": "{{ code }}"},
      {"name": "价格", "value": "{{ price }}"},
      {"name": "数量", "value": "{{ volume }}"}
    ]
  }'
```

### 步骤2：使用模板（Python - 类级）

```python
from ginkgo.notifier.core.notification_service import NotificationService

class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        signals = self.generate_signals(event)
        service = NotificationService()

        for signal in signals:
            # 使用类级模板 API 发送信号
            service.send_template(
                template_id="trading_signal",
                target="system",  # 发送到系统组
                direction=signal.direction,
                code=signal.code,
                price=signal.price,
                volume=signal.volume
            )

        return signals
```

## 最佳实践

### 1. 合理使用 details

```python
# ✅ 好的details：结构化、简洁
notify("数据更新", details={
    "代码": "000001.SZ",
    "记录数": "5000",
    "状态": "成功"
})

# ❌ 不好的details：太长、无结构
notify("数据更新", details={
    "详细信息": "从Tushare获取了000001.SZ的数据，一共5000条记录，耗时2分钟..."
})
```

### 2. 模块命名规范

```python
# 使用有意义的模块名
module="DataSync"      # ✅ 好
module="TradingEngine" # ✅ 好
module="sys"           # ❌ 太简短
module="system"        # ❌ 太通用
```

### 3. 异步 vs 同步

```python
# 大多数场景：异步（默认）
notify("数据更新完成", async_mode=True)

# 关键错误：同步确认
notify("数据库连接失败", async_mode=False)
```
