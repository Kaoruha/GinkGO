"""
健康检查工具模块
用于检查各种服务的健康状态和就绪情况
"""

import time
import socket
import subprocess
from typing import Dict, List, Callable, Optional
from rich.console import Console
from rich.emoji import Emoji
from ginkgo.libs import GLOG, GCONF

console = Console()


def check_port_open(host: str, port: int, timeout: int = 5) -> bool:
    """
    检查端口是否开放
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）
        
    Returns:
        bool: 端口是否开放
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        GLOG.DEBUG(f"Port check failed for {host}:{port} - {e}")
        return False


def check_clickhouse_ready(host: str = None, port: int = None, timeout: int = 5) -> bool:
    """
    检查ClickHouse是否就绪
    
    Args:
        host: ClickHouse主机地址（默认从GCONF获取）
        port: ClickHouse HTTP端口（默认从GCONF获取）
        timeout: 超时时间（秒）
        
    Returns:
        bool: ClickHouse是否就绪
    """
    try:
        if host is None:
            host = GCONF.CLICKHOST
        if port is None:
            port = GCONF.CLICKPORT
        
        import requests
        response = requests.get(f"http://{host}:{port}/ping", timeout=timeout)
        return response.status_code == 200 and "Ok" in response.text
    except Exception as e:
        GLOG.DEBUG(f"ClickHouse health check failed: {e}")
        return False


def check_mysql_ready(host: str = None, port: int = None, 
                     user: str = None, password: str = None, 
                     timeout: int = 5) -> bool:
    """
    检查MySQL是否就绪
    
    Args:
        host: MySQL主机地址（默认从GCONF获取）
        port: MySQL端口（默认从GCONF获取）
        user: 用户名（默认从GCONF获取）
        password: 密码（默认从GCONF获取）
        timeout: 超时时间（秒）
        
    Returns:
        bool: MySQL是否就绪
    """
    try:
        if host is None:
            host = GCONF.MYSQLHOST
        if port is None:
            port = int(GCONF.MYSQLPORT)
        if user is None:
            user = GCONF.MYSQLUSER
        if password is None:
            password = GCONF.MYSQLPWD
        
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=timeout,
            ssl_disabled=True
        )
        conn.ping(reconnect=False)
        conn.close()
        return True
    except Exception as e:
        GLOG.DEBUG(f"MySQL health check failed: {e}")
        return False


def check_redis_ready(host: str = None, port: int = None, 
                     password: Optional[str] = None, timeout: int = 5) -> bool:
    """
    检查Redis是否就绪
    
    Args:
        host: Redis主机地址（默认从GCONF获取）
        port: Redis端口（默认从GCONF获取）
        password: Redis密码（可选）
        timeout: 超时时间（秒）
        
    Returns:
        bool: Redis是否就绪
    """
    try:
        if host is None:
            host = GCONF.REDISHOST
        if port is None:
            port = int(GCONF.REDISPORT)
        
        import redis
        r = redis.Redis(
            host=host, 
            port=port, 
            password=password,
            socket_timeout=timeout,
            socket_connect_timeout=timeout
        )
        return r.ping()
    except Exception as e:
        GLOG.DEBUG(f"Redis health check failed: {e}")
        return False


def check_kafka_ready(host: str = None, port: int = None, 
                     container_name: str = "kafka1", timeout: int = 10) -> bool:
    """
    检查Kafka是否就绪
    
    Args:
        host: Kafka主机地址（默认从GCONF获取）
        port: Kafka端口（默认从GCONF获取）
        container_name: Kafka容器名称
        timeout: 超时时间（秒）
        
    Returns:
        bool: Kafka是否就绪
    """
    try:
        if host is None:
            host = GCONF.KAFKAHOST
        if port is None:
            port = int(GCONF.KAFKAPORT)
        
        # 先检查端口
        if not check_port_open(host, port, timeout):
            return False
        
        # 尝试列出topics
        result = subprocess.run([
            "docker", "exec", container_name,
            "kafka-topics.sh",
            "--bootstrap-server", f"{host}:{port}",
            "--list"
        ], capture_output=True, text=True, timeout=timeout)
        
        return result.returncode == 0
    except Exception as e:
        GLOG.DEBUG(f"Kafka health check failed: {e}")
        return False


def check_docker_containers_running(container_names: List[str]) -> Dict[str, bool]:
    """
    检查Docker容器是否在运行
    
    Args:
        container_names: 容器名称列表
        
    Returns:
        Dict[str, bool]: 容器名称和运行状态的映射
    """
    try:
        result = subprocess.run([
            "docker", "ps", "--format", "{{.Names}}"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            GLOG.ERROR("Failed to get docker container list")
            return {name: False for name in container_names}
        
        running_containers = set(result.stdout.strip().split('\n'))
        
        status = {}
        for container in container_names:
            is_running = container in running_containers
            status[container] = is_running
            if is_running:
                GLOG.DEBUG(f"Container {container} is running")
            else:
                GLOG.WARN(f"Container {container} is not running")
        
        return status
        
    except Exception as e:
        GLOG.ERROR(f"Error checking container status: {e}")
        return {name: False for name in container_names}


def wait_for_service(check_func: Callable[[], bool], service_name: str, 
                    max_wait: int = 60, check_interval: int = 3) -> bool:
    """
    等待单个服务就绪
    
    Args:
        check_func: 健康检查函数
        service_name: 服务名称
        max_wait: 最大等待时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        bool: 服务是否就绪
    """
    GLOG.INFO(f"Waiting for {service_name} to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if check_func():
            GLOG.INFO(f"{Emoji('white_check_mark')} {service_name} is ready!")
            return True
        
        elapsed = int(time.time() - start_time)
        GLOG.DEBUG(f"{Emoji('hourglass_not_done')} {service_name} not ready yet... ({elapsed}s/{max_wait}s)")
        time.sleep(check_interval)
    
    GLOG.ERROR(f"{Emoji('cross_mark')} {service_name} failed to become ready within {max_wait} seconds")
    return False


def wait_for_services(services_config: Dict[str, Dict], max_wait: int = 300) -> bool:
    """
    等待多个服务就绪
    
    Args:
        services_config: 服务配置字典，格式：
            {
                "service_name": {
                    "check_function": callable,
                    "required": bool,
                    "timeout": int (optional)
                }
            }
        max_wait: 总的最大等待时间（秒）
        
    Returns:
        bool: 所有必需服务是否就绪
    """
    GLOG.INFO(f"Waiting for {len(services_config)} services to be ready...")
    start_time = time.time()
    
    ready_services = set()
    required_services = {name for name, config in services_config.items() 
                        if config.get('required', True)}
    
    while time.time() - start_time < max_wait:
        all_required_ready = True
        
        for service_name, config in services_config.items():
            if service_name in ready_services:
                continue
                
            check_func = config['check_function']
            service_timeout = config.get('timeout', 5)
            
            try:
                if check_func():
                    GLOG.INFO(f"{Emoji('white_check_mark')} {service_name} is ready")
                    ready_services.add(service_name)
                else:
                    if config.get('required', True):
                        all_required_ready = False
                    
                    elapsed = int(time.time() - start_time)
                    GLOG.DEBUG(f"{Emoji('hourglass_not_done')} Waiting for {service_name}... ({elapsed}s/{max_wait}s)")
                    
            except Exception as e:
                GLOG.ERROR(f"Error checking {service_name}: {e}")
                if config.get('required', True):
                    all_required_ready = False
        
        # 检查是否所有必需服务都就绪
        if required_services.issubset(ready_services):
            GLOG.INFO(f"{Emoji('party_popper')} All required services are ready!")
            return True
        
        time.sleep(3)
    
    # 超时处理
    missing_services = required_services - ready_services
    if missing_services:
        GLOG.ERROR(f"{Emoji('cross_mark')} Timeout waiting for services: {', '.join(missing_services)}")
        return False
    
    return True


def get_ginkgo_services_config() -> Dict[str, Dict]:
    """
    获取Ginkgo项目的默认服务配置
    
    Returns:
        Dict: 服务配置字典
    """
    return {
        "ClickHouse": {
            "check_function": lambda: check_clickhouse_ready(),
            "required": True,
            "timeout": 10
        },
        "MySQL": {
            "check_function": lambda: check_mysql_ready(),
            "required": True,
            "timeout": 10
        },
        "Redis": {
            "check_function": lambda: check_redis_ready(),
            "required": True,
            "timeout": 5
        },
        "Kafka": {
            "check_function": lambda: check_kafka_ready(),
            "required": True,
            "timeout": 15
        }
    }


def wait_for_ginkgo_services(max_wait: int = 300) -> bool:
    """
    等待Ginkgo项目的所有服务就绪
    
    Args:
        max_wait: 最大等待时间（秒）
        
    Returns:
        bool: 所有服务是否就绪
    """
    services_config = get_ginkgo_services_config()
    return wait_for_services(services_config, max_wait)


# 用于install.py的便捷函数
def ensure_services_ready(container_names: List[str] = None, max_wait: int = 300) -> bool:
    """
    确保服务就绪的便捷函数
    
    Args:
        container_names: 需要检查的容器名称列表
        max_wait: 最大等待时间（秒）
        
    Returns:
        bool: 所有服务是否就绪
    """
    if container_names is None:
        container_names = ["kafka1", "kafka2", "kafka3", "clickhouse_master", "mysql_master", "redis_master"]
    
    GLOG.INFO(f"{Emoji('magnifying_glass_tilted_right')} Checking Docker containers...")
    container_status = check_docker_containers_running(container_names)
    
    failed_containers = [name for name, running in container_status.items() if not running]
    if failed_containers:
        GLOG.ERROR(f"{Emoji('cross_mark')} Containers not running: {', '.join(failed_containers)}")
        return False
    
    GLOG.INFO(f"{Emoji('white_check_mark')} All containers are running")
    
    GLOG.INFO(f"{Emoji('magnifying_glass_tilted_right')} Checking service readiness...")
    return wait_for_ginkgo_services(max_wait)