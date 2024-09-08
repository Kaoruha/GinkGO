import os
import subprocess
import shutil
import sys
import time
import platform
import tempfile
import argparse


def bye():
    print("Bye. Wish to see you soon.")
    sys.exit()


def blin(msg: str):
    return "\033[05m" + msg + "\033[0m"


def lightblue(msg: str):
    return "\033[96m" + msg + "\033[0m"


def blue(msg: str):
    return "\033[94m" + msg + "\033[0m"


def green(msg: str):
    return "\033[92m" + msg + "\033[0m"


def lightyellow(msg: str):
    return "\033[93m" + msg + "\033[0m"


def red(msg: str):
    return "\033[91m" + msg + "\033[0m"


def bg_red(msg: str):
    return "\033[41m" + msg + "\033[0m"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-y", "--y", help="pass yes to all request", action="store_true"
    )
    parser.add_argument(
        "-updateconfig",
        "--updateconfig",
        help="overwrite configuration",
        action="store_true",
    )
    parser.add_argument(
        "-kafkainit",
        "--kafkainit",
        help="reset kafka topic",
        action="store_true",
    )
    parser.add_argument(
        "-bin",
        "--bin",
        help="Build Binary.",
        action="store_true",
    )
    args = parser.parse_args()

    working_directory = os.path.dirname(os.path.abspath(__file__))

    path_log = os.path.expanduser("~") + "/.ginkgo/logs"
    path_db = f"{working_directory}/.db"
    path_pip = f"{working_directory}/requirements.txt"
    path_dockercompose = f"{working_directory}/.conf/docker-compose.yml"
    path_click = f"{working_directory}/.conf/clickhouse_users.xml"
    path_gink_conf = f"{working_directory}/src/ginkgo/config/config.yml"
    path_gink_sec = f"{working_directory}/src/ginkgo/config/secure.backup"

    print("======================================")
    print("Balabala Banner")  # TODO
    print("======================================")

    arch = platform.architecture()[0]
    os_name = platform.system()
    print(f"OS: {platform.system()} {arch}")
    print(platform.platform())
    print(f"CPU Cores: {os.cpu_count()}")

    docker_version = os.system("docker --version")
    compose_version = os.system("docker-compose --version")

    notice_info = "NOTICE"

    # Check Virtual Env
    env = os.environ.get("VIRTUAL_ENV")
    if env is None:
        print(
            f"[{blue(notice_info)}] You should active a {bg_red('virtual enviroment')}"
        )
        msg = f"[{blue(notice_info)}] To active, run: {green('python3 -m virtualenv venv;source venv/bin/activate')}"  # TODO change the command via system
        print(msg)
        bye()

    print(f"Working_directory: {lightblue(working_directory)}")
    print(f"ENV: {lightblue(env)}")
    ver = platform.python_version()
    print(f"Python : {lightblue(ver)}")
    if not args.y:
        input(f"Press {green('ENTER')} to continue")
        print("File Check:")

    if os.path.exists(path_pip):
        msg = f"[{green('CONFIRMED')}] Pip requirements."
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Pip requirements."
        print(msg)

    if os.path.exists(path_dockercompose):
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

    if os.path.exists(path_gink_conf):
        msg = f"[{green('CONFIRMED')}] Ginkgo config file"
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Ginkgo config file"
        print(msg)

    if os.path.exists(path_gink_sec):
        msg = f"[{green('CONFIRMED')}] Ginkgo secure file"
        print(msg)
    else:
        msg = f"[{red(' MISSING ')}] Ginkgo secure file, you need to create your secure.yml refer to README"
        print(msg)

    # Copy the config file

    path = os.path.expanduser("~") + "/.ginkgo"
    if not os.path.exists(path):
        os.makedirs(path)

    # If config file or secure file not exsit.
    if not os.path.exists(os.path.join(path, "config.yml")):
        origin_path = path_gink_conf
        target_path = os.path.join(path, "config.yml")
        shutil.copy(origin_path, target_path)
        print(f"Copy config.yml from {origin_path} to {target_path}")

    if not os.path.exists(os.path.join(path, "secure.yml")):
        origin_path = path_gink_sec
        target_path = os.path.join(path, "secure.yml")
        print(f"Copy secure.yml from {origin_path} to {target_path}")
        shutil.copy(origin_path, target_path)

    # If get the param updateconfig, overwrite the config and secure file by force.

    if args.updateconfig:
        origin_path = path_gink_conf
        target_path = os.path.join(path, "config.yml")
        shutil.copy(origin_path, target_path)
        print(f"Copy config.yml from {origin_path} to {target_path}")
        origin_path = path_gink_sec
        target_path = os.path.join(path, "secure.yml")
        print(f"Copy secure.yml from {origin_path} to {target_path}")
        shutil.copy(origin_path, target_path)

    # Install Ginkgo Package
    os.system("python ./setup_install.py")
    # Write log,unitest,working_directory to local config.
    os.system("pip install pyyaml -i https://pypi.tuna.tsinghua.edu.cn/simple")

    if not args.y:
        result = input("Conitnue? Y/N  ")
        if result.upper() != "Y":
            bye()

    # 安装依赖
    os.system("pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple")
    os.system("pip install wheel --default-timeout=20")
    os.system("pip install wheel -i https://pypi.tuna.tsinghua.edu.cn/simple")
    os.system(
        f"pip install -r {path_pip} --default-timeout=20 -i https://pypi.tuna.tsinghua.edu.cn/simple"
    )

    try:
        from ginkgo.libs.ginkgo_conf import GCONF

        # GCONF.set_logging_path(path_log)
        GCONF.set_work_path(working_directory)
        GCONF.set_unittest_path(working_directory)
        GCONF.set_logging_path(path_log)
    except Exception as e:
        print("Ginkgo not installed. Path setting will work at next installation.")

    # 创建映射文件夹
    if not os.path.exists(path_db):
        os.mkdir(path_db)

    # 创建日志文件夹
    if not os.path.exists(path_log):
        os.mkdir(path_log)

    # 启动Docker
    if "Windows" == str(platform.system()):
        os.system("docker rm -f ginkgo_web")
        os.system("docker rmi ginkgo_webui:latest")
        os.system(
            f"docker compose -p ginkgo -f {path_dockercompose} --compatibility up -d"
        )
    elif "Linux" == str(platform.system()):
        os.system("docker rm -f ginkgo_web")
        os.system("docker rmi ginkgo_webui:latest")
        os.system(
            f"docker compose -p ginkgo -f {path_dockercompose} --compatibility up -d"
        )
    else:
        os.system("docker rm -f ginkgo_web")
        os.system("docker rmi ginkgo_webui:latest")
        os.system(
            f"docker compose -p ginkgo -f {path_dockercompose} --compatibility up -d"
        )

    # Build an executable binary
    if args.bin:
        version_split = ver.split(".")
        version_tag = f"{version_split[0]}.{version_split[1]}"
        cmd = f"pyinstaller --onefile --paths /home/kaoru/Documents/Ginkgo/venv/lib/python{version_tag}/site-packages  main.py -n ginkgo"
        os.system(cmd)

    # Kafka setting
    # Should wait for container up.
    if args.kafkainit:
        from src.ginkgo.libs.ginkgo_thread import GTM
        from src.ginkgo.data.drivers.ginkgo_kafka import kafka_topic_set

        GTM.reset_worker_pool()
        # Kill LiveEngine
        kafka_topic_set()

    # 删除旧的 ginkgo 文件
    print("Clean ginkgo binary.")
    for path in ["/usr/bin/ginkgo", "/usr/local/bin/ginkgo"]:
        try:
            os.system(f"sudo rm {path}")
        except FileNotFoundError:
            pass

    shell_folder = os.path.dirname(os.path.realpath(__file__))
    output_file = "/usr/local/bin/ginkgo"
    script_content = f"""#!/bin/bash

# 检查第一个参数是否为 "serve"，第二个参数是否为 "nohup"
if [ "$1" = "serve" ] && [ "$2" = "nohup" ]; then
    # 如果是，则将 "serve" 命令放入后台运行
    nohup "{shell_folder}/venv/bin/python" "{shell_folder}/main.py" serve >/dev/null 2>&1 &
else
    # 如果不是，则前台运行 ginkgo 命令，并将所有参数传递给前台进程
    "{shell_folder}/venv/bin/python" "{shell_folder}/main.py" "$@"
fi
"""

    with tempfile.NamedTemporaryFile("w", delete=False) as tmp_file:
        tmp_file.write(script_content)
        temp_file_name = tmp_file.name

    # 使用 sudo 命令将临时文件移动到目标目录
    print("copy binary to bin.")
    os.system(f"sudo mv {temp_file_name} {output_file}")

    # 设置文件执行权限
    print("add executable to binary")
    os.system(f"sudo chmod +x {output_file}")
    if os.path.exists(temp_file_name):
        print("remove temp file")
        os.remove(temp_file_name)

    if os_name == "Linux":
        # Remove systemd conf
        print("remove ginkgo.service")
        output_systemd_file = "/etc/systemd/system/ginkgo.service"
        print("Stop ginkgo server")
        os.system("sudo systemctl stop ginkgo")
        print("Disable ginkgo server")
        os.system("sudo systemctl disable ginkgo")
        print("Remove ginkgo server")
        os.system(f"sudo rm {output_systemd_file}")

        # Write service conf
        service_content = f"""
[Unit]
Description=Ginkgo API server, main control and main watchdog

[Service]
Type=forking
User=kaoru
ExecStart=/usr/local/bin/ginkgo serve nohup
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp_service:
            tmp_service.write(service_content)
            temp_service_name = tmp_service.name

        # 使用 sudo 命令将临时文件移动到目标目录
        print("Copy ginkgo.server to systemd")
        os.system(f"sudo mv {temp_service_name} {output_systemd_file}")
        if os.path.exists(temp_service_name):
            print("remove temp ginkgo.server")
            os.remove(temp_service_name)
        print("reload")
        os.system("sudo systemctl daemon-reload")
        print("Start")
        os.system("sudo systemctl start ginkgo.service")
        print("set auto start")
        os.system("sudo systemctl enable ginkgo.service")
    elif os_name == "Darwin":
        print("this is mac, set system server in future")
    elif os_name == "Windows":
        print("this is windows, set system server in future")




if __name__ == "__main__":
    os.system("clear")
    main()
