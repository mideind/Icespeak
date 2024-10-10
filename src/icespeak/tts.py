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


This file contains wrappers for the entire text-to-speech pipeline
(phonetic transcription -> TTS with a specific voice/service).

"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar
from typing_extensions import override

import atexit
import queue
import threading
from logging import DEBUG, getLogger

from cachetools import LFUCache, cached

from .settings import SETTINGS, TRACE, Keys
from .transcribe import TranscriptionOptions
from .voices import (
    BaseVoice,
    TTSOptions,
    VoiceInfoT,
    aws_polly,
    azure,
    openai,
)

if TYPE_CHECKING:
    from pathlib import Path

_LOG = getLogger(__name__)
VoicesT = Mapping[str, VoiceInfoT]
ServicesT = Mapping[str, BaseVoice]


class TTSOutput(NamedTuple):
    file: Path
    text: str


def _setup_voices() -> tuple[VoicesT, ServicesT]:
    services = (
        aws_polly.AWSPollyVoice(),
        azure.AzureVoice(),
        openai.OpenAIVoice(),
        # google.GoogleVoice(),
    )
    voices: VoicesT = {}
    for service in services:
        _LOG.debug("Loading voices from service: %s", service)
        if not service.available:
            _LOG.info("Voices from service %s not available.", service)
            continue
        for voice, info in service.voices.items():
            # Info about each voice
            if voice in voices:
                _LOG.warning(
                    "Voice named %r already exists! "
                    + "Skipping the one defined in module %s.",
                    voice,
                    service.name,
                )
            else:
                voices[voice] = {"service": service.name, **info}
    return voices, {k.name: k for k in services}


VOICES, SERVICES = _setup_voices()

assert VOICES, """No voices available. Make sure to provide an API key \
for at least one speech synthesis engine in your ICESPEAK_KEYS_DIR directory."""


_T = TypeVar("_T")


class TmpFileLFUCache(LFUCache[_T, TTSOutput]):
    """
    Custom version of a least-frequently-used cache which,
    if the clean cache setting is True,
    schedules files for deletion upon eviction from the cache.
    See docs:
    https://cachetools.readthedocs.io/en/latest/#extending-cache-classes
    """

    @override
    def popitem(self) -> tuple[_T, TTSOutput]:
        """Schedule audio file for deletion upon evicting from cache."""
        key, audiofile = super().popitem()
        _LOG.debug("Expired audio file: %s", audiofile)
        # Schedule for deletion, if cleaning the cache
        if SETTINGS.AUDIO_CACHE_CLEAN:
            _EXPIRED_QUEUE.put(audiofile.file)
        return key, audiofile


_AUDIO_CACHE: TmpFileLFUCache[Any] = TmpFileLFUCache(maxsize=SETTINGS.AUDIO_CACHE_SIZE)

# Cleanup functionality, if cleaning cache setting is turned on
if SETTINGS.AUDIO_CACHE_CLEAN:
    _EXPIRED_QUEUE: queue.Queue[Path | None] = queue.Queue()

    def _cleanup():
        while audiofile := _EXPIRED_QUEUE.get():
            _LOG.log(TRACE, "Unlinking file: %s", audiofile)
            audiofile.unlink(missing_ok=True)

    # Small daemon thread which deletes files sent to the expired queue
    _cleanup_thread = threading.Thread(
        target=_cleanup, name="audio_cleanup", daemon=True
    )
    _cleanup_thread.start()

    def _evict_all():
        _LOG.debug("Evicting everything from cache...")
        _EXPIRED_QUEUE.put(None)  # Signal to thread to stop
        try:
            while _AUDIO_CACHE.currsize > 0:
                # Remove all files currently in cache
                _, v = _AUDIO_CACHE.popitem()
                _LOG.log(TRACE, "Unlinking file: %s", v.file)
                v.file.unlink(missing_ok=True)
        except Exception:
            _LOG.exception("Error when cleaning cache.")
        # Give the thread a little bit of time to join,
        # not much harm if it simply gets killed though
        _cleanup_thread.join(0.3)
        _LOG.debug("Finished evicting.")

    # This function runs upon clean exit from program
    atexit.register(_evict_all)


@cached(_AUDIO_CACHE)
def tts_to_file(
    text: str,
    tts_options: TTSOptions | None = None,
    transcription_options: TranscriptionOptions | None = None,
    *,
    transcribe: bool = True,
    keys_override: Keys | None = None,
) -> TTSOutput:
    """
    # Text-to-speech

    Synthesize speech for the given text and write to local file.

    Audio/voice settings can be supplied in `tts_options`,
    transcription turned on/off via the `transcribe` flag
    and its options supplied in `transcription_options`

    Returns a named tuple containing a path to the output audio file,
    along with the text that was sent to the TTS service.
    """
    if _LOG.isEnabledFor(DEBUG):
        _LOG.debug(
            "tts_to_file, text: %r, TTS options: %s, "
            + "transcribe: %r, transcription options: %s",
            text,
            (
                tts_options.model_dump(exclude_defaults=True) or "<default>"
                if tts_options
                else "None"
            ),
            transcribe,
            (
                transcription_options.model_dump(exclude_defaults=True) or "<default>"
                if transcription_options
                else "None"
            ),
        )
    tts_options = tts_options or TTSOptions()
    try:
        service = SERVICES[VOICES[tts_options.voice]["service"]]
    except KeyError as e:
        raise ValueError(f"Voice {tts_options.voice!r} not available.") from e

    if tts_options.audio_format not in service.audio_formats:
        raise ValueError(
            f"Service {service.name} doesn't support audio format {tts_options.audio_format}."
        )

    if transcribe:
        transcription_options = transcription_options or TranscriptionOptions()
        text = service.Transcriber.token_transcribe(text, options=transcription_options)

    output = TTSOutput(
        file=service.text_to_speech(text, tts_options, keys_override),
        text=text,
    )
    _LOG.debug("tts_to_file, out: %s", output)
    return output
