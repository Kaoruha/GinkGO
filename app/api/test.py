from app.libs.yellowprint import YellowPrint
from app.models.book import Book
from app.models.stock import Stock
from app.models.base import db
import datetime
from flask import request, jsonify, json
from app.libs.error import APIException

yp_test = YellowPrint('rp_user', url_prefix='/test')


@yp_test.route('/create')
def table_generation():
    data = request.get_data()
    json_re = json.loads(data)
    stock = json_re['stock']
    Stock.create_table(stock)
    return 'Nothing goes wrong!!'


@yp_test.route('/add')  # TODO 动态插入数据到不同库,查询的方法没用
def data_insert():
    data = request.get_data()
    json_re = json.loads(data)
    stock = json_re['stock']
    Book.set_base(0)
    with db.auto_commit():
        temp = Book(stock)
        db.session.add(temp)
    return str(datetime.datetime.now())


@yp_test.route('/add2')
def data_insert2():
    data = request.get_data()
    json_re = json.loads(data)
    stock = json_re['stock']
    Book.set_base(1)
    with db.auto_commit():
        temp = Book(stock)
        db.session.add(temp)
    return str(datetime.datetime.now())


@yp_test.route('/filter')
def data_filter():
    Book.set_base(1)
    temp = Book.test()
    print(temp[0])
    return temp[0].name


@yp_test.route('/filter2')
def data_filter2():
    Book.set_base(0)
    temp = Book.test()
    print(temp[0])
    return temp[0].name


@yp_test.route('/table4')
def table_generation4():
    return 'table4444'
