"""

Icespeak - Icelandic TTS library

Copyright (C) 2024 Miðeind ehf.

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
# with custom marks registered in pyproject.toml.
#
# These marked tests are *skipped by default*.
#
# To mark a test decorate it with e.g.
# `@pytest.mark.network` or `@pytest.mark.slow`
#
# Run the marked tests, use the corresponding
# CLI options e.g. `--run-network` or `--run-slow`

SKIP_MARKERS = (
    "network",
    "slow",
)


def pytest_addoption(parser: pytest.Parser):
    """Add options to the pytest CLI interface."""
    for marker in SKIP_MARKERS:
        # Add --run-{marker} arguments for each skip marker
        parser.addoption(
            f"--run-{marker}",
            action="store_true",
            default=False,
            help=f"run {marker} tests",
        )

    # The option `--run-all` is special, it runs *all* tests
    parser.addoption(
        "--run-all",
        action="store_true",
        default=False,
        help="run all tests that are skipped by default",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    """Add skip markers to tests, based on how pytest was invoked."""
    if config.getoption("--run-all"):
        # --run-all flag provided: don't skip any tests
        return

    # Set of markers which weren't specified to run with `--run-{marker}`
    skipped: set[str] = {marker for marker in SKIP_MARKERS if not config.getoption(f"--run-{marker}")}

    if len(skipped) == 0:
        # All --run-... options given independently
        # (someone likes typing long commands?)
        return

    # For each test item, find whether it has a mark which should be skipped
    for item in items:
        for marker in skipped.intersection(m.name for m in item.own_markers):
            # Add `pytest.mark.skip` to this test item
            item.add_marker(pytest.mark.skip(reason=f"run with --run-{marker}"))
