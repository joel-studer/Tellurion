"""GOD'S EYE extended namespace: SDK, demo, contracts, and safety gates.

Everything under ``gods_eye.future`` is part of the open-source core:

* plugin SDK, discovery, validator, and public API
* world layers, sensor registry, Ultra demo, synthetic datasets
* generic market, execution, and portfolio contracts (fixtures only)
* safety gates: ``exec_safety`` (live execution disabled in code),
  ``isolation`` (profile-driven path guard), ``boundary`` (open-core
  scans), ``extensions`` (slots for downstream capabilities)

Nothing in here activates trading, live execution, or credentials.
"""

from __future__ import annotations
