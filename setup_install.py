"""
自动化打包，并按照到当前环境，需要提前切换虚拟环境
"""

import os
import sys
import time
from src.ginkgo.config.package import VERSION

# Remove Package
wd = os.path.dirname(os.path.abspath(__file__))
os.system("pip uninstall ginkgo -y")

dist_path = f"{wd}/dist"

# 创建打包文件夹
if not os.path.exists(dist_path):
    os.mkdir(dist_path)
else:
    # 删除打包文件夹内所有文件
    files = os.listdir(dist_path)
    for i in files:
        os.remove(f"{dist_path}/{i}")

# 编译安装包
os.system("python setup.py sdist bdist_wheel")

# 安装

packageinstall = f"pip install {dist_path}/ginkgo-{VERSION}.tar.gz"
os.system(packageinstall)

# Clean
print("Clean Setup Cache.")
os.system(f"rm -rf {wd}/dist")
os.system(f"rm -rf {wd}/build")
os.system(f"rm -rf {wd}/src/ginkgo.egg-info")
