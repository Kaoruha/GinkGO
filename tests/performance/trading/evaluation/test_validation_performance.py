"""
Performance benchmark tests for strategy validation.

Tests validation speed against the SC-003 requirement:
- Structural validation should complete in < 2 seconds per file
"""

import time
from pathlib import Path
from typing import List

import pytest

from ginkgo.trading.evaluation.core.enums import EvaluationLevel, ComponentType
from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
from ginkgo.trading.evaluation.rules.rule_registry import RuleRegistry, get_global_registry


@pytest.mark.performance
@pytest.mark.benchmark
class TestValidationPerformance:
    """
    Performance tests for strategy validation.

    Requirements (SC-003):
    - Basic structural validation: < 2 seconds
    - Standard validation: < 3 seconds
    """

    @pytest.fixture(autouse=True)
    def setup_evaluator(self):
        """Setup evaluator with rule registry."""
        # Get or create rule registry
        try:
            registry = get_global_registry()
        except Exception:
            from ginkgo.trading.evaluation.rules.rule_registry import RuleRegistry
            registry = RuleRegistry()
            # Register structural rules
            from ginkgo.trading.evaluation.rules.structural_rules import (
                BaseStrategyInheritanceRule,
                CalMethodRequiredRule,
                SuperInitCallRule,
                CalSignatureValidationRule,
                AbstractMarkerRule,
            )
            for rule_class in [
                BaseStrategyInheritanceRule,
                CalMethodRequiredRule,
                SuperInitCallRule,
                AbstractMarkerRule,
            ]:
                registry.register(
                    ComponentType.STRATEGY,
                    EvaluationLevel.BASIC,
                    rule_class(),
                )
            for rule_class in [
                CalSignatureValidationRule,
            ]:
                registry.register(
                    ComponentType.STRATEGY,
                    EvaluationLevel.STANDARD,
                    rule_class(),
                )

        self.evaluator = SimpleEvaluator(
            component_type=ComponentType.STRATEGY,
            registry=registry,
        )

    def test_basic_validation_performance_under_2s(self):
        """
        Test that basic structural validation completes in < 2 seconds.

        Requirement: SC-003
        Expected: Validation time < 2.0 seconds
        """
        # Use a real strategy file
        strategy_file = Path(__file__).parent.parent.parent.parent.parent / \
                        "src/ginkgo/trading/strategies/trend_follow.py"

        if not strategy_file.exists():
            pytest.skip(f"Strategy file not found: {strategy_file}")

        # Run validation and measure time
        start_time = time.time()
        result = self.evaluator.evaluate(
            file_path=strategy_file,
            level=EvaluationLevel.BASIC,
            load_component=False,  # Static analysis only
        )
        elapsed_time = time.time() - start_time

        # Assertions
        assert result is not None, "Evaluation result should not be None"
        assert elapsed_time < 2.0, \
            f"Basic validation took {elapsed_time:.2f}s, exceeding 2.0s requirement (SC-003)"

        print(f"\n✓ Basic validation completed in {elapsed_time:.3f}s (< 2.0s requirement)")

    def test_standard_validation_performance_under_3s(self):
        """
        Test that standard validation completes in < 3 seconds.

        Standard validation includes both structural and logical checks.
        """
        strategy_file = Path(__file__).parent.parent.parent.parent.parent / \
                        "src/ginkgo/trading/strategies/trend_follow.py"

        if not strategy_file.exists():
            pytest.skip(f"Strategy file not found: {strategy_file}")

        # Run validation and measure time
        start_time = time.time()
        result = self.evaluator.evaluate(
            file_path=strategy_file,
            level=EvaluationLevel.STANDARD,
            load_component=False,
        )
        elapsed_time = time.time() - start_time

        # Assertions
        assert result is not None, "Evaluation result should not be None"
        assert elapsed_time < 3.0, \
            f"Standard validation took {elapsed_time:.2f}s, exceeding 3.0s limit"

        print(f"\n✓ Standard validation completed in {elapsed_time:.3f}s (< 3.0s limit)")

    def test_multiple_validations_performance(self):
        """
        Test validation performance on multiple files.

        This tests the evaluator's ability to handle batch validation efficiently.
        """
        # Find multiple strategy files
        src_dir = Path(__file__).parent.parent.parent.parent.parent / "src/ginkgo/trading/strategies"
        strategy_files = list(src_dir.glob("*.py"))

        if len(strategy_files) < 2:
            pytest.skip("Need at least 2 strategy files for batch validation test")

        # Limit to 5 files for benchmark
        strategy_files = strategy_files[:5]

        start_time = time.time()
        results = []

        for strategy_file in strategy_files:
            result = self.evaluator.evaluate(
                strategy_file,
                level=EvaluationLevel.BASIC,
                load_component=False,
            )
            results.append(result)

        total_time = time.time() - start_time
        avg_time = total_time / len(strategy_files)

        # Each file should validate in < 2 seconds on average
        assert avg_time < 2.0, \
            f"Average validation time {avg_time:.2f}s exceeds 2.0s requirement"

        print(f"\n✓ Batch validation of {len(strategy_files)} files:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time: {avg_time:.2f}s per file")

    def test_validation_with_component_loading(self):
        """
        Test validation performance with component class loading.

        This includes runtime inspection, which is slower but should still
        complete in reasonable time.
        """
        strategy_file = Path(__file__).parent.parent.parent.parent.parent / \
                        "src/ginkgo/trading/strategies/trend_follow.py"

        if not strategy_file.exists():
            pytest.skip(f"Strategy file not found: {strategy_file}")

        # Run validation with component loading
        start_time = time.time()
        result = self.evaluator.evaluate(
            file_path=strategy_file,
            level=EvaluationLevel.STANDARD,
            load_component=True,  # Load the actual class
        )
        elapsed_time = time.time() - start_time

        # Component loading adds overhead, allow 5 seconds
        assert elapsed_time < 5.0, \
            f"Validation with loading took {elapsed_time:.2f}s, exceeding 5.0s limit"

        print(f"\n✓ Validation with component loading: {elapsed_time:.3f}s")

    def test_large_file_validation_performance(self):
        """
        Test validation performance on a larger file.

        Larger files (>500 lines) should still validate quickly.
        """
        # Find a larger strategy file
        src_dir = Path(__file__).parent.parent.parent.parent.parent / "src/ginkgo/trading/strategies"
        strategy_files = [f for f in src_dir.glob("*.py") if f.stat().st_size > 10000]  # >10KB

        if not strategy_files:
            pytest.skip("No large strategy files found for benchmark")

        strategy_file = strategy_files[0]
        file_size_kb = strategy_file.stat().st_size / 1024

        # Run validation
        start_time = time.time()
        result = self.evaluator.evaluate(
            file_path=strategy_file,
            level=EvaluationLevel.BASIC,
            load_component=False,
        )
        elapsed_time = time.time() - start_time

        # Scale allowed time based on file size (0.2s per KB)
        max_time = max(2.0, file_size_kb * 0.2)

        assert elapsed_time < max_time, \
            f"Large file validation took {elapsed_time:.2f}s, exceeding {max_time:.2f}s limit"

        print(f"\n✓ Large file ({file_size_kb:.1f}KB) validation: {elapsed_time:.3f}s")


def run_performance_benchmark():
    """
    Run performance benchmarks and generate report.

    This function can be run standalone to generate a performance report.
    """
    import sys

    print("=" * 60)
    print("Strategy Validation Performance Benchmark")
    print("=" * 60)
    print()

    # Setup
    registry = get_global_registry()
    evaluator = SimpleEvaluator(
        component_type=ComponentType.STRATEGY,
        registry=registry,
    )

    # Find test files
    src_dir = Path(__file__).parent.parent.parent.parent.parent / "src/ginkgo/trading/strategies"
    strategy_files = list(src_dir.glob("*.py"))

    if not strategy_files:
        print("❌ No strategy files found for benchmark")
        return 1

    print(f"Found {len(strategy_files)} strategy files")
    print()

    # Run benchmarks
    results = {
        "basic": [],
        "standard": [],
    }

    for strategy_file in strategy_files[:5]:  # Limit to 5 files
        print(f"Validating: {strategy_file.name}")

        # Basic level
        start = time.time()
        evaluator.evaluate(strategy_file, level=EvaluationLevel.BASIC, load_component=False)
        basic_time = time.time() - start
        results["basic"].append(basic_time)

        # Standard level
        start = time.time()
        evaluator.evaluate(strategy_file, level=EvaluationLevel.STANDARD, load_component=False)
        standard_time = time.time() - start
        results["standard"].append(standard_time)

        print(f"  Basic: {basic_time:.3f}s | Standard: {standard_time:.3f}s")

    # Summary
    print()
    print("=" * 60)
    print("Performance Summary")
    print("=" * 60)
    print(f"\nBasic Level (target: < 2.0s):")
    print(f"  Average: {sum(results['basic'])/len(results['basic']):.3f}s")
    print(f"  Min: {min(results['basic']):.3f}s")
    print(f"  Max: {max(results['basic']):.3f}s")

    print(f"\nStandard Level (target: < 3.0s):")
    print(f"  Average: {sum(results['standard'])/len(results['standard']):.3f}s")
    print(f"  Min: {min(results['standard']):.3f}s")
    print(f"  Max: {max(results['standard']):.3f}s")

    # Check requirements
    avg_basic = sum(results['basic'])/len(results['basic'])
    avg_standard = sum(results['standard'])/len(results['standard'])

    print()
    if avg_basic < 2.0:
        print("✅ Basic validation meets SC-003 requirement (< 2.0s)")
    else:
        print("❌ Basic validation EXCEEDS SC-003 requirement (>= 2.0s)")

    if avg_standard < 3.0:
        print("✅ Standard validation meets performance target (< 3.0s)")
    else:
        print("❌ Standard validation EXCEEDS performance target (>= 3.0s)")

    print()

    return 0 if avg_basic < 2.0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(run_performance_benchmark())
