# Implementation Plan: Code Context Headers for LLM Understanding

**Branch**: `003-code-context-headers` | **Date**: 2025-12-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-code-context-headers/spec.md`

## Summary

为 Ginkgo 量化交易库的所有 Python 文件添加标准化的三行上下文头部注释。核心创新点是**使用大模型分析项目结构**，自动生成准确的模块功能映射，然后基于分析结果生成头部注释。

头部格式：
- 第1行: `# Upstream: <简短功能名称列表>` - 上游依赖
- 第2行: `# Downstream: <简短功能名称列表>` - 下游用途
- 第3行: `# Role: <模块内作用>` - 模块职责

技术方法：
1. **大模型分析项目结构**（迭代分析，读取完整源代码）
2. **基于分析结果生成三行头部**（自动集成到生成脚本）
3. **CI/CD 集成**（代码提交时自动更新分析）

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**:
- 标准库: ast, pathlib, re, typing, json
- 大模型 API: OpenAI API / Anthropic API / 开源模型（通过 API 调用）
- 文件操作: pathlib

**Storage**:
- 分析结果缓存: `.module_mapping.json` (本地文件)
- 无需数据库操作

**Testing**: pytest with unit/integration 标记分类

**Target Platform**: Linux/macOS/Windows (跨平台脚本)

**Project Type**: single (Python量化交易库)

**Performance Goals**:
- 大模型分析: ~5-10 分钟（首次，~1000 文件）
- 头部生成: ~2-3 分钟（使用缓存的分析结果）
- 低内存占用: <200MB

**Constraints**:
- 大模型 API 调用需要网络连接或本地模型
- API 调用成本需要控制（使用缓存）
- 分析结果需要人工审核机制

**Scale/Scope**:
- 约 500-1000 个 Python 文件需要添加头部
- 大模型需要分析 ~50-100 个模块目录

**关键技术决策**:
- **使用大模型分析项目结构**：迭代分析每个子目录，读取完整源代码
- **输出完整分析报告**：包含模块路径、功能名称、所有类、函数、依赖关系
- **集成到生成脚本**：每次生成头部时自动运行分析（有缓存）
- **CI/CD 集成**：每次代码提交时自动更新模块分析

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查 - 仅添加注释，无敏感信息
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理 - 大模型 API 密钥需要环境变量
- [x] 敏感配置文件已添加到.gitignore - 分析结果缓存文件需要添加

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 - 本功能为文档增强，不涉及架构变更
- [x] 使用ServiceHub统一访问服务 - 本功能不涉及服务访问
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责 - 头部注释明确模块层级

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`cache_with_expiration装饰器 - 脚本代码需要遵循
- [x] 提供类型注解，支持静态类型检查 - 脚本代码需要遵循
- [x] 禁止使用hasattr等反射机制回避类型错误 - 脚本代码需要遵循
- [x] 遵循既定命名约定 - 不涉及

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能 - 需要为大模型分析脚本编写测试
- [x] 测试按unit、integration标记分类 - 脚本测试分类
- [x] 数据库测试使用测试数据库，不涉及 - 不涉及数据库

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法 - 文件操作使用批处理
- [x] 合理使用多级缓存 - 分析结果缓存、API 调用缓存
- [x] 使用懒加载机制优化启动时间 - 脚本按需导入

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务 - 本功能本身不涉及
- [x] 已完成任务立即从活跃列表移除 - 不涉及
- [x] 任务优先级明确，高优先级任务优先显示 - 不涉及
- [x] 任务状态实时更新，确保团队协作效率 - 不涉及

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文 - 头部注释和分析报告使用中文
- [x] 核心API提供详细使用示例和参数说明 - 脚本需要提供使用示例
- [x] 重要组件有清晰的架构说明和设计理念文档 - 本功能即为文档增强

**Constitution Check Result**: ✅ **PASSED** - 所有检查项通过

**新增注意事项**:
- 大模型 API 密钥必须使用环境变量管理（不硬编码）
- 分析结果缓存文件 `.module_mapping.json` 需要添加到 .gitignore
- 需要提供 API 调用失败的重试和降级机制

## Project Structure

### Documentation (this feature)

```text
.specify/specs/003-code-context-headers/
├── plan.md              # This file
├── research.md          # Phase 0: 技术研究（包含大模型分析方案）
├── data-model.md        # Phase 1: 脚本数据结构
├── quickstart.md        # Phase 1: 快速开始指南
├── contracts/           # Phase 1: 脚本接口说明
└── tasks.md             # Phase 2: 任务分解（由 /speckit.tasks 生成）
```

### Source Code (repository root)

```text
# 新增脚本文件
scripts/
├── analyze_project.py         # 大模型分析脚本（新增）
├── check_headers.py           # 检查缺失头部的文件
├── generate_headers.py        # 生成头部（集成分析）
└── verify_headers.py          # 验证头部准确性

# 缓存文件
.module_mapping.json            # 大模型分析结果缓存（.gitignore）

# CI/CD 配置
.github/workflows/
└── update-headers.yml          # 自动更新头部的 workflow

# 修改的文件
src/ginkgo/                     # 所有 .py 文件添加三行头部
tests/                          # 所有 .py 文件添加三行头部
```

**Structure Decision**: 本功能为代码库文档增强，新增四个自动化脚本（包括大模型分析），修改现有 Python 文件添加头部注释。

## Complexity Tracking

| 复杂度来源 | 说明 | 简化方案被拒绝的原因 |
|-----------|------|---------------------|
| 大模型 API 依赖 | 需要外部 API 调用，网络连接 | 手动维护映射表无法适应项目变化，维护成本过高 |
| 完整源代码读取 | 需要读取所有文件内容，API 成本 | 仅读取 AST 无法理解代码逻辑和业务语义 |
| CI/CD 集成 | 需要在 CI 中运行分析 | 保持分析结果与代码同步，确保头部注释准确性 |

## Phase 0: Research & Technical Decisions

### 研究主题

1. **大模型 API 选择**
   - OpenAI GPT-4 / Claude 3.5 / 开源模型
   - API 成本和性能权衡
   - 离线/本地模型选项（Ollama, vLLM）

2. **项目结构分析策略**
   - 迭代分析算法设计
   - 如何识别模块边界
   - 如何提取模块功能描述

3. **分析结果格式设计**
   - JSON schema 定义
   - 模块关系表示方法
   - 类/函数/依赖关系的存储格式

4. **API 调用优化**
   - 如何减少 API 调用次数（批处理、缓存）
   - Token 使用优化策略
   - 失败重试和降级机制

5. **CI/CD 集成方案**
   - GitHub Actions workflow 设计
   - 定时任务 vs 触发式任务
   - 分析结果版本管理

**输出**: research.md - 包含所有技术决策和最佳实践

## Phase 1: Design Artifacts

### data-model.md
脚本数据结构定义：
- `ModuleAnalysisResult` - 模块分析结果
- `FileAnalysisResult` - 文件分析结果
- `ModuleMapping` - 模块映射缓存

### contracts/README.md
脚本接口规范：
- `analyze_project.py` CLI 参数
- `generate_headers.py` 集成接口
- JSON 输出格式

### quickstart.md
完整使用指南：
- 如何运行大模型分析
- 如何生成头部注释
- CI/CD 配置示例

**输出**: data-model.md, contracts/README.md, quickstart.md

### Agent Context Update

运行 `.specify/scripts/bash/update-agent-context.sh claude` 更新 agent 上下文。

---

**Plan Status**: ✅ **COMPLETE** - 计划已更新，包含大模型分析需求
