#!/bin/sh
#
# Generate pypi wheels universal package and upload
#
# python setup.py bdist_wheel --universal upload -r pypi
python setup.py sdist bdist_wheel