# 密钥等敏感信息配置
# 开发/生产环境不同的配置
import os

SECRET_KEY = os.urandom(24)

# DATABASE
DATABASE = 'mysql'
DRIVER = 'pymysql'
HOST = '47.102.46.64'
PORT = '3306'
BASENAME = 'myquant'
USERNAME = 'calvin'
PASSWORD = 'qweasd123'

SQLALCHEMY_DATABASE_URI = DATABASE + '+' + DRIVER + '://' + USERNAME + ':' + PASSWORD + '@' + HOST + ':' + PORT + '/' + BASENAME
# SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant'
SQLALCHEMY_TRACK_MODIFICATIONS = True
