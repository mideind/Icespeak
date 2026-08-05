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


Icelandic-language text to speech via Amazon Polly.

"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing_extensions import ReadOnly, TypedDict, override

from logging import getLogger
from threading import Lock

import boto3

from icespeak.settings import API_KEYS, SETTINGS, AWSPollyKey, Keys

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions, VoiceStyleT

if TYPE_CHECKING:
    from collections.abc import Mapping

    # Provided by the `boto3-stubs[polly]` development dependency
    from mypy_boto3_polly.client import PollyClient
    from mypy_boto3_polly.literals import (
        LanguageCodeType,
        OutputFormatType,
        VoiceIdType,
    )

_LOG = getLogger(__name__)


class _PollyVoiceInfoT(TypedDict):
    """
    Voice info as Polly describes it: the voice and language identifiers
    are the string literals that `synthesize_speech` accepts, rather than
    bare strings. Structurally a `VoiceInfoT`.
    """

    id: ReadOnly[VoiceIdType]
    lang: ReadOnly[LanguageCodeType]
    style: ReadOnly[VoiceStyleT]


# Maps the audio formats we expose to the ones Polly names
_fmt2polly: Mapping[str, OutputFormatType] = {
    "mp3": "mp3",
    "pcm": "pcm",
    "ogg_vorbis": "ogg_vorbis",
}


class AWSPollyVoice(BaseVoice):
    _NAME: str = "AWS Polly"
    _VOICES: Mapping[str, _PollyVoiceInfoT] = {
        "Karl": {"id": "Karl", "lang": "is-IS", "style": "male"},
        "Dora": {"id": "Dora", "lang": "is-IS", "style": "female"},
    }
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset(_fmt2polly)

    _lock = Lock()

    def _create_client(self, aws_key: AWSPollyKey) -> PollyClient:
        return boto3.client(
            "polly",
            region_name=aws_key.region_name.get_secret_value(),
            aws_access_key_id=aws_key.aws_access_key_id.get_secret_value(),
            aws_secret_access_key=aws_key.aws_secret_access_key.get_secret_value(),
        )

    @property
    @override
    def name(self):
        return AWSPollyVoice._NAME

    @property
    @override
    def voices(self) -> ModuleVoicesT:
        return AWSPollyVoice._VOICES

    @property
    @override
    def audio_formats(self):
        return AWSPollyVoice._AUDIO_FORMATS

    @override
    def load_api_keys(self):
        assert API_KEYS.aws, "AWS Polly API key missing."

        with AWSPollyVoice._lock:
            self._aws_client: PollyClient = self._create_client(API_KEYS.aws)

    @override
    def text_to_speech(self, text: str, options: TTSOptions, keys_override: Keys | None = None):
        if keys_override and keys_override.aws:
            _LOG.debug("Using overridden AWS keys")
            client = self._create_client(keys_override.aws)
        else:
            _LOG.debug("Using default AWS keys")
            client = self._aws_client
        # Special preprocessing for SSML markup
        if options.text_format == "ssml":
            # Adjust voice speed as appropriate
            if options.speed != 1.0:
                perc = int(options.speed * 100)
                text = f'<prosody rate="{perc}%">{text}</prosody>'
            # Wrap text in the required <speak> tag
            if not text.startswith("<speak>"):
                text = f"<speak>{text}</speak>"

        voice_info = AWSPollyVoice._VOICES[options.voice]
        try:
            _LOG.debug(
                "Synthesizing with AWS Polly: VoiceId=%s, LanguageCode=%s, TextType=%s, OutputFormat=%s",
                voice_info["id"],
                voice_info["lang"],
                options.text_format,
                options.audio_format,
            )
            response = client.synthesize_speech(
                Text=text,
                TextType=options.text_format.value,
                VoiceId=voice_info["id"],
                LanguageCode=voice_info["lang"],
                SampleRate="16000",
                OutputFormat=_fmt2polly[options.audio_format],
            )
        except Exception:
            _LOG.exception("Error synthesizing speech.")
            raise

        outfile = SETTINGS.get_empty_file(options.audio_format)
        outfile.write_bytes(response["AudioStream"].read())
        return outfile
