# Upstream: CLI评估命令
# Downstream: pipeline.stages (空包，暂无导出)
# Role: 评估流水线子包，预留EvaluationPipeline多阶段评估编排(静态分析/运行时检查/信号追踪)






"""
Pipeline components for evaluation workflow orchestration.

This package contains pipeline implementation:
- EvaluationPipeline: Main pipeline class
- stages: StaticAnalysisStage, RuntimeInspectionStage, SignalTracingStage
- execution_strategy: Serial and parallel execution strategies
"""

__all__ = []

