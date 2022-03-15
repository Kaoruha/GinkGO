'''
Date: 2021-12-23 10:16:23
Author: Suny
LastEditors: Suny
LastEditTime: 2021-12-24 17:14:00
FilePath: \GinkGO\install.py
'''
import os
import sys
import time
import platform

print(sys.platform)
print(platform.system())
print("Windows" == str(platform.system()))

# 创建打包文件夹
if not os.path.exists("dist"):
    os.mkdir("dist")
else:
    # 删除打包文件夹内所有文件
    path = './dist'
    files = os.listdir(path)
    for i in files:
        os.remove(f'{path}/{i}')


# 安装依赖
os.system("pip install -r ./requirements.yml")
os.system("pip install wheel")

# Python库打包
os.system("python setup.py sdist bdist_wheel")

# 创建映射文件夹
if not os.path.exists("mongo"):
    os.mkdir("mongo")
# 创建日志文件夹
if not os.path.exists("logs"):
    os.mkdir("logs")
# 启动Docker
os.system("docker-compose up -d")
