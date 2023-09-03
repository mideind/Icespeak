[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![tests](https://github.com/mideind/Icespeak/actions/workflows/main.yml/badge.svg)]()
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# Icespeak

_Icespeak_ is a Python library that makes Icelandic-language speech synthesis easy.

## Installation

> _Note: The Azure package currently only supports the very out-dated OpenSSL version 1.\*._

Clone the repository and cd into the folder. Then create and activate
a Python virtual environment, and install all required dependencies:

```sh
python3 -m venv venv
source venv/bin/activate
python3 -m pip install .
# Alternatively, to install in editable mode with extra dev dependencies:
python3 -m pip install -e '.[dev]'
```

## Usage

### Text-to-speech

Simple example of TTS, which includes phonetic transcription:

```python
from icespeak import text_to_speech, TTSOptions
audio_file = text_to_speech(
    "Hér kemur texti fyrir talgervingu. Ýmislegir textabútar eru hljóðritaðir eins og t.d. ekki.til@vefsida.is, 48,3% o.fl.",
    TTSOptions(
        text_format="text", # Set to 'ssml' if ssml tags in text should be interpreted
        audio_format="mp3", # Output audio will be in mp3 format
        voice="Gudrun" # Azure TTS voice
    ),
    trancribe=True # Default is True
)
print(audio_file) # pathlib.Path instance pointing to file on local file system
```

### Transcription

_Documentation still in progress._

### Text composition via GSSML

_Documentation still in progress._

## License

Icespeak is Copyright &copy; 2023 [Miðeind ehf.](https://mideind.is)

<a href="https://mideind.is"><img src="./img/mideind_logo.png" alt="Miðeind ehf."
    width="214" height="66" align="right" style="margin-left:20px; margin-bottom: 20px;"></a>

This set of programs is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any later
version.

This set of programs is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

<a href="https://www.gnu.org/licenses/gpl-3.0.html"><img src="./img/GPLv3.png"
align="right" style="margin-left:15px;" width="180" height="60"></a>

The full text of the GNU General Public License v3 is
[included here](./LICENSE.txt)
and also available here: [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html).

If you wish to use this set of programs in ways that are not covered under the
GNU GPLv3 license, please contact us at [mideind@mideind.is](mailto:mideind@mideind.is)
to negotiate a custom license. This applies for instance if you want to include or use
this software, in part or in full, in other software that is not licensed under
GNU GPLv3 or other compatible licenses.
