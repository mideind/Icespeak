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

from typing import TYPE_CHECKING, Any, cast

from logging import getLogger
from threading import Lock

import boto3
from botocore.exceptions import ClientError

from icespeak.settings import API_KEYS, AudioFormatsT, TextFormatsT

if TYPE_CHECKING:
    from pathlib import Path

_LOG = getLogger(__file__)

VOICES = frozenset(("Karl", "Dora"))
AUDIO_FORMATS = frozenset(("mp3", "pcm", "ogg_vorbis"))
with Lock():
    assert API_KEYS.aws, "AWS Polly API key missing."
    # See boto3.Session.client for arguments
    _AWS_CLIENT = boto3.client(
        "polly",
        region_name=API_KEYS.aws.region_name.get_secret_value(),
        aws_access_key_id=API_KEYS.aws.aws_access_key_id.get_secret_value(),
        aws_secret_access_key=API_KEYS.aws.aws_secret_access_key.get_secret_value(),
    )


# Time to live (in seconds) for synthesized text URL caching
# Add a safe 30 second margin to ensure that clients are never provided with an
# audio URL that is just about to expire and might do so before playback starts.
_AWS_URL_TTL = 600  # 10 mins in seconds
_AWS_CACHE_TTL = _AWS_URL_TTL - 30  # seconds
_AWS_CACHE_MAXITEMS = 30


def text_to_speech(
    text: str,
    *,
    voice_id: str,
    speed: float,
    text_format: TextFormatsT,
    audio_format: AudioFormatsT,
) -> Path | None:
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

    # Configure query string parameters for AWS request
    params = {
        # The text to synthesize
        "Text": text,
        # mp3 | ogg_vorbis | pcm
        "OutputFormat": audio_format,
        # Dora or Karl
        "VoiceId": voice_id,
        # Valid values for mp3 and ogg_vorbis are "8000", "16000", and "22050".
        # The default value is "22050".
        "SampleRate": "16000",
        # Either "text" or "ssml"
        "TextType": text_format,
        # Only required for bilingual voices
        # "LanguageCode": "is-IS"
    }

    try:
        url = cast(Any, _AWS_CLIENT).generate_presigned_url(
            ClientMethod="synthesize_speech",
            Params=params,
            ExpiresIn=_AWS_URL_TTL,
            HttpMethod="GET",
        )
    except ClientError:
        _LOG.exception("Error synthesizing speech.")
        return None

    return url
