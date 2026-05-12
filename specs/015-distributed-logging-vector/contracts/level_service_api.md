# API Contract: LevelService

**Service**: LevelService - 日志级别管理服务
**Version**: 1.0.0
**Date**: 2026-03-10

## Overview

LevelService 是日志级别管理服务，支持运行时动态修改日志级别，无需重启服务。提供 CLI 命令和 HTTP API 两种调用方式。

---

## API Methods

### 1. set_level

动态设置指定模块的日志级别。

**Signature**:
```python
def set_level(
    module_name: str,
    level: LEVEL_TYPES
) -> bool:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| module_name | str | 是 | 模块名称（如 backtest、trading、data） |
| level | LEVEL_TYPES | 是 | 日志级别枚举 |

**Returns**:
```python
bool  # 设置成功返回 True，失败返回 False
```

**模块白名单**:
- 允许动态调整: backtest、trading、data、analysis
- 不允许动态调整: libs、services（核心模块）

**Example**:
```python
from ginkgo.enums import LEVEL_TYPES

# 设置 backtest 模块为 DEBUG 级别
level_service.set_level("backtest", LEVEL_TYPES.DEBUG)
```

---

### 2. get_level

获取指定模块的当前日志级别。

**Signature**:
```python
def get_level(module_name: str) -> Optional[int]:
```

**Parameters**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| module_name | str | 是 | 模块名称 |

**Returns**:
```python
Optional[int]  # 返回日志级别整数值，模块不存在返回 None
```

**Example**:
```python
level = level_service.get_level("backtest")
print(f"当前级别: {LEVEL_TYPES.from_int(level)}")
```

---

### 3. get_all_levels

获取所有模块的当前日志级别。

**Signature**:
```python
def get_all_levels() -> Dict[str, int]:
```

**Returns**:
```python
Dict[str, int]  # {模块名: 日志级别整数值}
```

**Example**:
```python
levels = level_service.get_all_levels()
for module, level in levels.items():
    print(f"{module}: {LEVEL_TYPES.from_int(level)}")
```

---

### 4. reset_levels

重置所有模块的日志级别为配置文件默认值。

**Signature**:
```python
def reset_levels() -> bool:
```

**Returns**:
```python
bool  # 重置成功返回 True
```

**Example**:
```python
level_service.reset_levels()
```

---

## CLI 命令

### ginkgo logging set-level

动态设置日志级别。

**Usage**:
```bash
ginkgo logging set-level <LEVEL> [--module MODULE]
```

**Arguments**:

| 参数 | 说明 |
|------|------|
| LEVEL | 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| --module MODULE | 模块名称（默认所有模块） |

**Examples**:
```bash
# 设置所有模块为 DEBUG 级别
ginkgo logging set-level DEBUG

# 设置 backtest 模块为 DEBUG 级别
ginkgo logging set-level DEBUG --module backtest

# 设置 trading 模块为 ERROR 级别
ginkgo logging set-level ERROR --module trading
```

---

### ginkgo logging get-level

获取当前日志级别。

**Usage**:
```bash
ginkgo logging get-level [--module MODULE]
```

**Arguments**:

| 参数 | 说明 |
|------|------|
| --module MODULE | 模块名称（不指定则显示所有模块） |

**Examples**:
```bash
# 获取所有模块的日志级别
ginkgo logging get-level

# 获取 backtest 模块的日志级别
ginkgo logging get-level --module backtest
```

---

### ginkgo logging reset-level

重置日志级别为配置文件默认值。

**Usage**:
```bash
ginkgo logging reset-level
```

---

## HTTP API

### POST /api/logging/level

设置日志级别。

**Request**:
```json
{
    "module": "backtest",
    "level": "DEBUG"
}
```

**Response**:
```json
{
    "success": true,
    "message": "日志级别已更新"
}
```

---

### GET /api/logging/level

获取日志级别。

**Query Parameters**:
- `module` (optional): 模块名称

**Response**:
```json
{
    "backtest": 0,
    "trading": 1,
    "data": 1,
    "analysis": 1
}
```

---

### POST /api/logging/level/reset

重置日志级别。

**Response**:
```json
{
    "success": true,
    "message": "日志级别已重置"
}
```

---

## 配置参数

### GCONF 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| LOGGING_LEVEL_WHITELIST | list | ["backtest", "trading", "data", "analysis"] | 允许动态调整的模块白名单 |
| LOGGING_DEFAULT_LEVEL | str | "INFO" | 默认日志级别 |

---

## 性能要求

- 动态修改日志级别生效时间 < 1 秒
- 日志级别 CLI 命令响应时间 < 500ms
- HTTP API 获取日志级别响应时间 < 200ms
