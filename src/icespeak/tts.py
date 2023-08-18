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
from collections.abc import Iterable, Mapping
from typing import Protocol, cast

import importlib
from logging import getLogger
from pathlib import Path

# from cachetools import cached, TTLCache
from .settings import MAX_SPEED, MIN_SPEED, SETTINGS, AudioFormatsT, TextFormatsT

_LOG = getLogger(__file__)


class TTSFuncT(Protocol):
    """Type signature for a text-to-speech function."""

    def __call__(
        self,
        text: str,
        *,
        voice_id: str,
        speed: float,
        text_format: TextFormatsT,
        audio_format: AudioFormatsT,
    ) -> Path:
        ...


class VoiceModuleT(Protocol):
    """Protocol for a voice module."""

    VOICES: Iterable[str]
    text_to_speech: TTSFuncT


def _load_modules() -> Mapping[str, TTSFuncT]:
    """
    Dynamically load all voice modules, map
    voice ID strings to the relevant functions.
    """

    v2m: Mapping[str, TTSFuncT] = {}

    vm_dir = Path(__file__).parent / "voices"
    for file in vm_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        modname = f".{vm_dir.name}.{file.with_suffix('').name}"
        try:
            m: VoiceModuleT = cast(
                VoiceModuleT, importlib.import_module(modname, package="icespeak")
            )
        except Exception:  # noqa: PERF203
            _LOG.exception("Error importing voice module %r.", modname)
            continue
        voices = m.VOICES
        for v in voices:
            if v in v2m:
                raise ValueError(f"Voice {v} is already defined in another module.")
            v2m[v] = m.text_to_speech

    return v2m


AVAILABLE_VOICES: Mapping[str, TTSFuncT] = _load_modules()


# @cached(TTLCache(maxsize=500, ttu=SETTINGS.AUDIO_TTL))
# TODO: Use custom version of TLRUCache, which removes audio files upon cache eviction
# https://cachetools.readthedocs.io/en/latest/#cachetools.TLRUCache
# https://cachetools.readthedocs.io/en/latest/#extending-cache-classes
def text_to_speech(
    text: str,
    *,
    voice_id: str = SETTINGS.DEFAULT_VOICE,
    speed: float = SETTINGS.DEFAULT_VOICE_SPEED,
    text_format: TextFormatsT = SETTINGS.DEFAULT_TEXT_FORMAT,
    audio_format: AudioFormatsT = SETTINGS.DEFAULT_AUDIO_FORMAT,
) -> Path:
    """
    Text-to-speech
    ==============

    Request speech synthesis for the provided text.
    Returns an instance of :py:class:`pathlib.Path` pointing to the output audio file.
    """
    # Fall back to default voice if voice_id param invalid
    if voice_id not in AVAILABLE_VOICES:
        raise ValueError(
            f"Voice {voice_id} is not a supported voice: {AVAILABLE_VOICES.keys()}"
        )
    if speed < MIN_SPEED or speed > MAX_SPEED:
        raise ValueError(f"Speed {speed} is outside the range 0.5-2.0")

    return AVAILABLE_VOICES[voice_id](
        text,
        text_format=text_format,
        audio_format=audio_format,
        voice_id=voice_id,
        speed=speed,
    )
