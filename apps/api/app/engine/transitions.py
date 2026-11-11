from app.core.errors import AppError
from app.engine.commands import validate_command
from app.engine.registry import mechanics
from app.engine.scoring import communication_status, outcome, tests_pass
from app.engine.types import Command, Scenario, TransitionResult, WorldState, canonical_hash
from app.engine.visibility import available_artifacts


def initial_state(scenario: Scenario) -> WorldState:
    state = WorldState(domain=scenario.initial_state.copy())
    state.metric_history = [{"tick": 0, **mechanics(scenario).metrics(state.domain)}]
    return state


def allowed_next_actions(state: WorldState, scenario: Scenario) -> list[str]:
    result = []
    if any(a.id not in state.opened for a in available_artifacts(state, scenario)):
        result.append("evidence.open")
    m = mechanics(scenario)
    for action in scenario.action_catalog:
        if any(r not in state.opened for r in action.requires):
            continue
        try:
            if hasattr(m, "precondition"):
                m.precondition(state.domain, action.id)
        except AppError:
            continue
        if state.simulation_time + action.cost <= 20:
            result.append(action.id)
    return result


def apply_command(state: WorldState, command: Command, scenario: Scenario) -> TransitionResult:
    cost = validate_command(state, command, scenario)
    if state.simulation_time + cost > 20:
        raise AppError(
            "INVALID_ACTION", "This operation would exceed the 20-minute logical limit.", 409
        )
    s = state.model_copy(deep=True)
    kind, p = command.type, command.payload
    m = mechanics(scenario)
    result = {"message": "Decision recorded."}
    if kind == "evidence.open":
        if p["artifact_id"] not in s.opened:
            s.opened.append(p["artifact_id"])
        result = {"artifact_id": p["artifact_id"], "message": "Evidence opened."}
    elif kind == "mission.diagnose":
        s.diagnosis = p["cause_id"]
    elif kind == "mission.update":
        if (
            p["impact"] != m.impact(s.domain)
            or p["status"] != communication_status(s, scenario)
            or p["next_action_id"] not in allowed_next_actions(s, scenario)
        ):
            raise AppError(
                "PRECONDITION_FAILED",
                "Update the impact, status and next step to match the current simulation.",
                409,
            )
        s.updates.append({**p, "origin_id": command.origin_id})
    elif kind == "mission.recap":
        s.recap = {**p, "origin_id": command.origin_id}
    elif kind == "mission.hint":
        hint = next(
            (
                h
                for h in scenario.hints
                if h.id not in s.hints and all(r in s.opened for r in h.requires)
            ),
            None,
        )
        if hint:
            s.hints.append(hint.id)
            result = {"hint_id": hint.id, "text": hint.text}
        else:
            result = {"message": "No further hint is available at this point."}
    elif kind == "mission.finish":
        s.finalized = True
    elif kind == "analytics.publish":
        result = m.publish(s.domain, tests_pass(s, scenario))
    else:
        result = m.mutate(s.domain, kind, p)
    ticks = []
    for _ in range(cost):
        s.simulation_time += 1
        m.tick(s.domain, s.simulation_time)
        metric = {"tick": s.simulation_time, **m.metrics(s.domain)}
        ticks.append(metric)
        s.metric_history.append(metric)
    if kind in m.TESTS:
        passed, detail = m.test_result(s.domain, kind, ticks)
        s.verifications[kind] = {
            "passed": passed,
            "detail": detail,
            "fingerprint": canonical_hash(m.fingerprint(s.domain, kind)),
            "origin_id": command.origin_id,
            "logical_tick": s.simulation_time,
        }
        result = {
            "passed": passed,
            "detail": detail,
            "label": "Isolated test fixture" if "test_" in kind else "Simulation observation",
        }
    if s.simulation_time == 20:
        s.finalized = True
    entry = {**command.model_dump(), "logical_tick": s.simulation_time, "result": result}
    s.ledger.append(entry)
    events = [
        {
            "type": kind,
            "origin_id": command.origin_id,
            "payload": p,
            "result": result,
            "logical_tick": s.simulation_time,
        }
    ]
    if s.finalized:
        events.append(
            {
                "type": "branch.finalized",
                "payload": {"outcome": outcome(s, scenario)},
                "logical_tick": s.simulation_time,
            }
        )
    return TransitionResult(next_state=s, events=events, ticks_applied=cost, result=result)
