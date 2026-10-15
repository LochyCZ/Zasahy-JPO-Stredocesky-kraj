"""Config flow pro Zásahy JPO."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    URL_PREFIX,
)
from .coordinator import async_fetch
from .parser import ParseError, parse_okres, parse_zasahy


def _normalizuj(url: str) -> str:
    """Seřadí query parametry a zahodí prázdné, ať jde URL použít jako unique_id."""
    parts = urlsplit(url.strip())
    query = sorted((k, v) for k, v in parse_qsl(parts.query) if v)
    return f"{URL_PREFIX}?{urlencode(query)}" if query else URL_PREFIX


class PkrConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            raw = user_input[CONF_URL].strip()
            if not raw.startswith(URL_PREFIX):
                errors[CONF_URL] = "invalid_url"
            else:
                url = _normalizuj(raw)
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                try:
                    html = await async_fetch(async_get_clientsession(self.hass), url)
                    await self.hass.async_add_executor_job(parse_zasahy, html)
                except (aiohttp.ClientError, TimeoutError):
                    errors["base"] = "cannot_connect"
                except ParseError:
                    errors["base"] = "invalid_page"
                else:
                    okres = parse_okres(html)
                    title = f"Zásahy JPO – {okres}" if okres else "Zásahy JPO"
                    return self.async_create_entry(title=title, data={CONF_URL: url})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL,
                        default=(user_input or {}).get(CONF_URL, DEFAULT_URL),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                    )
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> PkrOptionsFlow:
        return PkrOptionsFlow()


class PkrOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="min",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
