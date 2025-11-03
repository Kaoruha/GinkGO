"""
自动化打包，并按照到当前环境，需要提前切换虚拟环境
"""

import os
import sys
import time
import shutil
from pathlib import Path
from src.ginkgo.config.package import VERSION

os.system("pip install setuptools")
# Remove Package
wd = os.path.dirname(os.path.abspath(__file__))
os.system("pip uninstall ginkgo -y")

dist_path = f"{wd}/dist"

# 创建打包文件夹
if not os.path.exists(dist_path):
    Path(dist_path).mkdir(parents=True, exist_ok=True)
else:
    # 删除打包文件夹内所有文件
    shutil.rmtree(dist_path)

# 编译安装包
os.system("python setup.py sdist bdist_wheel")

# 安装

packageinstall = f"pip install {dist_path}/ginkgo-{VERSION}.tar.gz"
os.system(packageinstall)

# Clean
print("Clean Setup Cache.")
os.system("pip uninstall setuptools -y")
os.system(f"rm -rf {wd}/dist")
os.system(f"rm -rf {wd}/build")
os.system(f"rm -rf {wd}/src/ginkgo.egg-info")
