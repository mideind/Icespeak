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


Icelandic-language text to speech via the OpenAI Speech API.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from typing_extensions import override

from logging import getLogger

from openai import OpenAI

from icespeak.settings import API_KEYS, SETTINGS, Keys

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions

if TYPE_CHECKING:
    from pathlib import Path

_LOG = getLogger(__name__)


class OpenAIVoice(BaseVoice):
    _NAME: str = "OpenAI"
    _VOICES: ModuleVoicesT = {
        "alloy": {"id": "alloy", "lang": "en-US", "style": "neutral"},
        "echo": {"id": "echo", "lang": "en-US", "style": "male"},
        "fable": {"id": "fable", "lang": "en-GB", "style": "male"},
        "onyx": {"id": "onyx", "lang": "en-US", "style": "male"},
        "nova": {"id": "nova", "lang": "en-US", "style": "female"},
        "shimmer": {"id": "shimmer", "lang": "en-US", "style": "female"},
    }
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset(("mp3", "opus", "aac", "flac", "wav", "pcm"))

    def _create_client(self, openai_key: str) -> OpenAI:
        return OpenAI(api_key=openai_key)

    @property
    @override
    def name(self) -> str:
        return OpenAIVoice._NAME

    @property
    @override
    def voices(self) -> ModuleVoicesT:
        return OpenAIVoice._VOICES

    @property
    @override
    def audio_formats(self) -> ModuleAudioFormatsT:
        return OpenAIVoice._AUDIO_FORMATS

    @override
    def load_api_keys(self) -> None:
        assert API_KEYS.openai, "OpenAI API key missing"

        self._openai_client: Any = None
        if self._openai_client is None:
            self._openai_client = self._create_client(API_KEYS.openai.api_key.get_secret_value())

    @override
    def text_to_speech(self, text: str, options: TTSOptions, keys_override: Keys | None = None) -> Path:
        if keys_override and keys_override.openai:
            _LOG.debug("Using overridden OpenAI keys")
            client = self._create_client(keys_override.openai.api_key.get_secret_value())
        else:
            _LOG.debug("Using default OpenAI keys")
            client = self._openai_client

        try:
            openai_args = {
                "model": "tts-1",  # TODO: add option of tts-1-hd model (slower, higher quality)
                "voice": OpenAIVoice._VOICES[options.voice]["id"],
                "input": text,
                "response_format": options.audio_format,
            }
            _LOG.debug("Synthesizing with OpenAI: %s", openai_args)
            with client.audio.speech.with_streaming_response.create(**openai_args) as response:
                outfile = SETTINGS.get_empty_file(options.audio_format)
                response.stream_to_file(outfile)
        except Exception:
            _LOG.exception("OpenAI TTS failed")
            raise

        return outfile
