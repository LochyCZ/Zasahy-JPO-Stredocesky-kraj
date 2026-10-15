"""Test integrace v Home Assistantu (vyžaduje pytest-homeassistant-custom-component)."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant import config_entries  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.data_entry_flow import FlowResultType  # noqa: E402
from homeassistant.util import dt as dt_util  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    async_capture_events,
)

from custom_components.pkr_zasahy.const import (  # noqa: E402
    DEFAULT_URL,
    DOMAIN,
    EVENT_AKTUALIZACE,
    EVENT_NOVY_ZASAH,
)

HTML = (Path(__file__).parent / "fixtures" / "rakovnik.html").read_text(encoding="utf-8")
URL = "https://pkr.kr-stredocesky.cz/pkr/zasahy-jpo/?r_cast_uzemi__in=1192"

NOVY_RADEK = (
    '<tr class="row1"><th>požár - rodinný dům - Kněževes</th>'
    '<td><span title="požár"><img src="x"></span></td>'
    '<td>probíhající <img src="y" /></td><td>Kněževes<br>okres Rakovník</td>'
    '<td align="center">II.</td><td>9. října 2026, 17:30</td></tr>'
)
UKONCENY_RADEK = NOVY_RADEK.replace("probíhající", "ukončená").replace("17:30", "18:45")


async def _obnov(hass: HomeAssistant) -> None:
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()


def _s_radkem(radek: str) -> str:
    return HTML.replace("<tbody>", "<tbody>" + radek, 1)


async def test_flow_senzory_a_eventy(hass: HomeAssistant, aioclient_mock, freezer):
    hass.config.language = "cs"
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to("2026-10-09 17:40:00+02:00")
    aioclient_mock.get(URL, text=HTML)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": DEFAULT_URL}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Zásahy JPO – okres Rakovník"
    assert result["data"]["url"] == URL
    await hass.async_block_till_done()

    dnes = hass.states.get("sensor.zasahy_jpo_okres_rakovnik_zasahy_dnes")
    assert dnes is not None, hass.states.async_entity_ids("sensor")
    assert dnes.state == "5"
    assert len(dnes.attributes["zasahy"]) == 5
    assert hass.states.get("sensor.zasahy_jpo_okres_rakovnik_zasahy_za_posledni_tyden").state == "26"
    assert hass.states.get("sensor.zasahy_jpo_okres_rakovnik_probihajici_zasahy").state == "0"
    posledni = hass.states.get("sensor.zasahy_jpo_okres_rakovnik_posledni_zasah")
    assert posledni.state == "únik nebezpečných látek - na komunikaci ropa - Rakovník"
    assert posledni.attributes["obec"] == "Rakovník"
    assert hass.states.get("sensor.zasahy_jpo_okres_rakovnik_cas_posledniho_zasahu").state == "2026-10-09T15:05:00+00:00"

    nove = async_capture_events(hass, EVENT_NOVY_ZASAH)
    akt = async_capture_events(hass, EVENT_AKTUALIZACE)

    # Nový probíhající požár
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, text=_s_radkem(NOVY_RADEK))
    freezer.tick(timedelta(minutes=11))
    await _obnov(hass)
    assert len(nove) == 1 and not akt
    assert nove[0].data["obec"] == "Kněževes"
    assert nove[0].data["stupen"] == "II."
    assert hass.states.get("sensor.zasahy_jpo_okres_rakovnik_probihajici_zasahy").state == "1"
    assert hass.states.get("sensor.zasahy_jpo_okres_rakovnik_zasahy_dnes").state == "6"

    # Stejný požár ukončen -> aktualizace, ne nový zásah
    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, text=_s_radkem(UKONCENY_RADEK))
    freezer.tick(timedelta(minutes=11))
    await _obnov(hass)
    assert len(nove) == 1
    assert len(akt) == 1
    assert akt[0].data["predchozi_stav"] == "probíhající"
    assert akt[0].data["stav"] == "ukončená"
    assert hass.states.get("sensor.zasahy_jpo_okres_rakovnik_probihajici_zasahy").state == "0"


async def test_flow_spatna_url(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": "https://example.com/"}
    )
    assert result["errors"] == {"url": "invalid_url"}


async def test_flow_rozbita_stranka(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(URL, text="<html>údržba</html>")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"url": DEFAULT_URL}
    )
    assert result["errors"] == {"base": "invalid_page"}


async def test_options_interval(hass: HomeAssistant, aioclient_mock):
    aioclient_mock.get(URL, text=HTML)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(result["flow_id"], {"url": DEFAULT_URL})
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 15}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval == timedelta(minutes=15)
