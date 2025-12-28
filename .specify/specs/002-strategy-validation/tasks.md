# Tasks: Strategy Validation Module

**Input**: Design documents from `/specs/002-strategy-evaluation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/cli_interface.md ✅

**Tests**: Per plan.md section "测试原则", tests should follow TDD workflow with unit/integration markers. Test tasks are included in this implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each validation capability.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Source code**: `src/ginkgo/` at repository root
- **Tests**: `tests/` at repository root
- **CLI**: `src/ginkgo/client/cli/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic module structure

- [X] T001 Create validation module directory structure in src/ginkgo/trading/evaluation/
- [X] T002 [P] Create __init__.py files for validation subdirectories (core, rules, evaluators, analyzers, reporters, utils)
- [X] T003 [P] Create test directory structure tests/unit/trading/evaluation/ and tests/integration/trading/evaluation/
- [X] T004 [P] Create test fixture strategies in tests/integration/trading/evaluation/fixtures/strategies/
- [X] T005 Install validation dependencies if needed (AST, inspect are built-in; verify Rich, Typer versions)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Core Enums and Result Entity

- [X] T006 [P] Create EvaluationLevel enum (BASIC, STANDARD, STRICT) in src/ginkgo/trading/evaluation/core/enums.py
- [X] T007 [P] Create EvaluationSeverity enum (ERROR, WARNING, INFO) in src/ginkgo/trading/evaluation/core/enums.py
- [X] T008 [P] Create ValidationIssue entity in src/ginkgo/trading/evaluation/core/evaluation_result.py (rule_id, severity, line, column, message, suggestion, code_snippet)
- [X] T009 [P] Create EvaluationResult entity in src/ginkgo/trading/evaluation/core/evaluation_result.py (strategy_file, strategy_name, level, passed, errors, warnings, suggestions, duration_ms)

### Base Classes for Three-Layer Architecture

- [X] T010 Create BaseRule abstract class in src/ginkgo/trading/evaluation/rules/base_rule.py (can_apply, validate, severity, level properties)
- [X] T011 Create BaseEvaluator abstract class in src/ginkgo/trading/evaluation/evaluators/base_evaluator.py (validate interface)
- [X] T012 Create BaseReporter abstract class in src/ginkgo/trading/evaluation/reporters/base_reporter.py (generate interface) ✅ 完成于 2025-12-28

### Utility Infrastructure

- [X] T013 Create AST helper utilities in src/ginkgo/trading/evaluation/utils/ast_helpers.py (parse_file, find_class_def, find_method_def) ✅ 完成于 2025-12-28
- [X] T014 Create file loader utility in src/ginkgo/trading/evaluation/utils/file_loader.py (load_strategy_class, safe_import) - Note: Integrated into SimpleEvaluator

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 策略结构验证 (Priority: P1) 🎯 MVP

**Goal**: 快速发现编写的策略类是否存在结构性问题（继承、方法签名、必需参数）

**Independent Test**: 创建一个缺少 `cal()` 方法的策略文件，运行 `ginkgo validate strategy invalid.py --level basic`，应报告"缺少必需的 cal() 方法"错误

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T015 [P] [US1] Create unit test with @pytest.mark.unit decorator for BaseStrategy inheritance check in tests/unit/trading/evaluation/test_rules/test_structural_rules.py::test_base_strategy_inheritance_rule
- [X] T016 [P] [US1] Create unit test with @pytest.mark.unit decorator for cal() method signature check in tests/unit/trading/evaluation/test_rules/test_structural_rules.py::test_cal_method_signature_rule
- [X] T017 [P] [US1] Create unit test with @pytest.mark.unit decorator for __abstract__ = False check in tests/unit/trading/evaluation/test_rules/test_structural_rules.py::test_abstract_marker_rule
- [X] T018 [P] [US1] Create integration test with @pytest.mark.integration decorator for basic validation workflow in tests/integration/trading/evaluation/test_validation_workflow.py::test_basic_structural_validation

### Implementation for User Story 1

**验证规则层 (Rules)**:
- [X] T019 [P] [US1] Implement BaseStrategyInheritanceRule in src/ginkgo/trading/evaluation/rules/structural_rules.py (checks class inherits from BaseStrategy)
- [X] T020 [P] [US1] Implement CalMethodSignatureRule in src/ginkgo/trading/evaluation/rules/structural_rules.py (checks cal() method signature matches required pattern)
- [X] T021 [P] [US1] Implement SuperInitCallRule in src/ginkgo/trading/evaluation/rules/structural_rules.py (checks __init__ calls super().__init__())
- [X] T022 [P] [US1] Implement AbstractMarkerRule in src/ginkgo/trading/evaluation/rules/structural_rules.py (checks __abstract__ = False is set) ✅ 完成于 2025-12-28

**验证器层 (Validator)**:
- [X] T023 [US1] Implement StructuralValidator in src/ginkgo/trading/evaluation/evaluators/base_evaluator.py (uses all structural rules, returns EvaluationResult) - Note: Implemented as SimpleEvaluator
- [X] T024 [US1] Add @time_logger decorator to StructuralValidator.validate() method ✅ 完成于 2025-12-28
- [X] T025 [US1] Add AST-based class analysis in src/ginkgo/trading/evaluation/analyzers/ast_analyzer.py (extract class structure, methods, decorators) ✅ 完成于 2025-12-28

**报告层 (Reporters)**:
- [X] T026 [P] [US1] Implement TextReporter in src/ginkgo/trading/evaluation/reporters/text_reporter.py (Rich-formatted console output) ✅ 完成于 2025-12-28
- [X] T027 [P] [US1] Implement JsonReporter in src/ginkgo/trading/evaluation/reporters/json_reporter.py (JSON format output) ✅ 完成于 2025-12-28
- [X] T028 [P] [US1] Implement MarkdownReporter in src/ginkgo/trading/evaluation/reporters/markdown_reporter.py (Markdown format output) ✅ 完成于 2025-12-28

**CLI集成**:
- [X] T029 [US1] Implement basic `ginkgo validate strategy` command in src/ginkgo/client/validation_cli.py (strategy_file argument, --level option, --show-context option)
- [X] T030 [US1] Integrate validation CLI with main ginkgo CLI (add validate subcommand to existing CLI structure)
- [X] T031 [US1] Add error handling and user-friendly error messages for file not found, syntax errors, import errors

**质量保证**:
- [X] T032 [US1] Add comprehensive error handling with proper exception types in evaluation_cli.py ✅ 完成于 2025-12-28
- [X] T033 [US1] Add structured logging with GLOG for validation operations ✅ 完成于 2025-12-28
- [X] T034 [US1] Add input validation (file exists check, .py extension check) ✅ 完成于 2025-12-28
- [X] T090 [P] [US1] 性能基准测试 - verify validation < 2s per SC-003 requirement (ensure structural validation meets performance target) ✅ 完成于 2025-12-28

**Checkpoint**: At this point, User Story 1 should be fully functional - running `ginkgo validate strategy my_strategy.py --level basic` should report structural errors in < 2 seconds

---

## Phase 4: User Story 2 - 策略逻辑验证 (Priority: P2)

**Goal**: 验证策略的业务逻辑是否符合框架要求（Signal字段、参数使用、时间获取）

**Independent Test**: 创建一个返回缺少 code 字段的 Signal 的策略，运行 `ginkgo validate strategy --level standard`，应报告"Signal must contain code field"错误

### Tests for User Story 2 ⚠️

- [X] T035 [P] [US2] Create unit test with @pytest.mark.unit decorator for Signal field validation in tests/unit/trading/evaluation/test_rules/test_logical_rules.py::test_signal_field_rule
- [X] T036 [P] [US2] Create unit test with @pytest.mark.unit decorator for direction validation in tests/unit/trading/evaluation/test_rules/test_logical_rules.py::test_direction_validation_rule
- [X] T037 [P] [US2] Create unit test with @pytest.mark.unit decorator for TimeProvider usage check in tests/unit/trading/evaluation/test_rules/test_logical_rules.py::test_time_provider_usage_rule
- [X] T038 [P] [US2] Create integration test with @pytest.mark.integration decorator for standard validation workflow in tests/integration/trading/evaluation/test_validation_workflow.py::test_standard_logical_validation ✅ 完成于 2025-12-28

### Implementation for User Story 2

**验证规则层 (Rules)**:
- [X] T039 [P] [US2] Implement ReturnStatementRule in src/ginkgo/trading/evaluation/rules/logical_rules.py (checks cal() returns List[Signal])
- [X] T040 [P] [US2] Implement SignalFieldRule in src/ginkgo/trading/evaluation/rules/logical_rules.py (checks Signal has code, direction, reason)
- [X] T041 [P] [US2] Implement SignalParameterRule in src/ginkgo/trading/evaluation/rules/logical_rules.py (checks Signal uses business_timestamp, not timestamp) ✅ 完成于 2025-12-29
- [X] T042 [P] [US2] Implement DirectionValidationRule in src/ginkgo/trading/evaluation/rules/logical_rules.py (checks direction is valid DIRECTION_TYPES)
- [X] T043 [P] [US2] Implement TimeProviderUsageRule in src/ginkgo/trading/evaluation/rules/logical_rules.py (checks uses self.get_time_provider() not datetime.now())
- [X] T044 [P] [US2] Implement ForbiddenOperationsRule in src/ginkgo/trading/evaluation/rules/logical_rules.py (detects database queries, network calls in cal())

**验证器层 (Validator)**:
- [X] T045 [US2] Implement LogicalValidator in src/ginkgo/trading/evaluation/validators/logical_evaluator.py (uses all logical rules, requires runtime inspection) ✅ 完成于 2025-12-28
- [X] T046 [US2] Add runtime analysis capability in src/ginkgo/trading/evaluation/analyzers/runtime_analyzer.py (inspect strategy class, instantiate safely) ✅ 完成于 2025-12-28
- [X] T047 [US2] Add @time_logger decorator to LogicalValidator.validate() method ✅ 完成于 2025-12-28

**CLI增强**:
- [X] T048 [US2] Extend CLI to support --level standard (combines structural + logical validation)
- [X] T049 [US2] Add --format option (text/json/markdown) to validation CLI ✅ 完成于 2025-12-28
- [X] T050 [US2] Add --output option to save report to file in evaluation_cli.py ✅ 完成于 2025-12-28

**Checkpoint**: User Stories 1 AND 2 should both work independently - `ginkgo validate strategy --level standard` validates structure + logic

---

## Phase 5: User Story 4 - 信号生成追踪与可视化 (Priority: P2)

**Goal**: 追踪策略运行时的信号生成过程，可视化信号位置

**Independent Test**: 提供测试数据 CSV 和策略，运行 `ginkgo validate strategy --data test.csv --show-trace`，应显示信号列表和生成原因

### Tests for User Story 4 ⚠️

- [ ] T060 [P] [US4] Create unit test with @pytest.mark.unit decorator for SignalTracer context manager in tests/unit/trading/evaluation/test_analyzers/test_runtime_analyzer.py::test_signal_tracer_context
- [ ] T060 [P] [US4] Create unit test with @pytest.mark.unit decorator for BarDataAdapter in tests/unit/trading/evaluation/test_analyzers/test_runtime_analyzer.py::test_bar_data_adapter
- [ ] T060 [P] [US4] Create unit test with @pytest.mark.unit decorator for TickDataAdapter in tests/unit/trading/evaluation/test_analyzers/test_runtime_analyzer.py::test_tick_data_adapter
- [ ] T060 [P] [US4] Create integration test with @pytest.mark.integration decorator for signal tracing workflow in tests/integration/trading/evaluation/test_validation_workflow.py::test_signal_tracing_with_data

### Implementation for User Story 4

**数据模型**:
- [X] T060 [P] [US4] Create SignalTrace entity in src/ginkgo/trading/evaluation/core/evaluation_result.py (trace_id, timestamp, input_context, signal, signal_info, strategy_state)
- [X] T060 [P] [US4] Create SignalTraceReport entity in src/ginkgo/trading/evaluation/core/evaluation_result.py (strategy_name, traces, start_time, end_time, signal_count, buy_count, sell_count)

**适配器层 (Adapters)**:
- [X] T060 [P] [US4] Create DataSourceAdapter interface in src/ginkgo/trading/evaluation/analyzers/runtime_analyzer.py (get_visualization_data, format_signal_info, get_data_summary)
- [X] T060 [P] [US4] Implement BarDataAdapter in src/ginkgo/trading/evaluation/analyzers/runtime_analyzer.py (handles EventPriceUpdate, extracts OHLCV data)
- [X] T060 [P] [US4] Implement TickDataAdapter in src/ginkgo/trading/evaluation/analyzers/runtime_analyzer.py (handles EventTickUpdate, extracts price/volume)
- [X] T060 [P] [US4] Implement AdapterFactory in src/ginkgo/trading/evaluation/analyzers/runtime_analyzer.py (auto-select adapter by event type)

**追踪器层 (Tracer)**:
- [X] T060 [US4] Implement SignalTracer in src/ginkgo/trading/evaluation/analyzers/runtime_analyzer.py (context manager, wraps cal(), records signals)
- [X] T061 [US4] Add trace report generation (export to JSON/CSV/Markdown) in SignalTraceReport
- [X] T062 [US4] Add @time_logger decorator to SignalTracer methods (start_tracing, _trace_wrapper, stop_tracing, finalize, get_report)

**可视化层 (Visualizer)**:
- [X] T063 [P] [US4] Implement SignalVisualizer in src/ginkgo/trading/evaluation/reporters/html_visualizer.py (generates HTML chart with signal markers)
- [X] T064 [P] [US4] Implement K线图生成 using Lightweight Charts (HTML) in HTMLSignalVisualizer ✅ 完成于 2025-12-28
- [X] T065 [P] [US4] Implement Tick 序列图生成 using Chart.js (HTML) in HTMLSignalVisualizer
- [X] T066 [P] [US4] Add signal markers (buy ▲ green, sell ▼ red) on charts in HTMLSignalVisualizer ✅ 完成于 2025-12-28
- [X] T067 [P] [US4] Implement chart output to HTML format in HTMLSignalVisualizer (standalone HTML with embedded Lightweight Charts) ✅ 完成于 2025-12-28

**CLI增强**:
- [X] T068 [US4] Add --data option to load test data (CSV/JSON) in validation_cli.py
- [X] T069 [US4] Add --show-trace option to enable signal tracing in validation_cli.py
- [X] T070 [US4] Add --visualize option to generate HTML charts in validation_cli.py (with --output option)
- [X] T071 [US4] Add --events option to control number of events to process in validation_cli.py
- [X] T072 [US4] Implement data loader for CSV/JSON test data in validation_cli.py

**Checkpoint**: User Story 4 adds tracing and visualization - `ginkgo validate strategy --show-trace --visualize --output chart.html` works ✅

---

## Phase 6: User Story 3 - 策略最佳实践检查 (Priority: P3)

**Goal**: 获得代码质量建议，编写更符合最佳实践的策略代码

**Independent Test**: 创建一个没有装饰器和异常处理的策略，运行 `ginkgo validate strategy --level strict`，应建议添加 @time_logger 和 try-except

### Tests for User Story 3 ⚠️

- [X] T073 [P] [US3] Create unit test with @pytest.mark.unit decorator for decorator usage check in tests/unit/trading/evaluation/test_rules/test_best_practice_rules.py::test_decorator_usage_rule ✅ 完成于 2025-12-28
- [X] T074 [P] [US3] Create unit test with @pytest.mark.unit decorator for exception handling check in tests/unit/trading/evaluation/test_rules/test_best_practice_rules.py::test_exception_handling_rule ✅ 完成于 2025-12-28
- [X] T075 [P] [US3] Create unit test with @pytest.mark.unit decorator for logging check in tests/unit/trading/evaluation/test_rules/test_best_practice_rules.py::test_logging_rule ✅ 完成于 2025-12-28
- [X] T076 [P] [US3] Create integration test with @pytest.mark.integration decorator for strict validation workflow in tests/integration/trading/evaluation/test_validation_workflow.py::test_strict_best_practice_validation ✅ 完成于 2025-12-28

### Implementation for User Story 3

**验证规则层 (Rules)**:
- [X] T077 [P] [US3] Implement DecoratorUsageRule in src/ginkgo/trading/evaluation/rules/best_practice_rules.py (checks for @time_logger, @retry) ✅ 完成于 2025-12-28
- [X] T078 [P] [US3] Implement ExceptionHandlingRule in src/ginkgo/trading/evaluation/rules/best_practice_rules.py (checks for try-except blocks) ✅ 完成于 2025-12-28
- [X] T079 [P] [US3] Implement LoggingRule in src/ginkgo.trading/evaluation/rules/best_practice_rules.py (checks for GLOG usage) ✅ 完成于 2025-12-28
- [X] T080 [P] [US3] Implement ResetStateRule in src/ginkgo/trading/evaluation/rules/best_practice_rules.py (checks reset_state() calls super()) ✅ 完成于 2025-12-28
- [X] T081 [P] [US3] Implement ParameterValidationRule in src/ginkgo/trading/evaluation/rules/best_practice_rules.py (checks input parameter validation) ✅ 完成于 2025-12-28

**验证器层 (Validator)**:
- [X] T082 [US3] Implement BestPracticeValidator in src/ginkgo/trading/evaluation/validators/best_practice_evaluator.py (uses all best practice rules) ✅ 完成于 2025-12-28
- [X] T083 [US3] Add @time_logger decorator to BestPracticeValidator.validate() method ✅ 完成于 2025-12-28

**CLI增强**:
- [X] T084 [US3] Extend CLI to support --level strict (combines structural + logical + best practice validation) ✅ 完成于 2025-12-28
- [X] T085 [US3] Add --verbose option for detailed suggestions in evaluation_cli.py ✅ 完成于 2025-12-28

**Checkpoint**: All user stories complete - `ginkgo validate strategy --level strict --verbose` provides comprehensive analysis

---

## Phase 6.5: User Story 5 - 数据库策略验证 (Priority: P1)

**Goal**: 支持验证存储在数据库中的策略代码，与本地文件验证功能完全相同

**Independent Test**: 插入测试策略到数据库，使用 `--file-id` 验证，检查临时文件是否被自动清理

### Tests for User Story 5 ⚠️

- [X] T097 [P] [US5] Create unit test with @pytest.mark.unit decorator for DatabaseStrategyLoader.load_by_file_id() in tests/unit/trading/evaluation/test_utils/test_database_loader.py::test_load_by_file_id ✅ 完成于 2025-12-28
- [X] T098 [P] [US5] Create unit test with @pytest.mark.unit decorator for DatabaseStrategyLoader.load_by_portfolio_id() in tests/unit/trading/evaluation/test_utils/test_database_loader.py::test_load_by_portfolio_id ✅ 完成于 2025-12-28
- [X] T099 [P] [US5] Create unit test with @pytest.mark.unit decorator for temporary file cleanup in tests/unit/trading/evaluation/test_utils/test_database_loader.py::test_temp_file_cleanup ✅ 完成于 2025-12-28
- [X] T101 [P] [US5] Create integration test with @pytest.mark.integration decorator for database strategy validation workflow in tests/integration/trading/evaluation/test_validation_workflow.py::test_database_strategy_validation ✅ 完成于 2025-12-28

### Implementation for User Story 5

**工具层 (Utils)**:
- [X] T102 [US5] Create DatabaseStrategyLoader in src/ginkgo/trading/evaluation/utils/database_loader.py ✅ 完成于 2025-12-28
  - `load_by_file_id(file_id: str) -> str`: Load strategy from MFile table, return temp file path
  - `load_by_portfolio_id(portfolio_id: str) -> str`: Load strategy via PortfolioFileMapping
  - `list_strategies(name_filter: str = None) -> List[Dict]`: List all strategies in database
  - Use `contextlib.contextmanager` for automatic temp file cleanup
  - Decode MFile.data (MEDIUMBLOB) with UTF-8
  - Handle errors: file not found, invalid portfolio_id, decode errors

**CLI 增强**:
- [X] T103 [US5] Add `--file-id` parameter to evaluation_cli.py (mutually exclusive with strategy_file) ✅ 完成于 2025-12-28
- [X] T104 [US5] Add `--portfolio-id` parameter to evaluation_cli.py ✅ 完成于 2025-12-28
- [X] T105 [US5] Add `--list` parameter to show database strategies in Rich table format ✅ 完成于 2025-12-28
- [X] T106 [US5] Add `--all` parameter for batch validation of all database strategies ✅ 完成于 2025-12-28
- [X] T107 [US5] Add `--filter` parameter for name filtering (works with --list and --all) ✅ 完成于 2025-12-28
- [X] T108 [US5] Update CLI to use DatabaseStrategyLoader when --file-id or --portfolio-id is provided ✅ 完成于 2025-12-28
- [X] T109 [US5] Ensure temp file cleanup happens in finally block (even on validation errors) ✅ 完成于 2025-12-28

**集成验证**:
- [X] T110 [US5] Verify database strategy validation works with --show-trace (same as local file) ✅ 完成于 2025-12-28
- [X] T111 [US5] Verify database strategy validation works with --visualize (same as local file) ✅ 完成于 2025-12-28
- [X] T112 [US5] Add "Source: Database (file_id: ...)" to validation report output ✅ 完成于 2025-12-28
- [X] T113 [US5] Add temp file path to verbose output (marked as "auto-cleaned") ✅ 完成于 2025-12-28

**Checkpoint**: `ginkgo validate strategy --file-id <uuid> --show-trace --visualize` works identically to local file validation, with automatic temp file cleanup

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### 质量保证任务

- [ ] T086 [P] TDD流程验证 - ensure all tests pass with pytest -m unit and pytest -m integration
- [ ] T087 [P] 代码质量检查 - verify type annotations on all public methods
- [ ] T088 [P] 命名规范检查 - verify validate_ prefix, Rule/Validator/Reporter suffixes
- [ ] T089 [P] 装饰器检查 - verify @time_logger, @retry on appropriate methods

### 性能优化任务

**Note**: T090 (性能基准测试) 已移至 Phase 3 作为 US1 完成检查点的一部分

- [X] T091 [P] Add AST parsing cache in base_evaluator.py for performance optimization ✅ 完成于 2025-12-28
- [X] T093 [P] Lazy loading optimization - only load component class when RuntimeRule exists ✅ 完成于 2025-12-28

### 测试增强任务

- [ ] T094 [P] Add edge case tests in tests/unit/trading/evaluation/: syntax errors, import failures, multiple classes per file
- [ ] T095 [P] Add CLI integration tests in tests/integration/trading/evaluation/test_cli_integration.py
- [ ] T096 [P] Create comprehensive test strategy fixtures (valid_strategy.py, invalid_structure.py, invalid_logic.py, best_practice_strategy.py)

### 文档和维护任务

- [ ] T097 Run quickstart.md validation with debug mode enabled to verify all examples work
- [ ] T098 Update spec.md with any implementation discoveries or adjustments
- [ ] T099 Code cleanup and refactoring - remove any temporary/debug code
- [ ] T101 [P] Security check - ensure no sensitive file paths or credentials in error messages

---

## Phase 8: User Story 6 - 架构可扩展性 (Priority: P4 - Optional)

**Goal**: 实现可扩展架构，支持评估多种组件类型（Strategy、Selector、Sizer、RiskManager）

**Independent Test**: 创建 RiskManager 评估规则配置，验证 `ginkgo eval risk_manager my_risk.py` 可以工作

**Note**: 本阶段为可选扩展功能，不阻塞 MVP 交付。可在 US1-US5 完成后根据需要实现。

### Tests for User Story 6 ⚠️

- [ ] T121 [P] [US6] Create unit test with @pytest.mark.unit decorator for ComponentEvaluator in tests/unit/trading/evaluation/test_evaluators/test_component_evaluator.py::test_unified_evaluator
- [ ] T122 [P] [US6] Create unit test with @pytest.mark.unit decorator for RuleRegistry in tests/unit/trading/evaluation/test_rules/test_rule_registry.py::test_rule_registration
- [ ] T123 [P] [US6] Create unit test with @pytest.mark.unit decorator for EvaluationPipeline in tests/unit/trading/evaluation/test_pipeline/test_pipeline.py::test_pipeline_stages
- [ ] T124 [P] [US6] Create unit test with @pytest.mark.unit decorator for ChartBuilder decorators in tests/unit/trading/evaluation/test_visualization/test_chart_builder.py::test_decorator_composition
- [ ] T125 [P] [US6] Create integration test with @pytest.mark.integration decorator for multi-component evaluation in tests/integration/trading/evaluation/test_validation_workflow.py::test_risk_manager_evaluation

### Implementation for User Story 6

**核心架构层**:
- [ ] T126 [US6] Create ComponentType enum in src/ginkgo/trading/evaluation/core/component_type.py (STRATEGY, SELECTOR, SIZER, RISK_MANAGER)
- [ ] T127 [US6] Create ComponentEvaluator in src/ginkgo/trading/evaluation/evaluators/component_evaluator.py
  - `RULES_REGISTRY` class attribute for organizing rules by component type and level
  - `evaluate(file_path, component_type, level)` unified evaluation method
  - Support dynamic rule registration via class methods
- [ ] T128 [US6] Create RuleRegistry in src/ginkgo/trading/evaluation/rules/rule_registry.py
  - `register(component_type, level, rule)` method for adding rules dynamically
  - `get_rules(component_type, level)` method for retrieving rule sets
  - Support rule inheritance (basic → standard → strict)

**Pipeline 流水线**:
- [ ] T129 [P] [US6] Create PipelineStage interface in src/ginkgo/trading/evaluation/pipeline/stages/base_stage.py
- [ ] T130 [P] [US6] Create StaticAnalysisStage in src/ginkgo/trading/evaluation/pipeline/stages/static_analysis_stage.py
- [ ] T131 [P] [US6] Create RuntimeInspectionStage in src/ginkgo/trading/evaluation/pipeline/stages/runtime_inspection_stage.py
- [ ] T132 [P] [US6] Create SignalTracingStage in src/ginkgo/trading/evaluation/pipeline/stages/signal_tracing_stage.py
- [ ] T133 [US6] Create EvaluationPipeline in src/ginkgo/trading/evaluation/pipeline/pipeline.py
  - `add_stage(stage)` method for building pipeline
  - `execute(context)` method with fail_fast and skip logic
  - Support parallel execution with `ParallelPipelineStage`

**可视化模块重构**:
- [ ] T134 [P] [US6] Create ChartBuilder in src/ginkgo/trading/evaluation/visualization/core/chart_builder.py
  - `add_decorator(decorator)` method for composition
  - `build(data)` method applying all decorators
  - `set_renderer(renderer)` method for switching backends
- [ ] T135 [P] [US6] Create ChartRenderer interface in src/ginkgo/trading/evaluation/visualization/renderers/base_renderer.py
- [ ] T136 [P] [US6] Implement MatplotlibRenderer in src/ginkgo/trading/evaluation/visualization/renderers/matplotlib_renderer.py
- [ ] T137 [P] [US6] Implement PlotlyRenderer in src/ginkgo/trading/evaluation/visualization/renderers/plotly_renderer.py
- [ ] T138 [P] [US6] Create SignalDecorator in src/ginkgo/trading/evaluation/visualization/decorators/signal_decorator.py
- [ ] T139 [P] [US6] Create IndicatorDecorator in src/ginkgo/trading/evaluation/visualization/decorators/indicator_decorator.py
- [ ] T140 [P] [US6] Create AnnotationDecorator in src/ginkgo/trading/evaluation/visualization/decorators/annotation_decorator.py

**报告模块重构**:
- [ ] T141 [P] [US6] Create TemplateEngine interface in src/ginkgo/trading/evaluation/reporting/core/template_engine.py
- [ ] T142 [P] [US6] Implement Jinja2TemplateEngine in src/ginkgo/trading/evaluation/reporting/core/template_engine.py
- [ ] T143 [P] [US6] Create report templates in src/ginkgo/trading/evaluation/reporting/templates/
  - `text/validation.txt.j2` for text format
  - `json/validation.json.j2` for JSON format
  - `markdown/validation.md.j2` for Markdown format
- [ ] T144 [P] [US6] Refactor existing reporters to use template engine in src/ginkgo/trading/evaluation/reporting/formatters/
- [ ] T145 [P] [US6] Create FileExporter in src/ginkgo/trading/evaluation/reporting/exporters/file_exporter.py

**配置模块**:
- [ ] T146 [US6] Create ConfigLoader in src/ginkgo/trading/evaluation/config/config_loader.py (YAML/JSON parsing)
- [ ] T147 [US6] Create EvaluatorComposer in src/ginkgo/trading/evaluation/config/evaluator_composer.py
  - `compose(config_dict)` method for building evaluators from config
  - Support rule inheritance and composition
- [ ] T148 [US6] Create default_config.yaml in src/ginkgo/trading/evaluation/config/
  - Define strategy_basic, strategy_standard, strategy_strict evaluators
  - Define rule configurations (class, severity, enabled)

**CLI 扩展**:
- [ ] T149 [US6] Extend CLI to support `ginkgo eval <component_type> <source>` syntax
- [ ] T150 [US6] Add `--config` option to load custom evaluation configuration
- [ ] T151 [US6] Update CLI to use ComponentEvaluator for all component types

**其他组件类型规则**:
- [ ] T152 [P] [US6] Implement BaseSelector rules in ComponentEvaluator.RULES_REGISTRY
- [ ] T153 [P] [US6] Implement BaseSizer rules in ComponentEvaluator.RULES_REGISTRY
- [ ] T154 [P] [US6] Implement BaseRiskManagement rules in ComponentEvaluator.RULES_REGISTRY

**Checkpoint**: `ginkgo eval risk_manager my_risk.py --level standard` works using unified ComponentEvaluator, and `ginkgo validate strategy my_strategy.py --config custom_config.yaml` allows custom evaluation configurations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6.5)**: All depend on Foundational phase completion
  - **US1 (P1)**: Can start after Foundational - No dependencies on other stories
  - **US2 (P2)**: Can start after Foundational - Extends US1 but independently testable
  - **US4 (P2)**: Can start after Foundational - Independent of US1/US2, adds new capabilities
  - **US3 (P3)**: Can start after Foundational - Extends US1+US2 but independently testable
  - **US5 (P1)**: Can start after Foundational - Independent of other stories (database loading)
- **Polish (Phase 7)**: Depends on all desired user stories being complete
- **Architecture Extensibility (Phase 8)**: **OPTIONAL** - Depends on US1-US5 completion, extends architecture for future needs

### Recommended Implementation Order

**Sequential MVP Approach**:
1. Complete Setup (Phase 1) → Foundation ready
2. Complete Foundational (Phase 2) → Core infrastructure ready
3. Complete US1 (Phase 3) → **MVP COMPLETE** - basic structural validation works
4. Complete US5 (Phase 6.5) → database strategy validation
5. Complete US2 (Phase 4) → standard validation (structure + logic)
6. Complete US4 (Phase 5) → signal tracing and visualization
7. Complete US3 (Phase 6) → strict validation (all checks)
8. Complete Polish (Phase 7) → **PRODUCTION READY**
9. **OPTIONAL**: Complete US6 (Phase 8) → architecture extensibility for multi-component evaluation

**Parallel Team Strategy** (if multiple developers):
1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - **Developer A**: US1 (P1) - Structural validation
   - **Developer B**: US2 (P2) - Logical validation
   - **Developer C**: US4 (P2) - Signal tracing and visualization
3. After P1/P2 complete:
   - **Developer A**: US3 (P3) - Best practice checks

### Within Each User Story

- Tests MUST be written first and FAIL before implementation (TDD)
- Rules before Validators
- Validators before Reporters
- Core implementation before CLI integration
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T002, T003, T004, T005 can all run in parallel

**Foundational Phase (Phase 2)**:
- T006, T007, T008, T009 can run in parallel (enums and entities)
- T010, T011, T012 can run in parallel (base classes)
- T013, T014 can run in parallel (utilities)

**User Story 1 (Phase 3)**:
- All tests (T015-T018) run in parallel
- All rules (T019-T022) run in parallel
- All reporters (T026-T028) run in parallel

**User Story 2 (Phase 4)**:
- All tests (T035-T038) run in parallel
- All rules (T039-T043) run in parallel

**User Story 4 (Phase 5)**:
- T054, T055 (entities) run in parallel
- All adapters (T057-T059) run in parallel
- All visualizers (T064-T067) run in parallel

**User Story 3 (Phase 6)**:
- All tests (T073-T076) run in parallel
- All rules (T077-T081) run in parallel

**Polish Phase (Phase 7)**:
- Most tasks can run in parallel (marked with [P])

**Architecture Extensibility Phase (Phase 8 - Optional)**:
- All tests (T121-T125) run in parallel
- Pipeline stages (T129-T132) run in parallel
- Visualization refactor (T134-T140) can run in parallel
- Report refactor (T141-T145) can run in parallel
- Other component rules (T152-T154) run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T015: Unit test for BaseStrategy inheritance check
Task T016: Unit test for cal() method signature check
Task T017: Unit test for __abstract__ = False check
Task T018: Integration test for basic validation workflow

# Launch all rules for User Story 1 together:
Task T019: Implement BaseStrategyInheritanceRule
Task T020: Implement CalMethodSignatureRule
Task T021: Implement SuperInitCallRule
Task T022: Implement AbstractMarkerRule

# Launch all reporters for User Story 1 together:
Task T026: Implement TextReporter
Task T027: Implement JsonReporter
Task T028: Implement MarkdownReporter
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T014) - CRITICAL, blocks everything
3. Complete Phase 3: User Story 1 (T015-T034)
4. **STOP and VALIDATE**: Run `ginkgo validate strategy my_strategy.py --level basic`
5. Verify MVP works - structural validation functional

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 → Basic structural validation works
2. **Increment 1**: Add US2 → `ginkgo validate strategy --level standard` validates structure + logic
3. **Increment 2**: Add US4 → `ginkgo validate strategy --data test.csv --show-trace` provides signal insights
4. **Increment 3**: Add US3 → `ginkgo validate strategy --level strict` provides comprehensive analysis
5. Each increment adds value without breaking previous capabilities

### Success Criteria Validation

After each user story completion, verify corresponding SC requirements:

- **US1 Complete**: SC-001 (100% structural error detection), SC-003 (<2s validation), SC-008 (<1s CLI response)
- **US2 Complete**: SC-002 (90%+ logical error detection)
- **US4 Complete**: SC-005 (K线 + Tick support), SC-009 (<1min to verify signals visually), SC-016 (10x faster than backtest)
- **US3 Complete**: SC-011 (<5% false positive rate), SC-014 (>80% early detection)

---

## 任务管理原则遵循

根据章程第6条任务管理原则，本任务列表确保：

- **任务数量控制**: 每个阶段活跃任务 < 10个，符合开发实际
- **优先级明确**: P1 (US1) → P2 (US2, US4) → P3 (US3) 清晰排序
- **独立可测**: 每个User Story都有独立的测试标准
- **状态实时更新**: 通过checkbox追踪任务完成状态
- **MVP优先**: US1完成后即可交付基础功能

---

## Notes

- **[P] tasks**: Different files, no dependencies, safe to parallelize
- **[Story] labels**: Map tasks to US1/US2/US3/US4 for traceability
- **TDD workflow**: Tests written first, confirmed failing, then implementation
- **Commit strategy**: Commit after each task or logical group (e.g., all rules for a story)
- **Checkpoint validation**: Stop at checkpoints to verify independent story functionality
- **Avoid**: Vague tasks like "implement validation" - use specific file paths and clear deliverables
- **Architecture adherence**: All validators/rules/reporters follow three-layer architecture per plan.md
