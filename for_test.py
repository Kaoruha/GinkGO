from ginkgo.config.setting import VERSION
import os
import sys
import time
import platform

print(VERSION)
print("OS: " + sys.platform)
print("OS: " + platform.system())
print("Windows" == str(platform.system()))
