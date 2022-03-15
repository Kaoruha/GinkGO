"""
Author: your name
Date: 2021-12-06 10:03:03
LastEditTime: 2021-12-06 10:17:52
LastEditors: your name
Description: 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
FilePath: \GinkGO\setup.py
"""
import setuptools

try:
    with open("README.md", "r", encoding="utf-8") as file:
        long_description = file.read()
except Exception as e:
    long_description = "Not found README.md"

config = {
    "package_name": "ginkgo",
    "version": "0.1.19",
    "author": "Suny",
    "email": "sun159753@gmail.com",
    "description": "An easy quant lib",
    "long_description": long_description,
    "url": "url://",
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
