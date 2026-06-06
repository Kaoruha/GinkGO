# Upstream: TaskTimer (定时任务调度器)
# Downstream: 无（工具函数）
# Role: 装饰器工具函数，提供任务崩溃隔离 + 执行记录追踪

import time
import functools
from typing import Callable, Any
from ginkgo.libs import GLOG


def safe_job_wrapper(func: Callable) -> Callable:
    """
    任务安全包装装饰器

    提供任务崩溃隔离、异常捕获、错误日志功能。
    同时自动记录执行历史到数据库（triggered → success/failed）。

    要求被装饰的方法属于 TaskTimer 实例（self 须有 _record_trigger / _complete_record 方法）。
    如果 TaskTimer 未初始化记录功能，则静默跳过记录，不影响任务执行。

    Args:
        func: 被装饰的函数

    Returns:
        包装后的函数

    Example:
        @safe_job_wrapper
        def _bar_snapshot_job(self):
            # 任务代码
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # 从方法名推断 job 信息
        job_name = func.__name__.lstrip("_").replace("_job", "")
        record_uuid = None
        start_time = time.time()

        # 记录触发
        try:
            if args and hasattr(args[0], "_record_trigger"):
                record_uuid = args[0]._record_trigger(func.__name__)
        except Exception as e:
            GLOG.WARN(f"Failed to record trigger for {func.__name__}: {e}")

        try:
            GLOG.DEBUG(f"Job {func.__name__} started")
            result = func(*args, **kwargs)
            GLOG.DEBUG(f"Job {func.__name__} completed")

            # 记录成功
            try:
                if record_uuid and args and hasattr(args[0], "_complete_record"):
                    duration_ms = int((time.time() - start_time) * 1000)
                    args[0]._complete_record(record_uuid, "success", duration_ms)
            except Exception as e:
                GLOG.WARN(f"Failed to record completion for {func.__name__}: {e}")

            return result

        except Exception as e:
            GLOG.ERROR(f"Job {func.__name__} failed: {e}")

            # 记录失败
            try:
                if record_uuid and args and hasattr(args[0], "_complete_record"):
                    duration_ms = int((time.time() - start_time) * 1000)
                    args[0]._complete_record(record_uuid, "failed", duration_ms, error=str(e))
            except Exception as rec_e:
                GLOG.WARN(f"Failed to record failure for {func.__name__}: {rec_e}")

            return None

    return wrapper
