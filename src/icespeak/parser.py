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
from __future__ import annotations

from typing_extensions import override

from collections import deque
from html.parser import HTMLParser
from inspect import ismethod
from logging import getLogger

from .settings import SETTINGS
from .transcribe import (
    GSSML_TAG,
    TRANSCRIBER_CLASS,
    DefaultTranscriber,
    TranscriptionMethod,
    TranscriptionOptions,
)
from .tts import SERVICE2IMPL, VOICES

_LOG = getLogger(__file__)


def fast_transcribe(
    text: str,
    voice: str | None = None,
    options: TranscriptionOptions | None = None,
):
    """
    Simple wrapper for token-based transcription
    of text for a specific TTS voice.

    If `voice` or `options` argument are `None`,
    falls back to the default voice and default transcriber.
    """
    service = VOICES[voice or SETTINGS.DEFAULT_VOICE]["service"]
    transcriber = SERVICE2IMPL[service][TRANSCRIBER_CLASS]
    return transcriber.token_transcribe(text, options)


class GreynirSSMLParser(HTMLParser):
    """
    Parses voice strings containing <greynir> tags and
    calls transcription handlers corresponding to each tag's type attribute.

    Note: Removes any other markup tags from the text as that
          can interfere with the voice engines.

    Example:
    ```python3
    # Provide voice
    gp = GreynirSSMLParser(voice)
    # Transcribe voice string
    voice_string = gp.transcribe(voice_string)
    ```
    """

    def __init__(self, voice: str = SETTINGS.DEFAULT_VOICE) -> None:
        """
        Initialize parser and setup transcription handlers
        for the provided speech synthesis engine.
        """
        super().__init__()
        if voice not in VOICES:
            _LOG.warning(
                "Voice %r not in supported voices, reverting to default: %r",
                voice,
                SETTINGS.DEFAULT_VOICE,
            )
            voice = SETTINGS.DEFAULT_VOICE

        # Fetch transcriber for this voice
        service = VOICES[voice]["service"]
        self._handler: type[DefaultTranscriber]
        self._handler = SERVICE2IMPL[service][TRANSCRIBER_CLASS]

        self._str_stack: deque[str] = deque()
        self._attr_stack: deque[dict[str, str | None]] = deque()

    def transcribe(self, voice_string: str) -> str:
        """Parse and return transcribed voice string."""
        # Prepare HTMLParser variables for parsing
        # (in case this method is called more
        # than once on a particular instance)
        self.reset()

        # Set (or reset) variables used during parsing
        self._str_stack.clear()
        self._str_stack.append("")
        self._attr_stack.clear()

        self.feed(voice_string)
        self.close()
        assert (
            len(self._str_stack) == 1
        ), "Error during parsing, are all markup tags correctly closed?"
        out = self._str_stack[0]
        # Capitalize before returning
        return out[0].upper() + out[1:] if out else out

    # ----------------------------------------

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        """Called when a tag is opened."""
        if tag == GSSML_TAG:
            self._str_stack.append("")
            self._attr_stack.append(dict(attrs))

    @override
    def handle_data(self, data: str) -> None:
        """Called when data is encountered."""
        # Append string data to current string in stack
        self._str_stack[-1] += self._handler.danger_symbols(data)

    @override
    def handle_endtag(self, tag: str):
        """Called when a tag is closed."""
        if tag == GSSML_TAG:
            # Parse data inside the greynir tag we're closing
            s: str = self._str_stack.pop()  # String content
            if self._attr_stack:
                dattrs = self._attr_stack.pop()  # Current tag attributes
                t: str | None = dattrs.pop("type")
                assert (
                    t
                ), f"Missing type attribute in <{GSSML_TAG}> tag around string: {s}"
                # Fetch corresponding transcription method from handler
                transf: TranscriptionMethod = getattr(self._handler, t)
                assert ismethod(transf), f"{t} is not a transcription method."
                # Transcriber classmethod found, transcribe text
                s = transf(s, **dattrs)
            # Add to our string stack
            if self._str_stack:
                self._str_stack[-1] += s
            else:
                self._str_stack.append(s)

    @override
    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]):
        """Called when a empty tag is opened (and closed), e.g. '<greynir ... />'."""
        if tag == GSSML_TAG:
            dattrs = dict(attrs)
            t: str | None = dattrs.pop("type")
            assert t, f"Missing type attribute in <{GSSML_TAG}> tag"
            transf: TranscriptionMethod = getattr(self._handler, t)
            # If handler found, replace empty greynir tag with output,
            # otherwise simply remove empty greynir tag
            assert ismethod(transf), f"{t} is not a transcription method."
            s: str = transf(**dattrs)
            self._str_stack[-1] += s
