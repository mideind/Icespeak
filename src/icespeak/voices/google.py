"""

    Icespeak - Icelandic TTS library

    Copyright (C) 2023 Miðeind ehf.  All rights reserved.


    Icelandic-language text to speech via the Google Cloud API.

"""
# pyright: reportUnknownMemberType=false
from typing import Optional

import uuid
from logging import getLogger
from pathlib import Path

from google.cloud import texttospeech  # pyright: ignore[reportMissingTypeStubs]

from . import AUDIO_SCRATCH_DIR, suffix_for_audiofmt

_LOG = getLogger(__file__)
NAME = "Google"
VOICES = frozenset(("Anna",))
AUDIO_FORMATS = frozenset("mp3")


def text_to_audio_data(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float = 1.0,
) -> Optional[bytes]:
    """Feeds text to Google's TTS API and returns audio data received from server."""

    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code
    # and the SSML voice gender.
    voice = texttospeech.VoiceSelectionParams(
        language_code="is-IS", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
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
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        _LOG.error(f"Error communicating with Google Cloud STT API: {e}")


def text_to_audio_url(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float = 1.0,
) -> Optional[str]:
    """Returns URL for speech-synthesized text."""

    data = text_to_audio_data(**locals())
    if not data:
        return None

    suffix = suffix_for_audiofmt(audio_format)
    out_fn: str = str(AUDIO_SCRATCH_DIR / f"{uuid.uuid4()}.{suffix}")
    try:
        with open(out_fn, "wb") as f:
            f.write(data)
    except Exception as e:
        _LOG.error(f"Error writing audio file {out_fn}: {e}")
        return None

    # Generate and return file:// URL to audio file
    return Path(out_fn).as_uri()
