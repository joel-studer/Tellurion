# SENSOR SOURCE CATALOGS (V18 — where candidates come from)

> Catalogs are discovery inputs, not approvals. A listing never
> implies redistributable, commercial-safe, or fresh. Every candidate
> lands in the registry as NEEDS_TERMS_REVIEW until qualified.

| Catalog | Scope | Licence (catalog itself) | Freshness | Quality | Why useful |
|---|---|---|---|---|---|
| public-apis/public-apis | 1,400+ public APIs by category | MIT (list, not the APIs) | community-maintained, uneven | mixed; auth/https/CORS flags handy | broad first sweep; `--in` file for `import_public_apis.py` |
| NOAA / weather.gov | US weather alerts + forecast | US public domain | real-time | high (US only) | only weather leg that is both keyless and public-domain |
| USGS Earthquake Hazards | quakes global | US public domain | minute feeds | high | only seismic leg that is keyless + open |
| NASA EONET | curated natural events | open metadata | near-real-time, intermittent | medium | disaster vocabulary + categories |
| NASA FIRMS | active fires | per-user key terms | NRT | high | wildfire leg for key holders |
| OpenSky Network | air traffic states | account terms | ~10 s snapshots | high where covered | aviation leg for key holders; quota-priced |
| AISStream | vessel stream (WS) | account terms | real-time | high where covered | maritime leg for key holders (server proxy) |
| AISHub | cooperative vessel feed | membership terms | real-time | high for members | receiver-owner leg only |
| Open-Meteo | forecast grids | terms-gated (attribution) | hourly runs | good | non-US weather overlay after sign-off |
| Public STAC catalogs | satellite scenes | per-collection | archive + NRT | high | footprint/preview vocabulary |
| DOT operator feeds | traffic cameras | per-operator | snapshots | medium | camera points after per-operator sign-off |
| GDELT | global events/news | free with attribution norms | 15-min updates | noisy | event candidates; review before any use |

Rule: enrich every import with rights + rate limits + commercial
terms + freshness + coverage before it touches the registry as
anything stronger than NEEDS_TERMS_REVIEW.
