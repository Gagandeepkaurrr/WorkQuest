from app.engine.transitions import apply_command
from app.engine.types import Command, ReplayResult, Scenario, WorldState


def replay_branch(base_snapshot: WorldState,recorded_commands: list[dict],scenario: Scenario) -> ReplayResult:
    state=base_snapshot.model_copy(deep=True)
    inherited={e['origin_id'] for e in state.ledger}
    for record in recorded_commands:
        if record['origin_id'] in inherited:continue
        state=apply_command(state,Command(type=record['type'],payload=record['payload'],origin_id=record['origin_id']),scenario).next_state
    return ReplayResult(state=state,state_hash=state.canonical_hash())
