import time
import math
import threading
from collections import OrderedDict

from functools import wraps
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from ginkgo.libs.core.config import GinkgoConfig

console = Console()
_gconf = GinkgoConfig()


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


def time_logger(func=None, *, enabled=None, threshold=None, profile_mode=None):
    """
    智能时间日志装饰器 - 环境感知的性能监控
    
    Args:
        func: 被装饰的函数
        enabled: 是否启用（None表示根据环境自动判断）
        threshold: 慢查询阈值（秒），超过此值才记录日志
        profile_mode: 性能分析模式，强制启用监控
    
    优化特性:
    - 生产环境默认禁用，避免性能开销
    - 智能阈值控制，只记录慢查询
    - 支持性能分析模式
    - 保持向后兼容性
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 从GCONF获取配置，参数优先于配置
            actual_enabled = enabled if enabled is not None else _gconf.DECORATOR_TIME_LOGGER_ENABLED
            actual_threshold = threshold if threshold is not None else _gconf.DECORATOR_TIME_LOGGER_THRESHOLD
            actual_profile_mode = profile_mode if profile_mode is not None else _gconf.DECORATOR_TIME_LOGGER_PROFILE_MODE
            
            # 环境感知判断
            should_monitor = actual_enabled
            if should_monitor is None:
                # 生产环境仅在profile模式或超过阈值时监控
                should_monitor = _gconf.DEBUGMODE or actual_profile_mode
            
            # 快速路径：生产环境且未启用性能分析
            if not should_monitor and not actual_profile_mode:
                return f(*args, **kwargs)

            # 检查特殊参数控制
            show_log = True
            if "progress" in kwargs and isinstance(kwargs["progress"], Progress):
                show_log = False
            if kwargs.get("no_log") == True:
                show_log = False
                
            # 如果不显示日志且非性能分析模式，直接执行
            if not show_log and not actual_profile_mode:
                return f(*args, **kwargs)

            start_time = time.time()
            result = None
            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                # 异常情况下总是记录性能数据
                duration = time.time() - start_time
                if show_log or duration > actual_threshold:
                    console.print(f":warning: FUNCTION [red]{f.__name__}[/] failed after {format_time_seconds(duration)}")
                console.print_exception()
                raise
            finally:
                if should_monitor or actual_profile_mode:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # 智能日志记录：只记录慢查询或调试模式
                    if show_log and (_gconf.DEBUGMODE or duration > actual_threshold or actual_profile_mode):
                        # 根据执行时间选择不同的图标和颜色
                        if duration > actual_threshold * 10:  # 超慢查询
                            icon, color = ":snail:", "red"
                        elif duration > actual_threshold * 5:  # 慢查询
                            icon, color = ":hourglass_not_done:", "yellow"
                        elif duration > actual_threshold:  # 略慢
                            icon, color = ":camel:", "yellow"
                        else:  # 正常
                            icon, color = ":zap:", "green"
                            
                        console.print(f"{icon} FUNCTION [{color}]{f.__name__}[/] executed in {format_time_seconds(duration)}")

        return wrapper
    
    # 支持 @time_logger 和 @time_logger(...) 两种调用方式
    if func is None:
        return decorator
    else:
        return decorator(func)


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


def retry(func=None, *, max_try: int = None, backoff_factor: float = None):
    """
    智能重试装饰器，支持从GCONF读取配置
    
    Args:
        max_try: 最大重试次数，None时从GCONF读取
        backoff_factor: 退避因子，None时从GCONF读取
    """
    # 获取配置
    from ginkgo.libs import GCONF
    
    actual_max_try = max_try if max_try is not None else GCONF.DECORATOR_RETRY_MAX_ATTEMPTS
    actual_backoff_factor = backoff_factor if backoff_factor is not None else GCONF.DECORATOR_RETRY_BACKOFF_FACTOR
    
    # 检查重试是否启用
    if not GCONF.DECORATOR_RETRY_ENABLED:
        # 重试被禁用，直接返回原函数
        if func is not None:
            return func
        else:
            return lambda f: f
    
    def _retry_logic(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(actual_max_try):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    console.print(f"[red]Retry FUNCTION [yellow]{f.__name__}[/] {i+1}/{actual_max_try}[/red]")
                    if i >= actual_max_try - 1:
                        console.print_exception()
                        raise e
                    else:
                        if GCONF.DEBUGMODE:
                            # Debug模式：跳过等待，立即重试
                            console.print(f"[yellow]Debug mode: Skipping wait, immediate retry {i+2}/{actual_max_try}[/]")
                        else:
                            # 使用配置的退避因子计算等待时间
                            base_sleep = 30  # 基础等待时间30秒
                            sleep_time = int(base_sleep * (actual_backoff_factor ** i))
                            console.print(
                                f"[yellow]Starting wait: {sleep_time} seconds before retry {i+2}/{actual_max_try}[/]"
                            )

                            # 使用Rich Progress显示等待进度
                            from rich.progress import Progress, BarColumn, TextColumn

                            with Progress(
                                TextColumn(f"[cyan]:hourglass_not_done: Retry {i+1}/{actual_max_try}"),
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

    if func is None:  # 带参调用 @retry(max_try=5)
        return _retry_logic
    else:  # 无参调用 @retry
        return _retry_logic(func)

def datasource_retry(source_name: str):
    """
    数据源专用重试装饰器，根据数据源类型自动配置重试策略
    
    Args:
        source_name: 数据源名称 ('tushare', 'baostock', 'tdx', 'yahoo')
    
    Usage:
        @datasource_retry('tushare')
        def fetch_stock_data():
            pass
    """
    from ginkgo.libs import GCONF
    
    # 获取数据源特定配置
    retry_config = GCONF.get_datasource_retry_config(source_name)
    
    return retry(
        max_try=retry_config["retry_max_attempts"],
        backoff_factor=retry_config["retry_backoff_factor"]
    )


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
                            # console.print(f":fire::fire::fire: 从缓存中获取结果: {f.__name__} :fire::fire::fire:")
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
        # 当直接使用 @cache_with_expiration 而不带参数时
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
                        # console.print(f":fire::fire::fire: 从缓存中获取结果: {func.__name__} :fire::fire::fire:")
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


def ensure_tick_table(func):
    """
    装饰器：确保tick表存在后再执行函数

    自动检测函数参数中的code参数，为对应的股票代码创建tick表

    Args:
        func: 被装饰的函数，需要包含code参数

    Returns:
        装饰后的函数
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        from ginkgo.libs import GLOG

        # 从kwargs中查找code参数
        if "code" in kwargs and isinstance(kwargs["code"], str):
            code = kwargs["code"]

            try:
                from ginkgo.data.drivers import create_table, is_table_exists
                from ginkgo.data.crud.tick_crud import get_tick_model

                # 获取动态tick模型
                tick_model = get_tick_model(code)

                # 检查表是否存在，不存在则创建
                if not is_table_exists(tick_model):
                    GLOG.INFO(f"Creating tick table for {code}: {tick_model.__tablename__}")
                    create_table(tick_model)
                    GLOG.INFO(f"Successfully created tick table: {tick_model.__tablename__}")
                else:
                    GLOG.DEBUG(f"Tick table already exists: {tick_model.__tablename__}")

            except Exception as table_error:
                GLOG.ERROR(f"Failed to ensure tick table for {code}: {table_error}")

        # 执行原函数
        return func(*args, **kwargs)

    return wrapper
