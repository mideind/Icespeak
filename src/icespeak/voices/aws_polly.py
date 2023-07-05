"""

    Icespeak - Icelandic TTS library

    Copyright (C) 2023 Miðeind ehf.  All rights reserved.


    Icelandic-language text to speech via Amazon Polly.

"""

from typing import Any, Optional, cast

import json
from logging import getLogger

_LOG = getLogger(__file__)
from threading import Lock

import boto3  # pyright: ignore[reportMissingTypeStubs]
import cachetools
import requests
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]
from utility import RESOURCES_DIR

NAME = "Amazon Polly"
VOICES = frozenset(("Karl", "Dora"))
AUDIO_FORMATS = frozenset(("mp3", "pcm", "ogg_vorbis"))

# The AWS Polly API access keys
# You must obtain your own keys if you want to use this code
# JSON format is the following:
# {
#     "aws_access_key_id": "my_key",
#     "aws_secret_access_key": "my_secret",
#     "region_name": "my_region"
# }
#
_AWS_KEYFILE_NAME = "AWSPollyServerKey.json"
_AWS_API_KEYS_PATH = str(RESOURCES_DIR / _AWS_KEYFILE_NAME)


_aws_api_client: Optional[boto3.Session] = None
_aws_api_client_lock = Lock()


def _initialize_aws_client() -> Optional[boto3.Session]:
    """Set up AWS Polly client."""
    global _api_client

    # Make sure that only one thread is messing with the global variable
    with _aws_api_client_lock:
        if _aws_api_client is None:
            # Read AWS Polly API keys from file
            aws_config = {}
            try:
                with open(_AWS_API_KEYS_PATH) as json_file:
                    aws_config = json.load(json_file)
            except Exception as e:
                _LOG.warning(f"Unable to read AWS Polly credentials: {e}")
                return None
            _api_client = boto3.Session(**aws_config).client("polly")
        # Return client instance
        return _api_client  # type: ignore


# Time to live (in seconds) for synthesized text URL caching
# Add a safe 30 second margin to ensure that clients are never provided with an
# audio URL that is just about to expire and might do so before playback starts.
_AWS_URL_TTL = 600  # 10 mins in seconds
_AWS_CACHE_TTL = _AWS_URL_TTL - 30  # seconds
_AWS_CACHE_MAXITEMS = 30


@cachetools.cached(cachetools.TTLCache(_AWS_CACHE_MAXITEMS, _AWS_CACHE_TTL))
def text_to_audio_url(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: Optional[str],
    speed: float = 1.0,
) -> Optional[str]:
    """Returns Amazon Polly URL to audio file with speech-synthesized text."""

    assert voice_id in VOICES
    assert audio_format in AUDIO_FORMATS

    # Set up client lazily
    client = _initialize_aws_client()
    if client is None:
        _LOG.warning("Unable to instantiate AWS client")
        return None

    if audio_format not in AUDIO_FORMATS:
        _LOG.warn(
            f"Unsupported audio format for Amazon Polly speech synthesis: {audio_format}."
            " Falling back to mp3"
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
        url = cast(Any, client).generate_presigned_url(
            ClientMethod="synthesize_speech",
            Params=params,
            ExpiresIn=_AWS_URL_TTL,
            HttpMethod="GET",
        )
    except ClientError as e:
        _LOG.error(e)
        return None

    return url


def text_to_audio_data(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float,
) -> Optional[bytes]:
    """Returns audio data for speech-synthesized text."""
    url = text_to_audio_url(**locals())
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        return r.content
    except Exception as e:
        _LOG.error(f"Error fetching URL {url}: {e}")
    return None
