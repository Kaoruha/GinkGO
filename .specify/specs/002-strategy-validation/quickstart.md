# Quick Start: Strategy Validation Module

**Feature**: 002-strategy-validation
**Target Audience**: 策略开发者
**Time to Complete**: 5 分钟

---

## 目标

除了运行完整回测，提供快速评估策略的方法，并直观确认信号生成是否符合预期。

---

## 安装

```bash
# 评估 Ginkgo 已安装
ginkgo version

# 确认评估模块可用
ginkgo validate --help
```

---

## 1. 快速代码评估（< 2 秒）

### 场景：刚写完策略，想快速检查是否有明显错误

```bash
# 基本评估（检查结构、逻辑和最佳实践）
ginkgo validate my_strategy.py

# 指定组件类型（策略、选择器、sizer、风控管理器）
ginkgo validate my_strategy.py --type strategy
ginkgo validate my_selector.py --type selector

# 从数据库验证
ginkgo validate --file-id <uuid> --type strategy
```

**预期输出**：
```
╭──────────────────────────────────────────────────────────╮
│           Component Validation Report                    │
╰──────────────────────────────────────────────────────────╯

File: my_strategy.py
Component: strategy
Result: ✅ PASSED

Status: PASSED
Duration: 1.23s
```

---

## 2. 信号生成追踪（< 5 秒）

### 场景：想知道策略在特定数据下会生成什么信号

**步骤 1：准备测试数据**

确保数据库中有历史数据：
```bash
# 更新股票数据
ginkgo system config set --debug on
ginkgo data update day --code 000001.SZ --start 2023-01-01 --end 2023-01-31
```

**步骤 2：运行信号追踪**

```bash
# 评估 + 显示信号追踪（使用数据库数据）
ginkgo validate my_strategy.py --show-trace --code 000001.SZ --events 100

# 追踪更多事件
ginkgo validate my_strategy.py --show-trace --code 000001.SZ --events 1000
```

**预期输出**：
```
╭──────────────────────────────────────────────────────────╮
│           Component Validation Report                    │
╰──────────────────────────────────────────────────────────╯

File: my_strategy.py
Component: strategy
Result: ✅ PASSED

╭──────────────────────────────────────────────────────────╮
│           Signal Trace Report                            │
╰──────────────────────────────────────────────────────────╯

Strategy: MyStrategy
Events Processed: 100
Signals Generated: 2 (1 buy, 1 sell)

Signals:
  📍 LONG 000001.SZ @ 10.70 on 2023-01-05
     Reason: 均线金叉
     Context: close=10.70, ma5=10.65

  📍 SHORT 000001.SZ @ 10.90 on 2023-01-15
     Reason: 均线死叉
     Context: close=10.90, ma5=10.82

Status: COMPLETED
Duration: 0.15s
```

**关键信息**：
- 信号数量是否符合预期？
- 信号方向（LONG/SHORT）是否正确？
- 信号原因（reason）是否描述准确？
- 上下文（context）数据是否合理？

---

## 3. 可视化信号（< 10 秒）

### 场景：直观查看信号在图表上的位置

```bash
# 生成交互式图表（HTML）
ginkgo validate my_strategy.py --visualize --code 000001.SZ --events 100

# 指定输出文件
ginkgo validate my_strategy.py --visualize --output signals.html --code 000001.SZ
```

**预期结果**：

打开生成的 HTML 文件，您将看到：
- K线图（蜡烛图）
- 买入信号标记为绿色向上箭头
- 卖出信号标记为红色向下箭头
- 信号位置与价格走势一目了然

**评估要点**：
- ✅ 买入信号是否出现在低点？
- ✅ 卖出信号是否出现在高点？
- ✅ 信号数量是否合理（不过多也不过少）？
- ✅ 是否有明显的"漏掉"的机会？

---

## 4. 完整工作流示例

### 场景：从零开发一个策略

```bash
# 1. 创建策略文件
cat > my_strategy.py << 'EOF'
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def __init__(self, name="MyStrategy", fast=5, slow=10, **kwargs):
        super().__init__(name=name, **kwargs)
        self.fast_period = fast
        self.slow_period = slow

    def cal(self, portfolio_info, event, *args, **kwargs):
        # 策略逻辑...
        return []
EOF

# 2. 静态评估
ginkgo validate my_strategy.py

# 3. 准备测试数据（使用历史数据）
ginkgo system config set --debug on
ginkgo data update day --code 000001.SZ --start 2023-01-01 --end 2023-01-31

# 4. 运行信号追踪
ginkgo validate my_strategy.py --show-trace --code 000001.SZ --events 100

# 5. 生成可视化
ginkgo validate my_strategy.py --visualize --code 000001.SZ --output my_strategy_signals.html

# 6. 查看可视化
open my_strategy_signals.html
```

---

## 5. 组合使用（一次性完成所有检查）

```bash
# 评估 + 追踪 + 可视化（一次性）
ginkgo validate my_strategy.py \
    --show-trace \
    --visualize \
    --output report.html \
    --code 000001.SZ \
    --events 100
```

**输出**：
1. 终端显示：评估报告 + 信号追踪详情
2. 文件输出：`report.html` 可视化图表

---

## 6. 常见问题排查

### 问题 1：评估失败

```bash
$ ginkgo validate my_strategy.py
❌ FAILED (2 errors, 1 warning)

Errors:
  ✗ Line 15: 缺少必需的 cal() 方法
  ⚠ Line 8: 建议使用 @time_logger 装饰器
```

**解决方案**：
- 按照错误提示修改代码
- 重新评估直到通过

### 问题 2：没有生成信号

```bash
$ ginkgo validate my_strategy.py --show-trace --code 000001.SZ
Signals Generated: 0
```

**可能原因**：
1. 策略条件过于严格
2. 测试数据时间范围太短
3. 策略逻辑有 bug

**调试方法**：
```bash
# 增加 --verbose 查看详细上下文
ginkgo validate my_strategy.py --show-trace --code 000001.SZ --verbose --events 1000

# 检查数据库中是否有数据
ginkgo data list bar --code 000001.SZ
```

### 问题 3：信号不符合预期

**场景**：期望在低点买入，但实际在高点买入

**解决方案**：
1. 查看追踪报告中的 `Context` 字段
2. 检查策略逻辑是否正确使用了数据
3. 对比可视化图表，确认信号位置

```bash
# 查看详细追踪报告（JSON格式）
ginkgo validate my_strategy.py --show-trace --format json --output trace.json --code 000001.SZ
cat trace.json

# 生成可视化对比
ginkgo validate my_strategy.py --visualize --output debug.html --code 000001.SZ
```

---

## 7. CI/CD 集成

### 场景：在提交代码前自动评估

**创建 `.github/workflows/validate.yml`**：

```yaml
name: Validate Strategy

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install Ginkgo
        run: |
          pip install ginkgo

      - name: Validate Strategy
        run: |
          ginkgo validate strategies/my_strategy.py \
            --format json \
            --output validation.json

      - name: Check Result
        run: |
          if ! grep -q '"passed": true' validation.json; then
            echo "❌ 策略评估失败"
            cat validation.json
            exit 1
          fi
          echo "✅ 策略评估通过"
```

---

## 8. 性能对比

| 方法 | 时间 | 需要数据 | 提供信息 |
|------|------|----------|----------|
| **静态评估** | ~1 秒 | ❌ 不需要 | 结构错误、逻辑问题 |
| **信号追踪** | ~2 秒 | ✅ 需要（数据库） | 信号列表、生成原因 |
| **可视化** | ~3 秒 | ✅ 需要（数据库） | 图表 + 信号位置 |
| **完整回测** | ~30 秒 | ✅ 需要 | 收益、最大回撤等 |

**结论**：
- 静态评估：**100 倍快于回测**
- 信号追踪：**15 倍快于回测**
- 可视化：**10 倍快于回测**

---

## 9. 数据库验证

### 从数据库加载和验证组件

```bash
# 列出数据库中所有组件
ginkgo component list

# 列出特定类型的组件
ginkgo component list --type strategy
ginkgo component list --type selector

# 按名称过滤
ginkgo component list --filter trend

# JSON 格式输出
ginkgo component list --raw

# 验证数据库中的组件
ginkgo validate --file-id <uuid>

# 验证所有策略
ginkgo validate --all --type strategy

# 验证并过滤
ginkgo validate --all --filter trend
```

---

## 10. 下一步

- 📖 阅读完整文档：[spec.md](./spec.md)
- 🔧 查看技术设计：[research.md](./research.md)
- 📊 了解数据模型：[data-model.md](./data-model.md)
- 💻 查看 CLI 参考：[contracts/cli_interface.md](./contracts/cli_interface.md)

---

## 11. 反馈与支持

遇到问题？请：
1. 检查本文档的"常见问题排查"部分
2. 使用 `--verbose` 参数获取更多调试信息
3. 在 GitHub Issues 中报告问题

---

**Quick Start Status**: ✅ **COMPLETE** - 提供完整的使用指南，包括：
- ✅ 快速代码评估
- ✅ 信号生成追踪（基于数据库）
- ✅ 可视化检查
- ✅ 完整工作流
- ✅ 常见问题排查
- ✅ CI/CD 集成示例
- ✅ 数据库验证支持
