import os
import sys
import time
import platform

# ==============================
# Important
# Run this after enter your env.
# ==============================
print("OS: " + sys.platform)
print("OS: " + platform.system())
print("Windows" == str(platform.system()))


# 安装依赖
os.system("pip install -r ./requirements.yml")
os.system("pip install wheel")

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
else:
    os.system("docker-compose up -d")

os.system("python ./setup_auto.py")
