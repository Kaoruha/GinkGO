# API Contracts: Ginkgo 量化研究功能模块

**Date**: 2026-02-16
**Feature**: 011-quant-research-modules

本文档定义新增模块的 Python API 契约。

---

## P0 - Paper Trading API

### PaperTradingEngine

```python
class PaperTradingEngine:
    """Paper Trading 引擎"""

    def __init__(
        self,
        portfolio: Optional[Portfolio] = None,
        slippage_model: str = "percentage",
        slippage_value: float = 0.001,
        commission_rate: float = 0.0003,
        commission_min: float = 5.0
    ) -> None:
        """初始化 Paper Trading 引擎"""

    def load_portfolio(self, portfolio_id: str) -> bool:
        """加载 Portfolio"""
        return bool

    def start(self) -> bool:
        """启动 Paper Trading"""
        return bool

    def stop(self) -> bool:
        """停止 Paper Trading"""
        return bool

    def pause(self) -> bool:
        """暂停 Paper Trading"""
        return bool

    def resume(self) -> bool:
        """恢复 Paper Trading"""
        return bool

    def get_status(self) -> PaperTradingState:
        """获取当前状态"""
        return PaperTradingState

    def get_positions(self) -> List[Position]:
        """获取当前持仓"""
        return List[Position]

    def get_signals(self, start_date: Optional[date] = None) -> List[PaperTradingSignal]:
        """获取信号记录"""
        return List[PaperTradingSignal]

    def compare_with_backtest(self, backtest_id: str) -> ComparisonResult:
        """与回测结果对比"""
        return ComparisonResult

    @property
    def is_running(self) -> bool:
        """是否运行中"""
        return bool
```

### SlippageModel

```python
class SlippageModel(ABC):
    """滑点模型基类"""

    @abstractmethod
    def apply(self, price: Decimal, direction: DIRECTION_TYPES) -> Decimal:
        """应用滑点"""
        return Decimal


class FixedSlippage(SlippageModel):
    """固定滑点"""

    def __init__(self, slippage: float = 0.01) -> None:
        self.slippage = slippage


class PercentageSlippage(SlippageModel):
    """百分比滑点"""

    def __init__(self, percentage: float = 0.001) -> None:
        self.percentage = percentage


class NoSlippage(SlippageModel):
    """无滑点"""
    pass
```

---

## P0 - 回测对比 API

### BacktestComparator

```python
class BacktestComparator:
    """回测对比器"""

    def __init__(self) -> None:
        pass

    def compare(
        self,
        backtest_ids: List[str],
        metrics: Optional[List[str]] = None
    ) -> ComparisonResult:
        """
        对比多个回测结果

        Args:
            backtest_ids: 回测 ID 列表
            metrics: 要对比的指标列表，默认全部

        Returns:
            ComparisonResult: 对比结果
        """
        return ComparisonResult

    def get_net_values(
        self,
        backtest_ids: List[str],
        normalized: bool = True
    ) -> Dict[str, List[Tuple[date, float]]]:
        """获取净值曲线数据"""
        return Dict

    def export_report(
        self,
        result: ComparisonResult,
        format: str = "html",
        output_path: Optional[str] = None
    ) -> str:
        """导出对比报告"""
        return str  # 文件路径
```

---

## P1 - IC 分析 API

### ICAnalyzer

```python
class ICAnalyzer:
    """IC 分析器"""

    def __init__(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame
    ) -> None:
        """
        初始化 IC 分析器

        Args:
            factor_data: 因子数据，columns=[date, code, factor_value]
            return_data: 收益数据，columns=[date, code, return]
        """

    def analyze(
        self,
        periods: List[int] = [1, 5, 10, 20],
        method: str = "pearson"
    ) -> ICAnalysisResult:
        """
        执行 IC 分析

        Args:
            periods: 预测周期列表
            method: 相关性计算方法 ("pearson" | "spearman")

        Returns:
            ICAnalysisResult: IC 分析结果
        """
        return ICAnalysisResult

    def get_statistics(self, period: int) -> ICStatistics:
        """获取指定周期的统计指标"""
        return ICStatistics

    def plot_ic_series(self, period: int) -> "matplotlib.figure.Figure":
        """绘制 IC 时序图"""
        pass

    def plot_ic_distribution(self, period: int) -> "matplotlib.figure.Figure":
        """绘制 IC 分布图"""
        pass
```

---

## P1 - 因子分层 API

### FactorLayering

```python
class FactorLayering:
    """因子分层"""

    def __init__(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame
    ) -> None:
        pass

    def run(
        self,
        n_groups: int = 5,
        rebalance_freq: int = 20
    ) -> LayeringResult:
        """
        执行分层回测

        Args:
            n_groups: 分组数量
            rebalance_freq: 调仓频率（天）

        Returns:
            LayeringResult: 分层结果
        """
        return LayeringResult

    def get_group_returns(self) -> Dict[str, pd.Series]:
        """获取各组收益序列"""
        return Dict

    def get_long_short_return(self) -> pd.Series:
        """获取多空收益"""
        return pd.Series

    def calculate_monotonicity(self) -> float:
        """计算单调性 R²"""
        return float
```

---

## P1 - 因子正交化 API

### FactorOrthogonalizer

```python
class FactorOrthogonalizer:
    """因子正交化"""

    def __init__(self, factor_data: pd.DataFrame) -> None:
        """
        Args:
            factor_data: 多因子数据，columns=[date, code, factor1, factor2, ...]
        """

    def gram_schmidt(self, order: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Gram-Schmidt 正交化

        Args:
            order: 因子顺序，默认按列顺序
        """
        return pd.DataFrame

    def pca(
        self,
        n_components: Optional[int] = None,
        variance_ratio: float = 0.95
    ) -> pd.DataFrame:
        """
        PCA 正交化

        Args:
            n_components: 保留的主成分数
            variance_ratio: 保留的方差比例
        """
        return pd.DataFrame

    def residualize(
        self,
        target: str,
        controls: List[str]
    ) -> pd.DataFrame:
        """
        残差法正交化

        Args:
            target: 目标因子
            controls: 控制因子列表
        """
        return pd.DataFrame

    def get_correlation_matrix(self) -> pd.DataFrame:
        """获取相关系数矩阵"""
        return pd.DataFrame
```

---

## P2 - 参数优化 API

### BaseOptimizer

```python
class BaseOptimizer(ABC):
    """优化器基类"""

    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        param_ranges: Dict[str, ParameterRange],
        target: str = "sharpe_ratio"
    ) -> None:
        pass

    @abstractmethod
    def optimize(
        self,
        data: pd.DataFrame,
        n_jobs: int = 1
    ) -> OptimizationResult:
        """执行优化"""
        return OptimizationResult


class GridSearchOptimizer(BaseOptimizer):
    """网格搜索"""
    pass


class GeneticOptimizer(BaseOptimizer):
    """遗传算法"""

    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        param_ranges: Dict[str, ParameterRange],
        target: str = "sharpe_ratio",
        population_size: int = 50,
        generations: int = 20,
        mutation_rate: float = 0.1
    ) -> None:
        pass


class BayesianOptimizer(BaseOptimizer):
    """贝叶斯优化"""

    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        param_ranges: Dict[str, ParameterRange],
        target: str = "sharpe_ratio",
        n_iterations: int = 50,
        acquisition: str = "ei"
    ) -> None:
        pass
```

---

## P2 - 走步验证 API

### WalkForwardValidator

```python
class WalkForwardValidator:
    """走步验证"""

    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        parameters: Dict[str, Any]
    ) -> None:
        pass

    def validate(
        self,
        data: pd.DataFrame,
        train_size: int = 252,
        test_size: int = 63,
        step_size: int = 21
    ) -> WalkForwardResult:
        """
        执行走步验证

        Args:
            data: 历史数据
            train_size: 训练期（天）
            test_size: 测试期（天）
            step_size: 滑动步长（天）
        """
        return WalkForwardResult

    def calculate_degradation(self) -> float:
        """计算过拟合程度"""
        return float
```

---

## P2 - 蒙特卡洛 API

### MonteCarloSimulator

```python
class MonteCarloSimulator:
    """蒙特卡洛模拟"""

    def __init__(
        self,
        returns: pd.Series,
        n_simulations: int = 10000,
        confidence_level: float = 0.95
    ) -> None:
        pass

    def run(self) -> MonteCarloResult:
        """执行模拟"""
        return MonteCarloResult

    def calculate_var(self, confidence: Optional[float] = None) -> float:
        """计算 VaR"""
        return float

    def calculate_cvar(self, confidence: Optional[float] = None) -> float:
        """计算 CVaR"""
        return float

    def plot_distribution(self) -> "matplotlib.figure.Figure":
        """绘制收益分布图"""
        pass
```

---

## Container 注册契约

```python
# ginkgo/trading/paper/containers.py
class PaperContainer(containers.DeclarativeContainer):
    engine = providers.Singleton(PaperTradingEngine)
    slippage = providers.Factory(PercentageSlippage)


# ginkgo/research/containers.py
class ResearchContainer(containers.DeclarativeContainer):
    ic_analyzer = providers.Singleton(ICAnalyzer)
    layering = providers.Singleton(FactorLayering)
    orthogonalizer = providers.Singleton(FactorOrthogonalizer)
    # ...


# ginkgo/validation/containers.py
class ValidationContainer(containers.DeclarativeContainer):
    walk_forward = providers.Singleton(WalkForwardValidator)
    monte_carlo = providers.Singleton(MonteCarloSimulator)
    # ...


# ginkgo/trading/optimization/containers.py
class OptimizationContainer(containers.DeclarativeContainer):
    grid_search = providers.Singleton(GridSearchOptimizer)
    genetic = providers.Singleton(GeneticOptimizer)
    bayesian = providers.Singleton(BayesianOptimizer)
```

---

## ServiceHub 扩展契约

```python
# ginkgo/service_hub.py
class ServiceHub:
    @property
    def research(self) -> ResearchContainer:
        """因子研究模块"""
        pass

    @property
    def validation(self) -> ValidationContainer:
        """策略验证模块"""
        pass

    # 扩展现有 trading 属性
    # trading.paper -> PaperContainer
    # trading.comparison -> ComparisonContainer
    # trading.optimization -> OptimizationContainer
```
