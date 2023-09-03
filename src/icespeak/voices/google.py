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


    Icelandic-language text to speech via the Google Cloud API.

"""
from __future__ import annotations

from typing_extensions import override

from google.cloud import texttospeech

from icespeak.settings import API_KEYS, LOG, SETTINGS

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions


class GoogleVoice(BaseVoice):
    _NAME: str = "Google"
    _VOICES: ModuleVoicesT = {
        "Anna": {"id": "is-IS-Standard-A", "lang": "is-IS", "style": "female"}
    }
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset(("mp3",))

    @property
    @override
    def name(self):
        return GoogleVoice._NAME

    @property
    @override
    def voices(self) -> ModuleVoicesT:
        return GoogleVoice._VOICES

    @property
    @override
    def audio_formats(self):
        return GoogleVoice._AUDIO_FORMATS

    @override
    def load_api_keys(self):
        assert API_KEYS.google is not None, "Google API key missing."
        self._key = API_KEYS.google

    @override
    def text_to_speech(self, text: str, options: TTSOptions):
        # Instantiates a client
        client = texttospeech.TextToSpeechClient.from_service_account_info(self._key)

        # Set the text input to be synthesized
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Build the voice request, select the language code and voice.
        voice_selection = texttospeech.VoiceSelectionParams(
            language_code=GoogleVoice._VOICES[options.voice]["lang"],
            name=GoogleVoice._VOICES[options.voice]["id"],
        )

        # Select the type of audio file you want returned.
        # We only support mp3 for now.
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        try:
            # Perform the text-to-speech request on the text input
            # with the selected voice parameters and audio file type.
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_selection, audio_config=audio_config
            )
            data = response.audio_content
        except Exception:
            LOG.exception("Error communicating with Google Cloud STT API.")
            raise

        outfile = SETTINGS.get_empty_file(options.audio_format)
        try:
            assert data is not None, "No data."
            outfile.write_bytes(data)
        except Exception:
            LOG.exception("Error writing audio file %s.", outfile)

        return outfile
