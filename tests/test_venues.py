"""V15 multi-venue intelligence + open-core developer preview tests.

Fixtures-only, no network, no credentials, no live execution.
The open-core import boundary is asserted (see also tests/test_boundary.py).
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- venues ---

def test_venue_model_asset_classes_and_unknown():
    from gods_eye.future import venues as v
    assert {a.value for a in v.AssetClass} >= {
        "EQUITY", "ETF", "INDEX", "FX", "CRYPTO_SPOT", "CRYPTO_PERPETUAL",
        "FUTURE", "OPTION", "BINARY_CONTRACT", "PREDICTION_MARKET",
        "RATE", "COMMODITY", "UNKNOWN"}
    venue = v.Venue(venue_id="demo-venue", asset_classes=(v.AssetClass.ETF,))
    assert venue.supports(v.AssetClass.ETF) == "SUPPORTED"
    # never UNSUPPORTED by guess:
    assert venue.supports(v.AssetClass.FX) == "UNKNOWN"
    with pytest.raises(ValueError):
        v.Venue(venue_id="", asset_classes=())
    with pytest.raises(ValueError):
        v.Venue(venue_id="x", asset_classes=("EQUITY",))  # type: ignore[list-item]


def test_venue_capability_unknown_defaults():
    from gods_eye.future import venues as v
    cap = v.VenueCapability()
    assert cap.paper_support == "UNKNOWN" and cap.live_support == "UNKNOWN"
    assert cap.market_data.l2 == "UNKNOWN"
    assert cap.orders.modify == "UNKNOWN"
    assert cap.fees.maker_bps is None  # UNKNOWN, never 0-by-default
    inst = v.MarketInstrument(instrument_id="DEMO:X", venue_id="demo-venue",
                              symbol="X")
    assert inst.asset_class == v.AssetClass.UNKNOWN
    assert inst.settlement == v.SettlementType.UNKNOWN
    with pytest.raises(ValueError):
        v.MarketInstrument(instrument_id="", venue_id="v", symbol="s")


def test_trading_session_tz_enforced():
    from datetime import datetime, timezone
    from gods_eye.future import venues as v
    s = v.TradingSession(venue_id="XNYS", day="2026-09-14",
                         state=v.TradingSessionState.REGULAR)
    assert s.state == v.TradingSessionState.REGULAR
    with pytest.raises(ValueError):
        v.TradingSession(venue_id="XNYS", day="2026-09-14",
                         open_time=datetime(2026, 9, 14, 13, 30))  # naive


# ----------------------------------------------------- prediction markets ---

def test_prediction_market_shapes():
    from gods_eye.future import prediction_markets as pm
    yes = pm.OutcomeToken(token_id="t-yes", market_id="m1",
                          outcome=pm.BinaryOutcome.YES, collateral="pUSD")
    no = pm.OutcomeToken(token_id="t-no", market_id="m1",
                         outcome=pm.BinaryOutcome.NO, collateral="pUSD")
    m = pm.BinaryMarket(market_id="m1", venue_id="demo-pm",
                        question="demo?", yes_token=yes, no_token=no,
                        status="OPEN")
    assert len(m.tokens()) == 2
    mm = pm.MultiOutcomeMarket(market_id="m2", question="demo multi",
                               outcomes=(yes, no), status="OPEN")
    assert len(mm.outcome_labels()) == 2
    px = pm.ProbabilityPrice(outcome=pm.BinaryOutcome.YES, price=0.62)
    assert px.implied_probability() == pytest.approx(0.62)
    with pytest.raises(ValueError):
        pm.ProbabilityPrice(outcome=pm.BinaryOutcome.YES, price=1.5)
    ref = pm.ResolutionRuleReference(market_id="m1", status="OPEN")
    assert ref.status == "OPEN"
    with pytest.raises(ValueError):
        pm.ResolutionRuleReference(market_id="m1", status="GUARANTEED")
    st = pm.SettlementReceipt(receipt_id="r1", market_id="m1", status="MATCHED")
    assert st.status == "MATCHED"
    with pytest.raises(ValueError):
        pm.SettlementReceipt(receipt_id="r1", market_id="m1", status="PROFIT")


# ------------------------------------------------------- capability matrix ---

def test_venue_registry_unknown_stays_unknown():
    from gods_eye.future import venue_registry as vr
    rows = vr.registry(ccxt_version="ccxt-4.5.46")
    assert len(rows) >= 5
    by_id = {r["venue_id"]: r for r in rows}
    assert set(by_id) >= {"polymarket", "binance", "XNYS", "sec_edgar"}
    # UNKNOWN explicitly tracked:
    assert by_id["binance"]["redistribution_rights"] == "UNKNOWN"
    assert "redistribution_rights" in by_id["binance"]["unknown_fields"]
    # verified facts present:
    assert by_id["sec_edgar"]["redistribution_rights"] == "yes"
    assert by_id["polymarket"]["live_support"] == "UNSUPPORTED"
    s = vr.summary(ccxt_version="ccxt-4.5.46")
    assert s["n_venues"] == len(rows)
    assert vr.get("NOPE_XX") is None


# ------------------------------------------------------------------- ccxt ---

def test_ccxt_metadata_offline_deterministic():
    from gods_eye.future import ccxt_meta as cm
    if not cm.ccxt_available():
        pytest.skip("optional market extra (ccxt) not installed")
    inv = cm.list_exchange_ids()
    assert inv["n"] == 110 and "binance" in inv["venues"]
    assert "offline" in inv["basis"]
    a = cm.describe_exchange("binance")
    b = cm.describe_exchange("binance")
    assert a == b  # deterministic
    assert a["status"] == "DESCRIBED_OFFLINE"
    assert a["markets"].startswith("UNKNOWN")
    assert a["rights"].startswith("per-venue UNKNOWN")
    assert "ccxt-" in a["provenance"]
    unk = cm.describe_exchange("NOPE_XX")
    assert unk["status"] == "UNKNOWN"
    # caller-supplied market dict normalizes without network:
    norm = cm.normalize_market_dict("binance", {
        "symbol": "BTC/USDT", "base": "BTC", "quote": "USDT",
        "spot": True, "swap": False, "precision": {"price": 2},
        "limits": {"amount": {"min": 0.001}}, "maker": 0.001, "taker": 0.001})
    assert norm["symbol"] == "BTC/USDT" and norm["market_type"] == "spot"
    assert norm["status"].startswith("NORMALIZED")
    prov = cm.record_provenance("binance", "describe", "2026-09-14")
    assert prov["rights"].startswith("UNKNOWN")


# ------------------------------------------------- nautilus polymarket shape ---

def test_nautilus_polymarket_fixture_mapping():
    from gods_eye.future import nautilus_polymarket as npm
    from gods_eye.future import prediction_markets as pm
    from gods_eye.future.execution import OrderIntent, Side
    yes = pm.OutcomeToken(token_id="t-yes", market_id="m1",
                          outcome=pm.BinaryOutcome.YES)
    no = pm.OutcomeToken(token_id="t-no", market_id="m1",
                         outcome=pm.BinaryOutcome.NO)
    market = pm.BinaryMarket(market_id="m1", venue_id="SIM",
                             question="demo?", yes_token=yes, no_token=no,
                             currency="pUSD", status="OPEN")
    shape = npm.binary_market_to_nautilus_shape(market)
    assert shape["nautilus_instrument"] == "BinaryOption"
    assert shape["engine_status"].startswith("STAGED")
    intent = OrderIntent(intent_id="i1", instrument_id="SIM:m1", venue="SIM",
                         side=Side.BUY, quantity=5, order_type=__import__(
                             "gods_eye.future.execution", fromlist=["OrderType"]).OrderType.LIMIT,
                         provenance="fixture")
    order = npm.order_intent_to_nautilus_shape(intent, "stage-0")
    assert "LIMIT" in order["nautilus_semantics"]
    # STOP refused (Nautilus Polymarket has no STOP):
    bad = OrderIntent(intent_id="i2", instrument_id="SIM:m1", venue="SIM",
                      side=Side.BUY, quantity=5, order_type=__import__(
                          "gods_eye.future.execution", fromlist=["OrderType"]).OrderType.STOP,
                      provenance="fixture")
    with pytest.raises(ValueError):
        npm.order_intent_to_nautilus_shape(bad, "stage-1")
    smoke = npm.smoke_fixture_mapping(market, [intent])
    assert smoke["verdict"].startswith("MAPPING_EXECUTABLE")


# ------------------------------------------------------------- plugin SDK ---

def test_venue_and_prediction_market_plugin_kinds():
    from gods_eye.future import plugins as pl
    assert "Venue" in pl.KINDS and "PredictionMarket" in pl.KINDS
    base = dict(name="x", version="1", kind="Venue", license="MIT",
                data_rights="public", network="none", secrets="none",
                provenance="test", health="ok", schema="v1")
    assert pl.declare(capabilities=["describe"], **base)["kind"] == "Venue"
    pm_base = dict(base, kind="PredictionMarket")
    assert pl.declare(capabilities=["list_markets"], **pm_base)["kind"] == \
        "PredictionMarket"


def test_plugin_alpha_capabilities_refused():
    from gods_eye.future import plugins as pl
    base = dict(name="x", version="1", kind="Sensor", license="MIT",
                data_rights="public", network="none", secrets="none",
                provenance="test", health="ok", schema="v1")
    for caps in (["alpha_signals"], ["signal-scores"], ["timing_edge"],
                 ["settlement-edge"], ["strategy_rank"], ["capital_alloc"],
                 ["source_rank"], ["model_select"], ["execution edge"]):
        with pytest.raises(ValueError):
            pl.declare(capabilities=caps, **base)


def test_plugin_rights_declaration_required():
    from gods_eye.future import plugins as pl
    base = dict(name="x", version="1", kind="Sensor", license="MIT",
                network="none", secrets="none",
                provenance="test", health="ok", schema="v1")
    ok = dict(base, data_rights="public-domain (synthetic CC0)")
    assert pl.production_qualified(pl.declare(capabilities=["poll"], **ok)) is True
    unk = dict(base, data_rights="UNKNOWN")
    assert pl.production_qualified(pl.declare(capabilities=["poll"], **unk)) is False
    with pytest.raises(ValueError):
        pl.qualify_or_refuse(pl.declare(capabilities=["poll"], **unk))
    with pytest.raises(ValueError):
        pl.declare(capabilities=["poll"], **base)  # missing data_rights


# --------------------------------------------------------------- public API ---

def test_public_api_registers():
    from gods_eye.future import public_api as api
    from gods_eye.future import plugins as pl
    api.clear_registry()
    try:
        decl = dict(name="s1", version="0.1", kind="Sensor", license="MIT",
                    data_rights="public", capabilities=["poll"],
                    network="none", secrets="none", provenance="t",
                    health="ok", schema="v1")
        r = api.register_sensor(decl)
        assert r["ok"] and r["slot"] == "sensor"
        vdecl = dict(decl, kind="Venue", capabilities=["describe"])
        rv = api.register_venue(vdecl)
        assert rv["slot"] == "venue"
        assert "register_venue" in api.api_surface()["functions"]
        with pytest.raises(ValueError):
            api.register_sensor(dict(decl, capabilities=["alpha_signals"]))
    finally:
        api.clear_registry()


# ---------------------------------------------------------------- demo data ---

def test_demo_dataset_redistribution_safe():
    from gods_eye.future import demo_dataset as dd
    ds = dd.demo_dataset()
    assert ds["license"].startswith("CC0")
    assert "REDISTRIBUTION" in ds["rights"]
    for key in ("world_event", "market_instrument", "evidence",
                "time_machine", "market_reaction", "venue"):
        assert key in ds
    v = dd.validate_no_holdout_refs()
    assert v["ok"] is True and v["hits"] == []


def test_demo_requires_no_credentials_and_no_holdout():
    from gods_eye.future import demo_dataset as dd
    from gods_eye.future import exec_safety as es
    blob = json.dumps(dd.demo_dataset()).lower()
    for token in ("api_key", "api_secret", "private_key", "mnemonic",
                  "passphrase", "password"):
        assert token not in blob
    with pytest.raises(es.LiveRefused):
        es.assert_mode_allowed("LIVE")
    # read-forbidden paths come from a downstream profile, never the core:
    from gods_eye.future import isolation
    isolation.configure(name="test", read_forbidden=("evals/sealed.json",))
    try:
        assert isolation.is_holdout(isolation.ROOT / "evals" / "sealed.json")
    finally:
        isolation.reset()


def test_no_live_execution():
    from gods_eye.future import exec_safety as es
    assert es.ALLOW_LIVE is False
    with pytest.raises(es.LiveRefused):
        es.LiveExecutionGuard().check("LIVE")


# ------------------------------------------------------- community boundary ---

def test_community_mode_runs_without_private_modules():
    from gods_eye.future import community as co
    rep = co.community_check()
    assert rep["community_mode"] is True
    assert rep["failed"] == []
    assert rep["private_introduced"] == []
    for cap in ("demo/replay", "world map", "evidence", "time machine",
                "generic market contracts"):
        assert cap in rep["capabilities"]


def test_open_core_private_import_boundary():
    pat = re.compile(
        r"^(import|from)\s+(ccxt|cryptofeed|nautilus_trader|hftbacktest|"
        r"skfolio|torch|duckdb)\b", re.MULTILINE)
    mods = ["venues", "prediction_markets", "venue_registry", "ccxt_meta",
            "nautilus_polymarket", "demo_dataset", "community", "public_api"]
    for name in mods:
        src = (ROOT / "python" / "gods_eye" / "future" / f"{name}.py"
               ).read_text(encoding="utf-8")
        assert pat.search(src) is None, f"forbidden module-scope import in {name}"
    for mod in ("gods_eye/cli", "gods_eye/demo"):
        src = (ROOT / "python" / (mod + ".py")).read_text(encoding="utf-8")
        from gods_eye.future import boundary
        assert boundary.secret_hits_text(src) == []


# ------------------------------------------------------------------ CLI / UI ---

def test_cli_doctor_smoke():
    from gods_eye.cli import cmd_doctor, cmd_plugins, cmd_sources
    rep = cmd_doctor()
    # WARN is allowed only for machine-specific rows (e.g. a busy port)
    assert rep["failed"] == 0 and rep["verdict"] in ("PASS", "WARN")
    assert {c["name"] for c in rep["checks"]} >= {
        "community-mode imports", "live execution disabled"}
    kinds = cmd_plugins()
    assert "Venue" in kinds["kinds"] and "PredictionMarket" in kinds["kinds"]
    src = cmd_sources()
    assert src["n_sources"] >= 1


def test_demo_payload_smoke():
    from gods_eye.demo import demo_payload, health_payload
    d = demo_payload()
    assert d["community_mode"] is True
    assert d["demo"]["dataset_id"] == "community-demo-v1"
    assert d["safety"]["ALLOW_LIVE"] is False
    h = health_payload()
    assert h["ok"] and h["allow_live"] is False


def test_ui_files_present():
    for f in ("demo.html", "landing.html", "ultra.html", "gallery.html"):
        assert (ROOT / "console" / f).is_file(), f
    demo = (ROOT / "console" / "demo.html").read_text(encoding="utf-8")
    assert "SYNTHETIC" in demo and "/api/demo" in demo
    landing = (ROOT / "console" / "landing.html").read_text(encoding="utf-8")
    assert "open-source world-intelligence platform" in landing
    # no proprietary alpha promises (the page explicitly disclaims them):
    assert "No market-beating claims" in landing or "no market-beating" in landing.lower()
    for hype in ("guaranteed returns", "will beat the market",
                 "risk-free profit", "beat the market with"):
        assert hype not in landing.lower()


def test_public_docs_present():
    for rel in ("README.md", "CONTRIBUTING.md", "SECURITY.md",
                "docs/README.md", "docs/OPEN_CORE_BOUNDARY.md",
                "docs/guides/security-defaults.md", "docs/guides/rights-policy.md",
                "legal/LICENSE_REVIEW.md", "legal/LICENSE_SIGNOFF.md"):
        assert (ROOT / rel).is_file(), rel
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "godseye demo" in readme
    assert "market beating" not in readme.lower()


def test_plugin_template_present_and_clean():
    base = ROOT / "examples" / "plugins" / "example_sensor"
    for f in ("manifest.json", "plugin.py", "fixture.json",
              "test_example_sensor.py"):
        assert (base / f).is_file(), f
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["secrets"] == "none" and manifest["network"] == "none"
    blob = ((base / "plugin.py").read_text(encoding="utf-8")
            + (base / "fixture.json").read_text(encoding="utf-8")).lower()
    # no credential material, no alpha hook identifiers (plain-English
    # "no alpha" disclaimers in comments are fine and expected):
    for token in ("api_key", "api_secret", "private_key", "mnemonic",
                  "alpha_signals", "timing_edge", "settlement_edge"):
        assert token not in blob
