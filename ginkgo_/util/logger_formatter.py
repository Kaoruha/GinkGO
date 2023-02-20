import tornado.log


class LogFormatter(tornado.log.LogFormatter):
    def __init__(self):
        super(LogFormatter, self).__init__(
            fmt=
            "[%(levelname)s] [%(asctime)s %(filename)s:%(funcName)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")
