# Upstream: Data Services
# Downstream: Data Drivers
# Role: 数据层装饰器（从 libs/utils/common.py 迁移，避免 libs 依赖 data）

from functools import wraps


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
