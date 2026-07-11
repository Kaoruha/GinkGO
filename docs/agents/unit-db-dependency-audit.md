# Unit DB Dependency Audit

Issue: #6130
Date: 2026-07-06

Scope command:

```bash
rg -l "sqlite|ginkgo_init|set_debug|create_engine" tests/unit --glob '*.py' | sort
```

Current hit count: 30 files.

## Summary

- `leak`: 9 files. These are unit-classified business/container tests that depend on debug DB state, usually through `GCONF.set_debug(True)`, `container.*_service()`, direct `_crud_repo` calls, or `@pytest.mark.db_cleanup`.
- `legit`: 21 files. These are storage/driver/model adapter tests, integration-marked external storage tests, or false positives where `create_engine` / `set_debug` is a mocked/domain method name rather than a DB dependency.
- Typical leak patterns:
  - Service logic tests instantiate global container services instead of injecting in-memory or mock CRUD dependencies.
  - Tests verify business transformations but create fixtures through real `_crud_repo.create/remove/find/count`.
  - Some unit modules use `@pytest.mark.db_cleanup`, which is a strong signal they are really integration tests.
  - A shared conftest enables debug DB for broad backtest fixtures even when most fixtures are pure in-memory data.

## Classification

| File | Trigger(s) | Class | Reason | Suggested destination |
| --- | --- | --- | --- | --- |
| `tests/unit/backtest/conftest.py` | `set_debug` | leak | Shared backtest fixtures enable debug DB for a broad unit subtree even though most fixtures are pure entities/dataframes. | Split DB fixture out; keep pure fixtures in unit and move DB users to integration. |
| `tests/unit/client/test_config_cli.py` | `set_debug` | legit | CLI tests patch `GCONF` and assert command behavior; no real DB setup is required by the hit. | Keep in unit. |
| `tests/unit/client/test_core_cli.py` | `set_debug`, `ginkgo init` text | legit | `init` and debug commands mock table creation/config writes; the hit is command vocabulary plus mocks. | Keep in unit. |
| `tests/unit/client/test_engine_cli.py` | `create_engine` text | legit | `create_engine` is CLI/domain vocabulary and services are mocked via container patches. | Keep in unit. |
| `tests/unit/core/factories/test_component_factory.py` | `create_engine` | legit | `create_engine` is a component-factory convenience method, not SQLAlchemy engine creation. | Keep in unit. |
| `tests/unit/data/drivers/test_base_driver.py` | `_create_engine` | legit | Tests the database driver abstraction with fake driver implementations. | Keep in unit. |
| `tests/unit/data/drivers/test_base_driver_comprehensive.py` | `_create_engine` | legit | Driver contract coverage uses mock engines and abstract-method checks. | Keep in unit. |
| `tests/unit/data/drivers/test_clickhouse_driver_comprehensive.py` | `create_engine` | legit | ClickHouse driver adapter tests patch engine creation and cover driver behavior. | Keep as adapter coverage; mark/move integration only for any real connection cases. |
| `tests/unit/data/drivers/test_mysql_driver_comprehensive.py` | `create_engine` | legit | MySQL driver adapter tests patch SQLAlchemy engine creation and verify driver behavior. | Keep as adapter coverage; mark/move integration only for any real connection cases. |
| `tests/unit/data/drivers/test_streaming_connection_lifecycle.py` | `_create_engine` | legit | Streaming lifecycle is tested with a mock driver engine hook. | Keep in unit. |
| `tests/unit/data/models/conftest.py` | `set_debug` | legit | Model-test support fixture toggles debug config around ORM/model metadata helpers, not business logic. | Keep, but avoid requesting the fixture in pure metadata tests. |
| `tests/unit/data/services/test_adjustfactor_service.py` | `set_debug`, `db_cleanup`, `_crud_repo` | leak | Adjustfactor business/service tests create and remove real records through container-backed CRUD. | Extract in-memory CRUD/data-source tests; move DB lifecycle cases to integration. |
| `tests/unit/data/services/test_bar_service.py` | `set_debug`, `db_cleanup`, `_crud_repo` | leak | Bar service logic/count/sync tests repeatedly enable debug DB and inspect real CRUD counts. | Extract in-memory adapter tests; move DB-backed sync/count workflows to integration. |
| `tests/unit/data/services/test_engine_service.py` | `set_debug`, `db_cleanup` | leak | Engine service CRUD/status/mapping workflows run through real container service and DB cleanup. | Move lifecycle workflows to integration; keep validation with injected mock CRUD. |
| `tests/unit/data/services/test_file_service.py` | `set_debug`, `db_cleanup` | legit | FileService is a storage adapter by issue definition and validates file plus metadata persistence. | Keep as storage coverage or relocate under integration/storage for clearer selection. |
| `tests/unit/data/services/test_kafka_service.py` | `set_debug`, `integration` | legit | KafkaService is an external storage/queue adapter and connection tests are already integration-marked. | Keep adapter coverage; consider moving file under integration for marker consistency. |
| `tests/unit/data/services/test_mapping_service_mode_validation.py` | `create_engine` text | legit | Mapping service uses injected mock CRUDs; `create_engine_portfolio_mapping` is a domain method name. | Keep in unit. |
| `tests/unit/data/services/test_param_service.py` | `set_debug`, `db_cleanup` | leak | Param service CRUD/copy/validation tests use container-backed DB state. | Extract in-memory CRUD tests; move DB lifecycle/copy workflows to integration. |
| `tests/unit/data/services/test_redis_service.py` | `set_debug`, `integration` | legit | RedisService is an external storage adapter and the module is integration-marked with connection skip. | Keep adapter coverage; consider moving file under integration for path clarity. |
| `tests/unit/data/services/test_signal_tracking_service.py` | `set_debug`, `db_cleanup` | leak | Signal tracking service lifecycle tests persist business records through debug DB. | Move lifecycle workflows to integration; keep pure validation with injected mock CRUD. |
| `tests/unit/data/services/test_stockinfo_service.py` | `set_debug`, `db_cleanup`, `_crud_repo` | leak | Stockinfo service business/sync/validation tests create and remove real DB records. | Extract in-memory CRUD/data-source tests; move persistence workflows to integration. |
| `tests/unit/data/services/test_tick_service.py` | `set_debug`, `db_cleanup`, `_crud_repo` | leak | Tick service sync/query/count tests depend on stockinfo and tick records in debug DB. | Extract in-memory CRUD/data-source tests; move DB-backed sync/query workflows to integration. |
| `tests/unit/data/test_notification_recipient_container.py` | `set_debug`, `container` | leak | Unit container smoke instantiates a real service and calls `list_all()` against debug DB. | Move to integration/container smoke or inject fake recipient CRUD. |
| `tests/unit/database/conftest.py` | `set_debug` | legit | Database test fixtures intentionally configure database-driver tests and validate DB config. | Keep in database test support. |
| `tests/unit/database/drivers/test_base_driver.py` | `_create_engine` | legit | Database driver base behavior is the subject under test and uses fake engine hooks. | Keep in database/driver coverage. |
| `tests/unit/database/drivers/test_base_driver_comprehensive.py` | `_create_engine` | legit | Comprehensive database driver contract tests target adapter infrastructure. | Keep; integration marker/path can be clarified separately. |
| `tests/unit/database/drivers/test_clickhouse_driver_comprehensive.py` | `create_engine` | legit | ClickHouse adapter tests patch engine creation and are integration-marked. | Keep adapter coverage; consider integration path relocation. |
| `tests/unit/database/drivers/test_mysql_driver_comprehensive.py` | `create_engine` | legit | MySQL adapter tests patch engine creation and are integration-marked. | Keep adapter coverage; consider integration path relocation. |
| `tests/unit/services/smoke/test_mapping_service_smoke.py` | `create_engine` text | legit | Smoke test injects mock CRUDs; `create_engine_portfolio_mapping` is a domain method. | Keep in unit smoke. |
| `tests/unit/trading/services/test_engine_assembly_service.py` | `create_engine_from_*` | legit | `create_engine_from_yaml/config` is trading engine assembly terminology, with services mocked where needed. | Keep in unit. |

## Follow-up Targets

Highest-value leak cleanups are the seven DB-backed business service modules:

```text
tests/unit/data/services/test_adjustfactor_service.py
tests/unit/data/services/test_bar_service.py
tests/unit/data/services/test_engine_service.py
tests/unit/data/services/test_param_service.py
tests/unit/data/services/test_signal_tracking_service.py
tests/unit/data/services/test_stockinfo_service.py
tests/unit/data/services/test_tick_service.py
```

Treat `tests/unit/data/test_notification_recipient_container.py` as a small container-smoke relocation, and split `tests/unit/backtest/conftest.py` so pure backtest unit tests do not inherit debug DB setup.
