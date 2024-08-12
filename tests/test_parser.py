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

import pytest

from icespeak import VOICES, GreynirSSMLParser, gssml
from icespeak import DefaultTranscriber as DT


def test_gssml():
    gv = gssml("5", type="number")
    assert gv == '<greynir type="number">5</greynir>'
    gv = gssml(type="vbreak")
    assert gv == '<greynir type="vbreak" />'
    gv = gssml(type="vbreak", strength="medium")
    assert gv == '<greynir type="vbreak" strength="medium" />'
    gv = gssml("whatever", type="misc", a="1", b=3, c=4.5)
    assert gv == '<greynir type="misc" a="1" b="3" c="4.5">whatever</greynir>'

    with pytest.raises(TypeError):
        gssml("something", no_type_arg="hello")  # type: ignore


def test_greynirssmlparser():
    gp = GreynirSSMLParser()
    n = gp.transcribe(f"Ég vel töluna {gssml(244, type='number', gender='kk')}")
    assert "tvö hundruð fjörutíu og fjórir" in n
    n = gp.transcribe(f"{gssml(type='vbreak')} {gssml(3, type='number', gender='kk', case='þf')}")
    assert "<break />" in n
    assert "þrjá" in n

    example_data = {
        "number": "1",
        "numbers": "1 2 3",
        "float": "1.0",
        "floats": "1.0 2.3",
        "ordinal": "1",
        "ordinals": "1., 3., 4.",
        "phone": "5885522",
        "time": "12:31",
        "date": "2000-01-01",
        "year": "1999",
        "years": "1999, 2000 og 2021",
        "abbrev": "t.d.",
        "spell": "SÍBS",
        "vbreak": None,
        "email": "t@olvupostur.rugl",
        "paragraph": "lítil efnisgrein",
        "sentence": "lítil setning eða málsgrein?",
    }

    for t, v in DT.__dict__.items():
        if t not in example_data:
            continue
        assert isinstance(v, (staticmethod, classmethod)), "not valid transcription method name"
        d = example_data[t]
        if d is None:
            # No data argument to gssml
            r = f"hér er {gssml(type=t)} texti"
            # Make sure gssml added <greynir/> tag
            assert "<greynir" in r
            assert "/>" in r
        else:
            r = f"hér er {gssml(d, type=t)} texti"
            # Make sure gssml added <greynir> tags
            assert "<greynir" in r
            assert "</greynir" in r
        n = gp.transcribe(r)
        # Make sure transcription removes all <greynir> tags
        assert "<greynir" not in n
        assert "</greynir" not in n

    # -------------------------
    # Tests for weird text data (shouldn't happen in normal query processing though)
    # Underlying HTMLParser class doesn't deal correctly with </tag a=">">,
    # nothing easy we can do to fix that
    x = """<ehskrytid> bla</s>  <t></t> <other formatting="fhe"> bla</other> fad <daf <fda> fda"""
    n = gp.transcribe(x)
    assert "&" not in n
    assert "<" not in n
    assert ">" not in n
    assert len(n) > 0
    # We strip spaces from the names of endtags,
    # but otherwise try to keep unrecognized tags unmodified

    x = """<bla attr="fad" f="3"></ bla  >"""
    n = gp.transcribe(x)
    assert "&" not in n
    assert "<" not in n
    assert ">" not in n
    assert not n

    x = """<bla attr="fad" f="3"><greynir type="vbreak" /></bla> <greynir type="number" gender="kvk">4</greynir>"""
    n = gp.transcribe(x)
    assert "&" not in n
    assert n.count("<") == 1
    assert n.count(">") == 1
    assert n == """<break /> fjórar"""

    x = """<bla attr="fad" f="3"><greynir type="vbreak" /> <greynir type="number" gender="kvk">4</greynir>"""
    n = gp.transcribe(x)
    assert "&" not in n
    assert n.count("<") == 1
    assert n.count(">") == 1
    assert n == """<break /> fjórar"""

    x = """<bla attr="fad" f="3"><greynir type="vbreak" /> <&#47;<greynir type="number" gender="kvk">4</greynir>>"""
    n = gp.transcribe(x)
    assert "&" not in n
    assert n.count("<") == 1
    assert n.count(">") == 1

    # -------------------------
    # Test voice engine specific transcription

    assert "Dora" in VOICES
    # Gudrun, the default voice, and Dora don't spell things the same
    gp2 = GreynirSSMLParser("Dora")
    alphabet = "aábcdðeéfghiíjklmnoópqrstuúvwxyýþæöz"
    n1 = gp.transcribe(gssml(alphabet, type="spell"))
    n2 = gp2.transcribe(gssml(alphabet, type="spell"))
    assert n1 != n2
