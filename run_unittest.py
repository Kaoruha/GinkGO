# coding:utf-8
import argparse
import datetime
import os
import unittest
from ginkgo.libs.ginkgo_conf import GINKGOCONF as g_conf
from ginkgo.libs import GINKGOLOGGER as gl


def main():
    # args
    parser = argparse.ArgumentParser()
    parser.add_argument("-dev", "--dev", help="dev mode", action="store_true")
    parser.add_argument(
        "-debug",
        "--debug",
        help="set debug level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "CRITICAL"],
    )
    args = parser.parse_args()

    LOGGING_FILE_ON = g_conf.LOGGING_FILE_ON
    LOGGING_PATH = g_conf.LOGGING_PATH

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(now)

    # Change LogLevel
    if args.debug:
        gl.logger.setLevel(args.debug)
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


if __name__ == "__main__":
    main()
