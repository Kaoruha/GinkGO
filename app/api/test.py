from app.libs.yellowprint import YellowPrint
from app.models.stock import Stock
from flask import request, json
from app.models.base import db
from app.ip_proxy import test
import datetime


yp_test = YellowPrint('rp_user', url_prefix='/test')


@yp_test.route('/create')
def table_generation():
    data = request.get_data()
    json_re = json.loads(data)
    stock = json_re['stock']
    Stock.create_table(stock)
    return 'Nothing goes wrong!!'


# TODO 单元测试
@yp_test.route('/add')  # DONE 动态插入数据到不同库,查询的方法没用
def data_insert():
    data = request.get_data()
    json_re = json.loads(data)
    stock = json_re['stock']
    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    Stock.add_msg(stock, time)
    return 'OK'


@yp_test.route('/add2')
def data_insert2():
    data = request.get_data()
    json_re = json.loads(data)
    stock = json_re['stock']
    stock1 = json_re['stock1']
    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msgs = []
    t1 = Stock.generate_record(stock, timestamp=time)
    t2 = Stock.generate_record(stock, timestamp=time + '1')
    msgs.append(t1)
    msgs.append(t2)
    Stock.add_msgs(msgs)
    return 'OK'


@yp_test.route('/getproxy')
def table_generation4():
    print(1)
    test.start_thread()
    return 'ok'
