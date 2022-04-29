# coding:utf-8
import argparse
import unittest
from src.config.setting import LOGGING_FILE_ON, LOGGING_PATH
from src.libs import GINKGOLOGGER as gl


if __name__ == "__main__":
    # args
    parser = argparse.ArgumentParser()
    parser.add_argument("-dev", "--dev", help="dev mode", action="store_true")
    parser.add_argument(
        "-debug",
        "--debug",
        help="set debug level",
        type=str,
        choices=["debug", "info", "warning", "critical"],
    )
    args = parser.parse_args()

    # 从test文件夹内读取所有单元测试
    path = "./test"
    if args.dev:
        path += "/dev"
    tests = unittest.defaultTestLoader.discover(path, pattern="test_*.py")
    suite = unittest.TestSuite()
    suite.addTest(tests)

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
