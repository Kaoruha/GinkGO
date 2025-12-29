# Research: Code Context Headers for LLM Understanding

**Feature**: 003-code-context-headers
**Date**: 2025-12-29
**Status**: Complete (Updated with LLM Analysis)

---

## 研究目标

本研究文档确定实现代码上下文头部功能所需的关键技术决策和最佳实践，**重点在于使用大模型分析项目结构**。

---

## Decision 1: 大模型 API 选择

**决策**: 使用 **Anthropic Claude API** (Claude 3.5 Sonnet) 作为主要分析引擎，支持本地模型备选

**理由**:
- Claude 3.5 Sonnet 在代码理解和分析任务上表现优秀
- 支持长上下文（200K tokens），适合分析大型代码库
- API 稳定性好，速率限制合理
- 支持函数调用，便于结构化输出
- 提供开源模型选项（通过合作伙伴或本地部署）

**实现方案**:
```python
import os
from anthropic import Anthropic

# 从环境变量读取 API 密钥
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)

def analyze_module_with_llm(file_contents: dict[str, str], module_path: str) -> dict:
    """使用 Claude 分析模块"""
    prompt = f"""分析以下 Python 模块的功能和结构：

模块路径: {module_path}

文件列表:
{chr(10).join(f"- {name}: {content[:500]}..." for name, content in file_contents.items())}

请返回 JSON 格式的分析结果，包含：
1. module_name: 模块功能名称（简短）
2. description: 模块功能描述（2-3句话）
3. classes: 主要类列表及其功能
4. functions: 主要函数列表及其功能
5. upstream: 哪些模块会使用此模块
6. downstream: 此模块使用哪些模块
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}  # 结构化 JSON 输出
    )

    import json
    return json.loads(message.content[0].text)
```

**备选方案**:
- **OpenAI GPT-4**: 代码理解能力强，但成本较高
- **Ollama + CodeLlama**: 本地部署，无网络依赖，但准确度略低
- **vLLM + DeepSeek Coder**: 开源模型，成本可控

**成本优化**:
- 使用缓存避免重复分析
- 批处理减少 API 调用次数
- 对于小模块（< 5 个文件），可使用更便宜的模型（Claude Haiku）

---

## Decision 2: 迭代分析算法设计

**决策**: 使用 **广度优先遍历 + 层级聚合** 的迭代分析策略

**理由**:
- BFS 保证按层级顺序分析，符合项目组织逻辑
- 层级聚合减少 API 调用次数（同一层级的文件一起分析）
- 便于实现增量更新（只分析变化的目录）

**实现方案**:
```python
from pathlib import Path
from typing import Dict, List
import json

def analyze_project_structure(root_dir: Path) -> Dict[str, dict]:
    """迭代分析项目结构"""

    # 第一步：收集所有模块目录
    modules = discover_module_dirs(root_dir)
    # [
    #   "src/ginkgo/data": {"files": [...], "parent": None},
    #   "src/ginkgo/data/models": {"files": [...], "parent": "src/ginkgo/data"},
    #   "src/ginkgo/trading": {"files": [...], "parent": None},
    #   ...
    # ]

    # 第二步：按层级分组
    by_level = group_by_level(modules)
    # Level 0: src/ginkgo/data, src/ginkgo/trading, ...
    # Level 1: src/ginkgo/data/models, src/ginkgo/trading/strategies, ...

    # 第三步：逐层分析
    results = {}
    for level, modules in sorted(by_level.items()):
        for module_path in modules:
            # 读取模块下所有文件
            files = read_all_files(module_path)

            # 调用 LLM 分析
            analysis = analyze_module_with_llm(files, module_path)
            results[module_path] = analysis

            # 将子模块的分析结果传递给父模块（用于理解上下文）
            store_analysis_result(module_path, analysis)

    return results

def discover_module_dirs(root_dir: Path) -> Dict[str, dict]:
    """发现所有模块目录"""
    modules = {}
    for dirpath in root_dir.rglob("*/"):
        # 跳过特殊目录
        if any(skip in str(dirpath) for skip in ["venv", "__pycache__", ".git", ".tox"]):
            continue

        # 检查是否包含 Python 文件
        python_files = list(dirpath.glob("*.py"))
        if python_files:
            modules[str(dirpath)] = {
                "files": python_files,
                "parent": str(dirpath.parent) if dirpath.parent != root_dir else None
            }

    return modules
```

**性能优化**:
- 并行分析同一层级的模块（使用 ThreadPoolExecutor）
- 缓存已分析的结果（基于文件 hash）
- 增量分析：只分析修改过的目录

---

## Decision 3: 分析结果格式设计

**决策**: 使用 **分层 JSON 结构**，支持模块间的引用关系

**理由**:
- JSON 格式易于解析和缓存
- 分层结构反映项目层级关系
- 便于查询和更新

**JSON Schema**:
```json
{
  "version": "1.0",
  "analyzed_at": "2025-12-29T00:00:00Z",
  "root_path": "/path/to/ginkgo",
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
      "children": ["src/ginkgo/data/models", "src/ginkgo/data/sources"]
    },
    "src/ginkgo/data/models": {
      "module_name": "Data Models",
      "description": "定义数据模型类（MBar, MTick, MStockInfo）",
      "level": 1,
      "parent": "src/ginkgo/data",
      "classes": [
        {"name": "MBar", "description": "K线数据模型，继承 MClickBase"},
        {"name": "MTick", "description": "Tick数据模型，继承 MClickBase"}
      ],
      "functions": [],
      "files": ["bar.py", "tick.py"],
      "upstream": ["CRUD Operations", "Data Services"],
      "downstream": ["ClickHouse"],
      "children": []
    }
  }
}
```

**存储格式**:
```python
@dataclass
class ModuleAnalysisResult:
    module_path: str                    # 模块路径
    module_name: str                    # 功能名称（简短）
    description: str                    # 功能描述
    level: int                          # 层级深度
    parent: str | None                  # 父模块路径
    classes: List[ClassInfo]           # 类信息
    functions: List[FunctionInfo]      # 函数信息
    files: List[str]                     # 文件列表
    upstream: List[str]                  # 上游依赖
    downstream: List[str]                # 下游依赖
    children: List[str]                  # 子模块
    analyzed_at: str                     # 分析时间戳
    file_hashes: Dict[str, str]         # 文件 hash（用于检测变化）

@dataclass
class ClassInfo:
    name: str
    description: str
    base_classes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)

@dataclass
class FunctionInfo:
    name: str
    description: str
    parameters: List[str] = field(default_factory=list)
```

---

## Decision 4: API 调用优化策略

**决策**: 使用 **批处理 + 多级缓存 + 智能重试** 优化 API 调用

**理由**:
- 批处理减少网络开销
- 多级缓存避免重复调用
- 智能重试提高可靠性

**实现方案**:

**1. 批处理策略**:
```python
def analyze_modules_batch(module_paths: List[str], max_batch_size: int = 5) -> Dict[str, dict]:
    """批量分析模块"""
    results = {}

    for i in range(0, len(module_paths), max_batch_size):
        batch = module_paths[i:i+max_batch_size]

        # 构建批处理 prompt
        batch_prompt = build_batch_analysis_prompt(batch)

        # 单次 API 调用分析多个模块
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            messages=[{"role": "user", "content": batch_prompt}]
        )

        # 解析批量结果
        batch_results = parse_batch_response(response)
        results.update(batch_results)

    return results
```

**2. 多级缓存**:
```python
import hashlib
import json
from pathlib import Path

CACHE_FILE = Path(".module_mapping.json")

class ModuleAnalysisCache:
    def __init__(self, cache_file: Path = CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """加载缓存"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def get(self, module_path: str, file_hashes: Dict[str, str]) -> dict | None:
        """获取缓存（如果有效）"""
        if module_path not in self.cache:
            return None

        cached = self.cache[module_path]
        # 检查文件是否变化
        if cached.get("file_hashes") == file_hashes:
            return cached

        return None

    def set(self, module_path: str, analysis: dict):
        """设置缓存"""
        self.cache[module_path] = analysis
        self._save_cache()

    def _save_cache(self):
        """保存缓存"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
```

**3. 智能重试**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def analyze_with_retry(module_path: str, files: dict) -> dict:
    """带重试的分析调用"""
    try:
        return analyze_module_with_llm(files, module_path)
    except Exception as e:
        GLOG.error(f"分析失败: {module_path}, 错误: {e}")
        # 降级：使用基础 AST 分析
        return fallback_ast_analysis(module_path)
```

---

## Decision 5: 头部生成策略（基于 LLM 分析）

**决策**: 使用 **映射表 + AST 解析** 生成头部，LLM 分析结果作为数据源

**理由**:
- 映射表提供简短功能名称
- AST 解析提供类/函数列表
- 结合两者生成准确的三行头部

**实现方案**:
```python
def generate_header_from_analysis(
    file_path: Path,
    module_analysis: dict,
    ast_info: dict
) -> str:
    """基于 LLM 分析结果生成头部"""

    # 从模块分析中获取功能信息
    module_path_str = str(file_path.parent)

    # 查找匹配的模块分析
    module_info = find_best_matching_module(module_path_str, module_analysis)

    if module_info:
        # Upstream: 从分析结果获取
        upstream = module_info.get("upstream", ["Various Modules"])
        upstream_str = ", ".join(upstream[:3])  # 最多显示3个

        # Downstream: 从分析结果获取
        downstream = module_info.get("downstream", ["Standard Library"])
        downstream_str = ", ".join(downstream[:3])

        # Role: 结合文件类型和分析结果
        role = generate_role_description(file_path, ast_info, module_info)
    else:
        # 降级：使用基础推断
        upstream_str = infer_upstream_from_imports(ast_info["imports"])
        downstream_str = "Standard Library"
        role = infer_role_from_filetype(file_path, ast_info)

    return f"""# Upstream: {upstream_str}
# Downstream: {downstream_str}
# Role: {role}
"""

def find_best_matching_module(
    file_path: str,
    module_analysis: dict
) -> dict | None:
    """查找最匹配的模块分析结果"""
    # 精确匹配
    if file_path in module_analysis:
        return module_analysis[file_path]

    # 父模块匹配
    for module_path, info in module_analysis.items():
        if file_path.startswith(module_path):
            return info

    return None
```

---

## Decision 6: CI/CD 集成方案

**决策**: 使用 **GitHub Actions + 触发式更新**，仅在代码变更时运行分析

**理由**:
- 仅在相关代码变更时运行，节省资源
- PR 检查点可以自动验证头部注释
- 定时任务作为补充（每周全面检查）

**GitHub Actions Workflow**:
```yaml
name: Update Code Context Headers

on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]
  workflow_dispatch:  # 手动触发

jobs:
  analyze-and-update:
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
          python scripts/generate_headers.py \
            --analysis .module_mapping.json \
            --commit

      - name: Verify headers
        run: |
          python scripts/verify_headers.py

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add -A
          git diff --quiet && git diff --staged --quiet || git commit -m "chore: update code context headers [skip ci]"

      - name: Push changes
        if: github.event_name == 'push'
        run: git push
```

---

## 性能基准与成本估算

**性能目标**:
- 首次完整分析: ~5-10 分钟（~1000 文件，~50-100 模块）
- 增量分析: ~30-60 秒（仅分析变更的模块）
- 头部生成: ~2-3 分钟（使用缓存）

**成本估算**（Claude 3.5 Sonnet）:
- 输入: ~500 tokens/文件 × 1000 文件 = 500K tokens
- 输出: ~1000 tokens/模块 × 100 模块 = 100K tokens
- 总计: ~600K tokens ≈ $1-2 USD/次

**优化后的成本**:
- 使用缓存：仅分析变更文件，成本降低 90%+
- 批处理：减少 API 调用次数，节省 20-30%
- Haiku 用于小模块：节省 50-70% 成本

---

## 依赖项清单

**Python 包**:
- `anthropic` - Anthropic API 客户端
- `tenacity` - 重试机制
- `pathlib` - 文件操作（标准库）
- `ast` - AST 解析（标准库）
- `json` - JSON 处理（标准库）
- `hashlib` - 文件 hash（标准库）

**外部服务**:
- Anthropic Claude API（或兼容的本地模型）

---

## 测试策略

**单元测试**:
- LLM 分析功能测试（mock API 响应）
- 缓存功能测试
- 头部生成逻辑测试

**集成测试**:
- 完整分析流程测试（使用小型测试项目）
- 头部生成验证测试

**性能测试**:
- 大型项目分析性能测试
- API 调用次数验证

---

## 未解决事项

以下问题在实现阶段需要处理：

1. **大模型 API 降级策略**: API 失败时如何处理？回退到 AST 分析？
2. **分析结果版本管理**: 如何处理团队成员的分析结果冲突？
3. **Token 使用监控**: 如何避免意外超支？

---

**Research Status**: ✅ **COMPLETE** - 包含大模型分析的完整技术方案
