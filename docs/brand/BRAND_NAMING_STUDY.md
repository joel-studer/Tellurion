# Brand naming study

Internal codename: **GOD'S EYE**. Public product name: **Tellurion** (recommended
and applied to public-facing surfaces). Python modules keep the `gods_eye`
name for compatibility; renaming them would churn every import for no user
benefit.

> Not a trademark clearance. The checks below are quick collision screens run
> on 2026-09-15/16: GitHub repository search by name, the PyPI JSON API, the npm
> registry, and a general web search. Before public launch, run a formal
> trademark search (Nice classes 9 and 42) and check domains.

## Goals

Unique, short, memorable, pronounceable internationally, serious and
technical, rooted in world / signals / evidence / time; not generic
cybersecurity, not military, not "AI something", not borrowed from category
leaders; usable as a repository name and a logo; one word preferred.

Excluded up front, as the brief requires: WorldLens, TerraScope, Orbiscope,
WorldView, God's Eye, God View, Argus, Atlas, Sentinel, Omni, Nexus.

## Candidates screened (40)

`GH repos` = repositories with the word in their name (GitHub search), with the
most-starred match. `PyPI` / `npm` = package name already taken.

| Name | Meaning | GH repos (top match, stars) | PyPI | npm | Verdict |
|---|---|---|---|---|---|
| **Tellurion** | orrery-like instrument showing Earth's day/night and seasons over time | 38 (colorizeDiffusion, 97) | free | free | **recommended** |
| Kairograph | *kairos* (the right moment) + graph | 3 | free | free | top 3; an Apple Watch astrology app uses the name |
| Earthline | Earth + worldline | 20 | free | free | top 3; close to EarthLink |
| Meridiem | midday / meridian: time and geography | 32 | free | taken | legal SaaS "Meridiem" |
| Graticule | the latitude/longitude grid | 142 (geocoding gem, 298) | free | taken | same-domain Ruby geocoder |
| Chorograph | a description of regions; surveying instrument | 25 | free | taken | Chorograph Ltd sells temporal graph analytics: too close |
| Sphaera | Latin "sphere" | 44 | taken | free | weak meaning |
| Gnomon | the part of a sundial that casts the shadow | 188 (paypal/gnomon, 932) | taken | taken | crowded |
| Orrery | model of the solar system | 817 | taken | taken | crowded; astronomy apps |
| Isochron | line of equal time | 700 | taken | taken | NXP tool, vending-telemetry company |
| Terrella | "little Earth" model globe | 17 (MapLibre Earth relief globe) | taken | taken | **rejected**: same-domain globe project |
| Earthstate | the state of the Earth | 3 | free | free | **rejected**: existing "Earth State" intelligence platform |
| Worldline | an object's path through spacetime | 840 | free | taken | **rejected**: large payments company |
| Meridian | line of longitude | 8105 | taken | taken | crowded |
| Tessera | mosaic tile (evidence pieces) | 9885 | taken | taken | crowded; OCR confusion |
| Vantage | point of view | 5187 | taken | taken | crowded |
| Strata | layers | 5911 | taken | taken | crowded |
| Lumen | light | 20014 | taken | taken | crowded |
| Nadir | point directly below a satellite | 3147 | taken | taken | crowded; negative connotation |
| Provena | provenance | 3797 | taken | free | reads as "Provenance" emulator |
| Ephemeris | table of positions over time | 623 | taken | taken | hard to spell |
| Isobar | line of equal pressure | 387 | taken | free | ad agency; music library |
| Palimpsest | layered, rewritten record | 398 | taken | taken | hard to say |
| Sightline | line of sight | 342 | taken | taken | surveillance tone |
| Heliograph | sun signal instrument | 46 | free | taken | npm taken |
| Umbrae | shadows | 56 | free | taken | dark tone |
| Planisphere | star chart | 98 | taken | taken | long |
| Ecliptica | the Sun's path | 65 | taken | free | awkward |
| Horologe | clock | 43 | free | taken | time only |
| Worldclock | world clock | 1403 | free | free | generic |
| Tellurian | of the Earth | 52 | free | free | energy company "Tellurian" |
| Tellurio | shortened tellurion | 27 | taken | taken | package names taken |
| Orbitra | orbit | 203 | taken | free | link shortener |
| Noctilux | night light | 17 (VS Code theme, 116) | free | free | theme association |
| Geotide | geo + tide | 4 | free | free | flood-prediction project; narrow meaning |
| Tessellum | small tile | 5 | taken | taken | unclear |
| Terravela | earth + sail | 1 | free | free | no meaning |
| Gnomonic | a map projection | 20 | free | free | too academic |
| Ortelius | first modern atlas maker | 134 (ortelius/ortelius, 402) | taken | taken | existing open-source catalog |
| Argus-style and "Eye" names | surveillance tone | n/a | n/a | n/a | avoided by policy |

## Top 10 (scored 1 to 10; collision risk: 10 = highest risk)

| # | Name | Uniqueness | Memorability | Meaning | Visual brand | GitHub searchability | Collision risk |
|---|---|---|---|---|---|---|---|
| 1 | **Tellurion** | 9 | 8 | 10 | 9 | 8 | 3 |
| 2 | Kairograph | 7 | 6 | 7 | 6 | 9 | 5 |
| 3 | Earthline | 6 | 8 | 6 | 6 | 8 | 5 |
| 4 | Sphaera | 6 | 6 | 6 | 7 | 7 | 4 |
| 5 | Meridiem | 5 | 6 | 7 | 6 | 8 | 6 |
| 6 | Graticule | 6 | 5 | 7 | 7 | 6 | 6 |
| 7 | Chorograph | 6 | 5 | 8 | 6 | 8 | 8 |
| 8 | Gnomon | 5 | 6 | 8 | 7 | 4 | 7 |
| 9 | Isochron | 4 | 6 | 7 | 5 | 4 | 7 |
| 10 | Orrery | 3 | 8 | 7 | 8 | 3 | 8 |

## Top 3

1. **Tellurion**: a tellurion is the classroom instrument that shows how the
   Earth turns through day and night and moves through the seasons. It is
   exactly "the state of the world, through time". It carries a distinctive
   symbol (a sunlit sphere, its terminator, and a tilted orbit), is free on PyPI
   and npm, and its web presence is a small mobile-game studio in another
   field. Weakness: a three-syllable stress pattern (tel-LOOR-ee-on) that
   non-native speakers may need to hear once.
2. **Kairograph**: "the graph of the right moment" fits the Time Machine, and
   package names are free, but an astrology watch app and several domains use
   the name, and it reads as time-only.
3. **Earthline**: plain and easy to say, free on package registries, but
   generic, weak as a trademark, and close to EarthLink.

## Recommendation

**Tellurion.** It is the only candidate that scores high on meaning, visual
potential, and uniqueness together, with low collision risk in the software
space.

Applied to public-facing surfaces: app header, landing page, README, gallery,
screenshots, social images, docs, demo banner, and the `tellurion` command
(alias of `godseye`). At launch the maintainer should: rename the GitHub
repository to `tellurion`, reserve the PyPI name `tellurion`, and run the
formal trademark and domain checks above.

## Sources (web checks)

- [Tellurion Mobile on the App Store](https://apps.apple.com/us/developer/tellurion-mobile/id941623768)
- [Alchez/terrella: MapLibre Earth relief globe](https://github.com/Alchez/terrella)
- [Meridiem legal practice software](https://meridiem.app/)
- [Chorograph (Crunchbase)](https://www.crunchbase.com/organization/chorograph)
- [NXP/isochron](https://github.com/NXP/isochron)
- [Kairograph astrology app](https://kairograph.app/)
- [Earth State intelligence platform (ixo)](https://thereadingape.substack.com/p/earth-state-ixo-protocol-cosmoverse)
- [Orrery open-source projects (AlternativeTo)](https://alternativeto.net/software/orrery)
