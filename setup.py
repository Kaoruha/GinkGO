"""
打包配置
"""

import setuptools
from ginkgo.config.package import PACKAGENAME, VERSION, AUTHOR, EMAIL, DESC, URL


config = {
    "package_name": PACKAGENAME,
    "version": VERSION,
    "author": AUTHOR,
    "email": EMAIL,
    "description": DESC,
    "long_description": "TODO",
    "package_url": URL,
}
setuptools.setup(
    name=config["package_name"],
    version=config["version"],
    author=config["author"],
    author_email=config["email"],
    description=config["description"],
    long_description=config["long_description"],
    long_description_content_type="text/markdown",
    url=config["package_url"],
    packages=setuptools.find_packages(),
    package_data={"": ["*.yaml", "*.yml"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)


# # # python setup.py sdist bdist_wheel
