# Implementation Tasks: Code Context Headers for LLM Understanding

**Feature**: 003-code-context-headers
**Branch**: `003-code-context-headers`
**Date**: 2025-12-29
**Status**: Ready for Implementation

---

## Overview

本功能为 Ginkgo 量化交易库的所有 Python 文件添加标准化的三行上下文头部注释。核心创新点是**使用大模型分析项目结构**，自动生成准确的模块功能映射，然后基于分析结果生成头部注释。

**目标**:
- 100% 的核心 Python 文件都有上下文头部
- 使用大模型自动分析项目结构，生成模块功能映射
- 提供自动化工具检查、生成、验证头部注释
- CI/CD 集成，自动更新分析结果

**头部格式**:
```python
# Upstream: <简短功能名称列表>      # 哪些模块会使用本文件
# Downstream: <简短功能名称列表>    # 本文件使用哪些模块
# Role: <模块内作用>                # 在模块中的职责
```

---

## User Story Mapping

| User Story | Priority | Description | Independent Test |
|------------|----------|-------------|------------------|
| US1 | P1 | 核心代码文件上下文头部 | 随机选择 10 个核心文件，验证每个文件都有完整的上下文头部 |
| US2 | P2 | 测试文件上下文头部 | 随机选择 10 个测试文件，验证每个文件都有完整的测试上下文头部 |
| US3 | P3 | 配置和文档文件上下文说明 | 检查所有配置文件，验证关键配置项都有注释说明 |

---

## Dependency Graph

```
Phase 1: Setup (基础脚本框架)
    ↓
Phase 2: Foundational (大模型分析 + AST 解析)
    ↓
Phase 3: US1 - 核心代码文件头部 (核心功能)
    ↓
Phase 4: US2 - 测试文件头部 (测试支持)
    ↓
Phase 5: US3 - 配置文件头部 (文档增强)
    ↓
Phase 6: Polish & CI/CD (自动化集成)
```

**Parallel Opportunities**:
- Phase 2 中，AST 解析工具和大模型分析脚本可以并行开发 [P]
- Phase 3、4、5 中，不同目录的处理可以并行执行 [P]

---

## MVP Scope (Minimum Viable Product)

**建议 MVP**: 仅实现 Phase 1-3 (Setup + Foundational + US1)

**MVP 验收标准**:
- ✅ 核心脚本框架可用
- ✅ 大模型分析功能可用
- ✅ 核心代码文件（src/ginkgo/）100% 有头部注释
- ✅ 头部准确性 > 95%

**MVP 后续扩展**:
- Phase 4: 测试文件头部
- Phase 5: 配置文件头部
- Phase 6: CI/CD 集成

---

## Task List

### Phase 1: Setup (项目初始化)

**目标**: 创建项目基础结构，配置开发环境

- [X] T001 创建 scripts/ 目录结构
- [X] T002 [P] 创建 .gitignore 添加 .module_mapping.json 和相关缓存文件
- [X] T003 [P] 创建脚本依赖配置文件（requirements.txt 或添加到 pyproject.toml）

**验收标准**: 目录结构完整，依赖配置就绪

---

### Phase 2: Foundational (基础功能)

**目标**: 实现大模型分析和 AST 解析的核心功能

#### 2.1 数据结构定义

- [X] T004 [P] 在 scripts/shared/data_models.py 定义 ModuleAnalysisResult 数据类
- [X] T005 [P] 在 scripts/shared/data_models.py 定义 ClassInfo 数据类
- [X] T006 [P] 在 scripts/shared/data_models.py 定义 FunctionInfo 数据类
- [X] T007 [P] 在 scripts/shared/data_models.py 定义 FileParseResult 数据类
- [X] T008 [P] 在 scripts/shared/data_models.py 定义 HeaderTemplate 数据类

#### 2.2 AST 解析工具

- [X] T009 [P] 创建 scripts/shared/ast_parser.py 实现 parse_file_for_header() 函数
- [X] T010 [P] 在 scripts/shared/ast_parser.py 实现 extract_imports() 函数
- [X] T011 [P] 在 scripts/shared/ast_parser.py 实现 extract_classes() 函数
- [X] T012 [P] 在 scripts/shared/ast_parser.py 实现 extract_functions() 函数
- [X] T013 [P] 在 scripts/shared/ast_parser.py 实现 has_existing_header() 函数

#### 2.3 大模型分析脚本

- [X] T014 创建 scripts/analyze_project.py 主入口，使用 argparse 解析命令行参数
- [X] T015 在 scripts/analyze_project.py 实现 discover_module_dirs() 发现所有模块目录
- [X] T016 在 scripts/analyze_project.py 实现 group_by_level() 按层级分组模块
- [X] T017 在 scripts/analyze_project.py 实现 calculate_file_hashes() 计算文件哈希
- [X] T018 在 scripts/analyze_project.py 实现 ModuleAnalysisCache 缓存管理类
- [X] T019 在 scripts/analyze_project.py 实现 analyze_module_with_llm() 调用大模型分析
- [X] T020 在 scripts/analyze_project.py 实现 analyze_modules_batch() 批量分析优化
- [X] T021 在 scripts/analyze_project.py 实现 analyze_project_structure() 主分析流程
- [X] T022 在 scripts/analyze_project.py 添加 @retry 装饰器处理 API 失败重试
- [X] T023 在 scripts/analyze_project.py 实现 fallback_ast_analysis() 降级策略

#### 2.4 头部生成脚本

- [X] T024 创建 scripts/generate_headers.py 主入口，使用 argparse 解析命令行参数
- [X] T025 在 scripts/generate_headers.py 实现 load_module_analysis() 加载分析结果
- [X] T026 在 scripts/generate_headers.py 实现 find_best_matching_module() 查找匹配模块
- [X] T027 在 scripts/generate_headers.py 实现 generate_header_from_analysis() 生成头部
- [X] T028 在 scripts/generate_headers.py 实现 generate_role_description() 生成 Role 描述
- [X] T029 在 scripts/generate_headers.py 实现 infer_upstream_from_imports() 降级推断
- [X] T030 在 scripts/generate_headers.py 实现 infer_role_from_filetype() 文件类型推断
- [X] T031 在 scripts/generate_headers.py 实现 add_header_to_file() 添加头部到文件
- [X] T032 在 scripts/generate_headers.py 实现 process_directory() 批量处理目录

#### 2.5 检查和验证脚本

- [X] T033 [P] 创建 scripts/check_headers.py 检查缺失头部的文件
- [X] T034 [P] 在 scripts/check_headers.py 实现 check_file_has_header() 检查单个文件
- [X] T035 [P] 在 scripts/check_headers.py 实现 scan_directory() 扫描目录
- [X] T036 [P] 在 scripts/check_headers.py 实现 print_report() 输出报告
- [X] T037 [P] 创建 scripts/verify_headers.py 验证头部准确性
- [X] T038 [P] 在 scripts/verify_headers.py 实现 verify_header_accuracy() 验证准确性
- [X] T039 [P] 在 scripts/verify_headers.py 实现 check_class_exists() 检查类是否存在
- [X] T040 [P] 在 scripts/verify_headers.py 实现 auto_fix_issues() 自动修复

**验收标准**:
- ✅ 大模型分析脚本可以分析项目结构并生成 .module_mapping.json
- ✅ AST 解析工具可以正确提取文件中的类、函数、导入信息
- ✅ 生成脚本可以基于分析结果生成三行头部注释
- ✅ 检查和验证脚本可以检测缺失和验证准确性

---

### Phase 3: US1 - 核心代码文件上下文头部 (P1)

**目标**: 为所有核心 Python 源代码文件（src/ginkgo/）添加上下文头部

**独立测试标准**: 随机选择 10 个核心文件，验证每个文件都有完整的上下文头部，头部内容准确反映文件的实际内容

#### 3.1 运行大模型分析

- [X] T041 [US1] 设置 ANTHROPIC_API_KEY 环境变量
- [X] T042 [US1] 运行 `python scripts/analyze_project.py --root src/ginkgo --output .module_mapping.json --cache`
- [X] T043 [US1] 验证 .module_mapping.json 文件生成成功，包含完整分析结果
- [X] T044 [US1] 检查分析结果覆盖所有 src/ginkgo/ 下的模块

#### 3.2 检查缺失头部

- [X] T045 [US1] 运行 `python scripts/check_headers.py --directory src/ginkgo`
- [X] T046 [US1] 记录缺失头部的文件列表
- [X] T047 [US1] 生成缺失头部报告（JSON 格式）

#### 3.3 生成头部预览

- [X] T048 [US1] 运行 `python scripts/generate_headers.py --directory src/ginkgo --dry-run`
- [X] T049 [US1] 检查生成的头部预览是否符合预期
- [X] T050 [US1] 人工审核生成的头部质量（抽样 10 个文件）

#### 3.4 应用头部到文件

- [X] T051 [US1] 运行 `python scripts/generate_headers.py --directory src/ginkgo`
- [X] T052 [US1] 验证所有文件头部添加成功
- [X] T053 [US1] 运行 `python scripts/check_headers.py --directory src/ginkgo` 确认 100% 覆盖

#### 3.5 验证头部准确性

- [X] T054 [US1] 运行 `python scripts/verify_headers.py --directory src/ginkgo`
- [X] T055 [US1] 检查验证报告，确保准确性 > 95%
- [X] T056 [US1] 人工审核需要检查的文件（如有）
- [X] T057 [US1] 使用 `--fix` 选项自动修复可修复的问题

#### 3.6 验收测试

- [X] T058 [US1] 随机选择 10 个核心文件
- [X] T059 [US1] 验证每个文件都有完整的三行头部
- [X] T060 [US1] 验证头部内容准确反映文件的实际内容
- [X] T061 [US1] 验证头部格式符合规范（# Upstream, # Downstream, # Role）

**验收标准**:
- ✅ 100% 的核心 Python 文件都有上下文头部
- ✅ 95% 以上的头部信息准确反映文件实际内容
- ✅ 头部格式一致，符合三行标准

---

### Phase 4: US2 - 测试文件上下文头部 (P2)

**目标**: 为所有测试文件（tests/）添加上下文头部

**独立测试标准**: 随机选择 10 个测试文件，验证每个文件都有完整的测试上下文头部

#### 4.1 测试文件特殊处理

- [ ] T062 [P] [US2] 在 scripts/shared/ast_parser.py 添加 extract_pytest_marks() 函数
- [ ] T063 [P] [US2] 在 scripts/shared/ast_parser.py 实现 detect_test_type() 检测测试类型
- [ ] T064 [P] [US2] 在 scripts/generate_headers.py 实现 generate_test_header() 生成测试头部
- [ ] T065 [P] [US2] 更新 generate_role_description() 支持测试文件

#### 4.2 生成测试文件头部

- [ ] T066 [US2] 运行 `python scripts/generate_headers.py --directory tests --dry-run`
- [ ] T067 [US2] 检查生成的测试头部是否包含测试类型标记
- [ ] T068 [US2] 检查生成的测试头部是否包含被测试的模块路径
- [ ] T069 [US2] 人工审核测试头部质量（抽样 5 个文件）

#### 4.3 应用测试文件头部

- [ ] T070 [US2] 运行 `python scripts/generate_headers.py --directory tests`
- [ ] T071 [US2] 验证所有测试文件头部添加成功
- [ ] T072 [US2] 运行 `python scripts/check_headers.py --directory tests` 确认 100% 覆盖

#### 4.4 验证测试文件头部

- [ ] T073 [US2] 运行 `python scripts/verify_headers.py --directory tests`
- [ ] T074 [US2] 检查测试头部是否包含测试类型（unit/integration/database）
- [ ] T075 [US2] 检查测试头部是否包含被测试模块路径

#### 4.5 验收测试

- [ ] T076 [US2] 随机选择 10 个测试文件
- [ ] T077 [US2] 验证每个文件都有完整的测试上下文头部
- [ ] T078 [US2] 验证测试头部包含测试类型标记
- [ ] T079 [US2] 验证测试头部包含被测试的源代码模块路径

**验收标准**:
- ✅ 100% 的测试文件都有测试上下文头部
- ✅ 测试头部包含测试类型标记（unit/integration/database）
- ✅ 测试头部包含被测试的源代码模块路径

---

### Phase 5: US3 - 配置和文档文件上下文说明 (P3)

**目标**: 为配置文件（pyproject.toml, setup.py）和关键文档添加上下文说明

**独立测试标准**: 检查所有配置文件，验证关键配置项都有注释说明

#### 5.1 配置文件分析

- [ ] T080 [P] [US3] 创建 scripts/shared/config_parser.py 解析配置文件
- [ ] T081 [P] [US3] 在 scripts/shared/config_parser.py 实现 parse_pyproject_toml() 解析 pyproject.toml
- [ ] T082 [P] [US3] 在 scripts/shared/config_parser.py 实现 extract_key_sections() 提取关键配置段

#### 5.2 配置文件注释生成

- [ ] T083 [US3] 为 pyproject.toml 添加关键配置项注释
- [ ] T084 [US3] 为 setup.py 添加注释说明
- [ ] T085 [US3] 为 .yaml 配置文件添加块注释说明
- [ ] T086 [US3] 为 README.md 顶部添加项目概述元数据

#### 5.3 验证配置文件注释

- [ ] T087 [US3] 运行检查脚本验证配置文件注释
- [ ] T088 [US3] 检查关键配置项都有注释说明
- [ ] T089 [US3] 验证注释内容准确反映配置项用途

#### 5.4 验收测试

- [ ] T090 [US3] 检查 pyproject.toml 关键配置项注释覆盖率 > 90%
- [ ] T091 [US3] 检查 setup.py 有完整注释说明
- [ ] T092 [US3] 验证 .yaml 配置文件有块注释说明

**验收标准**:
- ✅ 90% 以上的配置文件关键配置项有注释说明
- ✅ README.md 有项目概述元数据
- ✅ 注释内容准确反映配置项用途

---

### Phase 6: Polish & CI/CD (自动化集成)

**目标**: 完善 CI/CD 集成，自动化头部更新流程

#### 6.1 GitHub Actions 配置

- [ ] T093 [P] 创建 .github/workflows/update-headers.yml workflow 文件
- [ ] T094 [P] 在 workflow 中配置 Python 3.12 环境
- [ ] T095 [P] 在 workflow 中添加依赖安装步骤（anthropic, tenacity）
- [ ] T096 [P] 在 workflow 中添加大模型分析步骤
- [ ] T097 [P] 在 workflow 中添加头部生成步骤
- [ ] T098 [P] 在 workflow 中添加头部验证步骤
- [ ] T099 [P] 在 workflow 中添加自动提交步骤（[skip ci]）

#### 6.2 性能优化

- [ ] T100 [P] 在 scripts/analyze_project.py 实现批处理优化（--batch-size 参数）
- [ ] T101 [P] 在 scripts/analyze_project.py 实现并发分析优化（--max-workers 参数）
- [ ] T102 [P] 在 scripts/generate_headers.py 实现并发文件处理（--max-workers 参数）

#### 6.3 错误处理和日志

- [ ] T103 [P] 在所有脚本中添加统一的错误处理（try-except）
- [ ] T104 [P] 在所有脚本中添加进度输出（rich 进度条）
- [ ] T105 [P] 在所有脚本中添加详细日志（--verbose 选项）

#### 6.4 文档完善

- [ ] T106 [P] 更新 README.md 添加头部功能说明
- [ ] T107 [P] 创建 scripts/README.md 说明各脚本用途
- [ ] T108 [P] 在 scripts/ 目录添加示例用法

#### 6.5 最终验证

- [ ] T109 运行完整流程测试：分析 → 生成 → 验证
- [ ] T110 测试 CI/CD workflow（手动触发）
- [ ] T111 验证所有脚本 --help 输出完整
- [ ] T112 运行性能测试，确保符合预期指标

**验收标准**:
- ✅ CI/CD workflow 配置完成
- ✅ 所有脚本有完善的错误处理和日志
- ✅ 文档完整，包含使用示例
- ✅ 性能符合预期目标

---

## Implementation Strategy

### MVP First (推荐)

**第一阶段**: MVP (Phase 1-3)
- T001-T040: Setup + Foundational
- T041-T061: US1 - 核心代码文件头部

**验收标准**:
- ✅ 核心脚本可用
- ✅ 大模型分析功能可用
- ✅ 核心代码文件 100% 有头部

**后续扩展**:
- Phase 4: 测试文件头部
- Phase 5: 配置文件头部
- Phase 6: CI/CD 集成

---

### Incremental Delivery (增量交付)

**增量 1** (Week 1): Phase 1-2
- 完成基础脚本框架
- 实现大模型分析和 AST 解析

**增量 2** (Week 2): Phase 3
- 为核心代码文件添加头部
- 验证 MVP 功能完整

**增量 3** (Week 3): Phase 4-5
- 扩展到测试和配置文件

**增量 4** (Week 4): Phase 6
- CI/CD 集成
- 性能优化和文档完善

---

## Parallel Execution Examples

### Phase 2 并行执行

```bash
# 终端 1: AST 解析工具
python scripts/shared/ast_parser.py  # T009-T013

# 终端 2: 数据结构定义
python scripts/shared/data_models.py  # T004-T008
```

### Phase 3 并行执行（不同目录）

```bash
# 并行处理不同目录
python scripts/generate_headers.py --directory src/ginkgo/data &
python scripts/generate_headers.py --directory src/ginkgo/trading &
python scripts/generate_headers.py --directory src/ginkgo/client &
wait
```

---

## Validation Checkpoints

| Phase | 检查点 | 验收标准 |
|-------|--------|----------|
| Phase 1 | 目录结构和依赖 | scripts/ 目录存在，依赖配置完成 |
| Phase 2 | 基础功能 | 大模型分析脚本可运行，AST 解析正确 |
| Phase 3 | US1 完成 | 核心文件 100% 有头部，准确性 > 95% |
| Phase 4 | US2 完成 | 测试文件 100% 有头部，包含测试类型 |
| Phase 5 | US3 完成 | 配置文件 90% 有注释说明 |
| Phase 6 | CI/CD | workflow 配置完成，自动运行成功 |

---

## Success Metrics

| 指标 | 目标 | 测量方法 |
|------|------|----------|
| 核心文件覆盖率 | 100% | `check_headers.py --directory src/ginkgo` |
| 头部准确性 | > 95% | `verify_headers.py --directory src/ginkgo` |
| 分析性能 | < 10 分钟 | 首次运行 `analyze_project.py` |
| 增量分析性能 | < 60 秒 | 带缓存的 `analyze_project.py --cache` |
| 头部生成性能 | < 5 分钟 | `generate_headers.py --directory src/ginkgo` |

---

## Notes

1. **API 密钥管理**:
   - 必须使用环境变量 `ANTHROPIC_API_KEY`
   - 不得硬编码在脚本中

2. **缓存管理**:
   - `.module_mapping.json` 需要添加到 .gitignore
   - 缓存基于文件 hash，自动检测变更

3. **降级策略**:
   - API 失败时回退到 AST 分析
   - 确保即使没有 API 也能生成基础头部

4. **成本控制**:
   - 使用缓存避免重复分析
   - 批处理减少 API 调用次数
   - 首次分析成本约 $1-2 USD

---

**Tasks Status**: ✅ **READY** - 共 112 个任务，按用户故事组织，可独立实施
