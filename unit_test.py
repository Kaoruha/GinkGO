# coding:utf-8
import unittest

# 从test文件夹内读取所有单元测试
tests = unittest.defaultTestLoader.discover("./test", pattern="test_*.py")
suite = unittest.TestSuite()
suite.addTest(tests)

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
