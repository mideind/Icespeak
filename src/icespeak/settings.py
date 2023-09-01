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


    Shared settings for the Icespeak package.

"""
# pyright: reportConstantRedefinition=false
# We dont import annotations from __future__ here
# due to pydantic
from typing import Any, Literal, Optional

import json
import tempfile
from logging import getLogger
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# For details about SSML markup, see:
# https://developer.amazon.com/en-US/docs/alexa/custom-skills/speech-synthesis-markup-language-ssml-reference.html
# or:
# https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup
TextFormatsT = Literal["ssml", "text"]
AudioFormatsT = Literal["mp3", "ogg_vorbis", "pcm", "opus"]
MAX_SPEED = 2.0
MIN_SPEED = 0.5


class Settings(BaseSettings):
    """
    Settings for Icespeak.
    Attributes are read from environment variables or `.env` file.
    """

    model_config = SettingsConfigDict(env_prefix="ICESPEAK_")

    DEFAULT_VOICE: str = Field(
        default="Gudrun", description="Default TTS voice if none is requested."
    )
    DEFAULT_VOICE_SPEED: float = Field(default=1.0, le=MAX_SPEED, ge=MIN_SPEED)
    DEFAULT_TEXT_FORMAT: TextFormatsT = Field(
        default="ssml",
        description="Default format to interpret input text as.",
    )
    DEFAULT_AUDIO_FORMAT: AudioFormatsT = Field(
        default="mp3", description="Default audio output format."
    )

    AUDIO_DIR: Optional[Path] = Field(
        default=None,
        description=(
            "Where to save output audio files. "
            "If not set, creates a directory in the platform's temporary directory."
        ),
    )
    AUDIO_CACHE_SIZE: int = Field(
        default=300, gt=0, description="Max number of audio files to cache."
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

    def get_audio_dir(self) -> Path:
        """
        Return directory for saving output audio files.
        If no audio dir was set, create temporary directory.
        """
        if self.AUDIO_DIR is None:
            dir = Path(tempfile.gettempdir()) / "icespeak"
            dir.mkdir(exist_ok=True)
            self.AUDIO_DIR = dir
        return self.AUDIO_DIR


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


class Keys(BaseModel):
    """Contains API keys for various services."""

    azure: Optional[AzureKey] = Field(default=None, description="Azure API key.")
    aws: Optional[AWSPollyKey] = Field(default=None, description="AWS Polly API key.")
    google: Optional[dict[str, Any]] = Field(
        default=None, description="Google API key."
    )


API_KEYS = Keys()
_LOG = getLogger(__file__)

_kd = SETTINGS.KEYS_DIR
if not (_kd.exists() and _kd.is_dir()):
    _LOG.warning("Keys directory missing or incorrect, TTS will not work!")
else:
    # Load API keys
    try:
        API_KEYS.aws = AWSPollyKey.model_validate_json(
            (_kd / SETTINGS.AWSPOLLY_KEY_FILENAME).read_text().strip()
        )
    except Exception:
        _LOG.exception(
            "Could not load AWS Polly API key, ASR with AWS Polly will not work."
        )
    try:
        API_KEYS.azure = AzureKey.model_validate_json(
            (_kd / SETTINGS.AZURE_KEY_FILENAME).read_text().strip()
        )
    except Exception:
        _LOG.exception("Could not load Azure API key, ASR with Azure will not work.")
    try:
        API_KEYS.google = json.loads(
            (_kd / SETTINGS.GOOGLE_KEY_FILENAME).read_text().strip()
        )
    except Exception:
        _LOG.exception("Could not load Google API key, ASR with Google will not work.")
