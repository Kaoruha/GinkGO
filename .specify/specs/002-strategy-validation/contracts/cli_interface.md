# CLI Interface: Strategy Validation Module

**Feature**: 002-strategy-validation
**Date**: 2025-12-27
**Version**: 3.0.0

## 命令概览

```bash
# 统一评估命令
ginkgo eval strategy [SOURCE] [OPTIONS]
```

**策略来源**（三选一）：
- `strategy_file` - 本地文件路径（.py 文件）
- `--file-id <uuid>` - 数据库策略文件 ID（MFile.uuid）
- `--portfolio-id <uuid>` - 评估 Portfolio 绑定的策略
- `--list` - 列出数据库中所有策略
- `--all` - 批量评估所有数据库策略

通过输出参数控制显示模式：
- 默认：仅显示静态评估结果
- `--show-trace`：显示信号追踪
- `--visualize`：生成可视化图表

---

## 命令详解

### 用法

```bash
# 本地文件评估
ginkgo eval strategy <strategy_file> [OPTIONS]

# 数据库策略评估
ginkgo eval strategy --file-id <uuid> [OPTIONS]
ginkgo eval strategy --portfolio-id <uuid> [OPTIONS]

# 列表和批量
ginkgo eval strategy --list [--filter <pattern>]
ginkgo eval strategy --all [--filter <pattern>] [OPTIONS]
```

### 参数

| 参数 | 短选项 | 类型 | 默认值 | 说明 |
|------|--------|------|--------|------|
| **策略来源** | | | | |
| `strategy_file` | - | `Path` | 可选 | 本地策略文件路径（.py 文件） |
| `--file-id` | - | `str` | None | 数据库策略文件 ID（MFile.uuid） |
| `--portfolio-id` | - | `str` | None | Portfolio UUID，评估其绑定的策略 |
| `--list` | - | `bool` | False | 列出数据库中所有策略 |
| `--all` | - | `bool` | False | 批量评估所有数据库策略 |
| `--filter` | - | `str` | None | 过滤策略名称（支持 --list 和 --all） |
| **评估选项** | | | | |
| `--level` | `-l` | `str` | `standard` | 评估级别：`basic`/`standard`/`strict` |
| `--data` | `-d` | `Path` | None | 测试数据文件（CSV/JSON），用于追踪/可视化 |
| `--events` | `-e` | `int` | 10 | 处理的事件数量（需要 --data） |
| `--show-trace` | `-t` | `bool` | False | 显示信号追踪（需要 --data） |
| `--visualize` | `-V` | `bool` | False | 生成可视化图表（需要 --data 和 --output） |
| **输出选项** | | | | |
| `--format` | `-f` | `str` | `text` | 输出格式：`text`/`json`/`markdown` |
| `--output` | `-o` | `Path` | stdout | 输出文件路径（可视化必需） |
| `--verbose` | `-v` | `bool` | False | 显示详细信息 |

**参数依赖规则**：
- `strategy_file`、`--file-id`、`--portfolio-id`、`--list`、`--all` 互斥（只能指定一个）
- `--show-trace` 需要 `--data`
- `--visualize` 需要 `--data` 和 `--output`
- `--events` 需要 `--data`

---

## 使用场景

### 场景 1：本地文件评估（< 2 秒）

```bash
# 基本评估
ginkgo eval strategy my_strategy.py

# 标准评估
ginkgo eval strategy my_strategy.py --level standard

# 严格评估
ginkgo eval strategy my_strategy.py --level strict --verbose

# 导出报告
ginkgo eval strategy my_strategy.py --output report.md
```

**输出示例**：
```
╭──────────────────────────────────────────────────────────╮
│           Strategy Evaluation Report                     │
╰──────────────────────────────────────────────────────────╯

File: my_strategy.py
Level: STANDARD
Result: ✅ PASSED

Status: PASSED
Duration: 1.23s
```

---

### 场景 2：评估 + 信号追踪（< 5 秒）

```bash
# 评估并显示信号追踪
ginkgo eval strategy my_strategy.py --data test.csv --show-trace

# 追踪更多事件
ginkgo eval strategy my_strategy.py --data test.csv --show-trace --events 100

# JSON 格式输出
ginkgo eval strategy my_strategy.py --data test.csv --show-trace --format json
```

**输出示例**：
```
╭──────────────────────────────────────────────────────────╮
│           Strategy Evaluation Report                     │
╰──────────────────────────────────────────────────────────╯

File: my_strategy.py
Level: STANDARD
Result: ✅ PASSED

╭──────────────────────────────────────────────────────────╮
│           Signal Trace Report                            │
╰──────────────────────────────────────────────────────────╯

Strategy: MyStrategy
Events Processed: 10
Signals Generated: 3 (2 buy, 1 sell)

Signals:
  📍 LONG 000001.SZ @ 10.70 on 2023-01-01
     Reason: 均线金叉
     Context: close=10.70, ma5=10.65

  📍 SHORT 000001.SZ @ 10.85 on 2023-01-05
     Reason: 均线死叉
     Context: close=10.85, ma5=10.82

Status: COMPLETED
Duration: 0.15s
```

---

### 场景 2.5：数据库策略评估（< 2 秒）

```bash
# 按 file_id 评估
ginkgo eval strategy --file-id 37efc02509744a2395480bd144424bd1

# 按 portfolio_id 评估其绑定的策略
ginkgo eval strategy --portfolio-id d47f50b6ca9046448abf7a5eda5a3519

# 列出所有数据库策略
ginkgo eval strategy --list

# 列出特定策略（过滤）
ginkgo eval strategy --list --filter "trend"

# 批量评估所有策略
ginkgo eval strategy --all --format json --output validation_report.json

# 数据库策略 + 信号追踪
ginkgo eval strategy --file-id 37efc02509744a... --data test.csv --show-trace

# 数据库策略 + 可视化
ginkgo eval strategy --file-id 37efc02509744a... --data test.csv --visualize --output db_strategy.png
```

**输出示例（--list）**：
```
╭─────────────────────────────────────────────────────────────╮
│                    Database Strategies                      │
├─────────────────────────────────────────────────────────────┤
│ File ID                       │ Name              │ Size    │
├───────────────────────────────┼──────────────────┼─────────┤
│ 37efc02509744a...             │ my_strategy.py   │ 2.3 KB  │
│ d47f50b6ca9046...             │ trend_follow.py  │ 3.1 KB  │
│ a1b2c3d4e5f6...               │ bollinger_bands  │ 1.8 KB  │
│ 3 files found                                                 │
└─────────────────────────────────────────────────────────────┘
```

**输出示例（数据库策略评估）**：
```
╭──────────────────────────────────────────────────────────╮
│           Strategy Evaluation Report                     │
╰──────────────────────────────────────────────────────────╯

Source: Database (file_id: 37efc02509744a...)
Name: my_strategy.py
Level: STANDARD
Result: ✅ PASSED

Temp File: /tmp/tmp_ginkgo_validate_12345.py (auto-cleaned)

Status: PASSED
Duration: 1.45s
```

**关键说明**：
- 数据库策略与本地文件评估功能**完全相同**
- 临时文件自动清理，无需手动删除
- 支持 `--show-trace` 和 `--visualize` 所有功能

---

### 场景 3：评估 + 可视化（< 10 秒）

```bash
# 生成静态图表
ginkgo eval strategy my_strategy.py --data test.csv --visualize --output signals.png

# 生成交互式图表
ginkgo eval strategy my_strategy.py --data test.csv --visualize --output signals.html

# 自定义图表大小
ginkgo eval strategy my_strategy.py --data test.csv --visualize --output chart.png --width 1600 --height 800
```

**输出结果**：生成图表文件，不打印到终端

---

### 场景 4：评估 + 追踪 + 可视化（组合）

```bash
# 全部输出：评估报告 + 追踪信息 + 可视化图表
ginkgo eval strategy my_strategy.py \
    --data test.csv \
    --show-trace \
    --visualize \
    --output signals.png \
    --events 50
```

**输出**：
1. 终端显示：评估报告 + 信号追踪
2. 文件输出：`signals.png` 可视化图表

---

### 场景 5：仅导出可视化（无追踪信息）

```bash
# 只生成图表，不显示追踪详情
ginkgo eval strategy my_strategy.py \
    --data test.csv \
    --visualize \
    --output chart.png
```

**输出**：仅生成 `chart.png`，终端显示简要评估结果

---

## 数据文件格式

### CSV 格式（K线数据）

```csv
timestamp,code,open,high,low,close,volume
2023-01-01,000001.SZ,10.5,10.8,10.3,10.7,1000000
2023-01-02,000001.SZ,10.7,10.9,10.5,10.8,1200000
```

### JSON 格式（事件列表）

```json
{
  "events": [
    {
      "type": "EventPriceUpdate",
      "code": "000001.SZ",
      "timestamp": "2023-01-01T00:00:00",
      "open": 10.5,
      "high": 10.8,
      "low": 10.3,
      "close": 10.7,
      "volume": 1000000
    }
  ]
}
```

---

## 输出格式

### Text 格式（默认）

适合终端查看，使用 Rich 美化输出。

### JSON 格式

```json
{
  "validation": {
    "file": "my_strategy.py",
    "level": "STANDARD",
    "result": "PASSED",
    "summary": {
      "errors": 0,
      "warnings": 1,
      "suggestions": 0
    }
  },
  "trace": {
    "signals_generated": 3,
    "buy_count": 2,
    "sell_count": 1,
    "signals": [...]
  }
}
```

### Markdown 格式

适合文档生成和 CI/CD 日志。

```markdown
# Strategy Evaluation Report

**File**: my_strategy.py
**Level**: STANDARD
**Result**: ✅ PASSED

## Signal Trace

- Events Processed: 10
- Signals Generated: 3 (2 buy, 1 sell)
```

---

## 参数依赖关系

```
strategy_file (必需)
    |
    ├── level: 评估级别
    |
    ├── data (可选)
    │   ├── events: 事件数量
    │   ├── show-trace: 显示追踪
    │   └── visualize: 生成图表
    │       └── output (必需): 图表文件路径
    │
    ├── format: 输出格式
    ├── output (可选): 报告文件路径
    └── verbose: 详细信息
```

**依赖规则**：
- `--show-trace` 需要 `--data`
- `--visualize` 需要 `--data` 和 `--output`
- `--events` 需要 `--data`

---

## 组合工作流示例

### 典型开发流程

```bash
# 1. 快速评估（< 2 秒）
ginkgo eval strategy my_strategy.py

# 2. 如果评估通过，运行信号追踪
ginkgo eval strategy my_strategy.py --data test.csv --show-trace

# 3. 生成可视化检查
ginkgo eval strategy my_strategy.py --data test.csv --visualize --output signals.png

# 4. 完整检查（一次性）
ginkgo eval strategy my_strategy.py \
    --data test.csv \
    --show-trace \
    --visualize \
    --output signals.png
```

### CI/CD 集成

```bash
#!/bin/bash
# ci_validate_strategy.sh

# 评估策略
ginkgo eval strategy my_strategy.py \
    --level strict \
    --format json \
    --output validation.json

# 检查评估结果
if ! grep -q '"result": "PASSED"' validation.json; then
    echo "❌ 策略评估失败"
    cat validation.json
    exit 1
fi

# 运行信号追踪
ginkgo eval strategy my_strategy.py \
    --data test.csv \
    --show-trace \
    --events 50 \
    --format json \
    --output trace.json

# 生成可视化（用于 CI 日志）
ginkgo eval strategy my_strategy.py \
    --data test.csv \
    --visualize \
    --output ci_chart.png

echo "✅ 策略评估通过"
exit 0
```

---

## 退出码

| 退出码 | 含义 | 说明 |
|--------|------|------|
| 0 | SUCCESS | 命令成功执行 |
| 1 | VALIDATION_FAILED | 评估失败（发现错误） |
| 2 | FILE_ERROR | 文件不存在或无法读取 |
| 3 | PARSING_ERROR | 文件语法错误 |
| 4 | DATA_ERROR | 数据文件格式错误 |
| 5 | INTERNAL_ERROR | 内部错误（请报告 bug） |

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `GINKGO_VALIDATE_LEVEL` | 默认评估级别 | `standard` |
| `GINKGO_VALIDATE_FORMAT` | 默认输出格式 | `text` |
| `GINKGO_TRACE_EVENTS` | 默认追踪事件数 | `10` |
| `GINKGO_CHART_WIDTH` | 默认图表宽度 | `1200` |
| `GINKGO_CHART_HEIGHT` | 默认图表高度 | `600` |

示例：
```bash
export GINKGO_VALIDATE_LEVEL=strict
export GINKGO_VALIDATE_FORMAT=json
ginkgo eval strategy my_strategy.py
```

---

## 性能指标

| 操作 | 指标 | 目标 |
|------|------|------|
| 静态评估 | 响应时间 | < 1s |
| 信号追踪 | 单事件处理 | < 10ms |
| 可视化生成 | 图表生成 | < 5s |

---

**CLI Interface Status**: ✅ **COMPLETE** - 统一入口设计
- ✅ 单一命令 `ginkgo eval strategy`
- ✅ 通过参数控制输出模式
- ✅ 灵活的组合使用
- ✅ CI/CD 友好
