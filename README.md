[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Release](https://shields.io/github/v/release/mideind/Icespeak?display_name=tag)]()
[![PyPI](https://img.shields.io/pypi/v/icespeak?logo=pypi)](https://pypi.org/project/icespeak/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![tests](https://github.com/mideind/Icespeak/actions/workflows/main.yml/badge.svg)]()

# Icespeak

_Icespeak_ is a Python 3.9+ library that makes Icelandic-language speech synthesis easy.

## Local installation

> _Note: The Azure TTS package currently only supports OpenSSL version 3.0.\*_

Clone the repository and cd into the folder.
Then create and activate a virtual environment:

```sh
python3 -m venv venv
source venv/bin/activate
```

Install minimal set of dependencies to use the library:

```sh
python3 -m pip install .
```

In order to use the CLI interface, `tts`, install with:

```sh
python3 -m pip install '.[cli]'
```

Alternatively, to install in editable mode with extra dev dependencies:

```sh
python3 -m pip install -e '.[dev]'
```

## Usage

Before using, place API keys for the relevant services in the `/keys` folder
(or a folder specified by the `ICESPEAK_KEYS_DIR` environment variable).

Alternately, you can set the following environment variables:

```sh
export ICESPEAK_AWSPOLLY_API_KEY=your-aws-polly-api-key
export ICESPEAK_AZURE_API_KEY=your-azure-api-key
export ICESPEAK_GOOGLE_API_KEY=your-google-api-key
export ICESPEAK_OPENAI_API_KEY=your-openai-api-key
```

Output audio files are saved to the directory specified
by the `ICESPEAK_AUDIO_DIR` environment variable.
By default Icespeak creates the directory `<TEMP DIR>/icespeak`
where `<TEMP DIR>` is the temporary directory on your platform,
fetched via `tempfile.gettempdir()`.

By default, generated audio files are removed upon a clean exit,
but this can be disabled by setting `ICESPEAK_AUDIO_CACHE_CLEAN=0`.

### Text-to-speech

Simple example of TTS, which includes phonetic transcription:

```py
from icespeak import tts_to_file, TTSOptions
text = """\
Þetta er texti fyrir talgervingu. \
Í honum er ýmislegt sem mætti vera hljóðritað, \
t.d. ræður talgerving oft illa við íslenskar skammstafanir, \
tölvupósta eins og ekki.tolvupostur@vefsida.is,
eða prósentur eins og 48,3%, o.fl.\
"""
tts_out = tts_to_file(
    text,
    TTSOptions(
        text_format="text", # Set to 'ssml' if SSML tags in text should be interpreted
        audio_format="mp3", # Output audio will be in mp3 format
        voice="Gudrun" # Azure TTS voice
    ),
    transcribe=True # Default is True
)
print(tts_out.file) # pathlib.Path instance pointing to file on local file system
print(tts_out.text) # text that was sent to the TTS service (after the phonetic transcription)
```

Results are cached, so subsequent calls with the same arguments should be fast.

## License

Icespeak is Copyright &copy; 2024 [Miðeind ehf.](https://mideind.is)

<a href="https://mideind.is"><img src="https://github.com/mideind/Icespeak/blob/master/img/mideind_logo.png?raw=true" alt="Miðeind ehf."
    width="214" height="66" align="right" style="margin-left:20px; margin-bottom: 20px;"></a>

This set of programs is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any later
version.

This set of programs is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See the GNU General Public License for more details.

<a href="https://www.gnu.org/licenses/gpl-3.0.html"><img src="https://github.com/mideind/Icespeak/blob/master/img/GPLv3.png?raw=true"
align="right" style="margin-left:15px;" width="180" height="60"></a>

The full text of the GNU General Public License v3 is
[included here](https://github.com/mideind/Icespeak/LICENSE.txt)
and also available here: [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html).

If you wish to use this set of programs in ways that are not covered under the
GNU GPLv3 license, please contact us at [mideind@mideind.is](mailto:mideind@mideind.is)
to negotiate a custom license. This applies for instance if you want to include or use
this software, in part or in full, in other software that is not licensed under
GNU GPLv3 or other compatible licenses.
