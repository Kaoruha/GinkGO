from flask import request

from app.libs.error import APIException
from app.libs.yellowprint import YellowPrint
from app.libs.token_auth import auth

yp_user = YellowPrint('rp_user', url_prefix='/user')


@yp_user.route('/register', methods=['POST'])
def user_register():
    # data = request.json
    return 'today is good day'


@yp_user.route('/get2')
# @auth.login_required
def get_user():
    return 'This is getuser page'


@yp_user.route('/get1')
def get_user1():
    return 'This is getuser111 page'
