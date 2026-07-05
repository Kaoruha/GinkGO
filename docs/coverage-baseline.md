# Coverage Baseline

Date: 2026-07-06

This baseline is intentionally generated from the startup smoke subset instead
of the full test suite. Full-suite pytest is known to be memory-heavy in this
repository, so this snapshot establishes a repeatable low-risk coverage floor
for future diff-coverage work.

## Command

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest \
  tests/unit/data/crud/test_user_crud_mock.py \
  tests/unit/features/test_containers.py \
  tests/unit/client/test_user_cli.py \
  --cov=src/ginkgo \
  --cov-report=json:/tmp/ginkgo-coverage-baseline.json \
  --cov-report=term-missing:skip-covered \
  -q -o "addopts=" --no-header --tb=short
```

Result: 36 passed.

## Overall

| Metric | Value |
|---|---:|
| Covered lines | 6,818 |
| Statements | 79,337 |
| Missing lines | 72,519 |
| Line coverage | 6.85% |
| Branches | 23,418 |
| Covered branches | 225 |
| Missing branches | 23,193 |

## Module Snapshot

| Module | Covered / Statements | Coverage |
|---|---:|---:|
| client | 136 / 8,951 | 1.5% |
| config | 0 / 32 | 0.0% |
| core | 0 / 1,740 | 0.0% |
| data | 3,650 / 23,963 | 15.2% |
| entities | 688 / 2,286 | 30.1% |
| enums.py | 472 / 570 | 82.8% |
| features | 422 / 2,244 | 18.8% |
| interfaces | 182 / 205 | 88.8% |
| libs | 1,153 / 5,107 | 22.6% |
| livecore | 0 / 3,023 | 0.0% |
| messages | 0 / 30 | 0.0% |
| notifier | 21 / 2,128 | 1.0% |
| quant_ml | 0 / 1,281 | 0.0% |
| research | 0 / 769 | 0.0% |
| service_hub.py | 25 / 74 | 33.8% |
| trading | 0 / 23,319 | 0.0% |
| user | 69 / 540 | 12.8% |
| validation | 0 / 354 | 0.0% |
| workers | 0 / 2,721 | 0.0% |

## Largest Missing Files

| Missing lines | Statements | Coverage | File |
|---:|---:|---:|---|
| 681 | 753 | 8% | `src/ginkgo/data/services/redis_service.py` |
| 652 | 652 | 0% | `src/ginkgo/trading/gateway/center.py` |
| 624 | 624 | 0% | `src/ginkgo/workers/execution_node/node.py` |
| 616 | 616 | 0% | `src/ginkgo/trading/engines/time_controlled_engine.py` |
| 614 | 660 | 5% | `src/ginkgo/data/services/bar_service.py` |
| 605 | 689 | 10% | `src/ginkgo/libs/core/threading.py` |
| 599 | 652 | 6% | `src/ginkgo/data/services/backtest_task_service.py` |
| 597 | 644 | 5% | `src/ginkgo/data/services/portfolio_service.py` |
| 595 | 595 | 0% | `src/ginkgo/workers/paper_trading_worker.py` |
| 573 | 573 | 0% | `src/ginkgo/client/data_cli.py` |
| 571 | 606 | 4% | `src/ginkgo/data/services/tick_service.py` |
| 545 | 545 | 0% | `src/ginkgo/client/engine_cli.py` |
| 526 | 526 | 0% | `src/ginkgo/trading/bases/portfolio_base.py` |
| 517 | 517 | 0% | `src/ginkgo/data/seeding.py` |
| 505 | 505 | 0% | `src/ginkgo/client/serve_cli.py` |

## Notes

- The root `.coveragerc` is the canonical coverage configuration.
- The former `pyproject.toml` coverage section was moved to `.coveragerc` to
  avoid maintaining two equivalent coverage configs.
- This baseline is not a quality target. It is a reproducible starting point for
  module-level trend tracking and later diff-coverage gates.
