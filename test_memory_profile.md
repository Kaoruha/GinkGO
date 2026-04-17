# 单元测试内存分析

日期: 2026-04-09
测试文件总数: 284

## 结论

**找到 OOM 根因**：`tests/unit/client/test_kafka_cli.py::TestPurge::test_purge_with_confirm`

### 根因
`_purge_queue_messages` 的 while 循环依赖 `consume_messages()` 返回空列表来 break，但 mock 默认返回 MagicMock（truthy），导致循环跑满 30 秒 timeout，MagicMock 调用记录无限增长 → 3GB 内存。

### 修复
在测试中加一行：`mock_crud.consume_messages.return_value = []`

### 修复效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| test_kafka_cli.py 内存 | 3.1 GB | 222 MB |
| test_kafka_cli.py 耗时 | 30.6 s | 0.61 s |
| tests/unit/client 目录内存 | 3.0 GB | 292 MB |

## 逐文件内存数据

| # | 文件 | Max RSS (MB) | 状态 |
|---|------|-------------|------|
| 1 | tests/unit/backtest/analyzers/ (9 files) | 157-274 | PASS |
| 2 | tests/unit/backtest/indicators/ (6 files) | 158-160 | PASS |
| 3 | tests/unit/backtest/risk_managements/ (2 files) | 157-158 | PASS |
| 4 | tests/unit/backtest/test_*.py (7 files) | 157-274 | PASS |
| 5 | tests/unit/client/test_kafka_cli.py | **3063** | **PASS (30s)** |
| 6 | tests/unit/client/ (其余 19 files) | 155-272 | PASS |
| 7 | tests/unit/core/ (8 files) | 271-274 | PASS |
| 8 | tests/unit/database/ (9 files) | 157-221 | PASS |
| 9 | tests/unit/data/crud/ (45 files) | 218-222 | PASS |
| 10 | tests/unit/data/drivers/ (1 file) | 221 | PASS |
| 11 | tests/unit/data/models/ (13 files) | 218-222 | PASS |
| 12 | tests/unit/data/services/ (17 files) | 218-266 | PASS |
| 13 | tests/unit/data/sources/ (3 files) | 219-222 | PASS |
| 14 | tests/unit/data/ (其余 9 files) | 156-229 | PASS/NO_TESTS |
| 15 | tests/unit/enums/ (1 file) | 156 | PASS |
| 16 | tests/unit/features/ (1 file) | 156 | PASS |
| 17 | tests/unit/interfaces/ (2 files) | 157-219 | PASS |
| 18 | tests/unit/lab/ (8 files) | 156-220 | PASS/NO_TESTS |
| 19 | tests/unit/libs/ (10 files) | 155-209 | PASS |
| 20 | tests/unit/notifier/ (6 files) | 157-221 | PASS |
| 21 | tests/unit/notifiers/ (3 files) | 156-160 | PASS |
| 22 | tests/unit/research/ (5 files) | 212-226 | PASS |
| 23 | tests/unit/test_quant_ml.py | 293 | PASS |
| 24 | tests/unit/trading/ (80+ files) | 155-278 | PASS/FAIL |
| 25 | tests/unit/validation/ (3 files) | 157-160 | PASS |
