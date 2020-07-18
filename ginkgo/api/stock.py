from ginkgo.libs.error import APIException
from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.data.stock.baostock import start_update_all_stock,bao_instance,start_update_adjust_factor
from flask import request

yp_stock = YellowPrint('rp_stock', url_prefix='/stock')


@yp_stock.route('/get_stock', methods=['GET'])
def get_stock_from_bao():
    code = request.args.get('code')
    start = request.args.get('start')
    end = request.args.get('end')
    frequency = request.args.get('frequency')
    print(code, start, end, frequency)
    # t = BaoStock(code=code, start_date=start, end_date=end)
    # t.get_last_date()
    return 'OK'


@yp_stock.route('/all_stock', methods=['POST'])
def update_all_stock():
    start_update_all_stock()
    return 'Start Updating Now!!'


@yp_stock.route('/all_stock', methods=['GET'])
def get_update_progress():
    return 'It will return xx% in future.'


@yp_stock.route('/all_stock_code', methods=['POST'])
def get_all_stock_code():
    bao_instance.get_all_stock_code()
    return '开始获取所有股票代码'


@yp_stock.route('/adjust_code', methods=['POST'])
def get_all_adjust_factor():
    start_update_adjust_factor()
    return '开始更新所有股票复权因子'
