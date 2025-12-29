# Data Model: Code Context Headers (Updated with LLM Analysis)

**Feature**: 003-code-context-headers
**Date**: 2025-12-29
**Status**: Final

---

## 说明

本功能不涉及传统数据模型，主要涉及脚本运行时数据结构。

## 大模型分析数据结构

### ModuleAnalysisResult

大模型分析的模块级别结果：

```python
@dataclass
class ModuleAnalysisResult:
    module_path: str                    # 模块路径（如 "src/ginkgo/data"）
    module_name: str                    # 功能名称（如 "Data Layer"）
    description: str                    # 功能描述（2-3句话）
    level: int                          # 层级深度（0=顶层）
    parent: str | None                  # 父模块路径
    classes: List[ClassInfo]           # 类信息列表
    functions: List[FunctionInfo]      # 函数信息列表
    files: List[str]                     # 文件路径列表
    upstream: List[str]                  # 上游依赖（哪些模块会使用）
    downstream: List[str]                # 下游依赖（使用哪些模块）
    children: List[str]                  # 子模块路径列表
    analyzed_at: str                     # ISO 时间戳
    file_hashes: Dict[str, str]         # 文件 hash → 检测变化
```

### ClassInfo

类信息数据结构：

```python
@dataclass
class ClassInfo:
    name: str                           # 类名
    description: str                   # 功能描述
    base_classes: List[str]            # 基类列表
    methods: List[str]                  # 方法列表
```

### FunctionInfo

函数信息数据结构：

```python
@dataclass
class FunctionInfo:
    name: str                           # 函数名
    description: str                   # 功能描述
    parameters: List[str]              # 参数列表
```

## 缓存数据结构

### ProjectAnalysisCache

项目分析缓存（`.module_mapping.json`）：

```python
@dataclass
class ProjectAnalysisCache:
    version: str                       # 格式版本（如 "1.0"）
    analyzed_at: str                    # 分析时间
    root_path: str                      # 项目根路径
    modules: Dict[str, ModuleAnalysisResult]  # 模块路径 → 分析结果
```

**JSON Schema**:
```json
{
  "version": "1.0",
  "analyzed_at": "2025-12-29T00:00:00Z",
  "root_path": "/path/to/ginkgo",
  "modules": {
    "src/ginkgo/data": { /* ModuleAnalysisResult */ },
    "src/ginkgo/trading": { /* ModuleAnalysisResult */ }
  }
}
```

## 文件解析数据结构

### FileParseResult

文件解析结果（AST 分析）：

```python
@dataclass
class FileParseResult:
    path: str                          # 文件路径
    status: Literal["success", "failed"]  # 解析状态
    imports: List[str]                  # 导入的模块列表
    classes: List[str]                  # 定义的类名列表
    functions: List[str]                # 定义的函数名列表
    has_header: bool                    # 是否已有头部
    error_message: str | None = None    # 错误信息
```

## 头部模板数据结构

### HeaderTemplate

三行头部模板：

```python
@dataclass
class HeaderTemplate:
    upstream: str      # 上游依赖描述（如 "Trading Strategies, Portfolio Manager"）
    downstream: str    # 下游用途描述（如 "Data Models, Event System"）
    role: str         # 模块内作用描述（如 "定义 5 个数据模型类"）

    def render(self) -> str:
        """渲染为三行注释格式"""
        return f"""# Upstream: {self.upstream}
# Downstream: {self.downstream}
# Role: {self.role}
"""
```

---

## 结论

本功能的核心数据结构包括：
1. **ModuleAnalysisResult** - 大模型分析结果
2. **ProjectAnalysisCache** - 缓存结构
3. **FileParseResult** - AST 解析结果
4. **HeaderTemplate** - 头部生成模板
