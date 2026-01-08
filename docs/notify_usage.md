# 全局notify函数使用指南

## 简介

`notify()` 是一个**基于模板**的全局通知函数，可以在代码任何地方直接调用，自动发送系统通知到Discord。

## 导入

```python
from ginkgo.notifier.core.notification_service import notify
```

## 模板系统说明

notify函数基于Jinja2模板系统，支持：
- ✅ **默认模板** - `system_alert`（系统告警模板）
- ✅ **自定义模板** - 通过`template_id`参数指定
- ✅ **灵活变量** - `details`和`**template_vars`两种方式传递变量
- ✅ **字段前缀** - `details`自动转换为`field_*`变量

## 基本用法

### 1. 使用默认模板（system_alert）

默认模板变量：
- `{{ message }}` - 通知内容
- `{{ severity }}` - 级别（INFO/WARNING/ERROR/CRITICAL）
- `{{ module }}` - 模块名称
- `{{ timestamp }}` - 时间戳
- `{{ field_* }}` - 详细字段（从details转换）

```python
# 最简单的用法
notify("任务完成")

# 指定级别
notify("系统警告", level="WARNING")

# 带详细信息（转换为field_*变量）
notify(
    "K线数据更新完成",
    level="INFO",
    details={
        "代码": "000001.SZ",
        "记录数": "5000"
    },
    module="DataManager"
)
# → {{ field_代码 }} = "000001.SZ"
# → {{ field_记录数 }} = "5000"
```

### 2. 使用自定义模板

假设有一个交易信号模板`trading_signal`：
```json
{
  "title": "📈 交易信号 - {{ direction }}",
  "description": "{{ message }}",
  "color": 3066993,
  "fields": [
    {"name": "方向", "value": "{{ direction }}"},
    {"name": "代码", "value": "{{ code }}"},
    {"name": "价格", "value": "{{ price }}"},
    {"name": "数量", "value": "{{ volume }}"}
  ]
}
```

使用方式：
```python
notify(
    "双均线策略触发金叉",
    template_id="trading_signal",
    direction="LONG",
    code="000001.SZ",
    price=15.50,
    volume=1000,
    module="Strategy"
)
```

### 3. 混合使用details和template_vars

```python
notify(
    "订单成交通知",
    template_id="order_filled",
    details={
        "策略": "双均线",
        "时间": "2026-01-08 10:30:00"
    },
    order_id="12345",
    symbol="AAPL",
    quantity=100,
    price=150.25
)
# 可用变量：
# {{ field_策略 }}, {{ field_时间 }}
# {{ order_id }}, {{ symbol }}, {{ quantity }}, {{ price }}
```

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| content | str | ✅ | - | 通知内容（对应 {{ message }}） |
| level | str | ❌ | "INFO" | 级别（对应 {{ severity }}） |
| details | dict | ❌ | None | 详细信息，转换为 {{ field_* }} |
| module | str | ❌ | "System" | 模块名（对应 {{ module }}） |
| template_id | str | ❌ | "system_alert" | 模板ID |
| **template_vars | - | ❌ | - | 自定义模板变量（直接传递） |

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

### 2. 策略信号通知

假设创建了`strategy_signal`模板：
```python
class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        signals = self.generate_signals(event)

        for signal in signals:
            # 使用自定义模板发送信号
            notify(
                f"{self.__class__.__name__} 生成{signal.direction}信号",
                template_id="strategy_signal",
                direction=signal.direction,
                code=signal.code,
                price=signal.price,
                reason=signal.reason,
                strategy=self.__class__.__name__,
                level="INFO"
            )

        return signals
```

### 3. 订单执行通知

```python
def on_order_filled(self, order):
    notify(
        "订单成交",
        template_id="order_filled",
        order_id=order.uuid,
        symbol=order.code,
        side=order.direction,
        quantity=order.volume,
        price=order.price,
        details={
            "策略": order.strategy_id,
            "时间": datetime.now().strftime("%H:%M:%S")
        },
        level="INFO"
    )
```

### 4. 风控警告

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

## 模板变量规则

### details参数（自动添加field_前缀）

```python
notify("...", details={"代码": "000001", "价格": "15.50"})
# 模板中可用：{{ field_代码 }} 和 {{ field_价格 }}
```

### **template_vars（直接使用变量名）

```python
notify("...", code="000001", price=15.50)
# 模板中可用：{{ code }} 和 {{ price }}
```

### 预定义变量（自动提供）

- `{{ message }}` - content参数
- `{{ severity }}` - level参数
- `{{ module }}` - module参数
- `{{ timestamp }}` - 当前时间（默认模板）
- `{{ alert_type }}` - 等同于severity（默认模板）

## 完整示例：创建自定义模板

### 步骤1：创建模板

使用CLI创建模板：
```bash
ginkgo notify template create \
  --id "data_update" \
  --name "数据更新通知" \
  --type "embedded" \
  --content '{
    "title": "🔄 数据更新 - {{ field_数据源 }}",
    "description": "{{ message }}",
    "color": 3447003,
    "fields": [
      {"name": "数据源", "value": "{{ field_数据源 }}"},
      {"name": "代码", "value": "{{ field_代码 }}"},
      {"name": "记录数", "value": "{{ field_记录数 }}"},
      {"name": "耗时", "value": "{{ field_耗时 }}"},
      {"name": "模块", "value": "{{ module }}", "inline": true},
      {"name": "时间", "value": "{{ timestamp }}", "inline": true}
    ]
  }'
```

### 步骤2：使用模板

```python
from ginkgo.notifier.core.notification_service import notify

def sync_data():
    result = fetch_data()

    notify(
        "数据同步完成",
        template_id="data_update",
        details={
            "数据源": "Tushare",
            "代码": "000001.SZ",
            "记录数": "5000",
            "耗时": "120秒"
        },
        module="DataManager"
    )
```

## 最佳实践

### 1. 选择合适的级别

```python
# INFO - 正常信息
notify("任务完成", level="INFO")

# WARNING - 警告但不影响运行
notify("内存使用率80%", level="WARNING")

# ERROR - 错误但可恢复
notify("API请求失败，已重试", level="ERROR")

# CRITICAL - 严重错误，需要立即处理
notify("数据库连接断开", level="CRITICAL")
```

### 2. 合理使用details

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

### 3. 模块命名规范

```python
# 使用有意义的模块名
module="DataSync"      # ✅ 好
module="TradingEngine" # ✅ 好
module="sys"           # ❌ 太简短
module="system"        # ❌ 太通用
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
            template_id="order_filled",
            order_id=order.uuid,
            symbol=order.code,
            quantity=order.volume,
            price=order.price,
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
                "订单ID": order.uuid,
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
5. **模板验证** - 使用自定义模板前，确保模板已创建并测试过

