from app.libs.yellowprint import YellowPrint
from app.data.ip_proxy.proxy_getter import start_thread as proxy_get
from app.data.manager import kill_all_process
from app.data.stock.stock_getter import start_thread as stock_get

yp_spider = YellowPrint('rp_spider', url_prefix='/spider')


@yp_spider.route('/getproxy')
def get_ip_proxy():
    proxy_get()
    return 'Nothing goes wrong!!'


@yp_spider.route('/kill')
def kill_process():
    kill_all_process()
    return 'All processes killed'


@yp_spider.route('/getstock')
def get_stock():
    stock_get()
    return 'OK'
