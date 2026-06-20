---
feature: countries
type: plan
status: implemented
coverage: 85
audited: 2026-06-16
---

# CountryConfig: cálculo a partir del `country_iso_code`

Guía para replicar, en otro proyecto Python, el cálculo de la configuración de país (`CountryConfig`) tomando como entrada únicamente un código ISO de país (ej. `'MX'`, `'US'`, `'BR'`).

---

## 1. Resumen

`CountryConfig` NO se calcula dinámicamente. Es el resultado de **una búsqueda (lookup) en una tabla estática** de 242 países hardcodeada en `src/common/domain/data/countries.py`.

El flujo es:

```
country_iso_code (str "MX")
        │
        ▼
CountryIsoCode.from_value("MX")  ──► CountryIsoCode.MEXICO
        │
        ▼
ISO_CODE_MAPPING[CountryIsoCode.MEXICO]  ──► CountryConfig(...)
        │
        ▼  (si no existe la clave)
DEFAULT_COUNTRY_CONFIG  (ANY / USD / UTC / dial_code=0)
```

De ahí se obtienen los valores derivados (`currency_code`, `dial_code`, `dial_prefix`, `time_zone`, `emoji`, `name`, `lang`).

---

## 2. Estructura del `CountryConfig`

Archivo: `src/common/domain/models/country_config.py`

```python
from dataclasses import dataclass

from src.common.constants import DEFAULT_LANGUAGE
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.currencies import CurrencyCode
from src.common.domain.enums.locales import Language, TimeZone


@dataclass
class CountryConfig:
    name: str                       # "Mexico"
    iso_code: CountryIsoCode        # CountryIsoCode.MEXICO -> "MX"
    currency_code: CurrencyCode     # CurrencyCode.MXN      -> "MXN"
    dial_code: int                  # 52  (código telefónico internacional)
    time_zone: TimeZone             # TimeZone.AMERICA_MEXICO_CITY
    emoji: str                      # "🇲🇽"
    lang: Language = DEFAULT_LANGUAGE   # por defecto Language.ES
    dial_prefix: int | None = None  # prefijo móvil (ej. 1 para MX, 9 para BR)

    @classmethod
    def from_dict(cls, data: dict) -> 'CountryConfig':
        return cls(
            name=data.get('name'),
            iso_code=CountryIsoCode.from_value(data.get('iso_code')),
            currency_code=CurrencyCode.from_value(data.get('currency_code')),
            time_zone=TimeZone(data.get('time_zone')),
            dial_code=data.get('dial_code'),
            emoji=data.get('emoji'),
            dial_prefix=data.get('dial_prefix'),
        )
```

### Valores que se “calculan” (realmente: se resuelven)

| Campo           | Cómo se obtiene desde el `country_iso_code`                                         |
| --------------- | ----------------------------------------------------------------------------------- |
| `name`          | Lookup en tabla estática `COUNTRIES`.                                               |
| `iso_code`      | Se convierte el string al miembro de `CountryIsoCode` vía `from_value`.             |
| `currency_code` | Lookup en tabla estática (ej. `MX → MXN`).                                          |
| `dial_code`     | Lookup en tabla estática (ej. `MX → 52`, `US → 1`, `BR → 55`).                      |
| `time_zone`     | Lookup en tabla estática (ej. `MX → America/Mexico_City`).                          |
| `emoji`         | Lookup en tabla estática (bandera Unicode).                                         |
| `lang`          | Por defecto `Language.ES` (no depende del ISO, se toma de `DEFAULT_LANGUAGE`).      |
| `dial_prefix`   | Lookup en tabla estática; o vía `PHONE_NUMBER_PREFIXES_MAP` (solo `MX=1`, `BR=9`).  |

---

## 3. Enums involucrados (valores que debes replicar)

### `CountryIsoCode` (ISO 3166-1 alpha-2)

Archivo: `src/common/domain/enums/countries.py`

```python
class CountryIsoCode(BaseEnum):
    MEXICO = 'MX'
    UNITED_STATES = 'US'
    BRAZIL = 'BR'
    BOLIVIA = 'BO'
    ARGENTINA = 'AR'
    # ... 240+ miembros, todos con el alpha-2 ISO estándar
    ANY = 'ANY'   # fallback
```

### `CurrencyCode` (ISO 4217)

```python
class CurrencyCode(BaseEnum):
    MXN = 'MXN'
    USD = 'USD'
    BRL = 'BRL'
    BOB = 'BOB'
    EUR = 'EUR'
    # ... códigos ISO 4217
```

### `TimeZone` (IANA tz database)

```python
class TimeZone(BaseEnum):
    UTC = 'UTC'
    AMERICA_MEXICO_CITY = 'America/Mexico_City'
    AMERICA_NEW_YORK = 'America/New_York'
    AMERICA_SAO_PAULO = 'America/Sao_Paulo'
    AMERICA_LA_PAZ = 'America/La_Paz'
    # ... lista completa según pytz
```

### `Language`

```python
class Language(BaseEnum):
    ES = 'es'
    EN = 'en'
```

### `BaseEnum` (base compartida)

Archivo: `src/common/domain/__init__.py`

```python
from enum import Enum


class BaseEnum(Enum):
    @classmethod
    def get_members(cls):
        return [tag for tag in cls if type(tag.value) in [int, str, float]]

    @classmethod
    def choices(cls):
        return [(o.value, o.value) for o in cls if type(o.value) in [int, str, float]]

    @classmethod
    def values(cls):
        return [o.value for o in cls]

    @classmethod
    def from_value(cls, value):
        # construye el miembro a partir del valor (ej. 'MX' -> CountryIsoCode.MEXICO)
        return cls(value) if value is not None else None

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value)
```

> `from_value` es equivalente a `cls(value)` — Enum ya hace el lookup por valor.

---

## 4. La tabla estática de países

Archivo: `src/common/domain/data/countries.py`

Tiene **242 entradas** con la forma:

```python
COUNTRIES = [
    CountryConfig(
        name='Afghanistan',
        iso_code=CountryIsoCode.AFGHANISTAN,
        currency_code=CurrencyCode.AFN,
        dial_code=93,
        time_zone=TimeZone.ASIA_KABUL,
        emoji='🇦🇫',
    ),
    # ...
    CountryConfig(
        name='Mexico',
        iso_code=CountryIsoCode.MEXICO,
        currency_code=CurrencyCode.MXN,
        dial_code=52,
        dial_prefix=1,
        time_zone=TimeZone.AMERICA_MEXICO_CITY,
        emoji='🇲🇽',
    ),
    CountryConfig(
        name='United States',
        iso_code=CountryIsoCode.UNITED_STATES,
        currency_code=CurrencyCode.USD,
        dial_code=1,
        time_zone=TimeZone.AMERICA_NEW_YORK,
        emoji='🇺🇸',
    ),
    CountryConfig(
        name='Brazil',
        iso_code=CountryIsoCode.BRAZIL,
        currency_code=CurrencyCode.BRL,
        dial_code=55,
        dial_prefix=9,
        time_zone=TimeZone.AMERICA_SAO_PAULO,
        emoji='🇧🇷',
    ),
    CountryConfig(
        name='Bolivia',
        iso_code=CountryIsoCode.BOLIVIA,
        currency_code=CurrencyCode.BOB,
        dial_code=591,
        time_zone=TimeZone.AMERICA_LA_PAZ,
        emoji='🇧🇴',
    ),
    # ... ~240 países adicionales
]
```

Al final del archivo se generan los índices en memoria:

```python
ISO_CODE_MAPPING: dict[CountryIsoCode, CountryConfig] = {}
DIAL_CODE_MAPPING: dict[int, CountryConfig] = {}

for country in COUNTRIES:
    ISO_CODE_MAPPING[country.iso_code] = country
    DIAL_CODE_MAPPING[country.dial_code] = country

DEFAULT_COUNTRY_CONFIG = CountryConfig(
    name='ANY',
    iso_code=CountryIsoCode.ANY,
    currency_code=CurrencyCode.USD,
    time_zone=TimeZone.UTC,
    dial_code=0,
    emoji='🌍',
)


class CountryConfigBuilder:
    @classmethod
    def from_iso_code(cls, iso_code: CountryIsoCode) -> CountryConfig:
        return ISO_CODE_MAPPING.get(iso_code, DEFAULT_COUNTRY_CONFIG)

    @classmethod
    def from_dial_code(cls, dial_code: int) -> CountryConfig:
        return DIAL_CODE_MAPPING.get(dial_code, DEFAULT_COUNTRY_CONFIG)
```

> **Nota:** Para replicar en otro proyecto, la fuente de la tabla `COUNTRIES` se puede importar de una librería estándar como [`pycountry`](https://pypi.org/project/pycountry/) (nombre + ISO), [`phonenumbers`](https://pypi.org/project/phonenumbers/) (dial_code), y un mapping estático para `time_zone` y `emoji` (bandera Unicode = `chr(0x1F1E6 + ord(c) - ord('A'))` por cada letra del ISO).

---

## 5. Constantes globales (defaults)

Archivo: `src/common/constants.py`

```python
DEFAULT_TIMEZONE = TimeZone.MEXICO_CITY
DEFAULT_LANGUAGE = Language.ES
DEFAULT_CURRENCY_CODE = CurrencyCode.MXN
DEFAULT_COUNTRY_ISO_CODE = CountryIsoCode.MEXICO
DEFAULT_MEXICO_PREFIX = 1

# Prefijos móviles extra (útiles para números de teléfono)
PHONE_NUMBER_PREFIXES_MAP = {
    CountryIsoCode.MEXICO: 1,
    CountryIsoCode.BRAZIL: 9,
}
```

Y el helper asociado:

```python
# src/common/domain/helpers/phones.py
from src.common.constants import PHONE_NUMBER_PREFIXES_MAP
from src.common.domain.entities.common.country_config import CountryConfig


def calculate_phone_number_prefix(country_config: CountryConfig) -> int | None:
    if country_config.iso_code not in PHONE_NUMBER_PREFIXES_MAP:
        return None
    return PHONE_NUMBER_PREFIXES_MAP[country_config.iso_code]
```

---

## 6. Función self-contained lista para copiar

Versión mínima que encapsula todo el cálculo en una sola función. Ideal para portar a otro proyecto Python.

```python
from dataclasses import dataclass
from enum import Enum


# ---------- Enums ----------
class CountryIsoCode(str, Enum):
    MEXICO = 'MX'
    UNITED_STATES = 'US'
    BRAZIL = 'BR'
    BOLIVIA = 'BO'
    # ... completar con el ISO 3166-1 alpha-2
    ANY = 'ANY'


class CurrencyCode(str, Enum):
    MXN = 'MXN'
    USD = 'USD'
    BRL = 'BRL'
    BOB = 'BOB'
    # ... completar


class TimeZone(str, Enum):
    UTC = 'UTC'
    AMERICA_MEXICO_CITY = 'America/Mexico_City'
    AMERICA_NEW_YORK = 'America/New_York'
    AMERICA_SAO_PAULO = 'America/Sao_Paulo'
    AMERICA_LA_PAZ = 'America/La_Paz'
    # ... completar


class Language(str, Enum):
    ES = 'es'
    EN = 'en'


DEFAULT_LANGUAGE = Language.ES


# ---------- Dataclass ----------
@dataclass
class CountryConfig:
    name: str
    iso_code: CountryIsoCode
    currency_code: CurrencyCode
    dial_code: int
    time_zone: TimeZone
    emoji: str
    lang: Language = DEFAULT_LANGUAGE
    dial_prefix: int | None = None


# ---------- Tabla estática (extracto) ----------
COUNTRIES: list[CountryConfig] = [
    CountryConfig(
        name='Mexico',
        iso_code=CountryIsoCode.MEXICO,
        currency_code=CurrencyCode.MXN,
        dial_code=52,
        dial_prefix=1,
        time_zone=TimeZone.AMERICA_MEXICO_CITY,
        emoji='🇲🇽',
    ),
    CountryConfig(
        name='United States',
        iso_code=CountryIsoCode.UNITED_STATES,
        currency_code=CurrencyCode.USD,
        dial_code=1,
        time_zone=TimeZone.AMERICA_NEW_YORK,
        emoji='🇺🇸',
    ),
    CountryConfig(
        name='Brazil',
        iso_code=CountryIsoCode.BRAZIL,
        currency_code=CurrencyCode.BRL,
        dial_code=55,
        dial_prefix=9,
        time_zone=TimeZone.AMERICA_SAO_PAULO,
        emoji='🇧🇷',
    ),
    CountryConfig(
        name='Bolivia',
        iso_code=CountryIsoCode.BOLIVIA,
        currency_code=CurrencyCode.BOB,
        dial_code=591,
        time_zone=TimeZone.AMERICA_LA_PAZ,
        emoji='🇧🇴',
    ),
    # ... agregar el resto de los 242 países
]

ISO_CODE_MAPPING: dict[CountryIsoCode, CountryConfig] = {
    c.iso_code: c for c in COUNTRIES
}
DIAL_CODE_MAPPING: dict[int, CountryConfig] = {
    c.dial_code: c for c in COUNTRIES
}

DEFAULT_COUNTRY_CONFIG = CountryConfig(
    name='ANY',
    iso_code=CountryIsoCode.ANY,
    currency_code=CurrencyCode.USD,
    time_zone=TimeZone.UTC,
    dial_code=0,
    emoji='🌍',
)

PHONE_NUMBER_PREFIXES_MAP: dict[CountryIsoCode, int] = {
    CountryIsoCode.MEXICO: 1,
    CountryIsoCode.BRAZIL: 9,
}


# ---------- API pública ----------
def country_config_from_iso(iso_code_str: str) -> CountryConfig:
    """Resuelve el CountryConfig completo a partir del string ISO alpha-2."""
    try:
        iso = CountryIsoCode(iso_code_str)
    except ValueError:
        return DEFAULT_COUNTRY_CONFIG
    return ISO_CODE_MAPPING.get(iso, DEFAULT_COUNTRY_CONFIG)


def country_config_from_dial(dial_code: int) -> CountryConfig:
    return DIAL_CODE_MAPPING.get(dial_code, DEFAULT_COUNTRY_CONFIG)


def calculate_phone_number_prefix(cc: CountryConfig) -> int | None:
    return PHONE_NUMBER_PREFIXES_MAP.get(cc.iso_code)
```

### Uso

```python
cfg = country_config_from_iso('MX')
# CountryConfig(
#     name='Mexico',
#     iso_code=CountryIsoCode.MEXICO,
#     currency_code=CurrencyCode.MXN,
#     dial_code=52,
#     time_zone=TimeZone.AMERICA_MEXICO_CITY,
#     emoji='🇲🇽',
#     lang=Language.ES,
#     dial_prefix=1,
# )

cfg.currency_code   # CurrencyCode.MXN
cfg.dial_code       # 52
cfg.time_zone.value # 'America/Mexico_City'
cfg.dial_prefix     # 1

country_config_from_iso('ZZ')  # devuelve DEFAULT_COUNTRY_CONFIG (ANY)
```

---

## 7. Puntos clave para la réplica

1. **No hay cálculo algorítmico**: todo sale de una tabla estática (`COUNTRIES`) + índice dict por ISO.
2. **Fallback seguro**: cualquier ISO desconocido devuelve `DEFAULT_COUNTRY_CONFIG` (`ANY` / `USD` / `UTC` / `dial_code=0`).
3. **`lang` NO depende del país**: siempre arranca en `DEFAULT_LANGUAGE` (`es`) salvo que lo sobreescribas.
4. **`dial_prefix`** tiene dos fuentes redundantes en el repo: el propio `CountryConfig.dial_prefix` y el helper `calculate_phone_number_prefix()` que mapea `MX=1`, `BR=9`. Para otros países es `None`.
5. **`emoji`** es la bandera Unicode. Si no quieres mantener 242 emojis hardcoded, se puede generar: `''.join(chr(0x1F1E6 + ord(c) - ord('A')) for c in iso_alpha2)`.
6. **Fuentes sugeridas** para no mantener la tabla a mano en el nuevo proyecto:
   - [`pycountry`](https://pypi.org/project/pycountry/) → `name`, `iso_code`, `currency_code`.
   - [`phonenumbers`](https://pypi.org/project/phonenumbers/) → `dial_code` (via `phonenumbers.country_code_for_region(iso)`).
   - [`babel`](https://pypi.org/project/babel/) → zona horaria principal por país.

## 8. Archivos de referencia en este repo

- `src/common/domain/models/country_config.py` — dataclass.
- `src/common/domain/data/countries.py` — tabla de 242 países + builder.
- `src/common/domain/enums/countries.py` — `CountryIsoCode`.
- `src/common/domain/enums/currencies.py` — `CurrencyCode`.
- `src/common/domain/enums/locales.py` — `TimeZone`, `Language`.
- `src/common/domain/helpers/phones.py` — `calculate_phone_number_prefix`.
- `src/common/constants.py` — `DEFAULT_LANGUAGE`, `PHONE_NUMBER_PREFIXES_MAP`, etc.
- `src/common/domain/__init__.py` — `BaseEnum`.