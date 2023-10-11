#!/usr/bin/env python3

"""Evaluate different voices for TTS using predefined voices and text snippets.

Read the text snippets from a file called 'tts_voice_lines.txt' in the current directory.
Read the available voices from the Icespeak package.

The text snippets are read from the file line by line, and each line is used as input
to the TTS engine. The text snippets are assumed to be in the Icelandic language.
After generating the audio data for each text snippet, the audio data is saved to a
file in the current directory. The file name is constructed from the sentence read.
The wav file is automatically played back after it has been saved.

After the audio has been played back, the user is prompted to enter a rating for the
voice used to generate the audio. The rating is a number between 1 and 5, where 1 is
the worst and 5 is the best. The rating is saved to a file called 'tts_ratings.tsv'.
Each voice is rated for 'naturalness' and 'correctness'.

The user is prompted to enter a rating for each voice for each text snippet.
The user can also enter 's' to skip the current text snippet, or 'q' to quit the
evaluation process and 'r' to repeat the current sound.

The results are saved continuously to the file 'tts_ratings.tsv'. If the program is
interrupted, the results can be read from this file and the evaluation process can
be resumed at a later time.
"""

from typing import Any

import sys
from pathlib import Path

from icespeak import VOICES, TTSOptions, tts_to_file
from icespeak.cli import play_audio_file

try:
    import typer
    from rich import print
except ModuleNotFoundError:
    _TYPER_MISSING = """
To use the command line tool install icespeak with the 'cli' optional dependency:
    python3 -m pip install 'icespeak[cli]'
"""
    print(_TYPER_MISSING, file=sys.stderr)
    sys.exit(1)

voice_lines_file = Path(__file__).with_name("tts_voice_lines.txt")
tts_ratings_file = Path(__file__).with_name("tts_ratings.tsv")

app = typer.Typer()


def _die(msg: str, exit_code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise typer.Exit(1)


@app.command()
def evaluate():
    # Read the voices to be evaluated
    voices = [k for (k, v) in VOICES.items() if v["lang"] == "is-IS"]
    if not voices:
        _die("No voices to evaluate.")
    texts = [line for line in voice_lines_file.read_text().split("\n") if line.strip()]
    if not texts:
        _die("No text snippets to evaluate.")
    # read the ratings file
    ratings = {}
    try:
        with tts_ratings_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    voice, text, naturalness, correctness = line.split("\t")
                    ratings[(voice, text)] = (naturalness, correctness)
    except FileNotFoundError:
        pass
    # Evaluate each voice for each text snippet
    for text in texts:
        for voice in voices:
            # Skip text snippets that have already been rated
            if (voice, text) in ratings:
                print(f"Skipping {voice} for '{text}'")
                continue
            # Synthesize speech
            fn = tts_to_file(text, TTSOptions(voice=voice)).file
            # Play it
            play_audio_file(fn)
            # And display the text
            print(f"Text: '{text}'")
            # Prompt user to enter a rating
            while True:
                naturalness = input("Naturalness (1-5): ")
                if naturalness == "r":
                    play_audio_file(fn)
                    continue
                if naturalness == "q":
                    return
                if naturalness == "s":
                    break
                if naturalness.isdigit():
                    naturalness = int(naturalness)
                    if 1 <= naturalness <= 5:
                        break
            if naturalness == "s":
                continue
            while True:
                correctness = input("Correctness (1-5): ")
                if correctness == "r":
                    play_audio_file(fn)
                if correctness == "q":
                    return
                if correctness == "s":
                    break
                if correctness.isdigit():
                    correctness = int(correctness)
                    if 1 <= correctness <= 5:
                        break
            if correctness == "s":
                continue
            # Save the rating
            with tts_ratings_file.open("a") as f:
                f.write(f"{voice}\t{text}\t{naturalness}\t{correctness}\n")
    # Done
    print("Done.")


@app.command()
def report():
    """Read the ratings file and report average correctness and naturalness of each voice."""
    # Read the ratings file
    ratings: dict[str, Any] = {}
    try:
        with tts_ratings_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    voice, _, naturalness, correctness = line.split("\t")
                    naturalness = int(naturalness)
                    correctness = int(correctness)
                    if voice not in ratings:
                        ratings[voice] = ([], [])
                    ratings[voice][0].append(naturalness)
                    ratings[voice][1].append(correctness)
    except FileNotFoundError:
        _die("No ratings file found.")
    # Report results
    for voice, (naturalness, correctness) in ratings.items():
        print(
            f"{voice}: naturalness={sum(naturalness) / len(naturalness):.2f} correctness={sum(correctness) / len(correctness):.2f}"
        )


@app.command()
def stats():
    """Report statistics on the ratings.

    - number of ratings per voice
    - number of ratings per text snippet
    - most difficult (according to correctness) text snippet)
    - most difficult (according to naturalness) text snippet)
    """
    # Read the ratings file
    ratings: dict[str, Any] = {}
    max_count_for_difficulty = 5
    try:
        with tts_ratings_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    voice, text, naturalness, correctness = line.split("\t")
                    naturalness = int(naturalness)
                    correctness = int(correctness)
                    if voice not in ratings:
                        ratings[voice] = {}
                    if text not in ratings[voice]:
                        ratings[voice][text] = ([], [])
                    ratings[voice][text][0].append(naturalness)
                    ratings[voice][text][1].append(correctness)
    except FileNotFoundError:
        _die("No ratings file found.")
    # Report results
    print("Number of ratings per voice:")
    for voice, texts in ratings.items():
        print(f"{voice}: {len(texts.values())}")
    # create a better datastructure for texts
    text_raitings: dict[str, Any] = {}
    for texts in ratings.values():
        for text, (naturalness, correctness) in texts.items():
            if text not in text_raitings:
                text_raitings[text] = ([], [])
            text_raitings[text][0].append(sum(naturalness) / len(naturalness))
            text_raitings[text][1].append(sum(correctness) / len(correctness))
    print("Number of ratings per text snippet:")
    for text, (naturalness, _) in text_raitings.items():
        print(f"{text}: {len(naturalness)}")
    count = 0
    # sort the texts by correctness
    print("Most difficult (according to correctness) text snippet:")
    for text, (_, correctness) in sorted(
        text_raitings.items(), key=lambda x: sum(x[1][1]) / len(x[1][1]), reverse=False
    ):
        print(f"{text}: {sum(correctness) / len(correctness):.2f}")
        count += 1
        if count >= max_count_for_difficulty:
            break
    count = 0
    # sort the texts by naturalness
    print("Most difficult (according to naturalness) text snippet:")
    for text, (naturalness, _) in sorted(
        text_raitings.items(), key=lambda x: sum(x[1][0]) / len(x[1][0]), reverse=False
    ):
        print(f"{text}: {sum(naturalness) / len(naturalness):.2f}")
        count += 1
        if count >= max_count_for_difficulty:
            break


if __name__ == "__main__":
    app()
