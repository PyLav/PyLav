import os
import re
import sys
from pathlib import Path
from typing import IO

from setuptools import setup

ROOT_FOLDER = Path(__file__).parent.absolute()
REQUIREMENTS_FOLDER = ROOT_FOLDER / "requirements"

with open("./pylav/__init__.py") as f:
    version = re.search(r'^__version__\s*=\s*__VERSION__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE)[1]


def get_requirements(fp: IO):
    return [line.strip() for line in fp.read().splitlines() if line.strip() and not line.strip().startswith("#")]


def extras_combined(*extra_names):
    return list(
        {
            req
            for extra_name, extra_reqs in extras_require.items()
            if not extra_names or extra_name in extra_names
            for req in extra_reqs
        }
    )


with open(REQUIREMENTS_FOLDER / "base.txt", encoding="utf-8") as fp:
    install_requires = get_requirements(fp)

extras_require = {}
for file in REQUIREMENTS_FOLDER.glob("extra-*.txt"):
    with file.open(encoding="utf-8") as fp:
        extras_require[file.stem[len("extra-") :]] = get_requirements(fp)

extras_require["dev"] = extras_combined()
extras_require["all"] = extras_combined()


setup_kwargs = {
    "version": version,
    "install_requires": install_requires,
    "extras_require": extras_require,
}
if os.getenv("TOX_PYLAV", False) and sys.version_info >= (3, 12):
    setup(python_requires=">=3.11", **setup_kwargs)
else:
    # Metadata and options defined in setup.cfg
    setup(**setup_kwargs)
