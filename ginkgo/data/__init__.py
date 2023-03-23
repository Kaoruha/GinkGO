# import os
# import sys
# import inspect
# import importlib

# package_name = "ginkgo/data/models"
# files = os.listdir(package_name)
# for file in files:
#     if not (file.endswith(".py") and file != "__init__.py"):
#         continue

#     file_name = file[:-3]
#     # print(file_name)
#     package_name = package_name.replace("/", ".")
#     module_name = package_name + "." + file_name
#     # print(module_name)
#     for name, cls in inspect.getmembers(
#         importlib.import_module(module_name), inspect.isclass
#     ):
#         if cls.__module__ == module_name and cls.__abstract__ != True:
#             print(cls)
#             print(cls.__abstract__)
#             # cls.__table__.create()
