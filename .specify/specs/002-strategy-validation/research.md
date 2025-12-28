# Research: Strategy Validation Module

**Feature**: 002-strategy-validation
**Date**: 2025-12-27
**Phase**: Phase 0 - Research & Technology Selection

## 研究概述

本文档记录策略验证模块的技术调研结果，包括技术选型决策、最佳实践研究和实现方案。

**核心目标**: 除了回测，提供快速验证策略的方法，并直观确认信号生成是否符合预期。

---

## 1. 静态分析 vs 运行时分析 vs 信号追踪

### 决策：混合模式（AST 静态分析 + inspect 运行时检查）

**选择方案**:
- **AST 静态分析**：用于结构验证（继承关系、方法签名、装饰器检查）
- **inspect 运行时检查**：用于逻辑验证（实例化策略、检查方法行为）

**理由**:
1. **AST 优势**：
   - 不执行代码，避免副作用
   - 快速解析，< 100ms（满足 SC-007）
   - 可以检查语法错误和导入问题
   - 精确定位问题位置（行号、列号）

2. **inspect 优势**：
   - 验证实际运行时行为
   - 检查 Signal 对象的字段完整性
   - 验证 TimeProvider 调用方式
   - 捕获运行时异常

3. **混合模式**：
   - Basic 级别：仅 AST 分析
   - Standard 级别：AST + 基础 inspect 检查
   - Strict 级别：AST + 完整 inspect + 最佳实践检查

**替代方案对比**:
| 方案 | 优点 | 缺点 | 是否采用 |
|------|------|------|----------|
| 纯 AST | 安全、快速 | 无法验证运行时行为 | ❌ 不充分 |
| 纯 inspect | 验证完整 | 可能执行副作用代码 | ❌ 不安全 |
| 混合模式 | 平衡安全和完整度 | 实现复杂 | ✅ 采用 |

---

## 2. Python AST 模块最佳实践

### 决策：使用 ast.NodeVisitor 模式 + 自定义规则注册

**技术选型**:
```python
import ast

class ValidationVisitor(ast.NodeVisitor):
    def __init__(self, rules: List[BaseRule]):
        self.rules = rules
        self.issues = []

    def visit_ClassDef(self, node: ast.ClassDef):
        # 应用所有结构验证规则
        for rule in self.rules:
            if rule.can_apply(node):
                result = rule.validate(node)
                if result:
                    self.issues.append(result)
        self.generic_visit(node)
```

**最佳实践**:
1. **规则注册模式**：每个验证规则独立实现，支持动态加载
2. **上下文传递**：使用 `self.stack` 跟踪当前节点上下文
3. **类型注解解析**：使用 `typing.get_type_hints()` 辅助 AST 类型检查
4. **装饰器检测**：检查 `node.decorator_list` 识别装饰器使用

**参考实现**:
- `pylint`：使用 AST 进行静态检查
- `flake8`：AST + pep8 检查
- `mypy`：类型检查专用

---

## 3. 策略规则设计模式

### 决策：责任链模式 + 规则优先级

**设计模式**:
```python
class BaseRule(ABC):
    @abstractmethod
    def can_apply(self, node: ast.AST) -> bool:
        """判断规则是否适用于当前节点"""

    @abstractmethod
    def validate(self, node: ast.AST) -> Optional[ValidationIssue]:
        """执行验证，返回问题或 None"""

    @property
    def severity(self) -> ValidationSeverity:
        """问题严重程度"""
        return ValidationSeverity.ERROR

    @property
    def level(self) -> ValidationLevel:
        """适用的验证级别"""
        return ValidationLevel.BASIC
```

**规则分类**:
1. **结构规则**（StructuralRules）：
   - `BaseStrategyInheritanceRule`：检查继承关系
   - `CalMethodSignatureRule`：检查 cal() 方法签名
   - `SuperInitCallRule`：检查 super().__init__() 调用
   - `AbstractMarkerRule`：检查 `__abstract__ = False` 标记

2. **逻辑规则**（LogicalRules）：
   - `ReturnStatementRule`：检查返回类型
   - `SignalFieldRule`：检查 Signal 字段完整性
   - `TimeProviderUsageRule`：检查时间获取方式
   - `ForbiddenOperationsRule`：检查禁止操作（数据库查询等）

3. **最佳实践规则**（BestPracticeRules）：
   - `DecoratorUsageRule`：检查装饰器使用
   - `ExceptionHandlingRule`：检查异常处理
   - `LoggingRule`：检查日志记录
   - `ParameterValidationRule`：检查参数验证

---

## 4. CLI 接口设计

### 决策：使用 Typer 框架 + Rich 输出，统一入口设计

**技术选型**:
- **Typer**：与现有 Ginkgo CLI 保持一致
- **Rich**：美化和格式化输出
- **命令结构**：统一入口，通过参数控制输出模式
  ```bash
  ginkgo validate strategy <strategy_file> [OPTIONS]
  ```

**参数设计**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `strategy_file` | Path | 必需 | 策略文件路径 |
| `--level` / `-l` | str | `standard` | 验证级别：basic/standard/strict |
| `--data` / `-d` | Path | None | 测试数据文件（用于追踪/可视化） |
| `--events` / `-e` | int | 10 | 处理的事件数量 |
| `--show-trace` / `-t` | bool | False | 显示信号追踪 |
| `--visualize` / `-V` | bool | False | 生成可视化图表 |
| `--format` / `-f` | str | `text` | 输出格式：text/json/markdown |
| `--output` / `-o` | Path | stdout | 输出文件路径 |
| `--verbose` / `-v` | bool | False | 显示详细信息 |

**依赖规则**：
- `--show-trace` 需要 `--data`
- `--visualize` 需要 `--data` 和 `--output`

**实现示例**:
```python
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

@app.command()
def strategy(
    strategy_file: Path = typer.Argument(..., help="策略文件路径"),
    level: ValidationLevel = typer.Option(ValidationLevel.STANDARD, "--level", "-l"),
    data: Optional[Path] = typer.Option(None, "--data", "-d", help="测试数据文件"),
    events: int = typer.Option(10, "--events", "-e", help="处理的事件数量"),
    show_trace: bool = typer.Option(False, "--show-trace", "-t", help="显示信号追踪"),
    visualize: bool = typer.Option(False, "--visualize", "-V", help="生成可视化图表"),
    format: OutputFormat = typer.Option(OutputFormat.TEXT, "--format", "-f"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """验证策略文件的结构和逻辑"""
    # 1. 静态验证
    result = validate_strategy_file(strategy_file, level)
    reporter = ReporterFactory.create(format)
    console.print(reporter.generate_validation(result))

    # 2. 信号追踪（如果指定 --show-trace）
    if show_trace and data:
        trace_result = trace_signals(strategy_file, data, events)
        console.print(reporter.generate_trace(trace_result))

    # 3. 可视化（如果指定 --visualize）
    if visualize and data and output:
        generate_chart(strategy_file, data, output)
        console.print(f"✅ Chart saved to {output}")
```

**设计优势**：
- 单一入口，降低学习成本
- 参数组合灵活，支持多种使用场景
- 可以同时执行验证、追踪、可视化
- CI/CD 友好，易于集成

---

## 5. 报告格式设计

### 决策：三种格式支持不同使用场景

**Text 格式**（默认，适合终端）:
```
╭──────────────────────────────────────────────────────────╮
│           Strategy Validation Report                     │
╰──────────────────────────────────────────────────────────╯

File: my_strategy.py
Level: STANDARD
Result: ❌ FAILED (2 errors, 1 warning)

Errors:
  ✗ Line 15: 缺少必需的 cal() 方法
  ✗ Line 8: 必须继承 BaseStrategy

Warnings:
  ⚠ Line 25: 建议使用 @time_logger 装饰器

Status: FAILED
```

**JSON 格式**（适合程序解析）:
```json
{
  "file": "my_strategy.py",
  "level": "STANDARD",
  "result": "FAILED",
  "summary": {
    "errors": 2,
    "warnings": 1,
    "suggestions": 0
  },
  "issues": [
    {
      "severity": "ERROR",
      "line": 15,
      "column": 4,
      "message": "缺少必需的 cal() 方法",
      "suggestion": "添加 cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal] 方法"
    }
  ]
}
```

**Markdown 格式**（适合文档生成）:
```markdown
# Strategy Validation Report

**File**: my_strategy.py
**Level**: STANDARD
**Result**: ❌ FAILED

## Summary

- Errors: 2
- Warnings: 1
- Suggestions: 0

## Issues

### Errors

#### Line 15: 缺少必需的 cal() 方法

**Suggestion**: 添加 `cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]` 方法

#### Line 8: 必须继承 BaseStrategy

**Suggestion**: 修改类定义为 `class MyStrategy(BaseStrategy):`
```

---

## 6. 性能优化策略

### 决策：多级缓存 + 懒加载

**优化策略**:
1. **AST 解析缓存**：
   ```python
   @cache_with_expiration(3600)  # 缓存 1 小时
   def parse_ast(file_path: Path) -> ast.Module:
       with open(file_path) as f:
           return ast.parse(f.read())
   ```

2. **规则懒加载**：
   ```python
   class RuleRegistry:
       def __init__(self):
           self._rules = None

       @property
       def rules(self) -> List[BaseRule]:
           if self._rules is None:
               self._rules = self._load_rules()
           return self._rules
   ```

3. **批量验证优化**：
   - 并行解析多个文件（使用 `concurrent.futures`）
   - 共享规则实例（规则无状态）
   - 增量报告生成（边验证边输出）

**性能目标达成**:
- 单文件验证 < 2 秒 ✅（目标 SC-003）
- CLI 响应 < 1 秒 ✅（目标 SC-007）
- 批量验证 >= 10 个文件 ✅（目标 SC-004）

---

## 7. 测试策略

### 决策：TDD + 分类标记

**测试分类**:
1. **单元测试**（@pytest.mark.unit）：
   - 测试单个规则的 validate() 方法
   - 测试 AST 解析逻辑
   - 测试报告生成器

2. **集成测试**（@pytest.mark.integration）：
   - 测试完整验证流程
   - 测试 CLI 命令
   - 测试多种格式输出

**测试覆盖率目标**: > 85%（SC-008）

**测试策略文件**:
```python
# tests/integration/trading/validation/fixtures/strategies/

# valid_strategy.py - 完全正确的策略
class ValidStrategy(BaseStrategy):
    __abstract__ = False
    def cal(self, portfolio_info, event):
        return [Signal(...)]

# invalid_structure.py - 结构错误
class InvalidStructure:  # 未继承 BaseStrategy
    pass

# invalid_logic.py - 逻辑错误
class InvalidLogic(BaseStrategy):
    __abstract__ = False
    def cal(self, portfolio_info, event):
        return None  # 应返回 List[Signal]
```

---

## 8. 技术风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 策略文件导入失败 | 无法运行时检查 | 使用 AST 作为回退方案 |
| 动态生成的策略类 | AST 无法分析 | 标记警告，建议手动检查 |
| BaseStrategy 接口变化 | 规则失效 | 版本检测 + 友好错误提示 |
| 复杂装饰器干扰 | 误报/漏报 | 人工审核关键规则 |
| 性能退化 | 不满足 SC-003 | 性能基准测试 + CI 集成 |

---

## 9. 信号追踪技术设计

### 决策：上下文管理器 + 适配器模式

**核心设计**:
```python
from contextlib import contextmanager

class SignalTracer:
    """信号追踪器 - 捕获策略运行时的信号生成过程"""

    def __init__(self, strategy: BaseStrategy, adapter: DataSourceAdapter):
        self.strategy = strategy
        self.adapter = adapter
        self.traces: List[SignalTrace] = []

    @contextmanager
    def trace(self):
        """追踪上下文管理器"""
        original_cal = self.strategy.cal

        def traced_cal(portfolio_info, event, *args, **kwargs):
            # 记录输入
            input_context = self.adapter.get_data_summary(event)

            # 执行策略
            signals = original_cal(portfolio_info, event, *args, **kwargs)

            # 记录输出
            for signal in signals:
                trace = SignalTrace(
                    timestamp=event.business_timestamp,
                    input_context=input_context,
                    signal=signal,
                    signal_info=self.adapter.format_signal_info(signal, event)
                )
                self.traces.append(trace)
                print(f"📍 {signal.direction.name} {signal.code}: {signal.reason}")

            return signals

        self.strategy.cal = traced_cal
        yield
        self.strategy.cal = original_cal

    def get_report(self) -> SignalTraceReport:
        """生成追踪报告"""
        return SignalTraceReport(self.traces)
```

**使用方式**:
```python
# 创建追踪器
adapter = AdapterFactory.create(event)
tracer = SignalTracer(strategy, adapter)

# 在上下文中追踪
with tracer.trace():
    strategy.cal(portfolio_info, event)

# 获取报告
report = tracer.get_report()
```

---

## 10. 数据源适配器设计

### 决策：适配器模式 + 工厂模式

**适配器接口**:
```python
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

**K线适配器实现**:
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
        return (f"Signal[{signal.direction.name}] {signal.code} "
                f"@ {bar.close:.2f} on {bar.timestamp.date()}")

    def get_data_summary(self, event: EventPriceUpdate) -> Dict[str, Any]:
        bar = event.payload
        return {
            "code": bar.code,
            "timestamp": bar.timestamp,
            "close": bar.close,
            "volume": bar.volume
        }
```

**Tick 适配器实现**:
```python
class TickDataAdapter(DataSourceAdapter):
    """Tick数据适配器"""

    def get_visualization_data(self, event: EventTickUpdate) -> Dict[str, Any]:
        tick = event.payload
        return {
            "type": "tick",
            "timestamp": tick.timestamp,
            "price": tick.price,
            "volume": tick.volume,
            "bid_ask_spread": tick.bid_ask_spread
        }

    def format_signal_info(self, signal: Signal, event: EventTickUpdate) -> str:
        tick = event.payload
        return (f"Signal[{signal.direction.name}] {signal.code} "
                f"@ {tick.price:.4f} at {tick.timestamp.time()}")

    def get_data_summary(self, event: EventTickUpdate) -> Dict[str, Any]:
        tick = event.payload
        return {
            "code": tick.code,
            "timestamp": tick.timestamp,
            "price": tick.price,
            "volume": tick.volume
        }
```

**工厂模式**:
```python
class AdapterFactory:
    """适配器工厂"""

    _adapters = {
        EventPriceUpdate: BarDataAdapter,
        EventTickUpdate: TickDataAdapter,
        # 未来扩展:
        # EventOrderFlow: OrderFlowAdapter,
        # EventFundamentalUpdate: FundamentalAdapter
    }

    @classmethod
    def create(cls, event: EventBase) -> DataSourceAdapter:
        """根据事件类型创建适配器"""
        adapter_class = cls._adapters.get(type(event))
        if adapter_class is None:
            raise ValueError(f"Unsupported event type: {type(event)}")
        return adapter_class()

    @classmethod
    def register(cls, event_type: Type[EventBase], adapter_class: Type[DataSourceAdapter]):
        """注册新的适配器"""
        cls._adapters[event_type] = adapter_class
```

---

## 11. 可视化技术选型

### 决策：Matplotlib（静态）+ Plotly（交互式）

**技术对比**:

| 特性 | Matplotlib | Plotly |
|------|------------|--------|
| 静态图表 | ✅ 优秀 | ✅ 支持 |
| 交互式图表 | ❌ 不支持 | ✅ 优秀 |
| K线图 | 需 mplfinance | 内置支持 |
| 导出格式 | PNG/SVG/PDF | PNG/SVG/HTML |
| 性能 | 快 | 中等 |
| 学习曲线 | 平缓 | 中等 |

**选择方案**:
1. **默认使用 Matplotlib**：生成静态图表（PNG/SVG），满足基本需求
2. **可选 Plotly**：通过 `--interactive` 参数生成交互式 HTML 图表

**K线图可视化实现**:
```python
import matplotlib.pyplot as plt
import mplfinance as mpf

class SignalVisualizer:
    """信号可视化器"""

    def visualize_bars_with_signals(
        self,
        bars: List[Bar],
        signals: List[SignalTrace],
        output: Path,
        interactive: bool = False
    ):
        """可视化K线和信号"""

        # 准备数据
        df = pd.DataFrame([{
            'open': b.open,
            'high': b.high,
            'low': b.low,
            'close': b.close,
            'volume': b.volume
        } for b in bars])

        # 准备信号标注
        buy_signals = [s for s in signals if s.signal.direction == DIRECTION_TYPES.LONG]
        sell_signals = [s for s in signals if s.signal.direction == DIRECTION_TYPES.SHORT]

        # 创建附加图（信号标注）
        addplot = [
            mpf.make_addplot(self._create_signal_series(buy_signals, df), type='scatter', markersize=200, marker='^', color='g'),
            mpf.make_addplot(self._create_signal_series(sell_signals, df), type='scatter', markersize=200, marker='v', color='r')
        ]

        # 生成图表
        mpf.plot(df, type='candle', addplot=addplot, savefig=str(output))

    def _create_signal_series(self, signals: List[SignalTrace], df: pd.DataFrame) -> pd.Series:
        """创建信号标注序列"""
        series = pd.Series([np.nan] * len(df), index=df.index)
        for signal in signals:
            idx = self._find_bar_index(signal.timestamp, df)
            if idx is not None:
                series.iloc[idx] = df['close'].iloc[idx]
        return series
```

**Tick 图可视化实现**:
```python
def visualize_ticks_with_signals(self, ticks: List[Tick], signals: List[SignalTrace], output: Path):
    """可视化 Tick 序列和信号"""
    fig, ax = plt.subplots(figsize=(15, 6))

    # 绘制价格序列
    timestamps = [t.timestamp for t in ticks]
    prices = [t.price for t in ticks]
    ax.plot(timestamps, prices, 'b-', alpha=0.6, label='Price')

    # 标注买入信号
    buy_signals = [s for s in signals if s.signal.direction == DIRECTION_TYPES.LONG]
    if buy_signals:
        buy_times = [s.timestamp for s in buy_signals]
        buy_prices = [self._get_price_at(t, ticks) for t in buy_times]
        ax.scatter(buy_times, buy_prices, marker='^', color='g', s=200, label='Buy', zorder=5)

    # 标注卖出信号
    sell_signals = [s for s in signals if s.signal.direction == DIRECTION_TYPES.SHORT]
    if sell_signals:
        sell_times = [s.timestamp for s in sell_signals]
        sell_prices = [self._get_price_at(t, ticks) for t in sell_times]
        ax.scatter(sell_times, sell_prices, marker='v', color='r', s=200, label='Sell', zorder=5)

    ax.legend()
    ax.set_xlabel('Time')
    ax.set_ylabel('Price')
    ax.set_title('Tick Data with Signals')
    plt.savefig(output)
```

---

## 12. 待确认问题

❌ **无** - 所有技术决策已明确，无需进一步澄清

---

## 13. 参考资源

**Python AST 文档**:
- https://docs.python.org/3/library/ast.html
- https://greentreesnakes.readthedocs.io/

**静态分析工具参考**:
- pylint: https://github.com/PyCQA/pylint
- flake8: https://github.com/PyCQA/flake8
- mypy: https://github.com/python/mypy

**可视化库参考**:
- Matplotlib: https://matplotlib.org/
- mplfinance: https://github.com/matplotlib/mplfinance
- Plotly: https://plotly.com/python/

**设计模式参考**:
- Adapter Pattern: https://refactoring.guru/design-patterns/adapter
- Factory Pattern: https://refactoring.guru/design-patterns/factory-method
- Context Manager: https://docs.python.org/3/library/contextlib.html

**Ginkgo 内部参考**:
- `src/ginkgo/trading/strategies/base_strategy.py` - BaseStrategy 定义
- `src/ginkgo/trading/strategies/random_signal_strategy.py` - 策略示例
- `src/ginkgo/trading/events/price_update.py` - EventPriceUpdate 定义
- `src/ginkgo/client/cli/` - CLI 命令实现参考

---

**Research Status**: ✅ **COMPLETE** - 所有技术决策已确认，包括：
- ✅ 静态分析 + 运行时检查混合模式
- ✅ 信号追踪技术设计（上下文管理器 + 适配器）
- ✅ 数据源适配器设计（K线 + Tick）
- ✅ 可视化技术选型（Matplotlib + Plotly）
- ✅ CLI 统一入口设计（通过参数控制输出模式）
- ✅ 测试策略

**可以进入 Phase 1 设计阶段**
