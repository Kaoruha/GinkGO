"""
演示 trace_id 在日志输出中的集成

展示如何使用 trace_id 进行跨容器请求追踪：
1. 设置 trace_id
2. 使用上下文管理器临时设置 trace_id
3. 验证 trace_id 出现在日志输出中
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from ginkgo.libs.core.logger import GinkgoLogger
import json


def demo_basic_trace_id():
    """演示基本的 trace_id 设置和获取"""
    print("=" * 60)
    print("演示 1: 基本 trace_id 设置和获取")
    print("=" * 60)

    logger = GinkgoLogger("demo", console_log=False)

    # 设置 trace_id
    token = logger.set_trace_id("trace-123-abc")
    print(f"设置 trace_id: trace-123-abc")
    print(f"获取 trace_id: {logger.get_trace_id()}")

    # 清除 trace_id
    logger.clear_trace_id(token)
    print(f"清除后 trace_id: {logger.get_trace_id()}")
    print()


def demo_context_manager():
    """演示上下文管理器使用"""
    print("=" * 60)
    print("演示 2: 上下文管理器临时设置 trace_id")
    print("=" * 60)

    logger = GinkgoLogger("demo", console_log=False)

    # 设置原始 trace_id
    logger.set_trace_id("trace-original")
    print(f"原始 trace_id: {logger.get_trace_id()}")

    # 使用上下文管理器临时设置
    with logger.with_trace_id("trace-temporary"):
        print(f"上下文内 trace_id: {logger.get_trace_id()}")
        # 这里记录的日志会包含 trace-temporary

    print(f"上下文外 trace_id: {logger.get_trace_id()}")
    print()


def demo_ecs_integration():
    """演示 trace_id 在 ECS 日志中的集成"""
    print("=" * 60)
    print("演示 3: trace_id 在 ECS 日志输出中的集成")
    print("=" * 60)

    from ginkgo.libs.core.logger import ecs_processor

    # 模拟日志事件
    event_dict = {
        "timestamp": "2024-01-01T12:00:00Z",
        "level": "info",
        "logger_name": "demo_logger",
        "event": "Processing trade order"
    }

    # 没有 trace_id 的情况
    result_without = ecs_processor(None, None, event_dict.copy())
    print("没有 trace_id 的日志:")
    print(json.dumps(result_without, indent=2))

    # 有 trace_id 的情况
    logger = GinkgoLogger("demo", console_log=False)
    logger.set_trace_id("trace-xyz-789")

    result_with = ecs_processor(None, None, event_dict.copy())
    print("\n有 trace_id 的日志:")
    print(json.dumps(result_with, indent=2))

    # 清理
    logger.clear_trace_id(logger.set_trace_id("dummy"))
    print()


def demo_nested_context():
    """演示嵌套上下文"""
    print("=" * 60)
    print("演示 4: 嵌套上下文管理")
    print("=" * 60)

    logger = GinkgoLogger("demo", console_log=False)

    # 外层上下文
    logger.set_trace_id("trace-outer")
    print(f"外层 trace_id: {logger.get_trace_id()}")

    # 内层上下文
    with logger.with_trace_id("trace-inner"):
        print(f"内层 trace_id: {logger.get_trace_id()}")

        # 更深层
        with logger.with_trace_id("trace-deep"):
            print(f"深层 trace_id: {logger.get_trace_id()}")

        print(f"回到内层 trace_id: {logger.get_trace_id()}")

    print(f"回到外层 trace_id: {logger.get_trace_id()}")
    print()


if __name__ == "__main__":
    demo_basic_trace_id()
    demo_context_manager()
    demo_ecs_integration()
    demo_nested_context()

    print("=" * 60)
    print("所有演示完成！")
    print("=" * 60)
