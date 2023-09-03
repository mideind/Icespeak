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


    Icelandic-language text to speech via Tiro's text to speech API.

"""
from __future__ import annotations

from typing_extensions import override

import requests

from icespeak.settings import LOG, SETTINGS
from icespeak.transcribe import strip_markup

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions

_TIRO_TTS_URL = "https://tts.tiro.is/v0/speech"


class TiroVoice(BaseVoice):
    _NAME: str = "Tiro"
    _VOICES: ModuleVoicesT = {
        "Alfur": {"id": "Alfur", "lang": "is-IS", "style": "male"},
        "Dilja": {"id": "Dilja", "lang": "is-IS", "style": "female"},
        "Bjartur": {"id": "Bjartur", "lang": "is-IS", "style": "male"},
        "Rosa": {"id": "Rosa", "lang": "is-IS", "style": "female"},
        "Alfur_v2": {"id": "Alfur_v2", "lang": "is-IS", "style": "male"},
        "Dilja_v2": {"id": "Dilja_v2", "lang": "is-IS", "style": "female"},
    }
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset(("mp3", "pcm", "ogg_vorbis"))

    @property
    @override
    def name(self):
        return TiroVoice._NAME

    @property
    @override
    def voices(self) -> ModuleVoicesT:
        return TiroVoice._VOICES

    @property
    @override
    def audio_formats(self):
        return TiroVoice._AUDIO_FORMATS

    @override
    def load_api_keys(self):
        pass

    @override
    def text_to_speech(self, text: str, options: TTSOptions):
        # TODO: Tiro's API supports a subset of SSML tags
        # See https://tts.tiro.is/#tag/speech/paths/~1v0~1speech/post

        # However, for now, we just strip all markup
        text = strip_markup(text)

        jdict = {
            "Engine": "standard",
            "LanguageCode": "is-IS",
            "OutputFormat": options.audio_format,
            "SampleRate": "16000",
            "Text": text,
            "TextType": "text",
            "VoiceId": options.voice,
        }

        try:
            r = requests.post(_TIRO_TTS_URL, json=jdict, timeout=10)
            if r.status_code != 200:
                raise Exception(
                    f"Received HTTP status code {r.status_code} from Tiro server"
                )
            data = r.content
        except Exception as e:
            LOG.error("Error communicating with Tiro API at %s: %s", _TIRO_TTS_URL, e)
            raise

        outfile = SETTINGS.get_empty_file(options.audio_format)
        try:
            outfile.write_bytes(data)
        except Exception:
            LOG.exception("Error writing audio file %s.", outfile)

        return outfile
