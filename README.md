# 🚒 Zásahy JPO – Středočeský kraj

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-03A9F4.svg)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/github/v/release/TVUJ-UCET/ha-pkr-zasahy)](https://github.com/TVUJ-UCET/ha-pkr-zasahy/releases)

Integrace pro Home Assistant, která sleduje **výjezdy hasičů ve Středočeském kraji**.
Data bere ze stránky [Zásahy jednotek požární ochrany](https://pkr.kr-stredocesky.cz/pkr/zasahy-jpo/)
na Portálu krizového řízení Středočeského kraje. V HA z nich dělá senzory a eventy,
na které můžeš navázat notifikace nebo kartu v dashboardu.

> *English: Home Assistant custom integration that tracks fire brigade incidents in the
> Central Bohemian Region (Czechia) from the regional crisis management portal.
> Provides sensors and events for new incidents. The UI is in Czech and English.*

## Co umí

- **Filtr podle okresu a stupně poplachu:** stejný filtr, jaký si naklikáš na webu.
- **Senzory:** dnešní zásahy, probíhající zásahy, přehled za poslední týden a poslední zásah.
- **Event při novém výjezdu**, takže notifikaci dostaneš jen pro obce, které tě zajímají.
- **Event při změně stavu**, třeba když zásah přejde z probíhajícího na ukončený.
- **Nastavení celé přes UI**, bez YAML. Víc okresů = víc instancí.
- **Žádné notifikace navíc po restartu:** první načtení se jen zapamatuje.
- **Šetří databázi:** seznamy zásahů se neukládají do recorderu.

## Instalace

### HACS (doporučeno)

[![Otevřít v HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TVUJ-UCET&repository=ha-pkr-zasahy&category=integration)

Nebo ručně: **HACS → ⋮ → Custom repositories**, vlož `https://github.com/TVUJ-UCET/ha-pkr-zasahy`
a jako typ zvol **Integration**. Pak integraci najdi v HACS, nainstaluj ji a restartuj Home Assistant.

### Ručně

1. Stáhni si poslední [release](https://github.com/TVUJ-UCET/ha-pkr-zasahy/releases).
2. Složku `custom_components/pkr_zasahy` zkopíruj do `/config/custom_components/`.
3. Restartuj Home Assistant.

## Nastavení

[![Přidat integraci](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=pkr_zasahy)

1. Otevři [stránku zásahů](https://pkr.kr-stredocesky.cz/pkr/zasahy-jpo/) a v pravém panelu
   **Filtr** si vyber okres. Můžeš přidat i stupeň poplachu.
2. Zkopíruj adresu z prohlížeče.
3. V HA otevři **Nastavení → Zařízení a služby → Přidat integraci → Zásahy JPO** a adresu vlož.

Název instance se doplní sám podle filtru, například *Zásahy JPO – okres Rakovník*.
Výchozí adresa vede na okres Rakovník:

```
https://pkr.kr-stredocesky.cz/pkr/zasahy-jpo/?q=&r_cast_uzemi__in=1192
```

**Interval kontroly** změníš v **Konfigurovat**: 5–60 minut, výchozí je 10.

## Entity

Názvy entit se tvoří z názvu instance. Níže jsou ID pro HA v češtině a okres Rakovník.

| Entita | Stav | Atributy |
|---|---|---|
| `sensor.zasahy_jpo_okres_rakovnik_zasahy_dnes` | počet dnešních zásahů | `zasahy` |
| `sensor.zasahy_jpo_okres_rakovnik_probihajici_zasahy` | počet neukončených zásahů | `zasahy` |
| `sensor.zasahy_jpo_okres_rakovnik_zasahy_za_posledni_tyden` | počet zásahů v seznamu na webu | `zasahy` |
| `sensor.zasahy_jpo_okres_rakovnik_posledni_zasah` | název posledního zásahu | pole posledního zásahu (viz níže) |
| `sensor.zasahy_jpo_okres_rakovnik_cas_posledniho_zasahu` | čas posledního zásahu (timestamp) | – |

Přesná ID si ověříš v **Vývojářské nástroje → Stavy**.

### Pole zásahu

Tato pole má každá položka v atributu `zasahy` a také data eventů.

| Pole | Příklad | Popis |
|---|---|---|
| `nazev` | `požár - lesní porost - Mšecké Žehrovice` | celý název z webu |
| `kategorie` | `požár` | požár, dopravní nehoda, technická pomoc, únik nebezpečných látek, záchrana osob a zvířat… |
| `podtyp` | `lesní porost` | upřesnění události |
| `typ` | `požár` | typ podle ikony na webu |
| `stav` | `ukončená` | stav události |
| `aktivni` | `false` | `true`, dokud zásah není ukončený |
| `obec` | `Mšecké Žehrovice` | místo události |
| `okres` | `Rakovník` | u okresního města bývá `null` |
| `stupen` | `I.` | stupeň poplachu: `I.`, `II.`, `III.` nebo `Z` |
| `cas` | `2026-10-03T14:10:00+02:00` | poslední aktualizace dat (ISO 8601) |
| `id` | `a1b2c3d4e5f6` | identifikátor řádku |

## Eventy

| Event | Kdy se vyšle | Pole navíc |
|---|---|---|
| `pkr_zasahy_novy_zasah` | V seznamu se objeví nový zásah. | `entry_id` |
| `pkr_zasahy_aktualizace_zasahu` | Známá událost (stejný název a obec) dostane novější čas, typicky po změně stavu. | `entry_id`, `predchozi_stav` |

## Příklady

### Notifikace pro vybrané obce

```yaml
alias: "Hasiči – výjezd v okolí"
mode: queued
triggers:
  - trigger: event
    event_type: pkr_zasahy_novy_zasah
conditions:
  - condition: template
    value_template: >
      {{ trigger.event.data.obec in ['Rakovník', 'Lužná', 'Senomaty'] }}
actions:
  - action: notify.mobile_app_telefon
    data:
      title: >
        🚒 {{ trigger.event.data.kategorie | capitalize }} – {{ trigger.event.data.obec }}
      message: >
        {{ trigger.event.data.podtyp }} · {{ trigger.event.data.stav }}
        · stupeň {{ trigger.event.data.stupen }}
      data:
        url: "https://pkr.kr-stredocesky.cz/pkr/zasahy-jpo/?q=&r_cast_uzemi__in=1192"
```

Další užitečné podmínky:

```jinja
{{ trigger.event.data.kategorie == 'požár' }}   {# jen požáry #}
{{ trigger.event.data.stupen != 'I.' }}         {# jen vyšší stupeň poplachu #}
```

### Oznámení o ukončení zásahu

```yaml
alias: "Hasiči – zásah ukončen"
triggers:
  - trigger: event
    event_type: pkr_zasahy_aktualizace_zasahu
conditions:
  - condition: template
    value_template: "{{ not trigger.event.data.aktivni }}"
actions:
  - action: notify.mobile_app_telefon
    data:
      message: "✅ {{ trigger.event.data.nazev }} – ukončeno"
```

### Karta do dashboardu

```yaml
type: markdown
title: 🚒 Zásahy – okres Rakovník
content: |
  {% set z = state_attr('sensor.zasahy_jpo_okres_rakovnik_zasahy_za_posledni_tyden', 'zasahy') or [] %}
  | Čas | Událost | Obec | Stav |
  |---|---|---|---|
  {% for i in z[:10] -%}
  | {{ as_timestamp(i.cas) | timestamp_custom('%d.%m. %H:%M') }} | {{ i.kategorie }} – {{ i.podtyp }} | {{ i.obec }} | {{ '🔴' if i.aktivni else '⚪' }} {{ i.stav }} |
  {% endfor %}
```

## Jak to funguje

Web nemá veřejné API. Integrace proto v nastaveném intervalu stáhne HTML stránky,
přečte z něj tabulku zásahů a porovná ji s tím, co už zná. Nové řádky vyšle jako
`pkr_zasahy_novy_zasah`. Řádky se stejným názvem a obcí, které do 6 hodin dostanou
novější čas, vyšle jako `pkr_zasahy_aktualizace_zasahu`.

## Omezení

- **Data jsou zpožděná a orientační.** Web to sám uvádí a události zveřejňuje tak,
  jak byly vyhodnoceny při vzniku.
- **Čas vzniku události web neukazuje**, jen *Poslední aktualizaci dat*. Podle ní
  se počítají i dnešní zásahy.
- **Stránka ukazuje zhruba poslední týden**, starší zásahy integrace nezná.
- **Integrace závisí na struktuře webu.** Když se HTML změní, senzory přejdou do stavu
  *nedostupné* a v logu bude „Stránka má neočekávanou strukturu“. V tom případě
  [založ issue](https://github.com/TVUJ-UCET/ha-pkr-zasahy/issues).
- **Neptej se moc často.** Web automatické stahování nevítá. Kratší interval než
  5 minut integrace nepovolí a výchozích 10 minut na notifikace bohatě stačí.

## Vývoj

```bash
pip install pytest-homeassistant-custom-component
pytest tests
```

`tests/test_parser.py` testuje parser na uložené kopii stránky a nepotřebuje
Home Assistant, stačí `pytest`. `tests/test_integration.py` pouští config flow,
senzory a eventy v testovací instanci HA.

Logování pro ladění:

```yaml
logger:
  logs:
    custom_components.pkr_zasahy: debug
```

## Upozornění

Neoficiální projekt, který nemá nic společného se Středočeským krajem ani s HZS ČR.
Na notifikace z této integrace nespoléhej v situacích, kde jde o bezpečnost.
Data patří jejich provozovateli.

## Licence

[MIT](LICENSE)
