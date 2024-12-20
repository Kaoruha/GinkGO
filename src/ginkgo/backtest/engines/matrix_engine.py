"""
The MatrixBacktest class will provide a way to run a matrix backtest, which involves testing multiple variations of a given strategy across a range of parameter values.

- Defining the parameters to test and the range of values to test them across.

- Running the backtest for each combination of parameter values.

- Generating reports and metrics related to the performance of the backtesting system for each combination of parameter values.
"""

from ginkgo.backtest.engine.base_engine import BaseEngine


class MatrixEngine(BaseEngine):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(MatrixEngine, self).__init__(name, *args, **kwargs)
        self.strategy = None
        self.data = None
