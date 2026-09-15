# PLUGIN TRUST MODEL (V16 — preview)

> How a community user decides whether a plugin is safe to install.
> No auto-install, no auto-execute, no silent promotion.

## Principles

1. **Explicit install only.** A plugin enters the machine only via an
   explicit `pip install` (or a local directory the user passes with
   `godseye plugins --dir`). Discovery never downloads, never scans the
   working directory, never scans `PATH`.
2. **Explicit discovery only.** Two mechanisms, both caller-driven:
   - packaging entry points, group `gods_eye.plugins` (advertised dict
     payloads, validated with `plugins.declare()`);
   - caller-supplied directories (`discover_from_dirs`, non-recursive
     `manifest.json` scan). No working-directory auto-scan.
3. **Declaration before code.** Discovery reads the advertised
   declaration dict and validates required keys (`name`, `version`,
   `kind`, `license`, `data_rights`, `capabilities`, `network`,
   `secrets`, `provenance`, `health`, `schema`). Plugin code beyond the
   declared payload is never imported by discovery.
4. **Rights-first.** A plugin whose data rights are UNKNOWN (or missing)
   is discoverable but never production-qualified:
   `production_qualified()` returns False, `qualify_or_refuse()` raises.
   Software licence and data rights are separate; UNKNOWN stays UNKNOWN.
5. **No private capabilities.** Declarations carrying alpha/private
   capability tokens (ranking, allocation, timing or settlement logic,
   source/model selection hooks) are refused at `declare()` time.
6. **No secrets, no undisclosed network.** The declaration must state
   `network` and `secrets` needs honestly. Execution paths refuse
   credential keys (`exec_safety.assert_no_credentials`). Discovery and
   demo paths make no outbound network calls (localhost only).
7. **Licence boundary.** In-process adapters must be permissive
   (Apache-2.0/MIT/BSD). Copyleft engine adapters run in a separate
   process only, never linked in-process. GPL/AGPL code is never linked.
8. **Core-only imports.** Community plugins import only modules that
   ship in the `gods_eye` package. `community_check()` and the
   import-boundary scan fail closed on anything else.

## What the user sees

`godseye plugins` reports per plugin: licence, data rights, network and
secrets needs, health, capabilities, schema version, and the
production-qualified flag (GREEN only when licence + schema +
non-UNKNOWN rights; otherwise YELLOW/UNKNOWN, never silent GREEN).

## What plugin authors must do

Declare identity, licence, data rights, capabilities, network/secrets,
provenance, health, and schema compatibility in `manifest.json`
(schema `plugin-v1`). Keep module scope stdlib-only; lazy-import heavy
libraries inside functions behind availability probes. Ship a fixture
and an offline test. See `CONTRIBUTING.md` and
`examples/plugins/example_sensor/`.
