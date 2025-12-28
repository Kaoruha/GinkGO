"""
Unit tests for logical validation rules.

Tests for business logic validation rules in strategy evaluation.
"""

import ast
import pytest

from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel, EvaluationSeverity
from ginkgo.trading.evaluation.rules.base_rule import BaseRule


@pytest.mark.unit
@pytest.mark.tdd
class TestSignalFieldRule:
    """Test cases for SignalFieldRule - validates Signal field requirements."""

    def test_signal_with_all_required_fields_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that a Signal with all required fields (code, direction, reason) passes validation.
        """
        # TODO: 实现SignalFieldRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # signal = Signal(
        #     code="000001.SZ",
        #     direction=DIRECTION_TYPES.LONG,
        #     reason="Test signal"
        # )
        # """
        # tree = ast.parse(code)
        # rule = SignalFieldRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_signal_missing_code_field_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that a Signal without code field fails validation.
        """
        # TODO: 实现SignalFieldRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # signal = Signal(
        #     direction=DIRECTION_TYPES.LONG,
        #     reason="Missing code"
        # )
        # """
        # tree = ast.parse(code)
        # rule = SignalFieldRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("code" in issue.message.lower() for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_signal_missing_direction_field_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that a Signal without direction field fails validation.
        """
        # TODO: 实现SignalFieldRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        #
        # signal = Signal(
        #     code="000001.SZ",
        #     reason="Missing direction"
        # )
        # """
        # tree = ast.parse(code)
        # rule = SignalFieldRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("direction" in issue.message.lower() for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_signal_in_function_call_detected(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that Signal() calls in cal() method are detected and validated.
        """
        # TODO: 实现SignalFieldRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         return [Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)]
        # """
        # tree = ast.parse(code)
        # rule = SignalFieldRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_signal_with_extra_fields_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that Signal with extra optional fields passes validation.
        """
        # TODO: 实现SignalFieldRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # signal = Signal(
        #     code="000001.SZ",
        #     direction=DIRECTION_TYPES.LONG,
        #     reason="Test",
        #     volume=1000,
        #     price=10.5
        # )
        # """
        # tree = ast.parse(code)
        # rule = SignalFieldRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
@pytest.mark.tdd
class TestDirectionValidationRule:
    """Test cases for DirectionValidationRule - validates DIRECTION_TYPES usage."""

    def test_valid_direction_long_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that DIRECTION_TYPES.LONG is valid.
        """
        # TODO: 实现DirectionValidationRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        # """
        # tree = ast.parse(code)
        # rule = DirectionValidationRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_valid_direction_short_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that DIRECTION_TYPES.SHORT is valid.
        """
        # TODO: 实现DirectionValidationRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT)
        # """
        # tree = ast.parse(code)
        # rule = DirectionValidationRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_invalid_string_direction_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that using string instead of enum fails validation.
        """
        # TODO: 实现DirectionValidationRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        #
        # signal = Signal(code="000001.SZ", direction="LONG")
        # """
        # tree = ast.parse(code)
        # rule = DirectionValidationRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("DIRECTION_TYPES" in issue.message for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_missing_direction_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that missing direction parameter fails validation.
        """
        # TODO: 实现DirectionValidationRule后取消注释
        # code = """
        # from ginkgo.trading.entities import Signal
        #
        # signal = Signal(code="000001.SZ")
        # """
        # tree = ast.parse(code)
        # rule = DirectionValidationRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_multiple_signals_all_validated(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that all Signal() calls in strategy are validated.
        """
        # TODO: 实现DirectionValidationRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         return [
        #             Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG),
        #             Signal(code="000002.SZ", direction=DIRECTION_TYPES.SHORT)
        #         ]
        # """
        # tree = ast.parse(code)
        # rule = DirectionValidationRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
@pytest.mark.tdd
class TestTimeProviderUsageRule:
    """Test cases for TimeProviderUsageRule - validates time retrieval methods."""

    def test_get_time_provider_usage_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that using self.get_time_provider() passes validation.
        """
        # TODO: 实现TimeProviderUsageRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         tp = self.get_time_provider()
        #         current_time = tp.now()
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = TimeProviderUsageRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_datetime_now_usage_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that using datetime.now() fails validation.
        """
        # TODO: 实现TimeProviderUsageRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # import datetime
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         current_time = datetime.now()
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = TimeProviderUsageRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("get_time_provider" in issue.message.lower() for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_time_time_usage_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that using time.time() fails validation.
        """
        # TODO: 实现TimeProviderUsageRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # import time
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         current_time = time.time()
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = TimeProviderUsageRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_time_usage_in_other_methods_allowed(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that time usage in methods other than cal() is allowed.
        """
        # TODO: 实现TimeProviderUsageRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # import time
        #
        # class TestStrategy(BaseStrategy):
        #     def __init__(self):
        #         self.init_time = time.time()
        #
        #     def cal(self, portfolio_info, event):
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = TimeProviderUsageRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_event_timestamp_usage_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that using event.timestamp is valid for time retrieval.
        """
        # TODO: 实现TimeProviderUsageRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         current_time = event.timestamp
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = TimeProviderUsageRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
@pytest.mark.tdd
class TestReturnStatementRule:
    """Test cases for ReturnStatementRule - validates cal() return statement."""

    def test_returns_list_of_signals_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that returning List[Signal] passes validation.
        """
        # TODO: 实现ReturnStatementRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        # from typing import List
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event) -> List[Signal]:
        #         return [Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)]
        # """
        # tree = ast.parse(code)
        # rule = ReturnStatementRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_returns_empty_list_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that returning empty list passes validation.
        """
        # TODO: 实现ReturnStatementRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # from typing import List
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = ReturnStatementRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_returns_none_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that returning None fails validation.
        """
        # TODO: 实现ReturnStatementRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         return None
        # """
        # tree = ast.parse(code)
        # rule = ReturnStatementRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("return" in issue.message.lower() for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_returns_single_signal_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that returning single Signal (not in list) fails validation.
        """
        # TODO: 实现ReturnStatementRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         return Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        # """
        # tree = ast.parse(code)
        # rule = ReturnStatementRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_no_return_statement_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that missing return statement fails validation.
        """
        # TODO: 实现ReturnStatementRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         pass
        # """
        # tree = ast.parse(code)
        # rule = ReturnStatementRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("return" in issue.message.lower() for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_conditional_return_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that conditional returns with List[Signal] pass validation.
        """
        # TODO: 实现ReturnStatementRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        # from ginkgo.trading.entities import Signal
        # from ginkgo.trading.enums import DIRECTION_TYPES
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         if True:
        #             return []
        #         else:
        #             return [Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)]
        # """
        # tree = ast.parse(code)
        # rule = ReturnStatementRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
@pytest.mark.tdd
class TestForbiddenOperationsRule:
    """Test cases for ForbiddenOperationsRule - detects forbidden operations in cal()."""

    def test_database_query_in_cal_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that database queries in cal() fail validation.
        """
        # TODO: 实现ForbiddenOperationsRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         from ginkgo import services
        #         bars = services.data.cruds.bar().get_bars()
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = ForbiddenOperationsRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("database" in issue.message.lower() or "query" in issue.message.lower()
        #            for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_network_call_in_cal_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that network calls (requests, etc.) in cal() fail validation.
        """
        # TODO: 实现ForbiddenOperationsRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         import requests
        #         response = requests.get("http://api.example.com")
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = ForbiddenOperationsRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("network" in issue.message.lower() or "request" in issue.message.lower()
        #            for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_file_io_in_cal_fails(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that file I/O operations in cal() fail validation.
        """
        # TODO: 实现ForbiddenOperationsRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         with open("data.txt", "r") as f:
        #             data = f.read()
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = ForbiddenOperationsRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert not result.passed
        # assert any("file" in issue.message.lower() or "io" in issue.message.lower()
        #            for issue in result.issues)
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_data_feeder_usage_passes(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that using self.data_feeder is allowed (it's the proper way).
        """
        # TODO: 实现ForbiddenOperationsRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def cal(self, portfolio_info, event):
        #         bars = self.data_feeder.get_bars("000001.SZ")
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = ForbiddenOperationsRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"

    def test_forbidden_operations_in_init_allowed(self):
        """
        TDD Red阶段：测试用例尚未实现

        Test that forbidden operations in __init__ are allowed.
        """
        # TODO: 实现ForbiddenOperationsRule后取消注释
        # code = """
        # from ginkgo.trading.strategies.base_strategy import BaseStrategy
        #
        # class TestStrategy(BaseStrategy):
        #     def __init__(self):
        #         super().__init__()
        #         with open("config.txt", "r") as f:
        #             self.config = f.read()
        #
        #     def cal(self, portfolio_info, event):
        #         return []
        # """
        # tree = ast.parse(code)
        # rule = ForbiddenOperationsRule()
        # result = rule.check(tree, "test_strategy.py")
        # assert result.passed
        assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
@pytest.mark.tdd
class TestSignalParameterRule:
    """Test cases for SignalParameterRule - validates Signal parameter names."""

    def test_signal_with_business_timestamp_passes(self):
        """
        Test that Signal using business_timestamp parameter passes validation.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import SignalParameterRule

        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES

class TestStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        return [Signal(
            portfolio_id=portfolio_info.get("uuid"),
            engine_id=self.engine_id,
            run_id=self.run_id,
            business_timestamp=portfolio_info.get("now"),
            code=event.code,
            direction=DIRECTION_TYPES.LONG,
            reason="Test"
        )]
"""
        tree = ast.parse(code)
        rule = SignalParameterRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is None  # No issues

    def test_signal_with_timestamp_parameter_fails(self):
        """
        Test that Signal using incorrect 'timestamp' parameter fails validation.

        This is the key test - using 'timestamp' instead of 'business_timestamp'
        causes signal.business_timestamp to be None, leading to database validation errors.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import SignalParameterRule

        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES

class TestStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        return [Signal(
            timestamp=portfolio_info.get("now"),  # WRONG!
            code=event.code,
            direction=DIRECTION_TYPES.LONG
        )]
"""
        tree = ast.parse(code)
        rule = SignalParameterRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is not None
        assert "business_timestamp" in result.message
        assert "timestamp" in result.message

    def test_signal_missing_recommended_params_warns(self):
        """
        Test that Signal missing recommended parameters (portfolio_id, etc.) generates warning.

        This should be a warning, not an error, as some strategies might work without these.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import SignalParameterRule

        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES

class TestStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        return [Signal(
            business_timestamp=portfolio_info.get("now"),
            code=event.code,
            direction=DIRECTION_TYPES.LONG
        )]
"""
        tree = ast.parse(code)
        rule = SignalParameterRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is not None
        assert "missing recommended parameters" in result.message
        assert "portfolio_id" in result.message

    def test_multiple_signals_all_validated(self):
        """
        Test that all Signal() calls in cal() are validated.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import SignalParameterRule

        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES

class TestStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        return [
            Signal(timestamp=portfolio_info.get("now"), code="A", direction=DIRECTION_TYPES.LONG),
            Signal(timestamp=portfolio_info.get("now"), code="B", direction=DIRECTION_TYPES.SHORT)
        ]
"""
        tree = ast.parse(code)
        rule = SignalParameterRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is not None
        assert "timestamp" in result.message

    def test_rule_severity_is_error(self):
        """Test that SignalParameterRule has ERROR severity."""
        from ginkgo.trading.evaluation.rules.logical_rules import SignalParameterRule
        from ginkgo.trading.evaluation.core.enums import EvaluationSeverity

        rule = SignalParameterRule()
        assert rule.severity == EvaluationSeverity.ERROR

    def test_rule_id_is_correct(self):
        """Test that SignalParameterRule has correct rule_id."""
        from ginkgo.trading.evaluation.rules.logical_rules import SignalParameterRule

        rule = SignalParameterRule()
        assert rule.rule_id == "SIGNAL_PARAMETER"


@pytest.mark.unit
@pytest.mark.tdd
class TestForbiddenDirectDataAccessRule:
    """Test cases for ForbiddenDirectDataAccessRule - prevents direct data imports."""

    def test_no_forbidden_imports_passes(self):
        """Test that strategies without forbidden data imports pass validation."""
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        tree = ast.parse(code)
        rule = ForbiddenDirectDataAccessRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is None

    def test_forbidden_get_bars_import_fails(self):
        """Test that 'from ginkgo.data import get_bars' fails validation."""
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        code = """
from ginkgo.data import get_bars
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        bars = get_bars("000001.SZ", ...)
        return []
"""
        tree = ast.parse(code)
        rule = ForbiddenDirectDataAccessRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is not None
        assert result.code == "FORBIDDEN_DIRECT_DATA_ACCESS"
        assert "get_bars" in result.message
        assert "data_feeder" in result.suggestion.lower()

    def test_forbidden_multiple_data_imports_fails(self):
        """Test that multiple forbidden data imports are detected."""
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        code = """
from ginkgo.data import get_bars, get_daybar, get_tick
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        tree = ast.parse(code)
        rule = ForbiddenDirectDataAccessRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is not None
        assert result.code == "FORBIDDEN_DIRECT_DATA_ACCESS"
        assert "get_bars" in result.message

    def test_allowed_ginkgo_imports_pass(self):
        """Test that allowed imports from ginkgo modules pass validation."""
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.enums import DIRECTION_TYPES

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return [Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)]
"""
        tree = ast.parse(code)
        rule = ForbiddenDirectDataAccessRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is None

    def test_import_from_other_modules_passes(self):
        """Test that imports from other modules (not ginkgo.data) pass validation."""
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        code = """
from pandas import DataFrame
from numpy import array
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        tree = ast.parse(code)
        rule = ForbiddenDirectDataAccessRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is None

    def test_forbidden_add_bars_import_fails(self):
        """Test that 'from ginkgo.data import add_bars' fails validation."""
        from pathlib import Path
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        code = """
from ginkgo.data import add_bars
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        tree = ast.parse(code)
        rule = ForbiddenDirectDataAccessRule()
        result = rule.check_ast(tree, Path("test_strategy.py"), code)
        assert result is not None
        assert result.code == "FORBIDDEN_DIRECT_DATA_ACCESS"
        assert "add_bars" in result.message

    def test_rule_severity_is_error(self):
        """Test that ForbiddenDirectDataAccessRule has ERROR severity."""
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule
        from ginkgo.trading.evaluation.core.enums import EvaluationSeverity

        rule = ForbiddenDirectDataAccessRule()
        assert rule.severity == EvaluationSeverity.ERROR

    def test_rule_id_is_correct(self):
        """Test that ForbiddenDirectDataAccessRule has correct rule_id."""
        from ginkgo.trading.evaluation.rules.logical_rules import ForbiddenDirectDataAccessRule

        rule = ForbiddenDirectDataAccessRule()
        assert rule.rule_id == "FORBIDDEN_DIRECT_DATA_ACCESS"
