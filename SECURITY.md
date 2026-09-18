# Security policy

## Supported versions

| Version | Supported |
|---|---|
| `0.x` community preview (unpublished candidate) | Best-effort review of reports |
| Any `live` / trading configuration | **Not part of this preview** |

Live execution is disabled in code (`ALLOW_LIVE=false`). There is no
production deployment to patch in this tree.

## Reporting

Do **not** open a public issue for sensitive reports. Use GitHub private
vulnerability reporting (repository **Security** tab, **Report a
vulnerability**).
- Include: affected file/commit, reproduction steps, impact, and whether
  credentials or private data are involved.

## Plugin trust warning

Plugins run with your user privileges. Install only plugins you trust:

- explicit `pip install` or `--dir` only (discovery never downloads),
- read `manifest.json` (licence, rights, network, secrets) before use,
- `tellurion plugins validate ./plugin_dir` must not report FAIL,
- UNKNOWN data rights = never production-qualified.

## Data-rights responsibility

Software licence and data rights are separate. Contributors must only
submit data they may redistribute; reviewers check rights basis per
`docs/guides/rights-policy.md`.

## Lawful-use scope

Lawful public and licensed data only. Do not use this project to
scrape sources, circumvent access controls or paywalls, or violate
terms of service. Report rights violations as data-rights issues.

## Telemetry / network

Community paths make no outbound network calls (localhost only).
`tellurion doctor` verifies this on every run.
