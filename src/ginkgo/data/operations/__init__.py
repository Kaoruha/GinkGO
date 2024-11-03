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


def delete_adjustfactors_by_code_and_date_range(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import delete_adjustfactors_by_code_and_date_range as func

    return func(*args, **kwargs)


def update_adjustfactors_by_code_and_date_range(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import update_adjustfactors_by_code_and_date_range as func

    return func(*args, **kwargs)


def get_adjustfactors_by_code_and_date_range(*args, **kwargs):
    from ginkgo.data.operations.adjustfactor_crud import get_adjustfactors_by_code_and_date_range as func

    return func(*args, **kwargs)


# Analyzer Record CRUD
def add_analyzer_record(*args, **kwargs):
    from ginkgo.data.operations.analyzer_record_crud import add_analyzer_record as func

    return func(*args, **kwargs)


# TODO
# Bar CRUD
# TODO
def add_bars(*args, **kwargs):
    from ginkgo.data.operations.bar_crud import add_bars as func

    return func(*args, **kwargs)


def get_bars(*args, **kwargs):
    from ginkgo.data.operations.bar_crud import get_bars as func

    return func(*args, **kwargs)


# Capital Adjustment CRUD
# TODO
# Engine CRUD
def add_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import add_engine as func

    return func(*args, **kwargs)


def get_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import get_engine as func

    return func(*args, **kwargs)


def get_engines(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import get_engines as func

    return func(*args, **kwargs)


def delete_engine(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import delete_engine as func

    return func(*args, **kwargs)


def delete_engines(*args, **kwargs):
    from ginkgo.data.operations.engine_crud import delete_engines as func

    return func(*args, **kwargs)


# TODO
# Engine Handler Mapping CRUD
def add_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import add_engine_handler_mapping as func

    return func(*args, **kwargs)


def delete_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import delete_engine_handler_mapping as func

    return func(*args, **kwargs)


def get_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import get_engine_handler_mapping as func

    return func(*args, **kwargs)


def get_engine_handler_mappings(*args, **kwargs):
    from ginkgo.data.operations.engine_handler_mapping_crud import get_engine_handler_mappings as func

    return func(*args, **kwargs)


# TODO
# Engine Portfolio Mapping CRUD
def add_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import add_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def delete_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import delete_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def get_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import get_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def get_engine_portfolio_mappings(*args, **kwargs):
    from ginkgo.data.operations.engine_portfolio_mapping_crud import get_engine_portfolio_mappings as func

    return func(*args, **kwargs)


# Portfolio file Mapping CRUD
def add_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import add_portfolio_file_mapping as func

    return func(*args, **kwargs)


def delete_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import delete_portfolio_file_mapping as func

    return func(*args, **kwargs)


def update_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import update_portfolio_file_mapping as func

    return func(*args, **kwargs)


def get_portfolio_file_mapping(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import get_portfolio_file_mapping as func

    return func(*args, **kwargs)


def get_portfolio_file_mappings(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import get_portfolio_file_mappings as func

    return func(*args, **kwargs)


def get_portfolio_file_mappings_fuzzy(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import get_portfolio_file_mappings_fuzzy as func

    return func(*args, **kwargs)


# TODO
# File CRUD
def add_file(*args, **kwargs):
    from ginkgo.data.operations.file_crud import add_file as func

    return func(*args, **kwargs)


def get_files(*args, **kwargs):
    from ginkgo.data.operations.file_crud import get_files as func

    return func(*args, **kwargs)


def get_file_content(*args, **kwargs):
    from ginkgo.data.operations.file_crud import get_file_content as func

    return func(*args, **kwargs)


def delete_file(*args, **kwargs):
    from ginkgo.data.operations.file_crud import delete_file as func

    return func(*args, **kwargs)


def delete_files(*args, **kwargs):
    from ginkgo.data.operations.file_crud import delete_files as func

    return func(*args, **kwargs)


# TODO
# Handler CRUD
# TODO
# Param CRUD
def add_param(*args, **kwargs):
    from ginkgo.data.operations.param_crud import add_param as func

    return func(*args, **kwargs)


def get_params(*args, **kwargs):
    from ginkgo.data.operations.param_crud import get_params as func

    df = func(*args, **kwargs)
    if df.shape[0] == 0:
        return []
    df = df.sort_values(by="index")
    return df["value"].values.tolist()


# TODO
# Order CRUD
# TODO
# Order Record CRUD
# TODO
# Portfolio CRUD
def add_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import add_portfolio as func

    return func(*args, **kwargs)


def delete_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import delete_portfolio as func

    return func(*args, **kwargs)


def delete_portfolios(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import delete_portfolios as func

    return func(*args, **kwargs)


def get_portfolio(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import get_portfolio as func

    return func(*args, **kwargs)


def get_portfolios(*args, **kwargs):
    from ginkgo.data.operations.portfolio_crud import get_portfolios as func

    return func(*args, **kwargs)


# Portfolio Handler CRUD
# TODO
# Position CRUD
# TODO
# Position Record CRUD
# TODO
# Signal CRUD
# TODO
# Stock Info CRUD
def upsert_stockinfo(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import upsert_stockinfo as func

    return func(*args, **kwargs)


def get_stockinfos(*args, **kwargs):
    from ginkgo.data.operations.stockinfo_crud import get_stockinfos as func

    return func(*args, **kwargs)


# TODO
# Tick CRUD
def ensure_tick_table(func):
    from ginkgo.data.drivers import create_table
    from ginkgo.data.operations.tick_crud import get_tick_model

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if "code" in kwargs and isinstance(kwargs["code"], str):
                model = get_tick_model(code=kwargs["code"])
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
def get_ticks(*args, **kwargs):
    from ginkgo.data.operations.tick_crud import get_ticks as func

    return func(*args, **kwargs)


@ensure_tick_table
def delete_ticks(*args, **kwargs):
    from ginkgo.data.operations.tick_crud import delete_ticks as func

    return func(*args, **kwargs)


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
