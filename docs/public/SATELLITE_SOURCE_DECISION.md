# SATELLITE SOURCE RESEARCH (verified 2026-09-16)

> Metadata only. No terms-page content is copied into this repo.
> Review method: live documentation fetch + search-verified usage
> policy text. Re-verify before any activation.

## DECISION: NONE QUALIFIED for live use

No orbital-data source currently clears the Tellurion gate with a
citable licence for operational product use. Live satellites
therefore stay SYNTHETIC REPLAY (positions explicitly synthetic);
WORLD NOW shows an honest NO LIVE SOURCE state for satellites.

## Candidate 1 — CelesTrak (NOT enabled; blocker stands)

- endpoints: documented GP queries
  (`https://celestrak.org/NORAD/elements/gp.php?{CATNR,INTDES,GROUP,
  NAME,SPECIAL}=…&FORMAT={CSV,TLE,JSON-PRETTY}`), SATCAT/SOCRATES/EOP
- docs: usage policy + GP format docs (verified live 2026-09-16)
- usage_policy: documented queries only; GP refresh ≈ 2 h; EOP daily;
  directories ≤ 1/h; enforced limits on large sets; stop on HTTP 50x;
  abuse → firewall (a 2026-04-28 community case documents exactly
  this: repeated errors + legacy queries + no backoff = blocked)
- licence: **no citable grant for operational/commercial product use**
  (usage policy governs politeness, not rights; underlying data is
  USSF/18 SPCS-sourced via Space-Track, whose own user agreement
  applies upstream)
- verdict: NEEDS_TERMS_REVIEW → NOT enabled. The previous rights
  blocker is NOT resolved. A future path needs either a written
  clarification or a different qualified element source. Note the
  catalog has moved to 6-digit numbers (TLE format cannot carry
  them) — any future adapter must use CSV/OMM, never legacy TLE.

## Candidate 2 — Space-Track (not pursued)

- Requires user account + explicit user agreement; acceptable only
  as a future operator-key path with the operator's own agreement.
  Not implemented (no standby demand).

## Candidate 3 — NASA public catalogs (no live element feed found)

- No keyless live general-perturbation feed identified that meets
  the gate. Revisit on evidence.

## Safety + truth rules (binding when any satellite leg activates)

- Allowed: public catalog visualization; civil/weather/science
  objects; generic public catalog objects; provider-public military
  classification WITHOUT operational inference.
- Forbidden: tactical military satellite analysis, targeting
  functionality, mission prediction, base-to-object correlation for
  targeting.
- Truth discipline: propagated positions are CALCULATED
  (model output, SGP4-family, epoch-aged) — never presented as
  DIRECT OBSERVATION. Every object carries NORAD/catalog id (if
  public), epoch, orbit freshness, source. Accuracy degrades with
  epoch age — show it.
