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


    Small program to test caching and cleanup of audio files.
    Note: not run by pytest.

"""
# ruff: noqa: T201
import atexit
import logging
import os
import time

CACHE_SIZE: int = 1

os.environ["ICESPEAK_AUDIO_CACHE_SIZE"] = str(CACHE_SIZE)
os.environ["ICESPEAK_AUDIO_CACHE_CLEAN"] = "1"

logging.basicConfig()  # Otherwise messages lower than WARNING aren't shown
os.environ["ICESPEAK_LOG_LEVEL"] = "DEBUG"


def nprint(*values: object):
    """More noticeable print."""
    print("*" * 5, *values)


def _ensure_num_files():
    assert START_NUM_FILES == len(
        list(AUDIO_DIR.iterdir())
    ), "Number of files in audio dir before/after don't match!"


atexit.register(_ensure_num_files)

import icespeak

assert icespeak.SETTINGS.AUDIO_CACHE_SIZE == CACHE_SIZE

t1 = "Þetta er prufa, eyðast skrárnar á réttan hátt?"

AUDIO_DIR = icespeak.SETTINGS.get_audio_dir()
START_NUM_FILES = len(list(AUDIO_DIR.iterdir()))
nprint("Current number of files in audio directory:", START_NUM_FILES)

start = time.monotonic_ns()
p1 = icespeak.text_to_speech(t1)
duration = time.monotonic_ns() - start

nprint("Audio file:", p1)
nprint("Files in audio dir:", len(list(AUDIO_DIR.iterdir())))
nprint(f"Took {duration / 1e6:.3f} milliseconds.")

nprint("This should be cached...")

start = time.monotonic_ns()
p2 = icespeak.text_to_speech(t1)
duration = time.monotonic_ns() - start

nprint("Audio file:", p2)
nprint("Files in audio dir:", len(list(AUDIO_DIR.iterdir())))
assert p1 == p2, "This wasn't cached correctly!"
nprint(f"Took {duration / 1e6:.3f} milliseconds. (Should be a lot faster than above.)")

if CACHE_SIZE > 1:
    nprint("CACHE SIZE:", CACHE_SIZE)
    nprint("Filling cache")
    for n in range(1, CACHE_SIZE + 1):
        print(".", end="")
        # Fill cache with uncacheable stuff, if CACHE_SIZE > 1
        icespeak.text_to_speech(f"Texti númer {n+1}.")
    print()
    nprint("Cache filled.")

nprint("Now we should see an eviction!")

p3 = icespeak.text_to_speech("Þetta er allt annar texti!")
nprint("Audio file:", p3)
nprint("Files in audio dir:", len(list(AUDIO_DIR.iterdir())))

nprint("Sleeping a bit, allow cleanup thread to remove files...")
time.sleep(0.5)

if CACHE_SIZE == 1:
    # Here we only cache one file, so even the most frequently used one gets evicted
    assert not p1.is_file(), f"Audio file {p1} wasn't evicted!"
    assert not p2.is_file(), f"Audio file {p2} wasn't evicted!"
else:
    assert p1.is_file(), f"Audio file {p1} shouldn't be evicted, it is most frequent!"
    assert p2.is_file(), f"Audio file {p2} shouldn't be evicted, it is most frequent!"

assert p3.is_file(), f"Audio file {p3} should exist!"

nprint("Caching seems to work!")
