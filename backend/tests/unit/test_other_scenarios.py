import pytest

from app.core.errors import AppError
from app.engine.projections import project_visible_state
from app.engine.registry import load_scenario
from app.engine.scoring import evaluate_score
from app.engine.transitions import initial_state
from tests.unit.test_checkout import act


def complete(slug):
    s = load_scenario(slug)
    state = initial_state(s)
    state = act(
        state,
        s,
        "mission.update",
        impact=10 if slug == "inventory-race" else 40,
        status="impacted" if slug == "inventory-race" else "incorrect",
        next_action_id="evidence.open",
    )
    for c in s.golden_commands:
        state = act(state, s, c["type"], **c["payload"])
    state = act(state, s, "mission.diagnose", cause_id=s.rubric.cause_id)
    state = act(state, s, "mission.recap", cause_id=s.rubric.cause_id, outcome="successful")
    return s, act(state, s, "mission.finish")


def test_inventory_exact_reference():
    s, state = complete("inventory-race")
    m = project_visible_state(state, s).metrics
    assert state.simulation_time == 11
    assert m["new_oversells"] == m["lost_sales"] == m["invalid_reservations"] == 0
    assert m["accepted_per_tick"] == 20 and m["sold_out_per_tick"] == 5 and m["p95_ms"] == 100
    assert evaluate_score(state, s).total_score == 100


def test_inventory_negatives_and_fixture_isolation():
    s = load_scenario("inventory-race")
    state = initial_state(s)
    state = act(state, s, "evidence.open", artifact_id="inventory.ledger")
    before = state.canonical_hash()
    with pytest.raises(AppError):
        act(state, s, "inventory.reconcile")
    assert state.canonical_hash() == before
    state = act(state, s, "inventory.set_queue", enabled=True)
    state = act(state, s, "evidence.open", artifact_id="inventory.trace")
    state = act(state, s, "evidence.open", artifact_id="inventory.patch_review")
    state = act(state, s, "inventory.deploy_patch", kind="idempotency_only")
    count = len(state.domain["legitimate_ids"])
    state = act(state, s, "inventory.test_race")
    assert state.verifications["inventory.test_race"]["passed"] is False
    assert len(state.domain["legitimate_ids"]) == count + 20  # only ordinary tick, not fixture
    state = act(state, s, "inventory.deploy_patch", kind="atomic")
    assert state.domain["invalid_reservations"] > 0
    state = act(state, s, "inventory.set_sales", status="suspended")
    state = act(state, s, "inventory.test_ledger")
    assert not state.verifications["inventory.test_ledger"]["passed"]


def test_analytics_exact_reference():
    s, state = complete("analytics-timezone")
    m = project_visible_state(state, s).metrics
    assert state.simulation_time == 10 and m["incorrect_publications"] == 0
    assert [(r["orders"], r["revenue_cents"], r["conversion_percentage"]) for r in m["rows"]] == [
        (60, 600000, 60),
        (30, 300000, 60),
    ]
    assert m["total_orders"] == 90 and m["total_revenue_cents"] == 900000
    assert evaluate_score(state, s).total_score == 100


def test_analytics_negative_paths_and_stale_report():
    s = load_scenario("analytics-timezone")
    state = initial_state(s)
    state = act(state, s, "evidence.open", artifact_id="analytics.sources")
    state = act(state, s, "analytics.test_totals")
    assert state.verifications["analytics.test_totals"]["passed"]
    state = act(state, s, "analytics.restart_ingestion")
    assert state.domain["rows"][0]["orders"] == 40
    state = act(state, s, "evidence.open", artifact_id="analytics.transforms")
    state = act(state, s, "evidence.open", artifact_id="analytics.boundary_spec")
    state = act(state, s, "analytics.set_normalization", mode="fixed_minus_7")
    assert state.domain["rows"][0]["orders"] == 40
    assert not project_visible_state(state, s).verifications["analytics.test_totals"].current
    state = act(state, s, "analytics.rebuild")
    assert state.domain["rows"][0]["orders"] == 60
    state = act(state, s, "analytics.test_boundaries")
    assert not state.verifications["analytics.test_boundaries"]["passed"]
    state = act(state, s, "analytics.publish")
    assert state.domain["incorrect_publications"] == 1
    assert evaluate_score(state, s).outcome != "successful"
