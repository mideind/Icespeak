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


    Icelandic-language text to speech via the Google Cloud API.

"""
from __future__ import annotations

from typing import TYPE_CHECKING

import uuid

from google.cloud import texttospeech

from icespeak.settings import API_KEYS, LOG, SETTINGS, AudioFormatsT, TextFormatsT

from . import ModuleVoicesT, suffix_for_audiofmt

if TYPE_CHECKING:
    from pathlib import Path


NAME = "Google"
VOICES: ModuleVoicesT = {
    "Anna": {"id": "is-IS-Standard-A", "lang": "is-IS", "style": "female"}
}
AUDIO_FORMATS = frozenset(("mp3",))


assert API_KEYS.google is not None, "Google API key missing."


def text_to_audio_data(
    text: str,
    text_format: str,
    audio_format: str,
    voice: str,
    speed: float = 1.0,
) -> bytes:
    """Feeds text to Google's TTS API and returns audio data received from server."""

    # Instantiates a client
    assert API_KEYS.google is not None
    client = texttospeech.TextToSpeechClient.from_service_account_info(API_KEYS.google)

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code and voice.
    voice_selection = texttospeech.VoiceSelectionParams(
        language_code=VOICES[voice]["lang"], name=VOICES[voice]["id"]
    )

    # Select the type of audio file you want returned.
    # We only support mp3 for now.
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    try:
        # Perform the text-to-speech request on the text input
        # with the selected voice parameters and audio file type.
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice_selection, audio_config=audio_config
        )
        return response.audio_content
    except Exception:
        LOG.exception("Error communicating with Google Cloud STT API.")
        raise


def text_to_speech(
    text: str,
    *,
    voice: str,
    speed: float,
    text_format: TextFormatsT,
    audio_format: AudioFormatsT,
) -> Path:
    data = text_to_audio_data(
        text,
        voice=voice,
        speed=speed,
        text_format=text_format,
        audio_format=audio_format,
    )

    suffix = suffix_for_audiofmt(audio_format)
    out_file = SETTINGS.get_audio_dir() / f"{uuid.uuid4()}.{suffix}"
    try:
        assert data is not None, "No data."
        out_file.write_bytes(data)
    except Exception:
        LOG.exception("Error writing audio file %s.", out_file)

    return out_file
