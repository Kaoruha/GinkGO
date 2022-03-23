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

t = datetime.datetime.now().strftime("%Y-%m-%d")
print(t)


from src.libs import GINKGOLOGGER as gl

gl.logger.info("helo")
