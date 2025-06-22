from rich.console import Console
from functools import wraps

console = Console()
# Adjustfactor CRUD


def add_adjustfactor(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import add_adjustfactor as func

    return func(*args, **kwargs)


def add_adjustfactors(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import add_adjustfactors as func

    return func(*args, **kwargs)


def delete_adjustfactor(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import delete_adjustfactor as func

    return func(*args, **kwargs)


def get_adjustfactor(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import get_adjustfactor as func

    return func(*args, **kwargs)


def get_adjustfactors(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import get_adjustfactors_page_filtered as func

    return func(*args, **kwargs)


# Analyzer Record CRUD
def add_analyzer_record(*args, **kwargs):
    from ginkgo.data.operations.analyzer_record_crud import add_analyzer_record as func

    return func(*args, **kwargs)


def add_analyzer_records(*args, **kwargs):
    from ginkgo.data.operations.analyzer_record_crud import add_analyzer_records as func

    return func(*args, **kwargs)


def delete_analyzer_record(*args, **kwargs):
    from ginkgo.data.operations.analyzer_record_crud import delete_analyzer_record as func

    return func(*args, **kwargs)


def delete_analyzer_records_filtered(*args, **kwargs):
    from ginkgo.data.operations.analyzer_record_crud import delete_analyzer_records_filtered as func

    return func(*args, **kwargs)


def get_analyzer_records_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.analyzer_record_crud import get_analyzer_records_page_filtered as func

    return func(*args, **kwargs)


# Bar CRUD
def add_bar(*args, **kwargs):
    from ginkgo.data.operations.bar_crud import add_bar as func

    return func(*args, **kwargs)


def add_bars(*args, **kwargs):
    from ginkgo.data.operations.bar_crud import add_bars as func

    return func(*args, **kwargs)


def delete_bars_filtered(*args, **kwargs):
    from ginkgo.data.operations.bar_crud import delete_bars_filtered as func

    return func(*args, **kwargs)


def get_bars_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.bar_crud import get_bars_page_filtered as func

    return func(*args, **kwargs)


# Capital Adjustment CRUD
# TODO
# Engine CRUD
def add_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import add_engine as func

    return func(*args, **kwargs)


def delete_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import delete_engine as func

    return func(*args, **kwargs)


def delete_engines(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import softdelete_engines as func

    return func(*args, **kwargs)


def get_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import get_engine as func

    return func(*args, **kwargs)


def get_engines_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import get_engines_page_filtered as func

    return func(*args, **kwargs)


def update_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import update_engine as func

    return func(*args, **kwargs)


engine_status_name = "live_engine_status"


def update_engine_status(engine_id: str, status: str, *args, **kwargs):
    global engine_status_name
    from ginkgo.data.drivers import create_redis_connection

    redis = create_redis_connection()
    r = redis.hset(engine_status_name, engine_id, status)


def get_engine_status(engine_id: str, *args, **kwargs):
    global engine_status_name
    from ginkgo.data.drivers import create_redis_connection

    r = create_redis_connection()
    value = r.hget(engine_status_name, engine_id)
    return value


def delete_engine_status(engine_id: str, *args, **kwargs):
    global engine_status_name
    from ginkgo.data.drivers import create_redis_connection

    r = create_redis_connection()
    value = r.hdel(engine_status_name, engine_id)
    # TODO


# TODO
# Engine Handler Mapping CRUD
def add_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import add_engine_handler_mapping as func

    return func(*args, **kwargs)


def delete_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import delete_engine_handler_mapping as func

    return func(*args, **kwargs)


def update_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import update_engine_handler_mapping as func

    return func(*args, **kwargs)


def get_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import get_engine_handler_mapping as func

    return func(*args, **kwargs)


def get_engine_handler_mappings_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import get_engine_handler_mappings_page_filtered as func

    return func(*args, **kwargs)


# Engine Portfolio Mapping CRUD
def add_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import add_engine_portfolio_mapping as func

    # TODO Remove Params
    return func(*args, **kwargs)


def delete_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import delete_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def update_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import update_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def get_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import get_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def get_engine_portfolio_mappings_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import get_engine_portfolio_mappings_page_filtered as func

    return func(*args, **kwargs)


# Portfolio file Mapping CRUD
def add_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import add_portfolio_file_mapping as func

    return func(*args, **kwargs)


def delete_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import delete_portfolio_file_mapping as func

    # TODO Remove Params

    return func(*args, **kwargs)


def update_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import update_portfolio_file_mapping as func

    return func(*args, **kwargs)


def get_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import get_portfolio_file_mapping as func

    return func(*args, **kwargs)


def get_portfolio_file_mappings_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import get_portfolio_file_mappings_page_filtered as func

    return func(*args, **kwargs)


def fget_portfolio_file_mappings_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import fget_portfolio_file_mappings_page_filtered as func

    return func(*args, **kwargs)


# File CRUD
def add_file(*args, **kwargs):
    from ginkgo.data.operations.file_crud import add_file as func

    return func(*args, **kwargs)


def delete_file(*args, **kwargs):
    from ginkgo.data.operations.file_crud import delete_file as func

    return func(*args, **kwargs)


def update_file(*args, **kwargs):
    from ginkgo.data.operations.file_crud import update_file as func

    return func(*args, **kwargs)


def get_file(*args, **kwargs):
    from ginkgo.data.operations.file_crud import get_file as func

    return func(*args, **kwargs)


def get_files_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.file_crud import get_files_page_filtered as func

    return func(*args, **kwargs)


def get_file_content(*args, **kwargs):
    from ginkgo.data.operations.file_crud import get_file_content as func

    return func(*args, **kwargs)


# Handler CRUD
def add_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import add_handler as func

    return func(*args, **kwargs)


def delete_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import delete_handler as func

    return func(*args, **kwargs)


def update_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import update_handler as func

    return func(*args, **kwargs)


def get_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import get_handler as func

    return func(*args, **kwargs)


def get_handlers_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import get_handlers_page_filtered as func

    return func(*args, **kwargs)


# Param CRUD
def add_param(*args, **kwargs):
    from ginkgo.data.operations.param_crud import add_param as func

    return func(*args, **kwargs)


def delete_param(*args, **kwargs):
    from ginkgo.data.operations.param_crud import delete_param as func

    return func(*args, **kwargs)


def update_param(*args, **kwargs):
    from ginkgo.data.operations.param_crud import update_param as func

    return func(*args, **kwargs)


def get_params_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.param_crud import get_params_page_filtered as func

    return func(*args, **kwargs)


# Order CRUD
def add_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import add_order as func

    return func(*args, **kwargs)


def add_orders(*args, **kwargs):
    from ginkgo.data.operations.order_crud import add_orders as func

    return func(*args, **kwargs)


def delete_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import delete_order as func

    return func(*args, **kwargs)


def delete_orders_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_crud import delete_orders_filtered as func

    return func(*args, **kwargs)


def update_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import update_order as func

    return func(*args, **kwargs)


def get_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import get_order as func

    return func(*args, **kwargs)


def get_orders_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_crud import get_orders_page_filtered as func

    return func(*args, **kwargs)


# Order Record CRUD
def add_order_record(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import add_order_record as func

    return func(*args, **kwargs)


def add_order_records(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import add_order_records as func

    return func(*args, **kwargs)


def delete_order_record(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import delete_order_record as func

    return func(*args, **kwargs)


def delete_order_records_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import delete_order_records_filtered as func

    return func(*args, **kwargs)


def get_order_records_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import get_order_records_page_filtered as func

    return func(*args, **kwargs)


# Portfolio CRUD
def add_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import add_portfolio as func

    return func(*args, **kwargs)


def delete_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import softdelete_portfolio as func

    return func(*args, **kwargs)


def delete_portfolios(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import delete_portfolios as func

    # TODO Remove engine portfolio mappings
    # TODO Remove portfolio file mappings
    return func(*args, **kwargs)


def get_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import get_portfolio as func

    return func(*args, **kwargs)


def get_portfolios_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import get_portfolios_page_filtered as func

    return func(*args, **kwargs)


def update_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import update_portfolio as func

    return func(*args, **kwargs)


# Handler CRUD
def add_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import add_handler as func

    return func(*args, **kwargs)


def delete_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import delete_handler as func

    return func(*args, **kwargs)


def update_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import update_handler as func

    return func(*args, **kwargs)


def get_handler(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import get_handler as func

    return func(*args, **kwargs)


def get_handlers_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.handler_crud import get_handlers_page_filtered as func

    return func(*args, **kwargs)


# Position CRUD
def add_position(*args, **kwargs):
    from ginkgo.data.operations.position_crud import add_position as func

    return func(*args, **kwargs)


def delete_position(*args, **kwargs):
    from ginkgo.data.operations.position_crud import delete_position as func

    return func(*args, **kwargs)


def delete_positions_filtered(*args, **kwargs):
    from ginkgo.data.operations.position_crud import delete_positions_filtered as func

    return func(*args, **kwargs)


def update_position(*args, **kwargs):
    from ginkgo.data.operations.position_crud import update_position as func

    return func(*args, **kwargs)


def get_positions_filtered(*args, **kwargs):
    from ginkgo.data.operations.position_crud import get_positions_page_filtered as func

    return func(*args, **kwargs)


# Position Record CRUD
def add_position_record(*args, **kwargs):
    from ginkgo.data.operations.position_record_crud import add_position_record as func

    return func(*args, **kwargs)


def delete_position_records_filtered(*args, **kwargs):
    from ginkgo.data.operations.position_record_crud import delete_position_records_filtered as func

    return func(*args, **kwargs)


def get_position_records_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.position_record_crud import get_position_records_page_filtered as func

    return func(*args, **kwargs)


# Signal CRUD
def add_signal(*args, **kwargs):
    from ginkgo.data.operations.signal_crud import add_signal as func

    return func(*args, **kwargs)


def delete_signal_filtered(*args, **kwargs):
    from ginkgo.data.operations.signal_crud import delete_signal_filtered as func

    return func(*args, **kwargs)


def get_signals_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.signal_crud import get_signals_page_filtered as func

    return func(*args, **kwargs)


# Order CRUD
def add_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import add_order as func

    return func(*args, **kwargs)


def delete_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import delete_order as func

    return func(*args, **kwargs)


def update_order(*args, **kwargs):
    from ginkgo.data.operations.order_crud import update_order as func

    return func(*args, **kwargs)


def get_orders_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_crud import get_orders_page_filtered as func

    return func(*args, **kwargs)


# Order Record CRUD
def add_order_record(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import add_order_record as func

    return func(*args, **kwargs)


def delete_order_records_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import delete_order_records_filtered as func

    return func(*args, **kwargs)


def get_order_records_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.order_record_crud import get_order_records_page_filtered as func

    return func(*args, **kwargs)


# Stock Info CRUD
def add_stockinfo(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import add_stockinfo as func

    return func(*args, **kwargs)


def delete_stockinfo(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import delete_stockinfo as func

    return func(*args, **kwargs)


def upsert_stockinfo(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import upsert_stockinfo as func

    return func(*args, **kwargs)


def get_stockinfo(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import get_stockinfo as func

    return func(*args, **kwargs)


def get_stockinfos_filtered(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import get_stockinfos_filtered as func

    return func(*args, **kwargs)


# TODO
# Tick CRUD
def ensure_tick_table(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        from ginkgo.data.drivers import create_table
        from ginkgo.data.operations.tick_crud import get_tick_model

        try:
            if "code" in kwargs and isinstance(kwargs["code"], str):
                model = get_tick_model(code=kwargs["code"])
                if kwargs.get("no_log") == True:
                    create_table(model, no_log=True)
                else:
                    create_table(model)
            result = func(*args, **kwargs)  # 执行原函数
            return result
        except Exception as e:
            console.print_exception()
        finally:
            pass

    return wrapper


@ensure_tick_table
def add_ticks(*args, **kwargs):
    from ginkgo.data.operations.tick_crud import add_ticks as func

    return func(*args, **kwargs)


@ensure_tick_table
def get_ticks_page_filtered(*args, **kwargs):
    from ginkgo.data.operations.tick_crud import get_ticks_page_filtered as func

    return func(*args, **kwargs)


@ensure_tick_table
def delete_ticks_filtered(*args, **kwargs):
    from ginkgo.data.operations.tick_crud import delete_ticks_filtered as func

    return func(*args, **kwargs)


def get_backtest_record():
    pass


def get_analyzer_df_by_backtest():
    pass


# TODO
# Tick Summary CRUD
# TODO
# TradeDay CRUD
# TODO
# Transfer CRUD
# TODO
# Transfer Record CRUD
# TODO
import inspect

__all__ = [name for name, obj in inspect.getmembers(inspect.getmodule(inspect.currentframe()), inspect.isfunction)]
