# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import re
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
sys.path.insert(0, os.path.abspath("../.."))
sys.path.append(os.path.abspath("extensions"))
os.environ["BUILDING_DOCS"] = "1"

project = "PyLav"
copyright = "2021-present, Draper"
author = "Draper"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "builder",
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinxcontrib_trio",
    "details",
    "exception_hierarchy",
    "attributetable",
    "resourcelinks",
    "nitpick_file_ignorer",
    "sphinx.ext.viewcode",
]
autodoc_member_order = "bysource"
autodoc_typehints = "none"

extlinks = {
    "issue": ("https://github.com/Drapersniper/PyLav/issues/%s", "GH-"),
    "ddocs": ("https://discord.com/developers/docs/%s", None),
}

intersphinx_mapping = {
    "py": ("https://docs.python.org/3", None),
    "aio": ("https://docs.aiohttp.org/en/stable/", None),
    "req": ("https://requests.readthedocs.io/en/latest/", None),
    "dpy": ("https://discordpy.readthedocs.io/en/latest/", None),
    "red": ("https://docs.discord.red/en/latest/", None),
}

rst_prolog = """
.. |coro| replace:: This function is a |coroutine_link|_.
.. |maybecoro| replace:: This function *could be a* |coroutine_link|_.
.. |coroutine_link| replace:: *coroutine*
.. _coroutine_link: https://docs.python.org/3/library/asyncio-task.html#coroutine
"""

templates_path = ["_templates"]
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

version = ""
with open("../../pylav/__init__.py") as f:
    version = re.search(r'^__VERSION__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE)[1]


# The full version, including alpha/beta/rc tags.
release = version

# This assumes a tag is available for final releases
branch = "master"

gettext_compact = False
exclude_patterns = ["_build"]

pygments_style = "friendly"
nitpick_ignore_files = []
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_experimental_html5_writer = True
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_context = {
    "discord_invite": "https://discord.com/invite/Sjh2TSCYQB",
}
resource_links = {
    "discord": "https://discord.com/invite/Sjh2TSCYQB",
    "issues": "https://github.com/Drapersniper/PyLav/issues",
    "discussions": "https://github.com/Drapersniper/PyLav/discussions",
}
