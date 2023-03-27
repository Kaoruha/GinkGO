from types import FunctionType, MethodType


def pretty_repr(class_name: str, msg: list, width: int = None):
    """
    Pretty the object print.
    """
    row_max = 10
    if width:
        row_max = width
    else:
        for i in msg:
            if len(i) > row_max:
                row_max = len(i)
        row_max += 4

    r = "-" * (row_max // 2 - len(class_name)) + f" {class_name} "
    r += "-" * (row_max - len(r) - 1) + "+"
    for row in msg:
        r += "\n"
        r += row
        r += " " * (row_max - 1 - len(row)) + "|"
    r += "\n"
    r += "-" * (row_max - 1) + "+"

    return r


def base_repr(obj, name, label_len=12, total_len=80):
    methods = ["delete", "query", "registry", "metadata"]
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

        tmp = " " * (count - len(str(param)))
        tmp += f"{str(param).upper()}"
        s = obj.__getattribute__(param)
        filter_s = str(s).strip(b"\x00".decode())
        tmp += f" : {str(obj.__getattribute__(param))}"
        r.append(tmp)

    return pretty_repr(name, r, total_len)
