from app.libs.yellowprint import YellowPrint

yp_test = YellowPrint('rp_user', url_prefix='/test')


@yp_test.route('/table')
def table_generation():
    return 'table'


@yp_test.route('/table1')
def table_generation1():
    return 'table1'
