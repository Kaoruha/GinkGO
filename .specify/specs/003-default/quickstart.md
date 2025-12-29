# Quick Start: Code Context Headers for LLM Understanding

**Feature**: 003-code-context-headers
**Target Audience**: 开发者
**Time to Complete**: 10 分钟

---

## 目标

为 Ginkgo 项目的所有 Python 文件添加标准化的三行上下文头部注释，帮助 AI 大模型快速理解代码结构。

---

## 头部格式说明

每个 Python 文件顶部应包含以下三行注释：

```python
# Upstream: <简短功能名称列表>      # 哪些模块会使用本文件
# Downstream: <简短功能名称列表>    # 本文件使用哪些模块
# Role: <模块内作用>                # 在模块中的职责
```

**示例**：

```python
# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Models, Event System
# Role: 定义基础策略类和策略接口

from ginkgo.trading.strategies import BaseStrategy
# ... 其余代码
```

---

## 快速开始

### 步骤 0: 设置大模型 API 密钥（首次使用）

在使用自动化脚本前，需要先运行大模型分析，理解项目结构：

```bash
# 设置 Anthropic API 密钥（用于 Claude 3.5 Sonnet）
export ANTHROPIC_API_KEY="your-api-key-here"

# 或添加到 ~/.bashrc 或 ~/.zshrc
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**可选**：使用本地模型（如 Ollama + CodeLlama）代替云端 API。

---

### 步骤 1: 运行大模型项目分析

首次使用前，需要让大模型分析项目结构：

```bash
# 分析整个项目结构（使用 src/ 作为根目录）
python scripts/analyze_project.py \
    --root src/ginkgo \
    --output .module_mapping.json \
    --cache

# 输出示例：
# 📊 Analyzing project structure...
# 🔍 Found 45 modules to analyze
# 🤖 Running LLM analysis (may take 5-10 minutes)...
# ✅ Analysis complete: 45 modules analyzed
# 💾 Cache saved to .module_mapping.json
```

**分析结果示例**（`.module_mapping.json`）：
```json
{
  "version": "1.0",
  "analyzed_at": "2025-12-29T00:00:00Z",
  "root_path": "/home/user/Ginkgo/src/ginkgo",
  "modules": {
    "src/ginkgo/data": {
      "module_name": "Data Layer",
      "description": "数据访问层，负责数据存储、查询和管理",
      "level": 0,
      "parent": null,
      "classes": [
        {"name": "MBar", "description": "K线数据模型"},
        {"name": "MTick", "description": "Tick数据模型"}
      ],
      "functions": [],
      "files": ["models/bar.py", "models/tick.py", ...],
      "upstream": ["Trading Strategies", "Analysis Modules"],
      "downstream": ["ClickHouse", "MySQL"],
      "children": ["src/ginkgo/data/models", "src/ginkgo/data/sources"],
      "analyzed_at": "2025-12-29T00:00:00Z",
      "file_hashes": {
        "models/bar.py": "abc123...",
        "models/tick.py": "def456..."
      }
    }
  }
}
```

**性能说明**：
- 首次分析：~5-10 分钟（~1000 文件，~50 模块）
- 增量分析：~30-60 秒（仅分析变更的模块）
- API 成本：~$1-2 USD/次（使用缓存降低 90%+）

---

### 步骤 2: 检查缺失的头部

```bash
# 运行检查脚本（会自动加载 .module_mapping.json）
python scripts/check_headers.py

# 输出示例：
# ✅ 850 files have headers
# ❌ 120 files missing headers
# 📁 Missing: src/ginkgo/data/models/mymodel.py
# 📁 Missing: tests/unit/test_mymodule.py
```

---

### 步骤 3: 生成头部模板

```bash
# 为所有缺失头部的文件生成模板（基于 LLM 分析结果）
python scripts/generate_headers.py --dry-run

# 检查生成的模板（不修改文件）
# 查看生成的头部是否符合预期
```

**说明**：生成脚本会自动加载 `.module_mapping.json`，基于大模型分析结果生成准确的头部注释。

---

### 步骤 4: 应用头部到文件

```bash
# 实际应用头部到文件
python scripts/generate_headers.py

# 输出示例：
# ✅ Added header to src/ginkgo/data/models/mymodel.py
# ✅ Added header to tests/unit/test_mymodule.py
# 📊 Processed 120 files in 3.5 seconds
```

---

### 步骤 5: 验证头部准确性

```bash
# 验证头部信息是否准确
python scripts/verify_headers.py

# 输出示例：
# ✅ 850 headers are accurate
# ⚠️  15 headers need review
# 📁 Check: src/ginkgo/trading/mystrategy.py
#    - Upstream: "Unknown Module" (please verify)
```

---

## 常见使用场景

### 场景 1: 首次设置 - 完整流程

```bash
# 1. 设置 API 密钥
export ANTHROPIC_API_KEY="sk-ant-xxx..."

# 2. 运行大模型分析（首次，5-10分钟）
python scripts/analyze_project.py --root src/ginkgo --output .module_mapping.json

# 3. 检查缺失的头部
python scripts/check_headers.py

# 4. 生成头部（预览）
python scripts/generate_headers.py --dry-run

# 5. 应用头部
python scripts/generate_headers.py

# 6. 验证准确性
python scripts/verify_headers.py
```

---

### 场景 2: 代码变更后增量更新

```bash
# 修改了一些代码后，更新分析结果
python scripts/analyze_project.py \
    --root src/ginkgo \
    --output .module_mapping.json \
    --cache  # 自动使用缓存，仅分析变更的模块

# 重新生成受影响文件的头部
python scripts/generate_headers.py --directory src/ginkgo/data
```

---

### 场景 3: 为单个文件添加头部

```bash
# 手动为单个文件生成头部
python scripts/generate_headers.py --file src/ginkgo/data/models/mymodel.py

# 预览生成的头部
# Upstream: CRUD Operations, Data Services
# Downstream: Data Sources, ClickHouse
# Role: 定义 MyModel 数据模型类
```

---

### 场景 4: 批量处理特定目录

```bash
# 只处理 src/ginkgo/data 目录
python scripts/generate_headers.py --directory src/ginkgo/data

# 只处理测试文件
python scripts/generate_headers.py --directory tests
```

---

### 场景 5: 强制重新分析整个项目

```bash
# 清除缓存，强制重新分析
python scripts/analyze_project.py \
    --root src/ginkgo \
    --output .module_mapping.json \
    --force  # 忽略缓存，重新分析所有模块

# 重新生成所有头部
python scripts/generate_headers.py --force
```

---

### 场景 6: 使用本地模型（无网络）

```bash
# 使用 Ollama 本地模型
export LLM_PROVIDER="ollama"
export LLM_MODEL="codellama"

python scripts/analyze_project.py \
    --root src/ginkgo \
    --output .module_mapping.json
```

---

### 场景 7: CI/CD 自动集成

```yaml
# .github/workflows/update-headers.yml
name: Update Code Context Headers

on:
  push:
    branches: [master, main]

jobs:
  update-headers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install anthropic tenacity

      - name: Run LLM analysis
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python scripts/analyze_project.py \
            --root src/ginkgo \
            --output .module_mapping.json \
            --cache

      - name: Generate headers
        run: |
          python scripts/generate_headers.py

      - name: Verify headers
        run: |
          python scripts/verify_headers.py

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add -A
          git diff --quiet && git diff --staged --quiet || \
          git commit -m "chore: update code context headers [skip ci]"

      - name: Push changes
        if: github.event_name == 'push'
        run: git push
```

---

## 头部示例

### 核心模块文件

**数据模型 (`src/ginkgo/data/models/bar.py`)**:
```python
# Upstream: CRUD Operations, Data Services
# Downstream: ClickHouse, MySQL
# Role: 定义 MBar K线数据模型

from ginkgo.data.models import MClickBase
# ...
```

**策略基类 (`src/ginkgo/trading/strategies/base_strategy.py`)**:
```python
# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Models, Event System
# Role: 定义 BaseStrategy 基类和策略接口

from abc import ABC, abstractmethod
# ...
```

**CRUD 操作 (`src/ginkgo/data/cruds/bar.py`)**:
```python
# Upstream: Data Services, CLI Commands
# Downstream: Data Models, ClickHouse
# Role: 实现 Bar CRUD 操作类

from ginkgo.data.cruds import BaseCRUD
# ...
```

### 测试文件

**单元测试 (`tests/unit/test_bar.py`)**:
```python
# Upstream: CI/CD Pipeline
# Downstream: src/ginkgo/data/models/bar.py
# Role: 测试 MBar 模型 CRUD 操作

import pytest
# ...
```

### __init__.py 文件

**数据模块 (`src/ginkgo/data/__init__.py`)**:
```python
# Upstream: Trading Strategies, Analysis Modules
# Downstream: Module Exports
# Role: Data 模块初始化和公共导出

from ginkgo.data import models, cruds, services
# ...
```

---

## 命令行参数

### analyze_project.py（大模型分析）

| 参数 | 短选项 | 说明 |
|------|--------|------|
| `--root` | `-r` | 项目根目录（默认：src/ginkgo） |
| `--output` | `-o` | 输出文件路径（默认：.module_mapping.json） |
| `--cache` | - | 启用缓存，跳过未变更的模块 |
| `--force` | - | 强制重新分析，忽略缓存 |
| `--provider` | `-p` | LLM 提供商（anthropic/openai/ollama，默认：anthropic） |
| `--model` | `-m` | 模型名称（默认：claude-3-5-sonnet-20241022） |
| `--batch-size` | `-b` | 批处理大小（默认：5） |
| `--max-workers` | `-w` | 并发分析数（默认：3） |

### check_headers.py

| 参数 | 短选项 | 说明 |
|------|--------|------|
| `--directory` | `-d` | 指定检查目录（默认：整个项目） |
| `--verbose` | `-v` | 显示详细输出 |
| `--json` | `-j` | 输出 JSON 格式 |

### generate_headers.py

| 参数 | 短选项 | 说明 |
|------|--------|------|
| `--file` | `-f` | 处理单个文件 |
| `--directory` | `-d` | 处理指定目录 |
| `--dry-run` | - | 预览模式，不修改文件 |
| `--force` | - | 覆盖现有头部 |
| `--max-workers` | `-w` | 并发线程数（默认：4） |
| `--analysis` | `-a` | 分析结果文件（默认：.module_mapping.json） |

### verify_headers.py

| 参数 | 短选项 | 说明 |
|------|--------|------|
| `--directory` | `-d` | 指定验证目录 |
| `--fix` | - | 自动修复可修复的问题 |
| `--verbose` | `-v` | 显示详细输出 |
| `--analysis` | `-a` | 分析结果文件（默认：.module_mapping.json） |

---

## 性能指标

| 操作 | 预期时间 | 说明 |
|------|----------|------|
| **大模型分析（首次）** | ~5-10 分钟 | ~1000 文件，~50 模块 |
| **大模型分析（增量）** | ~30-60 秒 | 仅分析变更模块 |
| 检查头部 | < 1 分钟 | ~1000 文件 |
| 生成头部 | < 5 分钟 | ~1000 文件 |
| 验证头部 | < 2 分钟 | ~1000 文件 |

**成本估算**（Claude 3.5 Sonnet）：
- 首次分析：~$1-2 USD
- 增量分析：~$0.1-0.2 USD（使用缓存，降低 90%+）

---

## 故障排查

### 问题 1: API 密钥未设置

```bash
$ python scripts/analyze_project.py
Error: ANTHROPIC_API_KEY environment variable not set
```

**解决方案**:
```bash
export ANTHROPIC_API_KEY="sk-ant-xxx..."
# 或添加到 ~/.bashrc
echo 'export ANTHROPIC_API_KEY="sk-ant-xxx..."' >> ~/.bashrc
```

---

### 问题 2: API 调用失败

```bash
$ python scripts/analyze_project.py
Error: API request failed: 401 Unauthorized
```

**解决方案**:
- 检查 API 密钥是否正确
- 确认 API 密钥有足够的配额
- 检查网络连接是否正常

---

### 问题 3: 脚本执行失败

```bash
$ python scripts/generate_headers.py
Error: Unable to parse src/ginkgo/broken_file.py
```

**解决方案**:
- 检查文件是否有语法错误
- 使用 `--verbose` 查看详细错误信息
- 修复语法错误后重新运行

---

### 问题 4: 生成的头部不准确

```bash
$ python scripts/verify_headers.py
⚠️ src/ginkgo/mymodule.py: Upstream shows "Unknown Module"
```

**解决方案**:
- 运行 `analyze_project.py --force` 重新分析项目结构
- 手动编辑头部注释
- 检查 `.module_mapping.json` 是否包含该模块的分析结果

---

### 问题 5: 性能较慢

```bash
$ python scripts/analyze_project.py
🤖 Analyzing module 1/45... (this may take a while)
```

**解决方案**:
- 增加并发分析数：`--max-workers 5`
- 减小批处理大小：`--batch-size 3`
- 使用缓存：`--cache`（默认启用）

---

### 问题 6: 缓存失效

```bash
$ python scripts/analyze_project.py --cache
⚠️ Cache mismatch for module src/ginkgo/data
```

**解决方案**:
- 这是正常行为，脚本会自动重新分析变更的模块
- 如需强制重新分析：`--force`
- 如需清除缓存：删除 `.module_mapping.json`

---

### 问题 7: 本地模型连接失败

```bash
$ export LLM_PROVIDER="ollama"
$ python scripts/analyze_project.py
Error: Failed to connect to Ollama service
```

**解决方案**:
```bash
# 确保 Ollama 服务运行
ollama serve

# 拉取模型
ollama pull codellama

# 检查服务状态
curl http://localhost:11434/api/tags
```

---

## 下一步

- 📖 阅读完整设计文档：[research.md](./research.md)
- 🔧 查看 CLI 参数：运行脚本 `--help` 选项
- ✅ 运行验证：`python scripts/verify_headers.py`

---

**Quick Start Status**: ✅ **COMPLETE** - 提供完整的使用指南和示例
