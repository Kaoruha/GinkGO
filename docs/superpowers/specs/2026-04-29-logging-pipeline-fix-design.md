# 日志链路修复设计

## 问题

GLOG 写入 `~/.ginkgo/logs/`，Vector 监听 `/var/log/ginkgo/`，路径不匹配导致日志到不了 ClickHouse。`LOGGING_PATH` 不支持环境变量覆盖，容器部署时无法通过注入环境变量统一路径。

## 方案

保持 Vector 采集架构不变，通过 `GINKGO_LOGGING_PATH` 环境变量统一 GLOG 写入路径和 Vector 读取路径。

## 改动

### 1. config.py — LOGGING_PATH 增加环境变量优先级

优先级：`GINKGO_LOGGING_PATH` 环境变量 > `config.yml` 的 `log_path` > 默认值 `~/.ginkgo/logs`

```python
@property
def LOGGING_PATH(self) -> str:
    env_path = os.environ.get("GINKGO_LOGGING_PATH")
    if env_path:
        return env_path
    path = self._get_config("log_path")
    if path is None:
        return os.path.join(os.path.expanduser("~"), ".ginkgo", "logs")
    return path
```

### 2. logger.py — 修正注释

`_setup_json_file_handler` 方法注释中 `/var/log/ginkgo/` 硬编码描述改为引用 `LOGGING_PATH`。

### 3. vector.toml — 使用环境变量

```toml
[sources.ginkgo_logs]
type = "file"
include = ["${GINKGO_LOGGING_PATH}/**/*..log"]
```

容器部署时通过 docker-compose 注入 `GINKGO_LOGGING_PATH=/var/log/ginkgo`。

## 测试覆盖

| 测试 | 验证内容 |
|---|---|
| `test_logging_path_env_override` | `GINKGO_LOGGING_PATH` 环境变量覆盖 `config.yml` |
| `test_json_file_output_path` | GLOG 实际写入 `LOGGING_PATH` 指定的目录 |
| `test_json_format_fields` | JSON 行包含必需字段：timestamp, level, message, log_category, trace_id |
| `test_log_category_routing` | `GLOG.backtest.*` 输出 `log_category=backtest`，component/performance 同理 |
| `test_trace_id_in_json` | `set_trace_id` 后 JSON 输出包含 trace_id 字段 |
| `test_vector_config_path_match` | 解析 vector.toml，验证 include 路径使用 `${GINKGO_LOGGING_PATH}` |

## 不改的东西

- LogService 查询逻辑不变
- LogService CRUD 不变
- 不添加端到端集成测试（需要 Vector + ClickHouse 运行）
- 不改日志模型（MBacktestLog 等）
