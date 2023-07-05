"""

    Icespeak - Icelandic TTS library

    Copyright (C) 2023 Miðeind ehf.  All rights reserved.


    Icelandic-language text to speech via Tiro's text to speech API.

"""

from typing import Optional

from logging import getLogger

_LOG = getLogger(__file__)
import uuid
from pathlib import Path

import requests
from speech.trans import strip_markup

from . import AUDIO_SCRATCH_DIR, suffix_for_audiofmt

NAME = "Tiro"
VOICES = frozenset(("Alfur", "Dilja", "Bjartur", "Rosa", "Alfur_v2", "Dilja_v2"))
AUDIO_FORMATS = frozenset(("mp3", "pcm", "ogg_vorbis"))


_TIRO_TTS_URL = "https://tts.tiro.is/v0/speech"


def text_to_audio_data(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float = 1.0,
) -> Optional[bytes]:
    """Feeds text to Tiro's TTS API and returns audio data received from server."""

    # Tiro's API supports a subset of SSML tags
    # See https://tts.tiro.is/#tag/speech/paths/~1v0~1speech/post
    # However, for now, we just strip all markup
    text = strip_markup(text)
    text_format = "text"

    if audio_format not in AUDIO_FORMATS:
        _LOG.warn(
            f"Unsupported audio format for Tiro speech synthesis: {audio_format}."
            " Falling back to mp3"
        )
        audio_format = "mp3"

    jdict = {
        "Engine": "standard",
        "LanguageCode": "is-IS",
        "OutputFormat": audio_format,
        "SampleRate": "16000",
        "Text": text,
        "TextType": text_format,
        "VoiceId": voice_id,
    }

    try:
        r = requests.post(_TIRO_TTS_URL, json=jdict, timeout=10)
        if r.status_code != 200:
            raise Exception(
                f"Received HTTP status code {r.status_code} from {NAME} server"
            )
        return r.content
    except Exception as e:
        _LOG.error(f"Error communicating with Tiro API at {_TIRO_TTS_URL}: {e}")


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
