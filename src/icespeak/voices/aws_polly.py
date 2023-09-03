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


    Icelandic-language text to speech via Amazon Polly.

"""
from __future__ import annotations

from typing import Any
from typing_extensions import override

from threading import Lock

import boto3

from icespeak.settings import API_KEYS, LOG, SETTINGS

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions


class AWSPollyVoice(BaseVoice):
    _NAME: str = "AWS Polly"
    _VOICES: ModuleVoicesT = {
        "Karl": {"id": "Karl", "lang": "is-IS", "style": "male"},
        "Dora": {"id": "Dora", "lang": "is-IS", "style": "female"},
    }
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset(("mp3", "pcm", "ogg_vorbis"))

    _lock = Lock()

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

        self._aws_client: Any = None
        with AWSPollyVoice._lock:
            if self._aws_client is None:
                # See boto3.Session.client for arguments
                self._aws_client = boto3.client(
                    "polly",
                    region_name=API_KEYS.aws.region_name.get_secret_value(),
                    aws_access_key_id=API_KEYS.aws.aws_access_key_id.get_secret_value(),
                    aws_secret_access_key=API_KEYS.aws.aws_secret_access_key.get_secret_value(),
                )

    @override
    def text_to_speech(self, text: str, options: TTSOptions):
        # Special preprocessing for SSML markup
        if options.text_format == "ssml":
            # Adjust voice speed as appropriate
            if options.speed != 1.0:
                perc = int(options.speed * 100)
                text = f'<prosody rate="{perc}%">{text}</prosody>'
            # Wrap text in the required <speak> tag
            if not text.startswith("<speak>"):
                text = f"<speak>{text}</speak>"

        try:
            response: dict[str, Any] = self._aws_client.synthesize_speech(
                Text=text,
                TextType=options.text_format,
                VoiceId=AWSPollyVoice._VOICES[options.voice]["id"],
                LanguageCode=AWSPollyVoice._VOICES[options.voice]["lang"],
                SampleRate="16000",
                OutputFormat=options.audio_format,
            )
        except Exception:
            LOG.exception("Error synthesizing speech.")
            raise

        outfile = SETTINGS.get_empty_file(options.audio_format)
        outfile.write_bytes(response["AudioStream"].read())
        return outfile
