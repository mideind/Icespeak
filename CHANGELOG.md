# Changelog

All notable changes to Icespeak are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-04

### Removed

- Dropped support for Python 3.9, which reached end of life in October 2025.
  Icespeak now requires Python 3.10 or newer.
- Removed the Piper TTS dependency, as the project is barely maintained and only
  supports Python 3.10 and 3.11. The `icespeak.voices.piper_tts` module is still
  present but is no longer wired up and requires an external `piper` executable.

### Changed

- **The default voice is now `Gunnar` (Azure), was `Gudrun`.**
- **The default text format is now `text`, was `ssml`.**
- **The default audio format is now `wav`, was `mp3`.**
- Audio result caching is currently disabled, so repeated calls with identical
  arguments will synthesize the audio again.
- The command line tool is named `speak` (it was documented as `tts` in older
  READMEs, but the entry point has been `speak` for some time).
- The `cli` extra now depends on `typer>=0.15.0` instead of pinning `typer[all]==0.9.0`.
- API keys are read from the `ICESPEAK_*_API_KEY` environment variables or a
  `.env` file. Reading them from files in a `keys/` directory still works as a
  fallback, but a missing keys directory no longer logs a warning.
- Package metadata now declares the license as the SPDX expression
  `GPL-3.0-or-later` and advertises support for Python 3.10 through 3.13.

### Added

- HD variants of the OpenAI voices (`alloy_hd`, `echo_hd`, `fable_hd`, `onyx_hd`,
  `nova_hd`, `shimmer_hd`), which synthesize using the `tts-1-hd` model.
- Documentation for the `speak` command line tool in the README.
- A release workflow that publishes to PyPI via Trusted Publishing on tag push.

### Fixed

- Fixed a bug where the last words of a transcription could be dropped.
- Fixed SSML markup being added to text that is not in SSML format.
- Fixed a number of transcription errors involving months, floats and integers,
  and Roman numerals.
- Pull request CI now actually runs; the workflow was filtering on a `main`
  branch that does not exist in this repository.
- Tests no longer fail outright when no TTS API keys are configured.

## [0.3.7] - 2024-10-29

Releases up to and including 0.3.7 predate this changelog. See the
[release history](https://github.com/mideind/Icespeak/releases) on GitHub.

[0.4.0]: https://github.com/mideind/Icespeak/compare/v0.3.7...v0.4.0
[0.3.7]: https://github.com/mideind/Icespeak/releases/tag/v0.3.7
