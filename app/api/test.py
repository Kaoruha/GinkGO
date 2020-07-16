from app.libs.yellowprint import YellowPrint
from app.unit_test.u_backtest import unit_test_backtest

yp_test = YellowPrint('rp_test', url_prefix='/test')


# 单元测试
@yp_test.route('/backtest', methods=['POST'])
def backtest():
    print('start backtest!')
    unit_test_backtest()
    return 'Unit_backtest has begun!!!'
