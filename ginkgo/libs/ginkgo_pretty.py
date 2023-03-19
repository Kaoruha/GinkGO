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
