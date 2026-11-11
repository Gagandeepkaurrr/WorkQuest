from app.core.errors import AppError
from app.engine.registry import mechanics
from app.engine.types import Command, Scenario, WorldState
from app.engine.visibility import available_artifacts

COMMON = {
    "evidence.open",
    "mission.diagnose",
    "mission.update",
    "mission.recap",
    "mission.hint",
    "mission.finish",
}


def validate_payload(payload: dict, fields: dict, optional: set | None = None):
    optional = optional or set()
    if set(payload) - set(fields) or set(fields) - set(payload) - optional:
        raise AppError("VALIDATION_ERROR", "The operation parameters are invalid.", 422)
    for key, value in payload.items():
        rule = fields[key]
        if isinstance(rule, tuple):
            valid = value in rule and type(value) is str
        elif rule is int:
            valid = type(value) is int
        else:
            valid = isinstance(value, rule) and (rule is not bool or type(value) is bool)
        if not valid:
            raise AppError("VALIDATION_ERROR", "An operation parameter has an invalid value.", 422)


def validate_command(state: WorldState, command: Command, scenario: Scenario) -> int:
    if state.finalized:
        raise AppError("BRANCH_FINALIZED", "This attempt is finalized. Try another branch.", 409)
    kind, p = command.type, command.payload
    module = mechanics(scenario)
    if kind == "evidence.open":
        validate_payload(p, {"artifact_id": str})
        if p["artifact_id"] not in {a.id for a in available_artifacts(state, scenario)}:
            raise AppError("NOT_FOUND", "Artifact unavailable.", 404)
        return 0 if p["artifact_id"] in state.opened else 1
    if kind == "mission.diagnose":
        validate_payload(p, {"cause_id": tuple(c.id for c in scenario.diagnosis_choices)})
    elif kind == "mission.update":
        validate_payload(p, {"impact": int, "status": str, "next_action_id": str})
    elif kind == "mission.recap":
        validate_payload(
            p,
            {
                "cause_id": tuple(c.id for c in scenario.diagnosis_choices),
                "outcome": ("successful", "contained", "unresolved"),
            },
        )
    elif kind in ("mission.hint", "mission.finish"):
        validate_payload(p, {})
    elif kind in module.COSTS:
        validate_payload(p, module.PARAMETERS.get(kind, {}))
        if any(a not in state.opened for a in module.REQUIRES.get(kind, [])):
            raise AppError("PRECONDITION_FAILED", "Read the required evidence first.", 409)
        if hasattr(module, "precondition"):
            module.precondition(state.domain, kind)
        return module.COSTS[kind]
    else:
        raise AppError("INVALID_ACTION", "Unknown simulated operation.", 422)
    return 0
