<p align="center"><img src="https://raw.githubusercontent.com/cunningplay/ha-bajagas/main/custom_components/bajagas/brand/icon.png" alt="BajaGas" width="120"></p>

# Precio del gas LP de BajaGas para Home Assistant

**Español** · [English](#bajagas-lp-price-for-home-assistant)

Una integración personalizada que sigue el **precio por litro del gas LP** que
BajaGas (el proveedor) publica por ciudad en <https://bajagas.com/precios>.
Casa tiene un tanque de gas LP en la azotea con sensor de litros, pero no de
precio; esta integración expone el precio actual (MXN/L) de la ciudad elegida
como un sensor, para que Home Assistant pueda valuar el gas o una recarga.

- El precio se consulta una vez al día (configurable). La página tiene cinco
  tablas de precios; solo se lee la **primera** (la del precio por litro), no
  las de cilindros ni tanques.
- El precio se guarda localmente. Si la página no está disponible, el sensor
  sigue mostrando el último valor guardado.
- El historial de precios se guarda en las **estadísticas a largo plazo**, así
  que se puede graficar la evolución del precio.

## Instalación (HACS)

1. HACS → Integraciones → ⋮ → Repositorios personalizados (*Custom
   repositories*) → agrega este repositorio como *Integración* (*Integration*).
2. Instala **BajaGas LP price** y reinicia Home Assistant.
3. Ajustes → Dispositivos y servicios → Añadir integración (*Settings →
   Devices & services → Add integration*) → **BajaGas LP price**.

Instalación manual: copia `custom_components/bajagas` en tu carpeta
`config/custom_components/`.

Requiere Home Assistant 2026.10 o más reciente.

## Configuración

Al añadir la integración, Home Assistant lee la página de precios y muestra una
lista de ciudades. Elige la ciudad cuyo precio quieres seguir (Tijuana viene
sugerida). Se crea una entrada (y un dispositivo) por ciudad.

En **Configurar** puedes cambiar cada cuántas horas se revisa el precio
(predeterminado 24, mínimo 1).

## Entidad

Un dispositivo, `BajaGas <Ciudad>`, con un sensor:

| Entidad | Descripción |
|---|---|
| Precio del gas LP | Precio actual por litro (MXN/L). Atributos: `all_prices` (todas las ciudades), `updated`, `previous`, `change` (contra el anterior), `history` (hasta 30 registros recientes) |

## Estadísticas a largo plazo

Cada día que cambia el precio se agrega un punto a la estadística externa
`bajagas:<ciudad>_price` (MXN/L, tipo media), para graficar el precio a lo largo
del tiempo.

## Privacidad

Solo se descargan precios públicos; no hay datos personales. El último precio y
el historial se guardan en `.storage/bajagas.<entry_id>` dentro de la carpeta de
configuración de Home Assistant, y ese archivo se borra al eliminar la entrada.

## Licencia

MIT

---

# BajaGas LP price for Home Assistant

[Español](#precio-del-gas-lp-de-bajagas-para-home-assistant) · **English**

A custom integration that tracks the **per-liter LP gas price** that BajaGas
(the supplier) publishes by city at <https://bajagas.com/precios>. The house has
a roof LP tank with a liters sensor but no price; this integration exposes the
current price (MXN/L) for the chosen city as a sensor so Home Assistant can
value the gas or a refill.

- The price is polled once a day (configurable). The page has five price tables;
  only the **first** one (the per-liter price) is read, not the cylinder or tank
  tables.
- The price is stored locally. If the page is unreachable, the sensor keeps
  showing the last stored value.
- The price history is written to **long-term statistics**, so the price can be
  charted over time.

## Install (HACS)

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cunningplay&repository=ha-bajagas&category=integration)

1. In HACS, search for **BajaGas LP price** and download it, then restart Home Assistant.
2. Settings → Devices & services → Add integration → **BajaGas LP price**.

Older HACS versions that don't list it yet: HACS → ⋮ → Custom repositories → add
`https://github.com/cunningplay/ha-bajagas` as an *Integration*, then follow the steps above.

Manual install: copy `custom_components/bajagas` into your
`config/custom_components/`.

Requires Home Assistant 2026.10 or newer.

## Setup

When you add the integration, Home Assistant reads the price page and shows a
list of cities. Pick the city whose price to track (Tijuana is suggested). One
config entry (and one device) per city.

Under **Configure** you can change how often the price is checked (hours;
default 24, minimum 1).

## Entity

One device, `BajaGas <City>`, with one sensor:

| Entity | Description |
|---|---|
| LP price | Current per-liter price (MXN/L). Attributes: `all_prices` (every city), `updated`, `previous`, `change` (vs previous), `history` (up to 30 recent entries) |

## Long-term statistics

Each day the price changes, a point is added to the external statistic
`bajagas:<city>_price` (MXN/L, mean type) so the price can be charted over time.

## Privacy

Only public prices are fetched; there is no personal data. The last price and
the history are stored in `.storage/bajagas.<entry_id>` in the Home Assistant
config folder, and that file is deleted when the entry is removed.

## Development

```sh
# Scraper (pure, no Home Assistant)
uvx --with pytest pytest -q tests

# Home Assistant integration tests (config flow, polling, Store, statistics)
uvx -p 3.14 --with pytest-homeassistant-custom-component pytest -q tests_ha -o asyncio_mode=auto
```

The scraper (`custom_components/bajagas/scraper.py`) has no Home Assistant
imports and is tested against the real page saved as `tests/fixtures/precios.html`.

## License

MIT
