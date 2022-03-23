# coding:utf-8
import unittest
from src.config.setting import LOGGING_FILE_ON, LOGGING_PATH
from src.libs import GINKGOLOGGER as gl

# 从test文件夹内读取所有单元测试
tests = unittest.defaultTestLoader.discover("./test", pattern="test_*.py")
suite = unittest.TestSuite()
suite.addTest(tests)

if __name__ == "__main__":
    if LOGGING_FILE_ON:
        path = LOGGING_PATH + "unittest.log"
        gl.reset_logfile("unittest.log")
        try:
            f = open(path, "w")
            f.truncate()
        except Exception as e:
            print(e)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
