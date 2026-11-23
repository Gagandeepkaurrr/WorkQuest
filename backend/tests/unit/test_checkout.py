from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.errors import AppError
from app.engine.projections import project_visible_state
from app.engine.registry import load_scenario
from app.engine.replay import replay_branch
from app.engine.scoring import evaluate_score
from app.engine.transitions import apply_command, initial_state
from app.engine.types import Command


def act(state, scenario, command_type, **payload):
    return apply_command(
        state,
        Command(type=command_type, payload=payload, origin_id=f"event-{len(state.ledger) + 1}"),
        scenario,
    ).next_state


def reference():
    scenario = load_scenario("checkout-outage")
    state = initial_state(scenario)
    commands = [
        ("evidence.open", {"artifact_id": "checkout.logs"}),
        ("checkout.set_flag", {"enabled": False}),
        ("evidence.open", {"artifact_id": "checkout.config"}),
        ("checkout.publish_config", {}),
        ("checkout.invalidate_cache", {}),
        ("checkout.set_flag", {"enabled": True}),
        ("checkout.test_contract", {}),
        ("checkout.observe_health", {}),
    ]
    state = act(
        state,
        scenario,
        "mission.update",
        impact=30,
        status="impacted",
        next_action_id="evidence.open",
    )
    for k, p in commands:
        state = act(state, scenario, k, **p)
    state = act(state, scenario, "mission.diagnose", cause_id="config_contract_migration_missing")
    state = act(
        state,
        scenario,
        "mission.recap",
        cause_id="config_contract_migration_missing",
        outcome="successful",
    )
    state = act(state, scenario, "mission.finish")
    return scenario, state


def test_exact_checkout_reference_and_replay():
    scenario, state = reference()
    assert state.simulation_time == 10
    assert state.domain["failed_purchases"] == 30
    assert state.domain["origin_schema"] == state.domain["cache_schema"] == 2
    public = project_visible_state(state, scenario)
    assert public.metrics["p95_ms"] == 140
    assert public.metrics["successes_per_tick"] == 100
    score = evaluate_score(state, scenario)
    assert score.total_score == 100
    assert score.outcome == "successful"
    assert (
        replay_branch(initial_state(scenario), state.ledger, scenario).state_hash
        == state.canonical_hash()
    )


def test_negative_paths_and_hidden_evidence():
    s = load_scenario("checkout-outage")
    state = initial_state(s)
    assert "checkout.config" not in str(project_visible_state(state, s).artifacts)
    with pytest.raises(AppError):
        act(state, s, "evidence.open", artifact_id="checkout.config")
    restarted = act(state, s, "checkout.restart")
    assert restarted.domain["failed_purchases"] == 30
    assert project_visible_state(restarted, s).metrics["failure_percentage"] == 30
    invalidated = act(state, s, "checkout.invalidate_cache")
    assert invalidated.domain["cache_schema"] == 1
    state = act(state, s, "evidence.open", artifact_id="checkout.logs")
    state = act(state, s, "evidence.open", artifact_id="checkout.config")
    state = act(state, s, "checkout.publish_config")
    assert state.domain["cache_schema"] == 1
    state = act(state, s, "checkout.set_flag", enabled=False)
    state = act(state, s, "checkout.test_contract")
    state = act(state, s, "checkout.observe_health")
    assert not any(x["passed"] for x in state.verifications.values())


def test_relevant_fingerprint_and_free_reopens():
    scenario, state = reference()
    state = state.model_copy(deep=True)
    state.finalized = False
    old = state.simulation_time
    state = act(state, scenario, "evidence.open", artifact_id="checkout.logs")
    assert state.simulation_time == old
    assert all(x.current for x in project_visible_state(state, scenario).verifications.values())
    state = act(state, scenario, "checkout.set_flag", enabled=False)
    assert not any(x.current for x in project_visible_state(state, scenario).verifications.values())


def test_cap_and_rejected_command_does_not_mutate():
    scenario = load_scenario("checkout-outage")
    state = initial_state(scenario)
    for _ in range(19):
        state = act(state, scenario, "checkout.restart")
    before = deepcopy(state)
    with pytest.raises(AppError):
        act(state, scenario, "checkout.observe_health")
    assert state == before
    state = act(state, scenario, "checkout.restart")
    assert state.simulation_time == 20 and state.finalized
    with pytest.raises(AppError):
        act(state, scenario, "checkout.restart")


@given(st.lists(st.booleans(), max_size=20))
def test_scores_bounded_and_state_is_pure(flags):
    scenario = load_scenario("checkout-outage")
    state = initial_state(scenario)
    for flag in flags:
        before = deepcopy(state)
        new = act(state, scenario, "checkout.set_flag", enabled=flag)
        assert state == before
        state = new
    assert 0 <= evaluate_score(state, scenario).total_score <= 100
    assert 0 <= state.simulation_time <= 20
