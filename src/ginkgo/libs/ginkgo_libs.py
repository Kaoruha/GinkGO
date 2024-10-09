import threading
import math


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


def run_with_timeout(func, params, timeout: int = None, *args, **kwargs) -> None:
    """
    Run Thread within time limit.
    Args:
        func(Function): target function
        params(tuple): params for function, in the form of a tuple, e.g. ("hello", 10,)
        timeout(int): function timeout, will kill the thread running func
    Returns:
        None
    """

    def has_parameter(function, param_name):
        params = inspect.signature(function).parameters
        return param_name in params

    timeout = 60 if timeout == None else timeout
    flag = threading.Event()
    flag_name = "stop_flag"

    def target():
        if has_parameter(func, flag_name):
            func(*params, stop_flag=flag)
        else:
            print(f"Do not have FLAG:{flag_name}, wont stop with time limit.")
            return

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        flag.set()
        GLOG.DEBUG(f"Func:{func} terminated via TIMEOUT.")
