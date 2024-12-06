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


"""

from __future__ import annotations

from typing_extensions import override

import shlex
import shutil
import subprocess
from logging import getLogger
from pathlib import Path

from icespeak.settings import SETTINGS, Keys

from . import BaseVoice, ModuleAudioFormatsT, ModuleVoicesT, TTSOptions

_LOG = getLogger(__name__)


class PiperVoice(BaseVoice):
    _NAME: str = "Piper"
    _VOICES: ModuleVoicesT = {
        "bui": {"id": "bui-medium", "lang": "is_IS", "style": "male"},
        "salka": {"id": "salka-medium", "lang": "is_IS", "style": "male"},
        "steinn": {"id": "steinn-medium", "lang": "is_IS", "style": "male"},
        "ugla": {"id": "ugla-medium", "lang": "is_IS", "style": "male"},
    }
    _AUDIO_FORMATS: ModuleAudioFormatsT = frozenset({"pcm", "wav"})

    @property
    @override
    def name(self) -> str:
        return PiperVoice._NAME

    @property
    @override
    def voices(self) -> ModuleVoicesT:
        return PiperVoice._VOICES

    @property
    @override
    def audio_formats(self) -> ModuleAudioFormatsT:
        return PiperVoice._AUDIO_FORMATS

    @override
    def load_api_keys(self) -> None:
        _LOG.debug("Loading API keys for Piper unnecessarily. PiperVoice does not require API keys")

    def _get_piper_executable(self) -> Path:
        piper_path = shutil.which("piper")
        if not piper_path:
            raise RuntimeError("Piper executable not found in PATH")
        return Path(piper_path)

    @override
    def text_to_speech(self, text: str, options: TTSOptions, keys_override: Keys | None = None) -> Path:
        if keys_override:
            _LOG.debug("Using key override for Piper. PiperVoice does not require API keys")

        try:
            outfile = SETTINGS.get_empty_file(options.audio_format)
            audio_dir = SETTINGS.get_audio_dir()
            piper_args = {
                "model": shlex.quote(f"{self.voices[options.voice]['lang']}-{self.voices[options.voice]['id']}"),
                "voice": PiperVoice._VOICES[options.voice]["id"],
                "input": shlex.quote(text),
                "output_file": str(outfile),
                "data_dir": str(audio_dir / "Piper"),
            }
            _LOG.debug("Synthesizing with Piper: %s", piper_args)
            # NOTE: Piper only allows logging to be set to DEBUG or INFO level. Now stderr is suppressed.
            piper_path = self._get_piper_executable()
            if options.audio_format == "pcm":
                with outfile.open("w") as f:
                    subprocess.run(  # noqa: S603
                        [
                            piper_path,
                            "--model",
                            piper_args["model"],
                            "--output_raw",
                            "--data-dir",
                            piper_args["data_dir"],
                            "--download_dir",
                            piper_args["data_dir"],
                        ],
                        input=piper_args["input"],
                        text=True,
                        check=True,
                        stdout=f,
                        stderr=subprocess.DEVNULL,
                    )
            elif options.audio_format == "wav":
                subprocess.run(  # noqa: S603
                    [
                        piper_path,
                        "--model",
                        piper_args["model"],
                        "--output_file",
                        piper_args["output_file"],
                        "--data-dir",
                        piper_args["data_dir"],
                        "--download_dir",
                        piper_args["data_dir"],
                    ],
                    input=piper_args["input"],
                    text=True,
                    check=True,
                    capture_output=True,
                )
            else:
                raise ValueError(f"Unsupported Piper audio format: {options.audio_format}")

        except Exception:
            _LOG.exception("Piper TTS failed")
            raise

        return outfile


# TODO: Add option to use GPU. This requires onnxruntime-gpu, the --cuda flag and a functioning CUDA environment.
