# coding:utf-8
import sys
import argparse
import datetime
import os
import unittest
from ginkgo import GCONF, GLOG


def run_test(path: list):
    LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON
    LOGGING_PATH = GCONF.LOGGING_PATH
    suite = unittest.TestSuite()
    for i in path:
        tests = unittest.TestLoader().discover(i, pattern="test_*.py")
        suite.addTest(tests)

    log_path = LOGGING_PATH + "unittest.log"
    if LOGGING_FILE_ON:
        GLOG.reset_logfile("unittest.log")
        try:
            f = open(log_path, "w")
            f.truncate()
        except Exception as e:
            print(e)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def main():
    os.system("clear")
    # args
    parser = argparse.ArgumentParser()

    parser.add_argument("-all", "--all", help="Test all", action="store_true")
    parser.add_argument("-y", "--y", help="All Yes", action="store_true")
    parser.add_argument("-dev", "--dev", help="dev mode", action="store_true")
    parser.add_argument("-db", "--db", help="database test", action="store_true")
    parser.add_argument("-data", "--data", help="data test", action="store_true")
    parser.add_argument("-base", "--base", help="base test", action="store_true")
    parser.add_argument("-libs", "--libs", help="lib test", action="store_true")
    parser.add_argument(
        "-backtest", "--backtest", help="backtest test", action="store_true"
    )
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

    # Change Loglevel
    if args.debug:
        GLOG.logger.setLevel(args.debug)

    origin_path = "./test"
    path = []

    if args.all:
        args.base = True
        args.dev = True
        args.data = True
        args.backtest = True
        args.db = True
        args.libs = True
        args.y = True

    if args.base:
        path.append(origin_path)

    if args.db:
        if not args.y:
            result = input("DB Moduel may erase the database, Conitnue? Y/N  ")
            if result.upper() == "Y":
                t = origin_path + "/database"
                path.append(t)
        else:
            t = origin_path + "/database"
            path.append(t)

    if args.dev:
        t = origin_path + "/dev"
        path.append(t)

    if args.data:
        t = origin_path + "/data"
        path.append(t)

    if args.backtest:
        t = origin_path + "/backtest"
        path.append(t)

    if args.libs:
        t = origin_path + "/libs"
        path.append(t)

    run_test(path)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage:")
        print("python run_unittest.py --[mode]")
        print("  -dev    Run the units under construction.")
        print("  -db     Run database units.")
        print("  -data   Run data-source relative units.")
        print("  -base   Run frame basic units.")
        exit()

    main()
