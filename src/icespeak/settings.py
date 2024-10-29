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


Shared settings for the Icespeak package.

"""

# We dont import annotations from __future__ here
# due to pydantic
from typing import Any, Optional

import json
import os
import tempfile
import uuid
from enum import Enum
from logging import getLogger
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOG = getLogger(__package__)
TRACE = 5


# For details about SSML markup, see:
# https://developer.amazon.com/en-US/docs/alexa/custom-skills/speech-synthesis-markup-language-ssml-reference.html
# or:
# https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup
class TextFormats(str, Enum):
    SSML = "ssml"
    TEXT = "text"


class AudioFormats(str, Enum):
    MP3 = "mp3"
    OGG_VORBIS = "ogg_vorbis"
    PCM = "pcm"
    OPUS = "opus"


MAX_SPEED = 2.0
MIN_SPEED = 0.5

FALLBACK_SUFFIX = "data"
AUDIOFMT_TO_SUFFIX = {
    "mp3": "mp3",
    "wav": "wav",
    "ogg_vorbis": "ogg",
    "pcm": "pcm",
    # Recommended filename extension for Ogg Opus files is '.opus'.
    "opus": "opus",
}


def suffix_for_audiofmt(fmt: str) -> str:
    """Returns file suffix for the given audio format."""
    return AUDIOFMT_TO_SUFFIX.get(fmt, FALLBACK_SUFFIX)


class Settings(BaseSettings):
    """
    Settings for Icespeak.
    Attributes are read from environment variables or `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ICESPEAK_",
        env_nested_delimiter="__",
        case_sensitive=False,
        # Run validators when attributes are modified
        validate_assignment=True,
        extra="ignore",
    )

    DEFAULT_VOICE: str = Field(
        default="Gudrun", description="Default TTS voice if none is requested."
    )
    DEFAULT_VOICE_SPEED: float = Field(
        default=1.0,
        le=MAX_SPEED,
        ge=MIN_SPEED,
        description="Default TTS voice speed.",
    )
    DEFAULT_TEXT_FORMAT: TextFormats = Field(
        default=TextFormats.SSML,
        description="Default format to interpret input text as.",
    )
    DEFAULT_AUDIO_FORMAT: AudioFormats = Field(
        default=AudioFormats.MP3, description="Default audio output format."
    )

    AUDIO_DIR: Optional[Path] = Field(
        default=None,
        description=(
            "Where to save output audio files. "
            "If not set, creates a directory in the platform's temporary directory."
        ),
    )
    AUDIO_CACHE_SIZE: int = Field(
        default=300, gt=-1, description="Max number of audio files to cache."
    )
    AUDIO_CACHE_CLEAN: bool = Field(
        default=True, description="If True, cleans up generated audio files upon exit."
    )

    KEYS_DIR: Path = Field(
        default=Path("keys"), description="Where to look for API keys."
    )
    AWSPOLLY_KEY_FILENAME: str = Field(
        default="AWSPollyServerKey.json",
        description="Name of the AWS Polly API key file.",
    )
    AZURE_KEY_FILENAME: str = Field(
        default="AzureSpeechServerKey.json",
        description="Name of the Azure API key file.",
    )
    GOOGLE_KEY_FILENAME: str = Field(
        default="GoogleServiceAccount.json",
        description="Name of the Google API key file.",
    )
    OPENAI_KEY_FILENAME: str = Field(
        default="OpenAIServerKey.json",
        description="Name of the OpenAI API key file.",
    )

    def get_audio_dir(self) -> Path:
        """
        Return directory for saving output audio files.
        If no audio dir was set, create temporary directory.
        """
        if self.AUDIO_DIR is None:
            dir = Path(tempfile.gettempdir()) / "icespeak"
            dir.mkdir(exist_ok=True)
            self.AUDIO_DIR = dir  # pyright: ignore[reportConstantRedefinition]
        return self.AUDIO_DIR

    def get_empty_file(self, audio_format: str) -> Path:
        """Get empty file in `AUDIO_DIR`."""
        suffix = suffix_for_audiofmt(audio_format)
        return self.get_audio_dir() / f"{uuid.uuid4()}.{suffix}"


# Read settings from environment
SETTINGS = Settings()


class AWSPollyKey(BaseModel, frozen=True):
    "Format of an API key for AWS Polly."

    aws_access_key_id: SecretStr
    aws_secret_access_key: SecretStr
    region_name: SecretStr


class AzureKey(BaseModel, frozen=True):
    "Format of an API key for Azure."

    key: SecretStr
    region: SecretStr


class OpenAIKey(BaseModel, frozen=True):
    "Format of an API key for OpenAI."

    api_key: SecretStr


class Keys(BaseModel):
    """Contains API keys for various services."""

    azure: Optional[AzureKey] = Field(default=None, description="Azure API key.")
    aws: Optional[AWSPollyKey] = Field(default=None, description="AWS Polly API key.")
    google: Optional[dict[str, Any]] = Field(
        default=None, description="Google API key."
    )
    openai: Optional[OpenAIKey] = Field(default=None, description="OpenAI API key.")

    def __hash__(self):
        return hash((self.azure, self.aws, self.google, self.openai))

    def __eq__(self, other: object):
        return isinstance(other, Keys) and (
            self.azure,
            self.aws,
            self.google,
            self.openai,
        ) == (
            other.azure,
            other.aws,
            other.google,
            other.openai,
        )


API_KEYS = Keys()

_kd = SETTINGS.KEYS_DIR
if not (_kd.exists() and _kd.is_dir()):
    _LOG.warning(
        "Keys directory missing or incorrect: %s", _kd
    )

# Load API keys, logging exceptions in level DEBUG so they aren't logged twice,
# as exceptions are logged as warnings when voice modules are initialized

# Amazon Polly
try:
    if key := os.getenv("ICESPEAK_AWSPOLLY_API_KEY"):
        API_KEYS.aws = AWSPollyKey.model_validate_json(key)
    else:
        API_KEYS.aws = AWSPollyKey.model_validate_json(
            (_kd / SETTINGS.AWSPOLLY_KEY_FILENAME).read_text().strip()
        )
except Exception as err:
    _LOG.debug(
        "Could not load AWS Polly API key, ASR with AWS Polly will not work. Error: %s",
        err,
    )
# Azure
try:
    if key := os.getenv("ICESPEAK_AZURE_API_KEY"):
        API_KEYS.azure = AzureKey.model_validate_json(key)
    else:
        API_KEYS.azure = AzureKey.model_validate_json(
            (_kd / SETTINGS.AZURE_KEY_FILENAME).read_text().strip()
        )
except Exception as err:
    _LOG.debug(
        "Could not load Azure API key, ASR with Azure will not work. Error: %s", err
    )
# Google
try:
    if key := os.getenv("ICESPEAK_GOOGLE_API_KEY"):
        API_KEYS.google = json.loads(key)
    else:
        API_KEYS.google = json.loads(
            (_kd / SETTINGS.GOOGLE_KEY_FILENAME).read_text().strip()
        )
except Exception as err:
    _LOG.debug(
        "Could not load Google API key, ASR with Google will not work. Error: %s",
        err,
    )
# OpenAI
try:
    # First try to load the key from environment variable OPENAI_API_KEY
    if key := os.getenv("ICESPEAK_OPENAI_API_KEY"):
        API_KEYS.openai = OpenAIKey(api_key=SecretStr(key))
    else:
        API_KEYS.openai = OpenAIKey.model_validate_json(
            (_kd / SETTINGS.OPENAI_KEY_FILENAME).read_text().strip()
        )
except Exception as err:
    _LOG.debug(
        "Could not load OpenAI API key, ASR with OpenAI will not work. Error: %s",
        err,
    )
