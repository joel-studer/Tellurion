# RIGHTS-FIRST PLUGIN POLICY (V15)

Community plugins must declare data rights. A plugin with UNKNOWN rights
cannot silently become production-qualified.

## Rule

- `declare()` requires `license`, `data_rights`, `schema` keys (missing -> refuse).
- `production_qualified(declaration)` is False when `data_rights` is
  UNKNOWN/empty, or licence/schema are UNKNOWN/empty.
- `qualify_or_refuse()` raises for unqualified plugins.
- Alpha/private capability tokens (`alpha`, `signal`, `edge`,
  `strategy_rank`, `capital_alloc`, `timing_edge`, `settlement_edge`,
  `source_rank`, `model_select`, ...) are refused at declaration.

## UI exposure

Plugin discovery surfaces, per plugin:

- licence
- data rights (status + basis)
- network needs
- secrets needs
- health
- capabilities (sensor / entity-resolver / visualization)
- schema version
- production-qualified flag (GREEN only when licence + schema +
  non-UNKNOWN rights; otherwise YELLOW/UNKNOWN, never silent GREEN)

## Enforcement

- `tests/test_ultra.py` and `tests/test_preview_surface.py` assert:
  UNKNOWN-rights plugin is discoverable but not qualified;
  alpha-capability plugin is refused; missing-rights declaration raises.
- `console/demo.html` + future community UI show the qualified flag
  alongside health/capabilities (no silent promotion).
