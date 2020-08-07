from ginkgo.libs.yellowprint import YellowPrint
# from ginkgo.data.ip_proxy.proxy_getter import start_thread as proxy_get
from ginkgo.data.data_manager import kill_all_thread

yp_spider = YellowPrint('rp_spider', url_prefix='/spider')


@yp_spider.route('/getproxy')
def get_ip_proxy():
    # proxy_get()
    return 'Nothing goes wrong!!'


@yp_spider.route('/kill')
def kill_thread():
    kill_all_thread()
    return 'All threades killed'
