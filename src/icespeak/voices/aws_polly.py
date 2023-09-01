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

from typing import TYPE_CHECKING, Any

import uuid
from logging import getLogger
from threading import Lock

import boto3

from icespeak.settings import API_KEYS, SETTINGS, AudioFormatsT, TextFormatsT

from . import suffix_for_audiofmt

if TYPE_CHECKING:
    from pathlib import Path

    from . import ModuleVoicesT

_LOG = getLogger(__file__)

assert API_KEYS.aws, "AWS Polly API key missing."
NAME = "AWS Polly"
VOICES: ModuleVoicesT = {
    "Karl": {"id": "Karl", "lang": "is-IS", "style": "male"},
    "Dora": {"id": "Dora", "lang": "is-IS", "style": "female"},
}
AUDIO_FORMATS = frozenset(("mp3", "pcm", "ogg_vorbis"))
_aws_client: Any = None
_lock = Lock()
with _lock:
    if _aws_client is None:
        # See boto3.Session.client for arguments
        _aws_client = boto3.client(
            "polly",
            region_name=API_KEYS.aws.region_name.get_secret_value(),
            aws_access_key_id=API_KEYS.aws.aws_access_key_id.get_secret_value(),
            aws_secret_access_key=API_KEYS.aws.aws_secret_access_key.get_secret_value(),
        )


def text_to_speech(
    text: str,
    *,
    voice: str,
    speed: float,
    text_format: TextFormatsT,
    audio_format: AudioFormatsT,
) -> Path:
    """Returns Amazon Polly URL to audio file with speech-synthesized text."""

    if audio_format not in AUDIO_FORMATS:
        _LOG.warn(
            "Unsupported audio format for Amazon Polly speech synthesis: %s."
            + " Falling back to mp3",
            audio_format,
        )
        audio_format = "mp3"

    # Special preprocessing for SSML markup
    if text_format == "ssml":
        # Adjust voice speed as appropriate
        if speed != 1.0:
            perc = int(speed * 100)
            text = f'<prosody rate="{perc}%">{text}</prosody>'
        # Wrap text in the required <speak> tag
        if not text.startswith("<speak>"):
            text = f"<speak>{text}</speak>"

    try:
        response: dict[str, Any] = _aws_client.synthesize_speech(
            Text=text,
            TextType=text_format,
            VoiceId=VOICES[voice]["id"],
            LanguageCode=VOICES[voice]["lang"],
            SampleRate="16000",
            OutputFormat=audio_format,
        )
    except Exception:
        _LOG.exception("Error synthesizing speech.")
        raise

    suffix = suffix_for_audiofmt(audio_format)
    outfile = SETTINGS.get_audio_dir() / f"{uuid.uuid4()}.{suffix}"
    outfile.write_bytes(response["AudioStream"].read())
    return outfile
