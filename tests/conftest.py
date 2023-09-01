"""

    Icespeak - Icelandic TTS library

    Copyright (C) 2023 Miðeind ehf.

       This program is free software: you can redistribute it and/or modify
       it under the terms of the GNU General Public License as published by
       the Free Software Foundation, either version 3 of the License, or
       (at your option) any later version.
       This program is distributed in the hope that it will be useful,
       but WITHOUT ANY WARRANTY; without even the implied warranty of
       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
       GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see http://www.gnu.org/licenses/.


"""
import pytest


# Specify that the trio event loop shouldn't be used for tests
# See: https://github.com/agronholm/anyio/blob/master/docs/testing.rst
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# The following is for marking specific tests
# with `network` or `slow`.
#
# These tests are *skipped by default*.
#
# To mark a test decorate with:
# `@pytest.mark.network` or `@pytest.mark.slow`
# Run the tests with the flags:
# `--run-network`, `--run-slow`, `--run-all`


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="run tests which communicate with external services",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests",
    )
    parser.addoption(
        "--run-all",
        action="store_true",
        default=False,
        help="run all tests that are skipped by default",
    )


def pytest_configure(config: pytest.Config):
    config.addinivalue_line(
        "markers", "network: mark test as communicating with external services"
    )
    config.addinivalue_line("markers", "slow: mark test as slow")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    if config.getoption("--run-all"):
        # --run-all flag provided: don't skip any tests
        return

    # Map marker names to skip markers,
    # indicating the correct flag to use to run the tests.
    skip_markers = {
        "network": pytest.mark.skip(reason="run with '--run-network'"),
        "slow": pytest.mark.skip(reason="run with '--run-slow'"),
    }

    if config.getoption("--run-network"):
        # --run-network given in cli: do not skip network tests
        del skip_markers["network"]
    if config.getoption("--run-slow"):
        # --run-slow given in cli: do not skip slow tests
        del skip_markers["slow"]

    if len(skip_markers) == 0:
        # All flags given independently
        # (if someone likes typing long commands?)
        return

    # Mark relevant tests as being skipped
    for item in items:
        for kw, skip_mark in skip_markers.items():
            if kw in item.keywords:
                item.add_marker(skip_mark)
