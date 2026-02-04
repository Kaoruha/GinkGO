#!/usr/bin/env python3
"""
API Server 启动脚本 - 支持热重载
"""

import subprocess
import sys
import os

# 切换到脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 启动命令（使用 uvicorn --reload 支持热重载）
cmd = [
    "uv", "run", "uvicorn", "main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
    "--log-level", "info"
]

# 同时输出到终端和日志文件
log_file = open("/tmp/apiserver-dev.log", "w")

# 使用 tee 同时输出到终端和文件
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# 实时输出到终端和日志文件
for line in process.stdout:
    print(line, end='')
    log_file.write(line)
    log_file.flush()

process.wait()
log_file.close()
sys.exit(process.returncode)
