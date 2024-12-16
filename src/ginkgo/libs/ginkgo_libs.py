import time
import math
import threading
from collections import OrderedDict

from functools import wraps
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn


console = Console()


def try_wait_counter(try_time: int = 0, min: int = 0.1, max: int = 30) -> int:
    try_time = try_time if try_time > 1 else 1
    res = 2 * math.log(try_time)
    res = res if res < max else max
    return res if res > min else min


def str2bool(strint: str or int, *args, **kwargs) -> bool:
    """
    Try parse string or int to bool.
    Args:
        strint(str or int): input, 1 --> True, 'true' --> True
    Returns:
        try parse the input, if not Ture return False
    """
    if isinstance(strint, int):
        return strint == 1

    return strint.lower() in [
        "true",
        "1",
        "t",
        "y",
        "yes",
        "yeah",
        "yup",
        "certainly",
        "uh-huh",
    ]


def time_logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        in_progress = False
        if "progress" in kwargs and isinstance(kwargs["progress"], Progress):
            in_progress = True
        start_time = time.time()  # 记录开始时间
        result = None
        try:
            result = func(*args, **kwargs)  # 执行原函数
            return result  # 返回原函数的结果
        except Exception as e:
            console.print_exception()
        finally:
            end_time = time.time()  # 记录结束时间
            duration = end_time - start_time  # 计算持续时间
            if not in_progress:
                console.print(
                    f":camel: FUNCTION [yellow]{func.__name__}[/] excuted in {format_time_seconds(duration)}."
                )

    return wrapper


def format_time_seconds(ttl):
    if ttl < 0:
        return "Key does not exist or has expired."
    elif ttl < 60:
        return f"{ttl:.5f} seconds"
    elif ttl < 3600:
        minutes = int(ttl // 60)
        seconds = int(ttl % 60)
        return f"{minutes} minute{'s' if minutes >1 else ''} {seconds} second{'s' if seconds>1 else ''}"
    elif ttl < 86400:
        hours = int(ttl // 3600)
        minutes = int((ttl % 3600) // 60)
        return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes >1 else ''}"
    else:
        days = int(ttl // 86400)
        hours = int((ttl % 86400) // 3600)
        minutes = int(((ttl % 86400) % 3600) // 60)
        return f"{days} day{'s' if days > 1 else ''} {hours} hour{'s' if hours >1 else ''} {minutes} minute{'s'if minutes>1 else ''}"


def skip_if_ran(func):
    from ginkgo.data.drivers import create_redis_connection

    func_ran_expired = 60 * 60 * 4

    func_ran_expired = 60

    @wraps(func)
    def wrapper(*args, **kwargs):
        in_progress = False
        if "progress" in kwargs and isinstance(kwargs["progress"], Progress):
            in_progress = True
        cache_key = f"{func.__name__}:{args}:{kwargs}"
        print("Cached_KEY:")
        print(cache_key)
        cached_result = create_redis_connection().get(cache_key)
        if cached_result is not None:
            ttl = create_redis_connection().ttl(cache_key)
            if not in_progress:
                ttl_msg = ""
                console.print(f":camel: FUNCTION [yellow]{cache_key}[/] cached. ttl: {format_time_seconds(ttl)}.")
            return
        try:
            result = func(*args, **kwargs)  # 执行原函数
            create_redis_connection().set(cache_key, "Yeah", ex=func_ran_expired)
            return result
        except Exception as e:
            console.print_exception()
        finally:
            pass

    return wrapper


def retry(func=None, *, max_try: int = 5):  # 默认参数设置为 None，以区分是否传参
    if func is None:  # 如果没有传入函数，说明是带参调用

        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                for i in range(max_try):
                    try:
                        return f(*args, **kwargs)
                    except Exception as e:
                        console.print(f"[red]Retry FUNCTION [yellow]{f.__name__}[/] {i+1}/{max_try}[/red]")
                        if i >= max_try - 1:
                            console.print_exception()
                    finally:
                        pass

            return wrapper

        return decorator

    else:  # 如果传入了函数，说明是无参调用

        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_try):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    console.print(f"[red]Retry FUNCTION [yellow]{func.__name__}[/] {i+1}/{max_try}[/red]")
                    if i >= max_try - 1:
                        console.print_exception()
                finally:
                    pass

        return wrapper


class RichProgress:
    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=60),
            "[progress.percentage]{task.completed}/{task.total} [{task.percentage:>2.0f}%]",
            "Elapsed:",
            TimeElapsedColumn(),
            " ETA:",
            TimeRemainingColumn(),
        )
        self.progress.start()
        return self.progress

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.progress.stop()


cache_data = OrderedDict()


def cache_with_expiration(func=None, *, expiration_seconds=60):  # 默认缓存时长为60秒
    # ATTENTION expiration secconds too large will cause the mem leak.
    # Memory Clean
    max_cache_size = 64
    # 存储缓存的内容
    global cache_data
    if func is None:

        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))
                if cache_key in cache_data:
                    cached_value = cache_data.get(cache_key)
                    if cached_value is not None:
                        result, timestamp = cached_value
                        # 检查缓存是否过期
                        if time.time() - timestamp < expiration_seconds:
                            print(f"从缓存中获取结果")
                            return result
                        else:
                            print("缓存过期，重新计算并缓存")
                    else:
                        print("缓存值为None，重新计算并缓存")
                print("没有缓存，重新计算并缓存")

                # 执行函数，获取结果
                result = func(*args, **kwargs)
                # 存入缓存并记录时间戳
                cache_data[cache_key] = (result, time.time())
                print("缓存结果")
                if len(cache_data) > max_cache_size:
                    cache_data.popitem(last=False)
                return result

            return wrapper

        return decorator
    else:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key，包含方法名和参数
            cache_key = (func.__name__, args, tuple(sorted(kwargs.items())))
            # 检查缓存是否存在
            if cache_key in cache_data:
                cached_value = cache_data.get(cache_key)
                if cached_value is not None:
                    result, timestamp = cached_value
                    # 检查缓存是否过期
                    if time.time() - timestamp < expiration_seconds:
                        print(f"从缓存中获取结果")
                        return result
                    else:
                        print("缓存过期，重新计算并缓存")
                else:
                    print("缓存值为None，重新计算并缓存")
            print("没有缓存，重新计算并缓存")

            # 执行函数，获取结果
            result = func(*args, **kwargs)
            # 存入缓存并记录时间戳
            cache_data[cache_key] = (result, time.time())
            return result

        return wrapper
