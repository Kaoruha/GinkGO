import os
import shutil
import sys
import time
import platform
import argparse


def bye():
    print("\n")
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
        "-localserver",
        "--localserver",
        help="install servers local, if False just setup the client.",
        action="store_true",
    )
    args = parser.parse_args()

    wd = os.path.dirname(os.path.abspath(__file__))

    path_log = f"{wd}/.logs"
    path_db = f"{wd}/.db"
    path_pip = "./requirements.txt"
    path_docker = ".conf/docker-compose.yml"
    path_click = ".conf/clickhouse_users.xml"
    path_gink_conf = f"{wd}/src/ginkgo/config/config.yml"
    path_gink_sec = f"{wd}/src/ginkgo/config/secure.yml"

    # TODO Write logpath and workpath to config file

    print("======================================")
    print("Balabala Banner")  # TODO
    print("======================================")

    arch = platform.architecture()[0]
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
    else:
        print(f"CWD: {lightblue(wd)}")
        print(f"ENV: {lightblue(env)}")
        ver = platform.python_version()
        print(f"Python : {lightblue(ver)}")
        if not args.y:
            input(f"Press {green('ENTER')} to continue")

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

        current_path = os.path.abspath(__file__)

        # Copy the config file

        path = os.path.expanduser("~") + "/.ginkgo"
        if not os.path.exists(path):
            os.makedirs(path)

        if args.updateconfig:
            # TODO set the unittest path
            if not os.path.exists(os.path.join(path, "config.yml")):
                origin_path = os.path.join(wd, "src/ginkgo/config/config.yml")
                target_path = os.path.join(path, "config.yml")
                shutil.copy(origin_path, target_path)
                print(f"Copy config.yml from {origin_path} to {target_path}")

            if not os.path.exists(os.path.join(path, "secure.yml")):
                origin_path = os.path.join(wd, "src/ginkgo/config/secure.yml")
                target_path = os.path.join(path, "secure.yml")
                print(f"Copy secure.yml from {origin_path} to {target_path}")
                shutil.copy(origin_path, target_path)

        print("\n")
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

    # 创建映射文件夹
    if not os.path.exists(path_db):
        os.mkdir(path_db)

    # 创建日志文件夹
    if not os.path.exists(path_log):
        os.mkdir(path_log)

    # 启动Docker
    if "Windows" == str(platform.system()):
        os.system(f"docker compose -f {path_docker} --compatibility up -d")
    elif "Linux" == str(platform.system()):
        os.system(f"docker compose -f {path_docker} --compatibility up -d")
    else:
        os.system(f"docker compose -f {path_docker} --compatibility up -d")

    # Install Ginkgo Package
    os.system("python ./setup_install.py")

    # # Build an executable binary
    # version_split = ver.split('.')
    # version_tag = f"{version_split[0]}.{version_split[1]}"
    # cmd = f"pyinstaller --onefile --paths /home/kaoru/Documents/Ginkgo/venv/lib/python{version_tag}/site-packages  main.py -n ginkgo"
    # os.system(cmd)
    from src.ginkgo.libs.ginkgo_conf import GCONF
    GCONF.set_logging_path(path_log)
    GCONF.set_work_path(path)

    print(
        f"You could run : {lightblue('chmod +x ./install.sh;sudo ./install.sh')} to get the cli."
    )


if __name__ == "__main__":
    os.system("clear")
    main()
