from app.libs.yellowprint import YellowPrint
from flask import request, json
from app.ip_proxy.proxy_getter import start_thread
from app.ip_proxy.ip_proxy import kill_all_process


yp_spider = YellowPrint('rp_spider', url_prefix='/spider')


@yp_spider.route('/getproxy')
def get_ip_proxy():
    start_thread()
    return 'Nothing goes wrong!!'

@yp_spider.route('/kill')
def kill_process():
    kill_all_process()
    return 'All processes killed'



