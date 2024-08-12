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


Icelandic-language text to speech via the Azure Speech API.

"""

from __future__ import annotations

from typing_extensions import override

from logging import getLogger
from ssl import OPENSSL_VERSION_INFO

import azure.cognitiveservices.speech as speechsdk

from icespeak.settings import API_KEYS, SETTINGS, Keys
from icespeak.transcribe import DefaultTranscriber, strip_markup

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions

_LOG = getLogger(__name__)

# Audio format enums for Azure Speech API
# https://learn.microsoft.com/en-us/javascript/api/microsoft-cognitiveservices-speech-sdk/speechsynthesisoutputformat
_AzureSDKAudioFmts = speechsdk.SpeechSynthesisOutputFormat
_fmt2enum: dict[str, _AzureSDKAudioFmts] = {
    "mp3": _AzureSDKAudioFmts.Audio16Khz32KBitRateMonoMp3,
    "pcm": _AzureSDKAudioFmts.Raw16Khz16BitMonoPcm,
    "opus": _AzureSDKAudioFmts.Ogg16Khz16BitMonoOpus,
}
_AZURE_VOICES: ModuleVoicesT = {
    # Icelandic
    "Gudrun": {"id": "is-IS-GudrunNeural", "lang": "is-IS", "style": "female"},
    "Gunnar": {"id": "is-IS-GunnarNeural", "lang": "is-IS", "style": "male"},
    # English (UK)
    "Abbi": {"id": "en-GB-AbbiNeural", "lang": "en-GB", "style": "female"},
    "Alfie": {"id": "en-GB-AlfieNeural", "lang": "en-GB", "style": "male"},
    # English (US)
    "Jenny": {"id": "en-US-JennyNeural", "lang": "en-US", "style": "female"},
    "Brandon": {"id": "en-US-BrandonNeural", "lang": "en-US", "style": "male"},
    # French
    "Brigitte": {"id": "fr-FR-BrigitteNeural", "lang": "fr-FR", "style": "female"},
    "Alain": {"id": "fr-FR-AlainNeural", "lang": "fr-FR", "style": "male"},
    # German
    "Elke": {"id": "de-DE-ElkeNeural", "lang": "de-DE", "style": "female"},
    "Conrad": {"id": "de-DE-ConradNeural", "lang": "de-DE", "style": "male"},
    # Danish
    "Christel": {"id": "da-DK-ChristelNeural", "lang": "da-DK", "style": "female"},
    "Jeppe": {"id": "da-DK-JeppeNeural", "lang": "da-DK", "style": "male"},
    # Swedish
    "Sofie": {"id": "sv-SE-SofieNeural", "lang": "sv-SE", "style": "female"},
    "Mattias": {"id": "sv-SE-MattiasNeural", "lang": "sv-SE", "style": "male"},
    # Norwegian
    "Iselin": {"id": "nb-NO-IselinNeural", "lang": "nb-NO", "style": "female"},
    "Finn": {"id": "nb-NO-FinnNeural", "lang": "nb-NO", "style": "male"},
    # Spanish
    "Abril": {"id": "es-ES-AbrilNeural", "lang": "es-ES", "style": "female"},
    "Alvaro": {"id": "es-ES-AlvaroNeural", "lang": "es-ES", "style": "male"},
    # Polish
    "Agnieszka": {"id": "pl-PL-AgnieszkaNeural", "lang": "pl-PL", "style": "female"},
    "Marek": {"id": "pl-PL-MarekNeural", "lang": "pl-PL", "style": "male"},
    # Many more voices available, see:
    # https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support
}


class AzureVoice(BaseVoice):
    _NAME: str = "Azure"
    _VOICES: ModuleVoicesT = _AZURE_VOICES
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset(_fmt2enum.keys())

    class Transcriber(DefaultTranscriber):
        """
        Transcription handler class,
        specific to the Azure voice engine.
        """

        # Override some character pronunciations during
        # transcription (custom for this voice)
        _CHAR_PRONUNCIATION = {
            **DefaultTranscriber._CHAR_PRONUNCIATION,
            "b": "bjé",
            "c": "sjé",
            "d": "djé",
            "ð": "eeð",
            "e": "eeh",
            "é": "jé",
            "g": "gjéé",
            "i": "ii",
            "j": "íoð",
            "o": "úa",
            "ó": "oú",
            "u": "uu",
            "r": "errr",
            "t": "tjéé",
            "ú": "úúu",
            "ý": "ufsilon íí",
            "þ": "þodn",
            "æ": "æí",
            "ö": "öö",
        }

        # Weird entity pronunciations can be added here
        # when they're encountered
        _ENTITY_PRONUNCIATIONS = {
            **DefaultTranscriber._ENTITY_PRONUNCIATIONS,
            "BYKO": "Býkó",
            "ELKO": "Elkó",
            "FIDE": "fídeh",
            "FIFA": "fííffah",
            "GIRL": "görl",
            "LEGO": "llegó",
            "MIT": "emm æí tíí",
            "NEW": "njúú",
            "NOVA": "Nóva",
            "PLUS": "plöss",
            "SHAH": "Sjah",
            "TIME": "tæm",
            "UEFA": "júei fa",
            "UENO": "júeenó",
            "UKIP": "júkipp",
            "VISA": "vísa",
            "XBOX": "ex box",
        }

        # Override some weird name pronunciations
        _PERSON_PRONUNCIATION = {
            "Joe": "Djó",
            "Biden": "Bæden",
        }

    @property
    @override
    def name(self):
        return AzureVoice._NAME

    @property
    @override
    def voices(self) -> ModuleVoicesT:
        # Add voice languages, based on their ID
        return AzureVoice._VOICES

    @property
    @override
    def audio_formats(self):
        return AzureVoice._AUDIO_FORMATS

    @override
    def load_api_keys(self):
        if not (OPENSSL_VERSION_INFO[0] == 3 and OPENSSL_VERSION_INFO[1] == 0):
            # Azure only works with OpenSSL 3.0.*
            # See issue:
            # https://github.com/Azure-Samples/cognitive-services-speech-sdk/issues/2436
            _LOG.warning("OpenSSL version not compatible with Azure Cognitive Services, TTS might not work.")

        if API_KEYS.azure is None:
            raise RuntimeError("Azure API keys missing.")

        AzureVoice.AZURE_KEY = API_KEYS.azure.key.get_secret_value()
        AzureVoice.AZURE_REGION = API_KEYS.azure.region.get_secret_value()

    @override
    def text_to_speech(self, text: str, options: TTSOptions, keys_override: Keys | None = None):
        if keys_override and keys_override.azure:
            _LOG.debug("Using overridden Azure keys")
            subscription = keys_override.azure.key.get_secret_value()
            region = keys_override.azure.region.get_secret_value()
        else:
            _LOG.debug("Using default Azure keys")
            subscription = AzureVoice.AZURE_KEY
            region = AzureVoice.AZURE_REGION
        speech_conf = speechsdk.SpeechConfig(subscription=subscription, region=region)

        azure_voice_id = AzureVoice._VOICES[options.voice]["id"]
        speech_conf.speech_synthesis_voice_name = azure_voice_id

        fmt = _fmt2enum[options.audio_format]
        speech_conf.set_speech_synthesis_output_format(fmt)

        outfile = SETTINGS.get_empty_file(options.audio_format)
        try:
            audio_config = speechsdk.audio.AudioOutputConfig(filename=str(outfile))  # pyright: ignore[reportArgumentType]

            # Init synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_conf, audio_config=audio_config)

            result: speechsdk.SpeechSynthesisResult
            # Azure Speech API supports SSML but the notation is a bit different from Amazon Polly's
            # See https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup
            if options.text_format == "ssml":
                # Adjust speed
                if options.speed != 1.0:
                    text = f'<prosody rate="{options.speed}">{text}</prosody>'
                # Wrap text in the required <speak> and <voice> tags
                text = f"""
                    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{azure_voice_id[:5]}">
                    <voice name="{azure_voice_id}">
                    {text}
                    </voice></speak>
                """.strip()

                _LOG.debug("Synthesizing SSML with Azure: %r", text)
                result = synthesizer.speak_ssml(text)
            else:
                # We're not sending SSML so strip any markup from text
                text = strip_markup(text)
                _LOG.debug("Synthesizing plaintext with Azure: %r", text)
                result = synthesizer.speak_text(text)

            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Success, return path to the generated audio file
                return outfile

            cancellation_details = result.cancellation_details
            raise RuntimeError(f"TTS with Azure failed: {cancellation_details.error_details}")
        except Exception:
            _LOG.exception("Error communicating with Azure Speech API.")
            raise
