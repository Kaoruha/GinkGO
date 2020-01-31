from app.libs.yellowprint import YellowPrint

yp_test = YellowPrint('rp_user', url_prefix='/test')


@yp_test.route('/table')
def table_generation():
    return 'table'


@yp_test.route('/table1')
def table_generation1():
    return 'table11111'


@yp_test.route('/table2')
def table_generation2():
    return 'table22222'


@yp_test.route('/table3')
def table_generation3():
    return 'table3333'


@yp_test.route('/table4')
def table_generation4():
    return 'table4444'
