from app.libs.yellowprint import YellowPrint

yp_book = YellowPrint('rp_user', url_prefix='/book')


@yp_book.route('/set')
def set_book():
    return 'this is set book page'


@yp_book.route('/get')
def get_book():
    return 'this is get book page'
