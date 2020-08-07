from flask import request
from ginkgo.libs.response import APIException,NoException
from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.libs.token_auth import auth


yp_user = YellowPrint('rp_user', url_prefix='/user')


@yp_user.route('/register', methods=['POST'])
def user_register():
    # data = request.json
    return NoException(msg='today is good day')


@yp_user.route('/get2')
# @auth.login_required
def get_user():
    return NoException(msg='This is getuser page')


@yp_user.route('/get1')
def get_user1():
    return NoException(msg='This is getuser111 page')
