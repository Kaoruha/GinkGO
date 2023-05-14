# coding:utf-8
import argparse
import datetime
import os
import unittest
from ginkgo.libs.ginkgo_conf import GINKGOCONF as g_conf
from ginkgo.libs import GINKGOLOGGER as gl


def run_test(path: list):
    LOGGING_FILE_ON = g_conf.LOGGING_FILE_ON
    LOGGING_PATH = g_conf.LOGGING_PATH
    suite = unittest.TestSuite()
    for i in path:
        tests = unittest.TestLoader().discover(i, pattern="test_*.py")
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


def main():
    # args
    parser = argparse.ArgumentParser()
    parser.add_argument("-dev", "--dev", help="dev mode", action="store_true")
    parser.add_argument("-db", "--db", help="database test", action="store_true")
    parser.add_argument("-data", "--data", help="data test", action="store_true")
    parser.add_argument("-base", "--base", help="base test", action="store_true")
    parser.add_argument(
        "-debug",
        "--debug",
        help="set debug level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "CRITICAL"],
    )
    args = parser.parse_args()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(now)

    # Change LogLevel
    if args.debug:
        gl.logger.setLevel(args.debug)

    origin_path = "./test"
    path = []
    if args.base:
        path.append(origin_path)

    if args.db:
        t = origin_path + "/db"
        path.append(t)

    if args.dev:
        t = origin_path + "/dev"
        path.append(t)

    if args.data:
        t = origin_path + "/data"
        path.append(t)

    run_test(path)


if __name__ == "__main__":
    main()
