#!/bin/bash

# 获取当前时间，格式为 YYYY-MM-DD_HH-MM-SS
current_time=$(date +"%Y%m%d%H%M")

# 设置源目录和目标目录
clickhouse_dir="./.db/clickhouse"
mysql_dir="./.db/mysql"
backup_dir="/home/Backup"

# 设置备份文件名
backup_file="${backup_dir}/ginkgo_backup_${current_time}.tar.gz"

# 备份 ClickHouse 和 MySQL 数据目录到一个压缩包
docker stop clickhouse_master
docker stop mysql_master
sudo tar --use-compress-program=pigz -cvf "$backup_file" --directory="./.db" mysql clickhouse
docker start clickhouse_master
docker start mysql_master

# 打印完成消息
echo "Backup completed: $backup_file"
