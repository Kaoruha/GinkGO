# Ginkgo Strategy Evaluation Module

## 概述

策略评估模块提供静态分析和运行时验证功能，帮助策略开发者在回测前发现代码问题。

## 核心功能

### 1. 结构评估 (P1)
- 继承关系检查（BaseStrategy）
- 方法签名验证（cal() 方法）
- 必需方法实现检查
- 初始化参数验证

### 2. 逻辑评估 (P2)
- Signal 字段完整性验证
- TimeProvider 使用检查
- 参数使用验证
- 禁止操作检测

### 3. 最佳实践评估 (P3)
- 装饰器使用检查（@time_logger, @retry）
- 异常处理验证
- 日志记录检查
- 参数验证完整性

### 4. 信号追踪 (P2)
- 运行时信号生成捕获
- 上下文信息记录
- 支持多种数据源（K线、Tick）

### 5. 信号可视化 (P2)
- 价格图表 + 信号标注
- 支持多种输出格式（PNG, SVG, HTML）
- Matplotlib 和 Plotly 渲染器

## CLI 使用

```bash
# 基本评估
ginkgo eval strategy my_strategy.py

# 标准评估
ginkgo eval strategy my_strategy.py --level standard

# 信号追踪
ginkgo eval strategy my_strategy.py --data test.csv --show-trace

# 可视化
ginkgo eval strategy my_strategy.py --data test.csv --visualize --output chart.png
```

## 架构设计

```
evaluation/
├── core/           # 核心实体（枚举、结果）
├── rules/          # 评估规则
├── evaluators/     # 评估器
├── analyzers/      # 静态/运行时分析器
├── utils/          # 工具函数
├── visualization/  # 可视化组件
├── reporting/      # 报告生成
├── pipeline/       # 评估流水线
└── config/         # 配置管理
```

## 开发状态

- [ ] Phase 1: Setup
- [ ] Phase 2: Foundational
- [ ] Phase 3: User Story 1 - 结构评估
- [ ] Phase 4: User Story 2 - 逻辑评估
- [ ] Phase 5: User Story 4 - 信号追踪
- [ ] Phase 6: User Story 3 - 最佳实践
- [ ] Phase 7: User Story 5 - 数据库策略
- [ ] Phase 8: User Story 6 - 架构扩展性

## 文档

- [Feature Specification](../../.specify/specs/002-strategy-validation/spec.md)
- [Implementation Plan](../../.specify/specs/002-strategy-validation/plan.md)
- [Task List](../../.specify/specs/002-strategy-validation/tasks.md)
