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


"""

# ruff: noqa: S106
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from icespeak import TTSOptions, tts_to_file
from icespeak.settings import (
    API_KEYS,
    AWSPollyKey,
    Keys,
    TextFormats,
    suffix_for_audiofmt,
)
from icespeak.transcribe import strip_markup
from icespeak.tts import SERVICES, VOICES


def test_voices_utils():
    """Test utility functions used in voices."""

    assert suffix_for_audiofmt("mp3") == "mp3"
    assert suffix_for_audiofmt("blergh") == "data"

    assert strip_markup("hello") == "hello"
    assert strip_markup("<dajs dsajl>hello") == "hello"
    assert strip_markup("hello</jdfskfhds>") == "hello"
    assert strip_markup("<a>hello</a>") == "hello"
    assert strip_markup("<prefer:something>hello</else>") == "hello"


_TEXT = "Prufa"
_MIN_AUDIO_SIZE = 1000


@pytest.mark.skipif(API_KEYS.aws is None, reason="Missing AWS Polly API Key.")
@pytest.mark.network
def test_AWSPolly_speech_synthesis():
    tts_out = tts_to_file(
        _TEXT,
        TTSOptions(text_format=TextFormats.TEXT, audio_format="mp3", voice="Dora"),
    )
    path = tts_out.file
    assert path.is_file(), "Expected audio file to exist"
    assert path.stat().st_size > _MIN_AUDIO_SIZE, "Expected longer audio data"
    path.unlink()


@pytest.mark.skipif(API_KEYS.aws is None, reason="Missing AWS Polly API Key.")
@pytest.mark.network
def test_AWSPolly_speech_synthesis_with_keys_override():
    tts_out = tts_to_file(
        _TEXT,
        TTSOptions(text_format=TextFormats.TEXT, audio_format="mp3", voice="Dora"),
        keys_override=API_KEYS,
    )
    path = tts_out.file
    assert path.is_file(), "Expected audio file to exist"
    assert path.stat().st_size > _MIN_AUDIO_SIZE, "Expected longer audio data"
    path.unlink()


@pytest.mark.skipif(API_KEYS.azure is None, reason="Missing Azure API Key.")
@pytest.mark.network
def test_Azure_speech_synthesis():
    # Test Azure Cognitive Services
    tts_out = tts_to_file(
        _TEXT,
        TTSOptions(text_format=TextFormats.TEXT, audio_format="mp3", voice="Gudrun"),
    )
    path = tts_out.file
    assert path.is_file(), "Expected audio file to exist"
    assert path.stat().st_size > _MIN_AUDIO_SIZE, "Expected longer audio data"
    path.unlink()


@pytest.mark.skipif(API_KEYS.azure is None, reason="Missing Azure API Key.")
@pytest.mark.network
def test_Azure_speech_synthesis_with_keys_override():
    # Test Azure Cognitive Services
    tts_out = tts_to_file(
        _TEXT,
        TTSOptions(text_format=TextFormats.TEXT, audio_format="mp3", voice="Gudrun"),
        keys_override=API_KEYS,
    )
    path = tts_out.file
    assert path.is_file(), "Expected audio file to exist"
    assert path.stat().st_size > _MIN_AUDIO_SIZE, "Expected longer audio data"
    path.unlink()


@pytest.mark.skipif(API_KEYS.google is None, reason="Missing Google API Key.")
@pytest.mark.network
def test_Google_speech_synthesis():
    # Test Google Cloud
    tts_out = tts_to_file(
        _TEXT,
        TTSOptions(text_format=TextFormats.TEXT, audio_format="mp3", voice="Anna"),
    )
    path = tts_out.file
    assert path.is_file(), "Expected audio file to exist"
    assert path.stat().st_size > _MIN_AUDIO_SIZE, "Expected longer audio data"
    path.unlink()


@pytest.mark.skipif(API_KEYS.openai is None, reason="Missing OpenAI API Key.")
@pytest.mark.network
def test_OpenAI_speech_synthesis():
    # Test OpenAI
    tts_out = tts_to_file(
        _TEXT,
        TTSOptions(text_format=TextFormats.TEXT, audio_format="pcm", voice="echo"),
    )
    path = tts_out.file
    assert path.is_file(), "Expected audio file to exist"
    assert path.stat().st_size > _MIN_AUDIO_SIZE, "Expected longer audio data"
    path.unlink()


@patch.dict(SERVICES, {"mock_service": MagicMock()})
@patch.dict(VOICES, {"Dora": {"service": "mock_service"}})
def test_keys_override_in_tts_to_file():
    """Test if keys_override is correctly passed into service.text_to_speech."""
    _TEXT = "Test"
    SERVICES["mock_service"].audio_formats = ["mp3"] # type: ignore
    keys_override = Keys(
        aws=AWSPollyKey(
            aws_access_key_id=SecretStr("test"),
            aws_secret_access_key=SecretStr("test"),
            region_name=SecretStr("test"),
        )
    )
    opts = TTSOptions(text_format=TextFormats.TEXT, audio_format="mp3", voice="Dora")
    tts_to_file(
        _TEXT,
        opts,
        transcribe=False,
        keys_override=keys_override,
    )
    SERVICES["mock_service"].text_to_speech.assert_called_once_with( # type: ignore
        _TEXT,
        opts,
        keys_override,
    )
