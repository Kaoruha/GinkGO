import os
from src.config.setting import VERSION

dist_path = "./dist"

# 编译安装包
os.system("python setup.py sdist bdist_wheel")

# 安装
dist_uri = f"pip install {dist_path}/ginkgo-{VERSION}.tar.gz"
os.system(dist_uri)

# 清理Dist目录下编译出的安装包
files = os.listdir(dist_path)
for i in files:
    os.remove(f"{dist_path}/{i}")
