# 日志链路修复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 GLOG 写入路径与 Vector 采集路径不匹配的问题，使日志能正确流入 ClickHouse。

**Architecture:** 通过 `GINKGO_LOGGING_PATH` 环境变量统一 GLOG 写入路径和 Vector 读取路径。config.py 增加环境变量优先级，vector.toml 改用环境变量引用，logger.py 修正注释。

**Tech Stack:** Python 3.12, pytest, TOML (Vector config)

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `src/ginkgo/libs/core/config.py:341-349` | Modify | `LOGGING_PATH` property 增加环境变量优先级 |
| `src/ginkgo/libs/core/logger.py:507-511,520` | Modify | 修正注释，去掉硬编码路径描述 |
| `deploy/vector/vector.toml:15-17` | Modify | `include` 改用 `${GINKGO_LOGGING_PATH}` 环境变量 |
| `tests/unit/libs/test_logging_pipeline.py` | Create | 测试 LOGGING_PATH 环境变量覆盖、JSON 文件输出格式、Vector 配置一致性 |

---

### Task 1: config.py — LOGGING_PATH 增加环境变量优先级

**Files:**
- Modify: `src/ginkgo/libs/core/config.py:341-349`
- Test: `tests/unit/libs/test_logging_pipeline.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/libs/test_logging_pipeline.py`：

```python
"""
日志链路修复测试

验证 GLOG → 文件 → Vector 配置的一致性：
- LOGGING_PATH 环境变量覆盖
- JSON 文件输出路径和格式
- Vector 配置路径与 GLOG 一致
"""

import pytest
import os
import json
import tempfile
import shutil

from ginkgo.libs.core.config import GinkgoConfig


@pytest.mark.unit
class TestLoggingPathEnvOverride:
    """验证 LOGGING_PATH 支持环境变量覆盖"""

    def test_env_variable_takes_priority(self):
        """GINKGO_LOGGING_PATH 环境变量优先于 config.yml"""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GINKGO_LOGGING_PATH", "/custom/log/path")
            config = GinkgoConfig()
            assert config.LOGGING_PATH == "/custom/log/path"

    def test_config_yml_as_fallback(self):
        """没有环境变量时回退到 config.yml"""
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("GINKGO_LOGGING_PATH", raising=False)
            config = GinkgoConfig()
            # 应返回 config.yml 中的值或默认值
            path = config.LOGGING_PATH
            assert path is not None
            assert len(path) > 0

    def test_default_path_without_config(self):
        """没有环境变量也没有 config.yml 时使用默认值"""
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("GINKGO_LOGGING_PATH", raising=False)
            config = GinkgoConfig()
            path = config.LOGGING_PATH
            assert ".ginkgo" in path or "logs" in path
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/test_logging_pipeline.py::TestLoggingPathEnvOverride -v
```

Expected: `test_env_variable_takes_priority` FAIL（当前 LOGGING_PATH 不读环境变量）

- [ ] **Step 3: 修改 LOGGING_PATH property**

修改 `src/ginkgo/libs/core/config.py` 第 341-349 行：

```python
    @property
    def LOGGING_PATH(self) -> str:
        # 优先级：环境变量 > config.yml > 默认值
        env_path = os.environ.get("GINKGO_LOGGING_PATH")
        if env_path:
            return env_path
        path = self._get_config("log_path")
        if path is None:
            # 提供默认日志路径
            import os
            default_path = os.path.join(os.path.expanduser("~"), ".ginkgo", "logs")
            return default_path
        return path
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/test_logging_pipeline.py::TestLoggingPathEnvOverride -v
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/libs/core/config.py tests/unit/libs/test_logging_pipeline.py
git commit -m "feat(config): add GINKGO_LOGGING_PATH env var override for LOGGING_PATH"
```

---

### Task 2: logger.py — 修正注释

**Files:**
- Modify: `src/ginkgo/libs/core/logger.py:507-511,520`

- [ ] **Step 1: 修正 docstring 和行内注释**

修改 `src/ginkgo/libs/core/logger.py` 第 507-511 行，将：

```python
    def _setup_json_file_handler(self):
        """
        容器模式：设置 JSON 格式文件日志处理器

        输出到 /var/log/ginkgo/ 目录，使用 JSON 格式供 Vector 采集解析。
        """
```

改为：

```python
    def _setup_json_file_handler(self):
        """
        JSON 格式文件日志处理器

        输出到 LOGGING_PATH 目录，使用 JSON 格式供 Vector 采集解析。
        """
```

修改第 520 行，将：

```python
            # 容器模式使用 /var/log/ginkgo/ 路径
```

改为：

```python
            # 写入 LOGGING_PATH（可通过 GINKGO_LOGGING_PATH 环境变量覆盖）
```

- [ ] **Step 2: 验证无功能变化**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/test_core_logger_existing.py -v -x
```

Expected: 现有测试全部通过（仅注释变更，不影响逻辑）

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/libs/core/logger.py
git commit -m "docs(logger): fix hardcoded path comments, reference LOGGING_PATH"
```

---

### Task 3: vector.toml — 使用环境变量

**Files:**
- Modify: `deploy/vector/vector.toml:15-17`

- [ ] **Step 1: 修改 include 路径**

修改 `deploy/vector/vector.toml` 第 17 行，将：

```toml
include = ["/var/log/ginkgo/**/*.log"]
```

改为：

```toml
include = ["${GINKGO_LOGGING_PATH}/**/*.log"]
```

同时在文件头部（第 5 行之后）添加环境变量说明注释：

```toml
# 环境变量：
#   GINKGO_LOGGING_PATH - 日志文件目录（与 GLOG 写入路径一致）
#   默认值: ~/.ginkgo/logs (本地开发) 或 /var/log/ginkgo (容器部署)
```

- [ ] **Step 2: Commit**

```bash
git add deploy/vector/vector.toml
git commit -m "fix(vector): use GINKGO_LOGGING_PATH env var for log file path"
```

---

### Task 4: 测试 JSON 文件输出格式

**Files:**
- Modify: `tests/unit/libs/test_logging_pipeline.py`

- [ ] **Step 1: 写测试**

在 `tests/unit/libs/test_logging_pipeline.py` 末尾追加：

```python
@pytest.mark.unit
class TestJsonFileOutput:
    """验证 GLOG JSON 文件输出路径和格式"""

    def test_json_file_written_to_logging_path(self, tmp_path):
        """GLOG 实际写入 LOGGING_PATH 指定的目录"""
        log_dir = str(tmp_path / "logs")
        os.makedirs(log_dir, exist_ok=True)

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GINKGO_LOGGING_PATH", log_dir)
            # 重新导入以获取新的 LOGGING_PATH
            from ginkgo.libs.core import config as cfg
            mp.setattr(cfg, "LOGGING_PATH", log_dir)

            from ginkgo.libs.core.logger import GinkgoLogger
            logger = GinkgoLogger(
                "test_path_check",
                file_names=["test_pipeline"],
                console_log=False,
            )

            logger.INFO("pipeline test message")

            # flush handlers
            for h in logger.file_handlers:
                h.flush()

            # 验证文件被创建在 log_dir 下
            log_files = os.listdir(log_dir)
            assert any("test_pipeline" in f for f in log_files), f"Expected log file in {log_dir}, found: {log_files}"

            # 清理
            for h in logger.file_handlers:
                h.close()
                logger.logger.removeHandler(h)

    def test_json_format_required_fields(self, tmp_path):
        """JSON 行包含必需字段：timestamp, level, message, log_category, trace_id"""
        log_dir = str(tmp_path / "logs")
        os.makedirs(log_dir, exist_ok=True)

        from ginkgo.libs.core.logger import GinkgoLogger, set_trace_id, clear_trace_id
        log_file = os.path.join(log_dir, "test_format.log")

        logger = GinkgoLogger(
            "test_format",
            file_names=["test_format"],
            console_log=False,
        )

        # 设置 trace_id
        token = set_trace_id("trace-123")

        logger.INFO("format test message")

        for h in logger.file_handlers:
            h.flush()

        # 清理 trace_id
        clear_trace_id(token)

        # 读取日志文件并解析 JSON
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) >= 1, "No log lines written"
        parsed = json.loads(lines[-1])

        # 验证必需字段
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "message" in parsed
        assert parsed["message"] == "format test message"
        assert "trace_id" in parsed
        assert parsed["trace_id"] == "trace-123"

        # 清理
        for h in logger.file_handlers:
            h.close()
            logger.logger.removeHandler(h)

        # 清理临时日志文件
        for f in os.listdir(log_dir):
            os.remove(os.path.join(log_dir, f))


@pytest.mark.unit
class TestLogCategoryRouting:
    """验证 log_category 字段用于 Vector 路由"""

    def test_backtest_category_in_json(self, tmp_path):
        """GLOG.backtest.* 输出 log_category=backtest"""
        log_dir = str(tmp_path / "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "test_category.log")

        from ginkgo.libs.core.logger import GinkgoLogger, set_log_category
        logger = GinkgoLogger(
            "test_category",
            file_names=["test_category"],
            console_log=False,
        )

        set_log_category("backtest")
        logger.INFO("backtest event")
        for h in logger.file_handlers:
            h.flush()

        with open(log_file, "r") as f:
            lines = f.readlines()

        parsed = json.loads(lines[-1])
        assert parsed.get("log_category") == "backtest"

        # 清理
        for h in logger.file_handlers:
            h.close()
            logger.logger.removeHandler(h)
        for f in os.listdir(log_dir):
            os.remove(os.path.join(log_dir, f))


@pytest.mark.unit
class TestVectorConfigPathMatch:
    """验证 Vector 配置路径与 GLOG 使用同一变量"""

    def test_vector_includes_env_var(self):
        """vector.toml 的 include 路径使用 ${GINKGO_LOGGING_PATH}"""
        import tomllib

        toml_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "deploy", "vector", "vector.toml"
        )
        toml_path = os.path.normpath(toml_path)

        if not os.path.exists(toml_path):
            pytest.skip("vector.toml not found")

        with open(toml_path, "rb") as f:
            config = tomllib.load(f)

        includes = config["sources"]["ginkgo_logs"]["include"]
        assert len(includes) > 0, "No include patterns in vector.toml"

        # 验证路径引用了 GINKGO_LOGGING_PATH 环境变量
        assert any("${GINKGO_LOGGING_PATH}" in inc for inc in includes), \
            f"Expected ${{GINKGO_LOGGING_PATH}} in include patterns, got: {includes}"
```

- [ ] **Step 2: 运行测试**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/test_logging_pipeline.py -v
```

Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/unit/libs/test_logging_pipeline.py
git commit -m "test(logging): add pipeline tests for path override, JSON format, and Vector config"
```

---

### Task 5: 最终验证

- [ ] **Step 1: 运行全部相关测试**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/test_logging_pipeline.py tests/unit/libs/test_core_logger_existing.py -v
```

Expected: 全部 PASS

- [ ] **Step 2: 运行全部日志相关测试**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/ tests/unit/client/test_logging_cli.py -v
```

Expected: 全部 PASS，无回归
