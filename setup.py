"""
打包配置
"""

import setuptools


config = {
    "package_name": "ginkgo",
    "version": "0.6.0",
    "author": "kaoru",
    "email": "sun159753@gmail.com",
    "description": "Python Backtesting library for trading research",
    "long_description": "TODO",
    "package_url": "",
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
    python_requires=">=3",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    # package_data={"": ["*.yaml", "*.yml"]},
    package_data={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    # entry_points={
    #     "console_scripts": ["btm = main:main"],
    # },
)


# # # python setup.py sdist bdist_wheel
