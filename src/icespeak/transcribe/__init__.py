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


This file contains phonetic transcription functionality
turning data/text into text specifically intended
for Icelandic speech synthesis engines.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Union, cast

import itertools
import re
from functools import lru_cache
from logging import getLogger
from re import Match

from islenska.basics import ALL_CASES, ALL_GENDERS, ALL_NUMBERS
from pydantic import BaseModel, Field
from reynir import Greynir
from reynir.bindb import GreynirBin
from tokenizer import TOK, Abbreviations, Tok, detokenize, tokenize
from tokenizer.definitions import (
    CURRENCY_SYMBOLS,
    HYPHENS,
    AmountTuple,
    CurrencyTuple,
    DateTimeTuple,
    NumberTuple,
    PunctuationTuple,
)

from icespeak.settings import TRACE

from .num import (
    ROMAN_NUMERALS,
    CaseType,
    GenderType,
    NumberType,
    digits_to_text,
    float_to_text,
    floats_to_text,
    number_to_ordinal,
    number_to_text,
    numbers_to_ordinal,
    numbers_to_text,
    roman_numeral_to_ordinal,
    year_to_text,
    years_to_text,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from reynir.simpletree import SimpleTree

# Ensure abbreviations have been loaded
Abbreviations.initialize()
_LOG = getLogger(__name__)


def strip_markup(text: str) -> str:
    """Remove HTML/SSML tags from a string."""
    return re.sub(r"<.*?>", "", text)


class TranscriptionOptions(BaseModel):
    """Transcription options."""

    # frozen=True makes this hashable which enables caching
    model_config = {"frozen": True, "extra": "forbid"}

    emails: bool = Field(default=True, description="Whether to transcribe emails.")
    dates: bool = Field(default=True, description="Whether to transcribe dates.")
    years: bool = Field(default=True, description="Whether to transcribe years.")
    domains: bool = Field(default=True, description="Whether to transcribe domains.")
    urls: bool = Field(default=True, description="Whether to transcribe URLs.")
    amounts: bool = Field(
        default=True,
        description="Whether to transcribe amounts (number with currency).",
    )
    measurements: bool = Field(
        default=True,
        description="Whether to transcribe measurements " + "(number with unit of measurement).",
    )
    percentages: bool = Field(default=True, description="Whether to transcribe percentages.")
    # These are experimental, turned off by default
    numbers: bool = Field(default=False, description="Whether to transcribe (cardinal) numbers.")
    ordinals: bool = Field(default=False, description="Whether to transcribe ordinal numbers.")
    # TODO: Add slower option which parses text


def _currency_to_gender(code: str) -> GenderType:
    non_kvk_currencies: Mapping[str, GenderType] = {
        # KK
        "USD": "kk",
        "CHF": "kk",
        "CAD": "kk",
        # HK
        "GBP": "hk",
        "JPY": "hk",
        "PLN": "hk",
        "CNY": "hk",
        "RMB": "hk",
        "ZAR": "hk",
    }
    return non_kvk_currencies.get(code, "kvk")


_KK_UNITS = frozenset(
    (
        "m",
        "mm",
        "μm",
        "cm",
        "sm",
        "km",
        "m²",
        "fm",
        "km²",
        "cm²",
        "ha",
        "m³",
        "cm³",
        "km³",
        "l",
        "ltr",
        "dl",
        "cl",
        "ml",
        "m/s",
        "km/klst",
    )
)
_KVK_UNITS = frozenset(
    (
        "mi",
        "bbl",
        "K",
        "°K",
        "°C",
        "°F",
        "s",
        "ms",
        "μs",
        "klst",
        "mín",
        "kWh",
        "MWh",
        "kWst",
        "MWst",
        "kcal",
        "cal",
        "°",
        "%",
    )
)


def _unit_to_gender(unit: str) -> GenderType:
    if unit in _KK_UNITS:
        return "kk"
    if unit in _KVK_UNITS:
        return "kvk"
    return "hk"


# HACK: Inflect at runtime instead of hardcoding, doesn't deal with other cases
_SI_UNIT_NAMES: Mapping[str, Mapping[NumberType, str]] = {
    # Distance
    "m": {"et": "metri", "ft": "metrar"},
    "mm": {"et": "millimetri", "ft": "millimetrar"},
    "μm": {"et": "míkrómetri", "ft": "míkrómetrar"},
    "cm": {"et": "sentimetri", "ft": "sentimetrar"},
    "sm": {"et": "sentimetri", "ft": "sentimetrar"},
    "km": {"et": "kílómetri", "ft": "kílómetrar"},
    "ft": {"et": "fet", "ft": "fet"},
    "mi": {"et": "míla", "ft": "mílur"},
    # Area
    "m²": {"et": "fermetri", "ft": "fermetrar"},
    "fm": {"et": "fermetri", "ft": "fermetrar"},
    "km²": {"et": "ferkílómetri", "ft": "ferkílómetrar"},
    "cm²": {"et": "fersentimetri", "ft": "fersentimetrar"},
    "ha": {"et": "hektari", "ft": "hektarar"},
    # Volume
    "m³": {"et": "rúmmetri", "ft": "rúmmetrar"},
    "cm³": {"et": "rúmsentimetri", "ft": "rúmsentimetrar"},
    "km³": {"et": "rúmkílómetri", "ft": "rúmkílómetrar"},
    "l": {"et": "lítri", "ft": "lítrar"},
    "ltr": {"et": "lítri", "ft": "lítrar"},
    "dl": {"et": "desilítri", "ft": "desilítrar"},
    "cl": {"et": "sentilítri", "ft": "sentilítrar"},
    "ml": {"et": "millilítri", "ft": "millilítrar"},
    "gal": {"et": "gallon", "ft": "gallon"},
    "bbl": {"et": "tunna", "ft": "tunnur"},
    # Temperature
    "K": {"et": "kelvíngráða", "ft": "kelvíngráður"},
    "°K": {"et": "kelvíngráða", "ft": "kelvíngráður"},
    "°C": {"et": "gráða á selsíus", "ft": "gráður á selsíus"},
    "°F": {"et": "Fahrenheit-gráða", "ft": "Fahrenheit-gráður"},
    # Mass
    "g": {"et": "gramm", "ft": "grömm"},
    "gr": {"et": "gramm", "ft": "grömm"},
    "kg": {"et": "kílógramm", "ft": "kílógrömm"},
    "t": {"et": "tonn", "ft": "tonn"},
    "mg": {"et": "milligramm", "ft": "milligrömm"},
    "μg": {"et": "míkrógramm", "ft": "míkrógrömm"},
    "tn": {"et": "tonn", "ft": "tonn"},
    "lb": {"et": "pund", "ft": "pund"},
    # Duration
    "s": {"et": "sekúnda", "ft": "sekúndur"},
    "ms": {"et": "millisekúnda", "ft": "millisekúndur"},
    "μs": {"et": "míkrósekúnda", "ft": "míkrósekúndur"},
    "klst": {"et": "klukkustund", "ft": "klukkustundir"},
    "mín": {"et": "mínúta", "ft": "mínútur"},
    # Force
    "N": {"et": "njúton", "ft": "njúton"},
    "kN": {"et": "kílónjúton", "ft": "kílónjúton"},
    # Energy
    "J": {"et": "júl", "ft": "júl"},
    "kJ": {"et": "kílójúl", "ft": "kílójúl"},
    "MJ": {"et": "megajúl", "ft": "megajúl"},
    "GJ": {"et": "gígajúl", "ft": "gígajúl"},
    "TJ": {"et": "terajúl", "ft": "terajúl"},
    "kWh": {"et": "kílóvattstund", "ft": "kílóvattstundir"},
    "MWh": {"et": "megavattstund", "ft": "megavattstundir"},
    "kWst": {"et": "kílóvattstund", "ft": "kílóvattstundir"},
    "MWst": {"et": "megavattstund", "ft": "megavattstundir"},
    "kcal": {"et": "kílókaloría", "ft": "kílókaloríur"},
    "cal": {"et": "kaloría", "ft": "kaloríur"},
    # Power
    "W": {"et": "vatt", "ft": "vött"},
    "mW": {"et": "millivatt", "ft": "millivött"},
    "kW": {"et": "kílóvatt", "ft": "kílóvött"},
    "MW": {"et": "megavatt", "ft": "megavött"},
    "GW": {"et": "gígavatt", "ft": "gígavött"},
    "TW": {"et": "teravatt", "ft": "teravött"},
    # Electric potential
    "V": {"et": "volt", "ft": "volt"},
    "mV": {"et": "millivolt", "ft": "millivolt"},
    "kV": {"et": "kílóvolt", "ft": "kílóvolt"},
    # Electric current
    "A": {"et": "amper", "ft": "amper"},
    "mA": {"et": "milliamper", "ft": "milliamper"},
    # Frequency
    "Hz": {"et": "herts", "ft": "herts"},
    "kHz": {"et": "kílóherts", "ft": "kílóherts"},
    "MHz": {"et": "megaherts", "ft": "megaherts"},
    "GHz": {"et": "gígaherts", "ft": "gígaherts"},
    # Pressure
    "Pa": {"et": "paskal", "ft": "pasköl"},
    "kPa": {"et": "kílópaskal", "ft": "kílópasköl"},
    "hPa": {"et": "hektópaskal", "ft": "hektópasköl"},
    # Angle
    "°": {"et": "gráða", "ft": "gráður"},
    # Percentage and promille
    "%": {"et": "prósenta", "ft": "prósentur"},
    "‰": {"et": "prómill", "ft": "prómill"},
    # Velocity
    "m/s": {"et": "metri á sekúndu", "ft": "metrar á sekúndu"},
    "km/klst": {"et": "kílómetri á klukkustund", "ft": "kílómetrar á klukkustund"},
}


# Spell out how character names are pronounced in Icelandic
_CHAR_PRONUNCIATION: Mapping[str, str] = {
    "a": "a",
    "á": "á",
    "b": "bé",
    "c": "sé",
    "d": "dé",
    "ð": "eð",
    "e": "e",
    "é": "é",
    "f": "eff",
    "g": "gé",
    "h": "há",
    "i": "i",
    "í": "í",
    "j": "joð",
    "k": "ká",
    "l": "ell",
    "m": "emm",
    "n": "enn",
    "o": "o",
    "ó": "ó",
    "p": "pé",
    "q": "kú",
    "r": "err",
    "s": "ess",
    "t": "té",
    "u": "u",
    "ú": "ú",
    "v": "vaff",
    "w": "tvöfalt vaff",
    "x": "ex",
    "y": "ufsilon",
    "ý": "ufsilon í",
    "þ": "þoddn",
    "æ": "æ",
    "ö": "ö",
    "z": "seta",
}

# Icelandic/English alphabet, uppercased
ALPHABET = "".join(c.upper() for c in _CHAR_PRONUNCIATION)


_PUNCTUATION_NAMES: Mapping[str, str] = {
    " ": "bil",
    "~": "tilda",
    "`": "broddur",
    "!": "upphrópunarmerki",
    "@": "att merki",
    "#": "myllumerki",
    "$": "dollaramerki",
    "%": "prósentumerki",
    "^": "tvíbroddur",
    "&": "og merki",
    "*": "stjarna",
    "(": "vinstri svigi",
    ")": "hægri svigi",
    "-": "bandstrik",  # in some cases this should be "mínus"
    "_": "niðurstrik",
    "=": "jafnt og merki",
    "+": "plús",
    "[": "vinstri hornklofi",
    "{": "vinstri slaufusvigi",
    "]": "hægri hornklofi",
    "}": "hægri slaufusvigi",
    "\\": "bakstrik",
    "|": "pípumerki",
    ";": "semíkomma",
    ":": "tvípunktur",
    "'": "úrfellingarkomma",
    '"': "tvöföld gæsalöpp",
    ",": "komma",
    "<": "vinstri oddklofi",
    ".": "punktur",
    ">": "hægri oddklofi",
    "/": "skástrik",
    "?": "spurningarmerki",
    # Less common symbols
    "°": "gráðumerki",
    "±": "plús-mínus merki",
    # "-": "stutt þankastrik",
    "—": "þankastrik",
    "…": "úrfellingarpunktar",
    "™": "vörumerki",
    "®": "skrásett vörumerki",
    "©": "höfundarréttarmerki",
}
# HACK: Inflect at runtime instead of hardcoding, doesn't deal with other cases
_CURRENCY_NAMES: Mapping[str, Mapping[NumberType, str]] = {
    "ISK": {"et": "króna", "ft": "krónur"},
    "DKK": {"et": "dönsk króna", "ft": "danskar krónur"},
    "NOK": {"et": "norsk króna", "ft": "norskar krónur"},
    "SEK": {"et": "sænsk króna", "ft": "sænskar krónur"},
    "GBP": {"et": "sterlingspund", "ft": "sterlingspund"},
    "USD": {"et": "bandaríkjadalur", "ft": "bandaríkjadalir"},
    "EUR": {"et": "evra", "ft": "evrur"},
    "CAD": {"et": "kanadískur dalur", "ft": "kanadískir dalir"},
    "AUD": {"et": "ástralskur dalur", "ft": "ástralskir dalir"},
    "CHF": {"et": "svissneskur franki", "ft": "svissneskir frankar"},
    "JPY": {"et": "japanskt jen", "ft": "japönsk jen"},
    "PLN": {"et": "pólskt slot", "ft": "pólsk slot"},
    "RUB": {"et": "rússnesk rúbla", "ft": "rússneskar rúblur"},
    "CZK": {"et": "tékknesk króna", "ft": "tékkneskar krónur"},
    "INR": {"et": "indversk rúpía", "ft": "indverskar rúpíur"},
    "IDR": {"et": "indónesísk rúpía", "ft": "indónesískar rúpíur"},
    "CNY": {"et": "kínverskt júan", "ft": "kínversk júan"},
    "RMB": {"et": "kínverskt júan", "ft": "kínversk júan"},
    "HKD": {"et": "Hong Kong dalur", "ft": "Hong Kong dalir"},
    "NZD": {"et": "nýsjálenskur dalur", "ft": "nýsjálenskir dalir"},
    "SGD": {"et": "singapúrskur dalur", "ft": "singapúrskir dalir"},
    "MXN": {"et": "mexíkóskt pesó", "ft": "mexíkósk pesó"},
    "ZAR": {"et": "suður-afrískt rand", "ft": "suður-afrísk rand"},
}

# Matches e.g. "klukkan 14:30", "kl. 2:23:31", "02:15"
_TIME_REGEX = re.compile(
    r"((?P<klukkan>(kl\.|klukkan)) )?(?P<hour>\d{1,2}):" + r"(?P<minute>\d\d)(:(?P<second>\d\d))?",
    flags=re.IGNORECASE,
)
_MONTH_ABBREVS = (
    "jan",
    "feb",
    "mar",
    "apr",
    "maí",
    "jún",
    "júl",
    "ágú",
    "sep",
    "okt",
    "nóv",
    "des",
)
_MONTH_NAMES = (
    "janúar",
    "febrúar",
    "mars",
    "apríl",
    "maí",
    "júní",
    "júlí",
    "ágúst",
    "september",
    "október",
    "nóvember",
    "desember",
)
_DATE_REGEX = re.compile(
    "|".join(
        (  # TODO: This matches incorrect dates such as 1999-88-63 or 43/67/1999
            # Matches e.g. "1986-03-07"
            r"(?P<year1>\d{1,4})-(?P<month1>\d{1,2})-(?P<day1>\d{1,2})",
            # Matches e.g. "1/4/2001"
            r"(?P<day2>\d{1,2})/(?P<month2>\d{1,2})/(?P<year2>\d{1,4})",
            # Matches e.g. "25. janúar 1999" or "25 des."
            r"(?P<day3>\d{1,2})\.? ?"
            + r"(?P<month3>(jan(úar|\.)?|feb(rúar|\.)?|mar(s|\.)?|"
            + r"apr(íl|\.)?|maí\.?|jún(í|\.)?|"
            + r"júl(í|\.)?|ágú(st|\.)?|sept?(ember|\.)?|"
            + r"okt(óber|\.)?|nóv(ember|\.)?|des(ember|\.)?))"  # 'month' capture group ends
            + r"( (?P<year3>\d{1,4}))?",  # Optional
        )
    ),
    flags=re.IGNORECASE,
)


def _date_to_text(*, year: int | None, month: int, day: int | None, case: CaseType = "nf") -> str:
    out = ""
    if day:
        out += number_to_ordinal(day, gender="kk", case=case, number="et") + " "
    # Month names don't change in different declensions
    out += _MONTH_NAMES[month - 1]
    if year:
        out += " " + year_to_text(year)
    return out


def _time_to_text(hour: int, minute: int, second: int | None) -> str:
    suffix: str | None = None
    t: list[str] = []

    # Hours
    if hour == 0 and minute == 0:
        # Refer to 00:00 as "tólf á miðnætti"
        hour = 12
        suffix = "á miðnætti"
    elif 0 <= hour <= 5:
        # Refer to 00:xx-05:xx as "... um nótt"
        suffix = "um nótt"
    elif hour == 12 and minute == 0:
        # Refer to 12:00 as "tólf á hádegi"
        suffix = "á hádegi"
    t.append(number_to_text(hour, case="nf", gender="hk"))

    # Minutes
    if minute > 0:
        if minute < 10:
            # e.g. "þrettán núll fjögur"
            t.append("núll")
        t.append(number_to_text(minute, case="nf", gender="hk"))

    # Seconds
    if second is not None and second > 0:
        if second < 10:
            # e.g. "þrettán núll fjögur núll sex"
            t.append("núll")
        t.append(number_to_text(second, case="nf", gender="hk"))

    # Suffix for certain times of day to reduce ambiguity
    if suffix:
        t.append(suffix)

    return " ".join(t)


def _split_substring_types(t: str) -> Iterable[str]:
    """
    Split text into alphabetic, decimal or
    other character type substrings.

    Example:
        list(_split_substring_types("hello world,123"))
        -> ["hello", " ", "world", ",", "123"]
    """
    chartype2val: Callable[[str], int] = lambda c: c.isalpha() + 2 * c.isdecimal()
    return ("".join(g) for _, g in itertools.groupby(t, key=chartype2val))


# Matches letter followed by period or
# 2-5 uppercase letters side-by-side not
# followed by another uppercase letter
# (e.g. matches "EUIPO" or "MSc", but not "TESTING")
_ABBREV_RE = re.compile(rf"([{ALPHABET + ALPHABET.lower()}]\." + rf"|\b[{ALPHABET}]{{2,5}}(?![{ALPHABET}]))")

# Terms common in sentences which refer to results from sports
_SPORTS_LEMMAS: frozenset[str] = frozenset(("leikur", "vinna", "tapa", "sigra"))
_IGNORED_TOKENS = frozenset((TOK.WORD, TOK.PERSON, TOK.ENTITY, TOK.TIMESTAMP, TOK.UNKNOWN))
# These should not be interpreted as abbreviations
# unless they include a period
_IGNORED_ABBREVS = frozenset(("mið", "fim", "bandar", "mao", "próf", "tom", "mar"))
_HYPHEN_SYMBOLS = frozenset(HYPHENS)

_StrBool = Union[str, bool]
TranscriptionMethod = Callable[..., str]


def _is_plural(num: str | float) -> bool:
    """Determine whether an Icelandic word following a given number should be
    plural or not, e.g. "21 maður", "22 menn", "1,1 kílómetri", "11 menn" etc.
    Accepts string, float or int as argument."""
    sn = str(num)
    return not (sn.endswith("1") and not sn.endswith("11"))


def _transcribe_method(f: TranscriptionMethod) -> TranscriptionMethod:
    """
    Decorator which
    - returns "" if text is ""
    - wraps funtion with TRACE(=5) level logging
    """

    def _inner(cls: DefaultTranscriber, txt: str, **kwargs: _StrBool):
        _LOG.log(TRACE, "Input to %s, txt: %r, kwargs: %s", f, txt, kwargs)
        out = ""
        # NOTE: Keep `!= ""`
        if txt != "":  # noqa
            out = f(cls, txt, **kwargs)
        _LOG.log(TRACE, "Output from %s, txt: %r", f, out)
        return out

    return _inner


def _bool_args(*bool_args: str) -> Callable[[TranscriptionMethod], TranscriptionMethod]:
    """
    Returns a decorator which converts keyword arguments in bool_args
    from strings into booleans before calling the decorated function.

    As GSSML is text-based, all function arguments come from strings.
    Booleans also work when calling the methods directly, e.g. in testing.
    """

    def _decorator(f: TranscriptionMethod) -> TranscriptionMethod:
        def _bool_translate(cls: DefaultTranscriber, *args: str, **kwargs: str):
            # Convert keyword arguments in bool_args from
            # str to boolean before calling decorated function
            newkwargs = {key: (str(val) == "True" if key in bool_args else val) for key, val in kwargs.items()}
            return f(cls, *args, **newkwargs)

        return _bool_translate

    return _decorator


class DefaultTranscriber:
    """
    Class containing default phonetic transcription functions
    for Icelandic speech synthesis.
    """

    # Singleton Greynir instance
    _greynir: Greynir | None = None

    # &,<,> cause speech synthesis errors,
    # change these to text
    _DANGER_SYMBOLS: tuple[tuple[str, str], ...] = (
        ("&", " og "),
        ("<=", " minna eða jafnt og "),
        ("<", " minna en "),
        (">=", " stærra eða jafnt og "),
        (">", " stærra en "),
    )

    @classmethod
    @_transcribe_method
    def danger_symbols(cls, txt: str) -> str:
        """
        Takes in any text and replaces the symbols that
        cause issues for the speech synthesis engine.
        These symbols are &,<,>.

        Note: HTML charrefs (e.g. &amp;) should be translated to their
              unicode character before this function is called.
              (GreynirSSMLParser does this automatically.)
        """
        # TODO: Optimize this
        for symb, new in cls._DANGER_SYMBOLS:
            txt = txt.replace(symb, new)
        return txt

    @classmethod
    @_transcribe_method
    @_bool_args("one_hundred")
    def number(
        cls,
        txt: str,
        *,
        case: CaseType = "nf",
        gender: GenderType = "hk",
        one_hundred: bool = False,
    ) -> str:
        """Voicify a number."""
        return number_to_text(txt, case=case, gender=gender, one_hundred=one_hundred)

    @classmethod
    @_transcribe_method
    @_bool_args("one_hundred")
    def numbers(
        cls,
        txt: str,
        *,
        case: CaseType = "nf",
        gender: GenderType = "hk",
        one_hundred: bool = False,
    ) -> str:
        """Voicify text containing multiple numbers."""
        return numbers_to_text(txt, case=case, gender=gender, one_hundred=one_hundred)

    @classmethod
    @_transcribe_method
    @_bool_args("comma_null", "one_hundred")
    def float(
        cls,
        txt: str,
        *,
        case: CaseType = "nf",
        gender: GenderType = "hk",
        one_hundred: bool = False,
        comma_null: bool = False,
    ) -> str:
        """Voicify a float."""
        return float_to_text(
            txt,
            case=case,
            gender=gender,
            one_hundred=one_hundred,
            comma_null=comma_null,
        )

    @classmethod
    @_transcribe_method
    @_bool_args("comma_null", "one_hundred")
    def floats(
        cls,
        txt: str,
        *,
        case: CaseType = "nf",
        gender: GenderType = "hk",
        one_hundred: bool = False,
        comma_null: bool = False,
    ) -> str:
        """Voicify text containing multiple floats."""
        return floats_to_text(
            txt,
            case=case,
            gender=gender,
            one_hundred=one_hundred,
            comma_null=comma_null,
        )

    @classmethod
    @_transcribe_method
    def ordinal(
        cls,
        txt: str,
        *,
        case: CaseType = "nf",
        gender: GenderType = "hk",
        number: NumberType = "et",
    ) -> str:
        """Voicify an ordinal."""
        return number_to_ordinal(txt, case=case, gender=gender, number=number)

    @classmethod
    @_transcribe_method
    def ordinals(
        cls,
        txt: str,
        *,
        case: CaseType = "nf",
        gender: GenderType = "hk",
        number: NumberType = "et",
    ) -> str:
        """Voicify text containing multiple ordinals."""
        return numbers_to_ordinal(txt, case=case, gender=gender, number=number)

    @classmethod
    @_transcribe_method
    def digits(cls, txt: str) -> str:
        """Spell out digits."""
        return digits_to_text(txt)

    @classmethod
    @_transcribe_method
    def phone(cls, txt: str) -> str:
        """Spell out a phone number."""
        return cls.digits(txt).replace("+", "plús ")

    @classmethod
    @_transcribe_method
    def timespan(cls, seconds: str) -> str:
        """Voicify a span of time, specified in seconds."""
        # TODO: Replace time_period_desc in queries/util/__init__.py
        raise NotImplementedError

    @classmethod
    @_transcribe_method
    def distance(cls, meters: str) -> str:
        # TODO: Replace distance_desc in queries/util/__init__.py
        raise NotImplementedError

    @classmethod
    @_transcribe_method
    def time(cls, txt: str) -> str:
        """Voicifies time of day."""

        def _time_fmt(match: Match[str]) -> str:
            gd = match.groupdict()
            prefix: str | None = gd["klukkan"]
            h: int = int(gd["hour"])
            m: int = int(gd["minute"])
            s: int | None = int(gd["second"]) if gd["second"] is not None else None
            suffix: str | None = None

            t: list[str] = []
            # If "klukkan" or "kl." at beginning of string,
            # prepend "klukkan"
            if prefix:
                t.append("klukkan")

            # Hours
            if h == 0 and m == 0:
                # Refer to 00:00 as "tólf á miðnætti"
                h = 12
                suffix = "á miðnætti"
            elif 0 <= h <= 5:
                # Refer to 00:xx-05:xx as "... um nótt"
                suffix = "um nótt"
            elif h == 12 and m == 0:
                # Refer to 12:00 as "tólf á hádegi"
                suffix = "á hádegi"
            t.append(number_to_text(h, case="nf", gender="hk"))

            # Minutes
            if m > 0:
                if m < 10:
                    # e.g. "þrettán núll fjögur"
                    t.append("núll")
                t.append(number_to_text(m, case="nf", gender="hk"))

            # Seconds
            if s is not None and s > 0:
                if s < 10:
                    # e.g. "þrettán núll fjögur núll sex"
                    t.append("núll")
                t.append(number_to_text(s, case="nf", gender="hk"))

            # Suffix for certain times of day to reduce ambiguity
            if suffix:
                t.append(suffix)

            return " ".join(t)

        return _TIME_REGEX.sub(_time_fmt, txt)

    @classmethod
    @_transcribe_method
    def date(cls, txt: str, case: CaseType = "nf") -> str:
        """Voicifies a date"""
        # TODO: This function should accept year, month, day
        # as args instead of searching via regex
        if (match := _DATE_REGEX.search(txt)) is not None:
            # Found match
            gd = match.groupdict()

            d = next(filter(bool, (gd[f"day{i}"] for i in range(1, 4))), None)
            mon = next(filter(bool, (gd[f"month{i}"] for i in range(1, 4))), None)
            y = next(filter(bool, (gd[f"year{i}"] for i in range(1, 4))), None)

            # The year is optional
            if mon and d:
                m = int(mon) if mon.isdecimal() else _MONTH_ABBREVS.index(mon[:3]) + 1
                fmt_date = _date_to_text(
                    year=int(y) if y else None,
                    month=m,
                    day=int(d),
                    case=case,
                )
                start, end = match.span()
                # Only replace date part, leave rest of string intact
                txt = txt[:start] + fmt_date + txt[end:]
        return txt

    @classmethod
    @_transcribe_method
    def year(cls, txt: str) -> str:
        """Voicify a year."""
        return year_to_text(txt)

    @classmethod
    @_transcribe_method
    def years(cls, txt: str) -> str:
        """Voicify text containing multiple years."""
        return years_to_text(txt)

    # Pronunciation of character names in Icelandic
    _CHAR_PRONUNCIATION: Mapping[str, str] = {
        "a": "a",
        "á": "á",
        "b": "bé",
        "c": "sé",
        "d": "dé",
        "ð": "eð",
        "e": "e",
        "é": "é",
        "f": "eff",
        "g": "gé",
        "h": "há",
        "i": "i",
        "í": "í",
        "j": "joð",
        "k": "ká",
        "l": "ell",
        "m": "emm",
        "n": "enn",
        "o": "o",
        "ó": "ó",
        "p": "pé",
        "q": "kú",
        "r": "err",
        "s": "ess",
        "t": "té",
        "u": "u",
        "ú": "ú",
        "v": "vaff",
        "w": "tvöfaltvaff",
        "x": "ex",
        "y": "ufsilon",
        "ý": "ufsilon í",
        "þ": "þoddn",
        "æ": "æ",
        "ö": "ö",
        "z": "seta",
    }

    @classmethod
    @_transcribe_method
    @_bool_args("literal")
    def spell(
        cls,
        txt: str,
        *,
        pause_length: str | None = None,
        literal: bool = False,
    ) -> str:
        """
        Spell out a sequence of characters.
        If literal is set, also pronounce spaces and punctuation symbols.
        """

        f: Callable[[str], str]
        if literal:
            # Literal spelling (spell spaces and punctuation)
            f = lambda c: cls._CHAR_PRONUNCIATION.get(c.lower(), _PUNCTUATION_NAMES.get(c, c))
        else:
            # Non-literal spelling
            f = lambda c: cls._CHAR_PRONUNCIATION.get(c.lower(), c) if not c.isspace() else ""
        t = tuple(map(f, txt))
        return (
            cls.vbreak(time="10ms")
            + cls.vbreak(time=pause_length or "20ms").join(t)
            + cls.vbreak(time="20ms" if len(t) > 1 else "10ms")
        )

    @classmethod
    @_transcribe_method
    def abbrev(cls, txt: str) -> str:
        """Expand an abbreviation."""
        meanings = tuple(
            filter(
                lambda m: m.fl != "erl",  # Only Icelandic abbrevs
                Abbreviations.get_meaning(txt) or [],
            )
        )
        if meanings:
            # Abbreviation has at least one known meaning, expand it
            return cls.vbreak(time="10ms") + meanings[0].stofn + cls.vbreak(time="50ms")

        # Fallbacks:
        # - Spell out, if any letter is uppercase (e.g. "MSc")
        if not txt.islower():
            return cls.spell(txt.replace(".", ""))
        # - Give up and keep as-is for all-lowercase txt
        # (e.g. "cand.med."),
        return txt

    @classmethod
    @_transcribe_method
    def currency(cls, txt: str, *, number: NumberType = "ft") -> str:
        if txt not in _CURRENCY_NAMES:
            return cls.spell(txt)
        return _CURRENCY_NAMES[txt][number]

    @classmethod
    @_transcribe_method
    def unit(cls, txt: str, *, number: NumberType = "ft") -> str:
        if txt not in _SI_UNIT_NAMES:
            return txt
        return _SI_UNIT_NAMES[txt][number]

    @classmethod
    @_transcribe_method
    def molecule(cls, txt: str) -> str:
        """Voicify the name of a molecule"""
        return " ".join(
            cls.number(x, gender="kk") if x.isdecimal() else cls.spell(x, literal=True)
            for x in _split_substring_types(txt)
        )

    @classmethod
    @_transcribe_method
    def numalpha(cls, txt: str) -> str:
        """Voicify a alphanumeric string, spelling each character."""
        return " ".join(cls.digits(x) if x.isdecimal() else cls.spell(x) for x in _split_substring_types(txt))

    @classmethod
    @_transcribe_method
    def username(cls, txt: str) -> str:
        """Voicify a username."""
        newtext: list[str] = []
        if txt.startswith("@"):
            txt = txt[1:]
            newtext.append("att")
        for x in _split_substring_types(txt):
            if x.isdecimal():
                if len(x) > 2:
                    # Spell out numbers of more than 2 digits
                    newtext.append(cls.digits(x))
                else:
                    newtext.append(cls.number(x))
            else:
                if x.isalpha() and len(x) > 2:
                    # Alphabetic string, longer than 2 chars, pronounce as is
                    newtext.append(x)
                else:
                    # Not recognized as number or Icelandic word,
                    # spell this literally (might include punctuation symbols)
                    newtext.append(cls.spell(x, literal=True))
        return " ".join(newtext)

    _DOMAIN_PRONUNCIATIONS: Mapping[str, str] = {
        "is": "is",
        "org": "org",
        "net": "net",
        "com": "komm",
        "gmail": "gjé meil",
        "hotmail": "hott meil",
        "yahoo": "ja húú",
        "outlook": "átlúkk",
    }

    @classmethod
    @_transcribe_method
    def domain(cls, txt: str) -> str:
        """Voicify a domain name."""
        newtext: list[str] = []
        for x in _split_substring_types(txt):
            if x in cls._DOMAIN_PRONUNCIATIONS:
                newtext.append(cls._DOMAIN_PRONUNCIATIONS[x])
            elif x.isdecimal():
                if len(x) > 2:
                    # Spell out numbers of more than 2 digits
                    newtext.append(cls.digits(x))
                else:
                    newtext.append(cls.number(x))
            else:
                if x.isalpha() and len(x) > 2:
                    # Alphabetic string, longer than 2 chars, pronounce as is
                    newtext.append(x)
                elif x == ".":
                    # Periods are common in domains/URLs,
                    # skip calling the spell method
                    newtext.append("punktur")
                else:
                    # Short and/or non-alphabetic string
                    # (might consist of punctuation symbols)
                    # Spell this literally
                    newtext.append(cls.spell(x, literal=True))
        return " ".join(newtext)

    @classmethod
    @_transcribe_method
    def email(cls, txt: str) -> str:
        """Voicify an email address."""
        user, at, domain = txt.partition("@")
        return f"{cls.username(user)}{' att ' if at else ''}{cls.domain(domain)}"

    # Hardcoded pronounciations,
    # should be overriden based on voice engine
    _ENTITY_PRONUNCIATIONS: Mapping[str, str] = {
        "ABBA": "ABBA",
        "BOYS": "BOYS",
        "BUGL": "BUGL",
        "BYKO": "BYKO",
        "CAVA": "CAVA",
        "CERN": "CERN",
        "CERT": "CERT",
        "EFTA": "EFTA",
        "ELKO": "ELKO",
        "NATO": "NATO",
        "NEW": "NEW",
        "NOVA": "NOVA",
        "PLAY": "PLAY",
        "PLUS": "PLUS",
        "RARIK": "RARIK",
        "RIFF": "RIFF",
        "RÚV": "RÚV",
        "SAAB": "SAAB",
        "SAAS": "SAAS",
        "SHAH": "SHAH",
        "SIRI": "SIRI",
        "UENO": "UENO",
        "YVES": "YVES",
    }

    # These parts of a entity name aren't necessarily
    # all uppercase or contain a period,
    # but should be spelled out
    _ENTITY_SPELL = frozenset(
        (
            "GmbH",
            "USS",
            "Ltd",
            "bs",
            "ehf",
            "h/f",
            "hf",
            "hses",
            "hsf",
            "ohf",
            "s/f",
            "ses",
            "sf",
            "slf",
            "slhf",
            "svf",
            "vlf",
            "vmf",
        )
    )

    @classmethod
    @_transcribe_method
    def entity(cls, txt: str) -> str:
        """Voicify an entity name."""
        parts = txt.split()
        with GreynirBin.get_db() as gbin:
            for i, p in enumerate(parts):
                if p in cls._ENTITY_PRONUNCIATIONS:
                    # Hardcoded pronunciation
                    parts[i] = cls._ENTITY_PRONUNCIATIONS[p]
                    continue
                if p.isdecimal():
                    # Number
                    parts[i] = cls.number(p)
                    continue

                spell_part = False
                p_nodots = p.replace(".", "")
                if p_nodots in cls._ENTITY_SPELL:
                    # We know this should be spelled out
                    spell_part = True
                elif p_nodots.isupper():
                    if gbin.lookup(p_nodots, auto_uppercase=True)[1]:
                        # Uppercase word has similar Icelandic word,
                        # pronounce it that way
                        parts[i] = p_nodots.capitalize()
                        continue
                    # No known Icelandic pronounciation, spell
                    spell_part = True
                if spell_part:
                    # Spell out this part of the entity name
                    parts[i] = cls.spell(p_nodots)
        return " ".join(parts)

    @classmethod
    @_transcribe_method
    @_bool_args("full_text")
    @lru_cache(maxsize=50)  # Caching, as this method could be slow
    def parser_transcribe(cls, txt: str, *, full_text: bool = False) -> str:
        """
        Slow transcription of Icelandic text for TTS.
        Utilizes the parser from the GreynirPackage library.
        """
        if cls._greynir is None:
            cls._greynir = Greynir(no_sentence_start=True)
        p_result = cls._greynir.parse(txt)

        def _ordinal(tok: Tok, term: SimpleTree | None) -> str:
            """Handles ordinals, e.g. '14.' or '2.'."""
            case, gender, number = "nf", "hk", "et"
            if term is not None:
                case = next(filter(lambda v: v in ALL_CASES, term.variants), "nf")
                gender = next(filter(lambda v: v in ALL_GENDERS, term.variants), "hk")
            if term is not None and term.index is not None:
                leaves = tuple(term.root.leaves)
                if len(leaves) > term.index + 1:
                    # Fetch the grammatical number of the following word
                    number = next(
                        filter(
                            lambda v: v in ALL_NUMBERS,
                            leaves[term.index + 1].variants,
                        ),
                        "et",
                    )
            return cls.ordinal(txt, case=case, gender=gender, number=number)

        def _number(tok: Tok, term: SimpleTree | None) -> str:
            """Handles numbers, e.g. '135', '17,86' or 'fjörutíu og þrír'."""
            if not tok.txt.replace(".", "").replace(",", "").isdecimal():
                # Don't modify non-decimal numbers
                return tok.txt
            case, gender = "nf", "hk"
            if term is not None:
                case = next(filter(lambda v: v in ALL_CASES, term.variants), "nf")
                gender = next(filter(lambda v: v in ALL_GENDERS, term.variants), "hk")
            if "," in txt:
                return cls.float(txt, case=case, gender=gender)
            else:
                return cls.number(txt, case=case, gender=gender)

        def _percent(tok: Tok, term: SimpleTree | None) -> str:
            """Handles a percentage, e.g. '15,6%' or '40 prósent'."""
            gender = "hk"
            n, cases, _ = cast(tuple[float, Any, Any], tok.val)
            case = "nf" if cases is None else cases[0]
            if n.is_integer():
                val = cls.number(n, case=case, gender=gender)
            else:
                val = cls.float(n, case=case, gender=gender)
            if cases is None:
                # Uses "%" or "‰" instead of "prósent"
                # (permille value is converted to percentage by tokenizer)
                percent = "prósent"
            else:
                # Uses "prósent" in some form, keep as is
                percent = tok.txt.split(" ")[-1]
            return f"{val} {percent}"

        def _numwletter(tok: Tok, term: SimpleTree | None) -> str:
            num = "".join(filter(lambda c: c.isdecimal(), tok.txt))
            return cls.number(num, case="nf", gender="hk") + " " + cls.spell(tok.txt[len(num) + 1 :])

        # Map certain terminals directly to transcription functions
        handler_map: Mapping[int, Callable[[Tok, SimpleTree | None], str]] = {
            TOK.ENTITY: lambda tok, term: cls.entity(tok.txt),
            TOK.COMPANY: lambda tok, term: cls.entity(tok.txt),
            TOK.PERSON: lambda tok, term: cls.person(tok.txt),
            TOK.EMAIL: lambda tok, term: cls.email(tok.txt),
            TOK.HASHTAG: lambda tok, term: f"myllumerki {tok.txt[1:]}",
            TOK.TIME: lambda tok, term: cls.time(tok.txt),
            TOK.YEAR: lambda tok, term: cls.years(tok.txt),
            # TODO: Better handling of case for dates,
            # accusative is common though
            TOK.DATE: lambda tok, term: cls.date(tok.txt, case="þf"),
            TOK.DATEABS: lambda tok, term: cls.date(tok.txt, case="þf"),
            TOK.DATEREL: lambda tok, term: cls.date(tok.txt, case="þf"),
            TOK.TIMESTAMP: lambda tok, term: cls.time(cls.date(tok.txt, case="þf")),
            TOK.TIMESTAMPABS: lambda tok, term: cls.time(cls.date(tok.txt, case="þf")),
            TOK.TIMESTAMPREL: lambda tok, term: cls.time(cls.date(tok.txt, case="þf")),
            TOK.SSN: lambda tok, term: cls.digits(tok.txt),
            TOK.TELNO: lambda tok, term: cls.digits(tok.txt),
            TOK.SERIALNUMBER: lambda tok, term: cls.digits(tok.txt),
            TOK.MOLECULE: lambda tok, term: cls.molecule(tok.txt),
            TOK.USERNAME: lambda tok, term: cls.username(tok.txt),
            TOK.DOMAIN: lambda tok, term: cls.domain(tok.txt),
            TOK.URL: lambda tok, term: cls.domain(tok.txt),
            # TOK.AMOUNT: lambda tok, term: tok.txt,
            # TOK.CURRENCY: lambda tok, term: tok.txt, CURRENCY_SYMBOLS in tokenizer
            # TOK.MEASUREMENT: lambda tok, term: tok.txt, SI_UNITS in tokenizer
            TOK.NUMBER: _number,
            TOK.NUMWLETTER: _numwletter,
            TOK.ORDINAL: _ordinal,
            TOK.PERCENT: _percent,
        }

        parts: list[str] = []
        for s in p_result["sentences"]:
            s_parts: list[str] = []
            # list of (token, terminal node) pairs.
            # Terminal nodes can be None if the sentence wasn't parseable
            tk_term_list = tuple(zip(s.tokens, s.terminal_nodes or (None for _ in s.tokens)))
            for tok, term in tk_term_list:
                txt = tok.txt

                if tok.kind in handler_map:
                    # Found a handler for this token type
                    s_parts.append(handler_map[tok.kind](tok, term))
                    continue

                # Fallbacks if no handler found
                if txt.isupper():
                    # Fully uppercase string,
                    # might be part of an entity name
                    s_parts.append(cls.entity(txt))

                elif _ABBREV_RE.match(txt) and (
                    (term is not None and not _ABBREV_RE.match(term.lemma))
                    or any(not _ABBREV_RE.match(m.stofn) for m in tok.meanings)
                ):
                    # Probably an abbreviation such as "t.d." or "MSc"
                    s_parts.append(cls.abbrev(txt))

                # Check whether this is a hyphen denoting a range
                elif (
                    txt in _HYPHEN_SYMBOLS
                    and term is not None
                    and term.parent is not None
                    # Check whether parent nonterminal has at least 3 children (might be a range)
                    and len(term.parent) >= 3
                ):
                    # Hyphen found, probably denoting a range
                    if s.lemmas is not None and _SPORTS_LEMMAS.isdisjoint(s.lemmas):
                        # Probably not the result from a sports match
                        # (as the sentence doesn't contain sports-related lemmas),
                        # so replace the range-denoting hyphen with 'til'
                        s_parts.append("til")
                else:
                    # No transcribing happened
                    s_parts.append(txt)

            # Finished parsing a sentence
            sent = " ".join(s_parts).strip()
            parts.append(cls.sentence(sent) if full_text else sent)

        # Join sentences
        para = " ".join(parts)
        return cls.paragraph(para) if full_text else para

    _PERSON_PRONUNCIATION: Mapping[str, str] = {
        "Jr": "djúníor",
        "Jr.": "djúníor",
    }

    @classmethod
    @_transcribe_method
    def person(cls, txt: str) -> str:
        """Voicify the name of a person."""
        with GreynirBin.get_db() as gbin:
            gender = cast(GenderType, gbin.lookup_name_gender(txt))
        parts = txt.split()
        for i, p in enumerate(parts):
            if p in cls._PERSON_PRONUNCIATION:
                parts[i] = cls._PERSON_PRONUNCIATION[p]
                continue
            if "." in p:
                # Contains period (e.g. 'Jak.' or 'Ólafsd.')
                abbrs = next(
                    filter(
                        lambda m: m.ordfl == gender  # Correct gender
                        # Icelandic abbrev
                        and m.fl != "erl"
                        # Uppercase first letter
                        and m.stofn[0].isupper()
                        # Expanded meaning must be longer
                        # (otherwise we just spell it, e.g. 'Th.' = 'Th.')
                        and len(m.stofn) > len(p),
                        Abbreviations.get_meaning(p) or [],
                    ),
                    None,
                )
                if abbrs is not None:
                    # Replace with expanded version of part
                    parts[i] = abbrs.stofn
                else:
                    # Spell this part
                    parts[i] = cls.spell(p.replace(".", ""))
            if i + 2 >= len(parts) and all(l in ROMAN_NUMERALS for l in parts[i]):
                # Last or second to last part of name looks
                # like an uppercase roman numeral,
                # replace with ordinal
                parts[i] = roman_numeral_to_ordinal(parts[i], gender=gender)
        return " ".join(parts)

    VBREAK_STRENGTHS = frozenset(("none", "x-weak", "weak", "medium", "strong", "x-strong"))

    @classmethod
    def vbreak(cls, time: str | None = None, strength: str | None = None) -> str:
        """Create a break in the voice/speech synthesis."""
        if time:
            return f'<break time="{time}" />'
        if strength:
            assert strength in cls.VBREAK_STRENGTHS, f"Break strength {strength} is invalid."
            return f'<break strength="{strength}" />'
        return "<break />"

    @classmethod
    @_transcribe_method
    def paragraph(cls, txt: str) -> str:
        """Paragraph delimiter for speech synthesis."""
        return f"<p>{txt}</p>"

    @classmethod
    @_transcribe_method
    def sentence(cls, txt: str) -> str:
        """Sentence delimiter for speech synthesis."""
        return f"<s>{txt}</s>"

    @classmethod
    @_transcribe_method
    def token_transcribe(cls, text: str, *, options: TranscriptionOptions | None = None) -> str:
        """
        Quick transcription of Icelandic text for TTS.
        Utilizes the tokenizer library.
        """
        opt: TranscriptionOptions = options if options else TranscriptionOptions()
        tokens: list[Tok] = list(tokenize(text))
        for token in tokens:
            # Check if abbreviation
            if (
                token.kind == TOK.WORD
                and (meanings := Abbreviations.get_meaning(token.txt))
                and meanings[0].fl != "erl"
                and token.txt not in _IGNORED_ABBREVS
            ):
                # Expand abbreviation
                token.txt = meanings[0].stofn

            elif token.kind in _IGNORED_TOKENS:
                continue

            elif token.kind == TOK.PUNCTUATION:
                if token.txt == "-":
                    token.txt = "bandstrik"

            # NUMBERS/ORDINALS
            # Experimental, these don't always give
            # better results than no transcription
            elif token.kind == TOK.NUMBER and opt.numbers:
                token.txt = cls.float(token.number, case="nf", gender="hk")

            elif token.kind == TOK.ORDINAL and opt.ordinals:
                token.txt = cls.ordinal(token.ordinal, case="þf", gender="kk")

            # DATE/TIME

            elif token.kind == TOK.TIME:
                h, m, s = cast(DateTimeTuple, token.val)
                token.txt = _time_to_text(h, m, s or None)

            elif token.kind == TOK.DATE and opt.dates:
                y, m, d = cast(DateTimeTuple, token.val)
                token.txt = _date_to_text(
                    year=y or None,
                    month=m,
                    day=d,
                    case="þf",  # HACK: anecdotal, þf seems common in text
                )

            elif token.kind == TOK.YEAR and opt.years:
                token.txt = cls.year(token.integer)

            elif token.kind == TOK.DATEABS and opt.dates:
                y, m, d = cast(DateTimeTuple, token.val)
                token.txt = _date_to_text(
                    year=y,
                    month=m,
                    day=d,
                    case="þf",  # HACK: anecdotal
                )

            elif token.kind == TOK.DATEREL and opt.dates:
                y, m, d = cast(DateTimeTuple, token.val)
                token.txt = _date_to_text(
                    year=y or None,
                    month=m,
                    day=d or None,
                    case="þf",  # HACK: anecdotal
                )

            elif token.kind == TOK.TIMESTAMPABS and opt.dates:
                token.txt = cls.time(cls.date(token.txt, case="þf"))  # HACK: anecdotal

            elif token.kind == TOK.TIMESTAMPREL and opt.dates:
                token.txt = cls.time(cls.date(token.txt, case="þf"))  # HACK: anecdotal

            # COMMUNICATION/INTERNET

            elif token.kind == TOK.TELNO:
                token.txt = cls.phone(token.txt)

            elif token.kind == TOK.EMAIL and opt.emails:
                token.txt = cls.email(token.txt)

            elif token.kind == TOK.DOMAIN and opt.domains:
                token.txt = cls.domain(token.txt)

            elif token.kind == TOK.URL and opt.urls:
                protocol, _, domain = token.txt.partition("://")
                if domain:
                    token.txt = cls.spell(protocol) + cls.domain(domain)

            elif token.kind == TOK.HASHTAG:
                token.txt = "myllumerki " + token.txt.lstrip("#")

            elif token.kind == TOK.USERNAME:
                token.txt = cls.username(token.txt)

            # CURRENCY/BUSINESS

            elif token.kind == TOK.CURRENCY:
                curr, _, _ = cast(CurrencyTuple, token.val)
                token.txt = cls.currency(curr)

            elif token.kind == TOK.AMOUNT and opt.amounts:
                num, curr, _, _ = cast(AmountTuple, token.val)
                curr = CURRENCY_SYMBOLS.get(curr, curr)
                token.txt = (
                    cls.float(num, case="nf", gender=_currency_to_gender(curr))
                    + " "
                    + cls.currency(curr, number="ft" if _is_plural(num) else "et")
                )

            elif token.kind == TOK.COMPANY:
                token.txt = cls.entity(token.txt)

            # SCIENCE

            elif token.kind == TOK.PERCENT and opt.percentages:
                percent, _, _ = cast(NumberTuple, token.val)
                if "%" in token.txt:
                    token.txt = cls.float(percent, case="nf", gender="hk") + " prósent"
                elif "‰" in token.txt:
                    token.txt = cls.float(percent, case="nf", gender="hk") + " prómill"
                else:
                    # Probably written form (e.g. '3,5 prósent'), only transcribe the number
                    token.txt = cls.floats(token.txt, case="nf", gender="hk")

            elif token.kind == TOK.MEASUREMENT and opt.measurements:
                # We can't use token.val here because
                # the tokenization converts everything to SI units
                # unit, num = cast(MeasurementTuple, token.val)

                # HACK: Deal correctly with messes such as "-1.234,56km"
                i = 0
                while i < len(token.txt):
                    c = token.txt[i]
                    if not (c.isdecimal() or c in "+-,. "):
                        break
                    i += 1
                num = float(token.txt[:i].replace(".", "").replace(",", "."))
                unit = token.txt[i:]

                token.txt = (
                    cls.float(num, case="nf", gender=_unit_to_gender(unit))
                    + " "
                    + cls.unit(unit, number="ft" if _is_plural(num) else "et")
                )

            elif token.kind == TOK.MOLECULE:
                token.txt = cls.molecule(token.txt)

            # MISC

            elif token.kind == TOK.NUMWLETTER:
                num, letter = cast(PunctuationTuple, token.val)
                token.txt = cls.number(num, case="nf", gender="hk") + " " + cls.spell(letter)

            elif token.kind == TOK.SSN:
                token.txt = cls.digits(token.txt)

            elif token.kind == TOK.SERIALNUMBER:
                token.txt = cls.digits(token.txt)

        return detokenize(tokens)
