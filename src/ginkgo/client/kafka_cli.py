import typer
from typing import Optional
from rich.console import Console

app = typer.Typer(
    help=":satellite: Module for [bold medium_spring_green]KAFKA[/]. [grey62]Kafka queue management commands.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def status():
    """:bar_chart: Check Kafka queue status."""
    console.print("[bold blue]:magnifying_glass_tilted_left: Checking Kafka Queue Status...[/]")
    _check_queue_status()


@app.command()
def reset(
    queue_name: Optional[str] = typer.Option(None, help="指定队列名称，为空则重置所有"),
    force: bool = typer.Option(False, "--force", help="强制重置，跳过确认")
):
    """重置Kafka队列状态"""
    console.print("[bold yellow]:arrows_counterclockwise: Resetting Kafka queues...[/]")
    _reset_kafka_queues(queue_name, force)


@app.command()
def purge(
    queue_name: str = typer.Argument(..., help="要清理的队列名称"),
    confirm: bool = typer.Option(False, "--yes", help="跳过确认提示")
):
    """清理指定队列的所有消息"""
    console.print(f"[bold red]🗑️ Purging queue: {queue_name}[/]")
    _purge_queue_messages(queue_name, confirm)


@app.command()
def monitor(
    duration: int = typer.Option(60, help="监控持续时间（秒）"),
    interval: int = typer.Option(5, help="刷新间隔（秒）")
):
    """实时监控Kafka队列状态"""
    console.print(f"[bold blue]:bar_chart: Starting queue monitor for {duration}s...[/]")
    _start_queue_monitor(duration, interval)


@app.command()
def health():
    """执行Kafka队列健康检查"""
    console.print("[bold green]🏥 Running Kafka health check...[/]")
    _run_health_check()


@app.command()
def consumer_groups():
    """列出所有Consumer Groups状态"""
    console.print("[bold cyan]👥 Listing consumer groups...[/]")
    _list_consumer_groups()


@app.command()
def reset_offsets(
    group_id: str = typer.Argument(..., help="Consumer Group ID"),
    strategy: str = typer.Option("earliest", help="重置策略: earliest/latest/specific")
):
    """重置Consumer Group的offset"""
    console.print(f"[bold yellow]:round_pushpin: Resetting offsets for group: {group_id}[/]")
    _reset_consumer_offsets(group_id, strategy)


# ==================== 实际实现函数 ====================

def _check_queue_status():
    """检查队列状态 - 使用KafkaService实现"""
    try:
        from ginkgo.data.containers import container
        from rich.table import Table
        
        # 获取KafkaService实例
        kafka_service = container.kafka_service()
        
        # 获取服务统计信息
        stats = kafka_service.get_service_statistics()
        
        # 创建状态表格
        table = Table(title="Kafka Queue Status")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        
        # 显示连接状态
        kafka_conn = stats.get("kafka_connection", {})
        connection_status = ":white_check_mark: Connected" if kafka_conn.get("connected", False) else ":x: Disconnected"
        table.add_row("Connection Status", str(kafka_conn.get("connected", False)), connection_status)
        
        # 显示Producer状态
        producer_status = ":white_check_mark: Active" if kafka_conn.get("producer_active", False) else ":x: Inactive"
        table.add_row("Producer Status", str(kafka_conn.get("producer_active", False)), producer_status)
        
        # 显示活跃Consumer数量
        active_consumers = kafka_conn.get("active_consumers", 0)
        consumer_status = f":bar_chart: {active_consumers} active"
        table.add_row("Active Consumers", str(active_consumers), consumer_status)
        
        # 显示发送统计
        send_stats = stats.get("send_statistics", {})
        table.add_row("Total Messages Sent", str(send_stats.get("total_sent", 0)), ":outbox_tray:")
        table.add_row("Failed Sends", str(send_stats.get("failed_sends", 0)), ":x:")
        
        # 显示接收统计
        receive_stats = stats.get("receive_statistics", {})
        table.add_row("Total Messages Received", str(receive_stats.get("total_received", 0)), ":inbox_tray:")
        
        # 显示订阅信息
        active_subscriptions = stats.get("active_subscriptions", 0)
        running_consumers = stats.get("running_consumers", 0)
        table.add_row("Active Subscriptions", str(active_subscriptions), "📑")
        table.add_row("Running Consumers", str(running_consumers), "🏃")
        
        console.print(table)
        
        # 显示订阅详情
        subscription_details = stats.get("subscription_details", [])
        if subscription_details:
            detail_table = Table(title="Subscription Details")
            detail_table.add_column("Topic", style="cyan")
            detail_table.add_column("Handler", style="blue")
            detail_table.add_column("Consumer Status", style="green")
            detail_table.add_column("Thread Name", style="yellow")
            
            for sub in subscription_details:
                status = ":green_circle: Running" if sub.get("is_consuming", False) else ":red_circle: Stopped"
                detail_table.add_row(
                    sub.get("topic", "N/A"),
                    ":white_check_mark: Registered" if sub.get("has_handler", False) else ":x: No Handler",
                    status,
                    sub.get("thread_name", "N/A")
                )
            
            console.print(detail_table)
        
        # 执行健康检查
        health = kafka_service.health_check()
        health_status = health.get("status", "unknown")
        health_color = "green" if health_status == "healthy" else "red"
        console.print(f"\n[bold {health_color}]Overall Health: {health_status.upper()}[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error checking queue status: {e}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")


def _reset_kafka_queues(queue_name: Optional[str], force: bool):
    """重置Kafka队列 - 伪函数"""
    # TODO: 实现队列重置
    # - 停止相关Consumer
    # - 清理队列消息
    # - 重置Consumer Group
    # - 清理Redis状态
    pass


def _purge_queue_messages(queue_name: str, confirm: bool):
    """清理队列消息 - 伪函数"""
    # TODO: 实现消息清理
    # - 确认操作
    # - 创建临时Consumer
    # - 快速消费所有消息
    # - 统计清理数量
    pass


def _start_queue_monitor(duration: int, interval: int):
    """启动队列监控 - 使用KafkaService和Rich Live实现"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.libs.core.threading import GinkgoThreadManager
        from rich.live import Live
        from rich.table import Table
        from rich.layout import Layout
        from rich.panel import Panel
        import time
        import signal
        import sys
        
        console.print(f"[bold blue]:bar_chart: Starting real-time queue monitor...[/]")
        console.print(f"[blue]Duration: {duration}s, Refresh interval: {interval}s[/]")
        console.print("[yellow]Press Ctrl+C to stop monitoring[/]")
        
        # 获取服务实例
        kafka_service = container.kafka_service()
        gtm = GinkgoThreadManager()
        
        start_time = time.time()
        interrupt_count = 0
        
        def signal_handler(signum, frame):
            nonlocal interrupt_count
            interrupt_count += 1
            if interrupt_count >= 2:
                console.print("\n[bold red]Force stopping monitor...[/]")
                sys.exit(0)
            else:
                console.print(f"\n[yellow]Press Ctrl+C again to force stop (1/2)[/]")
        
        signal.signal(signal.SIGINT, signal_handler)
        
        def create_monitor_layout():
            """创建监控界面布局"""
            # Kafka状态表
            kafka_table = Table(title="Kafka Service Status", expand=True)
            kafka_table.add_column("Metric", style="cyan")
            kafka_table.add_column("Value", style="green")
            
            try:
                stats = kafka_service.get_service_statistics()
                kafka_conn = stats.get("kafka_connection", {})
                send_stats = stats.get("send_statistics", {})
                receive_stats = stats.get("receive_statistics", {})
                
                kafka_table.add_row("Connection", ":white_check_mark: Connected" if kafka_conn.get("connected") else ":x: Disconnected")
                kafka_table.add_row("Active Consumers", str(kafka_conn.get("active_consumers", 0)))
                kafka_table.add_row("Subscriptions", str(stats.get("active_subscriptions", 0)))
                kafka_table.add_row("Messages Sent", str(send_stats.get("total_sent", 0)))
                kafka_table.add_row("Messages Received", str(receive_stats.get("total_received", 0)))
                kafka_table.add_row("Failed Sends", str(send_stats.get("failed_sends", 0)))
                
            except Exception as e:
                kafka_table.add_row("Status", f":x: Error: {str(e)[:40]}...")
            
            # Worker状态表
            worker_table = Table(title="Worker Pool Status", expand=True)
            worker_table.add_column("Metric", style="cyan")
            worker_table.add_column("Value", style="green")
            
            try:
                worker_count = gtm.get_worker_count()
                workers_status = gtm.get_workers_status()
                
                status_counts = {}
                for status_info in workers_status.values():
                    status = status_info.get("status", "UNKNOWN")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                worker_table.add_row("Total Workers", str(worker_count))
                for status, count in status_counts.items():
                    worker_table.add_row(f"{status} Workers", str(count))
                    
            except Exception as e:
                worker_table.add_row("Status", f":x: Error: {str(e)[:40]}...")
            
            # 订阅详情表
            subscription_table = Table(title="Active Subscriptions", expand=True)
            subscription_table.add_column("Topic", style="cyan")
            subscription_table.add_column("Status", style="green")
            subscription_table.add_column("Thread", style="yellow")
            
            try:
                stats = kafka_service.get_service_statistics()
                subscription_details = stats.get("subscription_details", [])
                
                if subscription_details:
                    for sub in subscription_details:
                        status = ":green_circle: Running" if sub.get("is_consuming") else ":red_circle: Stopped"
                        subscription_table.add_row(
                            sub.get("topic", "N/A"),
                            status,
                            sub.get("thread_name", "N/A")
                        )
                else:
                    subscription_table.add_row("No subscriptions", "N/A", "N/A")
                    
            except Exception as e:
                subscription_table.add_row("Error", f"{str(e)[:30]}...", "N/A")
            
            # 创建布局
            layout = Layout()
            layout.split_column(
                Layout(kafka_table, name="kafka"),
                Layout(worker_table, name="worker"),
                Layout(subscription_table, name="subscriptions")
            )
            
            # 添加时间信息
            elapsed = time.time() - start_time
            remaining = max(0, duration - elapsed)
            time_info = f"Elapsed: {elapsed:.1f}s | Remaining: {remaining:.1f}s | Refresh: {interval}s"
            
            return Panel(layout, title=f"Kafka Queue Monitor - {time_info}", border_style="blue")
        
        # 开始监控
        with Live(create_monitor_layout(), refresh_per_second=1/interval, console=console) as live:
            try:
                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= duration:
                        break
                    
                    # 更新显示
                    live.update(create_monitor_layout())
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                pass
        
        console.print(f"\n[bold green]:white_check_mark: Queue monitoring completed after {time.time() - start_time:.1f} seconds[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error starting queue monitor: {e}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")


def _run_health_check():
    """运行健康检查 - 使用KafkaService实现"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.libs.core.threading import GinkgoThreadManager
        from rich.table import Table
        import time
        
        console.print("[bold blue]:magnifying_glass_tilted_left: Running comprehensive health check...[/]")
        
        # 创建健康检查结果表
        health_table = Table(title="System Health Check Results")
        health_table.add_column("Component", style="cyan", no_wrap=True)
        health_table.add_column("Status", style="green")
        health_table.add_column("Details", style="yellow")
        
        overall_healthy = True
        
        # 1. Kafka Service检查
        try:
            kafka_service = container.kafka_service()
            kafka_health = kafka_service.health_check()
            kafka_status = kafka_health.get("status", "unknown")
            
            if kafka_status == "healthy":
                health_table.add_row("Kafka Service", ":white_check_mark: Healthy", f"Connected: {kafka_health.get('kafka_connection', False)}")
            else:
                health_table.add_row("Kafka Service", ":x: Unhealthy", f"Status: {kafka_status}")
                overall_healthy = False
                
        except Exception as e:
            health_table.add_row("Kafka Service", ":x: Error", f"Exception: {str(e)[:50]}...")
            overall_healthy = False
        
        # 2. Redis连接检查
        try:
            redis_service = container.redis_service()
            redis_info = redis_service.get_redis_info()
            
            if redis_info.get("connected", False):
                version = redis_info.get("version", "Unknown")
                health_table.add_row("Redis Service", ":white_check_mark: Healthy", f"Version: {version}")
            else:
                health_table.add_row("Redis Service", ":x: Disconnected", redis_info.get("error", "Unknown error"))
                overall_healthy = False
                
        except Exception as e:
            health_table.add_row("Redis Service", ":x: Error", f"Exception: {str(e)[:50]}...")
            overall_healthy = False
        
        # 3. Worker状态检查
        try:
            gtm = GinkgoThreadManager()
            worker_count = gtm.get_worker_count()
            workers_status = gtm.get_workers_status()
            
            running_workers = sum(1 for status in workers_status.values() if status.get("status") == "RUNNING")
            idle_workers = sum(1 for status in workers_status.values() if status.get("status") == "IDLE")
            error_workers = sum(1 for status in workers_status.values() if status.get("status") == "ERROR")
            
            if worker_count > 0 and error_workers == 0:
                health_table.add_row("Worker Pool", ":white_check_mark: Healthy", f"Total: {worker_count}, Running: {running_workers}, Idle: {idle_workers}")
            elif worker_count == 0:
                health_table.add_row("Worker Pool", ":warning: No Workers", "No active workers found")
            else:
                health_table.add_row("Worker Pool", ":x: Issues", f"Errors: {error_workers}, Total: {worker_count}")
                overall_healthy = False
                
        except Exception as e:
            health_table.add_row("Worker Pool", ":x: Error", f"Exception: {str(e)[:50]}...")
            overall_healthy = False
        
        # 4. 主题状态检查
        try:
            topics_to_check = ["ginkgo_data_update", "ginkgo_main_control", "notify"]
            healthy_topics = 0
            
            for topic in topics_to_check:
                try:
                    topic_info = kafka_service.get_topic_status(topic)
                    if topic_info.get("exists", False):
                        healthy_topics += 1
                except:
                    pass
            
            if healthy_topics == len(topics_to_check):
                health_table.add_row("Kafka Topics", ":white_check_mark: All Healthy", f"{healthy_topics}/{len(topics_to_check)} topics available")
            else:
                health_table.add_row("Kafka Topics", ":warning: Some Issues", f"{healthy_topics}/{len(topics_to_check)} topics available")
                
        except Exception as e:
            health_table.add_row("Kafka Topics", ":x: Error", f"Exception: {str(e)[:50]}...")
        
        # 显示结果
        console.print(health_table)
        
        # 总体健康状态
        if overall_healthy:
            console.print("\n[bold green]:party_popper: Overall System Health: HEALTHY[/]")
        else:
            console.print("\n[bold red]:warning: Overall System Health: REQUIRES ATTENTION[/]")
        
        # 提供建议
        console.print("\n[bold blue]:bulb: Health Check Tips:[/]")
        console.print("• Run 'ginkgo kafka status' for detailed Kafka queue information")
        console.print("• Run 'ginkgo worker status' for detailed worker information")
        console.print("• Check logs if any components show errors")
        
    except Exception as e:
        console.print(f"[bold red]Error running health check: {e}[/]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/]")


def _list_consumer_groups():
    """列出Consumer Groups - 伪函数"""
    # TODO: 实现Consumer Groups列表
    # - 获取所有Consumer Groups
    # - 显示状态和lag信息
    # - 格式化表格输出
    pass


def _reset_consumer_offsets(group_id: str, strategy: str):
    """重置Consumer Offsets - 伪函数"""
    # TODO: 实现offset重置
    # - 停止指定Consumer Group
    # - 根据策略重置offset
    # - 验证重置结果
    pass