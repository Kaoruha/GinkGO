"""
打包配置
"""

import setuptools
from ginkgo.config.setting import (
    PACKAGE_NAME,
    VERSION,
    AUTHOR,
    EMAIL,
    DESCRIPTION,
    PACKAGE_URL,
)

try:
    with open("README.md", "r", encoding="utf-8") as file:
        long_description = file.read()
except Exception as e:
    long_description = "Not found README.md"

config = {
    "package_name": PACKAGE_NAME,
    "version": VERSION,
    "author": AUTHOR,
    "email": EMAIL,
    "description": DESCRIPTION,
    "long_description": long_description,
    "url": PACKAGE_URL,
}

setuptools.setup(
    name=config["package_name"],
    version=config["version"],
    author=config["author"],
    author_email=config["email"],
    description=config["description"],
    long_description=config["long_description"],
    long_description_content_type="text/markdown",
    url=config["url"],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)


# python setup.py sdist bdist_wheel
