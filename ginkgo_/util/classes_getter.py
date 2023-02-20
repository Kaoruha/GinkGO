import inspect
 
# 找出模块里所有的类名
def get_classes(arg):
    classes = []
    clsmembers = inspect.getmembers(arg, inspect.isclass)
    for i in clsmembers:
        classes.append(i[1])
    return classes