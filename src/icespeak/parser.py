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


This file contains functionality which simplifies composing text
with data that should be transcribed for TTS engines,
along with a parser which parses the composed text and
calls the appropriate transcription method from `./transcribe`.

"""

from __future__ import annotations

from typing import Any
from typing_extensions import override

from collections import deque
from html.parser import HTMLParser
from inspect import ismethod
from logging import getLogger

from .settings import SETTINGS, TRACE
from .transcribe import DefaultTranscriber, TranscriptionMethod
from .tts import SERVICES, VOICES

_LOG = getLogger(__name__)
GSSML_TAG = "greynir"


def gssml(data: Any = None, *, type: str, **kwargs: str | float) -> str:
    """
    Utility function, surrounds data with Greynir-specific
    voice transcription tags.
    E.g. '<greynir ...>{data}</greynir>'
      or '<greynir ... />' if data is None.

    Type specifies the type of handling needed when the tags are parsed.
    The kwargs are then passed to the handler functions as appropriate.

    The greynir tags can be transcribed
    in different ways depending on the voice engine used.

    Example:
        gssml(43, type="number", gender="kk") -> '<greynir type="number" gender="kk">43</greynir>'
    """
    assert type, "Type keyword cannot be empty."
    assert isinstance(type, str), f"type keyword arg must be string in function gssml; data: {data}"
    return (
        f'<{GSSML_TAG} type="{type}"'
        + "".join(f' {k}="{v}"' for k, v in kwargs.items())
        + (f">{data}</{GSSML_TAG}>" if data is not None else " />")
    )


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

        if not len(VOICES):
            raise RuntimeError("No voices available. Please install the API key for at least one voice engine.")
        if voice not in VOICES:
            _LOG.warning(
                "Voice %r not in supported voices, reverting to default: %r",
                voice,
                SETTINGS.DEFAULT_VOICE,
            )
            voice = SETTINGS.DEFAULT_VOICE

        # Fetch transcriber for this voice
        service = VOICES[voice].get("service")
        self._handler: type[DefaultTranscriber]
        self._handler = SERVICES[service].Transcriber if service else DefaultTranscriber

        self._str_stack: deque[str] = deque()
        self._attr_stack: deque[dict[str, str | None]] = deque()
        _LOG.debug(
            "Initialized GreynirSSMLParser, using TranscriptionHandler: %s",
            self._handler,
        )

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
        assert len(self._str_stack) == 1, "Error during parsing, are all markup tags correctly closed?"
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
            _LOG.debug("%s tag opened. Attrs: %s.", tag, attrs)
            _LOG.log(
                TRACE,
                "str stack: %s. attr stack: %s",
                self._str_stack,
                self._attr_stack,
            )

    @override
    def handle_data(self, data: str) -> None:
        """Called when data is encountered."""
        # Append string data to current string in stack
        _LOG.log(TRACE, "Data before danger symbols stripped: %r", data)
        self._str_stack[-1] += self._handler.danger_symbols(data)
        _LOG.log(TRACE, "Data after danger symbols stripped: %r", data)

    @override
    def handle_endtag(self, tag: str):
        """Called when a tag is closed."""
        if tag == GSSML_TAG:
            # Parse data inside the greynir tag we're closing
            s: str = self._str_stack.pop()  # String content
            if self._attr_stack:
                dattrs = self._attr_stack.pop()  # Current tag attributes
                t: str | None = dattrs.pop("type")
                assert t, f"Missing type attribute in <{GSSML_TAG}> tag around string: {s}"
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

            _LOG.debug("%s tag closed.", tag)
            _LOG.log(
                TRACE,
                "str stack: %s. attr stack: %s",
                self._str_stack,
                self._attr_stack,
            )

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
            _LOG.debug("%s tag opened and closed. Attrs: %s.", tag, attrs)
            _LOG.log(
                TRACE,
                "str stack: %s. attr stack: %s",
                self._str_stack,
                self._attr_stack,
            )
