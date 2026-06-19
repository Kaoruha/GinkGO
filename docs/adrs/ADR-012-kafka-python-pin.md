# ADR-012: kafka-python 依赖锁定与异常基类收口

**Status:** Accepted
**Date:** 2026-06-19

## Context

`pyproject.toml:59` 的 `"kafka-python>=3.0.0,<4"` 是全仓 79 个运行时依赖（`pyproject` `[project] dependencies` 实测）中**唯一**采用双端 pin（下限 + 上限）的依赖。其余依赖一律单下限（`redis>=4.6.0`、`psycopg>=3.2.0`、`fastapi>=0.116.0` …）。这个"唯一特例"背后是一次实战崩溃。

根因见 commit `33e5f0bc`（`fix(#6157)`，2026-06-15）：容器 `Dockerfile` 走 `uv pip install --system .`，**不读 `uv.lock`**，resolver 在仅有下限约束时抓到 `kafka-python 3.0.0`。该大版本**移除 `NoBrokersAvailable`**（并入 `KafkaConnectionError`），导致 `src/ginkgo/data/drivers/ginkgo_kafka.py` 一 `import` 即 `ImportError`，livecore 启动崩溃循环。关联修复 `2b032b52`（`#6154`/`#6169`）：schedule 链路的 kafka 3.0 兼容。

异常侧的配套收口：`ginkgo_kafka.py:19` 统一 `from kafka.errors import KafkaError`，4 处 `except KafkaError`（:67/:112/:149/:235）——`KafkaError` 是 2.x/3.x 共有的稳定基类，取代跨版本会漂移的具体子类 `NoBrokersAvailable`/`KafkaConnectionError`。

## Decision

1. **依赖**：`kafka-python` 在 `pyproject.toml` 双端 pin `>=3.0.0,<4`（全仓唯一例外，不得放开上限）。
2. **异常捕获**：统一用基类 `KafkaError`，**禁**再用 `NoBrokersAvailable` / `KafkaConnectionError` 等 3.0 重组后会消失的具体子类。

## Rationale

- **为何唯独 pin、且必须落在 pyproject**：容器构建不读 `uv.lock`，下限约束挡不住 resolver 抓 3.0.0 breaking；lock 不可移植，所以 pin 必须下沉到 `pyproject.toml` 才能在所有安装路径生效。
- **为何用基类而非具体子类**：kafka-python 3.0 对异常类做了重组（`NoBrokersAvailable` 被删并入 `KafkaConnectionError`），具体子类跨大版本不稳定；`KafkaError` 作为基类在 2.x/3.x 都存在，是唯一稳定捕获点。
- **已排除 A：靠 `uv.lock` 保证可复现**——容器 `uv pip install --system .` 不读 lock，失效。
- **已排除 B：放开上限跟主线**——每次上游 breaking 都会重现本次 livecore 崩溃循环，代价高于 pin 维护成本。

## Consequences

- **难逆转**：锁 `<4` 等于承诺长期手工跟进上游大版本；解锁需重做异常基类适配并补守护测试。
- **反直觉**：全仓唯一双端 pin，违背"pyproject 只放下限"惯例，新人极易误删上限"统一风格"——这正是本 ADR 要挡住的动作。
- **已知遗留（决策落地未全覆盖，须补）**：`install.py:309` 的 `kafka_reset()` 仍 `from kafka.errors import NoBrokersAvailable, KafkaConnectionError`，`:322 except NoBrokersAvailable`。在 kafka-python 3.0.0 下该 `import` 行即 `ImportError`，函数不可调用。现有守护测试只覆盖 `src/ginkgo`，未覆盖 `install.py`。**收口动作**：`install.py` 同样改用 `KafkaError` 基类，并扩守护测试到 install 入口。
- **交叉引用**：ADR-006（多 DB/中间件角色分工，Kafka 属消息中间件角色；本 ADR 聚焦"依赖锁定 + 异常基类"这一横切纪律，非角色分工本身）。

## 判定标准自检

- ① **难逆转**：pin + 异常基类收口，回退即重现 livecore 崩溃——满足。
- ② **反直觉**：全仓唯一双端 pin 特例——满足。
- ③ **真实权衡**：下限/上限 pin vs lock 可复现性、跟主线 vs pin 维护——满足。
