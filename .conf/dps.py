#!/usr/bin/env python3
"""
Docker PS 聚类显示工具
将同一服务的多个副本聚合显示
"""

import subprocess
import re
from collections import defaultdict

def get_containers():
    """获取所有运行中的容器"""
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
        capture_output=True,
        text=True
    )
    containers = []
    for line in result.stdout.strip().split('\n'):
        if '|' in line:
            name, status = line.split('|', 1)
            containers.append((name, status))
    return containers

def parse_container_name(name):
    """解析容器名称，提取服务名和副本号"""
    # 匹配 ginkgo-service_name-N 格式（scale 服务）
    match = re.match(r'ginkgo-(.+)-(\d+)$', name)
    if match:
        service = match.group(1)
        replica = int(match.group(2))
        return service, replica, 'scale'

    # 匹配 ginkgo-* 格式（单实例服务）
    if name.startswith('ginkgo-'):
        service = name[8:]  # 去掉 'ginkgo-'
        return service, 1, 'single'

    # 其他容器
    return name, 1, 'other'

def group_and_display():
    """按服务分组并显示"""
    containers = get_containers()

    # 按服务分组
    grouped = defaultdict(list)
    for name, status in containers:
        service, replica, ctype = parse_container_name(name)
        grouped[service].append({
            'name': name,
            'replica': replica,
            'status': status,
            'type': ctype
        })

    # 打印表格
    print("┌" + "─" * 78 + "┐")
    print("│ Ginkgo Docker Containers".ljust(79) + "│")
    print("├" + "─" * 78 + "┤")
    print(f"│ {'Service':<20} │ {'Type':<6} │ {'Replicas':<12} │ {'Status':<30} │")
    print("├" + "─" * 78 + "┤")

    # 按服务名排序
    for service in sorted(grouped.keys()):
        items = grouped[service]
        first = items[0]

        if first['type'] == 'scale':
            # Scale 服务：合并显示
            replicas = sorted([item['replica'] for item in items])
            if len(replicas) <= 4:
                replica_str = ', '.join(map(str, replicas))
            else:
                replica_str = ', '.join(map(str, replicas[:3])) + f' ... {replicas[-1]} ({len(replicas)} total)'
            status_str = first['status'][:30]
            print(f"│ {service:<20} │ Scale   │ {replica_str:<12} │ {status_str:<30} │")
        elif first['type'] == 'single':
            status_str = first['status'][:30]
            print(f"│ {service:<20} │ Single  │ 1            │ {status_str:<30} │")
        else:
            status_str = first['status'][:30]
            print(f"│ {service:<20} │ Other   │ 1            │ {status_str:<30} │")

    print("└" + "─" * 78 + "┘")
    print(f"\nTotal: {len(containers)} containers, {len(grouped)} services")

if __name__ == '__main__':
    group_and_display()
