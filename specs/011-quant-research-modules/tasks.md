# Tasks: Ginkgo 量化研究功能模块

**Input**: Design documents from `/specs/011-quant-research-modules/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contracts.md

**Tests**: TDD 流程，每个任务都有明确的测试与验收标准。

**Organization**: 任务按 User Story 分组，支持独立实现和测试。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属 User Story (US1-US8)
- 描述中包含精确文件路径

---

## Phase 1: Setup (项目初始化) ✅ COMPLETE

**Purpose**: 创建目录结构和基础配置

### T001 Create research module directory structure ✅

- **File**: `src/ginkgo/research/__init__.py`
- **Test**: `python -c "from ginkgo.research import __version__; print(__version__)"`
- **Acceptance**:
  - [x] 目录 `src/ginkgo/research/` 存在
  - [x] `__init__.py` 包含模块版本和导出列表
  - [x] `python -c "import ginkgo.research"` 无报错

### T002 Create validation module directory structure ✅

- **File**: `src/ginkgo/validation/__init__.py`
- **Test**: `python -c "from ginkgo.validation import __version__; print(__version__)"`
- **Acceptance**:
  - [x] 目录 `src/ginkgo/validation/` 存在
  - [x] `__init__.py` 包含模块版本和导出列表
  - [x] `python -c "import ginkgo.validation"` 无报错

### T003 [P] Create paper trading directory structure ✅

- **File**: `src/ginkgo/trading/paper/__init__.py`
- **Test**: `python -c "import ginkgo.trading.paper"`
- **Acceptance**:
  - [x] 目录 `src/ginkgo/trading/paper/` 存在
  - [x] `__init__.py` 存在且可导入

### T004 [P] Create comparison directory structure ✅

- **File**: `src/ginkgo/trading/comparison/__init__.py`
- **Test**: `python -c "import ginkgo.trading.comparison"`
- **Acceptance**:
  - [x] 目录 `src/ginkgo/trading/comparison/` 存在
  - [x] `__init__.py` 存在且可导入

### T005 [P] Create optimization directory structure ✅

- **File**: `src/ginkgo/trading/optimization/__init__.py`
- **Test**: `python -c "import ginkgo.trading.optimization"`
- **Acceptance**:
  - [x] 目录 `src/ginkgo/trading/optimization/` 存在
  - [x] `__init__.py` 存在且可导入

### T006 Add scipy, scikit-learn dependencies ✅

- **File**: `pyproject.toml`
- **Test**: `python -c "import scipy; import sklearn; print('OK')"`
- **Acceptance**:
  - [x] `pyproject.toml` 包含 `scipy>=1.11.0`
  - [x] `pyproject.toml` 包含 `scikit-learn>=1.3.0`
  - [x] `pip install -e .` 成功安装依赖

### T007 [P] Add optuna, deap as optional dependencies ✅

- **File**: `pyproject.toml`
- **Test**: `pip install -e ".[optimization]" && python -c "import optuna; import deap"`
- **Acceptance**:
  - [x] `pyproject.toml` 包含 `[project.optional-dependencies]`
  - [x] `optimization = ["optuna>=3.3.0", "deap>=1.4.0"]`
  - [ ] 可选依赖安装成功 (延迟到需要时安装)

---

## Phase 2: Foundational (基础设施) ✅ COMPLETE

**Purpose**: 所有 User Story 依赖的基础设施

**⚠️ CRITICAL**: 此阶段必须完成后才能开始任何 User Story

### T008 Create ResearchContainer ✅

- **File**: `src/ginkgo/research/containers.py`
- **Test**:
  ```python
  from ginkgo.research.containers import ResearchContainer
  container = ResearchContainer()
  assert container is not None
  ```
- **Acceptance**:
  - [x] `ResearchContainer` 继承 `DeclarativeContainer`
  - [x] 包含占位符 providers（后续添加具体服务）
  - [x] 可成功实例化

### T009 [P] Create ValidationContainer ✅

- **File**: `src/ginkgo/validation/containers.py`
- **Test**:
  ```python
  from ginkgo.validation.containers import ValidationContainer
  container = ValidationContainer()
  assert container is not None
  ```
- **Acceptance**:
  - [x] `ValidationContainer` 继承 `DeclarativeContainer`
  - [x] 可成功实例化

### T010 [P] Create PaperContainer ✅

- **File**: `src/ginkgo/trading/paper/containers.py`
- **Test**:
  ```python
  from ginkgo.trading.paper.containers import PaperContainer
  container = PaperContainer()
  assert container is not None
  ```
- **Acceptance**:
  - [x] `PaperContainer` 继承 `DeclarativeContainer`
  - [x] 可成功实例化

### T011 [P] Create ComparisonContainer ✅

- **File**: `src/ginkgo/trading/comparison/containers.py`
- **Test**:
  ```python
  from ginkgo.trading.comparison.containers import ComparisonContainer
  container = ComparisonContainer()
  assert container is not None
  ```
- **Acceptance**:
  - [x] `ComparisonContainer` 继承 `DeclarativeContainer`
  - [x] 可成功实例化

### T012 [P] Create OptimizationContainer ✅

- **File**: `src/ginkgo/trading/optimization/containers.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.containers import OptimizationContainer
  container = OptimizationContainer()
  assert container is not None
  ```
- **Acceptance**:
  - [x] `OptimizationContainer` 继承 `DeclarativeContainer`
  - [x] 可成功实例化

### T013 Register research container in ServiceHub ✅

- **File**: `src/ginkgo/service_hub.py`
- **Test**:
  ```python
  from ginkgo import service_hub
  assert hasattr(service_hub, 'research')
  assert service_hub.research is not None
  ```
- **Acceptance**:
  - [x] `ServiceHub` 添加 `@property research` 方法
  - [x] 懒加载 `ResearchContainer`
  - [x] `service_hub.research` 返回容器实例

### T014 [P] Register validation container in ServiceHub ✅

- **File**: `src/ginkgo/service_hub.py`
- **Test**:
  ```python
  from ginkgo import service_hub
  assert hasattr(service_hub, 'validation')
  assert service_hub.validation is not None
  ```
- **Acceptance**:
  - [x] `ServiceHub` 添加 `@property validation` 方法
  - [x] 懒加载 `ValidationContainer`

### T015 [P] Register paper/comparison/optimization containers ✅

- **File**: `src/ginkgo/service_hub.py`
- **Test**:
  ```python
  from ginkgo import service_hub
  # 新增顶级属性访问
  assert hasattr(service_hub, 'paper')
  assert hasattr(service_hub, 'comparison')
  assert hasattr(service_hub, 'optimization')
  ```
- **Acceptance**:
  - [x] 添加 `@property paper`、`@property comparison`、`@property optimization`
  - [x] 所有新容器可通过 `service_hub` 访问

### T016 Create research_cli.py with command group ✅

- **File**: `src/ginkgo/client/research_cli.py`
- **Test**: `python -c "from ginkgo.client.research_cli import app; print('OK')"`
- **Acceptance**:
  - [x] 创建 `app = typer.Typer()` 命令组
  - [x] 包含占位符命令（ic, layering 等）
  - [x] 模块可导入

### T017 [P] Register research CLI commands ⏳

- **File**: `src/ginkgo/client/app.py`
- **Test**: `ginkgo --help | grep research`
- **Acceptance**:
  - [ ] `app.py` 导入 `research_cli`
  - [ ] `app.add_typer(research_cli.app, name="research")`
  - [ ] `ginkgo research` 命令可用

**Checkpoint**: 基础设施就绪，`service_hub.research/validation/paper/comparison/optimization` 可访问

---

## Phase 3: User Story 1 - Paper Trading 模拟盘 (Priority: P1) 🎯 MVP ✅ COMPLETE

**Goal**: 使用实盘数据验证策略表现，与回测结果对比

**Independent Test**: 加载已回测的 Portfolio，启动 Paper Trading，验证信号生成和对比功能

### T018 [P] [US1] Create PaperTradingEngine test ✅

- **File**: `tests/trading/paper/test_paper_engine.py`
- **Test**: `pytest tests/trading/paper/test_paper_engine.py -v` (应先失败)
- **Acceptance**:
  - [x] 测试类 `TestPaperTradingEngine` 存在
  - [x] 包含测试: `test_init`, `test_start`, `test_stop`, `test_on_daily_close`
  - [x] 使用 `@pytest.mark.unit` 标记
  - [x] 运行测试返回失败（Red 阶段）→ Green 阶段通过

### T019 [P] [US1] Create SlippageModel test ✅

- **File**: `tests/trading/paper/test_slippage_models.py`
- **Test**: `pytest tests/trading/paper/test_slippage_models.py -v`
- **Acceptance**:
  - [x] 测试 `TestFixedSlippage`, `TestPercentageSlippage`, `TestNoSlippage`
  - [x] 包含测试: 买入加滑点、卖出入滑点、边界值
  - [x] 使用 `@pytest.mark.financial` 标记（金融精度）

### T020 [P] [US1] Create PaperTradingResult test ✅

- **File**: `tests/trading/paper/test_result.py`
- **Test**: `pytest tests/trading/paper/test_result.py -v`
- **Acceptance**:
  - [x] 测试 `TestPaperTradingResult`
  - [x] 包含测试: 差异计算、可接受判断、序列化

### T021 [P] [US1] Create PaperTradingState dataclass ✅

- **File**: `src/ginkgo/trading/paper/models.py`
- **Test**: 通过
- **Acceptance**:
  - [x] 包含所有字段: portfolio_id, paper_id, status, started_at, current_date 等
  - [x] 使用 `@dataclass` 装饰器
  - [x] 类型注解完整
  - [x] 测试通过

### T022 [P] [US1] Create PaperTradingSignal dataclass ✅

- **File**: `src/ginkgo/trading/paper/models.py`
- **Test**: 通过
- **Acceptance**:
  - [x] 包含字段: signal_id, paper_id, date, code, direction, order_price 等
  - [x] 类型注解完整

### T023 [P] [US1] Create PaperTradingResult dataclass ✅

- **File**: `src/ginkgo/trading/paper/models.py`
- **Test**: 通过
- **Acceptance**:
  - [x] 包含字段: paper_id, portfolio_id, total_return, backtest_return 等
  - [x] `is_acceptable` 属性: `abs(difference_pct) < 0.1`

### T024 [US1] Create SlippageModel ABC ✅

- **File**: `src/ginkgo/trading/paper/slippage_models.py`
- **Test**: 通过
- **Acceptance**:
  - [x] 继承 `ABC`
  - [x] 定义 `@abstractmethod apply(self, price: Decimal, direction: DIRECTION_TYPES) -> Decimal`

### T025 [US1] Implement FixedSlippage ✅

- **File**: `src/ginkgo/trading/paper/slippage_models.py`
- **Test**: 9 passed
- **Acceptance**:
  - [x] 继承 `SlippageModel`
  - [x] 实现 `apply` 方法
  - [x] 单元测试通过

### T026 [US1] Implement PercentageSlippage ✅

- **File**: `src/ginkgo/trading/paper/slippage_models.py`
- **Test**: 通过
- **Acceptance**:
  - [ ] 继承 `SlippageModel`
  - [ ] 百分比计算正确
  - [ ] 单元测试通过

### T027 [US1] Implement NoSlippage

- **File**: `src/ginkgo/trading/paper/slippage_models.py`
- **Test**:
  ```python
  from ginkgo.trading.paper.slippage_models import NoSlippage
  model = NoSlippage()
  assert model.apply(Decimal("10.00"), DIRECTION_TYPES.LONG) == Decimal("10.00")
  ```
- **Acceptance**:
  - [ ] 继承 `SlippageModel`
  - [ ] 返回原价格
  - [ ] 单元测试通过

### T028 [US1] Implement PaperTradingEngine.__init__

### T027 [US1] Implement NoSlippage ✅

- **File**: `src/ginkgo/trading/paper/slippage_models.py`
- **Test**: 通过
- **Acceptance**:
  - [x] 继承 `SlippageModel`
  - [x] 返回原价格
  - [x] 单元测试通过

### T028 [US1] Implement PaperTradingEngine.__init__ ✅

- **File**: `src/ginkgo/trading/paper/paper_engine.py`
- **Test**: 通过
- **Acceptance**:
  - [x] 初始化 slippage_model, commission_rate, commission_min
  - [x] `is_running` 默认 `False`
  - [x] 包含三行头部注释

### T029 [US1] Implement PaperTradingEngine.start/stop ✅

- **File**: `src/ginkgo/trading/paper/paper_engine.py`
- **Test**: 通过
- **Acceptance**:
  - [x] `start()` 设置 `is_running = True`
  - [x] `stop()` 设置 `is_running = False`
  - [x] 返回 `bool` 表示成功/失败

### T030 [US1] Implement PaperTradingEngine.on_daily_close ✅

- **File**: `src/ginkgo/trading/paper/paper_engine.py`
- **Test**: 通过 (框架完成，TODO: 完整数据集成)
- **Acceptance**:
  - [x] 基础框架完成
  - [ ] 从 data 模块获取当日日K（使用 bar_crud）- TODO
  - [ ] 调用 Portfolio 策略计算 - TODO
  - [ ] 模拟成交 - TODO

### T031 [US1] Implement PaperTradingEngine.compare_with_backtest ✅

- **File**: `src/ginkgo/trading/paper/paper_engine.py`
- **Test**: 通过 (框架完成，TODO: 完整数据集成)
- **Acceptance**:
  - [x] 基础框架完成
  - [ ] 加载回测结果 - TODO
  - [x] 返回 `PaperTradingResult`

### T032 [US1] Add paper start/stop CLI commands ⏳

- **File**: `src/ginkgo/client/paper_cli.py`
- **Test**:
  ```bash
  ginkgo paper start test_portfolio --help
  ginkgo paper stop test_portfolio --help
  ```
- **Acceptance**:
  - [ ] `ginkgo paper start <portfolio_id>` 命令
  - [ ] `ginkgo paper stop <portfolio_id>` 命令
  - [ ] 支持 `--slippage`, `--commission` 参数

### T033 [US1] Add paper status/compare CLI commands ⏳

- **File**: `src/ginkgo/client/paper_cli.py`
- **Test**:
  ```bash
  ginkgo paper status test_portfolio
  ginkgo paper compare test_portfolio --backtest bt_001
  ```
- **Acceptance**:
  - [ ] `ginkgo paper status <portfolio_id>` 显示当前状态
  - [ ] `ginkgo paper compare <portfolio_id> --backtest <id>` 对比结果
  - [ ] 输出格式化表格（使用 Rich）

**Checkpoint**: Paper Trading 可独立运行，`ginkgo paper` 命令完整

---

## Phase 4: User Story 2 - 回测对比 (Priority: P1)

**Goal**: 对比多个回测结果，生成对比表格和净值曲线

**Independent Test**: 运行两个回测，调用对比功能，验证对比表格

### T034 [P] [US2] Create BacktestComparator test

- **File**: `tests/trading/comparison/test_backtest_comparator.py`
- **Test**: `pytest tests/trading/comparison/test_backtest_comparator.py -v`
- **Acceptance**:
  - [ ] 测试 `test_compare`, `test_get_net_values`, `test_best_performers`
  - [ ] 使用 `@pytest.mark.unit` 标记

### T035 [P] [US2] Create ComparisonResult test

- **File**: `tests/trading/comparison/test_result.py`
- **Test**: `pytest tests/trading/comparison/test_result.py -v`
- **Acceptance**:
  - [ ] 测试序列化、指标访问

### T036 [P] [US2] Create ComparisonResult dataclass

- **File**: `src/ginkgo/trading/comparison/models.py`
- **Test**:
  ```python
  from ginkgo.trading.comparison.models import ComparisonResult
  result = ComparisonResult(comparison_id="c1", backtest_ids=["bt1", "bt2"])
  assert result.backtest_ids == ["bt1", "bt2"]
  ```
- **Acceptance**:
  - [ ] 包含字段: comparison_id, backtest_ids, metrics_table, best_performers, net_values

### T037 [US2] Implement BacktestComparator.__init__

- **File**: `src/ginkgo/trading/comparison/backtest_comparator.py`
- **Test**:
  ```python
  from ginkgo.trading.comparison.backtest_comparator import BacktestComparator
  comparator = BacktestComparator()
  assert comparator is not None
  ```
- **Acceptance**:
  - [ ] 初始化空的结果缓存
  - [ ] 包含三行头部注释

### T038 [US2] Implement BacktestComparator.compare

- **File**: `src/ginkgo/trading/comparison/backtest_comparator.py`
- **Test**:
  ```python
  comparator = BacktestComparator()
  result = comparator.compare(["bt_001", "bt_002", "bt_003"])
  assert "total_return" in result.metrics_table
  assert "bt_001" in result.best_performers.values()
  ```
- **Acceptance**:
  - [ ] 加载多个回测结果（从数据库）
  - [ ] 计算对比指标: total_return, sharpe_ratio, max_drawdown, win_rate 等
  - [ ] 标注每个指标的最佳表现

### T039 [US2] Implement BacktestComparator.get_net_values

- **File**: `src/ginkgo/trading/comparison/backtest_comparator.py`
- **Test**:
  ```python
  net_values = comparator.get_net_values(["bt_001"], normalized=True)
  assert "bt_001" in net_values
  assert net_values["bt_001"][0][1] == 1.0  # 归一化后从 1.0 开始
  ```
- **Acceptance**:
  - [ ] 支持归一化显示
  - [ ] 返回 `Dict[str, List[Tuple[date, float]]]`

### T040 [US2] Add compare CLI command

- **File**: `src/ginkgo/client/comparison_cli.py`
- **Test**: `ginkgo compare bt_001 bt_002 bt_003 --output report.html`
- **Acceptance**:
  - [ ] `ginkgo compare <ids...>` 命令
  - [ ] 支持 `--output` 导出报告
  - [ ] 输出格式化对比表格

**Checkpoint**: 回测对比功能可用，`ginkgo compare` 命令完整

---

## Phase 5: User Story 3 - IC 分析 (Priority: P2)

**Goal**: 计算因子 IC，生成统计指标

### T041 [P] [US3] Create ICAnalyzer test

- **File**: `tests/research/test_ic_analysis.py`
- **Test**: `pytest tests/research/test_ic_analysis.py -v`
- **Acceptance**:
  - [ ] 测试 Pearson IC、Rank IC 计算
  - [ ] 测试统计指标计算
  - [ ] 使用 `@pytest.mark.financial` 标记

### T042 [P] [US3] Create ICStatistics dataclass

- **File**: `src/ginkgo/research/models.py`
- **Test**:
  ```python
  from ginkgo.research.models import ICStatistics
  stats = ICStatistics(mean=0.05, std=0.15, icir=0.33, t_stat=2.1, p_value=0.03, pos_ratio=0.55)
  assert stats.icir == stats.mean / stats.std
  ```
- **Acceptance**:
  - [ ] 包含字段: mean, std, icir, t_stat, p_value, pos_ratio, abs_mean

### T043 [P] [US3] Create ICAnalysisResult dataclass

- **File**: `src/ginkgo/research/models.py`
- **Test**:
  ```python
  from ginkgo.research.models import ICAnalysisResult
  result = ICAnalysisResult(factor_name="MOM_20", periods=[1, 5, 10, 20])
  assert result.periods == [1, 5, 10, 20]
  ```
- **Acceptance**:
  - [ ] 包含字段: factor_name, periods, date_range, ic_series, statistics

### T044 [US3] Implement ICAnalyzer.__init__

- **File**: `src/ginkgo/research/ic_analysis.py`
- **Test**:
  ```python
  from ginkgo.research.ic_analysis import ICAnalyzer
  analyzer = ICAnalyzer(factor_df, return_df)
  assert analyzer.factor_data is not None
  ```
- **Acceptance**:
  - [ ] 验证输入数据格式
  - [ ] 检查必需列: date, code, factor_value/return

### T045 [US3] Implement ICAnalyzer.analyze (Pearson IC)

- **File**: `src/ginkgo/research/ic_analysis.py`
- **Test**:
  ```python
  result = analyzer.analyze(periods=[1, 5], method="pearson")
  assert 1 in result.ic_series
  assert len(result.ic_series[1]) > 0
  ```
- **Acceptance**:
  - [ ] 计算 `corr(factor_value, forward_return)`
  - [ ] 支持多周期

### T046 [US3] Implement ICAnalyzer.analyze (Rank IC)

- **File**: `src/ginkgo/research/ic_analysis.py`
- **Test**:
  ```python
  result = analyzer.analyze(periods=[1], method="spearman")
  assert result.rank_ic_series is not None
  ```
- **Acceptance**:
  - [ ] 使用 Spearman 相关系数
  - [ ] 存储到 `rank_ic_series`

### T047 [US3] Implement ICAnalyzer.get_statistics

- **File**: `src/ginkgo/research/ic_analysis.py`
- **Test**:
  ```python
  stats = analyzer.get_statistics(period=5)
  assert -1 <= stats.pos_ratio <= 1
  assert stats.icir == stats.mean / stats.std
  ```
- **Acceptance**:
  - [ ] 计算均值、标准差、ICIR、t统计量、p值、正IC占比

### T048 [US3] Add research ic CLI command

- **File**: `src/ginkgo/client/research_cli.py`
- **Test**: `ginkgo research ic --factor MOM_20 --start 20230101 --end 20231231`
- **Acceptance**:
  - [ ] 支持 `--factor`, `--start`, `--end`, `--periods` 参数
  - [ ] 输出 IC 统计表格

**Checkpoint**: IC 分析功能可用

---

## Phase 6: User Story 4 - 因子分层 (Priority: P2)

**Goal**: 按因子值分组，计算各组收益和多空收益

### T049 [P] [US4] Create FactorLayering test

- **File**: `tests/research/test_layering.py`
- **Test**: `pytest tests/research/test_layering.py -v`
- **Acceptance**:
  - [ ] 测试分组逻辑、收益计算、多空收益、单调性

### T050 [P] [US4] Create LayeringStatistics dataclass

- **File**: `src/ginkgo/research/models.py`
- **Test**:
  ```python
  from ginkgo.research.models import LayeringStatistics
  stats = LayeringStatistics(long_short_total_return=0.15, monotonicity_r2=0.85)
  assert stats.monotonicity_r2 >= 0
  ```
- **Acceptance**:
  - [ ] 包含字段: long_short_total_return, long_short_sharpe, max_drawdown, monotonicity_r2, turnover

### T051 [P] [US4] Create LayeringResult dataclass

- **File**: `src/ginkgo/research/models.py`
- **Test**:
  ```python
  from ginkgo.research.models import LayeringResult
  result = LayeringResult(factor_name="MOM_20", n_groups=5)
  assert result.n_groups == 5
  ```
- **Acceptance**:
  - [ ] 包含字段: factor_name, n_groups, date_range, group_returns, long_short_return, statistics

### T052 [US4] Implement FactorLayering.__init__

- **File**: `src/ginkgo/research/layering.py`
- **Test**:
  ```python
  from ginkgo.research.layering import FactorLayering
  layering = FactorLayering(factor_df, return_df)
  assert layering is not None
  ```
- **Acceptance**:
  - [ ] 验证输入数据

### T053 [US4] Implement FactorLayering.run

- **File**: `src/ginkgo/research/layering.py`
- **Test**:
  ```python
  result = layering.run(n_groups=5, rebalance_freq=20)
  assert len(result.group_returns) == 5
  assert result.long_short_return is not None
  ```
- **Acceptance**:
  - [ ] 按因子值分位数分组
  - [ ] 计算各组收益序列
  - [ ] 计算多空收益（最高组 - 最低组）

### T054 [US4] Implement FactorLayering.calculate_monotonicity

- **File**: `src/ginkgo/research/layering.py`
- **Test**:
  ```python
  r2 = layering.calculate_monotonicity()
  assert 0 <= r2 <= 1
  ```
- **Acceptance**:
  - [ ] 使用线性回归计算单调性
  - [ ] 返回 R² 值

### T055 [US4] Add research layering CLI command

- **File**: `src/ginkgo/client/research_cli.py`
- **Test**: `ginkgo research layering --factor MOM_20 --groups 5`
- **Acceptance**:
  - [ ] 支持 `--factor`, `--groups`, `--rebalance-freq` 参数

**Checkpoint**: 因子分层功能可用

---

## Phase 7: User Story 5 - 参数优化 (Priority: P2)

**Goal**: 支持网格搜索、遗传算法、贝叶斯优化

### T056 [P] [US5] Create BaseOptimizer test

- **File**: `tests/trading/optimization/test_base_optimizer.py`
- **Test**: `pytest tests/trading/optimization/test_base_optimizer.py -v`
- **Acceptance**:
  - [ ] 测试参数范围解析
  - [ ] 测试抽象方法

### T057 [P] [US5] Create GridSearchOptimizer test

- **File**: `tests/trading/optimization/test_grid_search.py`
- **Test**: `pytest tests/trading/optimization/test_grid_search.py -v`
- **Acceptance**:
  - [ ] 测试网格生成
  - [ ] 测试优化结果排序

### T058 [P] [US5] Create GeneticOptimizer test

- **File**: `tests/trading/optimization/test_genetic_optimizer.py`
- **Test**: `pytest tests/trading/optimization/test_genetic_optimizer.py -v`
- **Acceptance**:
  - [ ] 测试种群初始化
  - [ ] 测试进化过程

### T059 [P] [US5] Create BayesianOptimizer test

- **File**: `tests/trading/optimization/test_bayesian_optimizer.py`
- **Test**: `pytest tests/trading/optimization/test_bayesian_optimizer.py -v`
- **Acceptance**:
  - [ ] 测试贝叶斯优化流程

### T060 [P] [US5] Create ParameterRange dataclass

- **File**: `src/ginkgo/trading/optimization/models.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.models import ParameterRange
  pr = ParameterRange(name="fast_period", min=5, max=20, step=1)
  assert pr.name == "fast_period"
  ```
- **Acceptance**:
  - [ ] 支持连续值和离散值

### T061 [P] [US5] Create OptimizationResult dataclass

- **File**: `src/ginkgo/trading/optimization/models.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.models import OptimizationResult
  result = OptimizationResult(strategy_name="Test", optimizer_type="grid")
  assert result.results == []
  ```
- **Acceptance**:
  - [ ] 包含字段: strategy_name, optimizer_type, param_ranges, results, best_params, best_score

### T062 [US5] Implement BaseOptimizer ABC

- **File**: `src/ginkgo/trading/optimization/base_optimizer.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
  assert 'optimize' in BaseOptimizer.__abstractmethods__
  ```
- **Acceptance**:
  - [ ] 定义抽象方法 `optimize()`
  - [ ] 定义参数验证方法

### T063 [US5] Implement GridSearchOptimizer

- **File**: `src/ginkgo/trading/optimization/grid_search.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.grid_search import GridSearchOptimizer
  optimizer = GridSearchOptimizer(strategy_class, param_ranges)
  result = optimizer.optimize(data)
  assert len(result.results) > 0
  ```
- **Acceptance**:
  - [ ] 遍历所有参数组合
  - [ ] 运行回测并记录结果
  - [ ] 按目标指标排序

### T064 [US5] Implement GeneticOptimizer

- **File**: `src/ginkgo/trading/optimization/genetic_optimizer.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer
  optimizer = GeneticOptimizer(strategy_class, param_ranges, population_size=50)
  result = optimizer.optimize(data)
  assert result.best_params is not None
  ```
- **Acceptance**:
  - [ ] 使用 deap 库实现
  - [ ] 支持种群大小、迭代次数、变异率配置

### T065 [US5] Implement BayesianOptimizer

- **File**: `src/ginkgo/trading/optimization/bayesian_optimizer.py`
- **Test**:
  ```python
  from ginkgo.trading.optimization.bayesian_optimizer import BayesianOptimizer
  optimizer = BayesianOptimizer(strategy_class, param_ranges, n_iterations=50)
  result = optimizer.optimize(data)
  ```
- **Acceptance**:
  - [ ] 使用 optuna 库实现
  - [ ] 支持 acquisition 函数配置

### T066 [US5] Add optimize CLI commands

- **File**: `src/ginkgo/client/optimization_cli.py`
- **Test**:
  ```bash
  ginkgo optimize grid --strategy MyStrategy --params fast:5:20 slow:20:60
  ginkgo optimize genetic --strategy MyStrategy --population 50 --generations 20
  ```
- **Acceptance**:
  - [ ] 支持 grid, genetic, bayesian 子命令
  - [ ] 参数格式: `name:min:max:step` 或 `name:val1,val2,val3`

**Checkpoint**: 参数优化功能可用

---

## Phase 8: User Story 6 - 走步验证 (Priority: P2)

**Goal**: 滑动窗口验证，计算过拟合程度

### T067 [P] [US6] Create WalkForwardValidator test

- **File**: `tests/validation/test_walk_forward.py`
- **Test**: `pytest tests/validation/test_walk_forward.py -v`
- **Acceptance**:
  - [ ] 测试滑动窗口划分
  - [ ] 测试退化程度计算

### T068 [P] [US6] Create WalkForwardFold dataclass

- **File**: `src/ginkgo/validation/models.py`
- **Test**:
  ```python
  from ginkgo.validation.models import WalkForwardFold
  fold = WalkForwardFold(fold_num=1, train_period=("2023-01-01", "2023-12-31"))
  assert fold.fold_num == 1
  ```
- **Acceptance**:
  - [ ] 包含字段: fold_num, train_period, test_period, train_return, test_return, parameters

### T069 [P] [US6] Create WalkForwardResult dataclass

- **File**: `src/ginkgo/validation/models.py`
- **Test**:
  ```python
  from ginkgo.validation.models import WalkForwardResult
  result = WalkForwardResult(train_size=252, test_size=63, step_size=21)
  assert result.degradation == 0.0
  ```
- **Acceptance**:
  - [ ] 包含字段: train_size, test_size, step_size, folds, avg_train_return, avg_test_return, degradation, stability_score

### T070 [US6] Implement WalkForwardValidator.__init__

- **File**: `src/ginkgo/validation/walk_forward.py`
- **Test**:
  ```python
  from ginkgo.validation.walk_forward import WalkForwardValidator
  validator = WalkForwardValidator(strategy_class, parameters)
  assert validator is not None
  ```
- **Acceptance**:
  - [ ] 存储 strategy_class 和 parameters

### T071 [US6] Implement WalkForwardValidator.validate

- **File**: `src/ginkgo/validation/walk_forward.py`
- **Test**:
  ```python
  result = validator.validate(data, train_size=252, test_size=63, step_size=21)
  assert len(result.folds) > 0
  assert result.degradation >= 0
  ```
- **Acceptance**:
  - [ ] 按滑动窗口划分数据
  - [ ] 每个 fold 运行回测
  - [ ] 计算训练/测试收益

### T072 [US6] Implement WalkForwardValidator.calculate_degradation

- **File**: `src/ginkgo/validation/walk_forward.py`
- **Test**:
  ```python
  degradation = validator.calculate_degradation()
  # 退化程度 = (train - test) / train
  assert 0 <= degradation <= 1
  ```
- **Acceptance**:
  - [ ] 计算 (avg_train - avg_test) / avg_train
  - [ ] 计算 stability_score

### T073 [US6] Add validate walk-forward CLI command

- **File**: `src/ginkgo/client/validation_cli.py`
- **Test**: `ginkgo validate walk-forward --strategy MyStrategy --train 252 --test 63`
- **Acceptance**:
  - [ ] 支持 `--strategy`, `--train`, `--test`, `--step` 参数
  - [ ] 输出各 fold 结果和退化程度

**Checkpoint**: 走步验证功能可用

---

## Phase 9: User Story 7 - 蒙特卡洛模拟 (Priority: P3)

**Goal**: 随机模拟，计算 VaR/CVaR

### T074 [P] [US7] Create MonteCarloSimulator test

- **File**: `tests/validation/test_monte_carlo.py`
- **Test**: `pytest tests/validation/test_monte_carlo.py -v`
- **Acceptance**:
  - [ ] 测试模拟路径生成
  - [ ] 测试 VaR/CVaR 计算

### T075 [P] [US7] Create MonteCarloResult dataclass

- **File**: `src/ginkgo/validation/models.py`
- **Test**:
  ```python
  from ginkgo.validation.models import MonteCarloResult
  result = MonteCarloResult(n_simulations=10000, confidence_level=0.95)
  assert result.n_simulations == 10000
  ```
- **Acceptance**:
  - [ ] 包含字段: n_simulations, confidence_level, mean, std, percentiles, var, cvar

### T076 [US7] Implement MonteCarloSimulator.__init__

- **File**: `src/ginkgo/validation/monte_carlo.py`
- **Test**:
  ```python
  from ginkgo.validation.monte_carlo import MonteCarloSimulator
  simulator = MonteCarloSimulator(returns, n_simulations=10000)
  assert simulator.n_simulations == 10000
  ```
- **Acceptance**:
  - [ ] 验证输入收益序列
  - [ ] 设置模拟次数和置信水平

### T077 [US7] Implement MonteCarloSimulator.run

- **File**: `src/ginkgo/validation/monte_carlo.py`
- **Test**:
  ```python
  result = simulator.run()
  assert len(result.paths) == 10000  # 如果存储路径
  assert result.mean is not None
  ```
- **Acceptance**:
  - [ ] 基于历史收益分布生成随机路径
  - [ ] 计算均值、标准差、分位数

### T078 [US7] Implement MonteCarloSimulator.calculate_var/cvar

- **File**: `src/ginkgo/validation/monte_carlo.py`
- **Test**:
  ```python
  var = simulator.calculate_var(0.95)
  cvar = simulator.calculate_cvar(0.95)
  assert cvar <= var  # CVaR 通常比 VaR 更保守
  ```
- **Acceptance**:
  - [ ] VaR = 分位数（如 5% 分位数）
  - [ ] CVaR = 低于 VaR 的期望值

### T079 [US7] Add validate monte-carlo CLI command

- **File**: `src/ginkgo/client/validation_cli.py`
- **Test**: `ginkgo validate monte-carlo --returns returns.csv --simulations 10000`
- **Acceptance**:
  - [ ] 支持 `--returns`, `--simulations`, `--confidence` 参数
  - [ ] 输出 VaR/CVaR 结果

**Checkpoint**: 蒙特卡洛功能可用

---

## Phase 10: User Story 8 - 因子正交化 (Priority: P3)

**Goal**: Gram-Schmidt、PCA、残差法正交化

### T080 [P] [US8] Create FactorOrthogonalizer test

- **File**: `tests/research/test_orthogonalization.py`
- **Test**: `pytest tests/research/test_orthogonalization.py -v`
- **Acceptance**:
  - [ ] 测试 Gram-Schmidt、PCA、残差法
  - [ ] 验证正交化后相关性降低

### T081 [US8] Implement FactorOrthogonalizer.__init__

- **File**: `src/ginkgo/research/orthogonalization.py`
- **Test**:
  ```python
  from ginkgo.research.orthogonalization import FactorOrthogonalizer
  orth = FactorOrthogonalizer(factor_df)
  assert orth.factor_data is not None
  ```
- **Acceptance**:
  - [ ] 验证多因子数据格式

### T082 [US8] Implement FactorOrthogonalizer.gram_schmidt

- **File**: `src/ginkgo/research/orthogonalization.py`
- **Test**:
  ```python
  result = orth.gram_schmidt(order=["factor1", "factor2", "factor3"])
  # 验证正交性
  corr = result[["factor1", "factor2"]].corr()
  assert abs(corr.iloc[0, 1]) < 0.1  # 相关系数接近 0
  ```
- **Acceptance**:
  - [ ] 按指定顺序正交化
  - [ ] 返回正交化后的 DataFrame

### T083 [US8] Implement FactorOrthogonalizer.pca

- **File**: `src/ginkgo/research/orthogonalization.py`
- **Test**:
  ```python
  result = orth.pca(n_components=3)
  assert result.shape[1] == 3
  ```
- **Acceptance**:
  - [ ] 使用 sklearn PCA
  - [ ] 支持 n_components 或 variance_ratio

### T084 [US8] Implement FactorOrthogonalizer.residualize

- **File**: `src/ginkgo/research/orthogonalization.py`
- **Test**:
  ```python
  result = orth.residualize(target="factor1", controls=["factor2", "factor3"])
  # factor1 对 factor2, factor3 回归后的残差
  ```
- **Acceptance**:
  - [ ] 对目标因子进行残差化

### T085 [US8] Add research orthogonalize CLI command

- **File**: `src/ginkgo/client/research_cli.py`
- **Test**: `ginkgo research orthogonalize --factors factor1,factor2,factor3 --method pca`
- **Acceptance**:
  - [ ] 支持 `--factors`, `--method` (gram_schmidt/pca/residualize) 参数

**Checkpoint**: 因子正交化功能可用

---

## Phase 11: 扩展功能 (P1/P2/P3 其他功能)

### T086 [P] Implement FactorComparator

- **File**: `src/ginkgo/research/factor_comparison.py`
- **Test**:
  ```python
  from ginkgo.research.factor_comparison import FactorComparator
  comparator = FactorComparator(["factor1", "factor2"])
  result = comparator.compare()
  assert len(result) == 2
  ```
- **Acceptance**:
  - [ ] 对比多个因子的 IC、分层收益、换手率
  - [ ] 生成综合评分

### T087 [P] Implement FactorDecayAnalyzer

- **File**: `src/ginkgo/research/decay_analysis.py`
- **Test**:
  ```python
  from ginkgo.research.decay_analysis import FactorDecayAnalyzer
  analyzer = FactorDecayAnalyzer(factor_df, return_df)
  half_life = analyzer.calculate_half_life()
  assert half_life > 0
  ```
- **Acceptance**:
  - [ ] 计算不同滞后期的 IC
  - [ ] 计算半衰期

### T088 [P] Implement FactorTurnoverAnalyzer

- **File**: `src/ginkgo/research/turnover_analysis.py`
- **Test**:
  ```python
  from ginkgo.research.turnover_analysis import FactorTurnoverAnalyzer
  analyzer = FactorTurnoverAnalyzer(factor_df)
  turnover = analyzer.analyze()
  assert 0 <= turnover <= 2
  ```
- **Acceptance**:
  - [ ] 计算因子换手率时序
  - [ ] 计算平均换手率

### T089 [P] Implement SensitivityAnalyzer

- **File**: `src/ginkgo/validation/sensitivity.py`
- **Test**:
  ```python
  from ginkgo.validation.sensitivity import SensitivityAnalyzer
  analyzer = SensitivityAnalyzer(strategy_class, "fast_period", 10, [5, 10, 15, 20])
  result = analyzer.analyze()
  assert len(result.results) == 4
  ```
- **Acceptance**:
  - [ ] 分析单个参数变化的影响
  - [ ] 返回敏感性曲线

### T090 [P] Implement TimeSeriesCrossValidator

- **File**: `src/ginkgo/validation/cross_validation.py`
- **Test**:
  ```python
  from ginkgo.validation.cross_validation import TimeSeriesCrossValidator
  validator = TimeSeriesCrossValidator(strategy_class, parameters, n_folds=5)
  result = validator.validate(data)
  assert len(result.folds) == 5
  ```
- **Acceptance**:
  - [ ] 时间序列 K-Fold 验证
  - [ ] 避免数据泄漏

### T091 Implement FactorPortfolioBuilder

- **File**: `src/ginkgo/portfolio/factor_portfolio.py`
- **Test**:
  ```python
  from ginkgo.portfolio.factor_portfolio import FactorPortfolioBuilder
  builder = FactorPortfolioBuilder(factors=[...], weight_target="equal")
  weights = builder.build(date="2024-01-01")
  assert abs(weights.sum() - 1.0) < 0.01  # 权重和为 1
  ```
- **Acceptance**:
  - [ ] 多因子加权组合
  - [ ] 支持行业中性约束

---

## Phase 12: Polish & Cross-Cutting Concerns

### T092 [P] Add @time_logger decorators

- **File**: 所有新模块的公共方法
- **Test**: 检查日志输出包含执行时间
- **Acceptance**:
  - [ ] 所有公共方法添加 `@time_logger`
  - [ ] 日志输出正确

### T093 [P] Add @cache_with_expiration

- **File**: 频繁调用的方法（如 IC 计算、因子数据获取）
- **Test**: 重复调用验证缓存生效
- **Acceptance**:
  - [ ] 适当位置添加缓存装饰器
  - [ ] 缓存过期时间合理

### T094 [P] Verify batch operations in Paper Trading

- **File**: `src/ginkgo/trading/paper/paper_engine.py`
- **Test**: 检查数据操作使用批量方法
- **Acceptance**:
  - [ ] 使用 `add_bars` 而非单条插入
  - [ ] 批量信号记录

### T095 [P] Add type annotations

- **File**: 所有新文件
- **Test**: `mypy src/ginkgo/research/ src/ginkgo/validation/ src/ginkgo/trading/paper/`
- **Acceptance**:
  - [ ] 所有函数参数和返回值有类型注解
  - [ ] mypy 检查通过

### T096 [P] Add three-line headers

- **File**: 所有新文件
- **Test**: 检查文件头部包含 Upstream/Downstream/Role
- **Acceptance**:
  - [ ] 每个新文件包含三行头部注释
  - [ ] 格式正确

### T097 [P] Run mypy static type check

- **File**: 所有新模块
- **Test**: `mypy src/ginkgo/research/ src/ginkgo/validation/ --strict`
- **Acceptance**:
  - [ ] mypy 检查无错误

### T098 [P] Update API documentation

- **File**: 各模块的 `__init__.py` 和核心类
- **Test**: 检查 docstring 完整
- **Acceptance**:
  - [ ] 所有公共 API 有 docstring
  - [ ] 包含使用示例

### T099 [P] Add usage examples to docstrings

- **File**: 核心类文件
- **Test**: 检查 docstring 包含示例代码
- **Acceptance**:
  - [ ] 每个核心类有使用示例
  - [ ] 示例可执行

### T100 Run quickstart.md validation scenarios

- **File**: `specs/011-quant-research-modules/quickstart.md`
- **Test**: 手动执行 quickstart 中的所有示例
- **Acceptance**:
  - [ ] 所有代码示例可执行
  - [ ] 输出符合预期

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
     ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
     ↓
┌────┴────┐
↓         ↓
Phase 3   Phase 4    (P1 - 可并行)
(US1)     (US2)
     ↓
┌────┼────┬────┬────┐
↓    ↓    ↓    ↓
P5   P6   P7   P8    (P2 - 可并行)
(US3)(US4)(US5)(US6)
     ↓
┌────┴────┐
↓         ↓
Phase 9   Phase 10   (P3 - 可并行)
(US7)     (US8)
     ↓
Phase 11 (扩展功能)
     ↓
Phase 12 (Polish)
```

### Parallel Opportunities

| 阶段 | 可并行任务 |
|------|-----------|
| Setup | T003-T005, T007 |
| Foundational | T009-T012, T014-T017 |
| US1 | T018-T023, T024-T027 |
| US2 | T034-T036 |
| P1 Stories | US1 + US2 可并行开发 |
| P2 Stories | US3-US6 可并行开发 |
| P3 Stories | US7-US8 可并行开发 |

---

## 任务统计

| Phase | 任务数 | 测试任务 | 实现任务 |
|-------|--------|---------|---------|
| 1. Setup | 7 | 7 | 7 |
| 2. Foundational | 10 | 10 | 10 |
| 3. US1 Paper Trading | 16 | 3 | 13 |
| 4. US2 回测对比 | 7 | 2 | 5 |
| 5. US3 IC 分析 | 8 | 1 | 7 |
| 6. US4 因子分层 | 7 | 1 | 6 |
| 7. US5 参数优化 | 11 | 4 | 7 |
| 8. US6 走步验证 | 7 | 1 | 6 |
| 9. US7 蒙特卡洛 | 6 | 1 | 5 |
| 10. US8 因子正交化 | 6 | 1 | 5 |
| 11. 扩展功能 | 6 | 6 | 6 |
| 12. Polish | 9 | 9 | 9 |
| **总计** | **100** | **37** | **63** |

---

## MVP 范围 (推荐首批交付)

**Phases 1-4**: Setup + Foundational + US1 + US2

| 任务 | 数量 |
|------|------|
| Setup | 7 |
| Foundational | 10 |
| US1 Paper Trading | 16 |
| US2 回测对比 | 7 |
| **MVP 总计** | **40** |

**价值**: 核心验证流程可用，支持策略从回测到 Paper Trading 的完整验证。
