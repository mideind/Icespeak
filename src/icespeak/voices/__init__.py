"""

Icespeak - Icelandic TTS library

Copyright (C) 2025 Miðeind ehf.

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

from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING, Literal
from typing_extensions import ReadOnly, TypedDict

from abc import ABC, abstractmethod
from logging import getLogger

from pydantic import BaseModel, Field

from icespeak.settings import MAX_SPEED, MIN_SPEED, SETTINGS, Keys, TextFormats
from icespeak.transcribe import DefaultTranscriber

if TYPE_CHECKING:
    from pathlib import Path

_LOG = getLogger(__name__)


VoiceStyleT = Literal["female", "male", "neutral"]


class VoiceInfoT(TypedDict):
    """
    Info about a voice, as declared by an individual TTS service module.

    The fields are `ReadOnly` so that a service module can describe its
    voices with the narrower types its own API demands -- e.g. AWS Polly
    identifies voices and languages by string literal -- and still have
    that table be a valid `VoiceInfoT` mapping.
    """

    id: ReadOnly[str]
    lang: ReadOnly[str]
    style: ReadOnly[VoiceStyleT]


class RegisteredVoiceInfoT(VoiceInfoT):
    """
    Info about a voice which has been registered in the global voice
    registry, which records the service that provides it.
    """

    service: ReadOnly[str]


ModuleVoicesT = Mapping[str, VoiceInfoT]
ModuleAudioFormatsT = Collection[str]


class TTSOptions(BaseModel):
    # frozen=True makes this hashable which enables caching
    model_config = {"frozen": True, "extra": "forbid"}

    voice: str = Field(default=SETTINGS.DEFAULT_VOICE, description="Speech synthesis voice.")
    speed: float = Field(
        default=SETTINGS.DEFAULT_VOICE_SPEED,
        ge=MIN_SPEED,
        le=MAX_SPEED,
        description="TTS speed.",
    )
    text_format: TextFormats = Field(
        default=SETTINGS.DEFAULT_TEXT_FORMAT,
        description="Format of text (plaintext or SSML).",
    )
    audio_format: str = Field(
        default=SETTINGS.DEFAULT_AUDIO_FORMAT,
        description="Audio format for TTS output.",
    )


class BaseVoice(ABC):
    """
    Base class for TTS voice implementations.

    Implementations conventionally hold their service name, voice table
    and supported audio formats in `_NAME`, `_VOICES` and `_AUDIO_FORMATS`,
    and expose them through the abstract properties below. `_VOICES` is
    deliberately not declared here, so that an implementation can type its
    own table more precisely than `ModuleVoicesT` where its API calls for
    it; the `voices` property is the contract.
    """

    Transcriber: type[DefaultTranscriber] = DefaultTranscriber
    _NAME: str
    _AUDIO_FORMATS: ModuleAudioFormatsT

    def __init__(self) -> None:
        self._avail = True
        try:
            self.load_api_keys()
        except Exception as e:
            _LOG.warning(
                "Error loading API keys, TTS with service %s will not work! Error: %s",
                self.name,
                e,
            )
            self._avail = False

    @property
    def available(self) -> bool:
        return self._avail

    @property
    @abstractmethod
    def name(self) -> str:
        """TTS service name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def voices(self) -> ModuleVoicesT:
        """Available voices."""
        raise NotImplementedError

    @property
    @abstractmethod
    def audio_formats(self) -> Collection[str]:
        """Collection of available output audio formats."""
        raise NotImplementedError

    @abstractmethod
    def load_api_keys(self) -> None:
        """
        Load API keys needed for TTS.
        Access to the `text_to_speech` is disabled
        if this method raises an exception.
        """
        raise NotImplementedError

    @abstractmethod
    def text_to_speech(self, text: str, options: TTSOptions, keys_override: Keys | None = None) -> Path:
        raise NotImplementedError
