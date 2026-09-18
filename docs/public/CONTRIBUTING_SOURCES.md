# CONTRIBUTING A PUBLIC SOURCE (PR checklist)

Tellurion is: "Open-source, local-first world intelligence from
public data." Never: spy/surveillance/track-people/see-everything.

## Proposal must include

- [ ] source name, operator, domain, coverage, latency, update frequency
- [ ] authentication, rate limit, commercial use, redistribution,
      retention, attribution, licence, terms URL (archived text + hash)
- [ ] confidence + integration effort + visual value
- [ ] adapter (pure parse function over caller-fetched text; no fetch,
      no secrets, 4 MB cap, coordinate/timestamp validation)
- [ ] fixture (CC0 or public-domain sample, no persons, no scraped PII)
- [ ] tests (parse fixture; reject oversize; reject bad coords;
      UNKNOWN timestamps stay UNKNOWN)
- [ ] health mapping (ONLINE/DEGRADED/STALE/OFFLINE/RATE LIMITED/
      AUTH REQUIRED/RIGHTS BLOCKED) + refresh interval + cache TTL
- [ ] rights panel text (licence, attribution, redistribution,
      commercial use, retention, terms link) or UNKNOWN/NEEDS REVIEW

## Review questions (must answer in the PR)

1. Where are the terms? (URL + archived hash + date)
2. Commercial use? (quote the clause or UNKNOWN)
3. Redistribution? (quote the clause or UNKNOWN — "public API" is not
   an answer)
4. Rate limit? (documented limit + backoff plan)
5. Auth? (none / user-key-local / feed-share — never bundled)
6. Attribution? (exact string to display)

## Hard rejects

Private CCTV/RTSP/ONVIF, home cameras, facial/person/plate tracking,
device/Wi-Fi/BT/phone tracking, deanonymization, covert personnel
tracking, protected communications, paywall/auth bypass, shared
credentials, targeting/strike guidance.
