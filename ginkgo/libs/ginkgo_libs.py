def str2bool(strint: str or int) -> bool:
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
