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


Small program to test caching and cleanup of audio files.
Note: not run by pytest.

"""

# ruff: noqa: T201
if __name__ == "__main__":
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
    file1 = icespeak.tts_to_file(t1).file
    duration = time.monotonic_ns() - start

    nprint("Audio file:", file1)
    nprint("Files in audio dir:", len(list(AUDIO_DIR.iterdir())))
    nprint(f"Took {duration / 1e6:.3f} milliseconds.")

    nprint("This should be cached...")

    start = time.monotonic_ns()
    file2 = icespeak.tts_to_file(t1).file
    duration = time.monotonic_ns() - start

    nprint("Audio file:", file2)
    nprint("Files in audio dir:", len(list(AUDIO_DIR.iterdir())))
    assert file1 == file2, "This wasn't cached correctly!"
    nprint(f"Took {duration / 1e6:.3f} milliseconds. (Should be a lot faster than above.)")

    if CACHE_SIZE > 1:
        nprint("CACHE SIZE:", CACHE_SIZE)
        nprint("Filling cache")
        for n in range(1, CACHE_SIZE + 1):
            print(".", end="")
            # Fill cache with uncacheable stuff, if CACHE_SIZE > 1
            _ = icespeak.tts_to_file(f"Texti númer {n+1}.")
        print()
        nprint("Cache filled.")

    nprint("Now we should see an eviction!")

    last_file = icespeak.tts_to_file("Þetta er allt annar texti!").file
    nprint("Audio file:", last_file)
    nprint("Files in audio dir:", len(list(AUDIO_DIR.iterdir())))

    nprint("Sleeping a bit, allow cleanup thread to remove files...")
    time.sleep(0.5)

    if CACHE_SIZE == 1:
        # Here we only cache one file, so even the most frequently used one gets evicted
        assert not file1.is_file(), f"Audio file {file1} wasn't evicted!"
        assert not file2.is_file(), f"Audio file {file2} wasn't evicted!"
    else:
        assert file1.is_file(), f"Audio file {file1} shouldn't be evicted, it is most frequent!"
        assert file2.is_file(), f"Audio file {file2} shouldn't be evicted, it is most frequent!"

    assert last_file.is_file(), f"Audio file {last_file} should exist!"

    nprint("Caching seems to work!")
