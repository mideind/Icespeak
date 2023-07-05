"""

    Icespeak - Icelandic TTS library

    Copyright (C) 2023 Miðeind ehf.  All rights reserved.


    Icelandic-language text to speech via the MS Azure Speech API.

"""

from typing import Optional

import json
import pathlib
import uuid
from logging import getLogger

import azure.cognitiveservices.speech as speechsdk  # pyright: ignore[reportMissingTypeStubs]

from icespeak.trans import DefaultTranscriber, strip_markup

from . import AUDIO_SCRATCH_DIR, KEYS_DIR, suffix_for_audiofmt

_LOG = getLogger(__file__)
NAME = "Azure Cognitive Services"
AUDIO_FORMATS = frozenset(("mp3", "pcm", "opus"))
_VOICE_TO_ID = {
    # Icelandic
    "Gudrun": "is-IS-GudrunNeural",
    "Gunnar": "is-IS-GunnarNeural",
    # English (UK)
    "Abbi": "en-GB-AbbiNeural",
    "Alfie": "en-GB-AlfieNeural",
    # English (US)
    "Jenny": "en-US-JennyNeural",
    "Brandon": "en-US-BrandonNeural",
    # French
    "Brigitte": "fr-FR-BrigitteNeural",
    "Alain": "fr-FR-AlainNeural",
    # German
    "Amala": "de-DE-AmalaNeural",
    # Danish
    "Christel": "da-DK-ChristelNeural",
    "Jeppe": "da-DK-JeppeNeural",
    # Swedish
    "Sofie": "sv-SE-SofieNeural",
    "Mattias": "sv-SE-MattiasNeural",
    # Norwegian
    "Finn": "nb-NO-FinnNeural",
    "Iselin": "nb-NO-IselinNeural",
    # Spanish
    "Abril": "es-ES-AbrilNeural",
    "Alvaro": "es-ES-AlvaroNeural",
    # Polish
    "Agnieszka": "pl-PL-AgnieszkaNeural",
    "Marek": "pl-PL-MarekNeural",
    # Many more voices available, see:
    # https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support
}
VOICES = frozenset(_VOICE_TO_ID.keys())
_DEFAULT_VOICE_ID = "is-IS-GudrunNeural"

# The Azure Speech API access key
# You must obtain your own key if you want to use this code
# JSON format is the following:
# {
#     "key": ""my_key",
#     "region": "my_region",
# }
#
_AZURE_KEYFILE_NAME = "AzureSpeechServerKey.json"

_AZURE_API_KEY_PATH = str(KEYS_DIR / _AZURE_KEYFILE_NAME)

_AZURE_API_KEY = ""
_AZURE_API_REGION = ""


def _azure_api_key() -> tuple[str, str]:
    """Lazy-load API key and region from JSON and return as tuple."""
    global _AZURE_API_KEY
    global _AZURE_API_REGION

    if _AZURE_API_KEY and _AZURE_API_REGION:
        return (_AZURE_API_KEY, _AZURE_API_REGION)

    try:
        with open(_AZURE_API_KEY_PATH) as json_file:
            js = json.load(json_file)
            _AZURE_API_KEY = js["key"]
            _AZURE_API_REGION = js["region"]
    except Exception as e:
        _LOG.warning(f"Unable to read Azure Speech API credentials: {e}")

    return (_AZURE_API_KEY, _AZURE_API_REGION)


def _synthesize_text(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float = 1.0,
    **kwargs,
) -> Optional[str]:
    """Synthesizes text via Azure and returns path to generated audio file."""

    if audio_format not in AUDIO_FORMATS:
        _LOG.warn(
            f"Unsupported audio format for Azure speech synthesis: {audio_format}."
            " Falling back to mp3"
        )
        audio_format = "mp3"

    # Audio format enums for Azure Speech API
    # https://learn.microsoft.com/en-us/javascript/api/microsoft-cognitiveservices-speech-sdk/speechsynthesisoutputformat
    aof = speechsdk.SpeechSynthesisOutputFormat
    fmt2enum = {
        "mp3": aof.Audio16Khz32KBitRateMonoMp3,
        "pcm": aof.Raw16Khz16BitMonoPcm,
        "opus": aof.Ogg16Khz16BitMonoOpus,
    }

    try:
        # Configure speech synthesis
        (key, region) = _azure_api_key()
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        azure_voice_id = _VOICE_TO_ID.get(voice_id) or _DEFAULT_VOICE_ID
        speech_config.speech_synthesis_voice_name = azure_voice_id
        fmt = fmt2enum.get(audio_format, aof.Audio16Khz32KBitRateMonoMp3)
        speech_config.set_speech_synthesis_output_format(fmt)

        # Generate a unique filename for the audio output file
        suffix = suffix_for_audiofmt(audio_format)
        out_fn: str = str(AUDIO_SCRATCH_DIR / f"{uuid.uuid4()}.{suffix}")
        audio_config = speechsdk.audio.AudioOutputConfig(filename=out_fn)  # type: ignore

        # Init synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

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
            speak_fn = synthesizer.speak_ssml
        else:
            # We're not sending SSML so strip any markup from text
            text = strip_markup(text)
            speak_fn = synthesizer.speak_text

        # Feed text into speech synthesizer
        result = speak_fn(text)

        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Return path to generated audio file
            assert pathlib.Path(out_fn).exists()
            return out_fn
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            _LOG.error(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                _LOG.error(f"Azure TTS error: {cancellation_details.error_details}")
    except Exception as e:
        _LOG.error(f"Error communicating with Azure Speech API: {e}")


def text_to_audio_data(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float = 1.0,
) -> Optional[bytes]:
    """Feeds text to Azure Speech API and returns audio data received from server."""
    audio_file_path = _synthesize_text(**locals())
    if audio_file_path:
        try:
            # Read audio data from file and return it
            with open(audio_file_path, "rb") as f:
                return f.read()
        except Exception as e:
            _LOG.error(
                f"Azure: Error reading synthesized audio file {audio_file_path}: {e}"
            )
    return None


def text_to_audio_url(
    text: str,
    text_format: str,
    audio_format: str,
    voice_id: str,
    speed: float = 1.0,
) -> Optional[str]:
    """Returns URL for speech-synthesized text."""

    audio_file_path = _synthesize_text(**locals())
    if audio_file_path:
        # Generate and return file:// URL to audio file
        return pathlib.Path(audio_file_path).as_uri()
    return None


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
