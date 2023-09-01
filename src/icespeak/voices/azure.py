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


    Icelandic-language text to speech via the Azure Speech API.

"""
from __future__ import annotations

from typing import TYPE_CHECKING

import uuid
from logging import getLogger

import azure.cognitiveservices.speech as speechsdk

from icespeak.settings import API_KEYS, SETTINGS, AudioFormatsT, TextFormatsT
from icespeak.transcribe import DefaultTranscriber, strip_markup

from . import ModuleVoicesT, suffix_for_audiofmt

if TYPE_CHECKING:
    from pathlib import Path

_LOG = getLogger(__file__)

NAME = "Azure"
VOICES: ModuleVoicesT = {
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
AUDIO_FORMATS = frozenset(("mp3", "pcm", "opus"))

if API_KEYS.azure is None:
    raise RuntimeError("Azure API key missing.")

AZURE_KEY = API_KEYS.azure.key.get_secret_value()
AZURE_REGION = API_KEYS.azure.region.get_secret_value()


def text_to_speech(
    text: str,
    *,
    voice: str,
    speed: float,
    text_format: TextFormatsT,
    audio_format: AudioFormatsT,
) -> Path:
    """Synthesizes text via Azure and returns path to generated audio file."""

    if audio_format not in AUDIO_FORMATS:
        _LOG.warn(
            "Unsupported audio format for Azure speech synthesis: %s."
            + " Falling back to mp3",
            audio_format,
        )
        audio_format = "mp3"

    # Audio format enums for Azure Speech API
    # https://learn.microsoft.com/en-us/javascript/api/microsoft-cognitiveservices-speech-sdk/speechsynthesisoutputformat
    aof = speechsdk.SpeechSynthesisOutputFormat
    fmt2enum: dict[AudioFormatsT, aof] = {
        "mp3": aof.Audio16Khz32KBitRateMonoMp3,
        "pcm": aof.Raw16Khz16BitMonoPcm,
        "opus": aof.Ogg16Khz16BitMonoOpus,
    }
    speech_conf = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)

    azure_voice_id = VOICES[voice]["id"]
    speech_conf.speech_synthesis_voice_name = azure_voice_id

    fmt = fmt2enum.get(audio_format, aof.Audio16Khz32KBitRateMonoMp3)
    speech_conf.set_speech_synthesis_output_format(fmt)

    # Generate a unique filename for the audio output file
    suffix = suffix_for_audiofmt(audio_format)
    out_file = SETTINGS.get_audio_dir() / f"{uuid.uuid4()}.{suffix}"
    try:
        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=str(out_file)
        )  # pyright: ignore[reportGeneralTypeIssues]

        # Init synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_conf, audio_config=audio_config
        )

        result: speechsdk.SpeechSynthesisResult
        # Azure Speech API supports SSML but the notation is a bit different from Amazon Polly's
        # See https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup
        if text_format == "ssml":
            # Adjust speed
            if speed != 1.0:
                text = f'<prosody rate="{speed}">{text}</prosody>'
            # Wrap text in the required <speak> and <voice> tags
            text = f"""
                <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="is-IS">
                <voice name="{azure_voice_id}">
                {text}
                </voice></speak>
            """.strip()
            result = synthesizer.speak_ssml(text)
        else:
            # We're not sending SSML so strip any markup from text
            text = strip_markup(text)
            result = synthesizer.speak_text(text)

        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Success, return path to the generated audio file
            return out_file

        cancellation_details = result.cancellation_details
        raise RuntimeError(
            f"TTS with Azure failed: {cancellation_details.error_details}"
        )
    except Exception:
        _LOG.exception("Error communicating with Azure Speech API.")
        raise


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
