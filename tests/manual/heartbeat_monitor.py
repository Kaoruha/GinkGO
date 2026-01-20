#!/usr/bin/env python3
"""
LiveCore组件心跳监控脚本

监控所有LiveCore组件的心跳状态：
- TaskTimer
- Scheduler
- DataManager
- ExecutionNode

支持两种部署模式：
1. 线程模式（当前）：所有组件在同一进程
2. 微服务模式（未来）：组件独立部署

使用方式:
    python heartbeat_monitor.py

输出示例:
    LiveCore Heartbeat Monitor
    ==========================
    TaskTimer (task_timer_1): ✓ ALIVE
      Host: server-1, PID: 2106650
      Last heartbeat: 2026-01-19T22:15:30, 2s ago
      Jobs: 2
"""

import time
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from redis import Redis
    from ginkgo.libs import GCONF
except ImportError as e:
    print(f"[ERROR] Failed to import: {e}")
    sys.exit(1)


class HeartbeatMonitor:
    """心跳监控器"""

    # 心跳TTL阈值（秒）
    HEARTBEAT_TTL_THRESHOLD = 40  # 比TTL稍长，容忍一些延迟

    def __init__(self):
        """初始化监控器"""
        self.redis_client = self._get_redis_client()

    def _get_redis_client(self) -> Redis:
        """获取Redis客户端"""
        try:
            return Redis(
                host=GCONF.REDISHOST,
                port=GCONF.REDISPORT,
                db=0,
                decode_responses=True
            )
        except Exception as e:
            print(f"[ERROR] Failed to connect to Redis: {e}")
            sys.exit(1)

    def get_all_heartbeats(self) -> dict:
        """
        获取所有组件的心跳状态

        Returns:
            dict: {component_key: {status, last_heartbeat, age, metadata}}
        """
        result = {}

        # 获取所有心跳key
        heartbeat_keys = self.redis_client.keys("heartbeat:*")

        for key in heartbeat_keys:
            try:
                # 获取心跳值
                heartbeat_value = self.redis_client.get(key)

                # 获取TTL
                ttl = self.redis_client.ttl(key)

                # 解析组件信息
                parts = key.split(":")
                if len(parts) >= 3:
                    component_type = parts[1]
                    component_id = parts[2]

                    # 解析心跳数据（支持JSON格式）
                    heartbeat_data = self._parse_heartbeat_data(heartbeat_value)

                    # 计算心跳年龄
                    last_heartbeat = heartbeat_data.get("timestamp")
                    if last_heartbeat:
                        try:
                            dt = datetime.fromisoformat(last_heartbeat)
                            age = (datetime.now() - dt).total_seconds()
                        except:
                            age = None
                    else:
                        age = None

                    # 判断状态
                    is_alive = ttl > 0 and ttl < self.HEARTBEAT_TTL_THRESHOLD

                    result[key] = {
                        "component_type": component_type,
                        "component_id": component_id,
                        "status": "ALIVE" if is_alive else "DEAD",
                        "last_heartbeat": last_heartbeat,
                        "ttl": ttl,
                        "age": age,
                        "metadata": heartbeat_data,
                    }

            except Exception as e:
                print(f"[WARN] Failed to parse heartbeat for {key}: {e}")
                continue

        return result

    def _parse_heartbeat_data(self, heartbeat_value: str) -> dict:
        """
        解析心跳数据

        支持两种格式：
        1. JSON格式（新）：{"timestamp": "...", "host": "...", "pid": ...}
        2. ISO格式（旧）："2026-01-19T22:13:28.017968"

        Returns:
            dict: 解析后的心跳数据
        """
        if not heartbeat_value:
            return {}

        # 尝试解析为JSON
        try:
            return json.loads(heartbeat_value)
        except:
            # 不是JSON，当作ISO格式时间戳处理
            return {"timestamp": heartbeat_value}

    def print_status(self, heartbeats: dict):
        """打印心跳状态"""
        print("\n" + "=" * 60)
        print("LiveCore Heartbeat Monitor")
        print("=" * 60)
        print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if not heartbeats:
            print("No heartbeat data found. Components may not be running.")
            return

        # 按组件类型分组
        grouped = {}
        for key, info in heartbeats.items():
            component_type = info["component_type"]
            if component_type not in grouped:
                grouped[component_type] = []
            grouped[component_type].append(info)

        # 打印状态
        for component_type, components in sorted(grouped.items()):
            print(f"\n{component_type.upper()}:")
            for info in components:
                status_icon = "✓" if info["status"] == "ALIVE" else "✗"
                metadata = info["metadata"]

                # 基本信息
                last_time = metadata.get("timestamp", "N/A")
                if last_time != "N/A":
                    try:
                        dt = datetime.fromisoformat(last_time)
                        last_time = dt.strftime("%H:%M:%S")
                    except:
                        pass

                age_str = f"{info['age']:.1f}s ago" if info["age"] is not None else "N/A"

                print(f"  [{status_icon}] {info['component_id']}: {info['status']}")
                print(f"      Last: {last_time} ({age_str}), TTL: {info['ttl']}s")

                # 额外元数据
                host = metadata.get("host")
                pid = metadata.get("pid")
                if host or pid:
                    host_str = host or "N/A"
                    pid_str = str(pid) if pid else "N/A"
                    print(f"      Host: {host_str}, PID: {pid_str}")

                # 组件特定信息
                if "jobs_count" in metadata:
                    print(f"      Jobs: {metadata['jobs_count']}")

        # 统计
        alive_count = sum(1 for h in heartbeats.values() if h["status"] == "ALIVE")
        total_count = len(heartbeats)
        print(f"\nSummary: {alive_count}/{total_count} components alive")

    def watch(self, interval: int = 5):
        """
        持续监控心跳状态

        Args:
            interval: 刷新间隔（秒）
        """
        try:
            print("Starting heartbeat monitor (Press Ctrl+C to stop)...")
            print()

            while True:
                heartbeats = self.get_all_heartbeats()
                self.print_status(heartbeats)

                print(f"\nRefreshing in {interval} seconds...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nMonitor stopped.")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="LiveCore Heartbeat Monitor")
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch mode (continuously monitor)"
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)"
    )

    args = parser.parse_args()

    monitor = HeartbeatMonitor()

    if args.watch:
        monitor.watch(interval=args.interval)
    else:
        heartbeats = monitor.get_all_heartbeats()
        monitor.print_status(heartbeats)


if __name__ == "__main__":
    main()
