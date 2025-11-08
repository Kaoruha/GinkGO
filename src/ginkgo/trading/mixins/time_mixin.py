import datetime
import inspect
from contextlib import contextmanager
from datetime import date
from functools import wraps
from typing import Optional, List, Any
from rich.console import Console
from ginkgo.libs import GLOG, datetime_normalize

console = Console()


class TimeMixin:
    def __init__(self, business_timestamp: any = None, *args, **kwargs) -> None:
        # 现实时间戳 - 始终使用当前时间
        current_time = datetime.datetime.now()
        self._timestamp: datetime.datetime = current_time

        # 业务时间戳 - 可选参数，回测中的业务逻辑时间（如价格数据时间）
        self._business_timestamp: datetime.datetime = None
        if business_timestamp is not None:
            normalized_business_timestamp = datetime_normalize(business_timestamp)
            if normalized_business_timestamp is None:
                raise ValueError(f"Invalid business_timestamp format: {business_timestamp}")
            self._business_timestamp = normalized_business_timestamp

        # 时间提供者（中央时间管理）
        self._time_provider: Any = None

        # 当前时间（如果不使用time_provider，则用此变量存储）
        self._now: datetime.datetime = None

        # 实体创建/初始化时间
        self._init_time: datetime.datetime = current_time

        # 最后更新时间
        self._last_update: datetime.datetime = current_time

        # 验证专用run_id（兜底存储，当没有BacktestBase时使用）
        self._validation_run_id: Optional[str] = None

        # 时间验证相关（ITimeAwareComponent接口）
        self._time_validator: Optional[Any] = None  # TimeBoundaryValidator

    @property
    def timestamp(self) -> datetime.datetime:
        """
        The timestamp when this entity was created (real world time).
        This is the actual creation time in the real world.
        """
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: any) -> None:
        """
        Set the creation timestamp for this entity (real world time).
        """
        self._timestamp = datetime_normalize(value)

    @property
    def business_timestamp(self) -> datetime.datetime:
        """
        The business timestamp when this entity's business logic occurred.
        In backtesting, this is typically the time of the price data that triggered the event.
        """
        return self._business_timestamp

    @business_timestamp.setter
    def business_timestamp(self, value: any) -> None:
        """
        Set the business timestamp for this entity.
        """
        self._business_timestamp = datetime_normalize(value)

    def set_business_timestamp(self, business_timestamp: any) -> None:
        """
        设置业务时间戳的专用API方法
        每次调用时自动更新现实时间戳为当前时间

        Args:
            business_timestamp: 业务时间戳（业务逻辑时间）
        """
        # 自动更新现实时间戳为当前时间
        self._timestamp = datetime.datetime.now()

        # 更新业务时间戳
        normalized_business_timestamp = datetime_normalize(business_timestamp)
        if normalized_business_timestamp is None:
            raise ValueError(f"Invalid business_timestamp format: {business_timestamp}")
        self._business_timestamp = normalized_business_timestamp

    @property
    def init_time(self) -> datetime.datetime:
        """
        The time when this entity was created/initialized.
        """
        return self._init_time

    @init_time.setter
    def init_time(self, value: any) -> None:
        """
        Set the initialization time for this entity.
        """
        self._init_time = datetime_normalize(value)

    @property
    def last_update(self) -> datetime.datetime:
        """
        The time when this entity was last updated/modified.
        """
        return self._last_update

    @last_update.setter
    def last_update(self, value: any) -> None:
        """
        Set the last update time for this entity.
        """
        self._last_update = datetime_normalize(value)

    def advance_time(self, time: any, *args, **kwargs) -> bool:
        """
        Advance time to next frame.
        Timestamp update. Just support from past to future.

        After time advancement, calls _on_time_advance() for subclass-specific processing.

        Args:
            time(any): new time
        Returns:
            bool: True if time was successfully advanced, False otherwise
        """
        has_log = hasattr(self, "log") and callable(self.log)
        # Should support Day or Min or other frame gap
        try:
            time = datetime_normalize(time)
        except (ValueError, TypeError):
            # Invalid time format, log error and return without updating time
            if has_log:
                self.log("ERROR", "Time format not support, can not update time")
            return False

        if time is None:
            if has_log:
                self.log("ERROR", "Time format not support, can not update time")
            return False

        if self._now is None:
            self._now = time
            if has_log:
                self.log("DEBUG", f"{type(self).__name__} Time Init: None --> {self._now}")
            # Call time advance hook for initial setup
            self._on_time_advance(time)
            return True

        if time < self.now:
            if has_log:
                self.log("ERROR", "We can not go back such as a TIME TRAVALER.")
            return False

        elif time == self.now:
            if has_log:
                self.log("WARNING", "Time not goes on.")
            return False

        else:
            # time > self.now
            # Go next frame
            old = self._now
            self._now = time
            if has_log:
                self.log("DEBUG", f"{type(self).__name__} Time Elapses: {old} --> {self.now}")
            console.print(f":swimmer: {type(self).__name__} Time Elapses: {old} --> {self.now}")

            # Call time advance hook for subclass-specific processing
            self._on_time_advance(time)
            return True

    def is_before(self, other_time: any) -> bool:
        """
        Check if current time is before the given time.

        Args:
            other_time(any): Time to compare against
        Returns:
            bool: True if current time is before other_time
        """
        if self._now is None:
            return True  # No time set means we're before any time

        other_time = datetime_normalize(other_time)
        if other_time is None:
            return False

        return self._now < other_time

    def is_after(self, other_time: any) -> bool:
        """
        Check if current time is after the given time.

        Args:
            other_time(any): Time to compare against
        Returns:
            bool: True if current time is after other_time
        """
        if self._now is None:
            return False  # No time set means we're not after any time

        other_time = datetime_normalize(other_time)
        if other_time is None:
            return True

        return self._now > other_time

    def time_elapsed_since(self, start_time: any) -> datetime.timedelta:
        """
        Calculate time elapsed since start_time.

        Args:
            start_time(any): Start time to calculate from
        Returns:
            timedelta: Time elapsed since start_time
        """
        if self._now is None:
            raise ValueError("Current time not set, cannot calculate elapsed time")

        start_time = datetime_normalize(start_time)
        if start_time is None:
            raise ValueError("Invalid start_time format")

        return self._now - start_time

    def can_advance_to(self, target_time: any) -> bool:
        """
        Check if we can advance to the target time (no backward movement).

        Args:
            target_time(any): Target time to check
        Returns:
            bool: True if advancement is allowed
        """
        target_time = datetime_normalize(target_time)
        if target_time is None:
            return False

        if self._now is None:
            return True  # Can advance from None to any valid time

        return target_time >= self._now

    def reset_time(self) -> None:
        """
        Reset time state to None.
        Useful for testing or restarting time progression.
        """
        self._now = None

    def _on_time_advance(self, new_time: datetime.datetime) -> None:
        """
        Hook method called after time advancement.
        Subclasses can override this to implement time-dependent business logic.

        Args:
            new_time(datetime.datetime): The new current time
        """
        # Default behavior: update last_update timestamp
        self._last_update = new_time

    # ==================== ITimeAwareComponent接口实现 ====================

    def set_run_id(self, run_id: str) -> None:
        """
        设置回测会话ID（协作式多重继承 + 兜底存储）

        TimeRelated职责：更新validator的run_id以支持跨实例缓存共享
        BacktestBase职责：设置业务属性 _run_id

        Args:
            run_id: 回测会话的唯一标识符
        """
        # 1. 协作调用父类（如BacktestBase）
        if hasattr(super(), 'set_run_id'):
            super().set_run_id(run_id)
        else:
            # 2. 兜底：如果没有父类管理run_id，自己存一份
            self._validation_run_id = run_id

        # 3. 重建validator（如果已存在）
        if hasattr(self, '_time_validator') and self._time_validator is not None:
            old_provider = self._time_validator._time_provider
            from ginkgo.trading.time.providers import TimeBoundaryValidator
            self._time_validator = TimeBoundaryValidator(old_provider, run_id=run_id)

    def set_time_provider(self, time_provider: Any) -> None:
        """
        设置时间提供者

        Args:
            time_provider: 时间提供者实例，需要有now()方法
        """
        self._time_provider = time_provider

        # 创建时间边界验证器（validator内部持有provider）
        # 优先级查找run_id：BacktestBase.run_id > _validation_run_id
        from ginkgo.trading.time.providers import TimeBoundaryValidator
        run_id = getattr(self, 'run_id', None) or getattr(self, '_validation_run_id', None)
        self._time_validator = TimeBoundaryValidator(time_provider, run_id=run_id)

    def get_time_provider(self) -> Any:
        """
        获取当前绑定的时间提供者

        Returns:
            时间提供者实例，如果未绑定则返回None
        """
        return self._time_provider

    def on_time_update(self, new_time: datetime.datetime) -> None:
        """
        时间更新通知回调（ITimeAwareComponent接口）

        Args:
            new_time: 新的当前时间
        """
        self.advance_time(new_time)

    def get_current_time(self) -> Optional[datetime.datetime]:
        """
        获取当前时间（ITimeAwareComponent接口）

        Returns:
            Optional[datetime.datetime]: 当前时间，如果未设置则返回None
        """
        return self._now

    # ==================== 时间边界验证（带缓存） ====================

    def validate_data_time(self, data_time: Any, context: str = "data_access") -> bool:
        """
        验证数据时间边界，防止未来数据泄露（委托给Validator的实例级缓存）

        Args:
            data_time: 数据时间戳（datetime或date）
            context: 访问上下文描述（用于日志信息）

        Returns:
            bool: True表示合法，False表示非法
        """
        if self._time_validator is None:
            GLOG.ERROR(
                f"Time provider not set for {self.__class__.__name__}. "
                f"Cannot validate data access time. Call set_time_provider() first."
            )
            return False

        # 类型转换：如果是date类型，转为datetime（validator需要datetime）
        from datetime import date as date_type
        normalized_time = data_time
        if isinstance(data_time, date_type) and not isinstance(data_time, datetime.datetime):
            normalized_time = datetime.datetime.combine(data_time, datetime.time.min)

        current_time = self.get_current_time()

        # 委托给Validator的实例级缓存验证
        return self._time_validator.validate_data_access_cached(
            normalized_time,
            context=context,
            request_time=current_time
        )

    @contextmanager
    def time_validation(self, data_time: Any, context: str = "data_access"):
        """
        时间验证上下文管理器

        提供细粒度的时间验证控制，适合需要在方法内部分段验证的场景。

        Args:
            data_time: 要验证的时间戳（datetime或date）
            context: 上下文描述（用于日志）

        Yields:
            bool: True表示时间合法，False表示非法

        使用示例:
            # 简单使用
            with self.time_validation(end_date) as valid:
                if not valid:
                    return None
                return fetch_data(end_date)

            # 带上下文描述
            with self.time_validation(end_date, "main_query") as valid:
                if valid:
                    data = fetch_data(end_date)
                else:
                    data = None
        """
        is_valid = self.validate_data_time(data_time, context)
        yield is_valid

    # ==================== 时间验证装饰器 ====================

    @staticmethod
    def validate_time(time_params: Optional[List[str]] = None):
        """
        时间边界验证装饰器

        自动检测方法参数中的datetime/date类型并进行时间边界验证，
        防止回测中的未来数据泄露问题。

        Args:
            time_params: 指定要验证的参数名列表。
                        如果为None或空列表，自动检测所有datetime/date类型参数。
                        如果指定参数名，则只验证这些参数，跳过自动检测。

        使用示例:
            @TimeRelated.validate_time()  # 自动检测所有datetime/date参数
            def get_bars(self, code: str, start_date: datetime, end_date: datetime):
                pass

            @TimeRelated.validate_time(['end_date'])  # 只验证end_date
            def get_bars(self, code: str, start_date: datetime, end_date: datetime):
                pass

        Returns:
            装饰器函数
        """
        def decorator(func):
            # 缓存函数签名，避免每次调用都反射
            sig = inspect.signature(func)

            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # 绑定参数
                bound_args = sig.bind(self, *args, **kwargs)
                bound_args.apply_defaults()

                if time_params and len(time_params) > 0:
                    # 用户指定参数名 - 只验证这些参数
                    for param_name in time_params:
                        if param_name not in bound_args.arguments:
                            continue

                        time_value = bound_args.arguments[param_name]

                        # isinstance会自动过滤None值
                        if isinstance(time_value, (datetime.datetime, date)):
                            is_valid = self.validate_data_time(
                                time_value,
                                context=f"{func.__name__}.{param_name}"
                            )
                            if not is_valid:
                                # 验证失败，记录日志并返回None（不执行方法）
                                GLOG.WARN(
                                    f"Invalid time parameter '{param_name}' in {func.__name__}(): {time_value}. "
                                    f"Method execution skipped."
                                )
                                return None
                else:
                    # 自动检测 - 验证所有datetime/date参数
                    for param_name, param_value in bound_args.arguments.items():
                        if param_name == 'self':
                            continue

                        # isinstance会自动过滤None值
                        if isinstance(param_value, (datetime.datetime, date)):
                            is_valid = self.validate_data_time(
                                param_value,
                                context=f"{func.__name__}.{param_name}"
                            )
                            if not is_valid:
                                # 验证失败，记录日志并返回None（不执行方法）
                                GLOG.WARN(
                                    f"Invalid time parameter '{param_name}' in {func.__name__}(): {param_value}. "
                                    f"Method execution skipped."
                                )
                                return None

                return func(self, *args, **kwargs)

            return wrapper
        return decorator
