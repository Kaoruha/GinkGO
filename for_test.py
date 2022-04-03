"""
Author: Kaoru
Date: 2022-03-23 21:23:27
LastEditTime: 2022-04-03 00:52:25
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/for_test.py
What goes around comes around.
"""
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-dev", help="dev mode", action="store_true")
parser.add_argument("-debug")
args = parser.parse_args()
print(args.dev)
print(args.debug)
