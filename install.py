import os
import stat
import subprocess
import shutil
import sys
import time
import platform
import tempfile
import argparse

from pathlib import Path


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


def os_check():
    arch = platform.architecture()[0]
    os_name = platform.system()
    print(f"OS: {platform.system()} {arch}")
    print(platform.platform())
    print(f"CPU Cores: {os.cpu_count()}")


def docker_check():
    docker_version = os.system("docker --version")


def env_check():
    env = os.environ.get("VIRTUAL_ENV")
    conda_env = os.environ.get("CONDA_DEFAULT_ENV")
    notice_info = "NOTICE"
    if env is None and conda_env is None or conda_env == "base":
        print(f"[{blue(notice_info)}] You should active a {bg_red('virtual enviroment')}")
        msg = f"[{blue(notice_info)}] To active, run: {green('python3 -m virtualenv venv;source venv/bin/activate')} or {green('conda create -n ginkgo python=3.12.8; conda activate ginkgo')} "
        print(msg)
        return None
    return env or conda_env


def env_print(working_directory, env, python_version):
    print(f"Working_directory: {lightblue(working_directory)}")
    print(f"ENV: {lightblue(env)}")
    print(f"Python : {lightblue(python_version)}")


def copy_config(path_conf, path_secure, update_config):
    path = os.path.expanduser("~") + "/.ginkgo"
    if not os.path.exists(path):
        os.makedirs(path)

    # If update_config, overwrite the config and secure file by force.
    if update_config:
        origin_path = path_conf
        target_path = os.path.join(path, "config.yml")
        shutil.copy(origin_path, target_path)
        print(f"Copy config.yml from {origin_path} to {target_path}")
        origin_path = path_sec
        target_path = os.path.join(path, "secure.yml")
        print(f"Copy secure.yml from {origin_path} to {target_path}")
        shutil.copy(origin_path, target_path)
    else:
        # If config file or secure file not exsit.
        if not os.path.exists(os.path.join(path, "config.yml")):
            origin_path = path_conf
            target_path = os.path.join(path, "config.yml")
            shutil.copy(origin_path, target_path)
            print(f"Copy config.yml from {origin_path} to {target_path}")
        if not os.path.exists(os.path.join(path, "secure.yml")):
            origin_path = path_secure
            target_path = os.path.join(path, "secure.yml")
            print(f"Copy secure.yml from {origin_path} to {target_path}")
            shutil.copy(origin_path, target_path)


def install_ginkgo():
    # Install Ginkgo Package using modern pip with pyproject.toml
    try:
        print("Installing Ginkgo package in development mode...")
        subprocess.run(["pip", "install", "-e", "."], check=True)
        print("Ginkgo package installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Ginkgo package: {e}")
        print("Trying alternative installation method...")
        subprocess.run(["pip", "install", "setuptools", "wheel"])
        subprocess.run(["pip", "install", "-e", "."])
    
    # Install additional required packages
    subprocess.run(["pip", "install", "pyyaml", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])


def install_dependencies(path_pip):
    # 安装依赖
    source = "https://mirrors.aliyun.com/pypi/simple/"
    command = ["pip", "install", "--upgrade", "pip", "-i", source]
    try:
        subprocess.run(command, check=True)
        print("Pip upgrade success.")
    except Exception as e:
        print(e)
    finally:
        pass

    command = ["pip", "install", "wheel", "--default-timeout=20", "-i", source]
    try:
        subprocess.run(command, check=True)
    except Exception as e:
        print(e)
    finally:
        pass

    command = ["pip", "install", "-r", path_pip, "--default-timeout=20", "-i", source]
    try:
        subprocess.run(command, check=True)
    except Exception as e:
        print(e)
    finally:
        pass


def set_config_path(path_log, working_directory):
    try:
        from src.ginkgo.libs.core.config import GCONF
        
        GCONF.set_logging_path(path_log)
        GCONF.set_work_path(working_directory)
        GCONF.set_unittest_path(working_directory)
        result = subprocess.run(["which", "python"], capture_output=True, text=True)
        python_path = result.stdout.strip()
        GCONF.set_python_path(python_path)
        print("✅ Configuration paths set successfully.")
    except ImportError as e:
        print(f"⚠️  Could not import GCONF: {e}")
        print("📝 Ginkgo package not fully installed yet. Path setting will work after installation.")
    except Exception as e:
        print(f"❌ Error setting configuration paths: {e}")
        print("📝 Configuration will be set on next run.")


def start_docker(path_dockercompose):
    # 启动Docker
    print(f"{lightblue('Starting Docker services...')}")

    if "Windows" == str(platform.system()):
        command = ["docker", "rm", "-f", "ginkgo_web"]
        subprocess.run(command, capture_output=True)
        command = ["docker", "rmi", "-f", "ginkgo_web:latest"]
        subprocess.run(command, capture_output=True)
        result = os.system(f"docker compose -p ginkgo -f {path_dockercompose} --compatibility up -d")
    elif "Linux" == str(platform.system()):
        command = ["docker", "rm", "-f", "ginkgo_web"]
        subprocess.run(command, capture_output=True)
        command = ["docker", "rmi", "-f", "ginkgo_web:latest"]
        subprocess.run(command, capture_output=True)
        result = os.system(f"docker compose -p ginkgo -f {path_dockercompose} --compatibility up -d")

    if result != 0:
        print(f"{red('Docker compose failed to start')}")
        return False

    print(f"{green('Docker containers started, waiting for services to be ready...')}")
    return True


def build_binary(working_path):
    # TODO
    return
    version_split = ver.split(".")
    version_tag = f"{version_split[0]}.{version_split[1]}"
    result = subprocess.run(["which", "python"], capture_output=True, text=True)
    python_path = result.stdout.strip()
    cmd = f"pyinstaller --onefile --paths /home/kaoru/Documents/Ginkgo/venv/lib/python{version_tag}/site-packages  main.py -n ginkgo"  # TODO
    os.system(cmd)


def kafka_reset():
    try:
        from src.ginkgo.libs import GTM
        from src.ginkgo.data.drivers.ginkgo_kafka import kafka_topic_set

        print("kill all workers.")
        GTM.reset_all_workers()
        # Kill LiveEngine
        print("reset kafka topic.")
        kafka_topic_set()
    except ImportError as e:
        print(f"⚠️  Could not import Kafka components: {e}")
        print("📝 Kafka reset will be available after full installation.")


def wait_for_services():
    """等待服务就绪"""
    try:
        from ginkgo.libs import ensure_services_ready

        print(f"{lightblue('Checking service health...')}")

        # 等待服务就绪，最多等待5分钟
        if ensure_services_ready(max_wait=300):
            print(f"{green('All services are ready!')}")
            return True
        else:
            print(f"{red('Some services failed to start properly')}")
            print(f"{lightyellow('You may need to check Docker logs manually')}")
            return False

    except ImportError as e:
        print(f"{lightyellow(f'Health check module not available: {e}')}")
        print(f"{lightyellow('Skipping service health checks.')}")
        return True
    except Exception as e:
        print(f"{red(f'Error during service health check: {e}')}")
        return False


def create_entrypoint():
    # Remove EntryPoint
    print("Clean ginkgo binary.")
    for path in ["/usr/bin/ginkgo", "/usr/local/bin/ginkgo"]:
        if os.path.exists(path):
            command = ["sudo", "rm", path]
            subprocess.run(command, check=True)

    shell_folder = os.path.dirname(os.path.realpath(__file__))
    output_file = "/usr/local/bin/ginkgo"
    result = subprocess.run(["which", "python"], capture_output=True, text=True)
    python_path = result.stdout.strip()
    script_content = f"""#!/bin/bash

# 检查第一个参数是否为 "serve"，第二个参数是否为 "nohup"
if [ "$1" = "serve" ] && [ "$2" = "nohup" ]; then
    # 如果是，则将 "serve" 命令放入后台运行
    nohup "{python_path}" "{shell_folder}/main.py" serve >/dev/null 2>&1 &
else
    # 如果不是，则前台运行 ginkgo 命令，并将所有参数传递给前台进程
    "{python_path}" "{shell_folder}/main.py" "$@"
fi
"""

    with tempfile.NamedTemporaryFile("w", delete=False) as tmp_file:
        tmp_file.write(script_content)
        temp_file_name = tmp_file.name

    # 使用 sudo 命令将临时文件移动到目标目录
    print("copy binary to bin.")
    command = ["sudo", "mv", temp_file_name, output_file]
    subprocess.run(command, check=True)

    # 设置文件执行权限
    print("add executable to binary")
    command = ["sudo", "chmod", "+x", output_file]
    subprocess.run(command, check=True)
    if os.path.exists(temp_file_name):
        print("remove temp file")
        os.remove(temp_file_name)


def set_system_service():
    try:
        from ginkgo.libs.core.config import GCONF
    except ImportError as e:
        print(f"⚠️  Could not import GCONF: {e}")
        print("📝 System service setup will be available after full installation.")
        return

    # TODO uvicorn path need update conda
    os_name = platform.system()
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
        python_path = GCONF.PYTHONPATH
        dir1 = os.path.dirname(python_path)
        uvicorn_path = os.path.join(dir1, "uvicorn")

        # Write service conf
        service_content = f"""
[Unit]
Description=Ginkgo API server, main control and main watchdog

[Service]
Type=simple
User=kaoru
ExecStart={uvicorn_path} main:app --host 0.0.0.0 --port 8000 --app-dir {GCONF.WORKING_PATH}/api --timeout-graceful-shutdown 5
Restart=always
RestartSec=3
WorkingDirectory={GCONF.WORKING_PATH}

[Install]
WantedBy=multi-user.target
"""
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp_service:
            tmp_service.write(service_content)
            temp_service_name = tmp_service.name

        # 使用 sudo 命令将临时文件移动到目标目录
        print("Copy ginkgo.server to systemd")
        subprocess.run(["sudo", "mv", temp_service_name, output_systemd_file])
        if os.path.exists(temp_service_name):
            print("remove temp ginkgo.server")
            os.remove(temp_service_name)
        print("reload")
        subprocess.run(["sudo", "systemctl", "daemon-reload"])
        print("Start")
        subprocess.run(["sudo", "systemctl", "start", "ginkgo.service"])
        print("set auto start")
        subprocess.run(["sudo", "systemctl", "enable", "ginkgo.service"])
    elif os_name == "Darwin":
        print("this is mac, set system server in future")
    elif os_name == "Windows":
        print("this is windows, set system server in future")


def set_jupyterlab_config():
    env = os.environ.get("VIRTUAL_ENV")
    conda_env = os.environ.get("CONDA_PREFIX")
    env_path = env or conda_env
    # 添加到激活脚本中的内容

    if conda_env:
        # Activate Shell
        activate_script_path = os.path.join(conda_env, "etc", "conda", "activate.d", "jupyter.sh")
        Path(activate_script_path).parent.mkdir(parents=True, exist_ok=True)
        Path(activate_script_path).touch(exist_ok=True)
        current_permissions = Path(activate_script_path).stat().st_mode
        Path(activate_script_path).chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # Deactivate Shell
        deactivate_script_path = os.path.join(conda_env, "etc", "conda", "deactivate.d", "jupyter.sh")
        Path(deactivate_script_path).parent.mkdir(parents=True, exist_ok=True)
        Path(deactivate_script_path).touch(exist_ok=True)
        current_permissions = Path(activate_script_path).stat().st_mode
        Path(activate_script_path).chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    else:
        activate_script_path = os.path.join(env_path, "bin", "activate")
        deactivate_script_path = os.path.join(env_path, "bin", "deactivate")

    activate_env_variables = [
        "Custom Jupyter configuration for this VirtualEnv",
        "export JUPYTER_CONFIG_DIR",
        "export JUPYTER_DATA_DIR",
    ]
    # 打开并读取文件内容
    with open(activate_script_path, "r") as file:
        lines = file.readlines()
    # 筛选掉包含 activate_env_variables 中任意一个变量的行
    lines = [line for line in lines if not any(env_var in line for env_var in activate_env_variables)]
    # Add Env set
    lines.append("#! /bin/bash\n")
    lines.append("# Custom Jupyter configuration for this VirtualEnv\n")
    working_directory = os.path.dirname(os.path.abspath(__file__))
    lines.append(f"export JUPYTER_CONFIG_DIR={env_path}/etc/jupyter\n")
    os.environ["JUPYTER_CONFIG_DIR"] = f"{env_path}/etc/jupyter"
    lines.append(f"export JUPYTER_DATA_DIR={env_path}/.local/share/jupyter\n")
    os.environ["JUPYTER_DATA_DIR"] = f"{env_path}/.local/share/jupyter"
    # 写回文件，保存修改后的内容
    with open(activate_script_path, "w") as file:
        file.writelines(lines)

    deactivate_env_variables = ["Unset Jupyter configuration", "unset JUPYTER_CONFIG_DIR", "unset JUPYTER_DATA_DIR"]
    # 打开并读取文件内容
    with open(deactivate_script_path, "r") as file:
        lines = file.readlines()
    # 筛选掉包含 activate_env_variables 中任意一个变量的行
    lines = [line for line in lines if not any(env_var in line for env_var in deactivate_env_variables)]
    # Add Env set
    lines.append("#! /bin/bash\n")
    lines.append("# Unset Jupyter configuration\n")
    lines.append(f"unset JUPYTER_CONFIG_DIR\n")
    lines.append(f"unset JUPYTER_DATA_DIR\n")
    # 写回文件，保存修改后的内容
    with open(deactivate_script_path, "w") as file:
        file.writelines(lines)

    command = f"bash -i -c 'source {activate_script_path} && echo \"Activated virtual environment\"'"
    # os.system(command)
    command = ["jupyter", "lab", "--generate-config"]
    result = subprocess.run(command, check=True)

    jupyter_conf_path = os.path.join(env_path, "etc", "jupyter", "jupyter_lab_config.py")
    with open(jupyter_conf_path, "r") as file:
        lines = file.readlines()
    # Filter Jupyter configuration
    jupyter_conf_filter = ["c.ServerApp.ip", "c.ServerApp.port", "c.ServerApp.open_browser", "c.ServerApp.token"]
    lines = [line for line in lines if not any(env_var in line for env_var in jupyter_conf_filter)]
    lines.append("c.ServerApp.ip = '0.0.0.0'\n")
    lines.append("c.ServerApp.port = 8001\n")
    lines.append("c.ServerApp.open_browser = False\n")
    lines.append("c.ServerApp.token = ''\n")
    # 写回文件，保存修改后的内容
    with open(jupyter_conf_path, "w") as file:
        file.writelines(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--y", help="pass yes to all request", action="store_true")
    parser.add_argument(
        "-updateconfig",
        "--updateconfig",
        help="overwrite configuration",
        action="store_true",
    )
    parser.add_argument(
        "-server",
        "--server",
        help="service installation",
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

    os_check()

    env = env_check()
    if env is None:
        bye()

    env_print(working_directory, env, platform.python_version())

    if not args.y:
        input(f"Press {green('ENTER')} to continue, {lightblue('Ginkgo')} will be build.")
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
        import pdb

        pdb.set_trace()
        print(msg)

    copy_config(path_gink_conf, path_gink_sec, args.updateconfig)

    install_ginkgo()

    if not args.y:
        result = input(
            f"{lightblue('Ginkgo Build Complete')}. Dependencies will be installed. Conitnue? {green('Y')}es/{red('N')}o  "
        )
        if result.upper() != "Y":
            bye()

    install_dependencies(path_pip)

    set_config_path(path_log, working_directory)

    # 创建映射文件夹
    if not os.path.exists(path_db):
        Path(path_db).mkdir(parents=True, exist_ok=True)

    # 创建日志文件夹
    if not os.path.exists(path_log):
        Path(path_log).mkdir(parents=True, exist_ok=True)

    if args.bin:
        build_binary()

    if args.server:
        if start_docker(path_dockercompose):
            # 等待服务就绪
            if wait_for_services():
                set_system_service()
                if args.kafkainit:
                    kafka_reset()
            else:
                print(f"{red('Service startup verification failed, but continuing...')}")
                set_system_service()
                if args.kafkainit:
                    kafka_reset()
        else:
            print(f"{red('Docker startup failed, skipping service setup')}")
            sys.exit(1)
    create_entrypoint()
    set_jupyterlab_config()


if __name__ == "__main__":
    os.system("clear")
    main()
