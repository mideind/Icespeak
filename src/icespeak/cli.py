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


Friendly command line interface for Icelandic speech synthesis.
Returns 0 on success, 1 on error.

Run the following command for a list of options:

    tts --help

"""

# ruff: noqa: FBT001, FBT002
# TODO: Transcribe-only option
# TODO: Add separate progress bar for transcription phase
from typing import Annotated, Optional

import shutil
import subprocess
import sys
import wave
from pathlib import Path

try:
    import typer
    from rich import print
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ModuleNotFoundError:
    _TYPER_MISSING = """
To use the command line tool install icespeak with the 'cli' optional dependency:
    python3 -m pip install 'icespeak[cli]'
"""
    print(_TYPER_MISSING, file=sys.stderr)
    sys.exit(1)

from .settings import SETTINGS, AudioFormats, TextFormats
from .tts import VOICES, TTSOptions, tts_to_file


def _write_wav(
    fn: Path,
    data: bytes,
    num_channels: int = 1,
    sample_width: int = 2,
    sample_rate: int = 16000,
) -> None:
    """Write audio data to WAV file. Defaults to 16-bit mono 16 kHz PCM."""
    with wave.open(str(fn), "wb") as wav:
        wav.setnchannels(num_channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(data)


def play_audio_file(path: Path, player: Optional[str] = None) -> None:
    """Play audio file at path via command line player. This only works
    on systems with afplay (macOS), mpv, mpg123 or cmdmp3 installed."""

    cmd: list[str] = []
    if player and (custom := shutil.which(player)):
        cmd = [custom]
    elif afplay := shutil.which("afplay"):
        # afplay is only present on macOS systems
        cmd = [afplay]
    elif mpv := shutil.which("mpv"):
        # mpv is a cross-platform player
        cmd = [mpv]
    elif mpg123 := shutil.which("mpg123"):
        # mpg123 is a cross-platform player
        cmd = [mpg123, "--quiet"]
    elif vlc := shutil.which("vlc"):
        # vlc is a cross-platform player
        cmd = [vlc]
    elif cmdmp3 := shutil.which("cmdmp3"):
        # cmdmp3 is a Windows command line mp3 player
        cmd = [cmdmp3]

    if not cmd:
        print("No CLI audio player found.", file=sys.stderr)
        raise typer.Exit(1)

    cmd.append(str(path))
    print(f"Playing file '{path}'")
    subprocess.run(cmd)  # noqa: S603


DEFAULT_TEXT = "Góðan daginn og til hamingju með lífið."


def _check_voice(voice: str) -> str:
    if voice not in VOICES:
        raise typer.BadParameter(f"Voice {voice!r} is not an available voice.")
    return voice


def _list_voices(run: bool):
    """Print available voices in a table"""
    if run:
        voice_table = Table()  # type: ignore
        voice_table.add_column("Voice")
        voice_table.add_column("Language/Locale")
        voice_table.add_column("Style")
        voice_table.add_column("Service")
        for voice, info in VOICES.items():
            voice_table.add_row(voice, info["lang"], info["style"], info.get("service", "N/A"))
        print(voice_table)
        raise typer.Exit(0)


def _text_to_speech(
    text: Annotated[str, typer.Argument(help="Input text.")] = DEFAULT_TEXT,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Read input text from file instead."),
    ] = None,
    # TTS options
    voice: Annotated[
        str, typer.Option("--voice", "-v", callback=_check_voice, help="TTS voice.")
    ] = SETTINGS.DEFAULT_VOICE,
    speed: Annotated[
        float, typer.Option("--speed", "-s", min=0.5, max=2.0, help="TTS speed.")
    ] = SETTINGS.DEFAULT_VOICE_SPEED,
    text_format: Annotated[TextFormats, typer.Option(help="Input text format.")] = SETTINGS.DEFAULT_TEXT_FORMAT,
    # Transcription options
    transcribe: Annotated[
        bool,
        typer.Option(
            "--transcribe/--no-transcribe",
            "-t/-T",
            help="Transcribe Icelandic text before TTS.",
        ),
    ] = True,
    # Audio options
    play: Annotated[
        bool,
        typer.Option(
            help="Play output audio via CLI audio player.",
        ),
    ] = True,
    player: Annotated[
        Optional[str],
        typer.Option(
            help="Audio player application.",
        ),
    ] = None,
    # Output file options
    out: Annotated[
        Optional[Path],
        typer.Option(
            "--out",
            "-o",
            help="Output file to save audio to (by default the output file isn't kept).",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            help="Force writing to output file.",
        ),
    ] = False,
    audio_format: Annotated[AudioFormats, typer.Option(help="Output audio format.")] = SETTINGS.DEFAULT_AUDIO_FORMAT,
    wav: Annotated[
        Optional[bool],
        typer.Option(
            "--wav",
            help="Write PCM output audio in WAV format.",
        ),
    ] = False,
    # Util
    list_voices: Annotated[
        Optional[bool],
        typer.Option(
            "--list-voices",
            callback=_list_voices,
            is_eager=True,
            help="List the available voices and exit.",
        ),
    ] = False,
) -> None:
    """
    Command line interface to icespeak.

    Provides text-to-speech, transcription of Icelandic text
    and playing synthesized speech.
    """
    if file:
        if text != DEFAULT_TEXT:
            raise typer.BadParameter("Don't specify both text and --file.")
        if not file.is_file():
            raise typer.BadParameter(f"File {file} missing/invalid.")
        text = file.read_text()

    if out and out.exists() and not force:
        # Outfile exists, no --force parameter specified
        raise typer.BadParameter(f"File {out} already exists! Specify --force to overwrite.")
    if force and out and out.is_dir():
        raise typer.BadParameter(f"Cannot overwrite directory {out}.")
    if wav and audio_format != AudioFormats.PCM:
        raise typer.BadParameter('When --wav is specified, --audio-format must be "pcm".')
    if audio_format != SETTINGS.DEFAULT_AUDIO_FORMAT and not out:
        # When asking for specific audio format an output file must be specified
        # We're assuming that the user wants to keep the audio file,
        # because without --out icespeak simply removes the file.
        raise typer.BadParameter("Specify --out file if specifying --audio-format or --wav.")
    if transcribe and VOICES[voice]["lang"] != "is-IS":
        transcribe = False
        print("Transcription disabled, as the voice isn't Icelandic.", file=sys.stderr)

    # Finished validating arguments

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:  # type: ignore
        progress.add_task("Synthesizing text...", total=None)
        # Synthesize the text according to CLI options
        tts_out = tts_to_file(
            text,
            TTSOptions(
                text_format=text_format,
                audio_format=audio_format,
                voice=voice,
                speed=speed,
            ),
            transcribe=transcribe,
        )

    # Finished transcribing and synthesizing speech

    if out:
        if wav:
            # Rewrite file in WAV format
            _write_wav(out, tts_out.file.read_bytes())
        else:
            # Otherwise simply copy the file
            # (or move, doesn't matter, icespeak cleans up)
            shutil.copy(tts_out.file, out)
    else:
        out = tts_out.file

    # Play audio

    if play:
        play_audio_file(out, player)


def main():
    typer.run(_text_to_speech)


if __name__ == "__main__":
    main()
