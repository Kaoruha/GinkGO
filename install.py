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


def get_venv_path():
    ginkgo_dir = os.environ.get("GINKGO_DIR", os.path.expanduser("~/.ginkgo"))
    return os.path.join(ginkgo_dir, ".venv")


def check_uv_available():
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except FileNotFoundError:
        return False


def activate_venv(venv_path):
    """在当前进程中激活 venv（等价于 source activate）"""
    os.environ["VIRTUAL_ENV"] = venv_path
    os.environ["UV_ACTIVE_ENV"] = venv_path
    bin_dir = os.path.join(venv_path, "bin")
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    if os.name == "nt":
        bin_dir = os.path.join(venv_path, "Scripts")
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    for p in Path(venv_path).glob("lib/python*/site-packages"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


def env_check():
    venv_path = get_venv_path()

    if not check_uv_available():
        print(f"[{red('ERROR')}] uv is required but not found.")
        print(f"  Install: {green('curl -LsSf https://astral.sh/uv/install.sh | sh')}")
        return None

    active_env = os.environ.get("VIRTUAL_ENV") or os.environ.get("UV_ACTIVE_ENV")

    if active_env:
        if os.path.normpath(active_env) == os.path.normpath(venv_path):
            print(f"[{green('ACTIVE')}] UV env: {lightblue(venv_path)}")
            return venv_path
        else:
            print(f"[{lightyellow('WARN')}] Active env {lightblue(active_env)} != expected {lightblue(venv_path)}")
            return active_env

    if not os.path.exists(os.path.join(venv_path, "pyvenv.cfg")):
        print(f"[{green('CREATE')}] Creating venv at {lightblue(venv_path)}...")
        subprocess.run(["uv", "venv", venv_path, "--python", "3.12.8"], check=True)
    else:
        print(f"[{green('REUSE')}] Found existing venv at {lightblue(venv_path)}")

    activate_venv(venv_path)
    return venv_path


def env_print(working_directory, env, python_version):
    print(f"Working_directory: {lightblue(working_directory)}")
    print(f"ENV: {lightblue(env)}")
    print(f"Python : {lightblue(python_version)}")

    # Show package manager info
    package_manager = get_package_manager()
    env_type = "Unknown"

    if is_uv_environment():
        env_type = "UV Virtual Environment"
    elif os.environ.get("CONDA_DEFAULT_ENV"):
        env_type = "Conda Environment"
    elif os.environ.get("VIRTUAL_ENV"):
        env_type = "Virtual Environment (venv)"

    print(f"Environment Type: {lightblue(env_type)}")
    print(f"Package Manager: {lightblue(package_manager.upper())}")


def copy_config(path_conf, path_secure, update_config):
    path = os.path.expanduser("~") + "/.ginkgo"
    working_directory = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(path):
        os.makedirs(path)

    # If update_config, overwrite the config and secure file by force.
    if update_config:
        origin_path = path_conf
        target_path = os.path.join(path, "config.yml")
        shutil.copy(origin_path, target_path)
        print(f"Copy config.yml from {origin_path} to {target_path}")
        origin_path = path_secure
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

    # Copy task_timer.yml (always copy if not exists)
    path_task_timer = f"{working_directory}/src/ginkgo/config/task_timer.yml"
    if os.path.exists(path_task_timer):
        target_path = os.path.join(path, "task_timer.yml")
        if not os.path.exists(target_path):
            shutil.copy(path_task_timer, target_path)
            print(f"Copy task_timer.yml from {path_task_timer} to {target_path}")
        else:
            print(f"task_timer.yml already exists at {target_path}, skipping copy")
    else:
        print(f"[WARNING] task_timer.yml template not found at {path_task_timer}")


def is_uv_environment():
    return check_uv_available()


def write_client_config(ginkgo_dir, api_host, api_port="8000", api_tls=False):
    """写 client 版 config.yml（mode:client + 控制面 API 设置）（ADR-024 §4 混合架构）。

    client 仍装引擎（支持默认本地 ``backtest run``），数据面 DB 端点写进 secure.yml
    （见 ``write_client_secure``）。此处 config.yml 只承载模式 + 控制面 API；
    ``api_host``/``api_port``/``api_tls`` 经 GCONF 的 ``_get_config`` 读取生效。
    """
    import yaml

    if not os.path.exists(ginkgo_dir):
        os.makedirs(ginkgo_dir)
    config_path = os.path.join(ginkgo_dir, "config.yml")
    # 已存在则跳过（与 write_client_secure 对称）：保护用户安装后用 ``ginkgo config set`` 改过的
    # api_host/port（重跑 install 不应回退到安装期占位值）。要重新指向 server 用 config set。
    if os.path.exists(config_path):
        print(f"[{lightyellow('SKIP')}] config.yml already exists at {lightblue(config_path)} (preserving existing mode + API settings)")
        print(f"       To repoint server: {green('ginkgo config set api_host <host>')} / {green('ginkgo config set api_port <port>')}")
        return config_path
    config = {
        "mode": "client",
        "api_host": str(api_host),
        "api_port": str(api_port),
        "api_tls": str(bool(api_tls)).lower(),
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    scheme = "https" if api_tls else "http"
    print(f"[{green('CLIENT')}] Wrote client config to {lightblue(config_path)}")
    print(f"  mode: {green('client')}  (engine installed; data plane → server DB, control plane → server API)")
    print(f"  api:  {lightblue(f'{scheme}://{api_host}:{api_port}')}")
    print(f"  Next: {green('ginkgo user login')}  (modify later: {green('ginkgo config set api_host <host>')})")
    return config_path


def prompt_client_api(args):
    """交互式问 server（A）地址：api_host/port/tls（ADR-024 §4 混合架构）。

    A 的 API host 与 DB host 是同一台机，故 api_host 同时作数据面 DB 与控制面 API 的端点。
    非交互（``-y``）或命令行已传值时跳过提示，直接用传入值/默认占位符。
    """
    # host
    if args.api_host:
        api_host = args.api_host
    elif args.y:
        api_host = "localhost"  # 占位符，装完 config set 改
    else:
        raw = input(f"{lightblue('Ginkgo API host')} [{green('localhost')}] (enter=use default): ").strip()
        api_host = raw or "localhost"
    # port
    if args.api_port:
        api_port = args.api_port
    elif args.y:
        api_port = "8000"
    else:
        raw = input(f"{lightblue('Ginkgo API port')} [{green('8000')}] (enter=use default): ").strip()
        api_port = raw or "8000"
    # tls
    if args.api_tls:
        api_tls = True
    elif args.y:
        api_tls = False
    else:
        raw = input(f"{lightblue('Use TLS?')} [{green('n')}] (y/n, enter=n): ").strip().lower()
        api_tls = raw in ("y", "yes", "true", "1")
    return api_host, api_port, api_tls


def write_client_secure(ginkgo_dir, db_host, path_secure_template):
    """写 client 版 secure.yml：从 secure.template 拷贝，把数据面 DB host 指向 server（A）。

    ADR-024 §4 混合架构：client 的引擎数据面直连 server DB（``MYSQLHOST``/``CLICKHOST`` 等
    由 ``_ensure_env_vars`` 从 secure.yml 的 ``database.<engine>.host`` 烘焙成 env），故 DB host
    须指向 A（= api_host）。DB 凭据复用 A 的共享账号（"无专门 db 账号"），模板占位，
    装完用 ``ginkgo config set`` 填 A 的真实凭据。已存在 secure.yml 则跳过（保护已填凭据）。
    """
    import yaml

    secure_path = os.path.join(ginkgo_dir, "secure.yml")
    if os.path.exists(secure_path):
        print(f"[{lightyellow('SKIP')}] secure.yml already exists at {lightblue(secure_path)} (preserving existing DB creds)")
        print(f"       If server address changed, repoint {lightblue('database.*.host')} there to {green(db_host)}")
        return secure_path
    if not os.path.exists(path_secure_template):
        print(f"[{red(' MISSING ')}] Source secure template not found at {path_secure_template}")
        return None
    with open(path_secure_template) as f:
        secure = yaml.safe_load(f) or {}
    # 数据面 DB host 全部指向 server（A）
    db = secure.get("database", {})
    if isinstance(db, dict):
        for engine in ("clickhouse", "mysql", "mongodb", "redis", "kafka"):
            if isinstance(db.get(engine), dict):
                db[engine]["host"] = str(db_host)
    with open(secure_path, "w") as f:
        yaml.safe_dump(secure, f, default_flow_style=False, sort_keys=False)
    print(f"[{green('CLIENT')}] Wrote client secure.yml to {lightblue(secure_path)}")
    print(f"  DB hosts → {green(db_host)}  (data plane: engine reads/writes server DB directly)")
    print(f"  Next: set A's shared DB creds via {green('ginkgo config set')} (template placeholders need replacing)")
    return secure_path
def get_package_manager():
    return "uv"


def install_ginkgo():
    venv_path = get_venv_path()
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = venv_path
    try:
        print(f"Installing Ginkgo package in development mode using uv...")
        subprocess.run(["uv", "sync"], env=env, check=True)
        print("Ginkgo package installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Ginkgo package: {e}")
        print("Trying uv lock + sync...")
        subprocess.run(["uv", "lock"], env=env)
        subprocess.run(["uv", "sync"], env=env)


def install_dependencies(path_pip):
    venv_path = get_venv_path()
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = venv_path
    print("Installing dependencies using UV...")
    try:
        subprocess.run(["uv", "sync"], env=env, check=True)
        print("Dependencies installation success via UV.")
    except Exception as e:
        print(f"Failed to install dependencies via UV: {e}")
        sys.exit(1)


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


def start_docker(path_dockercompose, execution_nodes=1, data_workers=1):
    """
    启动Docker服务

    Args:
        path_dockercompose: docker-compose.yml 文件路径
        execution_nodes: ExecutionNode 副本数量（默认: 2）
        data_workers: DataWorker 副本数量（默认: 4）
    """
    # 启动Docker
    print(f"{lightblue('Starting Docker services...')}")
    print(f"{lightblue(f'ExecutionNode: {execution_nodes} replicas, DataWorker: {data_workers} replicas')}")

    # 清理旧的 scale 容器（避免命名不一致）
    print(f"{lightyellow('Cleaning up old scaled containers...')}")
    os.system("docker rm -f ginkgo_data_worker_1 ginkgo-data-worker-1 ginkgo-data-worker-2 ginkgo-data-worker-3 ginkgo-data-worker-4 2>/dev/null")
    os.system("docker rm -f ginkgo_execution_node_1 ginkgo-execution-node-1 ginkgo-execution-node-2 2>/dev/null")

    if "Windows" == str(platform.system()):
        command = ["docker", "rm", "-f", "ginkgo_web"]
        subprocess.run(command, capture_output=True)
        command = ["docker", "rmi", "-f", "ginkgo_web:latest"]
        subprocess.run(command, capture_output=True)
        # 一次性启动所有服务并指定 scale 数量
        print(f"{lightblue(f'Scaling execution-node to {execution_nodes} replicas...')}")
        print(f"{lightblue(f'Scaling data-worker to {data_workers} replicas...')}")
        result = os.system(f"docker compose -p ginkgo -f {path_dockercompose} up -d --build --force-recreate --scale execution-node={execution_nodes} --scale data-worker={data_workers}")
    elif "Linux" == str(platform.system()):
        command = ["docker", "rm", "-f", "ginkgo_web"]
        subprocess.run(command, capture_output=True)
        command = ["docker", "rmi", "-f", "ginkgo_web:latest"]
        subprocess.run(command, capture_output=True)
        # 一次性启动所有服务并指定 scale 数量
        print(f"{lightblue(f'Scaling execution-node to {execution_nodes} replicas...')}")
        print(f"{lightblue(f'Scaling data-worker to {data_workers} replicas...')}")
        result = os.system(f"docker compose -p ginkgo -f {path_dockercompose} up -d --build --force-recreate --scale execution-node={execution_nodes} --scale data-worker={data_workers}")

    if result != 0:
        print(f"{red('Docker compose failed to start')}")
        return False

    print(f"{green('Docker containers started, waiting for services to be ready...')}")
    # 显示副本信息（使用 Docker Compose 自动生成的命名格式）
    if execution_nodes > 0:
        exec_list = ", ".join([f"ginkgo-execution-node-{i+1}" for i in range(min(execution_nodes, 4))])
        if execution_nodes > 4:
            exec_list += ", ..."
        print(f"{green(f'ExecutionNode: {execution_nodes} replicas')}")
        print(f"{green(f'  → {exec_list}')}")
    if data_workers > 0:
        worker_list = ", ".join([f"ginkgo-data-worker-{i+1}" for i in range(min(data_workers, 4))])
        if data_workers > 4:
            worker_list += ", ..."
        print(f"{green(f'DataWorker: {data_workers} replicas')}")
        print(f"{green(f'  → {worker_list}')}")
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
    """
    重置 Kafka Topics

    需要 Kafka 服务正在运行。如果 Kafka 不可用，会给出提示并跳过。
    """
    try:
        from src.ginkgo.libs import GTM
        from src.ginkgo.data.drivers.ginkgo_kafka import kafka_topic_set
        from kafka.errors import NoBrokersAvailable, KafkaConnectionError

        print("kill all workers.")
        try:
            GTM.reset_all_workers()
        except Exception as e:
            print(f"{lightyellow('Warning: Could not reset workers')}: {e}")

        # 重置 Kafka Topics
        print("reset kafka topic.")
        try:
            kafka_topic_set()
            print(f"{green('Kafka topics reset successfully!')}")
        except NoBrokersAvailable:
            print(f"{red('Kafka broker not available')}")
            print(f"{lightyellow('Please ensure Kafka containers are running:')}")
            print(f"  docker compose -p ginkgo ps")
            print(f"{lightyellow('Start Kafka services if needed:')}")
            print(f"  docker compose -p ginkgo up -d kafka1 kafka2 kafka3")
            return False
        except KafkaConnectionError as e:
            print(f"{red('Kafka connection failed')}: {e}")
            print(f"{lightyellow('Please check Kafka container status and logs:')}")
            print(f"  docker compose -p ginkgo logs kafka1")
            return False
        except Exception as e:
            print(f"{red('Kafka reset failed')}: {e}")
            return False

    except ImportError as e:
        print(f"⚠️  Could not import Kafka components: {e}")
        print("📝 Kafka reset will be available after full installation.")
        return False

    return True


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
    print("Install ginkgo binary.")
    # 清理旧位置
    for path in ["/usr/bin/ginkgo", "/usr/local/bin/ginkgo"]:
        if os.path.exists(path):
            subprocess.run(["sudo", "rm", path], check=True)

    shell_folder = os.path.dirname(os.path.realpath(__file__))
    bin_dir = os.path.expanduser("~/.local/bin")
    output_file = os.path.join(bin_dir, "ginkgo")
    os.makedirs(bin_dir, exist_ok=True)

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

    with open(output_file, "w") as f:
        f.write(script_content)
    os.chmod(output_file, 0o755)


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

        # 确保deactivate脚本存在
        if not os.path.exists(deactivate_script_path):
            # 创建基本的deactivate脚本
            Path(deactivate_script_path).parent.mkdir(parents=True, exist_ok=True)
            with open(deactivate_script_path, "w") as f:
                f.write("#!/bin/bash\n# deactivate script\n")
            # 设置执行权限
            current_permissions = Path(deactivate_script_path).stat().st_mode
            Path(deactivate_script_path).chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

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

    # 检查deactivate脚本是否存在，如果不存在则创建
    lines = []
    if os.path.exists(deactivate_script_path):
        # 打开并读取文件内容
        with open(deactivate_script_path, "r") as file:
            lines = file.readlines()
        # 筛选掉包含 deactivate_env_variables 中任意一个变量的行
        lines = [line for line in lines if not any(env_var in line for env_var in deactivate_env_variables)]
    else:
        # 如果文件不存在，创建基础内容
        lines = []

    # Add jupyter deactivation configuration
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
    parser.add_argument(
        "-en",
        "--execution-nodes",
        help="Number of ExecutionNode replicas (default: 1)",
        type=int,
        default=1,
    )
    parser.add_argument(
        "-dw",
        "--data-workers",
        help="Number of DataWorker replicas (default: 1)",
        type=int,
        default=1,
    )
    # ADR-024 client 模式 API 设置（默认无 --server = client；非交互或脚本化安装可直传）
    parser.add_argument(
        "-api-host",
        "--api-host",
        help="Remote Ginkgo API host (client mode, default localhost)",
        default=None,
    )
    parser.add_argument(
        "-api-port",
        "--api-port",
        help="Remote Ginkgo API port (client mode, default 8000)",
        default=None,
    )
    parser.add_argument(
        "-api-tls",
        "--api-tls",
        help="Remote Ginkgo API use TLS (client mode)",
        action="store_true",
    )
    args = parser.parse_args()

    working_directory = os.path.dirname(os.path.abspath(__file__))

    ginkgo_dir = os.environ.get("GINKGO_DIR", os.path.expanduser("~/.ginkgo"))
    path_log = os.path.join(ginkgo_dir, "logs")
    path_db = f"{working_directory}/.db"
    path_pip = f"{working_directory}/requirements.txt"
    path_dockercompose = f"{working_directory}/docker-compose.yml"
    path_click = f"{working_directory}/.conf/clickhouse_users.xml"
    path_gink_conf = f"{working_directory}/src/ginkgo/config/config.yml"
    path_gink_sec = f"{working_directory}/src/ginkgo/config/secure.template"

    print("======================================")
    print(f"{green('Ginkgo Trading Framework')} Installation Script")
    print(f"{lightblue('Enhanced with UV support for faster dependency management!')}")
    print("======================================")

    os_check()

    env = env_check()
    if env is None:
        bye()

    env_print(working_directory, env, platform.python_version())

    if not args.y:
        input(f"Press {green('ENTER')} to continue, {lightblue('Ginkgo')} will be build.")
        print("File Check:")

    ginkgo_dir = os.environ.get("GINKGO_DIR", os.path.expanduser("~/.ginkgo"))
    ginkgo_config = os.path.join(ginkgo_dir, "config.yml")
    ginkgo_secure = os.path.join(ginkgo_dir, "secure.yml")

    # ADR-024 §4：--server=全量后端（拷 config+secure 起 Docker）；默认=client（装引擎，
    # 不起 Docker/本地 DB；写 client config.yml[mode+api] + secure.yml[DB host→A]）。
    if args.server:
        print(f"[{green('SERVER')}] Full backend install (Docker + config + secure)")
        # 检查 ~/.ginkgo 下配置文件，不存在则从源拷贝
        if not os.path.exists(ginkgo_config) or not os.path.exists(ginkgo_secure):
            print(f"[{lightblue('SETUP')}] Config files not found in {ginkgo_dir}, copying from source...")
            if not os.path.exists(path_gink_conf):
                print(f"[{red(' MISSING ')}] Source config file not found at {path_gink_conf}")
                sys.exit(1)
            if not os.path.exists(path_gink_sec):
                print(f"[{red(' MISSING ')}] Source secure file not found at {path_gink_sec}")
                sys.exit(1)
            copy_config(path_gink_conf, path_gink_sec, args.updateconfig)
        else:
            print(f"[{green('CONFIRMED')}] Config files in {lightblue(ginkgo_dir)}")
    else:
        print(f"[{green('CLIENT')}] Client install (engine installed; no Docker/local backend; data plane → server DB, control plane → server API)")
        api_host, api_port, api_tls = prompt_client_api(args)
        write_client_config(ginkgo_dir, api_host, api_port, api_tls)
        # ADR-024 §4 混合架构：数据面 DB host 指向 server（A），引擎本地跑时直连 A 的库。
        write_client_secure(ginkgo_dir, api_host, path_gink_sec)

    if os.path.exists(path_pip):
        print(f"[{green('CONFIRMED')}] Pip requirements.")
    else:
        print(f"[{red(' MISSING ')}] Pip requirements.")

    if args.server:
        # docker-compose / clickhouse 仅 server 模式需要（client 瘦装无本地后端，缺这些是正常的）
        if os.path.exists(path_dockercompose):
            print(f"[{green('CONFIRMED')}] Docker compose file")
        else:
            print(f"[{red(' MISSING ')}] Docker Compose file")
        if os.path.exists(path_click):
            print(f"[{green('CONFIRMED')}] Clickhouse config file")
        else:
            print(f"[{red(' MISSING ')}] Clickhouse config file")

    install_ginkgo()

    if not args.y:
        result = input(
            f"{lightblue('Ginkgo Build Complete')}. Dependencies will be installed. Conitnue? {green('Y')}es/{red('N')}o  "
        )
        if result.upper() != "Y":
            bye()

    install_dependencies(path_pip)

    set_config_path(path_log, working_directory)

    # 创建映射文件夹（仅 server：Docker 卷挂载点；client 瘦装无本地 DB）
    if args.server and not os.path.exists(path_db):
        Path(path_db).mkdir(parents=True, exist_ok=True)

    # 创建日志文件夹（两种模式都需要日志）
    if not os.path.exists(path_log):
        Path(path_log).mkdir(parents=True, exist_ok=True)

    if args.bin:
        build_binary()

    if args.server:
        if start_docker(path_dockercompose, args.execution_nodes, args.data_workers):
            # 等待服务就绪
            if wait_for_services():
                if args.kafkainit:
                    kafka_reset()
            else:
                print(f"{red('Service startup verification failed, but continuing...')}")
                if args.kafkainit:
                    kafka_reset()
        else:
            print(f"{red('Docker startup failed, skipping service setup')}")
            sys.exit(1)
    create_entrypoint()
    # TODO: Jupyter configuration temporarily disabled
    # set_jupyterlab_config()


if __name__ == "__main__":
    os.system("clear")
    main()
