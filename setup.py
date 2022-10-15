import re

from setuptools import setup

with open("./pylav/__init__.py") as f:
    version = re.search(r'^__version__\s*=\s*__VERSION__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE)[1]

setup(
    version=version,
)
