#!/usr/bin/env python3
"""
回测 Trace ID 验证脚本

验证回测过程中 trace_id 的设置和传播
"""

import sys
import os
sys.path.insert(0, 'src')

import datetime
from ginkgo.libs import GLOG, GCONF
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.enums import EXECUTION_MODE

def verify_trace_id():
    print("=" * 60)
    print("回测 Trace ID 验证")
    print("=" * 60)

    # 1. 创建引擎
    print("\n[步骤 1] 创建回测引擎...")
    engine = EventEngine(
        name="TraceIdVerification",
        mode=EXECUTION_MODE.BACKTEST
    )
    print(f"  引擎 ID: {engine.engine_id}")

    # 2. 启动引擎（此时应生成 run_id 和设置 trace_id）
    print("\n[步骤 2] 启动引擎...")
    engine.start()

    # 3. 验证 trace_id 已设置
    print("\n[步骤 3] 验证 Trace ID...")
    trace_id = GLOG.get_trace_id()
    run_id = engine.run_id

    print(f"  Run ID:    {run_id}")
    print(f"  Trace ID:  {trace_id}")
    print(f"  一致性:    {'✓ 通过' if trace_id == run_id else '✗ 失败'}")

    # 4. 验证 trace_id 在日志输出中
    print("\n[步骤 4] 验证日志输出包含 Trace ID...")
    from ginkgo.libs.core.logger import ecs_processor

    event_dict = {
        'event': 'Verification message',
        'level': 'info',
        'logger_name': 'verification'
    }

    result = ecs_processor(None, None, event_dict)

    has_trace = 'trace' in result
    trace_matches = result.get('trace', {}).get('id') == trace_id

    print(f"  日志包含 trace 字段: {'✓ 是' if has_trace else '✗ 否'}")
    print(f"  trace 值正确:      {'✓ 是' if trace_matches else '✗ 否'}")

    # 5. 停止引擎
    print("\n[步骤 5] 停止引擎...")
    engine.stop()

    # 6. 验证 trace_id 已清理
    final_trace_id = GLOG.get_trace_id()
    print(f"  停止后 Trace ID: {final_trace_id}")
    print(f"  Trace ID 已清理:   {'✓ 是' if final_trace_id is None else '✗ 否'}")

    # 总结
    print("\n" + "=" * 60)
    all_passed = (
        trace_id is not None and
        trace_id == run_id and
        has_trace and
        trace_matches and
        final_trace_id is None
    )

    if all_passed:
        print("✓ 所有验证通过！回测 Trace ID 功能正常工作")
        print(f"\n使用示例：查询该回测的所有日志")
        print(f"  log_service = LogService()")
        print(f"  logs = log_service.query_by_trace_id(trace_id='{trace_id}')")
    else:
        print("✗ 验证失败，请检查实现")

    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    # 确保调试模式开启
    GCONF.set_debug(True)

    success = verify_trace_id()
    sys.exit(0 if success else 1)
