import os
import sys
import time
import platform

# ==============================
# Important
# Run this after enter your env.
# ==============================

path_log="logs"
path_db="db"
path_pip="./requirements.txt"
path_docker="config/docker-compose.yml"
path_click="config/clickhouse_users.xml"
path_gink_conf = "ginkgo/config/config.yml"
path_gink_sec = "ginkgo/config/secure.yml"

print("======================================")
print("Balabala Banner")
print("======================================")

arch = platform.architecture()[0]
print(f"OS: {platform.system()} {arch}")
print(platform.platform())
print(f"CPU Cores: {os.cpu_count()}")
# print("Windows" == str(platform.system()))

docker_version = os.system("docker1 --version")
compose_version = os.system("docker-compose --version")

def bye():
    print("Bye. Wish to see you soon.")
    sys.exit()


def blin(msg):
    return "\033[05m"+msg+"\033[0m"

def lightblue(msg):
    return "\033[96m"+msg+"\033[0m"

def blue(msg):
    return "\033[94m"+msg+"\033[0m"

def green(msg):
    return "\033[92m"+msg+"\033[0m"

def lightyellow(msg):
    return "\033[93m"+msg+"\033[0m"

def red(msg):
    return "\033[91m"+msg+"\033[0m"

def bg_red(msg):
    return "\033[41m"+msg+"\033[0m"

notice_info = "NOTICE"

# Check Virtual Env
env = os.environ.get("VIRTUAL_ENV")
if env is None:
    print(f"[{blue(notice_info)}] You should active a {bg_red('virtual enviroment')}")
    msg = f"[{blue(notice_info)}] To active, run: {green('source venv/bin/activate')}" #TODO change the command via system
    print(msg)
    bye()
else:
    wd = os.getcwd()
    print(f"CWD: {lightblue(wd)}")
    print(f"ENV: {lightblue(env)}")
    ver = platform.python_version()
    print(f"Python : {lightblue(ver)}")

    print("File Check:")

    if os.path.exists(path_pip):
        msg = f"[{green('CONFIRMED')}] Pip requirements"
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Pip requirements"
        print(msg)

    if os.path.exists(path_docker):
        msg = f"[{green('CONFIRMED')}] Docker compose file"
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Docker Compose file"
        print(msg)

    if os.path.exists(path_click):
        msg = f"[{green('CONFIRMED')}] Clickhouse config file"
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Clickhouse config file"
        print(msg)

    if os.path.exists(path_gink_conf) and os.path.exists(path_gink_sec):
        msg = f"[{green('CONFIRMED')}] Ginkgo config file"
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Ginkgo config file"
        print(msg)


    print("\n")
    result = input("Conitnue? Y/N  ")
    if result.upper() != "Y":
        bye()

# 安装依赖
os.system("pip install wheel")
os.system(f"pip install -r {path_pip}")

# 创建映射文件夹
if not os.path.exists(path_db):
    os.mkdir(path_db)
# 创建日志文件夹
if not os.path.exists(path_log):
    os.mkdir(path_log)
# 启动Docker
if "Windows" == str(platform.system()):
    os.system(f"docker-compose -f {path_docker} up -d")
elif "Linux" == str(platform.system()):
    os.system(f"sudo docker-compose -f {path_docker} up -d")
else:
    os.system(f"docker-compose -f {path_docker} up -d")

# os.system("python ./setup_auto.py")
