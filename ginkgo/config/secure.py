# 密钥等敏感信息配置
# 开发/生产环境不同的配置
import os

SECRET_KEY = os.urandom(24)

# DATABASE
DATABASE = "quant"  # Mongo_Docker 中目标存储的数据库名
HOST = "127.0.0.1"  # Mongo_Docker 的地址，目前测试用本地的
PORT = 27017  # Mongo_Docker 暴露的端口号，默认为27017，启动Docker时可以进行端口映射
USERNAME = "ginkgo"
PASSWORD = "caonima123"

# # DATABASE
# DATABASE = 'mysql'
# DRIVER = 'pymysql'
# HOST = '47.102.46.64'
# PORT = '3306'
# BASENAME = 'myquant'
# USERNAME = 'calvin'
# PASSWORD = 'qweasd123'

# SQLALCHEMY_DATABASE_URI = DATABASE + '+' + DRIVER + '://' + USERNAME + ':' + PASSWORD + '@' + HOST + ':' + PORT + '/' + BASENAME
# # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://calvin:qweasd123@47.102.46.64:3306/myquant'
# SQLALCHEMY_TRACK_MODIFICATIONS = True
