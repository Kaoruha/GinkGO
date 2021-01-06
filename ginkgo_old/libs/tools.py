"""
系统工具类方法
"""
import os


def __is_dir_exists(path):
    """
    判断目录是否存在
    :param path: 文件目录
    :return: 如果存在返回True，不存在返回False
    """
    is_exists = os.path.exists(path)
    return is_exists


def makedir(path):
    """
    先判断目录是否存在，如果不存在则创建目录
    :param path: 文件目录
    :return:
    """
    if not __is_dir_exists(path):
        os.makedirs(path, mode=0o777)
        print(f"{path} 创建成功")
    else:
        print(f"{path} 已经存在")


path = './static/data/for_dir_test'
# 获取当前工作目录路径
