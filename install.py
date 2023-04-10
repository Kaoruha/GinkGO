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
# print("Windows" == str(platform.system()))


# 安装依赖
os.system("pip install -r ./requirements.txt")
os.system("pip install wheel")

# 创建映射文件夹
if not os.path.exists("db"):
    os.mkdir("db")
# 创建日志文件夹
if not os.path.exists("logs"):
    os.mkdir("logs")
# 启动Docker
if "Windows" == str(platform.system()):
    os.system("docker-compose -f config/docker-compose.yml up -d")
elif "Linux" == str(platform.system()):
    os.system("sudo docker-compose -f config/docker-compose.yml up -d")
else:
    os.system("docker-compose -f config/docker-compose.yml up -d")

# os.system("python ./setup_auto.py")
