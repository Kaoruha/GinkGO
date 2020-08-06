from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.test.u_backtest import unit_test_backtest, unit_test_feed

yp_test = YellowPrint('rp_test', url_prefix='/test')


# 单元测试
@yp_test.route('/backtest', methods=['POST'])
def backtest():
    print('start backtest!')
    unit_test_backtest()
    return 'Unit_backtest has begun!!!'


@yp_test.route('/backtest_feed', methods=['POST'])
def backtest_feed():
    print('start feed!')
    unit_test_feed()
    return 'Unit_backtest began to feed now!!!'
