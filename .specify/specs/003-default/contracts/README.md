# Contracts: Code Context Headers

**Feature**: 003-code-context-headers
**Date**: 2025-12-29

---

## 说明

本功能不涉及 API 契约定义。

功能仅涉及：
1. 为现有 Python 文件添加注释头部
2. 创建四个自动化脚本（内部工具）

因此不需要传统的 API 契约文档（OpenAPI/GraphQL schema 等）。

## 脚本接口规范

虽然不是传统意义上的 API，以下是四个自动化脚本的接口规范：

---

### analyze_project.py（大模型项目分析）

**功能**: 使用大模型分析项目结构，生成模块功能映射表

**CLI 参数**:

| 参数 | 短选项 | 类型 | 默认值 | 说明 |
|------|--------|------|--------|------|
| `--root` | `-r` | Path | `src/ginkgo` | 项目根目录 |
| `--output` | `-o` | Path | `.module_mapping.json` | 输出文件路径 |
| `--cache` | - | Flag | `False` | 启用缓存，跳过未变更的模块 |
| `--force` | - | Flag | `False` | 强制重新分析，忽略缓存 |
| `--provider` | `-p` | String | `anthropic` | LLM 提供商（anthropic/openai/ollama） |
| `--model` | `-m` | String | `claude-3-5-sonnet-20241022` | 模型名称 |
| `--batch-size` | `-b` | Int | `5` | 批处理大小（每批分析的模块数） |
| `--max-workers` | `-w` | Int | `3` | 并发分析数 |
| `--exclude` | `-e` | String | `venv,__pycache__,.git` | 排除的目录（逗号分隔） |

**环境变量**:

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | 是（如果使用 Anthropic） | Anthropic API 密钥 |
| `OPENAI_API_KEY` | 是（如果使用 OpenAI） | OpenAI API 密钥 |
| `LLM_PROVIDER` | 否 | 覆盖默认提供商 |
| `LLM_MODEL` | 否 | 覆盖默认模型 |

**返回**:
- Exit code 0: 分析成功
- Exit code 1: 分析失败
- 输出格式: JSON（保存到 `--output` 指定的文件）

**JSON 输出格式**:
```json
{
  "version": "1.0",
  "analyzed_at": "2025-12-29T00:00:00Z",
  "root_path": "/home/user/Ginkgo/src/ginkgo",
  "modules": {
    "src/ginkgo/data": {
      "module_path": "src/ginkgo/data",
      "module_name": "Data Layer",
      "description": "数据访问层，负责数据存储、查询和管理",
      "level": 0,
      "parent": null,
      "classes": [
        {"name": "MBar", "description": "K线数据模型"},
        {"name": "MTick", "description": "Tick数据模型"}
      ],
      "functions": [],
      "files": ["models/bar.py", "models/tick.py"],
      "upstream": ["Trading Strategies", "Analysis Modules"],
      "downstream": ["ClickHouse", "MySQL"],
      "children": ["src/ginkgo/data/models"],
      "analyzed_at": "2025-12-29T00:00:00Z",
      "file_hashes": {
        "models/bar.py": "abc123def456...",
        "models/tick.py": "789ghi012jkl..."
      }
    }
  }
}
```

**示例**:
```bash
# 基础用法
python scripts/analyze_project.py

# 自定义输出路径
python scripts/analyze_project.py --root src/ginkgo --output analysis/results.json

# 启用缓存（推荐）
python scripts/analyze_project.py --cache

# 强制重新分析
python scripts/analyze_project.py --force

# 使用 OpenAI 替代 Anthropic
python scripts/analyze_project.py --provider openai --model gpt-4

# 使用本地 Ollama
export LLM_PROVIDER="ollama"
export LLM_MODEL="codellama"
python scripts/analyze_project.py

# 增加并发（加快分析速度）
python scripts/analyze_project.py --max-workers 5 --batch-size 3
```

---

### check_headers.py

**功能**: 检查 Python 文件是否包含有效头部

**参数**:
- `--directory` | `-d`: 指定检查目录（默认：整个项目）
- `--verbose` | `-v`: 显示详细输出
- `--json` | `-j`: 输出 JSON 格式

**返回**:
- Exit code 0: 所有文件都有头部
- Exit code 1: 部分文件缺少头部
- 输出格式: Text (默认) 或 JSON (--json)

**示例**:
```bash
# 检查整个项目
python scripts/check_headers.py

# 输出 JSON 格式
python scripts/check_headers.py --json > report.json
```

---

### generate_headers.py

**功能**: 为缺失头部的文件生成三行注释（基于 `.module_mapping.json` 分析结果）

**参数**:
- `--file` | `-f`: 处理单个文件
- `--directory` | `-d`: 处理指定目录
- `--dry-run`: 预览模式
- `--force`: 覆盖现有头部
- `--max-workers` | `-w`: 并发线程数（默认：4）
- `--analysis` | `-a`: 分析结果文件（默认：`.module_mapping.json`）

**返回**:
- Exit code 0: 成功
- Exit code 1: 处理失败

**示例**:
```bash
# 基础用法（使用默认分析结果）
python scripts/generate_headers.py

# 使用自定义分析结果
python scripts/generate_headers.py --analysis custom/analysis.json

# 预览模式
python scripts/generate_headers.py --dry-run

# 处理单个文件
python scripts/generate_headers.py --file src/ginkgo/data/models/bar.py
```

---

### verify_headers.py

**功能**: 验证头部信息的准确性

**参数**:
- `--directory` | `-d`: 指定验证目录
- `--fix`: 自动修复可修复的问题
- `--verbose` | `-v`: 详细输出
- `--analysis` | `-a`: 分析结果文件（默认：`.module_mapping.json`）

**返回**:
- Exit code 0: 所有头部准确
- Exit code 1: 部分头部需要人工检查

**示例**:
```bash
# 验证整个项目
python scripts/verify_headers.py

# 自动修复可修复的问题
python scripts/verify_headers.py --fix

# 详细输出
python scripts/verify_headers.py --verbose
```

---

## JSON Schema 定义

### ModuleAnalysisResult

```typescript
{
  "module_path": string,              // 模块路径
  "module_name": string,              // 功能名称（简短）
  "description": string,              // 功能描述（2-3句话）
  "level": number,                    // 层级深度（0=顶层）
  "parent": string | null,            // 父模块路径
  "classes": ClassInfo[],             // 类信息
  "functions": FunctionInfo[],        // 函数信息
  "files": string[],                  // 文件列表
  "upstream": string[],               // 上游依赖（哪些模块会使用）
  "downstream": string[],             // 下游依赖（使用哪些模块）
  "children": string[],               // 子模块路径列表
  "analyzed_at": string,              // ISO 时间戳
  "file_hashes": Record<string, string>  // 文件 hash → 检测变化
}

interface ClassInfo {
  name: string;                       // 类名
  description: string;                // 功能描述
  base_classes?: string[];            // 基类列表（可选）
  methods?: string[];                 // 方法列表（可选）
}

interface FunctionInfo {
  name: string;                       // 函数名
  description: string;                // 功能描述
  parameters?: string[];              // 参数列表（可选）
}
```

### ProjectAnalysisCache

```typescript
{
  "version": string,                  // 格式版本（如 "1.0"）
  "analyzed_at": string,              // 分析时间（ISO 格式）
  "root_path": string,                // 项目根路径
  "modules": Record<string, ModuleAnalysisResult>  // 模块路径 → 分析结果
}
```

---

## 错误码定义

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| `E001` | API 密钥未设置 | 设置 `ANTHROPIC_API_KEY` 环境变量 |
| `E002` | API 调用失败 | 检查 API 密钥和网络连接 |
| `E003` | 文件解析失败 | 检查文件语法错误 |
| `E004` | 缓存文件损坏 | 删除 `.module_mapping.json` 重新分析 |
| `E005` | 模块未找到 | 运行 `analyze_project.py` 重新分析 |

---

## 结论

本功能无传统 API 契约定义需求，但提供了四个自动化脚本的完整接口规范。
