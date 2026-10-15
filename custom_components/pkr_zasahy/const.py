"""Konstanty integrace Zásahy JPO."""

DOMAIN = "pkr_zasahy"

CONF_URL = "url"
CONF_SCAN_INTERVAL = "scan_interval"

URL_PREFIX = "https://pkr.kr-stredocesky.cz/pkr/zasahy-jpo/"
DEFAULT_URL = f"{URL_PREFIX}?q=&r_cast_uzemi__in=1192"

DEFAULT_SCAN_INTERVAL = 10  # minut
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 60

EVENT_NOVY_ZASAH = f"{DOMAIN}_novy_zasah"
EVENT_AKTUALIZACE = f"{DOMAIN}_aktualizace_zasahu"

USER_AGENT = "HomeAssistant-pkr_zasahy/1.0 (osobni pouziti)"
