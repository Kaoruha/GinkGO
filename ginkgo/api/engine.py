import threading
from ginkgo.libs.thread_manager import thread_manager
from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.libs.response import NoException
from ginkgo.data.data_portal import data_portal
from ginkgo.libs.socket_manager import socket_boost

yp_engine = YellowPrint('rp_engine', url_prefix='/engine')


@yp_engine.route('/boost', methods=['POST'])
def engine_boost():
    print("hh")
    return NoException(msg="1", data={"name":"hha","age":1})