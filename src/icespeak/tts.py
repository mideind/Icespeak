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
from pydantic import BaseModel, Field

from .settings import MAX_SPEED, MIN_SPEED, SETTINGS, AudioFormatsT, TextFormatsT
from .transcribe import TRANSCRIBER_CLASS, DefaultTranscriber, TranscriptionOptions
from .voices import TTSOptions, VoiceStyleT

if TYPE_CHECKING:
    from .voices import ModuleVoiceInfoT

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
    """Contents of a voice module."""

    NAME: str
    VOICES: Mapping[str, ModuleVoiceInfoT]
    text_to_speech: TTSFuncT
    Transcriber: type[DefaultTranscriber] | None


class VoiceInfoT(TypedDict):
    lang: str
    style: VoiceStyleT
    service: str
    id: str


class _ServiceImpl(TypedDict):
    text_to_speech: TTSFuncT
    Transcriber: type[DefaultTranscriber]


VoicesT = Mapping[str, VoiceInfoT]


def _load_voice_modules() -> tuple[VoicesT, Mapping[str, _ServiceImpl]]:
    """
    Dynamically load all voice modules, map
    voice ID strings to the relevant functions.
    """

    voice_info: VoicesT = {}
    service_impl: Mapping[str, _ServiceImpl] = {}

    vm_dir = Path(__file__).parent / "voices"
    for file in vm_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue
        modname = f".{vm_dir.name}.{file.with_suffix('').name}"
        try:
            m: VoiceModuleT = cast(
                VoiceModuleT, importlib.import_module(modname, package="icespeak")
            )
            name = m.NAME
            voices = m.VOICES
            transcriber = getattr(m, TRANSCRIBER_CLASS, DefaultTranscriber)
            for v, info in voices.items():
                if v in voice_info:
                    _LOG.warning(f"Voice {v} is already defined in another module!")
                voice_info[v] = {
                    "service": name,
                    "lang": info["lang"],
                    "style": info["style"],
                    "id": info["id"],
                }
                service_impl[name] = {
                    "text_to_speech": m.text_to_speech,
                    TRANSCRIBER_CLASS: transcriber,
                }
        except Exception:
            _LOG.exception("Error importing voice module %r.", modname)
            continue

    return voice_info, service_impl


_vm = _load_voice_modules()
VOICES: VoicesT = _vm[0]
SERVICE2IMPL: Mapping[str, _ServiceImpl] = _vm[1]


class TTSInput(BaseModel):
    """Input into text-to-speech."""

    text: str = Field(description="Text to synthesize.")

    tts_options: TTSOptions = Field(default_factory=TTSOptions)

    transcribe: bool = Field(
        default=True,
        description="Whether to transcribe text before speech synthesis or not.",
    )
    transcribe_options: TranscriptionOptions = Field(
        default_factory=TranscriptionOptions
    )


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
    # Text-to-speech

    Request speech synthesis for the provided text.
    Returns an instance of `pathlib.Path` pointing to the output audio file.
    """

    if voice not in VOICES:
        raise ValueError(
            f"Voice {voice} is not a supported voice: {list(VOICES.keys())}"
        )

    if speed < MIN_SPEED or speed > MAX_SPEED:
        raise ValueError(f"Speed {speed} is outside the range {MIN_SPEED}-{MAX_SPEED}")

    service_tts_func = SERVICE2IMPL[VOICES[voice]["service"]]["text_to_speech"]
    return service_tts_func(
        text,
        voice=voice,
        speed=speed,
        text_format=text_format,
        audio_format=audio_format,
    )
