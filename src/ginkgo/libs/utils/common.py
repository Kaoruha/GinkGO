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
        show_log = True
        if "progress" in kwargs and isinstance(kwargs["progress"], Progress):
            show_log = False
        if kwargs.get("no_log") == True:
            show_log = False
        if not show_log:
            return func(*args, **kwargs)
        start_time = time.time()  # 记录开始时间
        result = None
        try:
            result = func(*args, **kwargs)  # 执行原函数
            return result  # 返回原函数的结果
        except Exception as e:
            console.print_exception()
            raise  # Re-raise the exception
        finally:
            end_time = time.time()  # 记录结束时间
            duration = end_time - start_time  # 计算持续时间
            console.print(f":camel: FUNCTION [yellow]{func.__name__}[/] excuted in {format_time_seconds(duration)}.")

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
    func_ran_expired = 60 * 60 * 4

    @wraps(func)
    def wrapper(*args, **kwargs):
        in_progress = False
        if "progress" in kwargs and isinstance(kwargs["progress"], Progress):
            in_progress = True

        # 检查是否有 no_skip 参数，如果有且为 True，则跳过缓存检查并强制执行
        no_skip = kwargs.pop("no_skip", False)  # 使用 pop 避免传递给原函数

        # 生成缓存键
        cache_key = f"skip_if_ran:{func.__name__}:{args}:{kwargs}"
        print("Cached_KEY:")
        print(cache_key)

        # 如果不是 no_skip，才检查缓存
        if not no_skip:
            # 使用RedisService检查缓存
            from ginkgo.data.containers import container

            redis_service = container.redis_service()

            if redis_service.exists(cache_key):
                # 缓存存在，跳过执行
                return

        try:
            result = func(*args, **kwargs)  # 执行原函数
            # 无论是否 no_skip，都更新缓存并刷新 TTL
            from ginkgo.data.containers import container

            redis_service = container.redis_service()
            redis_service.set_cache(cache_key, "Yeah", func_ran_expired)
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
                last_exception = None
                for i in range(max_try):
                    try:
                        return f(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        console.print(f"[red]Retry FUNCTION [yellow]{f.__name__}[/] {i+1}/{max_try}[/red]")
                        if i >= max_try - 1:
                            console.print_exception()
                            raise e
                        else:
                            # 检查debug模式
                            from ginkgo.libs import GCONF

                            if GCONF.DEBUGMODE:
                                # Debug模式：跳过等待，立即重试
                                console.print(f"[yellow]Debug mode: Skipping wait, immediate retry {i+2}/{max_try}[/]")
                            else:
                                # 正常模式：指数递增等待时间：30、36、42、51、60秒...
                                sleep_time = int(30 * (2 ** (i / 4)))
                                console.print(
                                    f"[yellow]Starting wait: {sleep_time} seconds before retry {i+2}/{max_try}[/]"
                                )

                                # 使用Rich Progress显示等待进度
                                from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

                                with Progress(
                                    TextColumn(f"[cyan]:hourglass_not_done: Retry {i+1}/{max_try}"),
                                    BarColumn(bar_width=20),
                                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                                    TextColumn("•"),
                                    TextColumn("[yellow]{task.completed}[/]/[green]{task.total}[/]s"),
                                    transient=True,
                                ) as progress:
                                    task = progress.add_task("waiting", total=sleep_time)
                                    for wait_sec in range(sleep_time):
                                        time.sleep(1)
                                        progress.update(task, advance=1)
                    finally:
                        pass

            return wrapper

        return decorator

    else:  # 如果传入了函数，说明是无参调用

        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(max_try):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    console.print(f"[red]Retry FUNCTION [yellow]{func.__name__}[/] {i+1}/{max_try}[/red]")
                    if i >= max_try - 1:
                        console.print_exception()
                        raise e
                    else:
                        # 检查debug模式
                        from ginkgo.libs import GCONF

                        if GCONF.DEBUGMODE:
                            # Debug模式：跳过等待，立即重试
                            console.print(f"[yellow]Debug mode: Skipping wait, immediate retry {i+2}/{max_try}[/]")
                        else:
                            # 正常模式：指数递增等待时间：30、36、42、51、60秒...
                            sleep_time = int(30 * (2 ** (i / 4)))
                            console.print(
                                f"[yellow]Starting wait: {sleep_time} seconds before retry {i+2}/{max_try}[/]"
                            )

                            # 使用Rich Progress显示等待进度
                            from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

                            with Progress(
                                TextColumn(f"[cyan]:hourglass_not_done: Retry {i+1}/{max_try}"),
                                BarColumn(bar_width=20),
                                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                                TextColumn("•"),
                                TextColumn("[yellow]{task.completed}[/]/[green]{task.total}[/]s"),
                                transient=True,
                            ) as progress:
                                task = progress.add_task("waiting", total=sleep_time)
                                for wait_sec in range(sleep_time):
                                    time.sleep(1)
                                    progress.update(task, advance=1)
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
                def make_hashable(obj, _seen=None):
                    """Convert unhashable objects to hashable form with better error handling"""
                    if _seen is None:
                        _seen = set()

                    # 防止循环引用
                    obj_id = id(obj)
                    if obj_id in _seen:
                        return f"<circular_ref_{obj_id}>"

                    try:
                        if isinstance(obj, dict):
                            _seen.add(obj_id)
                            result = tuple(sorted((k, make_hashable(v, _seen)) for k, v in obj.items()))
                            _seen.remove(obj_id)
                            return result
                        elif isinstance(obj, list):
                            _seen.add(obj_id)
                            result = tuple(make_hashable(item, _seen) for item in obj)
                            _seen.remove(obj_id)
                            return result
                        elif isinstance(obj, set):
                            _seen.add(obj_id)
                            result = tuple(sorted(make_hashable(item, _seen) for item in obj))
                            _seen.remove(obj_id)
                            return result
                        elif hasattr(obj, "__dict__") and not isinstance(obj, (str, int, float, bool, type(None))):
                            # 对于复杂对象，只使用类名和基本标识符，避免深度递归
                            return (obj.__class__.__name__, f"instance_{obj_id}")
                        else:
                            return obj
                    except (TypeError, RecursionError, AttributeError):
                        # 如果转换失败，返回对象的基本表示
                        return f"<unhashable_{type(obj).__name__}_{obj_id}>"

                hashable_args = tuple(make_hashable(arg) for arg in args)
                hashable_kwargs = tuple(sorted((k, make_hashable(v)) for k, v in kwargs.items()))
                cache_key = (f.__name__, hashable_args, hashable_kwargs)
                if cache_key in cache_data:
                    cached_value = cache_data.get(cache_key)
                    if cached_value is not None:
                        result, timestamp = cached_value
                        # 检查缓存是否过期
                        if time.time() - timestamp < expiration_seconds:
                            print(f":fire::fire::fire: 从缓存中获取结果: {f.__name__} :fire::fire::fire:")
                            return result
                        else:
                            print("缓存过期，重新计算并缓存")
                    else:
                        print("缓存值为None，重新计算并缓存")

                # 执行函数，获取结果
                result = f(*args, **kwargs)
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
                        print(f":fire::fire::fire: 从缓存中获取结果: {func.__name__} :fire::fire::fire:")
                        return result
                    else:
                        print("缓存过期，重新计算并缓存")
                else:
                    print("缓存值为None，重新计算并缓存")

            # 执行函数，获取结果
            result = func(*args, **kwargs)
            # 存入缓存并记录时间戳
            cache_data[cache_key] = (result, time.time())
            return result

        return wrapper
