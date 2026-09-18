# REGIONAL PLUGIN PACKS (adapter collections, no restricted data)

Packs are documentation + manifest lists, not data bundles. Each pack
names the qualified feeds for a region and the per-feed terms to verify.
No pack bundles credentials, bulk data, or restricted feeds.

## Europe pack

- EEA air quality (EU open), Copernicus EMS activations (free open),
  OSM static context (ODbL), per-country GTFS static (per-agency),
  national met-office alerts where public-domain/open (verify per
  country; e.g. DWD open data, Meteo-France open licence).

## US pack

- USGS earthquakes (PD), NWS alerts+forecast (PD), EPA AirNow (PD),
  USGS volcano notices (PD), FAA public notices where open (verify
  endpoint; ASWS leg is best-effort), GTFS static per agency.

## Austria pack

See `AUSTRIA_PACK.md`. Smallest complete demo: GeoSphere + data.gv.at
+ OEBB GTFS static + ASFINAG display + eHYD + UBA/EEA AQ.

## UK pack

- Met Office open data (verify DataPoint/open terms per product),
  Environment Agency flood warnings (OGL), OSM context, per-operator
  GTFS/NaPTAN (per-agency), EEA-adjacent AQ via Defra open (verify).

## Japan pack

- JMA public alerts where machine-readable + redistributable (verify;
  otherwise link-only), USGS global quake leg covers Japan seismicity,
  EONET/GDACS disaster legs, OSM context, GTFS static per agency.

## Global disaster pack

- USGS + EONET (metadata) + GDACS (summary/link) + ReliefWeb (reports)
  + Copernicus EMS (activations). Corroboration rule: link legs that
  share an upstream feed as ONE SOURCE, never independent.

Enabling any pack: install the listed sensor plugins explicitly,
supply own keys locally where required, keep fixtures as fallback.
Base demo never auto-enables a pack.
