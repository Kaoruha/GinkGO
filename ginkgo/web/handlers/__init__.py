from ginkgo.util.classes_getter import get_classes
from ginkgo.libs.ginkgo_logger import ginkgo_logger as gl

from ginkgo.web.handlers import engine
from ginkgo.web.handlers import stock
from ginkgo.web.handlers import user
from ginkgo.web.handlers import test


def get_url_patten():
    api_files = [engine, stock, user, test]
    url_list = []
    new_list = []

    for f in api_files:
        handler_list = get_classes(f)
        print(handler_list)

        for handler in handler_list:
            if handler.url_prefix not in url_list:
                new_list.append((str(handler.url_prefix), handler))
                url_list.append(str(handler.url_prefix))
            else:
                gl.error("API的URL有冲突，请检查代码")
    return new_list
