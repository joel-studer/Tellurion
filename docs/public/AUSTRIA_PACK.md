# AUSTRIA DEMO PACK (rights-first, no scraping)

Base demo ships CC0 reference points only (`plugins/austria_pack`).
Live Austrian feeds are operator opt-in: the user enables a feed after
verifying its terms. Nothing is bundled, polled, or credentialed.

## Qualified / verifiable Austrian public sources

| domain | source | operator | terms / licence | endpoint pattern | notes |
|---|---|---|---|---|---|
| weather | GeoSphere Austria open data | GeoSphere Austria | open (CC-BY-4.0 variants per dataset; verify) | https://www.geosphere.at/ / https://data.hub.geosphere.at/ | station obs + warnings; attribute GeoSphere Austria |
| open government | data.gv.at catalogue | Austrian federal / state publishers | CC-BY-4.0 (per dataset) | https://www.data.gv.at/ | catalogue only; follow per-dataset licence |
| transport timetables | OEBB / VOR / Linz AG GTFS static | OEBB-Personenverkehr et al. | per-agency open terms (verify feed) | agency GTFS zip | pin feed version + date; static context |
| road conditions | ASFINAG traffic info | ASFINAG | per-operator terms (verify; snapshots only) | https://www.asfinag.at/ | display-only; no bulk mirror without sign-off |
| hydrology | eHYD (BML) | BML / Hydrographischer Dienst | open (verify per dataset) | https://ehyd.gv.at/ | gauge levels; keep observation time |
| air quality | Umweltbundesamt / EEA | UBA / EEA | open reuse with attribution | https://www.umweltbundesamt.at/ | station obs; EEA leg covers Austria too |
| civil protection | AT-Alert / Zivilschutz (public notices) | BMI / states | public notices (link + summary) | per-state portals | GOVERNMENT_NOTICE, never scrape private portals |
| public webcams | operator-authorised only | road / tourism / ski operators | per-operator written terms | per-operator snapshot URL | snapshot + operator + time + rights shown; streams never embedded without permission |

## Rules

- Rights first: each feed stays NEEDS_TERMS_REVIEW until its licence
  page is archived (URL + hash + date in the PR).
- No scraping of private sites, no paywall/auth bypass, no credentials
  in the repo. User keys live in local env only.
- Demo route: Vienna (APT-VIE 48.11,16.57) -> Port of Vienna Freudenau
  (48.18,16.46) -> Semmering corridor. Open with `?region=Austria`.
