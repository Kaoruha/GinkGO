# 测试报告

日期: 2026-04-09 01:41

| 目录 | 测试数 | 内存 | 耗时 | 状态 |
|------|--------|------|------|------|
| `tests/unit/backtest` | 566p/0f/0e/27s | 291MB | 0:04.58s | PASS |
| `tests/unit/client` | 411p/3f/0e/0s | 284MB | 0:04.20s | FAIL(1) |

### tests/unit/client 详情
```
tests/unit/client/test_notify_cli.py::TestSend::test_send_to_group_sync FAILED [ 70%]
tests/unit/client/test_notify_cli.py::TestNotifyCLIValidation::test_send_no_valid_users_found FAILED [ 72%]
tests/unit/client/test_notify_cli.py::TestNotifyCLIExceptions::test_send_service_exception FAILED [ 73%]
2026-04-09 01:42:01 [   ERROR] 🔥 [f202627f] [UNLOAD] Failed to send Kafka notification for portfolio_456
FAILED tests/unit/client/test_notify_cli.py::TestSend::test_send_to_group_sync
FAILED tests/unit/client/test_notify_cli.py::TestNotifyCLIValidation::test_send_no_valid_users_found
FAILED tests/unit/client/test_notify_cli.py::TestNotifyCLIExceptions::test_send_service_exception
tests/unit/client/test_notify_cli.py::TestSend::test_send_to_group_sync FAILED [ 70%]
tests/unit/client/test_notify_cli.py::TestNotifyCLIValidation::test_send_no_valid_users_found FAILED [ 72%]
tests/unit/client/test_notify_cli.py::TestNotifyCLIExceptions::test_send_service_exception FAILED [ 73%]
=========================== short test summary info ============================
FAILED tests/unit/client/test_notify_cli.py::TestSend::test_send_to_group_sync
FAILED tests/unit/client/test_notify_cli.py::TestNotifyCLIValidation::test_send_no_valid_users_found
FAILED tests/unit/client/test_notify_cli.py::TestNotifyCLIExceptions::test_send_service_exception
```
| `tests/unit/core` | 265p/0f/0e/0s | 277MB | 0:02.77s | PASS |
| `tests/unit/data` | 1769p/0f/0e/54s | 286MB | 0:57.00s | PASS |
| `tests/unit/database` | 43p/0f/0e/80s | 220MB | 0:02.24s | PASS |
| `tests/unit/enums` | 3p/0f/0e/0s | 155MB | 0:00.84s | PASS |
| `tests/unit/interfaces` | 36p/0f/0e/0s | 221MB | 0:01.94s | PASS |
| `tests/unit/lab` | 46p/0f/0e/28s | 222MB | 0:02.00s | PASS |
| `tests/unit/libs` | 205p/0f/0e/3s | 214MB | 0:08.59s | PASS |
| `tests/unit/notifier` | 136p/0f/0e/0s | 224MB | 0:08.08s | PASS |
| `tests/unit/notifiers` | 0p/0f/0e/0s | 160MB | 0:00.91s | PASS |
| `tests/unit/research` | 56p/0f/0e/0s | 229MB | 0:09.14s | PASS |
| `tests/unit/trading` | 2284p/0f/0e/53s | 341MB | 0:29.69s | PASS |
| `tests/unit/validation` | 34p/0f/0e/0s | 161MB | 0:00.99s | PASS |
| `tests/unit/workers` | 39p/4f/0e/0s | 319MB | 0:03.08s | FAIL(1) |

### tests/unit/workers 详情
```
2026-04-09 01:44:09 [   ERROR] 🔥 [19077f1c] [PAPER-WORKER] Engine not initialized, cannot deploy
2026-04-09 01:44:09 [   ERROR] 🔥 [e2004cb0] [PAPER-WORKER] Engine not initialized, cannot unload
FAILED                                                                   [ 62%]
tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_accumulates_data_and_checks_on_slice_complete FAILED [ 76%]
tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_continues_on_portfolio_error FAILED [ 81%]
tests/unit/workers/test_paper_trading_worker.py::TestLoadTodayRecords::test_filters_records_by_today FAILED [ 83%]
2026-04-09 01:44:09 [   ERROR] 🔥 [5da7162c] [PAPER-WORKER] test-strategy: SEVERE deviation - max_drawdown (z=2.5)
2026-04-09 01:44:09 [   ERROR] ⚠️ [5da7162c] [PAPER-WORKER] test-strategy: SEVERE deviation - max_drawdown (z=2.5) (2th occurrence)
2026-04-09 01:44:09 [   ERROR] 🔥 [cd218f77] [PAPER-WORKER] Auto-takedown triggered for p-001
FAILED tests/unit/workers/test_paper_trading_worker.py::TestGetBaseline::test_computes_baseline_on_redis_miss
FAILED tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_accumulates_data_and_checks_on_slice_complete
FAILED tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_continues_on_portfolio_error
FAILED tests/unit/workers/test_paper_trading_worker.py::TestLoadTodayRecords::test_filters_records_by_today
FAILED                                                                   [ 62%]
tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_accumulates_data_and_checks_on_slice_complete FAILED [ 76%]
tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_continues_on_portfolio_error FAILED [ 81%]
tests/unit/workers/test_paper_trading_worker.py::TestLoadTodayRecords::test_filters_records_by_today FAILED [ 83%]
=========================== short test summary info ============================
FAILED tests/unit/workers/test_paper_trading_worker.py::TestGetBaseline::test_computes_baseline_on_redis_miss
FAILED tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_accumulates_data_and_checks_on_slice_complete
FAILED tests/unit/workers/test_paper_trading_worker.py::TestDeviationCheck::test_continues_on_portfolio_error
FAILED tests/unit/workers/test_paper_trading_worker.py::TestLoadTodayRecords::test_filters_records_by_today
```
| `tests/integration/data` | 0p/0f/0e/0s | 405MB | 5:00.03s | TIMEOUT |

### tests/integration/data 详情
```
2026-04-09 01:44:13 [   ERROR] 🔥 [a9e3b184] Failed to update API Key: type object 'datetime.datetime' has no attribute 'datetime'
FAILED                                                                   [  2%]
2026-04-09 01:44:13 [   ERROR] 🔥 [55b55cdd] MySQL session error: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:13 [   ERROR] 🔥 [cbde76cf] Failed to add data to database: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:15 [   ERROR] ⚠️ [55b55cdd] MySQL session error: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:15 [   ERROR] ⚠️ [cbde76cf] Failed to add data to database: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:16 [   ERROR] ⚠️ [55b55cdd] MySQL session error: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:16 [   ERROR] ⚠️ [cbde76cf] Failed to add data to database: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:18 [   ERROR] ⚠️ [55b55cdd] MySQL session error: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:18 [   ERROR] ⚠️ [cbde76cf] Failed to add data to database: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:19 [   ERROR] ⚠️ [55b55cdd] MySQL session error: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:19 [   ERROR] ⚠️ [cbde76cf] Failed to add data to database: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:22 [   ERROR] 🔥 [3dcec38c] Failed to add MApiKey item: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:26 [   ERROR] 🚨 [55b55cdd] Error pattern occurred 10 times, consider investigation: MySQL session error: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:28 [   ERROR] 🚨 [cbde76cf] Error pattern occurred 10 times, consider investigation: Failed to add data to database: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:30 [   ERROR] ⚠️ [3dcec38c] Failed to add MApiKey item: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:39 [   ERROR] ⚠️ [3dcec38c] Failed to add MApiKey item: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
2026-04-09 01:44:42 [   ERROR] 🔥 [636f1fe9] Failed to create API Key: (pymysql.err.IntegrityError) (1062, "Duplicate entry 'b0a7cd9249c460cfabffbb7735f8ccd8f890ba7754423b910aa1e5a444d326d1' for key 'api_keys.ix_api_keys_key_hash'")
FAILED                                                                   [  2%]
2026-04-09 01:44:42 [   ERROR] 🔥 [ddf84e1c] API Key not found: nonexistent_uuid_12345678
2026-04-09 01:44:43 [   ERROR] 🔥 [fd28d848] ClickHouse doesn't support UPDATE operations
2026-04-09 01:44:43 [   ERROR] 🔥 [ea1f06a4] Failed to get stock codes: BaseCRUD.find() got an unexpected keyword argument 'output_type'
FAILED                                                                   [  5%]
2026-04-09 01:44:43 [   ERROR] 🔥 [c5ae5b82] Data validation failed for MBar: Missing required field: timestamp
2026-04-09 01:44:43 [   ERROR] 🔥 [80cd5516] Failed to create MBar from params: Missing required field: timestamp
2026-04-09 01:44:43 [   ERROR] ⚠️ [c5ae5b82] Data validation failed for MBar: Missing required field: timestamp (2th occurrence)
2026-04-09 01:44:43 [   ERROR] ⚠️ [80cd5516] Failed to create MBar from params: Missing required field: timestamp (2th occurrence)
2026-04-09 01:44:43 [   ERROR] ⚠️ [c5ae5b82] Data validation failed for MBar: Missing required field: timestamp (3th occurrence)
2026-04-09 01:44:43 [   ERROR] ⚠️ [80cd5516] Failed to create MBar from params: Missing required field: timestamp (3th occurrence)
2026-04-09 01:44:43 [   ERROR] 🔥 [c91df6b3] MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:43 [   ERROR] 🔥 [c9cc425b] Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:45 [   ERROR] ⚠️ [c91df6b3] MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:45 [   ERROR] ⚠️ [c9cc425b] Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:46 [   ERROR] ⚠️ [c91df6b3] MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:46 [   ERROR] ⚠️ [c9cc425b] Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:47 [   ERROR] ⚠️ [c91df6b3] MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:47 [   ERROR] ⚠️ [c9cc425b] Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:49 [   ERROR] ⚠️ [c91df6b3] MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:49 [   ERROR] ⚠️ [c9cc425b] Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:52 [   ERROR] 🔥 [3c99c106] Failed to add MBrokerInstance item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:56 [   ERROR] 🚨 [c91df6b3] Error pattern occurred 10 times, consider investigation: MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:44:57 [   ERROR] 🚨 [c9cc425b] Error pattern occurred 10 times, consider investigation: Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:45:00 [   ERROR] ⚠️ [3c99c106] Failed to add MBrokerInstance item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:45:09 [   ERROR] ⚠️ [3c99c106] Failed to add MBrokerInstance item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
FAILED                                                                   [  5%]
2026-04-09 01:45:12 [   ERROR] 🔥 [3c7fc614] MySQL batch operation failed: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:45:20 [   ERROR] ⚠️ [3c99c106] Failed to add MBrokerInstance item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
2026-04-09 01:45:29 [   ERROR] ⚠️ [3c99c106] Failed to add MBrokerInstance item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
FAILED                                                                   [  5%]
2026-04-09 01:45:41 [   ERROR] ⚠️ [3c7fc614] MySQL batch operation failed: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
FAILED                                                                   [  5%]
tests/integration/data/crud/test_broker_instance_crud_integration.py::TestBrokerInstanceCRUDFind::test_find_empty FAILED [  5%]
2026-04-09 01:45:41 [   ERROR] ⚠️ [3c7fc614] MySQL batch operation failed: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
FAILED                                                                   [  5%]
2026-04-09 01:45:41 [   ERROR] ⚠️ [3c7fc614] MySQL batch operation failed: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`broker_instances`, CONSTRAINT `fk_broker_live_account` FOREIGN KEY (`live_account_id`) REFERENCES `live_accounts` (`uuid`))')
FAILED                                                                   [  5%]
tests/integration/data/crud/test_engine_handler_mapping_crud.py::TestEngineHandlerMappingCRUDConversion::test_data_count_changes_with_conversion FAILED [ 10%]
2026-04-09 01:45:46 [   ERROR] 🔥 [52260947] Data validation failed for MMarketSubscription: Missing required field: data_types
2026-04-09 01:45:46 [   ERROR] 🔥 [36819224] Failed to create MMarketSubscription from params: Missing required field: data_types
2026-04-09 01:45:46 [   ERROR] ⚠️ [52260947] Data validation failed for MMarketSubscription: Missing required field: data_types (2th occurrence)
2026-04-09 01:45:46 [   ERROR] ⚠️ [36819224] Failed to create MMarketSubscription from params: Missing required field: data_types (2th occurrence)
2026-04-09 01:45:46 [   ERROR] ⚠️ [52260947] Data validation failed for MMarketSubscription: Missing required field: data_types (3th occurrence)
2026-04-09 01:45:46 [   ERROR] ⚠️ [36819224] Failed to create MMarketSubscription from params: Missing required field: data_types (3th occurrence)
FAILED                                                                   [ 15%]
2026-04-09 01:45:55 [   ERROR] 🔥 [b465fb9e] Failed to add MNotificationRecipient item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
2026-04-09 01:45:59 [   ERROR] 📊 [c91df6b3] Error pattern count: 50 - MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
2026-04-09 01:46:03 [   ERROR] ⚠️ [b465fb9e] Failed to add MNotificationRecipient item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
2026-04-09 01:46:12 [   ERROR] ⚠️ [b465fb9e] Failed to add MNotificationRecipient item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
FAILED                                                                   [ 16%]
2026-04-09 01:46:20 [   ERROR] 📊 [c9cc425b] Error pattern count: 50 - Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_2` FOREIGN KEY (`user_group_id`) REFERENCES `user_groups` (`uuid`) ON DELETE CASCADE)')
2026-04-09 01:46:23 [   ERROR] ⚠️ [b465fb9e] Failed to add MNotificationRecipient item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_2` FOREIGN KEY (`user_group_id`) REFERENCES `user_groups` (`uuid`) ON DELETE CASCADE)')
2026-04-09 01:46:32 [   ERROR] ⚠️ [b465fb9e] Failed to add MNotificationRecipient item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_2` FOREIGN KEY (`user_group_id`) REFERENCES `user_groups` (`uuid`) ON DELETE CASCADE)')
FAILED                                                                   [ 16%]
tests/integration/data/crud/test_notification_recipient_crud_integration.py::TestNotificationRecipientCRUDQuery::test_get_by_name FAILED [ 16%]
2026-04-09 01:47:21 [   ERROR] 📊 [c91df6b3] Error pattern count: 100 - MySQL session error: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
2026-04-09 01:47:21 [   ERROR] 🚨 [b465fb9e] Error pattern occurred 10 times, consider investigation: Failed to add MNotificationRecipient item: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
FAILED                                                                   [ 16%]
2026-04-09 01:47:56 [   ERROR] 📊 [c9cc425b] Error pattern count: 100 - Failed to add data to database: (pymysql.err.IntegrityError) (1452, 'Cannot add or update a child row: a foreign key constraint fails (`ginkgo`.`notification_recipients`, CONSTRAINT `notification_recipients_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`uuid`) ON DELETE CASCADE)')
FAILED                                                                   [ 16%]
tests/integration/data/crud/test_notification_recipient_crud_integration.py::TestNotificationRecipientCRUDDelete::test_remove_recipient FAILED [ 16%]
2026-04-09 01:48:40 [   ERROR] 🔥 [7fc8743c] Data validation failed for MOrder: Missing required field: business_timestamp
2026-04-09 01:48:40 [   ERROR] 🔥 [31630536] Failed to create MOrder from params: Missing required field: business_timestamp
2026-04-09 01:48:40 [   ERROR] ⚠️ [7fc8743c] Data validation failed for MOrder: Missing required field: business_timestamp (2th occurrence)
2026-04-09 01:48:40 [   ERROR] ⚠️ [31630536] Failed to create MOrder from params: Missing required field: business_timestamp (2th occurrence)
2026-04-09 01:48:40 [   ERROR] ⚠️ [7fc8743c] Data validation failed for MOrder: Missing required field: business_timestamp (3th occurrence)
2026-04-09 01:48:40 [   ERROR] ⚠️ [31630536] Failed to create MOrder from params: Missing required field: business_timestamp (3th occurrence)
FAILED                                                                   [ 18%]
2026-04-09 01:48:40 [   ERROR] ⚠️ [7fc8743c] Data validation failed for MOrder: Missing required field: business_timestamp (4th occurrence)
2026-04-09 01:48:40 [   ERROR] ⚠️ [31630536] Failed to create MOrder from params: Missing required field: business_timestamp (4th occurrence)
2026-04-09 01:48:40 [   ERROR] ⚠️ [7fc8743c] Data validation failed for MOrder: Missing required field: business_timestamp (5th occurrence)
2026-04-09 01:48:40 [   ERROR] ⚠️ [31630536] Failed to create MOrder from params: Missing required field: business_timestamp (5th occurrence)
FAILED                                                                   [ 19%]
tests/integration/data/crud/test_order_crud_integration.py::TestOrderCRUDBusinessHelpers::test_find_by_portfolio_helper FAILED [ 19%]
tests/integration/data/crud/test_order_crud_integration.py::TestOrderCRUDBusinessHelpers::test_find_by_code_helper FAILED [ 19%]
tests/integration/data/crud/test_order_crud_integration.py::TestOrderCRUDBusinessHelpers::test_find_pending_orders_helper FAILED [ 19%]
FAILED                                                                   [ 19%]
tests/integration/data/crud/test_signal_crud.py::TestSignalCRUDQuery::test_model_list_conversions FAILED [ 29%]
2026-04-09 01:49:00 [   ERROR] 🔥 [61e0e665] MySQL session error: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:00 [   ERROR] 🔥 [4ea27c07] Failed to add data to database: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:02 [   ERROR] ⚠️ [61e0e665] MySQL session error: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:02 [   ERROR] ⚠️ [4ea27c07] Failed to add data to database: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:03 [   ERROR] ⚠️ [61e0e665] MySQL session error: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:03 [   ERROR] ⚠️ [4ea27c07] Failed to add data to database: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:05 [   ERROR] ⚠️ [61e0e665] MySQL session error: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:05 [   ERROR] ⚠️ [4ea27c07] Failed to add data to database: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:06 [   ERROR] ⚠️ [61e0e665] MySQL session error: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:06 [   ERROR] ⚠️ [4ea27c07] Failed to add data to database: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
2026-04-09 01:49:09 [   ERROR] 🔥 [59e1a8b0] Failed to add MTradeRecord item: (pymysql.err.OperationalError) (1054, "Unknown column 'meta' in 'field list'")
FAILED                                                                   [  2%]
FAILED                                                                   [  2%]
FAILED                                                                   [  5%]
FAILED                                                                   [  5%]
FAILED                                                                   [  5%]
FAILED                                                                   [  5%]
tests/integration/data/crud/test_broker_instance_crud_integration.py::TestBrokerInstanceCRUDFind::test_find_empty FAILED [  5%]
FAILED                                                                   [  5%]
FAILED                                                                   [  5%]
tests/integration/data/crud/test_engine_handler_mapping_crud.py::TestEngineHandlerMappingCRUDConversion::test_data_count_changes_with_conversion FAILED [ 10%]
FAILED                                                                   [ 15%]
FAILED                                                                   [ 16%]
FAILED                                                                   [ 16%]
tests/integration/data/crud/test_notification_recipient_crud_integration.py::TestNotificationRecipientCRUDQuery::test_get_by_name FAILED [ 16%]
FAILED                                                                   [ 16%]
FAILED                                                                   [ 16%]
tests/integration/data/crud/test_notification_recipient_crud_integration.py::TestNotificationRecipientCRUDDelete::test_remove_recipient FAILED [ 16%]
FAILED                                                                   [ 18%]
FAILED                                                                   [ 19%]
tests/integration/data/crud/test_order_crud_integration.py::TestOrderCRUDBusinessHelpers::test_find_by_portfolio_helper FAILED [ 19%]
tests/integration/data/crud/test_order_crud_integration.py::TestOrderCRUDBusinessHelpers::test_find_by_code_helper FAILED [ 19%]
tests/integration/data/crud/test_order_crud_integration.py::TestOrderCRUDBusinessHelpers::test_find_pending_orders_helper FAILED [ 19%]
FAILED                                                                   [ 19%]
tests/integration/data/crud/test_signal_crud.py::TestSignalCRUDQuery::test_model_list_conversions FAILED [ 29%]
```
| `tests/integration/database` | 244p/0f/0e/91s | 227MB | 0:03.95s | PASS |
| `tests/integration/backtest` | 88p/1f/0e/2s | 285MB | 0:07.63s | FAIL(1) |

### tests/integration/backtest 详情
```
tests/integration/backtest/test_analyzer_binding_simple.py::test_analyzer_binding FAILED [  1%]
2026-04-09 01:49:16 [   ERROR] 🔥 [ddd3d4a6] No component class found in file. Available classes: []
2026-04-09 01:49:16 [   ERROR] 🔥 [c363babe] Failed to instantiate strategy: No component class found in file. Available classes: []
2026-04-09 01:49:16 [   ERROR] 🔥 [6f9ea37c] [BIND PORTFOLIO] Failed to bind components for portfolio 3a61561dc1944c00ba248c8d678bfa30
2026-04-09 01:49:16 [   ERROR] 🔥 [d02f54e4] Failed to bind portfolio 3a61561dc1944c00ba248c8d678bfa30 to engine
2026-04-09 01:49:16 [   ERROR] 🔥 [c792a064] No portfolios were successfully bound to engine a150266f479246c9b67ae7b1814d85a6
2026-04-09 01:49:16 [   ERROR] 🔥 [b0682887] Cannot pause from idle state
2026-04-09 01:49:16 [   ERROR] 🔥 [b81933b5] Cannot stop from idle state
2026-04-09 01:49:16 [   ERROR] 🔥 [cdf4537a] Cannot pause from paused state
2026-04-09 01:49:16 [   ERROR] 🔥 [55d589d0] Cannot start from running state
2026-04-09 01:49:16 [   ERROR] ⚠️ [b0682887] Cannot pause from idle state (2th occurrence)
2026-04-09 01:49:16 [   ERROR] 🔥 [e6fece2e] Cannot pause from stopped state
2026-04-09 01:49:17 [   ERROR] ⚠️ [55d589d0] Cannot start from running state (2th occurrence)
2026-04-09 01:49:17 [   ERROR] ⚠️ [b81933b5] Cannot stop from idle state (2th occurrence)
2026-04-09 01:49:17 [   ERROR] 🔥 [bc18dc79] Cannot stop from stopped state
2026-04-09 01:49:18 [   ERROR] ⚠️ [bc18dc79] Cannot stop from stopped state (2th occurrence)
2026-04-09 01:49:19 [   ERROR] ⚠️ [bc18dc79] Cannot stop from stopped state (3th occurrence)
2026-04-09 01:49:19 [   ERROR] ⚠️ [b81933b5] Cannot stop from idle state (3th occurrence)
2026-04-09 01:49:19 [   ERROR] ⚠️ [b81933b5] Cannot stop from idle state (4th occurrence)
2026-04-09 01:49:19 [   ERROR] ⚠️ [b81933b5] Cannot stop from idle state (5th occurrence)
2026-04-09 01:49:19 [   ERROR] 🚨 [b81933b5] Error pattern occurred 10 times, consider investigation: Cannot stop from idle state
2026-04-09 01:49:21 [   ERROR] ⚠️ [bc18dc79] Cannot stop from stopped state (4th occurrence)
2026-04-09 01:49:21 [   ERROR] 🔥 [02ffeb79] Event processing failed: Test error
FAILED tests/integration/backtest/test_analyzer_binding_simple.py::test_analyzer_binding
tests/integration/backtest/test_analyzer_binding_simple.py::test_analyzer_binding FAILED [  1%]
=========================== short test summary info ============================
FAILED tests/integration/backtest/test_analyzer_binding_simple.py::test_analyzer_binding
```
| `tests/integration/trading` | 0p/0f/0e/0s | 283MB | 0:02.78s | FAIL(2) |

### tests/integration/trading 详情
```
==================================== ERRORS ====================================
_ ERROR collecting tests/integration/trading/engines/test_time_controlled_engine.py _
ERROR tests/integration/trading/engines/test_time_controlled_engine.py - Fail...
=========================== short test summary info ============================
```
| `tests/integration/network` | 14p/3f/0e/8s | 221MB | 0:29.84s | FAIL(1) |

### tests/integration/network 详情
```
tests/integration/network/test_database_connection.py::TestAllDriversConnection::test_all_drivers_available FAILED [ 32%]
FAILED                                                                   [ 52%]
FAILED                                                                   [ 56%]
FAILED tests/integration/network/test_database_connection.py::TestAllDriversConnection::test_all_drivers_available
FAILED tests/integration/network/test_kafka_connection.py::TestKafkaTopics::test_live_trading_topics_exist
FAILED tests/integration/network/test_kafka_connection.py::TestKafkaTopics::test_global_topics_exist
tests/integration/network/test_database_connection.py::TestAllDriversConnection::test_all_drivers_available FAILED [ 32%]
FAILED                                                                   [ 52%]
FAILED                                                                   [ 56%]
=========================== short test summary info ============================
FAILED tests/integration/network/test_database_connection.py::TestAllDriversConnection::test_all_drivers_available
FAILED tests/integration/network/test_kafka_connection.py::TestKafkaTopics::test_live_trading_topics_exist
FAILED tests/integration/network/test_kafka_connection.py::TestKafkaTopics::test_global_topics_exist
```

---
## 汇总

- 总测试: **6239 passed**, 11 failed, 0 errors, 346 skipped
- 总耗时: 481s
- 最大单批内存: 405MB
- 完成时间: 2026-04-09 01:49
