from types import FunctionType, MethodType
import pandas as pd
from enum import Enum


def chinese_count(msg):
    count = 0
    for _char in msg:
        if "\u4e00" <= _char <= "\u9fa5":
            count = count + 1
    return count


def pretty_repr(class_name: str, msg: list, width: int = None):
    """
    Pretty the object print.
    """
    if width:
        row_max = width
    else:
        for i in msg:
            if len(i) > row_max:
                row_max = len(i)
        row_max += 4

    r = ""
    r += "\n"
    r += "-" * (row_max // 2 - len(class_name)) + f" {class_name} "
    r += "-" * (row_max - len(r)) + "+"
    for row in msg:
        r += "\n"
        r += row
        l = row_max - 1 - len(row) - chinese_count(row)
        r += " " * l + "|"
    r += "\n"
    r += "-" * (row_max - 1) + "+"
    r += "\n"

    return r


def base_repr(obj, name, label_len=12, total_len=80, *args, **kwargs):
    methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
    r = []
    count = 12

    if label_len:
        count = label_len

    # MemoryLocation
    mem = " " * (count - len("MEM"))
    mem += "MEM : "
    mem += f"{hex(id(obj))}"
    r.append(mem)

    for param in obj.__dir__():
        if param in methods:
            continue

        if param.startswith("_"):
            continue

        if isinstance(obj.__getattribute__(param), MethodType):
            continue

        if isinstance(obj.__getattribute__(param), FunctionType):
            continue

        tmp = " " * (count - len(str(param)))
        tmp += f"{str(param).upper()}"
        s = obj.__getattribute__(param)
        filter_s = str(s).strip(b"\x00".decode())
        special_ins_param = ["engine", "matchmaking", "datafeeder", "portfolio", "selector", "risk_manager", "sizer"]
        special_list_param = ["portfolios", "strategies", "interested"]
        special_dict_param = ["positions", "analyzers"]
        if isinstance(s, pd.DataFrame):
            filter_s = f"{str(s.shape)}"
        if param in special_ins_param:
            filter_s = f"[{hex(id(s))}] {str(s.name)}" if s is not None else "None"
        if param in special_dict_param:
            filter_s = f"{len(s.keys())}"
        if param in special_list_param:
            filter_s = f"{len(s)}"
        if isinstance(s, Enum):
            filter_s += f" : {s.value}"
        max_len = total_len - count - 6
        l = len(filter_s) + chinese_count(filter_s)
        if l > max_len:
            cc = chinese_count(filter_s)
            end = int(max_len - 3 - cc / 2)
            filter_s = filter_s[:end] + "..."
        tmp += f" : {filter_s}"
        r.append(tmp)

    return pretty_repr(name, r, total_len)


def fix_string_length(s: str, length: int = 10):
    if len(s) > length:
        return s[: length - 3] + "..."
    else:
        return s.ljust(length)
