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

from typing import Callable

import datetime
import re
from itertools import product

import pytest

from icespeak import DefaultTranscriber as DT
from icespeak import TranscriptionOptions


def test_dt_time() -> None:
    assert DT.time("00:00") == "tólf á miðnætti"
    assert DT.time("12:00") == "tólf á hádegi"
    midnight = datetime.time(0, 0)
    six_am = datetime.time(6, 0)
    for h, m in product(range(24), range(60)):
        t = datetime.time(hour=h, minute=m)
        n = DT.time(t.strftime("%H:%M"))
        assert n.replace(" ", "").isalpha()
        if midnight < t < six_am:
            assert "um nótt" in n
    t = datetime.time(6, 6, 6)
    assert "klukkan sex núll sex núll sex" == DT.time(t.strftime("klukkan %H:%M:%S"))
    assert "klukkan sex núll sex núll sex" == DT.time(t.strftime("kl. %H:%M:%S"))
    t = datetime.time(3, 3, 3)
    assert "þrjú núll þrjú núll þrjú um nótt" == DT.time(t.strftime("%H:%M:%S"))


def test_dt_date() -> None:
    for d, m, y, case in product(
        range(1, 32),
        range(1, 13),
        (1, 100, 1800, 1850, 1900, 1939, 2022),
        ("nf", "þf", "þgf", "ef"),
    ):
        try:
            date = datetime.date(y, m, d)
        except ValueError:
            continue
        n1 = DT.date(date.isoformat(), case=case)
        assert n1 == DT.date(f"{y}-{m}-{d}", case=case)
        n2 = DT.date(f"{d}/{m}/{y}", case=case)
        assert n2 == DT.date(date.strftime("%d/%m/%Y"), case=case)
        # TODO: This only works with an Icelandic locale enabled
        # n3 = DT.date(date.strftime("%d. %B %Y"), case=case)
        # n4 = DT.date(date.strftime("%d. %b %Y"), case=case)
        # assert n1 == n2 == n3 == n4


def test_dt_spell() -> None:
    from icespeak.transcribe import ALPHABET

    for a in (ALPHABET + ALPHABET.lower(), "ÁÍS", "BSÍ", "LSH", "SÍBS"):
        n1 = DT.spell(a.upper())
        n2 = DT.spell(a.lower())
        assert n1 == n2
        assert "." not in re.sub(r"<break .*?/>", "", n1)
        assert len(n1) > len(a)
        assert n1.islower()


def test_dt_abbrev() -> None:
    abbrevs = (
        "t.d.",
        "MSc",
        "m.a.s.",
        "o.s.frv.",
        "m.a.",
        "PhD",
        "Ph.D.",
    )
    for a in abbrevs:
        n = DT.abbrev(a)
        assert "." not in re.sub(r"<break .*?/>", "", n)
        assert n.islower()


def test_dt_email() -> None:
    for e in (
        "jon.jonsson@mideind.is",
        "gunnar.brjann@youtube.gov.uk",
        "tolvupostur@gmail.com",
    ):
        n = DT.email(e)
        assert "@" not in n
        assert " att " in n
        assert "." not in re.sub(r"<break .*?/>", "", n)
        assert " punktur " in n


def test_dt_entity() -> None:
    n = DT.entity("Miðeind ehf.")
    assert "ehf." not in n
    n = DT.entity("BSÍ")
    assert "BSÍ" not in n
    n = DT.entity("SÍBS")
    assert "SÍBS" not in n
    n = DT.entity("L&L slf.")
    assert "L" not in n
    assert "slf" not in n
    n = DT.entity("Kjarninn")
    assert n == "Kjarninn"
    n = DT.entity("RANNÍS")
    assert n.upper() == "RANNÍS"
    n = DT.entity("Rannís")
    assert n == "Rannís"
    n = DT.entity("Verkís")
    assert n == "Verkís"
    n = DT.entity("RARIK")
    assert n == "RARIK"
    n = DT.entity("NATO")
    assert n == "NATO"
    n = DT.entity("NASA")
    assert n.upper() == "NASA"
    n = DT.entity("Víkurskel ehf.")
    assert n.startswith("Víkurskel")
    assert "ehf." not in n
    n = DT.entity("VF 45 ehf.")
    assert "VF" not in n
    assert "ehf." not in n
    assert "45" not in n
    n = DT.entity("Alþjóðalyfjaeftirlitsstofnunin")
    assert n == "Alþjóðalyfjaeftirlitsstofnunin"
    n = DT.entity("ÖSE")
    assert n != "ÖSE"
    n = DT.entity("Ungmennaráð UMFÍ")
    assert n.startswith("Ungmennaráð")
    assert "UMFÍ" not in n
    n = DT.entity("NEC Nijmegen")
    assert "NEC" not in n
    assert n.endswith("Nijmegen")
    n = DT.entity("Fabienne Buccio")
    assert n == "Fabienne Buccio"
    n = DT.entity("Salgado")
    assert n == "Salgado"
    n = DT.entity("Sleep Inn")
    assert n == "Sleep Inn"
    n = DT.entity("GSMbensín")
    assert n == "GSMbensín"
    n = DT.entity("USS Comfort")
    assert "USS" not in n
    assert n.endswith("Comfort")
    n = DT.entity("Bayern München - FC Rostov")
    assert "FC" not in n


def test_dt_person() -> None:
    # Roman numerals
    n = DT.person("Elísabet II")
    assert n == "Elísabet önnur"
    n = DT.person("Elísabet II Bretlandsdrottning")
    assert n == "Elísabet önnur Bretlandsdrottning"
    n = DT.person("Leópold II Belgakonungur")
    assert n == "Leópold annar Belgakonungur"
    n = DT.person("Óskar II Svíakonungur")
    assert n == "Óskar annar Svíakonungur"
    n = DT.person("Loðvík XVI")
    assert n == "Loðvík sextándi"

    # Normal
    n = DT.person("Einar Björn")
    assert n == "Einar Björn"
    n = DT.person("Martin Rivers")
    assert n == "Martin Rivers"
    n = DT.person("Tor Magne Drønen")
    assert n == "Tor Magne Drønen"
    n = DT.person("Richard Guthrie")
    assert n == "Richard Guthrie"
    n = DT.person("Jón Ingvi Bragason")
    assert n == "Jón Ingvi Bragason"
    n = DT.person("Regína Valdimarsdóttir")
    assert n == "Regína Valdimarsdóttir"
    n = DT.person("Sigurður Ingvi Snorrason")
    assert n == "Sigurður Ingvi Snorrason"
    n = DT.person("Aðalsteinn Sigurgeirsson")
    assert n == "Aðalsteinn Sigurgeirsson"

    # Abbreviations which should be spelled out
    # Note that the spelling can be different based on the voice engine
    n = DT.person("James H. Grendell")
    assert "H." not in n
    assert n.startswith("James")
    assert n.endswith("Grendell")
    n = DT.person("Guðni Th. Jóhannesson")
    assert "Th" not in n
    assert n.startswith("Guðni")
    assert n.endswith("Jóhannesson")
    n = DT.person("guðni th. jóhannesson")
    assert "th" not in n
    assert n.startswith("guðni")
    assert n.endswith("jóhannesson")
    n = DT.person("Mary J. Blige")
    assert "J." not in n
    assert n.startswith("Mary")
    assert n.endswith("Blige")
    n = DT.person("Alfred P. Sloan Jr.")
    assert "P." not in n
    assert "Jr." not in n
    assert "Alfred" in n
    assert "Sloan" in n

    # Lowercase middle names
    assert DT.person("Louis van Gaal") == "Louis van Gaal"
    assert DT.person("Frans van Houten") == "Frans van Houten"
    assert DT.person("Alex van der Zwaan") == "Alex van der Zwaan"
    assert DT.person("Rafael van der Vaart") == "Rafael van der Vaart"


def test_dt_vbreak() -> None:
    assert DT.vbreak() == "<break />"
    for t in ("0ms", "50ms", "1s", "1.7s"):
        n = DT.vbreak(time=t)
        assert n == f'<break time="{t}" />'
    for s in DT.VBREAK_STRENGTHS:
        n = DT.vbreak(strength=s)
        assert n == f'<break strength="{s}" />'


# Replace longer whitespace in text with single space
_ws_re = re.compile(r"\s\s+")
_fix_ws: Callable[[str], str] = lambda t: _ws_re.sub(" ", t.strip())


@pytest.mark.slow
def test_dt_parser_transcribe() -> None:
    n = DT.parser_transcribe("þjálfari ÍR")
    assert "ÍR" not in n
    assert "þjálfari " in n
    n = DT.parser_transcribe("fulltrúi í samninganefnd félagsins")
    assert n == "fulltrúi í samninganefnd félagsins"
    n = DT.parser_transcribe("formaður nefndarinnar")
    assert n == "formaður nefndarinnar"
    n = DT.parser_transcribe("fyrrverandi Bandaríkjaforseti")
    assert n == "fyrrverandi Bandaríkjaforseti"
    n = DT.parser_transcribe("þjálfari Fram í Olís deild karla")
    assert n == "þjálfari Fram í Olís deild karla"
    n = DT.parser_transcribe("NASF")
    assert n
    assert "NASF" not in n
    n = DT.parser_transcribe("íþróttakennari")
    assert n == "íþróttakennari"
    n = DT.parser_transcribe("formaður Bandalags háskólamanna")
    assert n == "formaður Bandalags háskólamanna"
    n = DT.parser_transcribe("formaður Leigjendasamtakanna")
    assert n == "formaður Leigjendasamtakanna"
    n = DT.parser_transcribe("framkvæmdastjóri Samtaka atvinnulífsins (SA)")
    assert "framkvæmdastjóri Samtaka atvinnulífsins" in n
    assert "SA" not in n
    n = DT.parser_transcribe("innanríkisráðherra í stjórn Sigmundar Davíðs Gunnlaugssonar")
    assert n == "innanríkisráðherra í stjórn Sigmundar Davíðs Gunnlaugssonar"
    n = DT.parser_transcribe("fyrsti ráðherra Íslands")
    assert n == "fyrsti ráðherra Íslands"
    n = DT.parser_transcribe("málpípur þær")
    assert n == "málpípur þær"
    n = DT.parser_transcribe("sundsérfræðingur RÚV")
    assert n == "sundsérfræðingur RÚV"
    n = DT.parser_transcribe("framkvæmdastjóri Strætó ehf.")
    assert "framkvæmdastjóri Strætó" in n
    assert "ehf." not in n
    n = DT.parser_transcribe("þáverandi sjávarútvegsráðherra")
    assert n == "þáverandi sjávarútvegsráðherra"
    n = DT.parser_transcribe("knattspyrnudómari")
    assert n == "knattspyrnudómari"
    n = DT.parser_transcribe("framkvæmdastjóri Félags atvinnurekenda")
    assert n == "framkvæmdastjóri Félags atvinnurekenda"
    n = DT.parser_transcribe("þjálfari Stjörnunnar")
    assert n == "þjálfari Stjörnunnar"
    n = DT.parser_transcribe("lektor við HÍ")
    assert "lektor við" in n
    assert "HÍ" not in n
    n = DT.parser_transcribe("formaður VR og LÍV")
    assert "formaður" in n
    assert "VR" not in n
    assert "LÍV" not in n
    # Test complete_text arg
    n = DT.parser_transcribe("trillukarl í Skerjafirði")
    assert n == "trillukarl í Skerjafirði"
    n = DT.parser_transcribe("trillukarl í Skerjafirði", full_text=True)
    assert n == "<p><s>trillukarl í Skerjafirði</s></p>"

    t = _fix_ws(
        """
        Breski seðlabankinn hækkaði stýrivexti sína í dag
        um hálft prósentustig og eru vextir nú yfir 3,2%.
        Það eru hæstu stýrivextir í Bretlandi í 14 ár.
        Seðlabankinn vonar að vaxtahækkunin stemmi stigu
        við mikilli verðbólgu í landinu.
        """
    )
    n = DT.parser_transcribe(t, full_text=True)
    assert "fjórtán" in n
    assert "yfir þrjú komma tvö prósent" in n
    t = _fix_ws(
        """
        t.d. var 249% munur á ódýrstu og dýrustu rauðrófunum,
        118% munur milli bökunarkartafla, 291% munur á grænum eplum,
        97% munur á vínberjum og 2-3% af jarðarberjum.
        """
    )
    n = DT.parser_transcribe(t, full_text=True)
    assert "%" not in n
    assert "til dæmis" in n
    assert "tvö hundruð níutíu og eitt prósent" in n
    assert "tvö til þrjú prósent"
    n = DT.parser_transcribe(
        "sagðist hún vona að á næstu 10-20 árum " + "yrði farið að nýta tæknina 9,2-5,3 prósent meira."
    )
    assert "tíu til tuttugu árum" in n
    assert "níu komma tvö til fimm komma þrjú prósent" in n
    t = _fix_ws(
        """
        Frakkland - Marókkó á HM.
        Leikurinn var bráðfjörugur en það voru Frakkar
        sem voru sterkari og unnu þeir leikinn 2-0.
        """
    )
    n = DT.parser_transcribe(t, full_text=True)
    assert "Frakkland til Marókkó" not in n
    assert "HM" not in n
    assert "tvö núll" in n
    t = _fix_ws(
        """
        2 eru slasaðir og um 1.500 fiskar dauðir eftir að um
        16 metra hátt fiskabúr í miðju Radisson hóteli
        í Berlín sprakk snemma í morgun.
        """
    )
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "tveir" in n
    assert "eitt þúsund og fimm hundruð" in n
    assert "sextán metra" in n

    t = _fix_ws("Fréttin var síðast uppfærð 3/12/2022 kl. 10:42.")
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "þriðja desember tvö þúsund tuttugu og tvö" in n
    assert "klukkan tíu fjörutíu og tvö" in n
    t = _fix_ws("Fréttin var síðast uppfærð 16. desember 2022 kl. 10:42.")
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "sextánda desember tvö þúsund tuttugu og tvö" in n
    assert "klukkan tíu fjörutíu og tvö" in n
    t = _fix_ws("Fréttin var síðast uppfærð 2. janúar 2022.")
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "annan janúar tvö þúsund tuttugu og tvö" in n
    t = _fix_ws("Fréttin var síðast uppfærð 01/01/2022.")
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "fyrsta janúar tvö þúsund tuttugu og tvö" in n
    t = _fix_ws("Fréttin var síðast uppfærð 14. nóvember og 16. desember 1999.")
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "fjórtánda nóvember og sextánda desember nítján hundruð níutíu og níu" in n
    t = _fix_ws("Fréttin var síðast uppfærð 2. febrúar klukkan 13:30.")
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "annan febrúar klukkan þrettán þrjátíu" in n

    t = _fix_ws(
        """
        „ICELAND-málið er mikilvægt og fordæmisgefandi bæði á sviði
        hugverkaréttar og þjóðaréttar enda getur niðurstaða þess leitt
        til breytinga á evrópskum hugverkarétti.
        Athygli hefur vakið að áfrýjunarnefnd EUIPO er að þessu sinni
        fjölskipuð, þ.e. skipuð níu aðilum í stað þriggja eins og í
        hefðbundnum áfrýjunarnefndum. Það er talið til marks um hve
        mikilvægt málið er talið vera, en af um það bil 2.500 árlegum
        áfrýjunum er einungis 3-5 vísað til fjölskipaðrar áfrýjunarnefndar.
        Þegar við bætist að málið er það fyrsta sem flutt er munnlega fyrir
        nefndinni verður þýðing þess enn betur ljós,“ segir á vef Stjórnarráðsins.
        """
    )
    n = DT.parser_transcribe(t, full_text=True)
    assert n.startswith("<p><s>")
    assert n.endswith("</s></p>")
    assert "hugverkarétti" in n
    assert "ICELAND" in n
    assert "það er" in n
    assert "þ.e." not in n
    assert "EUIPO" not in n
    assert "2.500" not in n
    assert "tvö þúsund og fimm hundruð árlegum áfrýjunum" in n
    # assert "þremur til fimm" in n # TODO


def test_dt_token_transcribe_basic() -> None:
    t = _fix_ws("""Frétt skrifuð þann 27. ágúst 2023 kl. 20:20.""")
    n = DT.token_transcribe(t)
    assert "tuttugasta og sjöunda ágúst tvö þúsund tuttugu og þrjú klukkan tuttugu tuttugu" in n
    t = _fix_ws("Fréttin var síðast uppfærð 3/12/2022 kl. 10:42.")
    n = DT.parser_transcribe(t)
    assert "þriðja desember tvö þúsund tuttugu og tvö" in n
    assert "klukkan tíu fjörutíu og tvö" in n
    t = _fix_ws("Fréttin var síðast uppfærð 3/1/2022 kl. 10:42.")
    n = DT.parser_transcribe(t)
    assert "þriðja janúar tvö þúsund tuttugu og tvö" in n
    assert "klukkan tíu fjörutíu og tvö" in n
    t = _fix_ws(
        """
        t.d. var 249% munur á ódýrstu og dýrustu rauðrófunum,
        118% munur milli bökunarkartafla, 291% munur á grænum eplum,
        97% munur á vínberjum og 2-3% af jarðarberjum.
        """
    )
    n = DT.token_transcribe(t)
    assert "%" not in n
    assert "til dæmis" in n
    assert "tvö hundruð níutíu og eitt prósent" in n
    assert "tvö til þrjú prósent"
    t = _fix_ws(
        """
        Sendu tölvupóst á jon.gudmundsson@gormur.bull.is og bla@gmail.com.
        Kíktu svo á vefsíðurnar is.wikipedia.org, ruv.is og bull.co.net.
        """
    )
    n = DT.token_transcribe(t)
    assert "@" not in n
    assert "jon.gudm" not in n
    assert " punktur " in n
    assert " is " in n
    assert ".com" not in n
    t = _fix_ws("Hvað eru 0,67cm í tommum?")
    n = DT.token_transcribe(t)
    assert "núll komma sextíu og sjö sentimetrar í tommum" in n
    t = _fix_ws("Hvað er 0,61cm í tommum?")
    n = DT.token_transcribe(t)
    assert "núll komma sextíu og einn sentimetri í tommum" in n
    t = "En ef við tökum mið af því hve fim hún er í fimleikum?"
    n = DT.token_transcribe(t)
    assert n == t
    t = "Hann bandar frá sér höndum þegar minnst er á mao zedong."
    n = DT.token_transcribe(t)
    assert n == t
    t = "maðurinn tom fékk mar eftir strembið próf í síðustu viku"
    n = DT.token_transcribe(t)
    assert n == t
    t = "Undirritað, próf. Jónína"
    n = DT.token_transcribe(t)
    assert "prófessor" in n
    t = "Hann er bandar. ríkisborgari"
    n = DT.token_transcribe(t)
    assert "bandarískur" in n


def test_dt_token_transcribe_experimental():
    t_opts = TranscriptionOptions(numbers=True, ordinals=True)
    n = DT.token_transcribe(
        "sagðist hún vona að á næstu 10-20 árum " + "yrði farið að nýta tæknina 9,2-5,3 prósent meira.",
        options=t_opts,
    )
    assert "tíu bandstrik tuttugu árum" in n
    assert "níu komma tvö bandstrik fimm komma þrjú prósent" in n
    t = _fix_ws(
        """
        Frakkland - Marókkó á HM.
        Leikurinn var bráðfjörugur en það voru Frakkar
        sem voru sterkari og unnu þeir leikinn 2-0.
        """
    )
    n = DT.token_transcribe(t, options=t_opts)
    assert "Frakkland bandstrik Marókkó" in n
    assert "tvö bandstrik núll" in n
    t = _fix_ws(
        """
        2 eru slasaðir og um 1.500 fiskar dauðir eftir að um
        16 metra hátt fiskabúr í miðju Radisson hóteli
        í Berlín sprakk snemma í morgun.
        """
    )
    n = DT.token_transcribe(t, options=t_opts)
    # assert "tveir" in n
    assert "eitt þúsund og fimm hundruð" in n
    assert "sextán" in n
    t = _fix_ws(
        """
        Dæmi eru um að nauðsynjavörur hafi nær tvöfaldast í verði á síðustu tveimur árum
        og enn hækka sumar vörur þrátt fyrir minni verðbólgu og sterkara gengi.
        Viðskiptaráðherra vill skýringar á því. Framkvæmdastjóri Bónuss segir að
        óvissa sé um verðlækkanir á næstunni því íslenskar landbúnaðarvörur hækki
        líklega áfram. Matarkarfan kostar 9983 kr í dag. Fréttastofa fór í Krónuna
        og kannaði verð á 15 algengum matvörum. Þessar vörur eiga það sameiginlegt að
        hafa verið teknar fyrir í matvörukönnun Verðlagseftirlits ASÍ haustið 2021 og í
        maí á þessu ári. Í körfunni er ýmislegt; þvottaduft, franskar og mjólk, svo eitthvað
        sé nefnt. Í heild hefur þessi vörukarfa hækkað um 2% frá því í maí en um tæp 28% frá
        haustinu 2021. Fór úr 7811 krónum haustið 2021 í 9983 í dag. Til samanburðar hefur
        launavísitalan hækkað um 18,5% frá haustinu 2021. Allar vörurnar nema tvær höfðu hækkað
        í verði frá haustinu 2021, þá var innrás Rússa í Úkraínu ekki hafin. Mjólkin hangir í
        206 krónum. Frá því í vor hefur verð haldist óbreytt á níu vörum af fimmtán. Mjólkin hefur
        ekki hækkað síðan í maí, kostar 206 krónur, og sama gildir um bananana, kílóverðið í
        Krónunni óbreytt frá í vor, 300 krónur. Þeir hafa þó hækkað um 27% frá haustinu 2021.
        Seríósið kom á óvart, það hefur hækkað um þriðjung frá maí og kílóverðið stendur í
        1.572 krónum. „Það er kominn tími á verðlækkun á innfluttum vörum, og ég held að neytendur
        muni sjá það en ég get ekki lofað verðlækkun á íslenskum landbúnaðarvörum því mér sýnist
        það ekki vera að fara að gerast, til dæmis er búið að gefa út verðhækkun til bænda, 20-25%,
        á lambakjöti og það eru hækkanir sem eiga eftir að skella á af fullum þunga í haust.“
        Hér er upphæð í eintölu: 21 kr.
        """
    )
    n = DT.token_transcribe(t, options=t_opts)
    assert "%" not in n
    assert "prósent" in n
    assert not any(c.isdecimal() for c in n)
    assert "níu þúsund níu hundruð áttatíu og þrjár krónur" in n
    assert "tuttugu og ein króna" in n
    t = _fix_ws(
        """
        Norðmaðurinn Jakob Ingebrigtsen átti stórkostlegan endasprett
        og tryggði sér heimsmeistaratitilinn í 5.000m hlaupi.
        Jakob beið þar til á lokametrunum að elta Spánverjann Mohamed
        Katir uppi og tók fram úr honum rétt áður en þeir komu að endamarkslínu.
        Sá norski hljóp á 13 mínútum og 11.30 sekúndum og varð 14 hundraðshlutum
        úr sekúndum á undan þeim spænska í mark. Jacob Krop frá Kenýa tók bronsið á 13:12.28.
        """
    )
    n = DT.token_transcribe(t, options=t_opts)
    assert "fimm þúsund metra" in n
    assert "ellefu komma þrj" in n
    t = "Í 1., 2., 3. og 4. lagi. Í 31. lagi"
    n = DT.token_transcribe(t, options=t_opts)
    assert "Í fyrsta" in n
    # TODO: Figure out a way to quickly put expanded word in correct case
    # assert "öðru" in n
    assert "þriðja" in n
    assert "fjórða" in n
    assert "þrítugasta og fyrsta" in n
    t = "Á mið. eða fim. verður fundur hjá okkur."
    n = DT.token_transcribe(t)
    # TODO: ditto the point above
    # assert "miðvikudag " in n
    # assert "fimmtudag " in n
