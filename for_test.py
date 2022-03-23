"""
Author: Kaoru
Date: 2022-03-20 23:37:02
LastEditTime: 2022-03-22 11:40:23
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/for_test.py
What goes around comes around.
"""
import datetime

t = datetime.date.today()
print(t)
t1 = datetime.datetime.today()
print(t1)
b = "2020-01-01"
d = datetime.datetime.strptime(b, "%Y-%m-%d")
print(d)
print(type(d))
print(d.date())
print(d.hour)
delta = datetime.timedelta(days=1, hours=1)
d = d + delta
print(d)
b2 = "2020-02-01"
d2 = datetime.datetime.strptime(b2, "%Y-%m-%d")
print(d2 - d)
print(type(d2 - d))


# c = "9999-01-01 01:01:01"
# dc = datetime.datetime.strptime(c, "%Y-%m-%d")
# print(dc)


class abb(object):
    def haha(self):
        print("hh")


a = abb()
print(type(a.haha))
