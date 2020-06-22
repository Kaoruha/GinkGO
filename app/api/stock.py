from app.libs.error import APIException
from app.libs.yellowprint import YellowPrint
from app.data_acquisition.stock.baostock import BaoStock
from flask import request

yp_stock = YellowPrint('rp_stock', url_prefix='/stock')


@yp_stock.route('/get_stock', methods=['GET'])
def get_stock_from_bao():
    code = request.args.get('code')
    start = request.args.get('start')
    end = request.args.get('end')
    frequency = request.args.get('frequency')
    print(code, start, end, frequency)
    t = BaoStock(code=code, start_date=start, end_date=end)
    t.get_last_date()
    return 'OK'


@yp_stock.route('/test', methods=['GET'])
def update_stock_from_bao():
    code = request.args.get('code')
    start = request.args.get('start')
    end = request.args.get('end')
    frequency = request.args.get('frequency')
    print(code, start, end, frequency)
    t = BaoStock(code=code, start_date=start, end_date=end)
    t.up_to_date_minute()
    return 'OK'
