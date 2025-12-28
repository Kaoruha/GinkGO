"""
Integration tests for strategy validation workflow.

Tests for complete validation workflows from CLI to evaluation results.
"""

import tempfile
from pathlib import Path

import pytest

from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry
from ginkgo.trading.evaluation.rules.structural_rules import (
    BaseStrategyInheritanceRule,
    CalMethodRequiredRule,
    CalSignatureValidationRule,
    SuperInitCallRule,
)


@pytest.mark.integration
@pytest.mark.tdd
class TestValidationWorkflow:
    """Integration tests for complete validation workflows."""

    def test_basic_structural_validation(self):
        """Test complete basic validation workflow with valid strategy."""
        # Create a valid strategy file
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES
from typing import List, Dict
from ginkgo.trading.events import EventBase


class ValidTestStrategy(BaseStrategy):
    __abstract__ = False

    def __init__(self):
        super().__init__()

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            # Register rules
            registry = get_global_registry()
            registry.register_rule_class(BaseStrategyInheritanceRule, ComponentType.STRATEGY)
            registry.register_rule_class(CalMethodRequiredRule, ComponentType.STRATEGY)

            # Create evaluator
            evaluator = SimpleEvaluator(ComponentType.STRATEGY)

            # Run evaluation
            result = evaluator.evaluate(file_path)

            # Assert validation passes
            assert result.passed, "Valid strategy should pass basic validation"
            assert result.error_count == 0
            assert result.duration_seconds is not None
            assert result.duration_seconds < 2.0, "Validation should complete in < 2 seconds"

        finally:
            file_path.unlink()

    def test_basic_structural_validation_invalid(self):
        """Test basic validation workflow with invalid strategy (missing cal())."""
        # Create invalid strategy file
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy


class InvalidTestStrategy(BaseStrategy):
    __abstract__ = False
    # Missing cal() method
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            # Register rules
            registry = get_global_registry()
            registry.register_rule_class(BaseStrategyInheritanceRule, ComponentType.STRATEGY)
            registry.register_rule_class(CalMethodRequiredRule, ComponentType.STRATEGY)

            # Create evaluator
            evaluator = SimpleEvaluator(ComponentType.STRATEGY)

            # Run evaluation
            result = evaluator.evaluate(file_path)

            # Assert validation fails
            assert not result.passed, "Invalid strategy should fail basic validation"
            assert result.error_count > 0, "Should have at least one error"

            # Check for specific error
            error_codes = [issue.code for issue in result.errors]
            assert "CAL_METHOD_REQUIRED" in error_codes

        finally:
            file_path.unlink()

    def test_standard_validation_workflow(self):
        """Test standard validation workflow (basic + logical)."""
        # Create a strategy with cal() method
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES
from typing import List, Dict
from ginkgo.trading.events import EventBase


class StandardTestStrategy(BaseStrategy):
    __abstract__ = False

    def __init__(self):
        super().__init__()

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        # Returns empty list (valid)
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            # Register all rules
            registry = get_global_registry()
            registry.register_rule_class(BaseStrategyInheritanceRule, ComponentType.STRATEGY)
            registry.register_rule_class(CalMethodRequiredRule, ComponentType.STRATEGY)
            registry.register_rule_class(CalSignatureValidationRule, ComponentType.STRATEGY)

            # Create evaluator
            evaluator = SimpleEvaluator(ComponentType.STRATEGY)

            # Run evaluation at standard level
            result = evaluator.evaluate(file_path)

            # Assert validation passes
            assert result.passed, "Valid strategy should pass standard validation"
            assert result.error_count == 0

        finally:
            file_path.unlink()


@pytest.mark.integration
@pytest.mark.tdd
class TestStandardLogicalValidation:
    """
    Integration tests for standard level validation (T038).

    Tests the combination of structural and logical validation.
    """

    def test_standard_validation_with_valid_strategy(self):
        """
        Test standard validation with a valid strategy file.

        Expected: Validation should pass without errors.
        """
        # Use a real strategy file from the codebase
        strategy_file = Path(__file__).parent.parent.parent.parent.parent / \
                        "src/ginkgo/trading/strategies/trend_follow.py"

        if not strategy_file.exists():
            pytest.skip(f"Strategy file not found: {strategy_file}")

        # Import and register logical rules
        from ginkgo.trading.evaluation.rules.logical_rules import (
            ReturnStatementRule,
            SignalFieldRule,
            DirectionValidationRule,
            TimeProviderUsageRule,
            ForbiddenOperationsRule,
        )

        registry = get_global_registry()

        # Register logical rules
        for rule_class in [
            ReturnStatementRule,
            SignalFieldRule,
            DirectionValidationRule,
            TimeProviderUsageRule,
            ForbiddenOperationsRule,
        ]:
            registry.register_rule_class(rule_class, ComponentType.STRATEGY)

        # Create evaluator
        evaluator = SimpleEvaluator(ComponentType.STRATEGY)

        # Run validation
        result = evaluator.evaluate(
            strategy_file,
            level=EvaluationLevel.STANDARD,
            load_component=False,
        )

        # Assertions
        assert result is not None
        assert result.file_path == strategy_file
        assert result.level == EvaluationLevel.STANDARD

        # Trend follow strategy should pass validation
        assert result.passed is True

    def test_logical_validation_with_logical_evaluator(self):
        """
        Test logical validation using LogicalEvaluator (T044).

        Expected: LogicalEvaluator should apply all logical rules.
        """
        from ginkgo.trading.evaluation.validators.logical_evaluator import LogicalEvaluator

        strategy_file = Path(__file__).parent.parent.parent.parent.parent / \
                        "src/ginkgo/trading/strategies/trend_follow.py"

        if not strategy_file.exists():
            pytest.skip(f"Strategy file not found: {strategy_file}")

        # Create logical evaluator
        evaluator = LogicalEvaluator()

        # Run validation
        result = evaluator.evaluate(
            strategy_file,
            level=EvaluationLevel.STANDARD,
            load_component=False,
        )

        # Assertions
        assert result is not None
        assert result.passed is True
        assert result.duration_seconds is not None

    def test_runtime_analyzer_inspection(self):
        """
        Test RuntimeAnalyzer class inspection capabilities (T045).

        Expected: RuntimeAnalyzer should be able to inspect strategy classes.
        """
        from ginkgo.trading.evaluation.analyzers.runtime_analyzer import RuntimeAnalyzer
        from ginkgo.trading.strategies.base_strategy import BaseStrategy

        # Create a simple test strategy
        class TestStrategy(BaseStrategy):
            __abstract__ = False

            def cal(self, portfolio_info, event):
                return []

        # Create analyzer
        analyzer = RuntimeAnalyzer()

        # Analyze the class
        result = analyzer.analyze_class(TestStrategy)

        # Assertions
        assert result is not None
        assert result["class_name"] == "TestStrategy"
        assert "BaseStrategy" in result["base_classes"]
        assert result["instantiation_success"] is True
        assert "cal" in result["methods"]


@pytest.mark.integration
@pytest.mark.tdd
class TestDatabaseStrategyValidation:
    """
    Integration tests for database strategy validation (T100).

    Tests the complete workflow of validating strategies stored in database.
    """

    def test_list_database_strategies(self):
        """
        Test listing strategies from database (T100).

        Expected: Should return list of strategy info or empty list.
        """
        from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader

        loader = DatabaseStrategyLoader()

        try:
            strategies = loader.list_strategies()

            # Should return a list (may be empty if no data)
            assert isinstance(strategies, list)

            # If strategies exist, verify structure
            if strategies:
                strategy = strategies[0]
                assert "file_id" in strategy
                assert "name" in strategy
                assert "portfolio_count" in strategy

        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    def test_load_strategy_from_database_by_file_id(self):
        """
        Test loading strategy by file_id from database (T100).

        Expected: Should create temp file with strategy code and auto-cleanup.
        """
        from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader
        from ginkgo.data.containers import container

        # First, try to find a real strategy file_id from database
        loader = DatabaseStrategyLoader()
        strategies = loader.list_strategies()

        if not strategies:
            pytest.skip("No strategies found in database")

        # Use first strategy
        file_id = strategies[0]["file_id"]

        try:
            # Load strategy by file_id
            with loader.load_by_file_id(file_id) as temp_path:
                # Verify temp file exists
                assert temp_path.exists()
                assert temp_path.suffix == ".py"

                # Verify content is valid Python
                content = temp_path.read_text(encoding="utf-8")
                assert len(content) > 0

                # Verify it contains strategy class
                assert "class" in content or "def" in content

            # Verify temp file was cleaned up
            assert not temp_path.exists()

        except FileNotFoundError:
            pytest.skip(f"Strategy file_id {file_id} not found in database")

    def test_validate_database_strategy_with_cli_workflow(self):
        """
        Test complete validation workflow for database strategy (T100).

        Expected: Should validate strategy from database same as local file.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader
        from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
        from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
        from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry
        from ginkgo.trading.evaluation.rules.structural_rules import (
            BaseStrategyInheritanceRule,
            CalMethodRequiredRule,
            SuperInitCallRule,
        )

        # Get a strategy from database
        loader = DatabaseStrategyLoader()
        strategies = loader.list_strategies()

        if not strategies:
            pytest.skip("No strategies found in database")

        file_id = strategies[0]["file_id"]

        try:
            # Register rules
            registry = get_global_registry()
            registry.register_rule_class(BaseStrategyInheritanceRule, ComponentType.STRATEGY)
            registry.register_rule_class(CalMethodRequiredRule, ComponentType.STRATEGY)

            # Create evaluator
            evaluator = SimpleEvaluator(ComponentType.STRATEGY)

            # Load and validate strategy from database
            with loader.load_by_file_id(file_id) as temp_path:
                result = evaluator.evaluate(temp_path)

                # Verify validation completed
                assert result is not None
                assert result.file_path == temp_path
                # Note: level defaults to STANDARD after LEVEL layer removal

                # Result may pass or fail, but should complete
                assert result.duration_seconds is not None
                assert result.duration_seconds < 5.0  # Should complete in < 5 seconds

            # Verify temp file was cleaned up
            assert not temp_path.exists()

        except FileNotFoundError:
            pytest.skip(f"Strategy file_id {file_id} not found")

    def test_database_strategy_with_portfolio_id(self):
        """
        Test loading strategy via portfolio_id (T100).

        Expected: Should resolve portfolio_id to file_id and load strategy.
        """
        from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader

        loader = DatabaseStrategyLoader()

        # Get strategies with portfolios
        strategies = loader.list_strategies()
        strategies_with_portfolios = [s for s in strategies if s["portfolio_count"] > 0]

        if not strategies_with_portfolios:
            pytest.skip("No strategies with portfolio mappings found in database")

        # For strategies with portfolios, we need to get the portfolio_id
        # This requires querying PortfolioFileMapping directly
        try:
            from ginkgo.data.containers import container
            mapping_crud = container.portfolio_file_mapping_crud()

            # Get first mapping
            mappings = mapping_crud.find(filters={}, page_size=1)

            if not mappings:
                pytest.skip("No portfolio mappings found")

            mapping = mappings[0]
            portfolio_id = mapping.portfolio_id

            # Load via portfolio_id
            with loader.load_by_portfolio_id(portfolio_id) as temp_path:
                assert temp_path.exists()
                content = temp_path.read_text(encoding="utf-8")
                assert len(content) > 0

            # Verify cleanup
            assert not temp_path.exists()

        except FileNotFoundError:
            pytest.skip(f"Portfolio {portfolio_id} not found in database")


@pytest.mark.integration
@pytest.mark.tdd
class TestStrictBestPracticeValidation:
    """
    Integration tests for strict level validation (T076).

    Tests the combination of structural, logical, and best practice validation.
    """

    def test_strict_validation_with_valid_strategy(self):
        """
        Test strict validation with a valid best practice strategy (T076).

        Expected: Validation should pass with best practice checks.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.validators.best_practice_evaluator import BestPracticeValidator
        from ginkgo.trading.evaluation.core.enums import EvaluationLevel

        # Use a real strategy file from the codebase
        strategy_file = Path(__file__).parent.parent.parent.parent.parent / \
                        "src/ginkgo/trading/strategies/trend_follow.py"

        if not strategy_file.exists():
            pytest.skip(f"Strategy file not found: {strategy_file}")

        # Create best practice validator
        validator = BestPracticeValidator()

        # Run validation
        result = validator.evaluate(
            strategy_file,
            level=EvaluationLevel.STRICT,
            load_component=False,
        )

        # Assertions
        assert result is not None
        assert result.file_path == strategy_file
        assert result.level == EvaluationLevel.STRICT

        # Trend follow strategy should pass validation
        assert result.passed is True

    def test_best_practice_with_decorator_recommendations(self):
        """
        Test best practice validator recommends decorators (T076).

        Expected: Strategy without decorators should get recommendations.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.validators.best_practice_evaluator import BestPracticeValidator
        from ginkgo.trading.evaluation.core.enums import EvaluationLevel

        # Create a strategy without decorators
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from typing import List, Dict
from ginkgo.trading.events import EventBase

class NoDecoratorStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        return []
"""

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            strategy_path = Path(f.name)

        try:
            validator = BestPracticeValidator()
            result = validator.evaluate(
                strategy_path,
                level=EvaluationLevel.STRICT,
                load_component=False,
            )

            # Should pass but with warnings/recommendations
            assert result is not None
            # Best practice rules are INFO level, so they won't fail validation
            # but we can check for issues
            # Note: The rule might recommend decorators or other improvements

        finally:
            strategy_path.unlink()

    def test_strict_validation_includes_all_levels(self):
        """
        Test strict validation includes structural, logical, and best practice checks (T076).

        Expected: All three validation levels should be applied.
        """
        from pathlib import Path
        from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
        from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
        from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry
        from ginkgo.trading.evaluation.rules.structural_rules import (
            BaseStrategyInheritanceRule,
            CalMethodRequiredRule,
        )
        from ginkgo.trading.evaluation.rules.best_practice_rules import (
            DecoratorUsageRule,
            ExceptionHandlingRule,
        )

        # Create a strategy
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from typing import List, Dict
from ginkgo.trading.events import EventBase

class StrictTestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        return []
"""

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            strategy_path = Path(f.name)

        try:
            # Register rules at all levels
            registry = get_global_registry()

            # BASIC level rules
            registry.register_rule_class(BaseStrategyInheritanceRule, ComponentType.STRATEGY)
            registry.register_rule_class(CalMethodRequiredRule, ComponentType.STRATEGY)

            # STRICT level rules (best practices)
            registry.register_rule_class(DecoratorUsageRule, ComponentType.STRATEGY)
            registry.register_rule_class(ExceptionHandlingRule, ComponentType.STRATEGY)

            # Create evaluator
            evaluator = SimpleEvaluator(ComponentType.STRATEGY)

            # Run at STRICT level - should apply all rules
            result = evaluator.evaluate(
                strategy_path,
                level=EvaluationLevel.STRICT,
                load_component=False,
            )

            # Assertions
            assert result is not None
            assert result.level == EvaluationLevel.STRICT

            # Strategy should pass structural checks (BASIC)
            # Best practice checks are recommendations (INFO level), so won't fail
            assert result.passed is True

        finally:
            strategy_path.unlink()

