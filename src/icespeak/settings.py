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
RecVoicesT = Literal["Gudrun", "Gunnar"]
MAX_SPEED = 2.0
MIN_SPEED = 0.5


def _create_audio_dir() -> Path:
    """
    Called when the user doesn't specify an output audio directory.
    Creates and returns path to directory in the temporary directory.
    """
    dir = Path(tempfile.gettempdir()) / "icespeak"
    dir.mkdir(exist_ok=True)
    return dir


class Settings(BaseSettings):
    """
    Settings for Icespeak.
    The attributes are read from the environment.
    """

    model_config = SettingsConfigDict(env_prefix="ICESPEAK_")

    DEFAULT_VOICE: RecVoicesT = Field(
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

    AUDIO_DIR: Path = Field(
        default_factory=_create_audio_dir,
        description=(
            "Where to save output audio files. "
            "If not set, creates a directory in the platform's temporary directory."
        ),
    )
    AUDIO_TTL: int = Field(
        default=600, gt=0, description="Time-to-live in seconds for cached audio files."
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
    google: Optional[dict[Any, Any]] = Field(
        default=None, description="Path to Google API key file."
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
