"""
Author: Kaoru
Date: 2021-12-24 23:46:54
LastEditTime: 2022-03-16 09:07:26
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/install.py
What goes around comes around.
"""
import os
import sys
import time
import platform

# ==============================
# Important
# Run this after enter your env.
# ==============================

print("OS: "+sys.platform)
print("OS: "+platform.system())
print("Windows" == str(platform.system()))

# 创建打包文件夹
if not os.path.exists("dist"):
    os.mkdir("dist")
else:
    # 删除打包文件夹内所有文件
    path = "./dist"
    files = os.listdir(path)
    for i in files:
        os.remove(f"{path}/{i}")


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
if "Windows" == str(platform.system()):
    os.system("docker-compose up -d")
elif "Linux" == str(platform.system()):
    os.system("sudo docker-compose up -d")
