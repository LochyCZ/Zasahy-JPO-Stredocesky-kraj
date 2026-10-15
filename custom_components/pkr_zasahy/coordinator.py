"""Coordinator: stahuje stránku, parsuje ji a posílá eventy o nových zásazích."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_AKTUALIZACE,
    EVENT_NOVY_ZASAH,
    USER_AGENT,
)
from .parser import ParseError, Zasah, parse_zasahy, rozdil

_LOGGER = logging.getLogger(__name__)

# Jak dlouho si pamatujeme řádky, které už ze stránky zmizely
# (stránka ukazuje zhruba poslední týden).
PAMET = timedelta(days=10)

type PkrConfigEntry = ConfigEntry["PkrCoordinator"]


async def async_fetch(session: aiohttp.ClientSession, url: str) -> str:
    """Stáhne HTML stránky."""
    async with asyncio.timeout(30):
        resp = await session.get(
            url, headers={"User-Agent": USER_AGENT, "Accept-Language": "cs"}
        )
        resp.raise_for_status()
        return await resp.text()


@dataclass
class PkrData:
    zasahy: list[Zasah] = field(default_factory=list)
    stazeno: datetime | None = None


class PkrCoordinator(DataUpdateCoordinator[PkrData]):
    """Pravidelně stahuje seznam zásahů."""

    config_entry: PkrConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PkrConfigEntry) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self._url: str = entry.data[CONF_URL]
        self._session = async_get_clientsession(hass)
        self._zname: dict[str, Zasah] = {}
        self._prvni_beh = True

    async def _async_update_data(self) -> PkrData:
        try:
            html = await async_fetch(self._session, self._url)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Stránku se nepodařilo stáhnout: {err}") from err

        try:
            zasahy = await self.hass.async_add_executor_job(parse_zasahy, html)
        except ParseError as err:
            raise UpdateFailed(f"Stránka má neočekávanou strukturu: {err}") from err

        self._zpracuj_eventy(zasahy)
        return PkrData(zasahy=zasahy, stazeno=dt_util.now())

    def _zpracuj_eventy(self, zasahy: list[Zasah]) -> None:
        # První načtení po startu jen naplní paměť, ať po restartu HA
        # nepřijde dávka notifikací za celý týden.
        if not self._prvni_beh:
            nove, aktualizovane = rozdil(self._zname, zasahy)
            for z in nove:
                _LOGGER.debug("Nový zásah: %s", z.nazev)
                self.hass.bus.async_fire(EVENT_NOVY_ZASAH, self._event_data(z))
            for predchozi, z in aktualizovane:
                data = self._event_data(z)
                data["predchozi_stav"] = predchozi.stav
                self.hass.bus.async_fire(EVENT_AKTUALIZACE, data)
        self._prvni_beh = False

        hranice = dt_util.now() - PAMET
        self._zname = {
            uid: z for uid, z in self._zname.items() if z.cas >= hranice
        }
        self._zname.update({z.uid: z for z in zasahy})

    def _event_data(self, z: Zasah) -> dict:
        data = z.as_dict()
        data["entry_id"] = self.config_entry.entry_id
        return data
