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


"""
from collections.abc import Mapping
from typing import TypedDict
from typing_extensions import Literal

from base64 import b64encode

from pydantic import BaseModel, Extra, Field

from icespeak.settings import (
    MAX_SPEED,
    MIN_SPEED,
    SETTINGS,
    AudioFormatsT,
    TextFormatsT,
)

# Mime types and suffixes
BINARY_MIMETYPE = "application/octet-stream"
AUDIOFMT_TO_MIMETYPE = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg_vorbis": "audio/ogg",
    "pcm": BINARY_MIMETYPE,
    # Uses an Ogg container. See https://www.rfc-editor.org/rfc/rfc7845
    "opus": "audio/ogg",
}

FALLBACK_SUFFIX = "data"
AUDIOFMT_TO_SUFFIX = {
    "mp3": "mp3",
    "wav": "wav",
    "ogg_vorbis": "ogg",
    "pcm": "pcm",
    # Recommended filename extension for Ogg Opus files is '.opus'.
    "opus": "opus",
}

VoiceStyleT = Literal["female", "male", "female, child", "male, child"]


class ModuleVoiceInfoT(TypedDict):
    id: str
    lang: str
    style: VoiceStyleT


ModuleVoicesT = Mapping[str, ModuleVoiceInfoT]


def mimetype_for_audiofmt(fmt: str) -> str:
    """Returns mime type for the given audio format."""
    return AUDIOFMT_TO_MIMETYPE.get(fmt, BINARY_MIMETYPE)


def suffix_for_audiofmt(fmt: str) -> str:
    """Returns file suffix for the given audio format."""
    return AUDIOFMT_TO_SUFFIX.get(fmt, FALLBACK_SUFFIX)


def generate_data_uri(data: bytes, mime_type: str = BINARY_MIMETYPE) -> str:
    """Generate Data URI (RFC2397) from bytes."""
    b64str = b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{b64str}"


class TTSOptions(BaseModel):
    """Text-to-speech options."""

    model_config = {"frozen": True, "extra": Extra.forbid}

    voice: str = Field(default=SETTINGS.DEFAULT_VOICE, description="TTS voice.")
    speed: float = Field(
        default=SETTINGS.DEFAULT_VOICE_SPEED,
        ge=MIN_SPEED,
        le=MAX_SPEED,
        description="TTS speed.",
    )
    text_format: TextFormatsT = Field(
        default=SETTINGS.DEFAULT_TEXT_FORMAT,
        description="Format of text (plaintext or SSML).",
    )
    audio_format: AudioFormatsT = Field(
        default=SETTINGS.DEFAULT_AUDIO_FORMAT,
        description="Audio format for TTS output.",
    )
