# 导入os模块，用于操作系统相关的功能
import os


# 定义一个函数，接受一个关键词列表作为参数，返回一个包含进程id和进程名的字典
def find_process_by_keyword(keyword):
    # 创建一个空字典，用于存储结果
    result = {}
    # 调用os.popen方法，执行ps命令，获取所有进程的信息
    output = os.popen(f"ps -ef")
    # 遍历输出的每一行，跳过第一行（标题行）
    for line in output.readlines()[1:]:
        # 用空格分割每一行，获取进程id和进程名
        pid, pname = line.split()[1], line.split()[-1]
        # 遍历关键词列表，判断进程名是否包含关键词
        if keyword in line:
            # 如果包含关键词，将进程id和进程名添加到结果字典中
            result[pid] = pname
    # 返回结果字典
    return result
