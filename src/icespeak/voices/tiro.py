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


    Icelandic-language text to speech via Tiro's text to speech API.

"""
from __future__ import annotations

from typing import TYPE_CHECKING

import uuid
from logging import getLogger

import requests

from icespeak.settings import SETTINGS, AudioFormatsT, TextFormatsT
from icespeak.transcribe import strip_markup

from . import VoiceMap, suffix_for_audiofmt

if TYPE_CHECKING:
    from pathlib import Path

_LOG = getLogger(__file__)
VOICES: VoiceMap = {
    "Alfur": {"id": "Alfur", "lang": "is-IS"},
    "Dilja": {"id": "Dilja", "lang": "is-IS"},
    "Bjartur": {"id": "Bjartur", "lang": "is-IS"},
    "Rosa": {"id": "Rosa", "lang": "is-IS"},
    "Alfur_v2": {"id": "Alfur_v2", "lang": "is-IS"},
    "Dilja_v2": {"id": "Dilja_v2", "lang": "is-IS"},
}
AUDIO_FORMATS = frozenset(("mp3", "pcm", "ogg_vorbis"))


_TIRO_TTS_URL = "https://tts.tiro.is/v0/speech"


def text_to_audio_data(
    text: str,
    *,
    voice: str,
    speed: float = 1.0,
    text_format: str,
    audio_format: str,
) -> bytes:
    """Feeds text to Tiro's TTS API and returns audio data received from server."""

    # Tiro's API supports a subset of SSML tags
    # See https://tts.tiro.is/#tag/speech/paths/~1v0~1speech/post
    # However, for now, we just strip all markup
    text = strip_markup(text)
    text_format = "text"

    if audio_format not in AUDIO_FORMATS:
        _LOG.warn(
            "Unsupported audio format for Tiro speech synthesis: %s."
            + " Falling back to mp3",
            audio_format,
        )
        audio_format = "mp3"

    jdict = {
        "Engine": "standard",
        "LanguageCode": "is-IS",
        "OutputFormat": audio_format,
        "SampleRate": "16000",
        "Text": text,
        "TextType": text_format,
        "VoiceId": voice,
    }

    try:
        r = requests.post(_TIRO_TTS_URL, json=jdict, timeout=10)
        if r.status_code != 200:
            raise Exception(
                f"Received HTTP status code {r.status_code} from Tiro server"
            )
        return r.content
    except Exception as e:
        _LOG.error("Error communicating with Tiro API at %s: %s", _TIRO_TTS_URL, e)
        raise


def text_to_speech(
    text: str,
    *,
    voice: str,
    speed: float,
    text_format: TextFormatsT,
    audio_format: AudioFormatsT,
) -> Path:
    """Returns URL for speech-synthesized text."""

    data = text_to_audio_data(
        text,
        voice=voice,
        speed=speed,
        text_format=text_format,
        audio_format=audio_format,
    )

    suffix = suffix_for_audiofmt(audio_format)
    outfile: Path = SETTINGS.AUDIO_DIR / f"{uuid.uuid4()}.{suffix}"
    try:
        outfile.write_bytes(data)
    except Exception:
        _LOG.exception("Error writing audio file %s.", outfile)

    # Generate and return file:// URL to audio file
    return outfile
