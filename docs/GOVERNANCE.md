# Governance (lightweight)

## Roles

- **Maintainer** — merges, cuts preview numbers, owns the trust model and
  rights policy. Currently: the project maintainer (named at 1.0).
- **Contributors** — anyone with a green plugin + honest rights basis.

## Plugin acceptance

`godseye plugins validate` PASS-equivalent (no FAIL rows), offline test
green, licence + non-UNKNOWN rights + provenance declared, core-only
imports, no secrets, no outbound calls. One plugin per PR.

## Schema changes

`plugin-v1` is frozen for the preview series. A `plugin-v2` needs a
written proposal, example migration, and one release of deprecation
warning. `UNKNOWN`-valued fields never become required.

## Security fixes

Sensitive reports via `SECURITY.md` contact; fix privately, disclose
after a fix exists. Never break `ALLOW_LIVE=false` or the localhost
default without a major preview bump + note.

## Rights violations

Narrow the claim first (fixture → synthetic, docs → UNKNOWN), ask
questions later. Repeat or wilful violations are reverted.

## Breaking changes

Preview `0.x`: STABLE_PREVIEW breaks only with a minor bump + note in
`docs/` + deprecation warning where feasible.
