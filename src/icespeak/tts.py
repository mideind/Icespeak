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
from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, TypedDict, cast

import importlib
from logging import getLogger
from pathlib import Path

from cachetools import LFUCache, cached

from .settings import MAX_SPEED, MIN_SPEED, SETTINGS, AudioFormatsT, TextFormatsT
from .transcribe import TRANSCRIBER_CLASS, DefaultTranscriber

if TYPE_CHECKING:
    from .voices import VoiceT

_LOG = getLogger(__file__)


class TTSFuncT(Protocol):
    """Type signature for a text-to-speech function."""

    def __call__(
        self,
        text: str,
        *,
        voice: str,
        speed: float,
        text_format: TextFormatsT,
        audio_format: AudioFormatsT,
    ) -> Path:
        ...


class VoiceModuleT(Protocol):
    """Protocol for a voice module."""

    VOICES: Mapping[str, VoiceT]
    text_to_speech: TTSFuncT
    Transcriber: type[DefaultTranscriber] | None


class VoiceDict(TypedDict):
    text_to_speech: TTSFuncT
    Transcriber: type[DefaultTranscriber] | None
    lang: str


VoiceMapping = Mapping[str, VoiceDict]


def _load_modules() -> VoiceMapping:
    """
    Dynamically load all voice modules, map
    voice ID strings to the relevant functions.
    """

    v2m: VoiceMapping = {}

    vm_dir = Path(__file__).parent / "voices"
    for file in vm_dir.glob("*.py"):
        if file.name == "__init__.py":
            continue
        modname = f".{vm_dir.name}.{file.with_suffix('').name}"
        try:
            m: VoiceModuleT = cast(
                VoiceModuleT, importlib.import_module(modname, package="icespeak")
            )
        except Exception:
            _LOG.exception("Error importing voice module %r.", modname)
            continue
        voices = m.VOICES
        for v, info in voices.items():
            if v in v2m:
                raise ValueError(f"Voice {v} is already defined in another module.")
            v2m[v] = {
                "text_to_speech": m.text_to_speech,
                "Transcriber": getattr(m, TRANSCRIBER_CLASS, None),
                "lang": info["lang"],
            }

    return v2m


AVAILABLE_VOICES: VoiceMapping = _load_modules()


@cached(LFUCache(maxsize=SETTINGS.AUDIO_CACHE_SIZE))
def text_to_speech(
    text: str,
    *,
    voice: str = SETTINGS.DEFAULT_VOICE,
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
    if voice not in AVAILABLE_VOICES:
        raise ValueError(
            f"Voice {voice} is not a supported voice: {AVAILABLE_VOICES.keys()}"
        )
    if speed < MIN_SPEED or speed > MAX_SPEED:
        raise ValueError(f"Speed {speed} is outside the range 0.5-2.0")

    return AVAILABLE_VOICES[voice]["text_to_speech"](
        text,
        voice=voice,
        speed=speed,
        text_format=text_format,
        audio_format=audio_format,
    )
