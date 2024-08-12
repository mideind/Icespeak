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

# pyright: reportPrivateUsage=false
from __future__ import annotations

from icespeak.transcribe.num import (
    _SUB_20_NEUTRAL,
    _TENS_NEUTRAL,
    digits_to_text,
    float_to_text,
    floats_to_text,
    number_to_neutral,
    number_to_ordinal,
    number_to_text,
    numbers_to_ordinal,
    numbers_to_text,
    year_to_text,
    years_to_text,
)

oktilljon = 10**48
septilljon = 10**42
sextilljon = 10**36
kvintilljon = 10**30
kvadrilljardur = 10**27
kvadrilljon = 10**24
trilljardur = 10**21
trilljon = 10**18
billjardur = 10**15
billjon = 10**12
milljardur = 10**9
milljon = 10**6
thusund = 1000

_NEUT_1_to_100 = (
    # 1-19
    *[(k, v) for k, v in _SUB_20_NEUTRAL.items()],
    # 20, 30
    *[(k, v) for k, v in _TENS_NEUTRAL.items()],
    # 21-29, 31-39, ..., 91-99
    *[
        (ten + digit, f"{tenstr} og {dstr}")
        for ten, tenstr in _TENS_NEUTRAL.items()
        for digit, dstr in list(_SUB_20_NEUTRAL.items())[:9]
    ],
    (100, "hundrað"),
)


def test_number_to_neutral() -> None:
    test_cases = (
        (0, "núll"),
        *_NEUT_1_to_100,
        (101, "hundrað og eitt"),
        (201, "tvö hundruð og eitt"),
        (1100, "eitt þúsund og eitt hundrað"),
        (
            -42_178_249,
            ("mínus fjörutíu og tvær milljónir eitt hundrað " "sjötíu og átta þúsund tvö hundruð fjörutíu og níu"),
        ),
        (241 * milljardur, "tvö hundruð fjörutíu og einn milljarður"),
        (100 * milljon, "eitt hundrað milljónir"),
        (milljardur + thusund, "einn milljarður og eitt þúsund"),
        (milljardur + 11, "einn milljarður og ellefu"),
        (milljardur + 1 * milljon, "einn milljarður og ein milljón"),
        (milljardur + 2 * milljon, "einn milljarður og tvær milljónir"),
        (200 * milljardur, "tvö hundruð milljarðar"),
        (3 * milljardur + 400 * thusund, "þrír milljarðar og fjögur hundruð þúsund"),
        (
            10 * milljon * oktilljon,
            "tíu milljónir oktilljóna",
        ),
        (
            oktilljon + milljardur,
            "ein oktilljón og einn milljarður",
        ),
        (
            oktilljon + 2 * milljardur,
            "ein oktilljón og tveir milljarðar",
        ),
        (
            oktilljon + 3 * milljardur,
            "ein oktilljón og þrír milljarðar",
        ),
        (
            2 * oktilljon + 100 * billjon,
            "tvær oktilljónir og eitt hundrað billjónir",
        ),
        (
            1_010_101_010_101_010,
            (
                "einn billjarður tíu billjónir eitt hundrað og einn milljarður "
                "tíu milljónir eitt hundrað og eitt þúsund og tíu"
            ),
        ),
    )
    for n, expected in test_cases:
        assert number_to_neutral(n) == expected


def test_number_to_text():
    # Shorten name for tests
    nt = number_to_text
    assert nt(milljardur + 200 * thusund + 200) == "einn milljarður tvö hundruð þúsund og tvö hundruð"
    assert nt(320) == "þrjú hundruð og tuttugu"
    assert nt(320 * thusund) == "þrjú hundruð og tuttugu þúsund"
    assert nt(320 * thusund + 1, gender="kk") == "þrjú hundruð og tuttugu þúsund og einn"
    assert nt(320 * thusund + 1, gender="kvk") == "þrjú hundruð og tuttugu þúsund og ein"
    assert nt(320 * thusund + 1, gender="hk") == "þrjú hundruð og tuttugu þúsund og eitt"
    assert nt(3202020202020) == (
        "þrjár billjónir tvö hundruð og tveir milljarðar " "tuttugu milljónir tvö hundruð og tvö þúsund og tuttugu"
    )
    assert nt(320202020) == ("þrjú hundruð og tuttugu milljónir tvö hundruð og tvö þúsund og tuttugu")

    assert nt(101, gender="kk") == "hundrað og einn"
    assert nt(-102, gender="kvk") == "mínus hundrað og tvær"
    assert nt(-102, gender="kvk", one_hundred=True) == "mínus eitt hundrað og tvær"
    assert nt(5, gender="kk") == "fimm"
    assert nt(10001, gender="kvk") == "tíu þúsund og ein"
    assert nt(113305, gender="kk") == "eitt hundrað og þrettán þúsund þrjú hundruð og fimm"
    assert nt(400567, gender="hk") == number_to_neutral(400567)
    assert nt(-11220024, gender="kvk") == "mínus ellefu milljónir tvö hundruð og tuttugu þúsund tuttugu og fjórar"
    assert nt(19501180) == "nítján milljónir fimm hundruð og eitt þúsund eitt hundrað og áttatíu"


def test_numbers_to_text():
    assert numbers_to_text("135 og -16") == "hundrað þrjátíu og fimm og mínus sextán"
    assert numbers_to_text("-55 manns") == "mínus fimmtíu og fimm manns"

    address_test_cases = (
        ("1", "eitt"),
        ("2", "tvö"),
        ("3", "þrjú"),
        ("4", "fjögur"),
        ("5", "fimm"),
        ("10", "tíu"),
        ("11", "ellefu"),
        ("12", "tólf"),
        ("13", "þrettán"),
        ("14", "fjórtán"),
        ("15", "fimmtán"),
        ("20", "tuttugu"),
        ("21", "tuttugu og eitt"),
        ("22", "tuttugu og tvö"),
        ("23", "tuttugu og þrjú"),
        ("24", "tuttugu og fjögur"),
        ("25", "tuttugu og fimm"),
        ("100", "hundrað"),
        ("101", "hundrað og eitt"),
        ("102", "hundrað og tvö"),
        ("103", "hundrað og þrjú"),
        ("104", "hundrað og fjögur"),
        ("105", "hundrað og fimm"),
        ("111", "hundrað og ellefu"),
        ("112", "hundrað og tólf"),
        ("113", "hundrað og þrettán"),
        ("114", "hundrað og fjórtán"),
        ("115", "hundrað og fimmtán"),
        ("121", "hundrað tuttugu og eitt"),
        ("174", "hundrað sjötíu og fjögur"),
        ("200", "tvö hundruð"),
        ("201", "tvö hundruð og eitt"),
        ("202", "tvö hundruð og tvö"),
        ("203", "tvö hundruð og þrjú"),
        ("204", "tvö hundruð og fjögur"),
        ("205", "tvö hundruð og fimm"),
        ("211", "tvö hundruð og ellefu"),
        ("212", "tvö hundruð og tólf"),
        ("213", "tvö hundruð og þrettán"),
        ("214", "tvö hundruð og fjórtán"),
        ("215", "tvö hundruð og fimmtán"),
        ("700", "sjö hundruð"),
        ("1-4", "eitt-fjögur"),
        ("1-17", "eitt-sautján"),
    )

    for n, expected in address_test_cases:
        assert numbers_to_text(f"Baugatangi {n}, Reykjavík") == f"Baugatangi {expected}, Reykjavík"


def test_year_to_text() -> None:
    assert year_to_text(1999) == "nítján hundruð níutíu og níu"
    assert year_to_text(2004) == "tvö þúsund og fjögur"
    assert year_to_text(-501) == "fimm hundruð og eitt fyrir okkar tímatal"
    assert year_to_text(1001) == "eitt þúsund og eitt"
    assert year_to_text(57) == "fimmtíu og sjö"
    assert year_to_text(2401) == "tvö þúsund fjögur hundruð og eitt"


def test_years_to_text() -> None:
    assert years_to_text("Ég fæddist 1994") == "Ég fæddist nítján hundruð níutíu og fjögur"
    assert (
        years_to_text("Árið 1461 var borgin Sarajevo stofnuð")
        == "Árið fjórtán hundruð sextíu og eitt var borgin Sarajevo stofnuð"
    )
    assert years_to_text("17. júlí 1210 lést Sverker II") == "17. júlí tólf hundruð og tíu lést Sverker II"
    assert (
        years_to_text("2021, 2007 og 1999")
        == "tvö þúsund tuttugu og eitt, tvö þúsund og sjö og nítján hundruð níutíu og níu"
    )


def test_number_to_ordinal() -> None:
    assert number_to_ordinal(0) == "núllti"
    assert number_to_ordinal(22, case="þgf", gender="kvk") == "tuttugustu og annarri"
    assert number_to_ordinal(302, gender="kvk") == "þrjú hundraðasta og önnur"
    assert number_to_ordinal(302, case="þgf", gender="hk") == "þrjú hundraðasta og öðru"
    assert number_to_ordinal(-302, case="þgf", gender="hk") == "mínus þrjú hundraðasta og öðru"
    assert number_to_ordinal(10202, case="þgf", gender="hk", number="ft") == "tíu þúsund tvö hundruðustu og öðrum"
    assert number_to_ordinal(milljon, case="þf", gender="kvk", number="et") == "milljónustu"
    assert number_to_ordinal(milljardur + 2, case="þf", gender="kvk", number="et") == "milljörðustu og aðra"


def test_numbers_to_ordinal() -> None:
    assert numbers_to_ordinal("Ég lenti í 41. sæti.", case="þgf") == "Ég lenti í fertugasta og fyrsta sæti."
    assert numbers_to_ordinal("Ég lenti í -41. sæti.", case="þgf") == "Ég lenti í mínus fertugasta og fyrsta sæti."
    assert numbers_to_ordinal("-4. sæti.", case="þgf") == "mínus fjórða sæti."
    assert numbers_to_ordinal("2. í röðinni var hæstur.") == "annar í röðinni var hæstur."
    assert (
        numbers_to_ordinal("1. konan lenti í 2. sæti.", regex=r"1\.", gender="kvk") == "fyrsta konan lenti í 2. sæti."
    )
    assert (
        numbers_to_ordinal("fyrsta konan lenti í 2. sæti.", gender="hk", case="þgf")
        == "fyrsta konan lenti í öðru sæti."
    )
    assert numbers_to_ordinal("Ég var 10201. í röðinni.") == "Ég var tíu þúsund tvö hundraðasti og fyrsti í röðinni."
    assert (
        numbers_to_ordinal("Björn sækist eftir 1. - 4. sæti í Norðvesturkjördæmi", case="þgf").replace("-", "til")
        == "Björn sækist eftir fyrsta til fjórða sæti í Norðvesturkjördæmi"
    )
    assert (
        numbers_to_ordinal("Björn sækist eftir 1.-4. sæti í Norðvesturkjördæmi", case="þgf").replace("-", " til ")
        == "Björn sækist eftir fyrsta til fjórða sæti í Norðvesturkjördæmi"
    )
    assert (
        numbers_to_ordinal("1.-4. sæti í Norðvesturkjördæmi", case="þgf").replace("-", " til ")
        == "fyrsta til fjórða sæti í Norðvesturkjördæmi"
    )


def test_float_to_text() -> None:
    assert float_to_text(-0.12) == "mínus núll komma tólf"
    assert float_to_text(-0.1012) == "mínus núll komma eitt núll eitt tvö"
    assert float_to_text(-0.1012, gender="kk") == "mínus núll komma einn núll einn tveir"
    assert float_to_text(-21.12, gender="kk") == "mínus tuttugu og einn komma tólf"
    assert float_to_text(-21.123, gender="kk") == "mínus tuttugu og einn komma einn tveir þrír"
    assert float_to_text(1.03, gender="kvk") == "ein komma núll þrjár"
    assert float_to_text(2.0, gender="kvk", case="þgf") == "tveimur"
    assert float_to_text(2.0, gender="kvk", case="þgf", comma_null=True) == "tveimur komma núll"
    assert (
        float_to_text("-10.100,21")
        == float_to_text("-10100,21")
        == float_to_text("-10100.21")
        == "mínus tíu þúsund og eitt hundrað komma tuttugu og eitt"
    )


def test_floats_to_text() -> None:
    assert floats_to_text("2,13 millilítrar af vökva.", gender="kk") == "tveir komma þrettán millilítrar af vökva."
    assert floats_to_text("0,04 prósent.") == "núll komma núll fjögur prósent."
    assert floats_to_text("-0,04 prósent.") == "mínus núll komma núll fjögur prósent."
    assert floats_to_text("101,0021 prósent.") == "hundrað og eitt komma núll núll tuttugu og eitt prósent."
    assert floats_to_text("10.100,21 prósent.") == "tíu þúsund og eitt hundrað komma tuttugu og eitt prósent."
    assert (
        floats_to_text("Um -10.100,21 prósent.") == "Um mínus tíu þúsund og eitt hundrað komma tuttugu og eitt prósent."
    )
    assert floats_to_text("-10.100,21 prósent.") == "mínus tíu þúsund og eitt hundrað komma tuttugu og eitt prósent."
    assert floats_to_text("2.000.000,00.", comma_null=False) == "tvær milljónir."


def test_digits_to_text() -> None:
    assert digits_to_text("5885522") == "fimm átta átta fimm fimm tveir tveir"
    assert digits_to_text("112") == "einn einn tveir"
    assert digits_to_text("123-0679") == "einn tveir þrír-núll sex sjö níu"
    assert digits_to_text("Síminn minn er 12342") == "Síminn minn er einn tveir þrír fjórir tveir"
    assert digits_to_text("581 2345") == "fimm átta einn tveir þrír fjórir fimm"
    assert (
        digits_to_text("5812346, það er síminn hjá þeim.")
        == "fimm átta einn tveir þrír fjórir sex, það er síminn hjá þeim."
    )
    assert digits_to_text("010270-2039") == "núll einn núll tveir sjö núll-tveir núll þrír níu"
    assert digits_to_text("192 0-1-127", regex=r"\d\d\d") == "einn níu tveir 0-1-einn tveir sjö"
    assert digits_to_text("Hringdu í 1-800-BULL", regex=r"\d+-\d+") == "Hringdu í einn átta núll núll-BULL"
