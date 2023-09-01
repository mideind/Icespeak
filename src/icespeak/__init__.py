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

from .parser import GreynirSSMLParser, fast_transcribe
from .settings import SETTINGS, __logger__
from .transcribe import DefaultTranscriber, TranscriptionOptions, gssml
from .tts import VOICES, TTSInput, text_to_speech
from .voices import TTSOptions

__all__ = (
    "DefaultTranscriber",
    "GreynirSSMLParser",
    "SETTINGS",
    "TTSInput",
    "TTSOptions",
    "TranscriptionOptions",
    "VOICES",
    "fast_transcribe",
    "gssml",
    "text_to_speech",
    "__logger__",
)
