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

from typing import Optional
from typing_extensions import override

from collections import deque
from html.parser import HTMLParser
from inspect import ismethod
from logging import getLogger

from .settings import SETTINGS
from .transcribe import TRANSCRIBER_CLASS, DefaultTranscriber, TranscriptionMethod
from .tts import AVAILABLE_VOICES

_LOG = getLogger(__file__)


class GreynirSSMLParser(HTMLParser):
    """
    Parses voice strings containing <greynir> tags and
    calls transcription handlers corresponding to each tag's type attribute.

    Note: Removes any other markup tags from the text as that
          can interfere with the voice engines.

    Example:
        # Provide voice engine ID
        gp = GreynirSSMLParser(voice_id)
        # Transcribe voice string
        voice_string = gp.transcribe(voice_string)
    """

    def __init__(self, voice_id: str = SETTINGS.DEFAULT_VOICE) -> None:
        """
        Initialize parser and setup transcription handlers
        for the provided speech synthesis engine.
        """
        super().__init__()
        if voice_id not in AVAILABLE_VOICES:
            _LOG.warning(
                f"Voice '{voice_id}' not in supported voices, reverting to default ({SETTINGS.DEFAULT_VOICE})"
            )
            voice_id = SETTINGS.DEFAULT_VOICE
        # Find the module that provides this voice
        module = AVAILABLE_VOICES[voice_id]

        # Fetch transcriber for this voice module,
        # using DefaultTranscriber as fallback
        self._handler: type[DefaultTranscriber] = getattr(
            module, TRANSCRIBER_CLASS, DefaultTranscriber
        )
        self._str_stack: deque[str] = deque()

    def transcribe(self, voice_string: str) -> str:
        """Parse and return transcribed voice string."""
        # Prepare HTMLParser variables for parsing
        # (in case this method is called more
        # than once on a particular instance)
        self.reset()

        # Set (or reset) variables used during parsing
        self._str_stack.clear()
        self._str_stack.append("")
        self._attr_stack: deque[dict[str, Optional[str]]] = deque()

        self.feed(voice_string)
        self.close()
        assert (
            len(self._str_stack) == 1
        ), "Error during parsing, are all markup tags correctly closed?"
        out = self._str_stack[0]
        # Capitalize before returning
        return out[0].upper() + out[1:]

    # ----------------------------------------

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        """Called when a tag is opened."""
        if tag == "greynir":
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
        if tag == "greynir":
            # Parse data inside the greynir tag we're closing
            s: str = self._str_stack.pop()  # String content
            if self._attr_stack:
                dattrs = self._attr_stack.pop()  # Current tag attributes
                t: Optional[str] = dattrs.pop("type")
                assert t, f"Missing type attribute in <greynir> tag around string: {s}"
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
    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        """Called when a empty tag is opened (and closed), e.g. '<greynir ... />'."""
        if tag == "greynir":
            dattrs = dict(attrs)
            t: Optional[str] = dattrs.pop("type")
            assert t, "Missing type attribute in <greynir> tag"
            transf: TranscriptionMethod = getattr(self._handler, t)
            # If handler found, replace empty greynir tag with output,
            # otherwise simply remove empty greynir tag
            assert ismethod(transf), f"{t} is not a transcription method."
            s: str = transf(**dattrs)
            self._str_stack[-1] += s
