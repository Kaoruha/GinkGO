"""
Independent performance analysis for structlog configuration.

This script isolates the structlog JSON serialization performance
without I/O overhead from handlers.
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


def test_pure_structlog_serialization():
    """Test pure structlog serialization (no I/O handlers)."""
    import structlog

    # Configure structlog with minimal processors (just JSON rendering)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger("perf_test")

    # Warmup
    for _ in range(100):
        logger.info("warmup")

    # Test pure serialization
    iterations = 1000
    start = time.perf_counter_ns()

    for _ in range(iterations):
        logger.info("Performance test message")

    end = time.perf_counter_ns()
    avg_ns = (end - start) / iterations
    avg_ms = avg_ns / 1_000_000

    return avg_ms


def test_full_processor_chain():
    """Test with all custom processors."""
    import structlog
    from ginkgo.libs.core.logger import (
        ecs_processor,
        ginkgo_processor,
        container_metadata_processor,
        masking_processor
    )

    # Full processor chain
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            ecs_processor,
            ginkgo_processor,
            container_metadata_processor,
            masking_processor,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger("perf_test")

    # Warmup
    for _ in range(100):
        logger.info("warmup")

    # Test
    iterations = 1000
    start = time.perf_counter_ns()

    for _ in range(iterations):
        logger.info("Performance test message")

    end = time.perf_counter_ns()
    avg_ms = (end - start) / iterations / 1_000_000

    return avg_ms


def test_optimized_processor_order():
    """Test with optimized processor order (fastest first)."""
    import structlog
    from ginkgo.libs.core.logger import (
        ecs_processor,
        ginkgo_processor,
        container_metadata_processor,
        masking_processor
    )

    # Optimized order: fastest processors first
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Fast
            structlog.stdlib.add_log_level,            # Fast
            structlog.stdlib.add_logger_name,         # Fast
            structlog.processors.TimeStamper(fmt="iso"),  # Medium
            structlog.processors.UnicodeDecoder(),    # Fast
            # Custom processors (order by complexity)
            ginkgo_processor,         # Simple dict check
            masking_processor,        # Simple field iteration
            container_metadata_processor,  # Potentially slow (file reads)
            ecs_processor,            # Dict reorganization
            # Slowest last
            structlog.processors.JSONRenderer()       # Slowest - JSON serialization
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger("perf_test")

    # Warmup
    for _ in range(100):
        logger.info("warmup")

    # Test
    iterations = 1000
    start = time.perf_counter_ns()

    for _ in range(iterations):
        logger.info("Performance test message")

    end = time.perf_counter_ns()
    avg_ms = (end - start) / iterations / 1_000_000

    return avg_ms


def main():
    print("=" * 70)
    print("Structlog Performance Analysis")
    print("=" * 70)
    print()

    print("Testing JSON serialization performance (no I/O)...")
    print()

    # Test 1: Pure structlog
    print("1. Pure Structlog (minimal processors)")
    print("-" * 40)
    pure_ms = test_pure_structlog_serialization()
    print(f"Average: {pure_ms:.6f} ms")
    print(f"Requirement: < 0.1ms")
    if pure_ms < 0.1:
        print("✅ PASS")
    else:
        print(f"❌ FAIL ({pure_ms/0.1:.1f}x slower)")
    print()

    # Test 2: Full processor chain
    print("2. Full Processor Chain (current config)")
    print("-" * 40)
    full_ms = test_full_processor_chain()
    print(f"Average: {full_ms:.6f} ms")
    print(f"Requirement: < 0.1ms")
    if full_ms < 0.1:
        print("✅ PASS")
    else:
        print(f"❌ FAIL ({full_ms/0.1:.1f}x slower)")
    print()

    # Test 3: Optimized order
    print("3. Optimized Processor Order")
    print("-" * 40)
    opt_ms = test_optimized_processor_order()
    print(f"Average: {opt_ms:.6f} ms")
    print(f"Requirement: < 0.1ms")
    if opt_ms < 0.1:
        print("✅ PASS")
    else:
        print(f"❌ FAIL ({opt_ms/0.1:.1f}x slower)")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\nPure structlog:        {pure_ms:.6f} ms")
    print(f"Full chain:            {full_ms:.6f} ms (+{(full_ms-pure_ms)*1000:.3f} µs overhead)")
    print(f"Optimized order:       {opt_ms:.6f} ms (+{(opt_ms-pure_ms)*1000:.3f} µs overhead)")
    print()

    if opt_ms < full_ms:
        improvement = ((full_ms - opt_ms) / full_ms) * 100
        print(f"✅ Optimized order improves performance by {improvement:.1f}%")

    # Analysis
    print()
    print("=" * 70)
    print("Processor Complexity Analysis")
    print("=" * 70)
    print()
    print("Fast processors (should be first):")
    print("  - contextvars.merge_contextvars: Dict merge only")
    print("  - stdlib.add_log_level: Simple dict assignment")
    print("  - stdlib.add_logger_name: Simple dict assignment")
    print("  - UnicodeDecoder: String processing")
    print()
    print("Medium processors (middle):")
    print("  - TimeStamper: Datetime formatting")
    print("  - ginkgo_processor: Simple dict check")
    print("  - masking_processor: Field iteration")
    print()
    print("Slow processors (should be last):")
    print("  - container_metadata_processor: File I/O (container detection)")
    print("  - ecs_processor: Dict reorganization")
    print("  - JSONRenderer: JSON serialization")
    print()
    print("Recommendations:")
    if pure_ms >= 0.1:
        print("  ⚠️  Pure structlog is slower than 0.1ms target")
        print("     This may be due to structlog version or Python environment")
    if full_ms > pure_ms * 2:
        print("  ⚠️  Custom processors add significant overhead")
        overhead_ms = full_ms - pure_ms
        print(f"     {overhead_ms*1000:.3f} µs overhead from custom processors")
    if opt_ms < full_ms:
        print("  ✅ Optimized processor order improves performance")
    else:
        print("  ℹ️  Processor order has minimal impact")

    return 0 if opt_ms < 0.1 else 1


if __name__ == "__main__":
    sys.exit(main())
