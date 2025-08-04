"""
The MatrixEngine class provides a high-performance, vectorized backtesting engine.
It operates on entire matrices of data at once, rather than processing event by event,
making it orders of magnitude faster for many common strategy types.

The workflow is as follows:
1. Fetch all necessary data for the given time range into pandas DataFrames.
2. Generate a "universe mask" based on the provided selector.
3. Generate signal matrices from all provided strategies.
4. Aggregate signals and apply risk management rules (as filters).
5. Calculate target positions based on the final signals and the sizer.
6. Run the simulation to generate portfolio returns and equity curve.
7. Calculate performance metrics using the existing Analyzer components.
"""

import pandas as pd
import numpy as np
from datetime import datetime

from ginkgo.backtest.execution.engines.base_engine import BaseEngine
from ginkgo.backtest.core.backtest_base import BacktestBase
from ginkgo.data.containers import container
from ginkgo.libs import GLOG
from ginkgo.backtest.strategy.selectors.base_selector import SelectorBase
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
from ginkgo.backtest.strategy.risk_managements.base_risk import RiskManagementBase
from ginkgo.backtest.strategy.sizers.base_sizer import SizerBase
from ginkgo.backtest.execution.portfolios.base_portfolio import PortfolioBase
from ginkgo.backtest.analysis.analyzers import *  # Import all available analyzers


class MatrixEngine(BaseEngine):
    def __init__(self, name: str = "MatrixEngine", *args, **kwargs):
        super(MatrixEngine, self).__init__(name, *args, **kwargs)

    def run(
        self,
        start_date: str,
        end_date: str,
        selector: SelectorBase,
        strategies: list[StrategyBase],
        portfolio: PortfolioBase,
        risk_managements: list[RiskManagementBase] = [],
        sizer: SizerBase = None,
    ):
        """
        Main method to run the vectorized backtest.
        """
        self.log(f"MatrixEngine Start. From {start_date} to {end_date}.")
        self.start()

        # 1. Fetch and Prepare Data
        self.log("Fetching and preparing data...")
        all_data = self._fetch_and_prepare_data(start_date, end_date)
        if all_data is None or all_data["close"].empty:
            self.log("No data found for the given period. Backtest stopped.", "ERROR")
            self.stop()
            return None

        # 2. Generate Universe Mask
        self.log("Generating universe mask...")
        universe_mask = self._generate_universe_mask(selector, all_data)

        # 3. Generate and Aggregate Signals
        self.log("Generating and aggregating signals...")
        combined_signals = self._generate_signals(strategies, all_data)

        # 4. Apply Universe and Risk Management
        self.log("Applying universe and risk management filters...")
        final_signals = self._apply_risk_and_universe(combined_signals, universe_mask, risk_managements, all_data)

        # 5. Calculate Target Positions
        self.log("Calculating target positions...")
        target_positions = self._calculate_target_positions(final_signals, sizer, all_data, portfolio.initial_capital)

        # 6. Run Simulation
        self.log("Running simulation...")
        equity_curve, returns = self._run_simulation(target_positions, all_data, portfolio.initial_capital)

        # 7. Analyze Performance
        self.log("Analyzing performance...")
        results = self._analyze_performance(equity_curve, returns)
        results["equity_curve"] = equity_curve

        self.log("MatrixEngine Finished.")
        self.stop()
        return results

    def _fetch_and_prepare_data(self, start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
        """
        Fetches data from ClickHouse using the existing CRUD layer and pivots it
        into a matrix format (dates x codes).
        """
        # We can pass a code list from selector if it's a fixed one for optimization
        bar_crud = container.cruds.bar()
        raw_df = bar_crud.get_bar_df_by_time_range(start=start_date, end=end_date)

        if raw_df.empty:
            return None

        # Pivot the DataFrame for each required column
        data_matrices = {}
        columns_to_pivot = ["open", "high", "low", "close", "volume"]
        for col in columns_to_pivot:
            try:
                # Use pivot_table for robustness against duplicate index entries
                matrix = raw_df.pivot_table(index="trade_date", columns="code", values=col)
                # Ensure the datetime index is sorted
                matrix.index = pd.to_datetime(matrix.index)
                matrix = matrix.sort_index()
                data_matrices[col] = matrix
            except Exception as e:
                self.log(f"Could not pivot column {col}. Error: {e}", "ERROR")
                return None

        return data_matrices

    def _generate_universe_mask(self, selector: SelectorBase, all_data: dict) -> pd.DataFrame:
        """
        Generates the boolean universe mask.
        Assumes the selector has a 'cal_vectorized' method.
        """
        if not hasattr(selector, "cal_vectorized"):
            self.log(
                f"Selector {selector.name} has no 'cal_vectorized' method. Assuming all stocks are in universe.", "WARN"
            )
            return pd.DataFrame(True, index=all_data["close"].index, columns=all_data["close"].columns)

        self.log(f"Using selector: {selector.name}")
        mask = selector.cal_vectorized(all_data)
        # Ensure mask aligns with data, filling missing values with False
        return mask.reindex_like(all_data["close"]).fillna(False)

    def _generate_signals(self, strategies: list[StrategyBase], all_data: dict) -> pd.DataFrame:
        """
        Generates signals from all strategies and aggregates them.
        Assumes strategies have a 'cal_vectorized' method.
        """
        all_signals = []
        for strategy in strategies:
            if hasattr(strategy, "cal_vectorized"):
                self.log(f"Calculating signals for strategy: {strategy.name}")
                signal = strategy.cal_vectorized(all_data)
                all_signals.append(signal)
            else:
                self.log(f"Strategy {strategy.name} has no 'cal_vectorized' method and will be skipped.", "WARN")

        if not all_signals:
            self.log("No valid vectorized strategies found. No signals generated.", "ERROR")
            # Return a DataFrame of zeros
            return pd.DataFrame(0, index=all_data["close"].index, columns=all_data["close"].columns)

        # Aggregate signals by simple addition
        combined_signals = sum(all_signals).fillna(0)
        return combined_signals

    def _apply_risk_and_universe(
        self, signals: pd.DataFrame, mask: pd.DataFrame, risk_managements: list, all_data: dict
    ) -> pd.DataFrame:
        """
        Applies the universe mask and then sequentially applies risk management filters.
        """
        # First, apply the universe mask
        filtered_signals = signals * mask

        # Then, apply risk management rules
        for rm in risk_managements:
            if hasattr(rm, "cal_vectorized"):
                self.log(f"Applying risk management: {rm.name}")
                filtered_signals = rm.cal_vectorized(filtered_signals, all_data)
            else:
                self.log(f"Risk management {rm.name} has no 'cal_vectorized' method and will be skipped.", "WARN")

        return filtered_signals

    def _calculate_target_positions(
        self, signals: pd.DataFrame, sizer: SizerBase, all_data: dict, initial_capital: float
    ) -> pd.DataFrame:
        """
        Converts final signals into target positions (weights).
        This is a simplified implementation.
        """
        if sizer and hasattr(sizer, "cal_vectorized"):
            self.log(f"Using sizer: {sizer.name}")
            return sizer.cal_vectorized(signals, all_data, initial_capital)
        else:
            self.log("No vectorized sizer found. Using equal weight sizing.", "WARN")
            # Simplified equal-weight sizer: normalize signals to sum to 1 daily
            daily_signal_abs_sum = signals.abs().sum(axis=1)
            # Avoid division by zero
            daily_signal_abs_sum[daily_signal_abs_sum == 0] = 1.0
            target_weights = signals.div(daily_signal_abs_sum, axis=0)
            return target_weights

    def _run_simulation(
        self, positions: pd.DataFrame, all_data: dict, initial_capital: float
    ) -> tuple[pd.Series, pd.Series]:
        """
        Runs the core simulation loop to calculate returns and equity.
        NOTE: This simplified version assumes next-day execution and ignores transaction costs.
        """
        # We can only act on yesterday's signal, so shift positions by 1 day.
        # The first day's position is always zero.
        executable_positions = positions.shift(1).fillna(0)

        # Calculate daily returns of each asset
        asset_returns = all_data["close"].pct_change().fillna(0)

        # Portfolio daily returns are the sum of asset returns weighted by their positions
        portfolio_returns = (asset_returns * executable_positions).sum(axis=1)

        # Calculate the equity curve
        equity_curve = (1 + portfolio_returns).cumprod() * initial_capital

        # Prepend the initial capital value at the start date
        start_date_dt = pd.to_datetime(equity_curve.index.min()) - pd.Timedelta(days=1)
        initial_equity = pd.Series([initial_capital], index=[start_date_dt])
        equity_curve = pd.concat([initial_equity, equity_curve])

        return equity_curve, portfolio_returns

    def _analyze_performance(self, equity_curve: pd.Series, returns: pd.Series) -> dict:
        """
        Uses the existing Analyzer classes to calculate performance metrics.
        """
        # This demonstrates the power of reusing your existing components.
        # We just need to feed them the results of our vectorized backtest.
        results = {}

        # Example for a few analyzers. You can extend this list.
        analyzers_to_run = {
            "sharpe_ratio": SharpeRatio,
            "max_drawdown": MaxDrawdown,
            "annualized_returns": AnnualizedReturns,
            "profit": Profit,
            "winloss_ratio": WinLossRatio,
        }

        for name, analyzer_class in analyzers_to_run.items():
            analyzer = analyzer_class()
            # Each analyzer might need a different input (equity, returns, etc.)
            # This part needs to be adapted to the actual interface of your analyzers.
            # For this example, I assume they have a `cal` method that takes the returns series.
            try:
                # A more robust implementation would inspect the `cal` method signature
                # and pass the correct arguments (equity_curve, returns, etc.)
                # For now, we'll assume they work with the returns series.
                metric_value = analyzer.cal(returns)
                results[name] = metric_value
                self.log(f"Calculated {name}: {metric_value}")
            except Exception as e:
                self.log(f"Could not run analyzer {name}. Error: {e}", "WARN")

        return results
