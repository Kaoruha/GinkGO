# Implementation Plan: Strategy Evaluation Module

**Branch**: `002-strategy-evaluation` | **Date**: 2025-12-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/002-strategy-evaluation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

构建一个策略评估模块，帮助策略开发者在回测前发现代码问题。主要功能包括：

1. **策略结构评估**（P1）：检查继承关系、方法签名、必需方法实现
2. **策略逻辑评估**（P2）：评估信号字段、参数使用、时间获取方式
3. **最佳实践检查**（P3）：装饰器使用、异常处理、日志记录
4. **信号追踪与可视化**（P2）：追踪运行时信号生成过程，可视化信号位置
5. **架构可扩展性**（P4）：支持评估多种组件类型（Strategy、Selector、Sizer、RiskManager）

技术方法：
- **静态分析**：使用 Python AST 模块解析策略代码，不执行代码
- **运行时检查**：使用 inspect 模块导入和实例化策略类进行评估
- **分层架构**：评估器层、规则层、报告层严格分离
- **单一评估器模式**：统一 `ComponentEvaluator` + 规则注册表支持多组件类型
- **Pipeline 模式**：灵活编排评估流程（静态分析 → 运行时检查 → 信号追踪）
- **CLI 接口**：`ginkgo eval strategy <file>` 支持 basic/standard/strict 三级评估
- **多格式报告**：text/json/markdown 三种输出格式
- **模板化报告**：使用 Jinja2 模板引擎，支持自定义报告格式
- **装饰器可视化**：ChartBuilder + Renderer + Decorator 三层分离

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: Typer (CLI), Rich (终端输出), AST (静态分析), inspect (运行时检查)
**Storage**: 主要无需数据库（本地文件验证），支持可选数据库策略加载（US5）
**Testing**: pytest with TDD workflow, unit/integration/database标记分类
**Target Platform**: Linux/MacOS/Windows (开发环境)
**Project Type**: single (Python量化交易库)
**Performance Goals**:
- 单策略文件验证 < 2秒 (SC-003)
- CLI 命令响应 < 1秒 (SC-007)
- 支持批量验证 >= 10 个策略文件 (SC-004)

**Constraints**:
- 必须支持动态加载用户策略文件（本地文件路径或数据库）
- 验证不能影响原有策略代码
- 数据库策略验证需要数据库连接（US5），本地文件验证不需要（US1-US4）

**Scale/Scope**:
- 支持验证单个策略文件或批量验证
- 处理文件大小：最多 2000 行代码
- 支持的验证级别：basic（结构）、standard（结构+逻辑）、strict（全部检查）

**Integration Points**:
- BaseStrategy 类：需要检查继承关系
- Signal 实体：需要验证字段完整性
- EventBase 体系：需要检查事件处理逻辑
- 现有 CLI 框架：需要集成到 ginkgo 命令

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查（N/A - 纯代码分析，无敏感信息）
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理（N/A - 无需访问）
- [x] 敏感配置文件已添加到.gitignore（N/A - 无敏感配置）

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构（评估模块本身不参与事件流，但评估策略是否符合事件驱动架构）
- [x] 使用ServiceHub统一访问服务（如需访问其他服务，使用service_hub）
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责（评估器层、规则层、报告层严格分离）

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器（FR-004要求）
- [x] 提供类型注解，支持静态类型检查（FR-005要求）
- [x] 禁止使用hasattr等反射机制回避类型错误（使用正确类型检查）
- [x] 遵循既定命名约定（validate_ 前缀，Rule/Report/Validator后缀）

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能（tasks.md已包含所有测试任务）
- [x] 测试按unit、integration/database标记分类（US5包含数据库测试）
- [x] 数据库测试使用测试数据库（US5数据库策略验证需要）

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法（N/A - 无数据库操作）
- [x] 合理使用多级缓存（AST解析结果可缓存）
- [x] 使用懒加载机制优化启动时间（按需加载策略文件）

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务（当前规划阶段）
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确（P1/P2/P3清晰划分）
- [x] 任务状态实时更新（通过TODO跟踪）

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文（spec.md和plan.md已使用中文）
- [x] 核心API提供详细使用示例和参数说明（待Phase 1生成API文档）
- [x] 重要组件有清晰的架构说明和设计理念文档（本plan.md和即将生成的research.md）

**Constitution Status**: ✅ **PASS** - 所有适用原则已通过，NA项已标注原因

## Project Structure

### Documentation (this feature)

```text
.specify/specs/002-strategy-validation/
├── plan.md              # 本文件
├── research.md          # Phase 0 输出（技术调研）
├── data-model.md        # Phase 1 输出（数据模型设计）
├── quickstart.md        # Phase 1 输出（快速开始指南）
├── contracts/           # Phase 1 输出（API契约）
│   ├── validation_api.yaml     # OpenAPI规范（如适用）
│   └── cli_interface.md        # CLI接口文档
└── tasks.md             # Phase 2 输出（任务分解，由/speckit.tasks生成）
```

### Source Code (repository root)

```text
# 策略评估模块代码结构
src/ginkgo/
├── trading/
│   ├── evaluation/                           # 评估模块（新增）
│   │   ├── __init__.py
│   │   ├── core/                             # 核心组件
│   │   │   ├── __init__.py
│   │   │   ├── component_type.py             # ComponentType 枚举（扩展）
│   │   │   ├── base_evaluator.py            # BaseEvaluator 抽象基类
│   │   │   ├── evaluation_result.py         # EvaluationResult 实体
│   │   │   └── enums.py                     # EvaluationLevel, EvaluationSeverity 枚举
│   │   ├── rules/                            # 评估规则层
│   │   │   ├── __init__.py
│   │   │   ├── base_rule.py                 # BaseRule 抽象基类
│   │   │   ├── rule_registry.py             # 规则注册表（扩展）
│   │   │   ├── structural_rules.py          # 结构评估规则（FR-011至FR-014）
│   │   │   ├── logical_rules.py             # 逻辑评估规则（FR-021至FR-024）
│   │   │   └── best_practice_rules.py       # 最佳实践规则（FR-031至FR-034）
│   │   ├── evaluators/                       # 评估器层
│   │   │   ├── __init__.py
│   │   │   ├── component_evaluator.py       # 统一组件评估器（扩展）
│   │   │   ├── structural_evaluator.py      # 结构评估器（P1）
│   │   │   ├── logical_evaluator.py         # 逻辑评估器（P2）
│   │   │   └── best_practice_evaluator.py   # 最佳实践评估器（P3）
│   │   ├── pipeline/                         # Pipeline 流水线（新增）
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py                  # EvaluationPipeline 主类
│   │   │   ├── stages/                      # Pipeline Stage
│   │   │   │   ├── static_analysis_stage.py
│   │   │   │   ├── runtime_inspection_stage.py
│   │   │   │   └── signal_tracing_stage.py
│   │   │   └── execution_strategy.py        # 执行策略（串行/并行）
│   │   ├── config/                           # 配置模块（新增）
│   │   │   ├── __init__.py
│   │   │   ├── config_loader.py             # YAML/JSON 配置加载
│   │   │   ├── evaluator_composer.py        # 评估器组装器
│   │   │   └── default_config.yaml          # 默认配置
│   │   ├── visualization/                    # 可视化模块（重构）
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── chart_builder.py         # 图表构建器
│   │   │   │   └── chart_config.py          # 图表配置
│   │   │   ├── renderers/                   # 渲染后端
│   │   │   │   ├── matplotlib_renderer.py
│   │   │   │   └── plotly_renderer.py
│   │   │   ├── decorators/                  # 装饰器
│   │   │   │   ├── signal_decorator.py
│   │   │   │   ├── indicator_decorator.py
│   │   │   │   └── annotation_decorator.py
│   │   │   └── charts/                      # 图表类型
│   │   │       ├── base_chart.py
│   │   │       ├── bar_chart.py
│   │   │       └── tick_chart.py
│   │   ├── reporting/                        # 报告模块（重构）
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   │   ├── report_data.py           # 报告数据模型
│   │   │   │   └── template_engine.py       # 模板引擎接口
│   │   │   ├── templates/                   # 报告模板
│   │   │   │   ├── text/
│   │   │   │   ├── json/
│   │   │   │   └── markdown/
│   │   │   ├── formatters/                  # 格式化器
│   │   │   │   ├── base_formatter.py
│   │   │   │   ├── rich_formatter.py
│   │   │   │   └── html_formatter.py
│   │   │   └── exporters/                   # 导出器
│   │   │       ├── file_exporter.py
│   │   │       ├── http_exporter.py
│   │   │       └── webhook_exporter.py
│   │   ├── analyzers/                        # 静态分析器
│   │   │   ├── __init__.py
│   │   │   ├── ast_analyzer.py              # AST静态分析器
│   │   │   └── runtime_analyzer.py          # 运行时分析器 + SignalTracer + 适配器
│   │   └── utils/                            # 工具函数
│   │       ├── __init__.py
│   │       ├── ast_helpers.py               # AST解析辅助函数
│   │       └── file_loader.py               # 动态文件加载器
│   └── strategies/
│       └── ...（现有策略文件）
│
├── client/
│   ├── cli/
│   │   ├── ...（现有CLI文件）
│   │   └── evaluation_cli.py                # 评估模块CLI命令（新增）
│   └── ...（其他客户端代码）
│
tests/
├── unit/trading/evaluation/                  # 单元测试（新增）
│   ├── test_core/
│   ├── test_rules/
│   ├── test_evaluators/
│   ├── test_pipeline/                       # Pipeline 测试（新增）
│   ├── test_visualization/                  # 可视化测试（重构）
│   ├── test_reporting/                      # 报告测试（重构）
│   ├── test_analyzers/
│   └── test_utils/
│
└── integration/trading/evaluation/           # 集成测试（新增）
    ├── test_evaluation_workflow.py
    ├── test_cli_integration.py
    └── fixtures/
        └── strategies/
```

**Structure Decision**:
- **核心架构**：采用 **统一评估器模式** + 规则注册表，支持多组件类型评估（FR-091, FR-092）
- **Pipeline 流水线**：支持灵活的评估流程编排（静态分析 → 运行时检查 → 信号追踪）
- **可视化分层**：ChartBuilder + Renderer + Decorator 三层分离，支持装饰器模式（FR-094）
- **报告模板化**：使用 Jinja2 模板引擎，数据和展示分离（FR-095）
- **配置驱动**：通过 YAML 配置文件定义规则集，支持继承和组合（FR-093）
- **CLI 集成**：在 `client/cli/evaluation_cli.py` 中实现统一的 `ginkgo eval strategy` 命令
- **完整测试覆盖**：unit 层测试各组件，integration 层测试完整工作流和 CLI 集成

## Phase Summary

### Phase 0: Research ✅ COMPLETE

**输出文档**: [research.md](./research.md)

**技术决策**:
- ✅ 混合评估模式：AST 静态分析 + inspect 运行时检查
- ✅ 信号追踪：上下文管理器 + 适配器模式
- ✅ 数据源适配器：支持 K线、Tick，可扩展到 OrderFlow
- ✅ 可视化：Matplotlib（静态）+ Plotly（交互式）

### Phase 1: Design ✅ COMPLETE

**输出文档**:
- ✅ [data-model.md](./data-model.md) - 完整的数据模型设计
- ✅ [quickstart.md](./quickstart.md) - 快速开始指南
- ✅ [contracts/cli_interface.md](./contracts/cli_interface.md) - CLI 接口文档

**设计成果**:
- ✅ 9 个核心实体（验证 + 追踪 + 适配器）
- ✅ 3 个 CLI 命令（validate、trace、visualize）
- ✅ 完整的工作流指南
- ✅ 与 Ginkgo 核心实体的集成关系

### Phase 2: Implementation (待执行)

**下一步**: 使用 `/speckit.tasks` 生成任务列表

**预期任务**:
1. 实现核心验证器（structural、logical、best_practice）
2. 实现信号追踪器（SignalTracer + 适配器）
3. 实现 CLI 命令（validate、trace、visualize）
4. 实现可视化组件（Matplotlib + Plotly）
5. 编写单元测试和集成测试

---

## 规划文件清单

```
.specify/specs/002-strategy-validation/
├── spec.md              # 功能规范 ✅
├── plan.md              # 本文件（实现计划） ✅
├── research.md          # 技术调研 ✅
├── data-model.md        # 数据模型 ✅
├── quickstart.md        # 快速开始 ✅
├── contracts/
│   └── cli_interface.md # CLI 接口 ✅
└── checklists/
    └── requirements.md  # 质量检查清单 ✅
```

---

## 核心设计原则

1. **快速验证优先**: 静态验证 < 2 秒，不需要运行完整回测
2. **灵活数据源**: 通过适配器模式支持多种数据源（K线、Tick、OrderFlow）
3. **直观可视化**: 在图表上标注信号位置，方便验证是否符合预期
4. **开发者友好**: 提供清晰的错误提示和修复建议
5. **架构可扩展**: 为未来支持其他组件类型评估奠定基础

---

## 架构扩展性设计 (P4 优先级)

### 1. 统一评估器模式

**设计目标**: 单一 `ComponentEvaluator` 类支持所有组件类型评估

```python
class ComponentEvaluator:
    """统一组件评估器"""

    # 规则注册表（按组件类型和评估级别组织）
    RULES_REGISTRY = {
        ComponentType.STRATEGY: {
            EvaluationLevel.BASIC: [
                BaseClassInheritanceRule(BaseStrategy),
                RequiredMethodRule("cal"),
            ],
            EvaluationLevel.STANDARD: [
                # ... Basic + 额外规则
            ],
        },
        ComponentType.SELECTOR: {
            EvaluationLevel.BASIC: [
                BaseClassInheritanceRule(BaseSelector),
                RequiredMethodRule("select_candidates"),
            ],
        },
        # ... RiskManager, Sizer
    }

    def evaluate(self, file_path: Path, component_type: ComponentType, level: EvaluationLevel):
        """统一的评估入口"""
        rules = self.RULES_REGISTRY[component_type][level]
        issues = [rule.check(file_path) for rule in rules]
        return EvaluationResult(issues=issues)
```

**扩展成本**: 添加新组件类型只需 3 步
1. 添加 `ComponentType` 枚举值
2. 定义规则集到 `RULES_REGISTRY`
3. CLI 自动支持（无需修改代码）

### 2. Pipeline 模式

**设计目标**: 支持灵活的评估流程编排

```python
class EvaluationPipeline:
    """评估流水线"""

    def __init__(self):
        self.stages = []

    def add_stage(self, stage: PipelineStage):
        """添加评估阶段"""
        self.stages.append(stage)
        return self

    def execute(self, context: EvaluationContext) -> EvaluationResult:
        """执行流水线"""
        result = EvaluationResult()
        for stage in self.stages:
            if stage.should_skip(context):
                continue
            stage_result = stage.execute(context)
            result.merge(stage_result)
            if stage.should_fail_fast() and not stage_result.passed:
                break
        return result

# 使用示例
pipeline = (EvaluationPipeline()
    .add_stage(StaticAnalysisStage())
    .add_stage(RuntimeInspectionStage())
    .add_stage(SignalTracingStage())  # 有数据时才执行
)
```

**扩展点**:
- 条件执行：`should_skip()` 根据上下文决定是否跳过
- 失败策略：`fail_fast`、`continue`、`collect_all`
- 并行执行：`ParallelPipelineStage` 多规则并行检查

### 3. 装饰器可视化架构

**设计目标**: 可视化模块支持装饰器模式，可组合多种图表装饰

```python
class ChartBuilder:
    """图表构建器"""

    def __init__(self):
        self.decorators = []

    def add_decorator(self, decorator: ChartDecorator):
        """添加装饰器"""
        self.decorators.append(decorator)
        return self

    def build(self, data: ChartData) -> Figure:
        """应用所有装饰器"""
        fig = self.renderer.create_figure(data)
        for decorator in self.decorators:
            fig = decorator.apply(fig, data)
        return fig

# 使用示例
chart = (ChartBuilder()
    .add_decorator(SignalDecorator(color='green', size=100))
    .add_decorator(MovingAverageDecorator(period=5, color='blue'))
    .add_decorator(BollingerBandsDecorator(period=20))
    .build(data)
)
```

**扩展点**:
- 新渲染后端：实现 `ChartRenderer` 接口（Echarts、Vega）
- 新图表类型：继承 `BaseChart`（VolumeChart、HeatmapChart）
- 新装饰器：实现 `ChartDecorator` 接口（SupportLevel、PnL）

### 4. 模板化报告系统

**设计目标**: 支持自定义报告模板和多渠道导出

```python
class TemplateReporter(BaseReporter):
    """模板驱动的报告器"""

    def __init__(self, template_path: str):
        self.template = self._load_template(template_path)

    def generate(self, result: EvaluationResult) -> str:
        return self.template.render(
            file=result.file,
            level=result.level,
            issues=result.issues,
            # ... 数据和展示分离
        )
```

**模板示例**（validation.txt.j2）:
```jinja2
╭──────────────────────────────────────────────────────────╮
│           Strategy Evaluation Report                     │
╰──────────────────────────────────────────────────────────╯

File: {{ file }}
Level: {{ level }}
Result: {% if passed %}✅ PASSED{% else %}❌ FAILED{% endif %}

{% for issue in issues %}
{{ issue.severity }}: {{ issue.message }}
{% endfor %}
```

**扩展点**:
- 新输出格式：添加模板文件（HTML、PDF、XML）
- 自定义样式：修改模板（公司品牌模板）
- 多渠道分发：实现 `Exporter`（邮件、Slack、Webhook）
- 国际化：多语言模板（en_US、zh_CN）

### 5. 配置文件驱动

**设计目标**: 通过 YAML 配置文件定义评估规则集和级别

```yaml
# evaluation_config.yaml
evaluators:
  strategy_basic:
    level: basic
    rules:
      - base_inheritance
      - cal_method_required

  strategy_standard:
    level: standard
    rules:
      - strategy_basic  # 继承 basic
      - cal_signature
      - signal_fields

rules:
  base_inheritance:
    class: BaseStrategyInheritanceRule
    severity: error
    enabled: true
```

**扩展成本**:
- 修改规则集：编辑 YAML 文件
- 自定义评估流程：组装不同阶段
- 环境差异化配置：dev/staging/prod 不同规则

---

## 下一步行动

**推荐执行顺序**:

1. **立即可做**: 使用 `/speckit.tasks` 生成详细任务列表
2. **实现优先级**:
   - P0: 静态验证（structural_validator）
   - P1: 信号追踪（SignalTracer + K线适配器）
   - P2: 可视化（Matplotlib K线图）
   - P3: 最佳实践检查、其他适配器

3. **第一个任务**: 实现 BaseValidator 抽象类和 StructuralValidator

---

**Planning Status**: ✅ **COMPLETE** - 所有设计文档已完成，可以进入实现阶段
