"""
自动化打包，并按照到当前环境，需要提前切换虚拟环境
"""

import os
from ginkgo.config.package import VERSION


dist_path = "./dist"

# 创建打包文件夹
if not os.path.exists("dist"):
    os.mkdir("dist")
else:
    # 删除打包文件夹内所有文件
    path = "./dist"
    files = os.listdir(path)
    for i in files:
        os.remove(f"{path}/{i}")

# 编译安装包
os.system("python setup.py sdist bdist_wheel")

# 安装
dist_uri = f"pip install {dist_path}/ginkgo-{VERSION}.tar.gz"
os.system(dist_uri)

# Clean
print("Clean Setup Cache.")
os.system("rm -rf dist")
os.system("rm -rf build")
os.system("rm -rf ginkgo.egg-info")
