"""
The MatrixBacktest class will provide a way to run a matrix backtest, which involves testing multiple variations of a given strategy across a range of parameter values.

- Defining the parameters to test and the range of values to test them across.

- Running the backtest for each combination of parameter values.

- Generating reports and metrics related to the performance of the backtesting system for each combination of parameter values.
"""
from ginkgo.backtest.engine.base_engine import BaseEngine


class MatrixEngine(BaseEngine):
    __abstract__ = False
    pass
