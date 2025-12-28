# Data Model: Strategy Validation Module

**Feature**: 002-strategy-validation
**Date**: 2025-12-27
**Phase**: Phase 1 - Design

## 实体概述

策略验证模块包含以下核心实体：

**验证相关**:
1. **ValidationResult** - 验证结果实体
2. **ValidationIssue** - 验证问题实体
3. **ValidationLevel** - 验证级别枚举
4. **ValidationSeverity** - 问题严重程度枚举
5. **StrategyMetadata** - 策略元数据实体

**信号追踪相关**:
6. **SignalTrace** - 信号追踪记录
7. **SignalTraceReport** - 追踪报告
8. **DataSourceAdapter** - 数据源适配器接口
9. **ChartConfig** - 图表配置

---

## 1. ValidationResult

验证结果实体，表示一次完整的验证结果。

### 属性

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `strategy_file` | `Path` | ✅ | 策略文件路径 |
| `strategy_name` | `str` | ✅ | 策略类名称 |
| `level` | `ValidationLevel` | ✅ | 验证级别 |
| `passed` | `bool` | ✅ | 是否通过验证 |
| `errors` | `List[ValidationIssue]` | ✅ | 错误列表 |
| `warnings` | `List[ValidationIssue]` | ✅ | 警告列表 |
| `suggestions` | `List[ValidationIssue]` | ✅ | 建议列表 |
| `duration_ms` | `int` | ✅ | 验证耗时（毫秒） |
| `timestamp` | `datetime` | ✅ | 验证时间戳 |

### 方法

```python
class ValidationResult:
    def __init__(self, strategy_file: Path, strategy_name: str, level: ValidationLevel):
        self.strategy_file = strategy_file
        self.strategy_name = strategy_name
        self.level = level
        self.passed = True
        self.errors: List[ValidationIssue] = []
        self.warnings: List[ValidationIssue] = []
        self.suggestions: List[ValidationIssue] = []
        self.duration_ms = 0
        self.timestamp = datetime.now()

    def add_issue(self, issue: ValidationIssue) -> None:
        """添加验证问题"""
        if issue.severity == ValidationSeverity.ERROR:
            self.errors.append(issue)
            self.passed = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings.append(issue)
        else:
            self.suggestions.append(issue)

    @property
    def total_issues(self) -> int:
        """获取总问题数"""
        return len(self.errors) + len(self.warnings) + len(self.suggestions)

    def get_summary(self) -> Dict[str, int]:
        """获取问题摘要"""
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "suggestions": len(self.suggestions),
            "total": self.total_issues
        }
```

### 状态转换

```
初始化 (passed=True)
    ↓
添加 ERROR → passed=False
添加 WARNING → passed 不变
添加 SUGGESTION → passed 不变
```

---

## 2. ValidationIssue

验证问题实体，表示一个具体的验证问题。

### 属性

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `rule_id` | `str` | ✅ | 规则唯一标识 |
| `severity` | `ValidationSeverity` | ✅ | 严重程度 |
| `line` | `int` | ✅ | 问题所在行号 |
| `column` | `int` | ✅ | 问题所在列号 |
| `message` | `str` | ✅ | 问题描述 |
| `suggestion` | `str` | ❌ | 修复建议 |
| `code_snippet` | `str` | ❌ | 问题代码片段 |

### 方法

```python
class ValidationIssue:
    def __init__(
        self,
        rule_id: str,
        severity: ValidationSeverity,
        line: int,
        column: int,
        message: str,
        suggestion: Optional[str] = None,
        code_snippet: Optional[str] = None
    ):
        self.rule_id = rule_id
        self.severity = severity
        self.line = line
        self.column = column
        self.message = message
        self.suggestion = suggestion or self._generate_suggestion()
        self.code_snippet = code_snippet

    def _generate_suggestion(self) -> Optional[str]:
        """根据规则 ID 生成修复建议"""
        # 从规则库中查找建议模板
        return RuleRegistry.get_suggestion(self.rule_id)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 输出）"""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet
        }
```

### 示例

```python
# 创建一个错误
issue = ValidationIssue(
    rule_id="FR-011",
    severity=ValidationSeverity.ERROR,
    line=15,
    column=0,
    message="策略类必须继承 BaseStrategy",
    suggestion="修改类定义为：class MyStrategy(BaseStrategy):"
)
```

---

## 3. ValidationLevel

验证级别枚举，定义三种验证级别。

### 枚举值

```python
from enum import Enum

class ValidationLevel(Enum):
    """验证级别"""
    BASIC = "basic"       # 仅结构验证（P1）
    STANDARD = "standard" # 结构 + 逻辑验证（P1 + P2）
    STRICT = "strict"     # 结构 + 逻辑 + 最佳实践（P1 + P2 + P3）
```

### 规则映射

| 级别 | 结构规则 | 逻辑规则 | 最佳实践规则 |
|------|----------|----------|-------------|
| BASIC | ✅ | ❌ | ❌ |
| STANDARD | ✅ | ✅ | ❌ |
| STRICT | ✅ | ✅ | ✅ |

---

## 4. ValidationSeverity

问题严重程度枚举。

### 枚举值

```python
class ValidationSeverity(Enum):
    """问题严重程度"""
    ERROR = "error"       # 错误：必须修复
    WARNING = "warning"   # 警告：应该修复
    INFO = "info"         # 建议：可以优化
```

### 使用场景

| 严重程度 | 含义 | 影响验证结果 |
|----------|------|-------------|
| ERROR | 违反必需规则（FR） | 导致验证失败 |
| WARNING | 违反推荐规则 | 不导致失败 |
| INFO | 优化建议 | 不导致失败 |

---

## 5. StrategyMetadata

策略元数据实体，存储从策略文件中提取的信息。

### 属性

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_path` | `Path` | ✅ | 文件路径 |
| `class_name` | `str` | ✅ | 策略类名 |
| `base_classes` | `List[str]` | ✅ | 继承的基类列表 |
| `has_cal_method` | `bool` | ✅ | 是否实现 cal() 方法 |
| `is_abstract` | `bool` | ✅ | 是否为抽象类 |
| `decorators` | `List[str]` | ✅ | 使用的装饰器列表 |
| `imports` | `List[str]` | ✅ | 导入的模块列表 |
| `line_count` | `int` | ✅ | 代码行数 |

### 方法

```python
class StrategyMetadata:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.class_name = ""
        self.base_classes = []
        self.has_cal_method = False
        self.is_abstract = True
        self.decorators = []
        self.imports = []
        self.line_count = 0

    @classmethod
    def from_ast(cls, file_path: Path, tree: ast.AST) -> "StrategyMetadata":
        """从 AST 解析元数据"""
        metadata = cls(file_path)
        visitor = StrategyMetadataVisitor(metadata)
        visitor.visit(tree)
        return metadata
```

---

## 6. SignalTrace

信号追踪记录，表示单次 cal() 调用的完整上下文。

### 属性

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `trace_id` | `str` | ✅ | 追踪记录唯一标识 |
| `timestamp` | `datetime` | ✅ | 信号生成时间 |
| `input_context` | `Dict[str, Any]` | ✅ | 输入事件摘要（由适配器提取） |
| `signal` | `Signal` | ✅ | 生成的信号对象 |
| `signal_info` | `str` | ✅ | 格式化的信号描述 |
| `strategy_state` | `Dict[str, Any]` | ❌ | 策略状态快照（可选） |

### 方法

```python
class SignalTrace:
    def __init__(
        self,
        trace_id: str,
        timestamp: datetime,
        input_context: Dict[str, Any],
        signal: Signal,
        signal_info: str,
        strategy_state: Optional[Dict[str, Any]] = None
    ):
        self.trace_id = trace_id
        self.timestamp = timestamp
        self.input_context = input_context
        self.signal = signal
        self.signal_info = signal_info
        self.strategy_state = strategy_state or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于导出）"""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "input_context": self.input_context,
            "signal": {
                "code": self.signal.code,
                "direction": self.signal.direction.name,
                "reason": self.signal.reason
            },
            "signal_info": self.signal_info,
            "strategy_state": self.strategy_state
        }
```

---

## 7. SignalTraceReport

信号追踪报告，汇总所有信号追踪记录。

### 属性

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `strategy_name` | `str` | ✅ | 策略名称 |
| `traces` | `List[SignalTrace]` | ✅ | 所有追踪记录 |
| `start_time` | `datetime` | ✅ | 追踪开始时间 |
| `end_time` | `datetime` | ✅ | 追踪结束时间 |
| `signal_count` | `int` | ✅ | 信号总数 |
| `buy_count` | `int` | ✅ | 买入信号数 |
| `sell_count` | `int` | ✅ | 卖出信号数 |

### 方法

```python
class SignalTraceReport:
    def __init__(self, traces: List[SignalTrace], strategy_name: str):
        self.traces = traces
        self.strategy_name = strategy_name
        self.start_time = min(t.timestamp for t in traces) if traces else datetime.now()
        self.end_time = max(t.timestamp for t in traces) if traces else datetime.now()
        self.signal_count = len(traces)
        self.buy_count = sum(1 for t in traces if t.signal.direction == DIRECTION_TYPES.LONG)
        self.sell_count = sum(1 for t in traces if t.signal.direction == DIRECTION_TYPES.SHORT)

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要统计"""
        return {
            "strategy_name": self.strategy_name,
            "signal_count": self.signal_count,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "duration": (self.end_time - self.start_time).total_seconds()
        }

    def export_json(self, output: Path) -> None:
        """导出为 JSON"""
        data = {
            "summary": self.get_summary(),
            "traces": [t.to_dict() for t in self.traces]
        }
        output.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def export_markdown(self, output: Path) -> None:
        """导出为 Markdown"""
        md = f"# Signal Trace Report\n\n"
        md += f"**Strategy**: {self.strategy_name}\n"
        md += f"**Signals**: {self.signal_count} ({self.buy_count} buy, {self.sell_count} sell)\n\n"

        for trace in self.traces:
            md += f"## {trace.timestamp}\n"
            md += f"- **Signal**: {trace.signal_info}\n"
            md += f"- **Input**: {trace.input_context}\n\n"

        output.write_text(md)
```

---

## 8. DataSourceAdapter (接口)

数据源适配器接口，定义统一的数据提取方法。

### 接口定义

```python
from abc import ABC, abstractmethod

class DataSourceAdapter(ABC):
    """数据源适配器接口"""

    @abstractmethod
    def get_visualization_data(self, event: EventBase) -> Dict[str, Any]:
        """提取可视化所需数据"""
        pass

    @abstractmethod
    def format_signal_info(self, signal: Signal, event: EventBase) -> str:
        """格式化信号描述"""
        pass

    @abstractmethod
    def get_data_summary(self, event: EventBase) -> Dict[str, Any]:
        """提取数据摘要"""
        pass
```

### 实现示例

```python
class BarDataAdapter(DataSourceAdapter):
    """K线数据适配器"""

    def get_visualization_data(self, event: EventPriceUpdate) -> Dict[str, Any]:
        bar = event.payload
        return {
            "type": "bar",
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        }

    def format_signal_info(self, signal: Signal, event: EventPriceUpdate) -> str:
        bar = event.payload
        return f"Signal[{signal.direction.name}] {signal.code} @ {bar.close:.2f} on {bar.timestamp.date()}"

    def get_data_summary(self, event: EventPriceUpdate) -> Dict[str, Any]:
        bar = event.payload
        return {
            "code": bar.code,
            "timestamp": bar.timestamp,
            "close": bar.close,
            "volume": bar.volume
        }
```

---

## 9. ChartConfig

图表配置实体，定义可视化样式。

### 属性

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `chart_type` | `str` | ✅ | 图表类型（candle/line/scatter） |
| `width` | `int` | ✅ | 图表宽度（像素） |
| `height` | `int` | ✅ | 图表高度（像素） |
| `show_volume` | `bool` | ❌ | 是否显示成交量 |
| `buy_color` | `str` | ❌ | 买入信号颜色 |
| `sell_color` | `str` | ❌ | 卖出信号颜色 |
| `interactive` | `bool` | ❌ | 是否交互式 |

### 默认配置

```python
DEFAULT_CHART_CONFIG = ChartConfig(
    chart_type="candle",
    width=1200,
    height=600,
    show_volume=True,
    buy_color="green",
    sell_color="red",
    interactive=False
)
```

---

## 10. 实体关系图（更新版）

```
验证模块实体:
┌─────────────────────────┐
│   ValidationResult      │
│  ─────────────────────  │
│  - strategy_file: Path  │
│  - strategy_name: str   │
│  - level: ValidationLevel│
│  - passed: bool         │ 1
│  - errors: List[]       │
│  - warnings: List[]     │
│  - suggestions: List[]  │
└─────────────────────────┘
            │
            │ 包含多个
            ▼
┌─────────────────────────┐
│    ValidationIssue      │
│  ─────────────────────  │
│  - rule_id: str         │
│  - severity: Severity   │
│  - line: int            │
│  - message: str         │
└─────────────────────────┘

信号追踪模块实体:
┌─────────────────────────┐
│   SignalTraceReport     │
│  ─────────────────────  │
│  - strategy_name: str   │
│  - traces: List[]       │ 1
│  - signal_count: int    │
│  - buy_count: int       │
│  - sell_count: int      │
└───────────┬─────────────┘
            │
            │ 包含多个
            ▼
┌─────────────────────────┐
│      SignalTrace        │
│  ─────────────────────  │
│  - trace_id: str        │
│  - timestamp: datetime  │
│  - input_context: Dict  │
│  - signal: Signal       │
│  - signal_info: str     │
└─────────────────────────┘

适配器模块:
┌─────────────────────────┐
│   DataSourceAdapter     │ (接口)
│  ─────────────────────  │
│  + get_visualization_data()
│  + format_signal_info() │
│  + get_data_summary()   │
└───────────┬─────────────┘
            │
            ├─────────────────┬─────────────────┐
            ▼                 ▼                 ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ BarDataAdapter│  │TickDataAdapter│  │OrderFlowAdapter│
    └─────────────┘  └─────────────┘  └─────────────┘
```

---

## 11. 数据持久化（更新）

### 存储策略

**验证结果**：
- **运行时使用**：验证结果仅在运行时使用，不存储到数据库
- **可选导出**：支持导出为 JSON/Markdown 文件用于记录

**信号追踪**：
- **运行时使用**：追踪记录保存在内存中，用于生成可视化和报告
- **必须导出**：追踪报告必须支持导出为 JSON/CSV/Markdown 格式
- **可视化文件**：生成的图表保存为 PNG/SVG/HTML 文件

### 追踪报告导出示例

```python
# 导出 JSON
report.export_json(Path("signal_trace.json"))

# 导出 Markdown
report.export_markdown(Path("signal_trace.md"))

# 导出 CSV
import csv
with open("signals.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "code", "direction", "reason"])
    writer.writeheader()
    for trace in report.traces:
        writer.writerow({
            "timestamp": trace.timestamp,
            "code": trace.signal.code,
            "direction": trace.signal.direction.name,
            "reason": trace.signal.reason
        })
```

---

## 12. 与 Ginkgo 核心实体的集成（更新）

### 依赖的核心实体

```python
# 策略验证模块依赖以下 Ginkgo 核心实体：
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.tick_update import EventTickUpdate
from ginkgo.trading.events.event_base import EventBase
from ginkgo.enums import DIRECTION_TYPES
```

### 验证规则映射

| 规则 ID | 检查内容 | 依赖实体 |
|---------|----------|---------|
| FR-011 | 继承 BaseStrategy | BaseStrategy |
| FR-012 | cal() 方法签名 | EventBase, Signal |
| FR-022 | Signal 字段完整性 | Signal |
| FR-023 | direction 有效性 | DIRECTION_TYPES |

### 信号追踪集成

| 功能 | 事件类型 | 适配器 | 可视化 |
|------|----------|--------|--------|
| K线追踪 | EventPriceUpdate | BarDataAdapter | K线图 + 信号标注 |
| Tick追踪 | EventTickUpdate | TickDataAdapter | 价格线 + 信号标注 |
| 订单流追踪 | EventOrderFlow | OrderFlowAdapter | 订单流图 + 信号标注 |

---

**Data Model Status**: ✅ **COMPLETE** - 所有实体定义清晰，包括：
- ✅ 验证模块实体（ValidationResult、ValidationIssue）
- ✅ 信号追踪实体（SignalTrace、SignalTraceReport）
- ✅ 数据源适配器接口（DataSourceAdapter）
- ✅ 可视化配置（ChartConfig）
- ✅ 与 Ginkgo 核心实体的集成关系

**可以进入实现阶段**
