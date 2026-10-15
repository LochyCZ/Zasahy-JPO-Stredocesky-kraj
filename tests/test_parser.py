"""Testy parseru (bez Home Assistantu): python -m pytest tests"""

from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "pkr_zasahy"))

from parser import TZ, ParseError, parse_datum, parse_okres, parse_zasahy, rozdil  # noqa: E402

HTML = (Path(__file__).parent / "fixtures" / "rakovnik.html").read_text(encoding="utf-8")


def test_pocet_a_razeni():
    z = parse_zasahy(HTML)
    assert len(z) == 26
    assert z == sorted(z, key=lambda x: x.cas, reverse=True)


def test_prvni_radek():
    z = parse_zasahy(HTML)[0]
    assert z.nazev == "únik nebezpečných látek - na komunikaci ropa - Rakovník"
    assert z.kategorie == "únik nebezpečných látek"
    assert z.podtyp == "na komunikaci ropa"
    assert z.typ == "únik nebezpečných látek"
    assert z.stav == "ukončená"
    assert not z.aktivni
    assert z.obec == "Rakovník"
    assert z.okres is None  # okresní město nemá druhý řádek
    assert z.stupen == "I."
    assert z.cas == datetime(2026, 10, 9, 17, 5, tzinfo=TZ)


def test_obec_s_okresem():
    z = parse_zasahy(HTML)[1]
    assert (z.obec, z.okres) == ("Lužná", "Rakovník")


def test_podtyp_s_carkou():
    z = next(x for x in parse_zasahy(HTML) if x.obec == "Milostín")
    assert z.podtyp == "odpad, ostatní"


def test_okres_z_filtru():
    assert parse_okres(HTML) == "okres Rakovník"


def test_datum():
    assert parse_datum("2. ledna 2027, 03:04") == datetime(2027, 1, 2, 3, 4, tzinfo=TZ)
    with pytest.raises(ParseError):
        parse_datum("včera")


def test_chybejici_tabulka():
    with pytest.raises(ParseError):
        parse_zasahy("<html><body>Údržba</body></html>")


def test_prazdna_tabulka():
    html = '<table id="result_list"><thead></thead><tbody></tbody></table>'
    assert parse_zasahy(html) == []


def test_rozdil_bez_zmen():
    z = parse_zasahy(HTML)
    assert rozdil({x.uid: x for x in z}, z) == ([], [])


def test_rozdil_novy_zasah():
    z = parse_zasahy(HTML)
    stare = z[1:]
    nove, akt = rozdil({x.uid: x for x in stare}, z)
    assert nove == [z[0]] and akt == []


def test_rozdil_zmena_stavu():
    z = parse_zasahy(HTML)
    probiha = replace(z[0], stav="probíhající", cas=z[0].cas - timedelta(minutes=40))
    zname = {x.uid: x for x in [probiha, *z[1:]]}
    nove, akt = rozdil(zname, z)
    assert nove == []
    assert akt == [(probiha, z[0])]


def test_rozdil_stejna_udalost_po_dnech_je_nova():
    z = parse_zasahy(HTML)
    stary = replace(z[0], cas=z[0].cas - timedelta(days=4))
    nove, akt = rozdil({stary.uid: stary}, [z[0]])
    assert nove == [z[0]] and akt == []
