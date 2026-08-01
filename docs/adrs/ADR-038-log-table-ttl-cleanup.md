# ADR-038: 日志表 TTL 自动清理（ginkgo_logs_* 三表 TTL 接线 + 存量 drop/reseed）

**Status:** Accepted
**Date:** 2026-07-29
**Related:** ADR-007（model 驱动禁 ALTER / create_all 不补已有表）、ADR-023（时间 seam：Infra Time 墙钟 vs Business Time）、ADR-032（CH 时序审计层）、spec 015（分布式日志）

## Context

Vector 采集链路（`.conf/vector.toml`）把应用 JSON 日志路由写入 ClickHouse 三表 `ginkgo_logs_backtest` / `ginkgo_logs_component` / `ginkgo_logs_performance`（`docker-compose.yml:428` vector 服务 → 三 sink）。**落库后无任何清理策略,三表只增不减,磁盘无限增长。**

spec 015（`specs/015-distributed-logging-vector/data-model.md`）设计了 TTL（backtest 180 天 / component 90 天 / performance 30 天）,但实现层全漏,经 spike 核实（锚点如下）:

### 双层断裂（非 #4652 式误判,均有实测锚点）

- **model 建表无 TTL**:`src/ginkgo/data/models/model_logs.py:34/185/235` 三表 `engines.ReplacingMergeTree / MergeTree(order_by=...)` 均**无 `ttl=`** 子句。
- **GCONF 配置是死参数**:`src/ginkgo/libs/core/config.py:1320/1339/1357` 的 `LOGGING_TTL_BACKTEST/COMPONENT/PERFORMANCE`（默认 180/90/30）全仓**零消费方**（grep 仅定义点,无任何读取）——与 ADR-037 `--slippage` 死参数同型。

### 源头已有兜底,问题集中在库侧

- 文件侧:`logger.py:422` `max_file_bytes=2GB / backup_count=3`,RotatingFileHandler 已轮转（3 处 handler）。文件源头不无限增长。
- 库侧:三表零 TTL、零清理 CLI、零 `MODIFY TTL`/`OPTIMIZE` 定时任务（grep 全仓无）。

### 叠加 create_all 铁律

ADR-007 / `arch_ch_create_all_no_alter_drift`:`create_all` 只建表,不给**已有表**补列/补 TTL。即使改 model 让新建表带 TTL,master/test **存量已建表**仍无 TTL,需独立迁移。

判定三条全中（drop 存量日志难逆转 / `timestamp` 做 TTL 反直觉易踩坑 / drop vs ALTER 真实权衡）,立本 ADR。

## Decision

### D1 起算字段:`timestamp`（非 `business_timestamp`）

三表统一 `TTL timestamp + INTERVAL N DAY`。

- `timestamp` = **Infra Time 墙钟写入时间**,`logger.py:134` `event_dict["@timestamp"] = ... datetime.utcnow().isoformat()`,经 `vector.toml:46` 映射入 CH `timestamp` 列。
- `business_timestamp` = **Business Time 回测业务历史时间**,`logger.py:193` 取自 `engine_ctx.business_timestamp`（TimeProvider,ADR-023）,回测 2024 年数据时即 2024-xx。

**反直觉点**（立 ADR 主因）:`timestamp` 名字像"事件时间",极易误选 `business_timestamp` 做 TTL——后者会让回测历史日志**一写入即过期**。本决策是 ADR-023 时间 seam（Infra Time vs Business Time）在日志 TTL 场景的直接应用。

### D2 三表 model 注入 TTL + 统一单一保留期（默认 6 个月）

`model_logs.py` 三表 `engines.*MergeTree(order_by=..., ttl=<读 GCONF 的表达式>)`,TTL 天数**统一读单一配置** `GCONF.LOGGING_TTL_DAYS`（默认 **180 天 ≈ 6 个月**）,三表同值。废弃 spec 015 原设计的 backtest/component/performance 分级（180/90/30）——三个分级 `@property`（`config.py:1320/1339/1357`）当前均为零消费死参数,直接以单一 `LOGGING_TTL_DAYS` 替换,无运行时兼容负担。值经 `config.yaml` 的 `logging.ttl.days` 或 `GINKGO_LOGGING_TTL_DAYS` 环境变量覆盖。

**生效路径约束**（承 D3 drop/reseed 与 ADR-007）:`logging.ttl.days` 在 **model 建表期**（`ginkgo init` create_all）注入 TTL;改 config.yaml 后**存量已建表不会自动跟随**（create_all 不 ALTER 已有表）,需 drop 三表 + `ginkgo init` 重建才套用新值。日志 TTL 通常设一次长期不变,一次性重建可接受;若未来要"改值即时生效不丢数据",需另开 `ALTER TABLE ... MODIFY TTL` 路径（本 ADR 不含）。

### D3 存量库:drop + `ginkgo init` 重建（非 ALTER MODIFY TTL）

master/test 已有无 TTL 表,`create_all` 不补（ADR-007）。存量迁移走 **drop 三张日志表 + `ginkgo init`（create_all 带新 model 重建）**,而非 `ALTER TABLE ... MODIFY TTL`。

## Considered Options

- **起算字段**:
  - A `business_timestamp`:否决——回测业务历史时间,历史回测日志一写入即过期。
  - B `ingested_at`:否决——`vector.toml` 未填充该列,`model_logs.py:157` `default=None`,NULL 导致 TTL 不触发;且需同步改 vector。
  - **C `timestamp`（本 ADR）**:墙钟写入时间,非空实时,安全;无需改 vector。
  - D 分表策略（backtest 用 ingested_at / component+performance 用 timestamp）:否决——引入字段不一致 + 仍需 vector 填 ingested_at,复杂度高于 C 且收益不抵。

- **存量迁移**:
  - P `ALTER TABLE ... MODIFY TTL`:否决——保留历史,但需独立迁移工具/CLI 长期维护,且 ADR-007 精神是"model 驱动、禁手动 ALTER"。
  - **Q drop + reseed（本 ADR）**:简单,create_all 重建即带新 TTL;代价是丢存量历史日志。
  - R 只管新建、存量不迁:否决——不解决用户原诉求（存量库继续无限增长）。

## Rationale

- **`timestamp` 是唯一安全且零改动的起算字段**:墙钟时间天然单调递增、非空,与回测业务时间解耦（ADR-023）。误用 `business_timestamp` 是该领域最可能的事故,故显式立 ADR 防后续 agent/人踩坑。
- **drop + reseed 与 ADR-007 一致**:model 驱动建表是正解,存量漂移靠重建非 ALTER（与 `arch_ch_create_all_no_alter_drift`、`arch_master_mysql_never_migrated` 同源处置）。自用项目历史日志无强审计需求,drop 可接受。
- **GCONF 接线而非硬编码**:TTL 天数因表而异（180/90/30）且可能调整,配置化优于魔法值;同时消除 ADR-037 型死参数。

## Consequences

- **正**:三表靠 CH 原生 TTL 后台 merge 自动清理,磁盘不再无限增长;`LOGGING_TTL_*` 活化为可调配置。
- **负**:
  - drop 丢失存量历史日志（不可逆,本 ADR 接受）。
  - **TTL 天数变更需再次 drop**:因 create_all 不改已有表,运行时改 GCONF 不会作用到已建表的 TTL。若未来需"热调 TTL 不丢数据",须另开 `ALTER TABLE ... MODIFY TTL` 路径（本 ADR 不含,留后续 ADR）。
  - CH TTL 是**真后台自动删除**（非"仅标记靠外部清"）:过期行在 background merge 期间被物理删除,无需外部 cron/DELETE。但**非插入即删**——受 `merge_with_ttl_timeout` 节流,**默认 14400s ≈ 4 小时**,过期行最多滞留约 4h 才清（设很小也不保证立即,merge 需调度+资源）。日常无需手动。
  - 手动立即触发（逃生口,不等 4h）:`ALTER TABLE ... MATERIALIZE TTL`（轻,重应用 TTL 于存量 parts）/ `OPTIMIZE TABLE ... FINAL`（重,全表 merge 副带清,IO 与临时空间翻倍）。#6859 `cleanup --force` 实现时据此择优。
- **关联约束**:受 ADR-007（禁 ALTER）、ADR-023（时间 seam）、ADR-032（CH 时序审计层定位）约束。

## Sub-issues

- **S1** 三表 model 注入 TTL（读 GCONF）+ 存量 drop/`ginkgo init` 重建 + 测试（`SHOW CREATE` 验 TTL 子句）
- **S2** 清理可观测 + 手动触发 CLI（`ttl-status` 查三表 TTL/行数/最老记录、`cleanup --force` 跑 `OPTIMIZE` 触发后台清）+ quickstart 文档
