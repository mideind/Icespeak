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

from pathlib import Path
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
)

import importlib
from collections import deque
from html.parser import HTMLParser
from inspect import isfunction, ismethod
from logging import getLogger
from typing_extensions import override

from .trans import TRANSCRIBER_CLASS, DefaultTranscriber, TranscriptionMethod

if TYPE_CHECKING:
    from collections.abc import Iterable

_LOG = getLogger(__file__)
# Text formats
# For details about SSML markup, see:
# https://developer.amazon.com/en-US/docs/alexa/custom-skills/speech-synthesis-markup-language-ssml-reference.html
# or:
# https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup
DEFAULT_TEXT_FORMAT = "ssml"
SUPPORTED_TEXT_FORMATS = frozenset(("text", "ssml"))
assert DEFAULT_TEXT_FORMAT in SUPPORTED_TEXT_FORMATS

# Audio formats
DEFAULT_AUDIO_FORMAT = "mp3"
SUPPORTED_AUDIO_FORMATS = frozenset(("mp3", "ogg_vorbis", "pcm", "opus"))
assert DEFAULT_AUDIO_FORMAT in SUPPORTED_AUDIO_FORMATS

VOICES_DIR = Path(__file__).parent / "voices"
assert VOICES_DIR.is_dir()


def _load_voice_modules() -> dict[str, ModuleType]:
    """Dynamically load all voice modules, map
    voice ID strings to the relevant modules."""

    v2m: dict[str, ModuleType] = {}
    for f in VOICES_DIR.glob("*.py"):
        if f.name == "__init__.py":
            continue
        modname = f".{'voices'}.{f.with_suffix('').name}"
        try:
            # Try to import
            m = importlib.import_module(modname)
            voices = getattr(m, "VOICES", None)
            if not voices or not isinstance(voices, Iterable):
                continue  # No voices declared, skip
            v: Any
            for v in voices:
                assert isinstance(v, str), f"Voice {v!r} is not a string"
                assert v not in v2m, f"Voice '{v}' already declared in module {v2m[v]}"
                v2m[v] = m
        except Exception:
            _LOG.exception("Error importing voice module %s.", modname)

    return v2m


VOICE_TO_MODULE = _load_voice_modules()
SUPPORTED_VOICES = frozenset(VOICE_TO_MODULE.keys())
RECOMMENDED_VOICES = frozenset(("Gudrun", "Gunnar"))
DEFAULT_VOICE = "Gudrun"
DEFAULT_VOICE_SPEED = 1.0

assert DEFAULT_VOICE in SUPPORTED_VOICES
assert DEFAULT_VOICE in RECOMMENDED_VOICES


def _sanitize_args(args: dict[str, Any]) -> dict[str, Any]:
    """Make sure arguments to speech synthesis functions are sane."""
    # Make sure we have a valid voice ID
    voice_id = args["voice_id"].lower().capitalize()
    if voice_id not in SUPPORTED_VOICES:
        _LOG.warning(
            f"Voice '{voice_id}' not in supported voices, reverting to default ({DEFAULT_VOICE})"
        )
        args["voice_id"] = DEFAULT_VOICE
    else:
        args["voice_id"] = voice_id

    # Clamp speed to 50-200% range
    args["speed"] = max(min(2.0, args["speed"]), 0.5)

    return args


def text_to_audio_data(
    text: str,
    text_format: str = DEFAULT_TEXT_FORMAT,
    audio_format: str = DEFAULT_AUDIO_FORMAT,
    voice_id: str = DEFAULT_VOICE,
    speed: float = DEFAULT_VOICE_SPEED,
) -> bytes:
    """Returns audio data for speech-synthesized text."""
    # Fall back to default voice if voice_id param invalid
    if voice_id not in SUPPORTED_VOICES:
        voice_id = DEFAULT_VOICE
    # Create a copy of all function arguments
    args = locals().copy()
    # Find the module that provides this voice
    module = VOICE_TO_MODULE.get(voice_id)
    assert module is not None
    # Get the function from the module
    fn = module.text_to_audio_data
    assert isfunction(fn)
    # Call function in module, passing on the arguments
    return fn(**_sanitize_args(args))


def text_to_audio_url(
    text: str,
    text_format: str = DEFAULT_TEXT_FORMAT,
    audio_format: str = DEFAULT_AUDIO_FORMAT,
    voice_id: str = DEFAULT_VOICE,
    speed: float = DEFAULT_VOICE_SPEED,
) -> str:
    """Returns URL to audio of speech-synthesized text."""
    # Fall back to default voice if voice_id param invalid
    if voice_id not in SUPPORTED_VOICES:
        voice_id = DEFAULT_VOICE
    # Create a copy of all function arguments
    args = locals().copy()
    # Find the module that provides this voice
    module = VOICE_TO_MODULE.get(voice_id)
    assert module is not None
    # Get the function from the module
    fn = module.text_to_audio_url
    assert isfunction(fn)
    # Call function in module, passing on the arguments
    return fn(**_sanitize_args(args))


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

    def __init__(self, voice_id: str = DEFAULT_VOICE) -> None:
        """
        Initialize parser and setup transcription handlers
        for the provided speech synthesis engine.
        """
        super().__init__()
        if voice_id not in SUPPORTED_VOICES:
            _LOG.warning(
                f"Voice '{voice_id}' not in supported voices, reverting to default ({DEFAULT_VOICE})"
            )
            voice_id = DEFAULT_VOICE
        # Find the module that provides this voice
        module = VOICE_TO_MODULE[voice_id]

        # Fetch transcriber for this voice module,
        # using DefaultTranscriber as fallback
        self._handler: type[DefaultTranscriber] = getattr(
            module, TRANSCRIBER_CLASS, DefaultTranscriber
        )

    def transcribe(self, voice_string: str) -> str:
        """Parse and return transcribed voice string."""
        # Prepare HTMLParser variables for parsing
        # (in case this method is called more
        # than once on a particular instance)
        self.reset()

        # Set (or reset) variables used during parsing
        self._str_stack: deque[str] = deque()
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
