"""Pytest hooks shared by the repository test suites.

Every plugin directory ships a module named ``plugin.py`` and its test does
``from plugin import ...``. When several plugin directories are collected in
one run, drop the cached ``plugin`` module before each test module is
imported, so every test binds to the plugin in its own directory.
"""

import sys

import pytest


def pytest_collectstart(collector):
    if isinstance(collector, pytest.Module):
        sys.modules.pop("plugin", None)
